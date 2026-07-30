"""OpenAI Chat Completions + Responses adapter."""

from __future__ import annotations

import json
from typing import Any

from llmreplay.core.match import (
    sort_openai_tool_calls_in_messages,
    sort_openai_tool_message_runs,
    sort_responses_function_outputs,
    sort_tool_blocks,
)


class OpenAIChatAdapter:
    """Adapter for ``POST /v1/chat/completions`` and ``POST /v1/responses``."""

    @property
    def id(self) -> str:
        return "openai_chat"

    def sort_tools_in_messages(self, messages: list[Any]) -> list[Any]:
        sorted_msgs = [sort_tool_blocks(m) if isinstance(m, dict) else m for m in messages]
        sorted_msgs = sort_openai_tool_message_runs(sorted_msgs)
        sorted_msgs = sort_openai_tool_calls_in_messages(sorted_msgs)
        sorted_msgs = sort_responses_function_outputs(sorted_msgs)
        return sorted_msgs

    def synthesize_sse(self, message: dict[str, Any]) -> bytes:
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
