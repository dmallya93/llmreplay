"""On-disk cassette store (SPEC S4 layout — C1 subset)."""

from __future__ import annotations

import json
import os
import sys
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from llmreplay.store.models import CassetteManifest, CassetteTransaction


def _exclusive_lock(lock_path: Path):
    """Context manager: exclusive advisory lock on ``lock_path``."""

    class _Lock:
        def __enter__(self) -> Path:
            lock_path.parent.mkdir(parents=True, exist_ok=True)
            self._fh = lock_path.open("a+", encoding="utf-8")
            if sys.platform == "win32":
                import msvcrt

                msvcrt.locking(self._fh.fileno(), msvcrt.LK_LOCK, 1)
            else:
                import fcntl

                fcntl.flock(self._fh.fileno(), fcntl.LOCK_EX)
            return lock_path

        def __exit__(self, *args: object) -> None:
            if sys.platform == "win32":
                import msvcrt

                self._fh.seek(0)
                msvcrt.locking(self._fh.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(self._fh.fileno(), fcntl.LOCK_UN)
            self._fh.close()

    return _Lock()


def _fsync_dir(directory: Path) -> None:
    if sys.platform == "win32":
        return
    fd = os.open(str(directory), os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


@dataclass
class CassetteStore:
    """Filesystem cassette root with atomic manifest writes."""

    root: Path
    schema_version: int = 1
    cassette_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def __post_init__(self) -> None:
        self.root = Path(self.root)
        self.root.mkdir(parents=True, exist_ok=True)
        for name in ("requests", "responses", "bodies", "snapshots", "locks"):
            (self.root / name).mkdir(exist_ok=True)

    @property
    def manifest_path(self) -> Path:
        return self.root / "cassette.json"

    @property
    def lock_path(self) -> Path:
        return self.root / "locks" / "cassette.lock"

    def empty_manifest(self) -> CassetteManifest:
        return CassetteManifest(
            schema_version=self.schema_version,
            cassette_id=self.cassette_id,
        )

    def load_manifest(self) -> CassetteManifest:
        if not self.manifest_path.is_file():
            return self.empty_manifest()
        raw = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        return CassetteManifest.model_validate(raw)

    def write_manifest(self, manifest: CassetteManifest) -> None:
        """Atomically replace cassette.json under exclusive lock."""
        with _exclusive_lock(self.lock_path):
            self._write_manifest_unlocked(manifest)

    def _write_manifest_unlocked(self, manifest: CassetteManifest) -> None:
        payload = json.dumps(manifest.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"
        tmp = self.manifest_path.with_suffix(f".tmp.{os.getpid()}.{uuid.uuid4().hex}")
        with tmp.open("w", encoding="utf-8") as fh:
            fh.write(payload)
            fh.flush()
            os.fsync(fh.fileno())
        if self.manifest_path.is_file():
            bak = self.root / f"cassette.json.bak.{uuid.uuid4().hex[:8]}"
            self.manifest_path.replace(bak)
        tmp.replace(self.manifest_path)
        _fsync_dir(self.root)

    def append_transaction(
        self,
        *,
        request: dict[str, Any],
        response: dict[str, Any],
        static_hash: str,
    ) -> str:
        """Persist request/response JSON and append a transaction to the manifest."""
        tx_id = uuid.uuid4().hex
        req_name = f"{tx_id}.json"
        resp_name = f"{tx_id}.json"
        tx = CassetteTransaction(
            id=tx_id,
            request_ref=f"requests/{req_name}",
            response_ref=f"responses/{resp_name}",
            static_hash=static_hash,
        )
        with _exclusive_lock(self.lock_path):
            req_path = self.root / "requests" / req_name
            resp_path = self.root / "responses" / resp_name
            req_path.write_text(
                json.dumps(request, indent=2, sort_keys=True) + "\n", encoding="utf-8"
            )
            resp_path.write_text(
                json.dumps(response, indent=2, sort_keys=True) + "\n", encoding="utf-8"
            )
            manifest = self.load_manifest()
            manifest.transactions.append(tx)
            self._write_manifest_unlocked(manifest)
        return tx_id

    def set_test_stack(self, fingerprint: dict[str, Any]) -> None:
        """Record free-stack fingerprint on the cassette header (SPEC S8)."""
        with _exclusive_lock(self.lock_path):
            manifest = self.load_manifest()
            manifest.test_stack = dict(fingerprint)
            self._write_manifest_unlocked(manifest)

    def set_hook_digests(self, digests: dict[str, str]) -> None:
        """Record SHA-256 digests of hook scripts (DESIGN S12)."""
        with _exclusive_lock(self.lock_path):
            manifest = self.load_manifest()
            merged = dict(manifest.hook_digests)
            merged.update(digests)
            manifest.hook_digests = merged
            self._write_manifest_unlocked(manifest)
