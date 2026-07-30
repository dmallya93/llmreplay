"""pytest plugin for LLMReplay — hermetic agent replay fixtures.

Registers a ``llmreplay_cassette`` fixture and a ``@pytest.mark.llmreplay``
marker for declarative cassette replay in consumer test suites.

Entry point registered via ``[project.entry-points.pytest11]`` in pyproject.toml.

.. note::

   All llmreplay imports are deferred to fixture execution time so that this
   module can be loaded by pytest's plugin machinery without triggering early
   imports of ``llmreplay.core``, ``llmreplay.scrub``, etc.  Those early
   imports cause ``coverage`` to report "module previously imported, but not
   measured" and drop coverage to ~76% (the gate requires ≥95%).
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import httpx
import pytest


def pytest_configure(config: Any) -> None:
    """Register the ``llmreplay`` marker."""
    config.addinivalue_line(
        "markers",
        "llmreplay(cassette, profile, allow_live): replay from an LLMReplay cassette",
    )


@pytest.fixture
async def llmreplay_cassette(request: pytest.FixtureRequest) -> AsyncIterator[httpx.AsyncClient]:
    """Provide an ``httpx.AsyncClient`` wired to a ``ReplayTransport``.

    Usage::

        @pytest.mark.llmreplay(cassette=".llmreplay/cassette", profile="ci")
        async def test_agent_turn(llmreplay_cassette):
            resp = await llmreplay_cassette.post("/v1/messages", json={...})
            assert resp.status_code == 200
    """
    from llmreplay.transport import (
        ReplayTransport,  # noqa: PLC0415 — deferred to avoid early-import coverage penalty
    )

    marker = request.node.get_closest_marker("llmreplay")
    if marker is None:
        raise pytest.UsageError(
            "llmreplay_cassette fixture requires @pytest.mark.llmreplay(cassette=...)"
        )
    cassette_dir = Path(marker.kwargs.get("cassette", ".llmreplay/cassette"))
    profile = marker.kwargs.get("profile", "ci")
    allow_live = marker.kwargs.get("allow_live", False)

    transport = ReplayTransport(
        cassette_dir=cassette_dir,
        profile=profile,
        allow_live=allow_live,
    )
    client = httpx.AsyncClient(transport=transport, base_url="http://llmreplay")
    yield client
    await client.aclose()
