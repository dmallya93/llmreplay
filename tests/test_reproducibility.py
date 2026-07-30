"""Reproducibility: multi-tool chains, parallel tools, complex→simple, N-fold replay."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import httpx
import pytest

from llmreplay.core.match import match_key
from llmreplay.parity.harness import record_session, replay_session
from llmreplay.parity.sessions import (
    claude_parallel_tools_session,
    claude_tool_chain_session,
    claude_tool_session,
    codex_responses_session,
    openai_chat_tool_chain_session,
    openai_parallel_tools_session,
    simple_echo_session,
)
from llmreplay.proxy.app import create_app
from llmreplay.proxy.normalize import normalize_request_event
from llmreplay.scrub.engine import Scrubber
from llmreplay.store.cassette import CassetteStore

REPLAY_ROUNDS = 10


async def _replay_n_times(session, cassette: Path, rounds: int = REPLAY_ROUNDS) -> list:
    """Replay the same session many times; return list of response lists."""
    results = []
    for _ in range(rounds):
        results.append(await replay_session(session, cassette))
    return results


def _assert_identical_replays(runs: list) -> None:
    assert runs, "no runs"
    first = runs[0]
    for i, run in enumerate(runs[1:], start=2):
        assert run == first, f"replay round {i} diverged from round 1"


@pytest.mark.contract
@pytest.mark.asyncio
async def test_simple_prompt_reproducible(tmp_path: Path) -> None:
    session = simple_echo_session()
    cass = tmp_path / "simple"
    await record_session(session, cass)
    runs = await _replay_n_times(session, cass)
    _assert_identical_replays(runs)
    assert runs[0][0]["content"][0]["text"] == "hello"


@pytest.mark.contract
@pytest.mark.asyncio
async def test_basic_tool_turn_reproducible(tmp_path: Path) -> None:
    session = claude_tool_session()
    cass = tmp_path / "basic-tool"
    await record_session(session, cass)
    runs = await _replay_n_times(session, cass)
    _assert_identical_replays(runs)
    assert runs[0][0]["content"][0]["id"] == "toolu_1"
    assert runs[0][1]["content"][0]["text"] == "two files"


@pytest.mark.contract
@pytest.mark.asyncio
async def test_parallel_tools_and_reordered_results_reproducible(tmp_path: Path) -> None:
    session = claude_parallel_tools_session()
    cass = tmp_path / "parallel"
    await record_session(session, cass)
    runs = await _replay_n_times(session, cass)
    _assert_identical_replays(runs)
    assert {b["id"] for b in runs[0][0]["content"]} == {"toolu_read", "toolu_bash"}
    assert "cwd=/workspace" in runs[0][1]["content"][0]["text"]

    # Same follow-up with tool_result blocks swapped → same match / same response.
    swapped = deepcopy(session)
    content = swapped.turns[1].request["body"]["messages"][2]["content"]
    swapped.turns[1].request["body"]["messages"][2]["content"] = list(reversed(content))
    again = await replay_session(swapped, cass)
    assert again == runs[0]


@pytest.mark.contract
@pytest.mark.asyncio
async def test_three_turn_tool_chain_reproducible(tmp_path: Path) -> None:
    session = claude_tool_chain_session()
    cass = tmp_path / "chain"
    await record_session(session, cass)
    assert len(CassetteStore(cass).load_manifest().transactions) == 3
    runs = await _replay_n_times(session, cass)
    _assert_identical_replays(runs)
    assert runs[0][2]["content"][0]["text"].startswith("fixed:")


@pytest.mark.contract
@pytest.mark.asyncio
async def test_openai_chat_tool_chain_reproducible(tmp_path: Path) -> None:
    session = openai_chat_tool_chain_session()
    cass = tmp_path / "openai-chain"
    await record_session(session, cass)
    runs = await _replay_n_times(session, cass)
    _assert_identical_replays(runs)
    assert runs[0][1]["choices"][0]["message"]["content"] == "cwd is /tmp"


@pytest.mark.contract
@pytest.mark.asyncio
async def test_complex_and_simple_sessions_independent(tmp_path: Path) -> None:
    """Complex chain and simple echo share a process but not a cassette — both stable."""
    complex_s = claude_tool_chain_session()
    simple_s = simple_echo_session()
    c_complex = tmp_path / "cx"
    c_simple = tmp_path / "sx"
    await record_session(complex_s, c_complex)
    await record_session(simple_s, c_simple)
    for _ in range(5):
        cr = await replay_session(complex_s, c_complex)
        sr = await replay_session(simple_s, c_simple)
        assert cr[-1]["content"][0]["text"].startswith("fixed:")
        assert sr[0]["content"][0]["text"] == "hello"


@pytest.mark.unit
def test_body_messages_parallel_tool_order_does_not_change_match_key() -> None:
    """Proxy events nest messages under body — sorting must apply there."""
    tools_a = [
        {"type": "tool_use", "id": "b", "name": "Z", "input": {"x": 1}},
        {"type": "tool_use", "id": "a", "name": "A", "input": {"x": 1}},
    ]
    tools_b = list(reversed(tools_a))
    event_a = normalize_request_event(
        method="POST",
        path="/v1/messages",
        headers={"authorization": "Bearer secret", "x-request-id": "1"},
        body={"model": "m", "messages": [{"role": "assistant", "content": tools_a}]},
    )
    event_b = normalize_request_event(
        method="POST",
        path="/v1/messages",
        headers={"authorization": "Bearer other", "x-request-id": "2"},
        body={"model": "m", "messages": [{"role": "assistant", "content": tools_b}]},
    )
    assert match_key(event_a) == match_key(event_b)


@pytest.mark.unit
def test_ignore_noise_same_as_clean_request() -> None:
    clean = normalize_request_event(
        method="POST",
        path="/v1/messages",
        headers={},
        body={"model": "m", "messages": [{"role": "user", "content": "hi"}]},
    )
    noisy = normalize_request_event(
        method="POST",
        path="/v1/messages",
        headers={"x-request-id": "abc", "date": "Wed"},
        body={
            "model": "m",
            "messages": [{"role": "user", "content": "hi"}],
            "usage": {"input_tokens": 99},
            "stream": True,
            "latency_ms": 12,
        },
    )
    assert match_key(clean) == match_key(noisy)


@pytest.mark.contract
@pytest.mark.asyncio
async def test_stream_flag_does_not_break_reproducibility(tmp_path: Path) -> None:
    session = simple_echo_session()
    cass = tmp_path / "stream"
    await record_session(session, cass)
    scrubber = Scrubber(hmac_key=b"parity")
    app = create_app(mode="replay", cassette_dir=cass, scrubber=scrubber)
    transport = httpx.ASGITransport(app=app)
    bodies = []
    async with httpx.AsyncClient(transport=transport, base_url="http://proxy") as client:
        for stream in (False, True, False, True):
            body = deepcopy(session.turns[0].request["body"])
            body["stream"] = stream
            resp = await client.post("/v1/messages", json=body)
            assert resp.status_code == 200
            if stream:
                assert "text/event-stream" in resp.headers["content-type"]
                assert b"hello" in resp.content
            else:
                bodies.append(resp.json())
    assert bodies[0] == bodies[1]
    assert bodies[0]["content"][0]["text"] == "hello"


@pytest.mark.contract
@pytest.mark.asyncio
async def test_codex_responses_previous_id_reproducible(tmp_path: Path) -> None:
    session = codex_responses_session()
    cass = tmp_path / "codex-resp"
    await record_session(session, cass)
    runs = await _replay_n_times(session, cass)
    _assert_identical_replays(runs)
    assert runs[0][0]["id"] == "resp_1"
    assert runs[0][1]["id"] == "resp_2"
    assert session.turns[1].request["body"]["previous_response_id"] == "resp_1"


@pytest.mark.contract
@pytest.mark.asyncio
async def test_openai_parallel_tool_calls_reorder_n_fold(tmp_path: Path) -> None:
    session = openai_parallel_tools_session()
    cass = tmp_path / "oai-par"
    await record_session(session, cass)
    runs = await _replay_n_times(session, cass)
    _assert_identical_replays(runs)
    swapped = deepcopy(session)
    msgs = swapped.turns[1].request["body"]["messages"]
    # swap the two tool role messages
    msgs[2], msgs[3] = msgs[3], msgs[2]
    again_runs = await _replay_n_times(swapped, cass, rounds=10)
    _assert_identical_replays(again_runs)
    assert again_runs[0] == runs[0]


@pytest.mark.contract
@pytest.mark.asyncio
async def test_streaming_three_turn_chain_n_fold(tmp_path: Path) -> None:
    session = claude_tool_chain_session()
    cass = tmp_path / "stream-chain"
    await record_session(session, cass)
    scrubber = Scrubber(hmac_key=b"parity")
    app = create_app(mode="replay", cassette_dir=cass, scrubber=scrubber)
    transport = httpx.ASGITransport(app=app)
    payloads: list[list[bytes]] = []
    async with httpx.AsyncClient(transport=transport, base_url="http://proxy") as client:
        for _ in range(REPLAY_ROUNDS):
            round_bytes: list[bytes] = []
            for turn in session.turns:
                body = deepcopy(turn.request["body"])
                body["stream"] = True
                resp = await client.post("/v1/messages", json=body)
                assert resp.status_code == 200
                assert "text/event-stream" in resp.headers["content-type"]
                round_bytes.append(resp.content)
            payloads.append(round_bytes)
    first = payloads[0]
    for i, run in enumerate(payloads[1:], start=2):
        assert run == first, f"SSE round {i} diverged"


@pytest.mark.contract
@pytest.mark.asyncio
async def test_parallel_wrong_tool_result_misses(tmp_path: Path) -> None:
    session = claude_parallel_tools_session()
    cass = tmp_path / "par-miss"
    await record_session(session, cass)
    bad = deepcopy(session)
    bad.turns[1].request["body"]["messages"][2]["content"][0]["content"] = "TAMPERED"
    scrubber = Scrubber(hmac_key=b"parity")
    app = create_app(mode="replay", cassette_dir=cass, scrubber=scrubber)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://proxy") as client:
        r0 = await client.post("/v1/messages", json=bad.turns[0].request["body"])
        assert r0.status_code == 200
        r1 = await client.post("/v1/messages", json=bad.turns[1].request["body"])
        assert r1.status_code == 409
        assert r1.json()["error"]["type"] == "llmreplay_miss"


@pytest.mark.unit
def test_openai_tool_role_order_does_not_change_match_key() -> None:
    base_msgs = [
        {"role": "user", "content": "x"},
        {"role": "assistant", "tool_calls": [{"id": "a"}, {"id": "b"}]},
        {"role": "tool", "tool_call_id": "b", "content": "2"},
        {"role": "tool", "tool_call_id": "a", "content": "1"},
    ]
    swapped = [
        base_msgs[0],
        base_msgs[1],
        base_msgs[3],
        base_msgs[2],
    ]
    a = normalize_request_event(
        method="POST",
        path="/v1/chat/completions",
        headers={},
        body={"model": "m", "messages": base_msgs},
    )
    b = normalize_request_event(
        method="POST",
        path="/v1/chat/completions",
        headers={},
        body={"model": "m", "messages": swapped},
    )
    assert match_key(a) == match_key(b)


@pytest.mark.contract
@pytest.mark.asyncio
async def test_upstream_error_returns_llmreplay_json(tmp_path: Path) -> None:
    class _Boom:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):  # noqa: ANN002, ARG002
            return None

        async def request(self, *args, **kwargs):  # noqa: ANN002, ARG002
            raise httpx.ConnectError("refused")

    app = create_app(
        mode="record",
        cassette_dir=tmp_path / "c",
        upstream_base="http://upstream",
        http_client_factory=_Boom,
    )
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://proxy") as client:
        resp = await client.post("/v1/messages", json={"model": "m"})
        assert resp.status_code == 503
        assert resp.json()["error"]["type"] == "llmreplay_upstream_error"
