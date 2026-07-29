"""Cassette validation (`llmreplay validate`)."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from llmreplay.scrub.engine import residual_secret_hits
from llmreplay.store.cassette import CassetteStore
from llmreplay.store.models import CassetteManifest


class ValidateIssue(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    path: str
    message: str


class ValidateReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ok: bool
    cassette_dir: str
    issues: list[ValidateIssue] = Field(default_factory=list)


def validate_cassette(cassette_dir: Path, *, scan_secrets: bool = True) -> ValidateReport:
    store = CassetteStore(cassette_dir)
    issues: list[ValidateIssue] = []
    if not store.manifest_path.is_file():
        issues.append(
            ValidateIssue(
                code="manifest_missing",
                path=str(store.manifest_path),
                message="cassette.json not found",
            )
        )
        return ValidateReport(ok=False, cassette_dir=str(cassette_dir), issues=issues)

    try:
        raw = json.loads(store.manifest_path.read_text(encoding="utf-8"))
        manifest = CassetteManifest.model_validate(raw)
    except (json.JSONDecodeError, ValidationError) as exc:
        issues.append(
            ValidateIssue(
                code="manifest_invalid",
                path=str(store.manifest_path),
                message=str(exc),
            )
        )
        return ValidateReport(ok=False, cassette_dir=str(cassette_dir), issues=issues)

    seen_hashes: dict[str, str] = {}
    for tx in manifest.transactions:
        for label, ref in (("request", tx.request_ref), ("response", tx.response_ref)):
            path = store.root / ref
            if not path.is_file():
                issues.append(
                    ValidateIssue(
                        code="missing_blob",
                        path=ref,
                        message=f"{label} blob missing for transaction {tx.id}",
                    )
                )
                continue
            if scan_secrets:
                text = path.read_text(encoding="utf-8", errors="ignore")
                hits = residual_secret_hits(text)
                if hits:
                    issues.append(
                        ValidateIssue(
                            code="residual_secret",
                            path=ref,
                            message=f"residual secret patterns: {', '.join(hits)}",
                        )
                    )
        if tx.static_hash in seen_hashes:
            issues.append(
                ValidateIssue(
                    code="ambiguous_match",
                    path=tx.id,
                    message=(
                        f"duplicate static_hash with transaction {seen_hashes[tx.static_hash]}"
                    ),
                )
            )
        else:
            seen_hashes[tx.static_hash] = tx.id

    if manifest.schema_version < 1:
        issues.append(
            ValidateIssue(
                code="stale_schema",
                path="cassette.json",
                message=f"schema_version {manifest.schema_version} is invalid",
            )
        )

    return ValidateReport(
        ok=not issues,
        cassette_dir=str(cassette_dir),
        issues=issues,
    )
