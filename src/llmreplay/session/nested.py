"""Nested / child cassette helpers (SPEC S10 nested sessions — alpha subset)."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from llmreplay.store.cassette import CassetteStore


class NestedSessionMeta(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session_id: str
    parent_session_id: str | None = None
    depth: int = Field(default=0, ge=0)
    child_cassette_hashes: list[str] = Field(default_factory=list)


def _manifest_digest(cassette_dir: Path) -> str:
    path = cassette_dir / "cassette.json"
    data = path.read_bytes()
    return hashlib.sha256(data).hexdigest()


def read_nested_meta(cassette_dir: Path) -> NestedSessionMeta | None:
    store = CassetteStore(cassette_dir)
    raw: Any = store.load_manifest().extensions.get("session")
    if not isinstance(raw, dict):
        return None
    return NestedSessionMeta.model_validate(raw)


def write_nested_meta(cassette_dir: Path, meta: NestedSessionMeta) -> None:
    store = CassetteStore(cassette_dir)
    manifest = store.load_manifest()
    extensions = dict(manifest.extensions)
    extensions["session"] = meta.model_dump(mode="json")
    store.write_manifest(manifest.model_copy(update={"extensions": extensions}))


def link_child_cassette(
    parent_dir: Path,
    child_dir: Path,
    *,
    parent_session_id: str | None = None,
) -> NestedSessionMeta:
    """Register a child cassette hash on the parent (depth-first replay contract)."""
    parent = CassetteStore(parent_dir)
    parent_manifest = parent.load_manifest()
    existing = parent_manifest.extensions.get("session")
    if isinstance(existing, dict):
        meta = NestedSessionMeta.model_validate(existing)
    else:
        meta = NestedSessionMeta(
            session_id=parent_session_id or parent_manifest.cassette_id,
            parent_session_id=None,
            depth=0,
        )

    child = CassetteStore(child_dir)
    child_manifest = child.load_manifest()
    child_meta = NestedSessionMeta(
        session_id=child_manifest.cassette_id,
        parent_session_id=meta.session_id,
        depth=meta.depth + 1,
        child_cassette_hashes=[],
    )
    # Write child first so the digest registered on the parent is final.
    write_nested_meta(child_dir, child_meta)
    digest = _manifest_digest(child_dir)
    if digest not in meta.child_cassette_hashes:
        meta.child_cassette_hashes = [*meta.child_cassette_hashes, digest]
    write_nested_meta(parent_dir, meta)
    return meta


def verify_children(parent_dir: Path, child_dirs: list[Path]) -> list[str]:
    """Return issue strings if child digests do not match parent registration."""
    meta = read_nested_meta(parent_dir)
    if meta is None:
        return []
    issues: list[str] = []
    live = sorted(_manifest_digest(p) for p in child_dirs if (p / "cassette.json").is_file())
    expected = sorted(meta.child_cassette_hashes)
    if expected and live != expected:
        issues.append(
            "child cassette digest mismatch — parent abort required "
            f"(expected={expected}, live={live})"
        )
    for digest in expected:
        if digest not in live:
            issues.append(f"missing child cassette digest {digest[:16]}…")
    return issues
