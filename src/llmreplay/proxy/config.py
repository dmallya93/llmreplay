"""Pydantic config for the local proxy."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

ProxyMode = Literal["record", "replay"]
_LOOPBACK = frozenset({"127.0.0.1", "::1", "localhost"})


class ProxyConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", arbitrary_types_allowed=True)

    mode: ProxyMode
    cassette_dir: Path
    upstream_base: str | None = None
    strict_routes: bool = True
    host: str = "127.0.0.1"
    # 0 = OS-assigned ephemeral port (resolved after bind by run_with_proxy).
    port: int = Field(default=7432, ge=0, le=65535)
    profile: str = "local"
    config_path: Path | None = None
    free_mode: bool = False
    free_key_store: Path | None = None
    ollama_model: str = "qwen2.5-coder:latest"
    allow_non_loopback: bool = False
    allow_live: bool = False

    @model_validator(mode="after")
    def _validate_record_upstream(self) -> ProxyConfig:
        if self.upstream_base is not None:
            cleaned = self.upstream_base.strip().rstrip("/")
            object.__setattr__(self, "upstream_base", cleaned or None)
        if self.free_mode and self.mode == "record" and not self.upstream_base:
            object.__setattr__(self, "upstream_base", "http://127.0.0.1:3456")
        if self.mode == "record" and not self.upstream_base:
            raise ValueError("upstream_base is required when mode=record")
        if not self.allow_non_loopback and self.host not in _LOOPBACK:
            raise ValueError(
                f"{self.mode} mode refuses non-loopback --host "
                f"{self.host!r} (pass allow_non_loopback=True / --allow-remote)"
            )
        if self.allow_non_loopback and not self.free_mode:
            raise ValueError(
                "non-loopback bind requires free_mode=True / --free "
                "(unauthenticated open proxy otherwise)"
            )
        return self
