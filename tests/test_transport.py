"""Tests for ReplayTransport / RecordTransport (in-process, no port binding)."""

from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse

import httpx
import pytest
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from llmreplay.scrub.engine import Scrubber
from llmreplay.store.cassette import CassetteStore
from llmreplay.transport import RecordTransport, ReplayTransport


def _fake_upstream() -> Starlette:
    async def messages(request: Request) -> JSONResponse:
        body = await request.json()
        return JSONResponse(
            {
                "id": "msg_transport",
                "model": body.get("model", "fake"),
                "content": [{"type": "text", "text": "transport-ok"}],
                "usage": {"input_tokens": 1, "output_tokens": 1},
            }
        )

    return Starlette(routes=[Route("/v1/messages", messages, methods=["POST"])])


class _UpstreamClient:
    def __init__(self, upstream: Starlette) -> None:
        self._upstream = upstream

    async def __aenter__(self):  # noqa: ANN204
        return self

    async def __aexit__(self, *args):  # noqa: ANN002
        return None

    async def request(self, method, url, content=None, headers=None):  # noqa: ANN001
        parsed = urlparse(url)
        transport = httpx.ASGITransport(app=self._upstream)
        async with httpx.AsyncClient(transport=transport, base_url="http://up") as c:
            return await c.request(method, parsed.path, content=content, headers=headers or {})


@pytest.mark.contract
@pytest.mark.asyncio
async def test_record_then_replay_transport(tmp_path: Path) -> None:
    """Record via RecordTransport, replay via ReplayTransport — no port."""
    cassette = tmp_path / "cass"
    upstream = _fake_upstream()
    scrubber = Scrubber(hmac_key=b"test-transport")

    record = RecordTransport(
        cassette_dir=cassette,
        upstream_base="http://upstream",
        scrubber=scrubber,
        http_client_factory=lambda: _UpstreamClient(upstream),
    )
    async with httpx.AsyncClient(transport=record, base_url="http://llmreplay") as client:
        resp = await client.post(
            "/v1/messages",
            json={"model": "m", "messages": [{"role": "user", "content": "hi"}]},
        )
    assert resp.status_code == 200
    assert resp.json()["content"][0]["text"] == "transport-ok"

    store = CassetteStore(cassette)
    assert len(store.load_manifest().transactions) == 1

    replay = ReplayTransport(cassette_dir=cassette, scrubber=scrubber)
    async with httpx.AsyncClient(transport=replay, base_url="http://llmreplay") as client:
        resp2 = await client.post(
            "/v1/messages",
            json={"model": "m", "messages": [{"role": "user", "content": "hi"}]},
        )
    assert resp2.status_code == 200
    assert resp2.json()["content"][0]["text"] == "transport-ok"


@pytest.mark.unit
def test_import_public_api() -> None:
    """All public symbols are importable from the top-level package."""
    from llmreplay import (
        CassetteStore,
        ProxyConfig,
        RecordTransport,
        ReplayTransport,
        Scrubber,
        create_app,
        load_llmreplay_yaml,
        match_key,
    )

    assert callable(match_key)
    assert callable(create_app)
    assert callable(load_llmreplay_yaml)
    for cls in (CassetteStore, ProxyConfig, RecordTransport, ReplayTransport, Scrubber):
        assert isinstance(cls, type)
