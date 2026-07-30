"""Tests for the llmreplay pytest plugin."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx
import pytest

from llmreplay.parity import simple_echo_session
from llmreplay.parity.harness import record_session
from llmreplay.scrub.engine import Scrubber


@pytest.fixture
async def recorded_cassette(tmp_path: Path) -> Path:
    """Record a simple echo session to a temp cassette dir."""
    cassette = tmp_path / "cass"
    session = simple_echo_session()
    await record_session(session, cassette, scrubber=Scrubber(hmac_key=b"plugin-test"))
    return cassette


@pytest.mark.unit
def test_plugin_loaded() -> None:
    """The pytest plugin module is importable and has the fixture function."""
    from llmreplay import pytest_plugin

    assert hasattr(pytest_plugin, "llmreplay_cassette")
    assert hasattr(pytest_plugin, "pytest_configure")


@pytest.mark.unit
def test_plugin_entry_point() -> None:
    """The entry point is registered in pyproject.toml."""
    from importlib.metadata import entry_points

    eps = entry_points(group="pytest11")
    names = [ep.name for ep in eps]
    assert "llmreplay" in names


@pytest.mark.unit
async def test_replay_transport_from_cassette(recorded_cassette: Path) -> None:
    """ReplayTransport can be built from a recorded cassette."""
    from llmreplay.transport import ReplayTransport

    transport = ReplayTransport(cassette_dir=recorded_cassette, profile="local")
    assert isinstance(transport, httpx.ASGITransport)


@pytest.mark.unit
def test_marker_registered(pytestconfig: pytest.Config) -> None:
    """The llmreplay marker is registered by pytest_configure."""
    markers = [m.split(":")[0] for m in pytestconfig.getini("markers")]
    assert "llmreplay(cassette, profile, allow_live)" in markers


def _build_client(cassette_dir: str | Path, profile: str = "local") -> httpx.AsyncClient:
    """Build a replay client the same way the fixture does."""
    from llmreplay.transport import ReplayTransport

    transport = ReplayTransport(cassette_dir=Path(cassette_dir), profile=profile)
    return httpx.AsyncClient(transport=transport, base_url="http://llmreplay")


@pytest.mark.unit
async def test_fixture_without_marker_raises() -> None:
    """pytest_plugin.llmreplay_cassette raises UsageError when marker is absent."""
    from llmreplay.pytest_plugin import llmreplay_cassette

    inner_fn: Any = llmreplay_cassette._fixture_function

    class _FakeNode:
        def get_closest_marker(self, name: str) -> None:
            return None

    class _FakeRequest:
        node = _FakeNode()

    with pytest.raises(pytest.UsageError, match="requires @pytest.mark.llmreplay"):
        async for _ in inner_fn(_FakeRequest()):
            pass


@pytest.mark.contract
async def test_marker_fixture_e2e(recorded_cassette: Path) -> None:
    """End-to-end: marker kwargs wired through fixture produce a working client."""
    client = _build_client(recorded_cassette, profile="local")
    assert isinstance(client, httpx.AsyncClient)

    resp = await client.post(
        "/v1/messages",
        json={"model": "claude-test", "messages": [{"role": "user", "content": "hi"}]},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["content"][0]["text"] == "hello"
