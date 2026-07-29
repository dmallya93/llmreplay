"""Pydantic models for scrub pattern config."""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field


class SecretRegex(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    pattern: str


class ScrubPatterns(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scrub_header_keys: list[str] = Field(default_factory=list)
    sensitive_keys: list[str] = Field(default_factory=list)
    scrub_paths: list[str] = Field(default_factory=list)
    secret_regexes: list[SecretRegex] = Field(default_factory=list)


def load_scrub_patterns(path: Path | None = None) -> ScrubPatterns:
    """Load scrub patterns from YAML (defaults to packaged default_patterns.yaml)."""
    if path is None:
        path = Path(__file__).with_name("default_patterns.yaml")
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return ScrubPatterns.model_validate(data)
