"""llmreplay demo — one-terminal, zero-config start→end showcase.

Starts a stub upstream, runs record + replay through ``llmreplay run``'s
proxy lifecycle, and prints a clear success path. No CCR, no free keys,
no second terminal.
"""

from __future__ import annotations

import logging
import socket
import sys
import threading
import time
from pathlib import Path

import uvicorn
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from llmreplay.cli.env_helpers import DEFAULT_LOCAL_HMAC, ensure_local_hmac
from llmreplay.cli.run_cmd import free_port, run_with_proxy
from llmreplay.proxy.config import ProxyConfig
from llmreplay.store.cassette import CassetteStore

logger = logging.getLogger(__name__)

_DEMO_PROMPT = "say hello in one sentence"
_DEMO_REPLY = "hello from the cassette"


def _start_stub_upstream(port: int) -> tuple[uvicorn.Server, threading.Thread]:
    """Tiny Anthropic-shaped stub that the proxy records against."""

    async def messages(_request: Request) -> JSONResponse:
        return JSONResponse(
            {
                "id": "msg_demo",
                "type": "message",
                "role": "assistant",
                "model": "demo-stub",
                "content": [{"type": "text", "text": _DEMO_REPLY}],
            }
        )

    app = Starlette(routes=[Route("/v1/messages", messages, methods=["POST"])])
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    for _ in range(50):
        with socket.socket() as s:
            if s.connect_ex(("127.0.0.1", port)) == 0:
                break
        time.sleep(0.05)
    return server, thread


def _agent_command() -> list[str]:
    """Child 'agent': one POST to ANTHROPIC_BASE_URL (set by run_with_proxy)."""
    # Keep as a single python -c so users see a real child process through the proxy.
    script = f"""
import json, os, urllib.request
base = os.environ["ANTHROPIC_BASE_URL"].rstrip("/")
req = urllib.request.Request(
    base + "/v1/messages",
    data=json.dumps({{
        "model": "demo-stub",
        "max_tokens": 64,
        "messages": [{{"role": "user", "content": {_DEMO_PROMPT!r}}}],
    }}).encode(),
    headers={{"content-type": "application/json", "x-api-key": "demo"}},
    method="POST",
)
with urllib.request.urlopen(req) as resp:
    body = json.load(resp)
text = body["content"][0]["text"]
print("agent ←", text)
assert text == {_DEMO_REPLY!r}, text
"""
    return [sys.executable, "-c", script]


def run_demo(*, cassette_dir: Path | None = None) -> int:
    """Execute the full hermetic demo. Returns process exit code."""
    hmac = ensure_local_hmac()
    cassette = cassette_dir or Path(".llmreplay/demo")
    stub_port = free_port()
    proxy_port = free_port()
    upstream = f"http://127.0.0.1:{stub_port}"

    print("")
    print("╔══════════════════════════════════════════════════════════╗")
    print("║  LLMReplay demo — one terminal, no API keys, no CCR      ║")
    print("╚══════════════════════════════════════════════════════════╝")
    print("")
    print(f"1) HMAC          LLMREPLAY_HMAC_KEY={hmac}")
    print(f"2) Stub gateway  {upstream}  (fake LLM)")
    print(f"3) Proxy         http://127.0.0.1:{proxy_port}")
    print(f"4) Cassette      {cassette}")
    print("")

    stub_server, stub_thread = _start_stub_upstream(stub_port)
    try:
        print("▶ RECORD  (proxy starts → child agent → cassette written)")
        record_cfg = ProxyConfig(
            mode="record",
            cassette_dir=cassette,
            upstream_base=upstream,
            host="127.0.0.1",
            port=proxy_port,
            profile="local",
        )
        code = run_with_proxy(config=record_cfg, command=_agent_command())
        if code != 0:
            print(f"✗ record failed (exit {code})")
            return code
        print("  ✓ cassette recorded")
        print("")

        print("▶ REPLAY  (offline — stub not needed; match from cassette)")
        # New proxy port for replay leg
        replay_port = free_port()
        replay_cfg = ProxyConfig(
            mode="replay",
            cassette_dir=cassette,
            host="127.0.0.1",
            port=replay_port,
            profile="local",
        )
        code = run_with_proxy(config=replay_cfg, command=_agent_command())
        if code != 0:
            print(f"✗ replay failed (exit {code})")
            return code
        print("  ✓ offline replay matched")
        print("")

        store = CassetteStore(cassette)
        n = len(store.load_manifest().transactions)
        print(f"▶ CHECK   {n} transaction(s) in {cassette}")

        print("")
        print("✓ Done. Start→end in one terminal.")
        print("")
        print("Next — same shape with a real agent (still one terminal):")
        print(f"  # llmreplay run auto-sets LLMREPLAY_HMAC_KEY={DEFAULT_LOCAL_HMAC} if unset")
        print("  # keep your ANTHROPIC_API_KEY in the environment")
        print("  llmreplay run --mode record --cassette .llmreplay/demo \\")
        print("    --upstream https://api.anthropic.com -- claude --print 'say hi'")
        print("  llmreplay run --mode replay --cassette .llmreplay/demo \\")
        print("    -- claude --print 'say hi'")
        print("")
        return 0
    finally:
        stub_server.should_exit = True
        stub_thread.join(timeout=3)
