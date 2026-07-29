"""Free-mode test stack models and defaults (SPEC S8)."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

DEFAULT_OLLAMA_HOST = "http://127.0.0.1:11434"
DEFAULT_CCR_HOST = "http://127.0.0.1:3456"
DEFAULT_PROXY_HOST = "http://127.0.0.1:7432"
DEFAULT_OLLAMA_MODEL = "qwen2.5-coder:latest"


class FreeStackConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ollama_host: str = DEFAULT_OLLAMA_HOST
    ccr_host: str = DEFAULT_CCR_HOST
    proxy_host: str = DEFAULT_PROXY_HOST
    ollama_model: str = DEFAULT_OLLAMA_MODEL
    config_dir: Path = Field(default_factory=lambda: Path.home() / ".llmreplay" / "test-stack")


class ComponentStatus(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: Literal["ollama", "ccr", "proxy"]
    ok: bool
    detail: str
    url: str


class FreeStackStatus(BaseModel):
    model_config = ConfigDict(extra="forbid")

    healthy: bool
    components: list[ComponentStatus] = Field(default_factory=list)
    degraded: bool = False
    next: str = ""


class FreeKeyRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key_id: str
    token: str
    created_at: str
    quota_remaining: int
    localhost_only: bool = True
