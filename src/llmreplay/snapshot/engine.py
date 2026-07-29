"""Filesystem snapshot capture/restore (SPEC S7)."""

from __future__ import annotations

import hashlib
import io
import json
import os
import tarfile
from pathlib import Path
from typing import Any

import zstandard as zstd
from pydantic import BaseModel, ConfigDict, Field

DEFAULT_DENYLIST = (
    ".env",
    ".env.local",
    ".env.production",
    "id_rsa",
    "id_ed25519",
    "credentials",
    ".aws/credentials",
    ".ssh/",
)


class SnapshotMeta(BaseModel):
    model_config = ConfigDict(extra="forbid")

    snapshot_id: str
    root: str
    manifest_hash: str
    files: list[str] = Field(default_factory=list)
    denylist: list[str] = Field(default_factory=list)


def _is_denied(rel: str, denylist: tuple[str, ...] | list[str]) -> bool:
    name = rel.replace("\\", "/")
    base = Path(name).name
    for pattern in denylist:
        pat = pattern.replace("\\", "/")
        if pat.endswith("/"):
            if name.startswith(pat) or f"/{pat}" in f"/{name}/":
                return True
        elif base == pat or name.endswith(f"/{pat}") or name == pat:
            return True
    return False


def resolve_under_root(root: Path, candidate: Path) -> Path:
    """Resolve candidate and ensure it stays under root (no traversal)."""
    root_resolved = root.resolve()
    target = (root / candidate).resolve() if not candidate.is_absolute() else candidate.resolve()
    try:
        target.relative_to(root_resolved)
    except ValueError as exc:
        raise PermissionError(f"path escapes workspace root: {candidate}") from exc
    return target


def iter_tracked_files(
    root: Path, denylist: tuple[str, ...] | list[str] = DEFAULT_DENYLIST
) -> list[Path]:
    root = root.resolve()
    files: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        # prune denied dirs
        rel_dir = Path(dirpath).resolve().relative_to(root).as_posix()
        dirnames[:] = [
            d
            for d in dirnames
            if not _is_denied(f"{rel_dir}/{d}".lstrip("./") + "/", denylist)
            and not _is_denied(d + "/", denylist)
        ]
        for name in filenames:
            rel = (Path(dirpath) / name).resolve().relative_to(root).as_posix()
            if _is_denied(rel, denylist) or _is_denied(name, denylist):
                continue
            files.append(Path(dirpath) / name)
    return sorted(files, key=lambda p: p.as_posix())


def manifest_hash(root: Path, files: list[Path]) -> str:
    root = root.resolve()
    h = hashlib.sha256()
    for path in files:
        rel = path.resolve().relative_to(root).as_posix()
        h.update(rel.encode("utf-8"))
        h.update(b"\0")
        h.update(path.read_bytes())
        h.update(b"\0")
    return h.hexdigest()


def create_snapshot(
    workspace: Path,
    dest_dir: Path,
    *,
    snapshot_id: str,
    denylist: tuple[str, ...] | list[str] = DEFAULT_DENYLIST,
) -> SnapshotMeta:
    workspace = workspace.resolve()
    if not workspace.is_dir():
        raise FileNotFoundError(f"workspace not found: {workspace}")
    dest_dir.mkdir(parents=True, exist_ok=True)
    files = iter_tracked_files(workspace, denylist)
    digest = manifest_hash(workspace, files)

    tar_buf = io.BytesIO()
    with tarfile.open(fileobj=tar_buf, mode="w") as tar:
        for path in files:
            rel = path.resolve().relative_to(workspace).as_posix()
            tar.add(path, arcname=rel)
    compressed = zstd.ZstdCompressor().compress(tar_buf.getvalue())
    archive = dest_dir / f"{snapshot_id}.tar.zst"
    archive.write_bytes(compressed)

    meta = SnapshotMeta(
        snapshot_id=snapshot_id,
        root=str(workspace),
        manifest_hash=digest,
        files=[p.resolve().relative_to(workspace).as_posix() for p in files],
        denylist=list(denylist),
    )
    (dest_dir / f"{snapshot_id}.json").write_text(
        json.dumps(meta.model_dump(mode="json"), indent=2) + "\n",
        encoding="utf-8",
    )
    return meta


def restore_snapshot(
    snapshot_dir: Path,
    snapshot_id: str,
    workspace: Path,
    *,
    force: bool = False,
) -> SnapshotMeta:
    """Restore snapshot into workspace. Refuses non-empty dirty trees without force."""
    meta_path = snapshot_dir / f"{snapshot_id}.json"
    archive = snapshot_dir / f"{snapshot_id}.tar.zst"
    if not meta_path.is_file() or not archive.is_file():
        raise FileNotFoundError(f"snapshot {snapshot_id} missing")
    meta = SnapshotMeta.model_validate(json.loads(meta_path.read_text(encoding="utf-8")))
    workspace.mkdir(parents=True, exist_ok=True)
    workspace = workspace.resolve()
    existing = [p for p in workspace.rglob("*") if p.is_file()]
    if existing and not force:
        raise RuntimeError("refuse dirty snapshot restore without force")

    raw = zstd.ZstdDecompressor().decompress(archive.read_bytes())
    with tarfile.open(fileobj=io.BytesIO(raw), mode="r:") as tar:
        for member in tar.getmembers():
            if member.name.startswith("/") or ".." in Path(member.name).parts:
                raise PermissionError(f"unsafe archive member: {member.name}")
            resolve_under_root(workspace, Path(member.name))
        tar.extractall(workspace, filter="data")

    files = iter_tracked_files(workspace, meta.denylist)
    digest = manifest_hash(workspace, files)
    if digest != meta.manifest_hash:
        raise RuntimeError("restored manifest hash mismatch")
    return meta


def extensions_fs_payload(meta: SnapshotMeta) -> dict[str, Any]:
    return {
        "snapshot_id": meta.snapshot_id,
        "manifest_hash": meta.manifest_hash,
        "file_count": len(meta.files),
    }
