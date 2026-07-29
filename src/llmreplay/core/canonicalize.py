"""RFC 8785 JCS canonicalization helpers."""

from __future__ import annotations

from typing import Any

import rfc8785


def dumps_jcs(value: Any) -> bytes:
    """Return RFC 8785 canonical JSON bytes for a JSON-compatible value."""
    return rfc8785.dumps(value)


def dumps_jcs_str(value: Any) -> str:
    """UTF-8 string form of JCS bytes."""
    return dumps_jcs(value).decode("utf-8")
