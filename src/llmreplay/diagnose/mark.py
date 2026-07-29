"""Profile / yaml mutation helpers (`mark-ignore`, `mark-live`)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from llmreplay.config.profiles import LLMReplayFileConfig, load_llmreplay_yaml


def _dump_yaml(cfg: LLMReplayFileConfig, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = cfg.model_dump(mode="json")
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def mark_ignore_fields(
    path: Path,
    fields: list[str],
    *,
    profile: str | None = None,
) -> LLMReplayFileConfig:
    """Append fields to defaults.ignore (or profile.ignore). Never auto-applied."""
    cfg = load_llmreplay_yaml(path if path.is_file() else None)
    targets = fields
    if profile:
        prof = cfg.resolved_profile(profile)
        existing = list(prof.ignore)
        for field in targets:
            if field not in existing:
                existing.append(field)
        cfg.profiles[profile] = prof.model_copy(update={"ignore": existing})
    else:
        existing = list(cfg.defaults.ignore)
        for field in targets:
            if field not in existing:
                existing.append(field)
        cfg.defaults = cfg.defaults.model_copy(update={"ignore": existing})
    _dump_yaml(cfg, path)
    return cfg


def mark_live_tool(path: Path, tool_name: str, **extra: Any) -> LLMReplayFileConfig:
    """Mark a tool as live in llmreplay.yaml tools map."""
    cfg = load_llmreplay_yaml(path if path.is_file() else None)
    entry = dict(cfg.tools.get(tool_name, {}))
    entry["class"] = "live"
    entry.update(extra)
    cfg.tools[tool_name] = entry
    _dump_yaml(cfg, path)
    return cfg
