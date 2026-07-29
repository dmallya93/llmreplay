"""C4 CLI: record/replay harness, why, doctor, validate, bundle."""

from __future__ import annotations

import json
import zipfile
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx
import pytest
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route
from typer.testing import CliRunner

from llmreplay.cli.docs_gen import check_cli_reference, write_cli_reference
from llmreplay.cli.main import app
from llmreplay.core.exit_codes import ExitCode
from llmreplay.core.match import match_key
from llmreplay.diagnose.why import diagnose_miss
from llmreplay.proxy.app import create_app
from llmreplay.proxy.normalize import normalize_request_event
from llmreplay.scrub.engine import Scrubber
from llmreplay.store.cassette import CassetteStore

runner = CliRunner()


def _upstream_factory(upstream: Starlette) -> Any:
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

    return _UpstreamClient


@pytest.mark.contract
@pytest.mark.asyncio
async def test_fake_agent_record_then_replay_offline(tmp_path: Path) -> None:
    """Harness: fake agent → record → replay offline (C4 acceptance)."""

    async def messages(_request: Request) -> JSONResponse:
        return JSONResponse(
            {
                "id": "msg_1",
                "content": [{"type": "text", "text": "pong"}],
                "usage": {"input_tokens": 1},
            }
        )

    upstream = Starlette(routes=[Route("/v1/messages", messages, methods=["POST"])])
    cassette = tmp_path / "cass"
    scrubber = Scrubber(hmac_key=b"harness-key")
    record_app = create_app(
        mode="record",
        cassette_dir=cassette,
        upstream_base="http://upstream",
        http_client_factory=_upstream_factory(upstream),
        scrubber=scrubber,
    )
    payload = {"model": "m", "messages": [{"role": "user", "content": "ping"}]}
    transport = httpx.ASGITransport(app=record_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://proxy") as client:
        recorded = await client.post("/v1/messages", json=payload)
        assert recorded.status_code == 200
        assert recorded.json()["content"][0]["text"] == "pong"

    assert CassetteStore(cassette).load_manifest().transactions

    replay_app = create_app(
        mode="replay",
        cassette_dir=cassette,
        scrubber=scrubber,
    )
    transport = httpx.ASGITransport(app=replay_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://proxy") as client:
        replayed = await client.post("/v1/messages", json=payload)
        assert replayed.status_code == 200
        assert replayed.json()["content"][0]["text"] == "pong"

        # Static mismatch → 409 miss (CLI why maps to exit 1).
        miss = await client.post(
            "/v1/messages",
            json={"model": "m", "messages": [{"role": "user", "content": "CHANGED"}]},
        )
        assert miss.status_code == 409
        assert miss.json()["error"]["type"] == "llmreplay_miss"


@pytest.mark.unit
def test_why_static_mismatch_suggests_mark_ignore(tmp_path: Path) -> None:
    cassette = tmp_path / "cass"
    store = CassetteStore(cassette)
    event = normalize_request_event(
        method="POST",
        path="/v1/messages",
        headers={},
        body={"model": "m", "messages": [{"role": "user", "content": "a"}]},
    )
    scrubber = Scrubber(hmac_key=b"k")
    scrubbed = scrubber.scrub_event(event)
    store.append_transaction(
        request=scrubbed,
        response={"ok": True},
        static_hash=match_key(scrubbed),
    )
    live = normalize_request_event(
        method="POST",
        path="/v1/messages",
        headers={},
        body={"model": "m", "messages": [{"role": "user", "content": "b"}]},
    )
    result = diagnose_miss(cassette_dir=cassette, request_event=live)
    assert result.matched is False
    assert "mark-ignore" in result.suggestion

    req_path = tmp_path / "req.json"
    req_path.write_text(json.dumps(live), encoding="utf-8")
    cli = runner.invoke(
        app,
        ["why", "--cassette", str(cassette), "--request", str(req_path)],
    )
    assert cli.exit_code == int(ExitCode.STATIC_MISMATCH)
    assert "mark-ignore" in cli.stdout


@pytest.mark.unit
def test_validate_and_bundle_scrubbed(tmp_path: Path) -> None:
    cassette = tmp_path / "cass"
    store = CassetteStore(cassette)
    secret = "sk-abcdefghijklmnopqrstuvwxyz012345"
    event = {
        "method": "POST",
        "path": "/v1/messages",
        "headers": {},
        "body": {"model": "x", "prompt": secret},
    }
    scrubber = Scrubber(hmac_key=b"bundle-key")
    store.append_transaction(
        request=scrubber.scrub_event(event),
        response={"id": "1", "note": secret},
        static_hash=match_key(scrubber.scrub_event(event)),
    )
    # Intentionally put a plaintext secret in a response blob to prove bundle scrub.
    resp_files = list((cassette / "responses").glob("*.json"))
    assert resp_files
    resp_files[0].write_text(
        json.dumps({"id": "1", "leak": secret}, indent=2) + "\n",
        encoding="utf-8",
    )
    v = runner.invoke(app, ["validate", "--cassette", str(cassette)])
    assert v.exit_code == int(ExitCode.SECRET_SCRUB_OR_LIMIT)
    out = tmp_path / "b.zip"
    b = runner.invoke(
        app,
        ["bundle", "--cassette", str(cassette), "--output", str(out)],
    )
    assert b.exit_code == 0
    assert out.is_file()
    with zipfile.ZipFile(out) as zf:
        names = zf.namelist()
        assert "cassette.json" in names
        assert "validate.json" in names
        assert "README.txt" in names
        for name in names:
            if name.endswith(".json"):
                assert secret not in zf.read(name).decode("utf-8")


@pytest.mark.unit
def test_validate_ok_clean_cassette(tmp_path: Path) -> None:
    cassette = tmp_path / "cass"
    store = CassetteStore(cassette)
    event = {"method": "POST", "path": "/v1/messages", "headers": {}, "body": {"model": "x"}}
    store.append_transaction(
        request=event,
        response={"id": "1"},
        static_hash=match_key(event),
    )
    v = runner.invoke(app, ["validate", "--cassette", str(cassette)])
    assert v.exit_code == 0
    check = runner.invoke(app, ["replay", "--check", "--cassette", str(cassette)])
    assert check.exit_code == 0
    assert "offline replay ready" in check.stdout

    cfg = tmp_path / "llmreplay.yaml"
    r1 = runner.invoke(app, ["mark-ignore", "usage", "latency_ms", "--config", str(cfg)])
    assert r1.exit_code == 0
    text = cfg.read_text(encoding="utf-8")
    assert "usage" in text
    r2 = runner.invoke(app, ["mark-live", "Bash", "--config", str(cfg)])
    assert r2.exit_code == 0
    assert "Bash" in cfg.read_text(encoding="utf-8")


@pytest.mark.unit
def test_doctor_json_has_proxy_port_check() -> None:
    result = runner.invoke(app, ["doctor", "--json"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    ids = {c["id"] for c in payload["checks"]}
    assert "proxy_port" in ids
    assert "cassette_writable" in ids
    assert payload["ok"] is True


@pytest.mark.unit
def test_docs_gen_and_check(tmp_path: Path) -> None:
    out = tmp_path / "cli.md"
    write_cli_reference(out, app)
    assert out.is_file()
    assert "llmreplay why" in out.read_text(encoding="utf-8")
    assert check_cli_reference(out, app) is True
    out.write_text("stale\n", encoding="utf-8")
    assert check_cli_reference(out, app) is False
    cli = runner.invoke(app, ["docs", "gen", "--output", str(out)])
    assert cli.exit_code == 0
    check = runner.invoke(app, ["docs", "gen", "--check", "--output", str(out)])
    assert check.exit_code == 0


@pytest.mark.unit
def test_replay_check_empty_cassette(tmp_path: Path) -> None:
    cassette = tmp_path / "empty"
    cassette.mkdir()
    result = runner.invoke(app, ["replay", "--check", "--cassette", str(cassette)])
    # Missing manifest → validate fails schema/repair
    assert result.exit_code in {
        int(ExitCode.SCHEMA_OR_REPAIR_REQUIRED),
        int(ExitCode.CASSETTE_MISSING),
    }
