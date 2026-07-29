"""Match pipeline: sort tool blocks, static projection, SHA-256 key."""

from __future__ import annotations

import hashlib
from copy import deepcopy
from typing import Any

from llmreplay.core.canonicalize import dumps_jcs
from llmreplay.core.volatility import (
    DEFAULT_IGNORE_KEYS,
    strip_ignore_fields,
    strip_thinking_blocks,
)


def sort_tool_blocks(message: dict[str, Any]) -> dict[str, Any]:
    """
    Return a copy of ``message`` with parallel tool_use / tool_result blocks sorted.

    Sort key: (name, JCS(input), tool_use_id) for tool_use;
    (tool_use_id,) for tool_result.
    """
    msg = deepcopy(message)
    content = msg.get("content")
    if not isinstance(content, list):
        return msg

    tool_uses = [b for b in content if isinstance(b, dict) and b.get("type") == "tool_use"]
    others = [b for b in content if not (isinstance(b, dict) and b.get("type") == "tool_use")]
    if len(tool_uses) >= 1:
        if len(tool_uses) > 1:
            tool_uses.sort(
                key=lambda b: (
                    str(b.get("name", "")),
                    dumps_jcs(b.get("input", {})),
                    str(b.get("id", "")),
                )
            )
        msg["content"] = others + tool_uses
        return msg

    tool_results = [
        b for b in content if isinstance(b, dict) and b.get("type") == "tool_result"
    ]
    others = [
        b for b in content if not (isinstance(b, dict) and b.get("type") == "tool_result")
    ]
    if len(tool_results) > 1:
        # tool_result has no name/input — sort by tool_use_id only (SPEC degenerates).
        tool_results.sort(key=lambda b: str(b.get("tool_use_id", "")))
        msg["content"] = others + tool_results
    return msg


def static_projection(
    event: Any,
    *,
    ignore_keys: frozenset[str] | None = None,
) -> Any:
    """Build the static projection used for matching (SPEC S1)."""
    keys = ignore_keys if ignore_keys is not None else DEFAULT_IGNORE_KEYS
    projected = strip_ignore_fields(event, keys)
    projected = strip_thinking_blocks(projected)
    if isinstance(projected, dict) and "messages" in projected:
        messages = projected["messages"]
        if isinstance(messages, list):
            projected["messages"] = [
                sort_tool_blocks(m) if isinstance(m, dict) else m for m in messages
            ]
    return projected


def match_key(
    event: Any,
    *,
    ignore_keys: frozenset[str] | None = None,
) -> str:
    """SHA-256 hex of JCS(static_projection(event))."""
    projection = static_projection(event, ignore_keys=ignore_keys)
    digest = hashlib.sha256(dumps_jcs(projection)).hexdigest()
    return digest
