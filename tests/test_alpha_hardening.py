"""Alpha hardening: ignore wiring, SSE synthesis, migrate fail-hard, loopback."""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from llmreplay.migrate.engine import migrate_cassette
from llmreplay.proxy.app import create_app
from llmreplay.proxy.config import ProxyConfig
from llmreplay.proxy.sse import parse_openai_sse, synthesize_sse, wants_stream
from llmreplay.scrub.engine import resolve_hmac_key
from llmreplay.store.cassette import CassetteStore


def _fake_upstream() -> Starlette:
    async def messages(request: Request) -> JSONResponse:
        body = await request.json()
        assert body.get("stream") is not True
        return JSONResponse(
            {
                "id": "msg_fake",
                "model": body.get("model", "fake"),
                "content": [{"type": "text", "text": "hello-sse"}],
            }
        )

    async def chat(request: Request) -> JSONResponse:
        body = await request.json()
        assert body.get("stream") is not True
        return JSONResponse(
            {
                "id": "chat_fake",
                "choices": [
                    {"message": {"role": "assistant", "content": "streamed-hi"}},
                ],
            }
        )

    return Starlette(
        routes=[
            Route("/v1/messages", messages, methods=["POST"]),
            Route("/v1/chat/completions", chat, methods=["POST"]),
        ]
    )


class _UpstreamClient:
    def __init__(self, upstream: Starlette) -> None:
        self._upstream = upstream

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):  # noqa: ANN002, ARG002
        return None

    async def request(self, method, url, content=None, headers=None):  # noqa: ANN001
        from urllib.parse import urlparse

        parsed = urlparse(url)
        transport = httpx.ASGITransport(app=self._upstream)
        async with httpx.AsyncClient(transport=transport, base_url="http://up") as client:
            return await client.request(method, parsed.path, content=content, headers=headers or {})


