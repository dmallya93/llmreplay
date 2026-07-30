"""Anthropic Messages adapter."""

from __future__ import annotations

import json
from typing import Any

from llmreplay.core.match import sort_tool_blocks


class AnthropicMessagesAdapter:
    """Adapter for ``POST /v1/messages``."""

    @property
    def id(self) -> str:
        return "anthropic_messages"

    def sort_tools_in_messages(self, messages: list[Any]) -> list[Any]:
        return [sort_tool_blocks(m) if isinstance(m, dict) else m for m in messages]

    def synthesize_sse(self, message: dict[str, Any]) -> bytes:
        start = {"type": "message_start", "message": message}
        chunks = [
            f"event: message_start\ndata: {json.dumps(start, ensure_ascii=False)}\n\n",
            'event: message_stop\ndata: {"type": "message_stop"}\n\n',
        ]
        return "".join(chunks).encode("utf-8")
