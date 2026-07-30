"""Record/replay multi-turn protocol sessions against the proxy."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from llmreplay.core.match import match_key
from llmreplay.parity.sessions import ProtocolSession
from llmreplay.proxy.app import create_app
from llmreplay.scrub.engine import Scrubber
from llmreplay.store.cassette import CassetteStore


async def record_session(
    session: ProtocolSession,
    cassette_dir: Path,
    *,
    scrubber: Scrubber | None = None,
) -> CassetteStore:
    """Record each turn via proxy against a scripted upstream."""
    scrubber = scrubber or Scrubber(hmac_key=b"parity")
    # Build upstream that returns responses in order keyed by path+hash of body model
    queue = list(session.turns)

    async def handler(request: Request) -> JSONResponse:
        if not queue:
            return JSONResponse({"error": "exhausted"}, status_code=500)
        turn = queue.pop(0)
        return JSONResponse(turn.response)

    upstream = Starlette(
        routes=[
            Route("/v1/messages", handler, methods=["POST"]),
            Route("/v1/responses", handler, methods=["POST"]),
            Route("/v1/chat/completions", handler, methods=["POST"]),
        ]
    )

    class _UpstreamClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):  # noqa: ANN002, ARG002
            return None

        async def request(self, method, url, content=None, headers=None):  # noqa: ANN001
            parsed = urlparse(url)
            transport = httpx.ASGITransport(app=upstream)
            async with httpx.AsyncClient(transport=transport, base_url="http://up") as client:
                return await client.request(
                    method, parsed.path, content=content, headers=headers or {}
                )

    store = CassetteStore(cassette_dir)
    record_app = create_app(
        mode="record",
        cassette_dir=cassette_dir,
        upstream_base="http://upstream",
        http_client_factory=_UpstreamClient,
        scrubber=scrubber,
    )
    transport = httpx.ASGITransport(app=record_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://proxy") as client:
        for turn in session.turns:
            path = turn.request["path"]
            body = turn.request.get("body")
            resp = await client.post(path, json=body)
            assert resp.status_code == 200, resp.text
    return store


async def replay_session(
    session: ProtocolSession,
    cassette_dir: Path,
    *,
    scrubber: Scrubber | None = None,
) -> list[dict[str, Any]]:
    scrubber = scrubber or Scrubber(hmac_key=b"parity")
    replay_app = create_app(
        mode="replay",
        cassette_dir=cassette_dir,
        scrubber=scrubber,
    )
    transport = httpx.ASGITransport(app=replay_app)
    out: list[dict[str, Any]] = []
    async with httpx.AsyncClient(transport=transport, base_url="http://proxy") as client:
        for turn in session.turns:
            path = turn.request["path"]
            body = turn.request.get("body")
            resp = await client.post(path, json=body)
            assert resp.status_code == 200, resp.text
            out.append(resp.json())
    return out


def assert_tool_ids_stable(session: ProtocolSession) -> None:
    """Ensure tool_use / tool_result ids align across turns (Claude)."""
    if session.agent != "claude":
        return
    ids: set[str] = set()
    for turn in session.turns:
        content = turn.response.get("content")
        if isinstance(content, list):
            for block in content:
                if isinstance(block, dict) and block.get("type") == "tool_use":
                    ids.add(str(block["id"]))
        body = turn.request.get("body") or {}
        messages = body.get("messages") or []
        for msg in messages:
            blocks = msg.get("content")
            if isinstance(blocks, list):
                for block in blocks:
                    if isinstance(block, dict) and block.get("type") == "tool_result":
                        assert str(block["tool_use_id"]) in ids


def assert_previous_response_id(session: ProtocolSession) -> None:
    if session.agent != "codex":
        return
    assert session.turns[1].request["body"]["previous_response_id"] == "resp_1"
    # Match key must include previous_response_id (static).
    key = match_key(session.turns[1].request)
    assert isinstance(key, str) and len(key) == 64
