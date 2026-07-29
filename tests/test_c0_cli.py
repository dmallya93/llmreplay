"""C0 unit tests — exit codes and CLI smoke."""

from __future__ import annotations

import json

import pytest
from typer.testing import CliRunner

from llmreplay import __version__
from llmreplay.cli.main import app
from llmreplay.core.exit_codes import EXIT_CODE_HELP, ExitCode

runner = CliRunner()


@pytest.mark.unit
def test_exit_codes_are_stable() -> None:
    assert int(ExitCode.SUCCESS) == 0
    assert int(ExitCode.STATIC_MISMATCH) == 1
    assert int(ExitCode.ROUTE_OR_PROTOCOL) == 9
    assert len(ExitCode) == len(EXIT_CODE_HELP)


@pytest.mark.unit
def test_version_command() -> None:
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert __version__ in result.stdout


@pytest.mark.unit
def test_doctor_json() -> None:
    result = runner.invoke(app, ["doctor", "--json"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["llmreplay_version"] == __version__
    assert any(c["id"] == "cli_installed" and c["ok"] for c in payload["checks"])


@pytest.mark.unit
def test_exit_codes_command() -> None:
    result = runner.invoke(app, ["exit-codes"])
    assert result.exit_code == 0
    assert "STATIC_MISMATCH" in result.stdout
