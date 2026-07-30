"""Adapter registry — resolve a ProtocolAdapter by request path."""

from __future__ import annotations

from llmreplay.adapters.anthropic import AnthropicMessagesAdapter
from llmreplay.adapters.base import ProtocolAdapter
from llmreplay.adapters.openai import OpenAIChatAdapter

_ANTHROPIC = AnthropicMessagesAdapter()
_OPENAI = OpenAIChatAdapter()

_PATH_MAP: dict[str, ProtocolAdapter] = {
    "/v1/messages": _ANTHROPIC,
    "/v1/chat/completions": _OPENAI,
    "/v1/responses": _OPENAI,
}


def adapter_for_path(path: str) -> ProtocolAdapter | None:
    """Return the adapter for a request path, or ``None`` for unknown paths."""
    return _PATH_MAP.get(path)
