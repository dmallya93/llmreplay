"""Orchestrate free test-stack config materialization (up/down/status)."""

from __future__ import annotations

import shutil
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from llmreplay.teststack.config import write_ccr_config
from llmreplay.teststack.models import FreeStackConfig
from llmreplay.teststack.status import status as probe_status


class StackUpResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    config_dir: str
    ccr_config: str
    instructions: list[str]


def stack_up(config: FreeStackConfig | None = None) -> StackUpResult:
    """Materialize CCR config + instructions. Does not start OS daemons in CI."""
    cfg = config or FreeStackConfig()
    cfg.config_dir.mkdir(parents=True, exist_ok=True)
    ccr_path = write_ccr_config(cfg.config_dir / "ccr-config.json", cfg)
    instructions = [
        "1. Ensure Ollama is installed and running (`ollama serve`).",
        f"2. Pull/pin model: `ollama pull {cfg.ollama_model}`.",
        "3. Install CCR: `npm i -g @musistudio/claude-code-router`.",
        f"4. Copy {ccr_path} to ~/.claude-code-router/config.json (or merge Providers).",
        "5. Start CCR (`ccr` / `ccr code` per upstream docs).",
        f"6. `llmreplay record --upstream {cfg.ccr_host}` then point agent at {cfg.proxy_host}.",
        "7. `llmreplay keys create --free` and export the printed env.",
    ]
    return StackUpResult(
        config_dir=str(cfg.config_dir),
        ccr_config=str(ccr_path),
        instructions=instructions,
    )


def stack_down(config: FreeStackConfig | None = None, *, purge: bool = False) -> Path:
    """Remove generated test-stack files (does not kill Ollama/CCR processes)."""
    cfg = config or FreeStackConfig()
    if purge and cfg.config_dir.exists():
        shutil.rmtree(cfg.config_dir)
    return cfg.config_dir


def stack_status(config: FreeStackConfig | None = None):
    return probe_status(config)
