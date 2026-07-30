"""Hook script digests and cassette header updates."""

from __future__ import annotations

import hashlib
from pathlib import Path

from llmreplay.hooks.models import HookVerifyResult
from llmreplay.store.cassette import CassetteStore

HOOK_PROTOCOL_VERSION = 1


def digest_script(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha256(data).hexdigest()


def digest_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def verify_hook_digests(
    cassette: CassetteStore,
    scripts: dict[str, Path],
    *,
    profile: str = "local",
) -> HookVerifyResult:
    """Compare live script digests to cassette ``hook_digests``.

    ``ci``/``strict`` treat any mismatch as failure (exit 6 at CLI).
    """
    recorded = cassette.load_manifest().hook_digests
    mismatches: dict[str, str] = {}
    for name, path in scripts.items():
        live = digest_script(path)
        expected = recorded.get(name)
        if expected is None:
            mismatches[name] = f"missing in cassette (live={live[:12]}…)"
        elif expected != live:
            mismatches[name] = f"expected={expected[:12]}… live={live[:12]}…"
    for name in recorded:
        if name not in scripts:
            mismatches[name] = "script missing on disk"
    strict = profile in {"ci", "strict"}
    if mismatches and strict:
        return HookVerifyResult(
            ok=False,
            mismatches=mismatches,
            message="hook digest mismatch (ci/strict) — exit HOOK_OR_POLICY_DIVERGENCE",
        )
    if mismatches:
        return HookVerifyResult(
            ok=True,
            mismatches=mismatches,
            message="hook digest drift (local warn)",
        )
    return HookVerifyResult(ok=True, mismatches={}, message="hook digests match")
