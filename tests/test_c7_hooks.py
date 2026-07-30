"""C7 hooks tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from llmreplay.cli.main import app
from llmreplay.core.exit_codes import ExitCode
from llmreplay.hooks.digest import digest_script, verify_hook_digests
from llmreplay.hooks.install import install_claude_hooks
from llmreplay.hooks.models import HookDecision, HookRequest
from llmreplay.hooks.protocol import HookProtocolError, parse_hook_request
from llmreplay.hooks.recorder import record_decision, replay_decision, tool_stub_response
from llmreplay.hooks.runtime import run_hook_main
from llmreplay.store.cassette import CassetteStore

runner = CliRunner()


@pytest.mark.unit
def test_parse_hook_request_and_fail_oversized() -> None:
    req = parse_hook_request(
        json.dumps(
            {
                "version": 1,
                "id": "h1",
                "event": "PreToolUse",
                "tool_name": "Bash",
                "tool_input": {"command": "ls"},
            }
        )
    )
    assert req.tool_name == "Bash"
    with pytest.raises(HookProtocolError):
        parse_hook_request(b"{" + b"x" * (2 * 1024 * 1024))


@pytest.mark.unit
def test_record_then_replay_forces_deny(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    cassette = CassetteStore(tmp_path / "cass")
    monkeypatch.setenv("LLMREPLAY_CASSETTE", str(cassette.root))
    monkeypatch.setenv("LLMREPLAY_HOOK_FORCE", "deny")
    req = HookRequest(version=1, id="deny-1", event="PreToolUse", tool_name="Bash")
    record_decision(
        cassette,
        req,
        HookDecision(id="deny-1", decision="deny", reason="blocked"),
    )
    forced = replay_decision(cassette, req)
    assert forced.decision == "deny"
    stub = tool_stub_response("Bash")
    assert "stub" in stub["content"]


@pytest.mark.unit
def test_digest_mismatch_fails_strict(tmp_path: Path) -> None:
    hooks = tmp_path / "hooks"
    result = install_claude_hooks(hooks, mode="record")
    cassette = CassetteStore(tmp_path / "cass")
    cassette.set_hook_digests(result.digests)
    # Tamper script
    path = hooks / "pre_tool_use.py"
    path.write_text(path.read_text(encoding="utf-8") + "\n# tampered\n", encoding="utf-8")
    scripts = {
        "PreToolUse": path,
        "PostToolUse": hooks / "post_tool_use.py",
    }
    local = verify_hook_digests(cassette, scripts, profile="local")
    assert local.ok is True
    assert local.mismatches
    strict = verify_hook_digests(cassette, scripts, profile="strict")
    assert strict.ok is False


@pytest.mark.unit
def test_hooks_install_and_verify_cli(tmp_path: Path) -> None:
    hooks = tmp_path / "hooks"
    cassette = tmp_path / "cass"
    inst = runner.invoke(
        app,
        [
            "hooks",
            "install",
            "--dir",
            str(hooks),
            "--cassette",
            str(cassette),
            "--mode",
            "record",
        ],
    )
    assert inst.exit_code == 0
    assert (hooks / "pre_tool_use.py").is_file()
    digests = CassetteStore(cassette).load_manifest().hook_digests
    assert "PreToolUse" in digests
    assert digests["PreToolUse"] == digest_script(hooks / "pre_tool_use.py")

    ok = runner.invoke(
        app,
        [
            "hooks",
            "verify",
            "--dir",
            str(hooks),
            "--cassette",
            str(cassette),
            "--profile",
            "ci",
        ],
    )
    assert ok.exit_code == 0

    (hooks / "pre_tool_use.py").write_text("# broken\n", encoding="utf-8")
    bad = runner.invoke(
        app,
        [
            "hooks",
            "verify",
            "--dir",
            str(hooks),
            "--cassette",
            str(cassette),
            "--profile",
            "ci",
        ],
    )
    assert bad.exit_code == int(ExitCode.HOOK_OR_POLICY_DIVERGENCE)


@pytest.mark.unit
def test_run_hook_main_record_allow(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    cassette = tmp_path / "cass"
    monkeypatch.setenv("LLMREPLAY_CASSETTE", str(cassette))
    payload = json.dumps(
        {
            "version": 1,
            "id": "r1",
            "event": "PostToolUse",
            "tool_name": "Read",
        }
    ).encode()
    assert run_hook_main(mode="record", raw=payload) == 0
    out = capsys.readouterr().out
    decision = json.loads(out.strip())
    assert decision["decision"] == "allow"
    assert decision["id"] == "r1"
