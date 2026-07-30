"""C8 fork/tweak/sticky/template tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from llmreplay.cli.main import app
from llmreplay.config.profiles import LLMReplayFileConfig
from llmreplay.core.exit_codes import ExitCode
from llmreplay.core.match import match_key
from llmreplay.lineage.fork import fork_cassette, load_lineage
from llmreplay.lineage.sticky import maybe_sticky_write, sticky_writeback_allowed
from llmreplay.lineage.templates import apply_materializer, list_materializers
from llmreplay.lineage.tweak import tweak_transaction
from llmreplay.store.cassette import CassetteStore

runner = CliRunner()


def _seed_cassette(root: Path, n: int = 3) -> CassetteStore:
    store = CassetteStore(root)
    for i in range(n):
        event = {
            "method": "POST",
            "path": "/v1/messages",
            "headers": {},
            "body": {"model": f"m{i}", "n": i},
        }
        store.append_transaction(
            request=event,
            response={"id": f"r{i}"},
            static_hash=match_key(event),
        )
    return store


@pytest.mark.unit
def test_fork_at_seq_shares_prefix(tmp_path: Path) -> None:
    src = tmp_path / "src"
    _seed_cassette(src, 3)
    dest = tmp_path / "fork"
    run_id, manifest = fork_cassette(src, dest, seq=2)
    assert run_id
    assert len(manifest.transactions) == 2
    assert manifest.extensions["fork_seq"] == 2
    assert manifest.extensions["parent_run_id"]
    lineage = load_lineage(dest)
    assert len(lineage.nodes) == 2
    assert lineage.nodes[1].parent_run_id == lineage.nodes[0].run_id


@pytest.mark.unit
def test_tweak_invalidates_suffix(tmp_path: Path) -> None:
    root = tmp_path / "cass"
    _seed_cassette(root, 3)
    result = tweak_transaction(root, seq=0, field="model", value="tweaked")
    assert result.dropped_transactions == 2
    store = CassetteStore(root)
    assert len(store.load_manifest().transactions) == 1
    req = json.loads((root / store.load_manifest().transactions[0].request_ref).read_text())
    assert req["body"]["model"] == "tweaked"


@pytest.mark.unit
def test_sticky_forbidden_ci_strict() -> None:
    assert sticky_writeback_allowed("ci") is False
    assert sticky_writeback_allowed("strict") is False
    cfg = LLMReplayFileConfig()
    assert cfg.resolved_profile("debug_sticky").sticky_writeback is True


@pytest.mark.unit
def test_sticky_write_debug_profile(tmp_path: Path) -> None:
    root = tmp_path / "cass"
    _seed_cassette(root, 1)
    denied = maybe_sticky_write(root, profile="ci", seq=0, field="model", value="x")
    assert denied.applied is False
    ok = maybe_sticky_write(root, profile="debug_sticky", seq=0, field="model", value="stuck")
    assert ok.applied is True


@pytest.mark.unit
def test_unknown_materializer_rejected() -> None:
    assert "uuid.v4" in list_materializers()
    with pytest.raises(KeyError, match="unknown materializer"):
        apply_materializer("not_a_real_one", "x")
    out = apply_materializer("path_rebase", "/old/a", {"from": "/old", "to": "/new"})
    assert out.output == "/new/a"


@pytest.mark.unit
def test_fork_tweak_template_cli(tmp_path: Path) -> None:
    src = tmp_path / "src"
    _seed_cassette(src, 2)
    dest = tmp_path / "dst"
    f = runner.invoke(
        app,
        ["fork", "--cassette", str(src), "--dest", str(dest), "--seq", "1"],
    )
    assert f.exit_code == 0
    t = runner.invoke(
        app,
        [
            "tweak",
            "--cassette",
            str(dest),
            "--seq",
            "0",
            "--field",
            "model",
            "--value",
            "x",
        ],
    )
    assert t.exit_code == 0
    bad = runner.invoke(app, ["template", "nope"])
    assert bad.exit_code == int(ExitCode.ROUTE_OR_PROTOCOL)
    listed = runner.invoke(app, ["template", "list"])
    assert listed.exit_code == 0
    sticky_ci = runner.invoke(
        app,
        ["sticky", "--cassette", str(dest), "--profile", "ci", "--value", "y"],
    )
    assert sticky_ci.exit_code == int(ExitCode.HOOK_OR_POLICY_DIVERGENCE)
