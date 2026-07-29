"""CCR config + env helpers for free-mode startup."""

from __future__ import annotations

import json
from pathlib import Path

from llmreplay.teststack.models import FreeStackConfig


def render_ccr_config(config: FreeStackConfig | None = None) -> dict:
    """Minimal CCR config routing default traffic to local Ollama."""
    cfg = config or FreeStackConfig()
    model = cfg.ollama_model
    return {
        "Providers": [
            {
                "name": "ollama",
                "api_base_url": f"{cfg.ollama_host.rstrip('/')}/v1/chat/completions",
                "api_key": "ollama",
                "models": [model],
            }
        ],
        "Router": {
            "default": f"ollama,{model}",
            "background": f"ollama,{model}",
            "think": f"ollama,{model}",
            "longContext": f"ollama,{model}",
        },
    }


def write_ccr_config(path: Path, config: FreeStackConfig | None = None) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(render_ccr_config(config), indent=2) + "\n", encoding="utf-8")
    return path


def free_mode_env(
    *,
    proxy_base: str,
    free_token: str,
) -> dict[str, str]:
    """Env vars to inject for Claude Code / Codex against the llmreplay proxy."""
    base = proxy_base.rstrip("/")
    return {
        "ANTHROPIC_BASE_URL": base,
        "ANTHROPIC_API_KEY": free_token,
        "OPENAI_BASE_URL": f"{base}/v1",
        "OPENAI_API_KEY": free_token,
        "LLMREPLAY_FREE": "1",
    }


def print_env_exports(env: dict[str, str]) -> str:
    lines = [f"export {k}={v!s}" for k, v in env.items()]
    return "\n".join(lines) + "\n"
