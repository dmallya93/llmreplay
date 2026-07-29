"""Proxy route allowlist (SPEC S5)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Route:
    method: str
    path: str


ALLOWED_ROUTES: frozenset[tuple[str, str]] = frozenset(
    {
        ("POST", "/v1/messages"),
        ("POST", "/v1/chat/completions"),
        ("POST", "/v1/responses"),
        ("GET", "/v1/models"),
        ("GET", "/healthz"),
    }
)

ROUTE_DENIED_BODY = {
    "error": {
        "type": "llmreplay_route_denied",
        "message": "404 LLMREPLAY_ROUTE_DENIED — path not in allowlist",
    }
}


def is_allowed(method: str, path: str) -> bool:
    return (method.upper(), path) in ALLOWED_ROUTES
