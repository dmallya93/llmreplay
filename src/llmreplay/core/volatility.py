"""Volatility / field-class path helpers."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

# Minimal starter ignore pack (SPEC defaults). Paths use simple dotted keys
# relative to a normalized event dict (not full JSONPath engine in C1).
DEFAULT_IGNORE_KEYS: frozenset[str] = frozenset(
    {
        "usage",
        "latency_ms",
        "x-request-id",
        "date",
        "created",
        "created_at",
        # Streaming is transport-only; match on final message shape (SPEC S6).
        "stream",
    }
)

THINKING_BLOCK_TYPES: frozenset[str] = frozenset({"thinking", "reasoning"})


def _is_ignore_key(key: str, ignore_keys: frozenset[str]) -> bool:
    lowered = key.lower()
    return lowered in ignore_keys or key in ignore_keys


def strip_ignore_fields(value: Any, ignore_keys: frozenset[str] | None = None) -> Any:
    """Deep-copy ``value`` removing keys listed in the ignore pack."""
    keys = ignore_keys if ignore_keys is not None else DEFAULT_IGNORE_KEYS
    return _strip(deepcopy(value), keys)


def _strip(value: Any, ignore_keys: frozenset[str]) -> Any:
    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for k, v in value.items():
            if _is_ignore_key(str(k), ignore_keys):
                continue
            out[str(k)] = _strip(v, ignore_keys)
        return out
    if isinstance(value, list):
        return [_strip(item, ignore_keys) for item in value]
    return value


def strip_thinking_blocks(value: Any) -> Any:
    """Remove thinking/reasoning content blocks from message-like structures."""
    return _strip_thinking(deepcopy(value))


def _strip_thinking(value: Any) -> Any:
    if isinstance(value, dict):
        # Anthropic-style content block
        if value.get("type") in THINKING_BLOCK_TYPES:
            return None
        out: dict[str, Any] = {}
        for k, v in value.items():
            cleaned = _strip_thinking(v)
            if cleaned is None:
                continue
            out[str(k)] = cleaned
        if "content" in out and isinstance(out["content"], list):
            out["content"] = [c for c in out["content"] if c is not None]
        return out
    if isinstance(value, list):
        return [item for item in (_strip_thinking(i) for i in value) if item is not None]
    return value
