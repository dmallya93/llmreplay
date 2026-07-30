"""SSE helpers for SPEC S6 — synthesize stream from final message."""

from __future__ import annotations

import json
from typing import Any


def wants_stream(body: Any, headers: dict[str, str] | None = None) -> bool:
    if isinstance(body, dict) and body.get("stream") is True:
        return True
    if headers:
        accept = headers.get("accept") or headers.get("Accept") or ""
        if "text/event-stream" in accept.lower():
            return True
    return False


def strip_stream_flag(body: Any) -> Any:
    """Return a copy of body with stream forced off for upstream capture."""
    if not isinstance(body, dict):
        return body
    out = dict(body)
    out["stream"] = False
    return out


def synthesize_sse(path: str, message: dict[str, Any]) -> bytes:
    """Build a minimal valid SSE body from a stored final JSON message."""
    if path.endswith("/messages"):
        # Anthropic Messages-style: message_start with full message + message_stop.
        start = {
            "type": "message_start",
            "message": message,
        }
        chunks = [
            f"event: message_start\ndata: {json.dumps(start, ensure_ascii=False)}\n\n",
            'event: message_stop\ndata: {"type": "message_stop"}\n\n',
        ]
        return "".join(chunks).encode("utf-8")

    # OpenAI Chat Completions / Responses-style: one chunk then [DONE]
    if "choices" in message:
        delta = {
            "id": message.get("id", "chatcmpl-llmreplay"),
            "object": "chat.completion.chunk",
            "choices": [
                {
                    "index": 0,
                    "delta": {"content": _openai_text(message)},
                    "finish_reason": "stop",
                }
            ],
        }
        return (f"data: {json.dumps(delta, ensure_ascii=False)}\n\ndata: [DONE]\n\n").encode()

    # Generic: wrap whole JSON as a single data event
    return f"data: {json.dumps(message, ensure_ascii=False)}\n\ndata: [DONE]\n\n".encode()


def _openai_text(message: dict[str, Any]) -> str:
    choices = message.get("choices")
    if isinstance(choices, list) and choices:
        msg = choices[0].get("message") if isinstance(choices[0], dict) else None
        if isinstance(msg, dict):
            content = msg.get("content")
            if isinstance(content, str):
                return content
    return json.dumps(message, ensure_ascii=False)


def parse_openai_sse(raw: str) -> dict[str, Any]:
    """Best-effort assemble a chat.completion object from OpenAI SSE text."""
    content_parts: list[str] = []
    last: dict[str, Any] = {}
    for line in raw.splitlines():
        if not line.startswith("data:"):
            continue
        data = line[5:].strip()
        if not data or data == "[DONE]":
            continue
        try:
            chunk = json.loads(data)
        except json.JSONDecodeError:
            continue
        if isinstance(chunk, dict):
            last = chunk
            choices = chunk.get("choices")
            if isinstance(choices, list) and choices and isinstance(choices[0], dict):
                delta = choices[0].get("delta") or {}
                if isinstance(delta, dict) and isinstance(delta.get("content"), str):
                    content_parts.append(delta["content"])
    if content_parts:
        return {
            "id": last.get("id", "chatcmpl-assembled"),
            "object": "chat.completion",
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": "".join(content_parts)},
                    "finish_reason": "stop",
                }
            ],
        }
    return last or {"raw_text": raw}
