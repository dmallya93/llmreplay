"""Multi-turn protocol fixtures for Claude Messages + OpenAI Responses."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class Turn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request: dict[str, Any]
    response: dict[str, Any]


class ProtocolSession(BaseModel):
    model_config = ConfigDict(extra="forbid")

    agent: str
    turns: list[Turn] = Field(default_factory=list)


def claude_tool_session() -> ProtocolSession:
    """Two-turn Claude Messages: tool_use then tool_result."""
    turn1_req = {
        "method": "POST",
        "path": "/v1/messages",
        "headers": {},
        "body": {
            "model": "claude-test",
            "messages": [{"role": "user", "content": "list files"}],
            "tools": [{"name": "Bash", "input_schema": {"type": "object"}}],
        },
    }
    turn1_resp = {
        "id": "msg_1",
        "content": [
            {
                "type": "tool_use",
                "id": "toolu_1",
                "name": "Bash",
                "input": {"command": "ls"},
            }
        ],
        "stop_reason": "tool_use",
    }
    turn2_req = {
        "method": "POST",
        "path": "/v1/messages",
        "headers": {},
        "body": {
            "model": "claude-test",
            "messages": [
                {"role": "user", "content": "list files"},
                {"role": "assistant", "content": turn1_resp["content"]},
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": "toolu_1",
                            "content": "a.txt\nb.txt",
                        }
                    ],
                },
            ],
        },
    }
    turn2_resp = {
        "id": "msg_2",
        "content": [{"type": "text", "text": "two files"}],
        "stop_reason": "end_turn",
    }
    return ProtocolSession(
        agent="claude",
        turns=[
            Turn(request=turn1_req, response=turn1_resp),
            Turn(request=turn2_req, response=turn2_resp),
        ],
    )


def claude_parallel_tools_session() -> ProtocolSession:
    """Assistant emits two parallel tool_uses; follow-up returns both results (any order)."""
    tools_out = [
        {
            "type": "tool_use",
            "id": "toolu_read",
            "name": "Read",
            "input": {"path": "a.py"},
        },
        {
            "type": "tool_use",
            "id": "toolu_bash",
            "name": "Bash",
            "input": {"command": "pwd"},
        },
    ]
    turn1_req = {
        "method": "POST",
        "path": "/v1/messages",
        "headers": {},
        "body": {
            "model": "claude-test",
            "messages": [
                {
                    "role": "user",
                    "content": (
                        "You are a senior engineer. Inspect a.py and print cwd, "
                        "then summarize. Use tools in parallel."
                    ),
                }
            ],
            "tools": [
                {"name": "Read", "input_schema": {"type": "object"}},
                {"name": "Bash", "input_schema": {"type": "object"}},
            ],
        },
    }
    turn1_resp = {
        "id": "msg_p1",
        "content": tools_out,
        "stop_reason": "tool_use",
    }
    # Results intentionally reverse order vs tool_use emission — match must still hit.
    turn2_req = {
        "method": "POST",
        "path": "/v1/messages",
        "headers": {},
        "body": {
            "model": "claude-test",
            "messages": [
                turn1_req["body"]["messages"][0],
                {"role": "assistant", "content": tools_out},
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": "toolu_bash",
                            "content": "/workspace",
                        },
                        {
                            "type": "tool_result",
                            "tool_use_id": "toolu_read",
                            "content": "print('hi')",
                        },
                    ],
                },
            ],
        },
    }
    turn2_resp = {
        "id": "msg_p2",
        "content": [{"type": "text", "text": "a.py prints hi; cwd=/workspace"}],
        "stop_reason": "end_turn",
    }
    return ProtocolSession(
        agent="claude",
        turns=[
            Turn(request=turn1_req, response=turn1_resp),
            Turn(request=turn2_req, response=turn2_resp),
        ],
    )


def claude_tool_chain_session() -> ProtocolSession:
    """Three-turn chain: plan → tool → follow-up tool → final answer."""
    t1_req = {
        "method": "POST",
        "path": "/v1/messages",
        "headers": {},
        "body": {
            "model": "claude-test",
            "messages": [{"role": "user", "content": "fix the flaky test"}],
            "tools": [{"name": "Bash", "input_schema": {"type": "object"}}],
        },
    }
    t1_resp = {
        "id": "msg_c1",
        "content": [
            {
                "type": "tool_use",
                "id": "toolu_c1",
                "name": "Bash",
                "input": {"command": "pytest -q"},
            }
        ],
        "stop_reason": "tool_use",
    }
    t2_req = {
        "method": "POST",
        "path": "/v1/messages",
        "headers": {},
        "body": {
            "model": "claude-test",
            "messages": [
                {"role": "user", "content": "fix the flaky test"},
                {"role": "assistant", "content": t1_resp["content"]},
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": "toolu_c1",
                            "content": "1 failed",
                        }
                    ],
                },
            ],
        },
    }
    t2_resp = {
        "id": "msg_c2",
        "content": [
            {
                "type": "tool_use",
                "id": "toolu_c2",
                "name": "Bash",
                "input": {"command": "pytest -q tests/test_x.py"},
            }
        ],
        "stop_reason": "tool_use",
    }
    t3_req = {
        "method": "POST",
        "path": "/v1/messages",
        "headers": {},
        "body": {
            "model": "claude-test",
            "messages": [
                {"role": "user", "content": "fix the flaky test"},
                {"role": "assistant", "content": t1_resp["content"]},
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": "toolu_c1",
                            "content": "1 failed",
                        }
                    ],
                },
                {"role": "assistant", "content": t2_resp["content"]},
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": "toolu_c2",
                            "content": "1 passed",
                        }
                    ],
                },
            ],
        },
    }
    t3_resp = {
        "id": "msg_c3",
        "content": [{"type": "text", "text": "fixed: narrowed to test_x.py"}],
        "stop_reason": "end_turn",
    }
    return ProtocolSession(
        agent="claude",
        turns=[
            Turn(request=t1_req, response=t1_resp),
            Turn(request=t2_req, response=t2_resp),
            Turn(request=t3_req, response=t3_resp),
        ],
    )


def simple_echo_session() -> ProtocolSession:
    """Minimal one-turn prompt (reproducibility baseline)."""
    req = {
        "method": "POST",
        "path": "/v1/messages",
        "headers": {},
        "body": {
            "model": "claude-test",
            "messages": [{"role": "user", "content": "hi"}],
        },
    }
    resp = {
        "id": "msg_s1",
        "content": [{"type": "text", "text": "hello"}],
        "stop_reason": "end_turn",
    }
    return ProtocolSession(agent="claude", turns=[Turn(request=req, response=resp)])


def openai_chat_tool_chain_session() -> ProtocolSession:
    """OpenAI Chat Completions multi-turn with tool_calls."""
    t1_req = {
        "method": "POST",
        "path": "/v1/chat/completions",
        "headers": {},
        "body": {
            "model": "gpt-test",
            "messages": [{"role": "user", "content": "run pwd"}],
            "tools": [{"type": "function", "function": {"name": "Bash"}}],
        },
    }
    t1_resp = {
        "id": "chat_1",
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "tool_calls": [
                        {
                            "id": "call_1",
                            "type": "function",
                            "function": {
                                "name": "Bash",
                                "arguments": '{"command":"pwd"}',
                            },
                        }
                    ],
                },
                "finish_reason": "tool_calls",
            }
        ],
    }
    t2_req = {
        "method": "POST",
        "path": "/v1/chat/completions",
        "headers": {},
        "body": {
            "model": "gpt-test",
            "messages": [
                {"role": "user", "content": "run pwd"},
                t1_resp["choices"][0]["message"],
                {"role": "tool", "tool_call_id": "call_1", "content": "/tmp"},
            ],
        },
    }
    t2_resp = {
        "id": "chat_2",
        "choices": [
            {
                "message": {"role": "assistant", "content": "cwd is /tmp"},
                "finish_reason": "stop",
            }
        ],
    }
    return ProtocolSession(
        agent="codex",
        turns=[
            Turn(request=t1_req, response=t1_resp),
            Turn(request=t2_req, response=t2_resp),
        ],
    )


def codex_responses_session() -> ProtocolSession:
    """Two-turn OpenAI Responses with previous_response_id."""
    turn1_req = {
        "method": "POST",
        "path": "/v1/responses",
        "headers": {},
        "body": {
            "model": "codex-test",
            "input": [{"role": "user", "content": "hello"}],
        },
    }
    turn1_resp = {
        "id": "resp_1",
        "output": [{"type": "message", "content": [{"type": "output_text", "text": "hi"}]}],
    }
    turn2_req = {
        "method": "POST",
        "path": "/v1/responses",
        "headers": {},
        "body": {
            "model": "codex-test",
            "previous_response_id": "resp_1",
            "input": [{"role": "user", "content": "again"}],
        },
    }
    turn2_resp = {
        "id": "resp_2",
        "output": [{"type": "message", "content": [{"type": "output_text", "text": "ok"}]}],
    }
    return ProtocolSession(
        agent="codex",
        turns=[
            Turn(request=turn1_req, response=turn1_resp),
            Turn(request=turn2_req, response=turn2_resp),
        ],
    )
