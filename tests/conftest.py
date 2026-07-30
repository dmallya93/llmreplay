"""Shared pytest fixtures."""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _stable_hmac_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """CI/strict record requires LLMREPLAY_HMAC_KEY; keep hermetic tests stable."""
    monkeypatch.setenv("LLMREPLAY_HMAC_KEY", "llmreplay-test-hmac-key")
