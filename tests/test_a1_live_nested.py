"""Alpha: mark-live pass-through + nested session digests."""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from llmreplay.config.profiles import LLMReplayFileConfig, load_llmreplay_yaml
from llmreplay.hooks.models import HookDecision, HookRequest
from llmreplay.hooks.recorder import (
    decisions_path,
    load_decisions,
    record_decision,
    replay_decision,
    tool_stub_response,
)
from llmreplay.hooks.runtime import run_hook_main
from llmreplay.proxy.app import create_app
from llmreplay.proxy.config import ProxyConfig
from llmreplay.proxy.sse import (
    _openai_text,
    parse_openai_sse,
    strip_stream_flag,
    synthesize_sse,
)
from llmreplay.session.nested import link_child_cassette, read_nested_meta, verify_children
from llmreplay.store.cassette import CassetteStore


@pytest.mark.unit
def test_live_tools_from_yaml(tmp_path: Path) -> None:
    cfg_path = tmp_path / "llmreplay.yaml"
    cfg_path.write_text(
        "tools:\n  Bash:\n    class: live\n  __llm__:\n    class: live\n",
        encoding="utf-8",
    )
    cfg = load_llmreplay_yaml(cfg_path)
    assert cfg.is_live_tool("Bash")
    assert cfg.is_llm_live()
    assert not cfg.is_live_tool("Edit")


@pytest.mark.unit
def test_mark_live_bypasses_cassette_deny(tmp_path: Path) -> None:
    cassette = CassetteStore(tmp_path / "cass")
    req = HookRequest(version=1, id="h1", event="PreToolUse", tool_name="Bash")
    record_decision(
        cassette,
        req,
        HookDecision(id="h1", decision="deny", reason="recorded deny"),
    )
    forced = replay_decision(cassette, req)
    assert forced.decision == "deny"
    live = replay_decision(cassette, req, live_tools=frozenset({"Bash"}))
    assert live.decision == "allow"
    assert live.reason == "mark-live:Bash"


