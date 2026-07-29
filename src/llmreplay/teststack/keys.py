"""Localhost-only free keys with simple quota (SPEC S8)."""

from __future__ import annotations

import json
import secrets
import uuid
from datetime import UTC, datetime
from pathlib import Path

from llmreplay.teststack.models import FreeKeyRecord

DEFAULT_QUOTA = 10_000
FREE_KEY_PREFIX = "llmreplay-free-"


class FreeKeyStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def _load(self) -> list[FreeKeyRecord]:
        if not self.path.is_file():
            return []
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        return [FreeKeyRecord.model_validate(item) for item in raw]

    def _save(self, records: list[FreeKeyRecord]) -> None:
        payload = [r.model_dump(mode="json") for r in records]
        self.path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    def create(self, *, quota: int = DEFAULT_QUOTA) -> FreeKeyRecord:
        record = FreeKeyRecord(
            key_id=str(uuid.uuid4()),
            token=f"{FREE_KEY_PREFIX}{secrets.token_urlsafe(24)}",
            created_at=datetime.now(UTC).isoformat(),
            quota_remaining=quota,
            localhost_only=True,
        )
        records = self._load()
        records.append(record)
        self._save(records)
        return record

    def get(self, token: str) -> FreeKeyRecord | None:
        for record in self._load():
            if record.token == token:
                return record
        return None

    def consume(self, token: str, *, units: int = 1) -> FreeKeyRecord:
        records = self._load()
        for idx, record in enumerate(records):
            if record.token != token:
                continue
            if not record.localhost_only:
                raise PermissionError("free keys are localhost-only")
            if record.quota_remaining < units:
                raise RuntimeError("free key quota exhausted")
            updated = record.model_copy(update={"quota_remaining": record.quota_remaining - units})
            records[idx] = updated
            self._save(records)
            return updated
        raise KeyError("unknown free key")

    def assert_localhost(self, peer_host: str) -> None:
        allowed = {"127.0.0.1", "::1", "localhost"}
        if peer_host not in allowed:
            raise PermissionError(f"free key refused for non-loopback peer {peer_host!r}")
