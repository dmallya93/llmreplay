"""llmreplay run — one-process record / replay wrapper.

Starts the proxy in a background thread, injects ``ANTHROPIC_BASE_URL`` /
``OPENAI_BASE_URL`` into the child environment, runs the command, and
propagates the child exit code.
"""

from __future__ import annotations

import logging
import os
import signal
import socket
import subprocess
import threading
import time
from typing import Any

import httpx
import uvicorn

from llmreplay.proxy.app import create_app
from llmreplay.proxy.config import ProxyConfig

logger = logging.getLogger(__name__)

_HMAC_ENV_KEY = "LLMREPLAY_HMAC_KEY"
_KEYS_TO_STRIP = frozenset({_HMAC_ENV_KEY})


def _wait_for_healthz(
    base_url: str,
    server_thread: threading.Thread,
    *,
    timeout: float = 10.0,
    interval: float = 0.1,
) -> None:
    """Block until the proxy's ``/healthz`` returns 200 or timeout."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if not server_thread.is_alive():
            raise RuntimeError("proxy server thread died before becoming healthy")
        try:
            r = httpx.get(f"{base_url}/healthz", timeout=2.0)
            if r.status_code == 200:
                return
        except httpx.HTTPError:
            pass
        time.sleep(interval)
    raise RuntimeError(f"proxy did not become healthy at {base_url} within {timeout}s")


def free_port() -> int:
    """Return an ephemeral port the OS guarantees is available.

    Note: this is still a small TOCTOU window between close and a later bind.
    Prefer ``port=0`` with :func:`run_with_proxy` when possible.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _resolve_bound_port(server: uvicorn.Server, *, timeout: float = 5.0) -> int:
    """Return the TCP port uvicorn actually bound (supports ``port=0``)."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        for http_server in getattr(server, "servers", []) or []:
            for sock in getattr(http_server, "sockets", []) or []:
                addr = sock.getsockname()
                if isinstance(addr, tuple) and len(addr) >= 2:
                    return int(addr[1])
        time.sleep(0.01)
    raise RuntimeError("proxy server did not report a bound port")


def run_with_proxy(
    *,
    config: ProxyConfig,
    command: list[str],
    extra_env: dict[str, str] | None = None,
    http_client_factory: Any | None = None,
) -> int:
    """Start the ASGI proxy, run *command* as a subprocess, return its exit code.

    The proxy is torn down after the child exits regardless of outcome.
    Pass ``config.port == 0`` to let the OS assign an ephemeral port (avoids
    free_port TOCTOU races under parallel server startup).
    """
    config.cassette_dir.mkdir(parents=True, exist_ok=True)
    asgi_app = create_app(config=config, http_client_factory=http_client_factory)

    uvi_config = uvicorn.Config(
        asgi_app,
        host=config.host,
        port=config.port,
        log_level="warning",
    )
    server = uvicorn.Server(uvi_config)

    server_thread = threading.Thread(target=server.run, daemon=True)
    server_thread.start()

    try:
        port = config.port if config.port else _resolve_bound_port(server)
        # Keep config.port in sync so callers/tests can inspect the live port.
        if config.port == 0:
            object.__setattr__(config, "port", port)
        base_url = f"http://{config.host}:{port}"
        _wait_for_healthz(base_url, server_thread)

        child_env = {**os.environ, **(extra_env or {})}
        child_env["ANTHROPIC_BASE_URL"] = base_url
        child_env["OPENAI_BASE_URL"] = f"{base_url}/v1"
        child_env.setdefault("ANTHROPIC_API_KEY", "llmreplay-local")
        child_env.setdefault("OPENAI_API_KEY", "llmreplay-local")
        for key in _KEYS_TO_STRIP:
            child_env.pop(key, None)

        result = subprocess.run(command, env=child_env)  # noqa: S603
        return result.returncode
    except KeyboardInterrupt:
        return 128 + signal.SIGINT
    except OSError as exc:
        logger.error("failed to run command %s: %s", command, exc)
        return 9
    finally:
        server.should_exit = True
        server_thread.join(timeout=5)
        if server_thread.is_alive():
            logger.warning("proxy server thread did not stop within 5s")
