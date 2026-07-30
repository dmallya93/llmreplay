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