@pytest.mark.contract
@pytest.mark.asyncio
async def test_mark_ignore_changes_match_via_yaml(tmp_path: Path) -> None:
    """Custom ignore fields from llmreplay.yaml must flow into match_key."""
    cassette = tmp_path / "cass"
    cfg_path = tmp_path / "llmreplay.yaml"
    cfg_path.write_text(
        "defaults:\n  ignore:\n    - noise_field\n",
        encoding="utf-8",
    )
    upstream = _fake_upstream()

    record_app = create_app(
        config=ProxyConfig(
            mode="record",
            cassette_dir=cassette,
            upstream_base="http://upstream",
            config_path=cfg_path,
        ),
        http_client_factory=lambda: _UpstreamClient(upstream),
    )
    transport = httpx.ASGITransport(app=record_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://proxy") as client:
        r1 = await client.post(
            "/v1/messages",
            json={
                "model": "fake",
                "messages": [{"role": "user", "content": "hi"}],
                "noise_field": "aaa",
            },
        )
        assert r1.status_code == 200

    replay_app = create_app(
        config=ProxyConfig(
            mode="replay",
            cassette_dir=cassette,
            config_path=cfg_path,
        ),
    )
    transport = httpx.ASGITransport(app=replay_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://proxy") as client:
        hit = await client.post(
            "/v1/messages",
            json={
                "model": "fake",
                "messages": [{"role": "user", "content": "hi"}],
                "noise_field": "ZZZ-different",
            },
        )
        assert hit.status_code == 200
        assert hit.json()["content"][0]["text"] == "hello-sse"

    # Without the yaml ignore, the same bodies must miss.
    bare = create_app(mode="replay", cassette_dir=cassette)
    transport = httpx.ASGITransport(app=bare)
    async with httpx.AsyncClient(transport=transport, base_url="http://proxy") as client:
        miss = await client.post(
            "/v1/messages",
            json={
                "model": "fake",
                "messages": [{"role": "user", "content": "hi"}],
                "noise_field": "ZZZ-different",
            },
        )
        assert miss.status_code == 409


@pytest.mark.contract
@pytest.mark.asyncio
async def test_replay_stream_true_synthesizes_sse(tmp_path: Path) -> None:
    cassette = tmp_path / "cass"
    store = CassetteStore(cassette)
    event = {
        "method": "POST",
        "path": "/v1/chat/completions",
        "headers": {},
        "body": {"model": "m", "messages": [{"role": "user", "content": "x"}]},
    }
    from llmreplay.core.match import match_key

    store.append_transaction(
        request=event,
        response={
            "id": "chat_1",
            "choices": [{"message": {"role": "assistant", "content": "hello-chunk"}}],
        },
        static_hash=match_key(event),
    )
    app = create_app(mode="replay", cassette_dir=cassette)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://proxy") as client:
        resp = await client.post(
            "/v1/chat/completions",
            json={
                "model": "m",
                "messages": [{"role": "user", "content": "x"}],
                "stream": True,
            },
        )
        assert resp.status_code == 200
        assert "text/event-stream" in resp.headers["content-type"]
        text = resp.text
        assert "hello-chunk" in text
        assert "data: [DONE]" in text


@pytest.mark.contract
@pytest.mark.asyncio
async def test_record_strips_stream_for_upstream(tmp_path: Path) -> None:
    cassette = tmp_path / "cass"
    upstream = _fake_upstream()
    record_app = create_app(
        mode="record",
        cassette_dir=cassette,
        upstream_base="http://upstream",
        http_client_factory=lambda: _UpstreamClient(upstream),
    )
    transport = httpx.ASGITransport(app=record_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://proxy") as client:
        resp = await client.post(
            "/v1/messages",
            json={
                "model": "fake",
                "messages": [{"role": "user", "content": "hi"}],
                "stream": True,
            },
        )
        assert resp.status_code == 200
        assert "text/event-stream" in resp.headers["content-type"]
        assert "hello-sse" in resp.text


@pytest.mark.unit
def test_sse_helpers() -> None:
    assert wants_stream({"stream": True}) is True
    assert wants_stream({}, {"Accept": "text/event-stream"}) is True
    assert wants_stream({}) is False
    anthropic = synthesize_sse(
        "/v1/messages",
        {"id": "m", "content": [{"type": "text", "text": "t"}]},
    )
    assert b"message_start" in anthropic
    assembled = parse_openai_sse(
        'data: {"choices":[{"delta":{"content":"a"}}]}\n\n'
        'data: {"choices":[{"delta":{"content":"b"}}]}\n\n'
        "data: [DONE]\n\n"
    )
    assert assembled["choices"][0]["message"]["content"] == "ab"


@pytest.mark.unit
def test_replay_refuses_non_loopback_host(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="non-loopback"):
        ProxyConfig(mode="replay", cassette_dir=tmp_path, host="0.0.0.0")
    ok = ProxyConfig(
        mode="replay",
        cassette_dir=tmp_path,
        host="0.0.0.0",
        allow_non_loopback=True,
    )
    assert ok.host == "0.0.0.0"


@pytest.mark.unit
def test_hmac_fallback_is_random_not_fixed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LLMREPLAY_HMAC_KEY", raising=False)
    import llmreplay.scrub.engine as eng

    eng._PROCESS_HMAC_KEY = None
    a = resolve_hmac_key()
    b = resolve_hmac_key()
    assert a == b
    assert a != b"llmreplay-ephemeral-dev-key"
    assert len(a) == 32


@pytest.mark.unit
def test_migrate_fails_on_corrupt_request_blob(tmp_path: Path) -> None:
    cass = tmp_path / "bad"
    cass.mkdir()
    req = cass / "requests"
    req.mkdir()
    (req / "tx0.json").write_text("{not-json", encoding="utf-8")
    (cass / "cassette.json").write_text(
        json.dumps(
            {
                "cassette_id": "x",
                "transactions": [
                    {
                        "id": "tx0",
                        "request_ref": "requests/tx0.json",
                        "response_ref": "responses/tx0.json",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="cannot recompute static_hash"):
        migrate_cassette(cass)
