"""Tests for llmreplay demo (one-terminal start→end)."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from typer.testing import CliRunner

from llmreplay.cli.demo_cmd import run_demo
from llmreplay.cli.main import app
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
    from llmreplay.cli.env_helpers import DEFAULT_LOCAL_HMAC, ensure_local_hmac

    monkeypatch.delenv("LLMREPLAY_HMAC_KEY", raising=False)
    assert ensure_local_hmac() == DEFAULT_LOCAL_HMAC
    assert os.environ["LLMREPLAY_HMAC_KEY"] == DEFAULT_LOCAL_HMAC
