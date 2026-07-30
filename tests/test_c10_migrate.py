"""C10 migrate + release tests."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import httpx
import pytest
from typer.testing import CliRunner

from llmreplay.cli.main import app
from llmreplay.core.exit_codes import ExitCode
from llmreplay.core.match import match_key
from llmreplay.migrate.engine import CURRENT_SCHEMA_VERSION, migrate_cassette, plan_migrate
from llmreplay.proxy.app import create_app
from llmreplay.scrub.engine import Scrubber
from llmreplay.store.cassette import CassetteStore

runner = CliRunner()
FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "legacy" / "v0"


@pytest.mark.unit
def test_plan_and_migrate_v0_to_v1(tmp_path: Path) -> None:
    dest = tmp_path / "cass"
    shutil.copytree(FIXTURES, dest)
    plan = plan_migrate(dest)
    assert plan.from_version == 0
    assert plan.to_version == CURRENT_SCHEMA_VERSION
    assert plan.steps == ["0→1"]

    dry = migrate_cassette(dest, dry_run=True)
    assert dry.changed is True
    raw = json.loads((dest / "cassette.json").read_text(encoding="utf-8"))
    assert "schema_version" not in raw

    result = migrate_cassette(dest, dry_run=False)
    assert result.changed is True
    assert result.backup
    manifest = CassetteStore(dest).load_manifest()
    assert manifest.schema_version == 1
    assert manifest.transactions[0].request_ref.startswith("requests/")
    assert manifest.transactions[0].static_hash != "0" * 64


@pytest.mark.contract
@pytest.mark.asyncio
async def test_migrated_legacy_cassette_replays(tmp_path: Path) -> None:
    dest = tmp_path / "cass"
    shutil.copytree(FIXTURES, dest)
    migrate_cassette(dest)
    scrubber = Scrubber()
    body = {
        "model": "legacy",
        "messages": [{"role": "user", "content": "hi"}],
    }
    app_asgi = create_app(mode="replay", cassette_dir=dest, scrubber=scrubber)
    transport = httpx.ASGITransport(app=app_asgi)
    async with httpx.AsyncClient(transport=transport, base_url="http://p") as client:
        resp = await client.post("/v1/messages", json=body)
        assert resp.status_code == 200
        assert resp.json()["content"][0]["text"] == "hello-legacy"


@pytest.mark.unit
def test_migrate_cli_dry_run(tmp_path: Path) -> None:
    dest = tmp_path / "cass"
    shutil.copytree(FIXTURES, dest)
    result = runner.invoke(
        app,
        ["migrate", "--cassette", str(dest), "--dry-run"],
    )
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert data["from_version"] == 0
    assert data["to_version"] == 1
    assert data["steps"] == ["0→1"]


@pytest.mark.unit
def test_migrate_already_current(tmp_path: Path) -> None:
    store = CassetteStore(tmp_path / "fresh")
    store.write_manifest(store.empty_manifest())
    result = migrate_cassette(tmp_path / "fresh")
    assert result.changed is False
    assert result.to_version == CURRENT_SCHEMA_VERSION


@pytest.mark.unit
def test_release_fixture_offline_replay_check(tmp_path: Path) -> None:
    """Minimal offline fixture used by release_smoke.sh."""
    cass = tmp_path / "release-fixture"
    store = CassetteStore(cass)
    event = {
        "method": "POST",
        "path": "/v1/messages",
        "headers": {},
        "body": {"model": "m", "messages": [{"role": "user", "content": "ping"}]},
    }
    store.append_transaction(
        request=event,
        response={"id": "1", "content": [{"type": "text", "text": "pong"}]},
        static_hash=match_key(event),
    )
    check = runner.invoke(app, ["replay", "--check", "--cassette", str(cass)])
    assert check.exit_code == int(ExitCode.SUCCESS)
    assert "offline replay ready" in check.stdout
