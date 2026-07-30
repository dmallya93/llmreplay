"""Cassette schema migrations (SPEC S16 / C10)."""

from __future__ import annotations

import json
import shutil
from collections.abc import Callable
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from llmreplay.core.match import match_key
from llmreplay.scrub.engine import Scrubber
from llmreplay.store.cassette import CassetteStore
from llmreplay.store.models import CassetteManifest

CURRENT_SCHEMA_VERSION = 1

MigrationFn = Callable[[dict[str, Any], Path], dict[str, Any]]


class MigratePlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    from_version: int
    to_version: int
    steps: list[str] = Field(default_factory=list)
    dry_run: bool = False


class MigrateResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cassette_dir: str
    from_version: int
    to_version: int
    changed: bool
    backup: str | None = None
    steps: list[str] = Field(default_factory=list)


def detect_schema_version(raw: dict[str, Any]) -> int:
    ver = raw.get("schema_version")
    if ver is None:
        return 0
    return int(ver)


def ensure_transaction_blobs(cassette_dir: Path, data: dict[str, Any]) -> None:
    """Create empty JSON blobs for refs that are missing (legacy imports)."""
    root = Path(cassette_dir)
    for tx in data.get("transactions") or []:
        for key in ("request_ref", "response_ref"):
            ref = tx.get(key)
            if not ref:
                continue
            path = root / ref
            path.parent.mkdir(parents=True, exist_ok=True)
            if not path.is_file():
                path.write_text("{}\n", encoding="utf-8")


def _migrate_0_to_1(raw: dict[str, Any], root: Path) -> dict[str, Any]:
    """Normalize pre-v1 / incomplete manifests to schema_version 1."""
    out = dict(raw)
    out["schema_version"] = 1
    if not out.get("cassette_id"):
        out["cassette_id"] = "migrated-" + (root.name or "cassette")
    out.setdefault("extensions", {})
    out.setdefault("checksums", {})
    out.setdefault("tool_id_map", {})
    out.setdefault("hook_digests", {})
    out.setdefault("test_stack", {})
    txs: list[dict[str, Any]] = []
    scrubber = Scrubber()
    for i, tx in enumerate(out.get("transactions") or []):
        item = dict(tx)
        item.setdefault("id", f"tx{i}")
        if "request_ref" not in item and "request" in item:
            item["request_ref"] = str(item.pop("request"))
        if "response_ref" not in item and "response" in item:
            item["response_ref"] = str(item.pop("response"))
        item.setdefault("request_ref", f"requests/{item['id']}.json")
        item.setdefault("response_ref", f"responses/{item['id']}.json")
        req_path = root / item["request_ref"]
        if req_path.is_file():
            try:
                request = json.loads(req_path.read_text(encoding="utf-8"))
                item["static_hash"] = match_key(scrubber.scrub_event(request))
            except (json.JSONDecodeError, OSError, TypeError, ValueError):
                item.setdefault("static_hash", "0" * 64)
        elif "static_hash" not in item or len(str(item.get("static_hash", ""))) != 64:
            item["static_hash"] = "0" * 64
        txs.append(item)
    out["transactions"] = txs
    ensure_transaction_blobs(root, out)
    return out


MIGRATIONS: dict[int, MigrationFn] = {
    0: _migrate_0_to_1,
}


def plan_migrate(
    cassette_dir: Path,
    *,
    target: int = CURRENT_SCHEMA_VERSION,
) -> MigratePlan:
    path = cassette_dir / "cassette.json"
    if not path.is_file():
        raise FileNotFoundError(f"missing cassette.json in {cassette_dir}")
    raw = json.loads(path.read_text(encoding="utf-8"))
    from_ver = detect_schema_version(raw)
    if from_ver > target:
        raise ValueError(f"cassette schema {from_ver} newer than supported {target}")
    steps: list[str] = []
    ver = from_ver
    while ver < target:
        if ver not in MIGRATIONS:
            raise ValueError(f"no migration path from schema {ver}")
        steps.append(f"{ver}→{ver + 1}")
        ver += 1
    return MigratePlan(from_version=from_ver, to_version=target, steps=steps, dry_run=True)


def migrate_cassette(
    cassette_dir: Path,
    *,
    target: int = CURRENT_SCHEMA_VERSION,
    dry_run: bool = False,
) -> MigrateResult:
    cassette_dir = Path(cassette_dir)
    plan = plan_migrate(cassette_dir, target=target)
    path = cassette_dir / "cassette.json"
    raw = json.loads(path.read_text(encoding="utf-8"))
    if plan.from_version == target:
        return MigrateResult(
            cassette_dir=str(cassette_dir),
            from_version=plan.from_version,
            to_version=target,
            changed=False,
            steps=[],
        )
    ver = plan.from_version
    data = raw
    applied: list[str] = []
    while ver < target:
        data = MIGRATIONS[ver](data, cassette_dir)
        applied.append(f"{ver}→{ver + 1}")
        ver += 1
    CassetteManifest.model_validate(data)
    if dry_run:
        return MigrateResult(
            cassette_dir=str(cassette_dir),
            from_version=plan.from_version,
            to_version=target,
            changed=True,
            steps=applied,
        )
    backup = cassette_dir / f"cassette.json.bak.pre-migrate-v{plan.from_version}"
    shutil.copy2(path, backup)
    store = CassetteStore(cassette_dir)
    store.write_manifest(CassetteManifest.model_validate(data))
    return MigrateResult(
        cassette_dir=str(cassette_dir),
        from_version=plan.from_version,
        to_version=target,
        changed=True,
        backup=str(backup),
        steps=applied,
    )
