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

    tool_results = [b for b in content if isinstance(b, dict) and b.get("type") == "tool_result"]
    others = [b for b in content if not (isinstance(b, dict) and b.get("type") == "tool_result")]
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
    return _sort_tools_in_tree(projected)


def _sort_tools_in_tree(value: Any) -> Any:
    """Sort parallel tool blocks under ``messages`` and Responses ``input``."""
    if isinstance(value, dict):
        out: dict[str, Any] = {str(k): _sort_tools_in_tree(v) for k, v in value.items()}
        for key in ("messages", "input"):
            seq = out.get(key)
            if isinstance(seq, list):
                sorted_seq = [sort_tool_blocks(m) if isinstance(m, dict) else m for m in seq]
                out[key] = _sort_openai_tool_message_runs(sorted_seq)
                out[key] = _sort_openai_tool_calls_in_messages(out[key])
                out[key] = _sort_responses_function_outputs(out[key])
        return out
    if isinstance(value, list):
        return [_sort_tools_in_tree(item) for item in value]
    return value


def _sort_openai_tool_message_runs(messages: list[Any]) -> list[Any]:
    """Sort contiguous OpenAI ``role=tool`` messages by ``tool_call_id``."""
    out: list[Any] = []
    i = 0
    while i < len(messages):
        msg = messages[i]
        if isinstance(msg, dict) and msg.get("role") == "tool":
            run: list[dict[str, Any]] = []
            while i < len(messages):
                cur = messages[i]
                if isinstance(cur, dict) and cur.get("role") == "tool":
                    run.append(cur)
                    i += 1
                    continue
                break
            run.sort(key=lambda m: str(m.get("tool_call_id", "")))
            out.extend(run)
            continue
        out.append(msg)
        i += 1
    return out


def _sort_openai_tool_calls_in_messages(messages: list[Any]) -> list[Any]:
    """Sort ``tool_calls`` arrays on assistant messages by id (parallel tools)."""
    out: list[Any] = []
    for msg in messages:
        if not isinstance(msg, dict):
            out.append(msg)
            continue
        calls = msg.get("tool_calls")
        if isinstance(calls, list) and len(calls) > 1:
            cloned = dict(msg)
            cloned["tool_calls"] = sorted(
                calls,
                key=lambda c: str(c.get("id", "")) if isinstance(c, dict) else "",
            )
            out.append(cloned)
        else:
            out.append(msg)
    return out


def _sort_responses_function_outputs(items: list[Any]) -> list[Any]:
    """Sort contiguous Responses ``function_call_output`` items by ``call_id``."""
    out: list[Any] = []
    i = 0
    while i < len(items):
        item = items[i]
        if isinstance(item, dict) and item.get("type") == "function_call_output":
            run: list[dict[str, Any]] = []
            while i < len(items):
                cur = items[i]
                if isinstance(cur, dict) and cur.get("type") == "function_call_output":
                    run.append(cur)
                    i += 1
                    continue
                break
            run.sort(key=lambda m: str(m.get("call_id", "")))
            out.extend(run)
            continue
        out.append(item)
        i += 1
    return out


def match_key(
    event: Any,
    *,
    ignore_keys: frozenset[str] | None = None,
) -> str:
    """SHA-256 hex of JCS(static_projection(event))."""
    projection = static_projection(event, ignore_keys=ignore_keys)
    digest = hashlib.sha256(dumps_jcs(projection)).hexdigest()
    return digest
