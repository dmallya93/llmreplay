"""Normalize inbound proxy requests for matching."""

from __future__ import annotations

from typing import Any

_DROP_HEADERS = frozenset(
    {
        "authorization",
        "x-api-key",
        "user-agent",
        "date",
        "x-request-id",
        "traceparent",
        "tracestate",
        "host",
        "content-length",
        "content-type",
        "accept",
        "accept-encoding",
        "connection",
    }
)


def normalize_request_event(
    *,
    method: str,
    path: str,
    headers: dict[str, str],
    body: Any,
) -> dict[str, Any]:
    """Build the event dict used for match_key (auth headers dropped)."""
    clean_headers = {k.lower(): v for k, v in headers.items() if k.lower() not in _DROP_HEADERS}
    event: dict[str, Any] = {
        "method": method.upper(),
        "path": path,
        "headers": clean_headers,
    }
    if body is not None:
        event["body"] = body
    return event
