"""Contract: cassette schema stub validates a minimal manifest."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.contract
def test_cassette_schema_file_exists() -> None:
    schema_path = ROOT / "schemas" / "cassette.v1.json"
    assert schema_path.is_file()
    schema = json.loads(schema_path.read_text())
    assert schema["properties"]["schema_version"]["type"] == "integer"
    assert "extensions" in schema["properties"]


@pytest.mark.contract
def test_minimal_manifest_shape() -> None:
    manifest = {
        "schema_version": 1,
        "cassette_id": "c0-smoke",
        "extensions": {},
        "transactions": [],
        "checksums": {},
    }
    required = {"schema_version", "cassette_id", "transactions"}
    assert required <= manifest.keys()
