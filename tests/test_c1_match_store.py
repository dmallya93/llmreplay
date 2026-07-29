"""C1 unit + property tests for match/hash and cassette store."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from hypothesis import given
from hypothesis import strategies as st

from llmreplay.core.canonicalize import dumps_jcs
from llmreplay.core.match import match_key, sort_tool_blocks, static_projection
from llmreplay.store.cassette import CassetteStore


@pytest.mark.unit
def test_ignore_fields_do_not_change_match_key() -> None:
    base = {"model": "m", "messages": [{"role": "user", "content": "hi"}]}
    with_usage = {**base, "usage": {"input_tokens": 9}, "latency_ms": 12}
    assert match_key(base) == match_key(with_usage)


@pytest.mark.unit
def test_static_field_change_changes_key() -> None:
    a = {"model": "m1", "messages": []}
    b = {"model": "m2", "messages": []}
    assert match_key(a) != match_key(b)


@pytest.mark.unit
def test_thinking_blocks_excluded_from_hash() -> None:
    without = {
        "messages": [
            {"role": "assistant", "content": [{"type": "text", "text": "ok"}]},
        ]
    }
    with_thinking = {
        "messages": [
            {
                "role": "assistant",
                "content": [
                    {"type": "thinking", "thinking": "secret chain"},
                    {"type": "text", "text": "ok"},
                ],
            }
        ]
    }
    assert match_key(without) == match_key(with_thinking)


@pytest.mark.unit
def test_parallel_tool_result_sort_stable() -> None:
    msg = {
        "role": "user",
        "content": [
            {"type": "tool_result", "tool_use_id": "u2", "content": "b"},
            {"type": "tool_result", "tool_use_id": "u1", "content": "a"},
        ],
    }
    sorted_msg = sort_tool_blocks(msg)
    ids = [b["tool_use_id"] for b in sorted_msg["content"]]
    assert ids == ["u1", "u2"]


@pytest.mark.unit
def test_reasoning_blocks_excluded() -> None:
    a = {"messages": [{"role": "assistant", "content": [{"type": "text", "text": "x"}]}]}
    b = {
        "messages": [
            {
                "role": "assistant",
                "content": [
                    {"type": "reasoning", "text": "chain"},
                    {"type": "text", "text": "x"},
                ],
            }
        ]
    }
    assert match_key(a) == match_key(b)


@pytest.mark.unit
def test_cassette_atomic_manifest(tmp_path: Path) -> None:
    store = CassetteStore(tmp_path / "cass")
    tx = store.append_transaction(
        request={"model": "m"},
        response={"content": "hi"},
        static_hash=match_key({"model": "m"}),
    )
    manifest = store.load_manifest()
    assert manifest.schema_version == 1
    assert len(manifest.transactions) == 1
    assert manifest.transactions[0].id == tx
    assert (store.root / "requests" / f"{tx}.json").is_file()
    # schema-required keys present
    raw = json.loads(store.manifest_path.read_text(encoding="utf-8"))
    assert {"schema_version", "cassette_id", "transactions"} <= raw.keys()


@given(
    st.dictionaries(
        st.sampled_from(["model", "stream", "foo"]),
        st.one_of(
            st.text(max_size=20),
            st.integers(min_value=-(2**53) + 1, max_value=(2**53) - 1),
            st.booleans(),
        ),
        max_size=5,
    )
)
@pytest.mark.unit
def test_jcs_idempotent_bytes(data: dict) -> None:
    once = dumps_jcs(data)
    twice = dumps_jcs(json.loads(once.decode("utf-8")))
    assert once == twice


@pytest.mark.unit
def test_static_projection_drops_ignore() -> None:
    event = {"model": "m", "usage": {"x": 1}, "latency_ms": 3}
    proj = static_projection(event)
    assert "usage" not in proj
    assert "latency_ms" not in proj
    assert proj["model"] == "m"
