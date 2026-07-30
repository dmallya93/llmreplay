"""Cassette miss diagnosis (`llmreplay why`)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from llmreplay.config.profiles import load_llmreplay_yaml
from llmreplay.core.match import match_key, static_projection
from llmreplay.core.volatility import DEFAULT_IGNORE_KEYS
from llmreplay.store.cassette import CassetteStore


class WhyResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    matched: bool
    request_hash: str
    cassette_hashes: list[str] = Field(default_factory=list)
    closest_tx_id: str | None = None
    suggestion: str
    ignore_candidates: list[str] = Field(default_factory=list)


def _body_keys(event: Any) -> set[str]:
    if not isinstance(event, dict):
        return set()
    body = event.get("body")
    if isinstance(body, dict):
        return {str(k) for k in body}
    return set()


def _body_map(event: Any) -> dict[str, Any]:
    if not isinstance(event, dict):
        return {}
    body = event.get("body")
    return body if isinstance(body, dict) else {}


def diagnose_miss(
    *,
    cassette_dir: Path,
    request_event: dict[str, Any],
    config_path: Path | None = None,
    profile: str = "local",
    ignore_keys: frozenset[str] | None = None,
) -> WhyResult:
    """Compare a request event to cassette static hashes (SPEC teaching miss)."""
    if ignore_keys is None:
        yaml_cfg = load_llmreplay_yaml(config_path)
        ignore_keys = frozenset(yaml_cfg.merged_ignore(profile)) | DEFAULT_IGNORE_KEYS
    store = CassetteStore(cassette_dir)
    manifest = store.load_manifest()
    request_hash = match_key(request_event, ignore_keys=ignore_keys)
    hashes = [tx.static_hash for tx in manifest.transactions]
    if request_hash in hashes:
        tx = next(t for t in manifest.transactions if t.static_hash == request_hash)
        return WhyResult(
            matched=True,
            request_hash=request_hash,
            cassette_hashes=hashes,
            closest_tx_id=tx.id,
            suggestion="Exact static match — replay should hit this transaction.",
        )

    if not manifest.transactions:
        return WhyResult(
            matched=False,
            request_hash=request_hash,
            cassette_hashes=hashes,
            closest_tx_id=None,
            suggestion=(
                "Cassette empty or missing — run `llmreplay record` first "
                "(exit 2 CASSETTE_MISSING)."
            ),
        )

    closest = manifest.transactions[0]
    req_path = store.root / closest.request_ref
    ignore_candidates: list[str] = []
    if req_path.is_file():
        recorded = json.loads(req_path.read_text(encoding="utf-8"))
        live_proj = static_projection(request_event, ignore_keys=ignore_keys)
        rec_proj = static_projection(recorded, ignore_keys=ignore_keys)
        live_body = _body_map(live_proj)
        rec_body = _body_map(rec_proj)
        candidates = sorted(_body_keys(request_event) | _body_keys(recorded))
        differing = [k for k in candidates if live_body.get(k) != rec_body.get(k)]
        ignore_candidates = differing or candidates[:5]

    fields = " ".join(ignore_candidates[:3]) if ignore_candidates else "<field>"
    suggestion = (
        "Static mismatch (exit 1). If the field is non-behavioral noise, run:\n"
        f"  llmreplay mark-ignore {fields}\n"
        "Never auto-promote mismatches to ignore — confirm the field does not "
        "change the next agent action."
    )
    return WhyResult(
        matched=False,
        request_hash=request_hash,
        cassette_hashes=hashes,
        closest_tx_id=closest.id,
        suggestion=suggestion,
        ignore_candidates=ignore_candidates,
    )


def load_request_event(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("request JSON must be an object")
    return data