@pytest.mark.unit
def test_hook_runtime_reads_live_from_config(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    cassette = CassetteStore(tmp_path / "cass")
    cfg = tmp_path / "llmreplay.yaml"
    cfg.write_text("tools:\n  Bash:\n    class: live\n", encoding="utf-8")
    req = HookRequest(version=1, id="x", event="PreToolUse", tool_name="Bash")
    record_decision(
        cassette,
        req,
        HookDecision(id="x", decision="deny", reason="nope"),
    )
    monkeypatch.setenv("LLMREPLAY_CASSETTE", str(cassette.root))
    monkeypatch.setenv("LLMREPLAY_CONFIG", str(cfg))
    code = run_hook_main(
        mode="replay",
        raw=req.model_dump_json().encode("utf-8"),
    )
    assert code == 0
    out = json.loads(capsys.readouterr().out.strip())
    assert out["decision"] == "allow"


@pytest.mark.contract
@pytest.mark.asyncio
async def test_llm_live_replays_via_upstream(tmp_path: Path) -> None:
    upstream_calls = {"n": 0}

    async def messages(request: Request) -> JSONResponse:
        upstream_calls["n"] += 1
        body = await request.json()
        return JSONResponse(
            {
                "id": "live",
                "content": [{"type": "text", "text": f"live:{body.get('model')}"}],
            }
        )

    upstream = Starlette(routes=[Route("/v1/messages", messages, methods=["POST"])])

    class _Client:
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

    cfg_path = tmp_path / "llmreplay.yaml"
    cfg_path.write_text("tools:\n  __llm__:\n    class: live\n", encoding="utf-8")
    cassette = tmp_path / "cass"
    CassetteStore(cassette).write_manifest(CassetteStore(cassette).empty_manifest())

    app = create_app(
        config=ProxyConfig(
            mode="replay",
            cassette_dir=cassette,
            upstream_base="http://upstream",
            config_path=cfg_path,
        ),
        http_client_factory=_Client,
    )
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://proxy") as client:
        resp = await client.post(
            "/v1/messages",
            json={"model": "m", "messages": [{"role": "user", "content": "hi"}]},
        )
        assert resp.status_code == 200
        assert resp.json()["content"][0]["text"] == "live:m"
        assert upstream_calls["n"] == 1
        # Live path must not append cassette transactions.
        assert CassetteStore(cassette).load_manifest().transactions == []


@pytest.mark.contract
@pytest.mark.asyncio
async def test_llm_live_without_upstream_errors(tmp_path: Path) -> None:
    cfg = LLMReplayFileConfig(tools={"__llm__": {"class": "live"}})
    cassette = tmp_path / "cass"
    CassetteStore(cassette).write_manifest(CassetteStore(cassette).empty_manifest())
    app = create_app(
        mode="replay",
        cassette_dir=cassette,
        file_config=cfg,
    )
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://proxy") as client:
        resp = await client.post("/v1/messages", json={"model": "m"})
        assert resp.status_code == 503
        assert resp.json()["error"]["type"] == "llmreplay_live"


@pytest.mark.contract
@pytest.mark.asyncio
async def test_default_replay_still_serves_cassette(tmp_path: Path) -> None:
    """Unmarked replay must remain hermetic (no accidental live forward)."""
    from llmreplay.core.match import match_key

    cassette = tmp_path / "cass"
    store = CassetteStore(cassette)
    event = {
        "method": "POST",
        "path": "/v1/messages",
        "headers": {},
        "body": {"model": "m", "messages": [{"role": "user", "content": "hi"}]},
    }
    store.append_transaction(
        request=event,
        response={"id": "1", "content": [{"type": "text", "text": "from-cassette"}]},
        static_hash=match_key(event),
    )
    app = create_app(mode="replay", cassette_dir=cassette)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://proxy") as client:
        resp = await client.post(
            "/v1/messages",
            json={"model": "m", "messages": [{"role": "user", "content": "hi"}]},
        )
        assert resp.status_code == 200
        assert resp.json()["content"][0]["text"] == "from-cassette"


@pytest.mark.unit
def test_nested_session_link_and_verify(tmp_path: Path) -> None:
    parent = tmp_path / "parent"
    child = tmp_path / "child"
    for path in (parent, child):
        store = CassetteStore(path)
        store.write_manifest(store.empty_manifest())
    assert read_nested_meta(parent) is None
    assert verify_children(parent, [child]) == []
    meta = link_child_cassette(parent, child)
    assert meta.child_cassette_hashes
    # Relink preserves existing session meta and does not duplicate digests.
    again = link_child_cassette(parent, child)
    assert again.child_cassette_hashes == meta.child_cassette_hashes
    child_meta = read_nested_meta(child)
    assert child_meta is not None
    assert child_meta.parent_session_id == meta.session_id
    assert child_meta.depth == 1
    assert verify_children(parent, [child]) == []
    # Tamper child → digest mismatch
    CassetteStore(child).append_transaction(
        request={"method": "POST", "path": "/v1/messages", "headers": {}, "body": {}},
        response={"ok": True},
        static_hash="a" * 64,
    )
    issues = verify_children(parent, [child])
    assert issues


@pytest.mark.unit
def test_replay_decision_tool_match_and_empty_load(tmp_path: Path) -> None:
    cassette = CassetteStore(tmp_path / "cass")
    assert load_decisions(cassette) == []
    record_decision(
        cassette,
        HookRequest(version=1, id="old", event="PreToolUse", tool_name="Edit"),
        HookDecision(id="old", decision="allow", reason=""),
    )
    # Blank line in decisions file is skipped.
    path = decisions_path(cassette)
    path.write_text(path.read_text(encoding="utf-8") + "\n\n", encoding="utf-8")
    matched = replay_decision(
        cassette,
        HookRequest(version=1, id="new-id", event="PreToolUse", tool_name="Edit"),
    )
    assert matched.decision == "allow"
    assert "tool match" in (matched.reason or "")
    assert tool_stub_response(None)["content"].endswith("unknown not executed on replay")


@pytest.mark.unit
def test_sse_edge_paths() -> None:
    assert strip_stream_flag("x") == "x"
    generic = synthesize_sse("/v1/responses", {"id": "r", "output": []})
    assert b"[DONE]" in generic
    assert _openai_text({"choices": [{"message": {"role": "assistant"}}]}).startswith("{")
    assert parse_openai_sse("data: not-json\n\ndata: [DONE]\n\n") == {
        "raw_text": "data: not-json\n\ndata: [DONE]\n\n"
    }
    assert parse_openai_sse('data: {"id":"only"}\n\n')["id"] == "only"


@pytest.mark.unit
def test_proxy_config_free_default_upstream(tmp_path: Path) -> None:
    cfg = ProxyConfig(mode="record", cassette_dir=tmp_path, free_mode=True)
    assert cfg.upstream_base == "http://127.0.0.1:3456"
