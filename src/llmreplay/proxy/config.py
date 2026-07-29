"""Pydantic config for the local proxy."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

ProxyMode = Literal["record", "replay"]


class ProxyConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", arbitrary_types_allowed=True)

    mode: ProxyMode
    cassette_dir: Path
    upstream_base: str | None = None
    strict_routes: bool = True
    host: str = "127.0.0.1"
    port: int = Field(default=7432, ge=1, le=65535)
    profile: str = "local"
    config_path: Path | None = None
    free_mode: bool = False
    free_key_store: Path | None = None
    ollama_model: str = "qwen2.5-coder:latest"

    @model_validator(mode="after")
    def _validate_record_upstream(self) -> ProxyConfig:
        if self.upstream_base is not None:
            cleaned = self.upstream_base.strip().rstrip("/")
            object.__setattr__(self, "upstream_base", cleaned or None)
        if self.free_mode and self.mode == "record" and not self.upstream_base:
            object.__setattr__(self, "upstream_base", "http://127.0.0.1:3456")
        if self.mode == "record" and not self.upstream_base:
            raise ValueError("upstream_base is required when mode=record")
        return self
