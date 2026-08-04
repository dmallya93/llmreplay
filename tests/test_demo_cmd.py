"""Tests for llmreplay demo (one-terminal start→end)."""

from __future__ import annotations

import os
import socket
import sys
import threading
import time
from pathlib import Path
from unittest.mock import patch

import pytest
import uvicorn
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route
from typer.testing import CliRunner

from llmreplay.cli.demo_cmd import run_demo
from llmreplay.cli.env_helpers import DEFAULT_LOCAL_HMAC, ensure_local_hmac
from llmreplay.cli.main import app
from llmreplay.cli.run_cmd import free_port
from llmreplay.proxy.config import ProxyConfig
from llmreplay.store.cassette import CassetteStore


@pytest.mark.contract
def test_run_demo_record_then_replay(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LLMREPLAY_HMAC_KEY", raising=False)
    cassette = tmp_path / "demo"
    code = run_demo(cassette_dir=cassette)
    assert code == 0
    store = CassetteStore(cassette)
    assert len(store.load_manifest().transactions) >= 1
    assert cassette.joinpath("cassette.json").is_file()


@pytest.mark.unit
def test_demo_cli_command(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLMREPLAY_HMAC_KEY", "demo-test-hmac")
    runner = CliRunner()
    result = runner.invoke(app, ["demo", "--cassette", str(tmp_path / "cass")])
    assert result.exit_code == 0, result.output
    assert "Done" in result.output or "offline replay matched" in result.output


@pytest.mark.unit
def test_run_record_requires_upstream_or_free() -> None:
    runner = CliRunner()
    result = runner.invoke(
        app,
        ["run", "--mode", "record", "--cassette", "/tmp/x", "--", "true"],
    )
    assert result.exit_code != 0
    assert "--upstream" in result.output or "Tip: llmreplay demo" in result.output


@pytest.mark.unit
def test_record_requires_upstream_or_free() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["record", "--cassette", "/tmp/x"])
    assert result.exit_code != 0
    assert "--upstream" in result.output


@pytest.mark.unit
def test_ensure_local_hmac_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LLMREPLAY_HMAC_KEY", raising=False)
    assert ensure_local_hmac() == DEFAULT_LOCAL_HMAC
    assert os.environ["LLMREPLAY_HMAC_KEY"] == DEFAULT_LOCAL_HMAC


@pytest.mark.unit
def test_ensure_local_hmac_preserves_existing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLMREPLAY_HMAC_KEY", "keep-me")
    assert ensure_local_hmac() == "keep-me"


@pytest.mark.unit
def test_run_free_defaults_ccr_upstream(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, ProxyConfig] = {}

    def fake_run(*, config: ProxyConfig, command: list[str], **_kwargs: object) -> int:
        captured["config"] = config
        return 0

    monkeypatch.setenv("LLMREPLAY_HMAC_KEY", "t")
    with patch("llmreplay.cli.main.run_with_proxy", side_effect=fake_run):
        result = CliRunner().invoke(
            app,
            ["run", "--mode", "record", "--free", "--cassette", "/tmp/x", "--", "true"],
        )
    assert result.exit_code == 0, result.output
    cfg = captured["config"]
    assert cfg.upstream_base == "http://127.0.0.1:3456"
    assert cfg.free_mode is True


@pytest.mark.contract
def test_cli_run_record_replay_against_stub(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """One-terminal run gateway: record then replay via CLI against a stub."""
    monkeypatch.setenv("LLMREPLAY_HMAC_KEY", "cli-run-hmac")
    stub_port = free_port()

    async def messages(_request: Request) -> JSONResponse:
        return JSONResponse(
            {
                "id": "msg",
                "type": "message",
                "role": "assistant",
                "model": "m",
                "content": [{"type": "text", "text": "cli-ok"}],
            }
        )

    stub = uvicorn.Server(
        uvicorn.Config(
            Starlette(routes=[Route("/v1/messages", messages, methods=["POST"])]),
            host="127.0.0.1",
            port=stub_port,
            log_level="error",
        )
    )
    threading.Thread(target=stub.run, daemon=True).start()
    for _ in range(50):
        with socket.socket() as s:
            if s.connect_ex(("127.0.0.1", stub_port)) == 0:
                break
        time.sleep(0.05)

    cassette = tmp_path / "cass"
    child = [
        sys.executable,
        "-c",
        "import json,os,urllib.request;"
        "b=os.environ['ANTHROPIC_BASE_URL'].rstrip('/');"
        "body=json.dumps({'model':'m','max_tokens':8,"
        "'messages':[{'role':'user','content':'hi'}]}).encode();"
        "req=urllib.request.Request(b+'/v1/messages',data=body,"
        "headers={'content-type':'application/json','x-api-key':'k'},method='POST');"
        "print(json.load(urllib.request.urlopen(req))['content'][0]['text'])",
    ]
    runner = CliRunner()
    rec = runner.invoke(
        app,
        [
            "run",
            "--mode",
            "record",
            "--cassette",
            str(cassette),
            "--upstream",
            f"http://127.0.0.1:{stub_port}",
            "--port",
            str(free_port()),
            "--",
            *child,
        ],
    )
    assert rec.exit_code == 0, rec.output
    assert len(CassetteStore(cassette).load_manifest().transactions) == 1

    rep = runner.invoke(
        app,
        [
            "run",
            "--mode",
            "replay",
            "--cassette",
            str(cassette),
            "--port",
            str(free_port()),
            "--",
            *child,
        ],
    )
    assert rep.exit_code == 0, rep.output
    stub.should_exit = True
