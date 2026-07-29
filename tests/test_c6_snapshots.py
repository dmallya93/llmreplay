"""C6 filesystem snapshot tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from llmreplay.snapshot.engine import (
    create_snapshot,
    extensions_fs_payload,
    resolve_under_root,
    restore_snapshot,
)


@pytest.mark.unit
def test_snapshot_roundtrip_hash(tmp_path: Path) -> None:
    workspace = tmp_path / "ws"
    workspace.mkdir()
    (workspace / "a.txt").write_text("hello", encoding="utf-8")
    (workspace / "sub").mkdir()
    (workspace / "sub" / "b.txt").write_text("world", encoding="utf-8")
    dest = tmp_path / "snaps"
    meta = create_snapshot(workspace, dest, snapshot_id="s1")
    assert (dest / "s1.tar.zst").is_file()
    assert meta.manifest_hash

    out = tmp_path / "restored"
    restored = restore_snapshot(dest, "s1", out, force=True)
    assert restored.manifest_hash == meta.manifest_hash
    assert (out / "a.txt").read_text(encoding="utf-8") == "hello"
    assert (out / "sub" / "b.txt").read_text(encoding="utf-8") == "world"
    assert extensions_fs_payload(meta)["file_count"] == 2


@pytest.mark.unit
def test_denylist_excludes_secrets(tmp_path: Path) -> None:
    workspace = tmp_path / "ws"
    workspace.mkdir()
    (workspace / "ok.py").write_text("x=1", encoding="utf-8")
    (workspace / ".env").write_text("SECRET=1", encoding="utf-8")
    (workspace / ".ssh").mkdir()
    (workspace / ".ssh" / "id_rsa").write_text("PRIVATE", encoding="utf-8")
    meta = create_snapshot(workspace, tmp_path / "snaps", snapshot_id="s2")
    assert "ok.py" in meta.files
    assert ".env" not in meta.files
    assert not any(f.startswith(".ssh") for f in meta.files)


@pytest.mark.unit
def test_path_traversal_rejected(tmp_path: Path) -> None:
    root = tmp_path / "ws"
    root.mkdir()
    with pytest.raises(PermissionError):
        resolve_under_root(root, Path("../outside"))


@pytest.mark.unit
def test_refuse_dirty_restore_without_force(tmp_path: Path) -> None:
    workspace = tmp_path / "ws"
    workspace.mkdir()
    (workspace / "a.txt").write_text("a", encoding="utf-8")
    dest = tmp_path / "snaps"
    create_snapshot(workspace, dest, snapshot_id="s3")
    dirty = tmp_path / "dirty"
    dirty.mkdir()
    (dirty / "leftover").write_text("x", encoding="utf-8")
    with pytest.raises(RuntimeError, match="force"):
        restore_snapshot(dest, "s3", dirty, force=False)
