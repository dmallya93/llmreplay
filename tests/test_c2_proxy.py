"""C2 proxy contract tests — allowlist, record, replay, miss."""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route
from typer.testing import CliRunner

from llmreplay.cli.main import app
from llmreplay.proxy.app import create_app
from llmreplay.proxy.routes import is_allowed
from llmreplay.store.cassette import CassetteStore

runner = CliRunner()


def _fake_upstream() -> Starlette:
    async def messages(request: Request) -> JSONResponse:
        body = await request.json()
        return JSONResponse(
            {
                "id": "msg_fake",
                "model": body.get("model", "fake"),
                "content": [{"type": "text", "text": "hello-from-upstream"}],
                "usage": {"input_tokens": 1, "output_tokens": 1},
            }
        )

    async def chat(_request: Request) -> JSONResponse:
        return JSONResponse(
            {
                "id": "chat_fake",
                "choices": [{"message": {"role": "assistant", "content": "hi"}}],
            }
        )

    async def responses(_request: Request) -> JSONResponse:
        return JSONResponse({"id": "resp_fake", "output": [{"type": "text", "text": "ok"}]})

    async def models(_request: Request) -> JSONResponse:
        return JSONResponse({"object": "list", "data": [{"id": "upstream-model"}]})

    return Starlette(
        routes=[
            Route("/v1/messages", messages, methods=["POST"]),
            Route("/v1/chat/completions", chat, methods=["POST"]),
            Route("/v1/responses", responses, methods=["POST"]),
            Route("/v1/models", models, methods=["GET"]),
        ]
    )


@pytest.mark.contract
def test_allowlist() -> None:
    assert is_allowed("GET", "/healthz")
    assert is_allowed("POST", "/v1/messages")
    assert not is_allowed("POST", "/v1/secret")


@pytest.mark.contract
@pytest.mark.asyncio
async def test_denied_route(tmp_path: Path) -> None:
    proxy = create_app(mode="replay", cassette_dir=tmp_path / "c")
    transport = httpx.ASGITransport(app=proxy)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/v1/secret", json={})
    assert resp.status_code == 404
    assert resp.json()["error"]["type"] == "llmreplay_route_denied"


@pytest.mark.contract
@pytest.mark.asyncio
async def test_healthz(tmp_path: Path) -> None:
    proxy = create_app(mode="replay", cassette_dir=tmp_path / "c")
    transport = httpx.ASGITransport(app=proxy)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json()["ok"] is True


@pytest.mark.contract
@pytest.mark.asyncio
async def test_record_then_replay(tmp_path: Path) -> None:
    upstream = _fake_upstream()
    cassette = tmp_path / "cass"

    class _UpstreamClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):  # noqa: ANN002, ARG002
            return None

        async def request(self, method, url, content=None, headers=None):  # noqa: ANN001
            from urllib.parse import urlparse

            parsed = urlparse(url)
            transport = httpx.ASGITransport(app=upstream)
            async with httpx.AsyncClient(transport=transport, base_url="http://up") as client:
                return await client.request(
                    method, parsed.path, content=content, headers=headers or {}
                )

    record_app = create_app(
        mode="record",
        cassette_dir=cassette,
        upstream_base="http://upstream",
        http_client_factory=_UpstreamClient,
    )
    transport = httpx.ASGITransport(app=record_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://proxy") as client:
        r1 = await client.post(
            "/v1/messages",
            json={"model": "fake", "messages": [{"role": "user", "content": "hi"}]},
        )
        assert r1.status_code == 200
        assert "hello-from-upstream" in json.dumps(r1.json())

        r_chat = await client.post(
            "/v1/chat/completions",
            json={"model": "fake", "messages": []},
        )
        assert r_chat.status_code == 200

        r_resp = await client.post("/v1/responses", json={"model": "fake"})
        assert r_resp.status_code == 200

    assert (cassette / "cassette.json").is_file()
    store = CassetteStore(cassette)
    manifest = store.load_manifest()
    assert len(manifest.transactions) >= 3

    replay_app = create_app(mode="replay", cassette_dir=cassette)
    transport = httpx.ASGITransport(app=replay_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://proxy") as client:
        r2 = await client.post(
            "/v1/messages",
            json={"model": "fake", "messages": [{"role": "user", "content": "hi"}]},
        )
        assert r2.status_code == 200
        assert "hello-from-upstream" in json.dumps(r2.json())

        miss = await client.post(
            "/v1/messages",
            json={"model": "other", "messages": [{"role": "user", "content": "hi"}]},
        )
        assert miss.status_code == 409
        assert miss.json()["error"]["type"] == "llmreplay_miss"

        models = await client.get("/v1/models")
        assert models.status_code == 200


@pytest.mark.unit
def test_proxy_cli_requires_upstream_in_record() -> None:
    result = runner.invoke(app, ["proxy", "--mode", "record"])
    assert result.exit_code == 9
