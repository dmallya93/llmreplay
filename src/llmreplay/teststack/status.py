"""Probe Ollama / CCR / proxy health for free-mode (SPEC S8)."""

from __future__ import annotations

import httpx

from llmreplay.teststack.models import (
    ComponentStatus,
    FreeStackConfig,
    FreeStackStatus,
)


def _probe(url: str, *, timeout: float = 1.0) -> tuple[bool, str]:
    try:
        with httpx.Client(timeout=timeout) as client:
            resp = client.get(url)
        if resp.status_code < 500:
            return True, f"HTTP {resp.status_code}"
        return False, f"HTTP {resp.status_code}"
    except httpx.HTTPError as exc:
        return False, str(exc) or exc.__class__.__name__


def status(config: FreeStackConfig | None = None) -> FreeStackStatus:
    cfg = config or FreeStackConfig()
    components: list[ComponentStatus] = []

    ollama_ok, ollama_detail = _probe(f"{cfg.ollama_host.rstrip('/')}/api/tags")
    components.append(
        ComponentStatus(
            name="ollama",
            ok=ollama_ok,
            detail=ollama_detail,
            url=cfg.ollama_host,
        )
    )

    ccr_ok, ccr_detail = _probe(f"{cfg.ccr_host.rstrip('/')}/")
    components.append(
        ComponentStatus(
            name="ccr",
            ok=ccr_ok,
            detail=ccr_detail,
            url=cfg.ccr_host,
        )
    )

    proxy_ok, proxy_detail = _probe(f"{cfg.proxy_host.rstrip('/')}/healthz")
    components.append(
        ComponentStatus(
            name="proxy",
            ok=proxy_ok,
            detail=proxy_detail,
            url=cfg.proxy_host,
        )
    )

    # Free path requires Ollama; CCR may be degraded if Ollama speaks Anthropic natively later.
    healthy = ollama_ok
    degraded = ollama_ok and not ccr_ok
    if healthy and not degraded:
        nxt = "Stack healthy — create a free key and point the agent at the proxy."
    elif healthy and degraded:
        nxt = (
            "Ollama up but CCR down — start CCR or point proxy --upstream at Ollama "
            "OpenAI-compatible /v1 (degraded mode)."
        )
    else:
        nxt = (
            "Test-stack unhealthy (exit 4) — install/start Ollama, then `llmreplay test-stack up`."
        )
    return FreeStackStatus(
        healthy=healthy,
        components=components,
        degraded=degraded,
        next=nxt,
    )
