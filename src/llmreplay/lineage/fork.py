"""Cassette lineage: fork DAG + run ids."""

from __future__ import annotations

import shutil
import uuid
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from llmreplay.store.cassette import CassetteStore
from llmreplay.store.models import CassetteManifest


class LineageNode(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    parent_run_id: str | None = None
    fork_seq: int | None = None
    cassette_dir: str


class LineageGraph(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nodes: list[LineageNode] = Field(default_factory=list)


def _copy_blob(src_root: Path, dst_root: Path, ref: str) -> None:
    src = src_root / ref
    dst = dst_root / ref
    dst.parent.mkdir(parents=True, exist_ok=True)
    if src.is_file():
        shutil.copy2(src, dst)


def fork_cassette(
    source: Path,
    dest: Path,
    *,
    seq: int,
    run_id: str | None = None,
) -> tuple[str, CassetteManifest]:
    """Fork at transaction index ``seq`` (0-based). Prefix [0..seq) shared; new run_id.

    Transactions at and after ``seq`` are dropped (invalidate suffix).
    """
    if seq < 0:
        raise ValueError("seq must be >= 0")
    src = CassetteStore(source)
    manifest = src.load_manifest()
    if seq > len(manifest.transactions):
        raise ValueError(f"seq {seq} exceeds transaction count {len(manifest.transactions)}")

    new_run = run_id or str(uuid.uuid4())
    dest = Path(dest)
    if dest.exists() and any(dest.iterdir()):
        raise FileExistsError(f"destination not empty: {dest}")
    store = CassetteStore(dest)
    prefix = manifest.transactions[:seq]
    for tx in prefix:
        _copy_blob(src.root, store.root, tx.request_ref)
        _copy_blob(src.root, store.root, tx.response_ref)

    parent_id = str(manifest.extensions.get("run_id") or manifest.cassette_id)
    new_manifest = CassetteManifest(
        schema_version=manifest.schema_version,
        cassette_id=new_run,
        extensions={
            **dict(manifest.extensions),
            "run_id": new_run,
            "parent_run_id": parent_id,
            "fork_seq": seq,
            "lineage": LineageGraph(
                nodes=[
                    LineageNode(
                        run_id=parent_id,
                        parent_run_id=None,
                        fork_seq=None,
                        cassette_dir=str(source),
                    ),
                    LineageNode(
                        run_id=new_run,
                        parent_run_id=parent_id,
                        fork_seq=seq,
                        cassette_dir=str(dest),
                    ),
                ]
            ).model_dump(mode="json"),
        },
        transactions=list(prefix),
        checksums=dict(manifest.checksums),
        tool_id_map=dict(manifest.tool_id_map),
        hook_digests=dict(manifest.hook_digests),
        test_stack=dict(manifest.test_stack),
    )
    # Also copy hooks/decisions prefix if present
    decisions = src.root / "hooks" / "decisions.jsonl"
    if decisions.is_file() and seq > 0:
        lines = decisions.read_text(encoding="utf-8").splitlines()
        out = store.root / "hooks" / "decisions.jsonl"
        out.parent.mkdir(parents=True, exist_ok=True)
        # Best-effort: keep first seq decision lines when available
        out.write_text("\n".join(lines[:seq]) + ("\n" if lines[:seq] else ""), encoding="utf-8")

    store.write_manifest(new_manifest)
    return new_run, new_manifest


def load_lineage(cassette_dir: Path) -> LineageGraph:
    manifest = CassetteStore(cassette_dir).load_manifest()
    raw: Any = manifest.extensions.get("lineage")
    if not raw:
        run_id = str(manifest.extensions.get("run_id") or manifest.cassette_id)
        return LineageGraph(
            nodes=[
                LineageNode(
                    run_id=run_id,
                    parent_run_id=None,
                    fork_seq=None,
                    cassette_dir=str(cassette_dir),
                )
            ]
        )
    return LineageGraph.model_validate(raw)
