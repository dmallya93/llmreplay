"""Extra coverage for C10 critical modules (coverage gate)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from llmreplay.migrate.engine import migrate_cassette, plan_migrate
from llmreplay.scrub.engine import Scrubber, residual_hits_in_payload, resolve_hmac_key


@pytest.mark.unit
def test_resolve_hmac_key_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLMREPLAY_HMAC_KEY", "from-env")
    assert resolve_hmac_key() == b"from-env"
    assert resolve_hmac_key(b"explicit") == b"explicit"


@pytest.mark.unit
def test_scrub_paths_query_and_response() -> None:
    scrubber = Scrubber(hmac_key=b"cov", extra_scrub_paths=["body.token"])
    event = scrubber.scrub_event(
        {
            "path": "/v1/messages?q=sk-abcdefghijklmnopqrstuvwxyz0123",
            "headers": {"x-custom": "ok"},
            "query": {"n": 1},
            "body": {"token": "plaintext-secret", "keep": "yes"},
        }
    )
    assert "sk-abcdefghijklmnopqrstuvwxyz0123" not in event["path"]
    assert event["body"]["token"].startswith("«REDACTED:hmac:")
    assert event["body"]["keep"] == "yes"
    resp = scrubber.scrub_response({"api_key": "abc", "ok": True})
    assert resp["api_key"].startswith("«REDACTED:hmac:")
    assert residual_hits_in_payload({"x": "clean"}) == []
    listed = Scrubber(hmac_key=b"cov", extra_scrub_paths=["body.msgs.0"])
    out = listed.scrub_event({"body": {"msgs": ["sk-abcdefghijklmnopqrstuvwxyz0123"]}})
    assert "sk-" not in json.dumps(out)


@pytest.mark.unit
def test_migrate_errors(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        plan_migrate(tmp_path / "missing")
    bad = tmp_path / "newer"
    bad.mkdir()
    (bad / "cassette.json").write_text(
        json.dumps({"schema_version": 99, "cassette_id": "x", "transactions": []}),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="newer"):
        plan_migrate(bad)
    cur = tmp_path / "cur"
    cur.mkdir()
    (cur / "cassette.json").write_text(
        json.dumps({"schema_version": 1, "cassette_id": "x", "transactions": []}),
        encoding="utf-8",
    )
    result = migrate_cassette(cur)
    assert result.changed is False
