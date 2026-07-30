"""Tweak a cassette transaction and invalidate the suffix."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict

from llmreplay.core.match import match_key
from llmreplay.store.cassette import CassetteStore


class TweakResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    seq: int
    field: str
    new_hash: str
    dropped_transactions: int


def _set_dotted(obj: dict[str, Any], dotted: str, value: Any) -> None:
    parts = dotted.split(".")
    cur: Any = obj
    for part in parts[:-1]:
        if not isinstance(cur, dict) or part not in cur:
            raise KeyError(f"path not found: {dotted}")
        cur = cur[part]
    if not isinstance(cur, dict):
        raise KeyError(f"path not found: {dotted}")
    cur[parts[-1]] = value


def tweak_transaction(
    cassette_dir: Path,
    *,
    seq: int,
    field: str,
    value: Any,
) -> TweakResult:
    """Patch request body field at ``seq`` and drop all later transactions."""
    store = CassetteStore(cassette_dir)
    manifest = store.load_manifest()
    if seq < 0 or seq >= len(manifest.transactions):
        raise IndexError(f"seq {seq} out of range (n={len(manifest.transactions)})")
    tx = manifest.transactions[seq]
    req_path = store.root / tx.request_ref
    request = json.loads(req_path.read_text(encoding="utf-8"))
    # Prefer body.<field> unless field already rooted
    target = field if field.startswith("body.") or "." in field else f"body.{field}"
    if target.startswith("body.") and "body" not in request:
        request["body"] = {}
    _set_dotted(request, target, value)
    new_hash = match_key(request)
    req_path.write_text(json.dumps(request, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    dropped = len(manifest.transactions) - seq - 1
    kept = list(manifest.transactions[: seq + 1])
    kept[seq] = kept[seq].model_copy(update={"static_hash": new_hash})
    # Remove blob files for dropped txs
    for old in manifest.transactions[seq + 1 :]:
        for ref in (old.request_ref, old.response_ref):
            path = store.root / ref
            if path.is_file():
                path.unlink()
    manifest.transactions = kept
    store.write_manifest(manifest)
    return TweakResult(
        seq=seq,
        field=field,
        new_hash=new_hash,
        dropped_transactions=dropped,
    )
