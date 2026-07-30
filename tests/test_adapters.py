"""Tests for ProtocolAdapter extraction — registry, sort permutation, SSE parity."""

from __future__ import annotations

import copy

import pytest

from llmreplay.adapters import ProtocolAdapter, adapter_for_path
from llmreplay.adapters.anthropic import AnthropicMessagesAdapter
from llmreplay.adapters.openai import OpenAIChatAdapter
from llmreplay.core.match import match_key
from llmreplay.parity import (
    claude_parallel_tools_session,
    openai_parallel_tools_session,
)
from llmreplay.proxy.sse import synthesize_sse


@pytest.mark.unit
class TestAdapterRegistry:
    def test_anthropic_path(self) -> None:
        adapter = adapter_for_path("/v1/messages")
        assert adapter is not None
        assert isinstance(adapter, AnthropicMessagesAdapter)
        assert adapter.id == "anthropic_messages"

    def test_openai_chat_path(self) -> None:
        adapter = adapter_for_path("/v1/chat/completions")
        assert adapter is not None
        assert isinstance(adapter, OpenAIChatAdapter)
        assert adapter.id == "openai_chat"

    def test_openai_responses_path(self) -> None:
        adapter = adapter_for_path("/v1/responses")
        assert adapter is not None
        assert isinstance(adapter, OpenAIChatAdapter)

    def test_unknown_path_returns_none(self) -> None:
        assert adapter_for_path("/v1/unknown") is None

    def test_adapters_satisfy_protocol(self) -> None:
        assert isinstance(AnthropicMessagesAdapter(), ProtocolAdapter)
        assert isinstance(OpenAIChatAdapter(), ProtocolAdapter)


@pytest.mark.unit
class TestAdapterSortPermutation:
    """Verify that shuffling parallel tool blocks produces the same match key."""

    def test_claude_parallel_tool_order_invariant(self) -> None:
        session = claude_parallel_tools_session()
        turn2 = session.turns[1].request
        key_original = match_key(turn2)

        shuffled = copy.deepcopy(turn2)
        msgs = shuffled["body"]["messages"]
        user_msg = msgs[-1]
        content = user_msg["content"]
        tool_results = [
            b for b in content if isinstance(b, dict) and b.get("type") == "tool_result"
        ]
        assert len(tool_results) >= 2, "fixture must have >=2 tool_results"
        tool_results.reverse()
        others = [
            b for b in content
            if not (isinstance(b, dict) and b.get("type") == "tool_result")
        ]
        user_msg["content"] = others + tool_results

        key_shuffled = match_key(shuffled)
        assert key_original == key_shuffled

    def test_openai_tool_message_order_invariant(self) -> None:
        session = openai_parallel_tools_session()
        turn2 = session.turns[1].request
        key_original = match_key(turn2)

        shuffled = copy.deepcopy(turn2)
        msgs = shuffled["body"]["messages"]
        tool_msgs = [m for m in msgs if isinstance(m, dict) and m.get("role") == "tool"]
        assert len(tool_msgs) >= 2, "fixture must have >=2 tool messages"
        tool_msgs.reverse()
        non_tool = [
            m for m in msgs if not (isinstance(m, dict) and m.get("role") == "tool")
        ]
        shuffled["body"]["messages"] = non_tool + tool_msgs

        key_shuffled = match_key(shuffled)
        assert key_original == key_shuffled

    def test_codex_responses_function_output_order_invariant(self) -> None:
        """Shuffling function_call_output items produces the same match key."""
        items = [
            {"type": "function_call_output", "call_id": "call_z", "output": "out-z"},
            {"type": "function_call_output", "call_id": "call_a", "output": "out-a"},
        ]
        event_a = {
            "method": "POST",
            "path": "/v1/responses",
            "headers": {},
            "body": {"model": "test", "input": items},
        }
        event_b = copy.deepcopy(event_a)
        event_b["body"]["input"] = list(reversed(items))

        assert match_key(event_a) == match_key(event_b)


@pytest.mark.unit
class TestAdapterSSEParity:
    """Adapter SSE matches proxy/sse.py byte-for-byte."""

    def test_anthropic_sse_matches_proxy(self) -> None:
        adapter = AnthropicMessagesAdapter()
        msg = {
            "id": "msg_1",
            "content": [{"type": "text", "text": "hi"}],
            "stop_reason": "end_turn",
        }
        adapter_sse = adapter.synthesize_sse(msg)
        proxy_sse = synthesize_sse("/v1/messages", msg)
        assert adapter_sse == proxy_sse

    def test_openai_chat_sse_matches_proxy(self) -> None:
        adapter = OpenAIChatAdapter()
        msg = {
            "id": "chat_1",
            "choices": [
                {
                    "message": {"role": "assistant", "content": "hello"},
                    "finish_reason": "stop",
                }
            ],
        }
        adapter_sse = adapter.synthesize_sse(msg)
        proxy_sse = synthesize_sse("/v1/chat/completions", msg)
        assert adapter_sse == proxy_sse

    def test_openai_responses_sse_matches_proxy(self) -> None:
        adapter = OpenAIChatAdapter()
        msg = {"id": "resp_1", "output": [{"type": "text", "text": "ok"}]}
        adapter_sse = adapter.synthesize_sse(msg)
        proxy_sse = synthesize_sse("/v1/responses", msg)
        assert adapter_sse == proxy_sse
