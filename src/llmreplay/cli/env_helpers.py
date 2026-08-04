"""Shared CLI env helpers for one-terminal onboarding."""

from __future__ import annotations

import os

DEFAULT_LOCAL_HMAC = "dev-local-hmac"
HMAC_ENV_KEY = "LLMREPLAY_HMAC_KEY"


def ensure_local_hmac(*, announce: bool = False) -> str:
    """Return HMAC key, defaulting to a stable local value when unset.

    Avoids the common footgun where unset → random per-process key and
    cassette placeholders cannot be replayed later. CI/strict still require
    an explicit key at the proxy layer.
    """
    existing = os.environ.get(HMAC_ENV_KEY)
    if existing:
        return existing
    os.environ[HMAC_ENV_KEY] = DEFAULT_LOCAL_HMAC
    if announce:
        print(f"note: set {HMAC_ENV_KEY}={DEFAULT_LOCAL_HMAC} (stable local default)")
    return DEFAULT_LOCAL_HMAC
