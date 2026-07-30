"""C9 agent parity harness tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from llmreplay.core.match import match_key, sort_tool_blocks
from llmreplay.parity.harness import (
    assert_previous_response_id,
    assert_tool_ids_stable,
    record_session,
    replay_session,
)
from llmreplay.parity.sessions import claude_tool_session, codex_responses_session
from llmreplay.store.cassette import CassetteStore


@pytest.mark.contract
@pytest.mark.asyncio
async def test_claude_multi_turn_record_replay(tmp_path: Path) -> None:
    session = claude_tool_session()
    assert_tool_ids_stable(session)
    cassette = tmp_path / "claude"
    await record_session(session, cassette)
    assert len(CassetteStore(cassette).load_manifest().transactions) == 2
    responses = await replay_session(session, cassette)
    assert responses[0]["content"][0]["id"] == "toolu_1"
    assert responses[1]["content"][0]["text"] == "two files"


@pytest.mark.contract
@pytest.mark.asyncio
async def test_codex_previous_response_id_record_replay(tmp_path: Path) -> None:
    session = codex_responses_session()
    assert_previous_response_id(session)
    cassette = tmp_path / "codex"
    await record_session(session, cassette)
    responses = await replay_session(session, cassette)
    assert responses[0]["id"] == "resp_1"
    assert responses[1]["id"] == "resp_2"


@pytest.mark.unit
def test_thinking_excluded_from_match_key() -> None:
    base = {
        "method": "POST",
        "path": "/v1/messages",
        "headers": {},
        "body": {
            "model": "m",
            "messages": [
                {
                    "role": "assistant",
                    "content": [
                        {"type": "thinking", "thinking": "secret chain"},
                        {"type": "text", "text": "hi"},
                    ],
                }
            ],
        },
    }
    other = {
        "method": "POST",
        "path": "/v1/messages",
        "headers": {},
        "body": {
            "model": "m",
            "messages": [
                {
                    "role": "assistant",
                    "content": [
                        {"type": "thinking", "thinking": "different"},
                        {"type": "text", "text": "hi"},
                    ],
                }
            ],
        },
    }
    assert match_key(base) == match_key(other)


@pytest.mark.unit
def test_parallel_tool_use_sort_stable() -> None:
    msg = {
        "role": "assistant",
        "content": [
            {"type": "tool_use", "id": "b", "name": "Z", "input": {"x": 1}},
            {"type": "tool_use", "id": "a", "name": "A", "input": {"x": 1}},
        ],
    }
    sorted_msg = sort_tool_blocks(msg)
    names = [b["name"] for b in sorted_msg["content"] if b["type"] == "tool_use"]
    assert names == ["A", "Z"]
