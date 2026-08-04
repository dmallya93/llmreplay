"""Doctor checks (`llmreplay doctor`)."""

from __future__ import annotations

import os
import socket
import sys
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from llmreplay import __version__
from llmreplay.proxy.routes import is_allowed
from llmreplay.teststack.status import status as stack_status


class DoctorCheck(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    ok: bool
    detail: str
    next: str | None = None


class DoctorReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    llmreplay_version: str
    python: str
    cwd: str
    checks: list[DoctorCheck] = Field(default_factory=list)
    ok: bool = True
    next: str = ""


def _port_free(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.5)
        return sock.connect_ex((host, port)) != 0


def run_doctor(
    *,
    cassette_dir: Path | None = None,
    proxy_host: str = "127.0.0.1",
    proxy_port: int = 7432,
) -> DoctorReport:
    checks: list[DoctorCheck] = []
    checks.append(
        DoctorCheck(
            id="cli_installed",
            ok=True,
            detail="llmreplay importable",
        )
    )
    checks.append(
        DoctorCheck(
            id="proxy_routes",
            ok=is_allowed("GET", "/healthz"),
            detail="allowlist loaded (GET /healthz)",
            next=None if is_allowed("GET", "/healthz") else "Reinstall llmreplay package",
        )
    )
    port_ok = _port_free(proxy_host, proxy_port)
    checks.append(
        DoctorCheck(
            id="proxy_port",
            ok=port_ok,
            detail=f"{proxy_host}:{proxy_port} {'available' if port_ok else 'in use'}",
            next=None if port_ok else f"Free the port or pass --port (default {proxy_port})",
        )
    )
    cassette = cassette_dir or Path(".llmreplay/cassette")
    cassette_parent = cassette if cassette.is_dir() else cassette.parent
    writable = True
    try:
        cassette_parent.mkdir(parents=True, exist_ok=True)
        probe = cassette_parent / ".llmreplay-doctor-write"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
    except OSError as exc:
        writable = False
        checks.append(
            DoctorCheck(
                id="cassette_writable",
                ok=False,
                detail=str(exc),
                next="Fix permissions on the cassette directory",
            )
        )
    if writable:
        checks.append(
            DoctorCheck(
                id="cassette_writable",
                ok=True,
                detail=f"can write under {cassette_parent}",
            )
        )

    anthropic = os.environ.get("ANTHROPIC_BASE_URL")
    openai = os.environ.get("OPENAI_BASE_URL")
    agent_ok = bool(anthropic or openai)
    checks.append(
        DoctorCheck(
            id="agent_env",
            ok=True,
            detail=(
                f"ANTHROPIC_BASE_URL={anthropic!r} OPENAI_BASE_URL={openai!r}"
                if agent_ok
                else "agent base URLs unset (set when wiring Claude Code / Codex)"
            ),
            next=(
                None
                if agent_ok
                else "Point the agent at the llmreplay proxy (see docs/integrations)"
            ),
        )
    )
    hmac_set = bool(os.environ.get("LLMREPLAY_HMAC_KEY"))
    checks.append(
        DoctorCheck(
            id="hmac_key",
            ok=True,
            detail=(
                "LLMREPLAY_HMAC_KEY set"
                if hmac_set
                else "LLMREPLAY_HMAC_KEY unset (ephemeral local key; set for CI)"
            ),
            next=(
                None
                if hmac_set
                else "Run `llmreplay demo` or export LLMREPLAY_HMAC_KEY=dev-local-hmac"
            ),
        )
    )
    stack = stack_status()
    checks.append(
        DoctorCheck(
            id="test_stack",
            ok=stack.healthy,
            detail=(
                "Ollama reachable"
                if stack.healthy
                else "CCR+Ollama stack unhealthy (optional until free-mode use)"
            ),
            next=stack.next,
        )
    )

    soft = {"test_stack", "hmac_key", "agent_env"}
    failing = [c for c in checks if not c.ok and c.id not in soft]
    ok = not failing
    next_action = (
        failing[0].next or failing[0].detail
        if failing
        else "Run record/replay. Free stack: `llmreplay test-stack status`."
    )
    return DoctorReport(
        llmreplay_version=__version__,
        python=sys.version.split()[0],
        cwd=str(Path.cwd()),
        checks=checks,
        ok=ok,
        next=next_action,
    )


def doctor_as_dict(report: DoctorReport) -> dict[str, Any]:
    return report.model_dump(mode="json")
