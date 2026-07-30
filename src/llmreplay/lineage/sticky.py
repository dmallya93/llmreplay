"""debug_sticky writeback helpers."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict

from llmreplay.config.profiles import STRICT_PROFILES, load_llmreplay_yaml
from llmreplay.lineage.tweak import tweak_transaction


class StickyResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    applied: bool
    reason: str


def sticky_writeback_allowed(profile: str, config_path: Path | None = None) -> bool:
    cfg = load_llmreplay_yaml(config_path)
    if profile in STRICT_PROFILES:
        return False
    return cfg.resolved_profile(profile).sticky_writeback


def maybe_sticky_write(
    cassette_dir: Path,
    *,
    profile: str,
    seq: int,
    field: str,
    value: object,
    config_path: Path | None = None,
) -> StickyResult:
    """Apply a sticky mismatch writeback only when the profile permits it."""
    if not sticky_writeback_allowed(profile, config_path):
        return StickyResult(
            applied=False,
            reason=f"sticky_writeback forbidden for profile {profile}",
        )
    tweak_transaction(cassette_dir, seq=seq, field=field, value=value)
    return StickyResult(applied=True, reason="wrote mismatch into cassette (debug_sticky)")
