"""llmreplay demo — one-terminal, zero-config start→end showcase.

Starts a stub upstream, runs record + replay through ``llmreplay run``'s
proxy lifecycle, and prints a clear success path. No CCR, no free keys,
no second terminal.
"""

from __future__ import annotations

import json
import shutil
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

import uvicorn
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from llmreplay.cli.env_helpers import DEFAULT_LOCAL_HMAC, ensure_local_hmac
from llmreplay.cli.run_cmd import run_with_proxy
from llmreplay.proxy.config import ProxyConfig
from llmreplay.store.cassette import CassetteStore

_DEMO_PROMPT = "say hello in one sentence"
_DEMO_REPLY = "hello from the cassette"


def _wait_http_ready(url: str, *, timeout: float = 5.0) -> bool:
    """True when *url* accepts an HTTP request (TCP listen alone is not enough)."""
    deadline = time.monotonic() + timeout
    payload = json.dumps({"model": "demo-stub", "max_tokens": 1, "messages": []}).encode()
    while time.monotonic() < deadline:
        try:
            req = urllib.request.Request(
                url,
                data=payload,
                headers={"content-type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=0.5) as resp:
                if 200 <= resp.status < 500:
                    return True
        except urllib.error.HTTPError as exc:
            # App is up enough to return an HTTP status.
            if exc.code < 500:
                return True
        except (urllib.error.URLError, TimeoutError, OSError):
            pass
        time.sleep(0.05)
    return False


def _start_stub_upstream() -> tuple[uvicorn.Server, threading.Thread, int]:
    """Tiny Anthropic-shaped stub; binds ``port=0`` then returns the real port."""

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
    config = uvicorn.Config(app, host="127.0.0.1", port=0, log_level="error")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    # Discover the OS-assigned port, then wait until HTTP is actually served.
    deadline = time.monotonic() + 5.0
    port = 0
    while time.monotonic() < deadline and port == 0:
        for http_server in getattr(server, "servers", []) or []:
            for sock in getattr(http_server, "sockets", []) or []:
                addr = sock.getsockname()
                if isinstance(addr, tuple) and len(addr) >= 2:
                    port = int(addr[1])
                    break
            if port:
                break
        if not port:
            time.sleep(0.01)

    if not port:
        server.should_exit = True
        thread.join(timeout=1)
        raise RuntimeError("demo stub gateway did not bind a port")

    ready_url = f"http://127.0.0.1:{port}/v1/messages"
    if _wait_http_ready(ready_url):
        return server, thread, port
    server.should_exit = True
    thread.join(timeout=1)
    raise RuntimeError(f"demo stub gateway did not become ready on 127.0.0.1:{port}")


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
    # Fresh cassette each run so re-demo stays a clean 1-transaction showcase.
    if cassette.exists():
        shutil.rmtree(cassette)
    cassette.mkdir(parents=True, exist_ok=True)

    cass_disp = str(cassette)

    try:
        stub_server, stub_thread, stub_port = _start_stub_upstream()
    except RuntimeError as exc:
        print(f"✗ {exc}")
        return 9

    upstream = f"http://127.0.0.1:{stub_port}"

    print("")
    print("╔══════════════════════════════════════════════════════════╗")
    print("║  LLMReplay demo — one terminal, no API keys, no CCR      ║")
    print("╚══════════════════════════════════════════════════════════╝")
    print("")
    print(f"1) HMAC          LLMREPLAY_HMAC_KEY={hmac}")
    print(f"2) Stub gateway  {upstream}  (fake LLM)")
    print("3) Proxy         ephemeral (port=0, assigned on bind)")
    print(f"4) Cassette      {cass_disp}")
    print("")

    try:
        print("▶ RECORD  (proxy starts → child agent → cassette written)")
        code = 1
        for attempt in range(2):
            record_cfg = ProxyConfig(
                mode="record",
                cassette_dir=cassette,
                upstream_base=upstream,
                host="127.0.0.1",
                port=0,
                profile="local",
            )
            code = run_with_proxy(config=record_cfg, command=_agent_command())
            if code == 0:
                break
            # Rare under heavy local port churn (many uvicorn threads): retry once
            # if the stub is still healthy.
            if attempt == 0 and _wait_http_ready(f"{upstream}/v1/messages", timeout=1.0):
                print("  … retrying record (transient upstream/proxy race)")
                continue
            print(f"✗ record failed (exit {code})")
            return code
        print("  ✓ cassette recorded")
        print("")

        print("▶ REPLAY  (offline — stub not needed; match from cassette)")
        replay_cfg = ProxyConfig(
            mode="replay",
            cassette_dir=cassette,
            host="127.0.0.1",
            port=0,
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
        print(f"▶ CHECK   {n} transaction(s) in {cass_disp}")

        print("")
        print("✓ Done. Start→end in one terminal.")
        print("")
        print("Next — same shape with a real agent (still one terminal):")
        print(f"  # llmreplay run auto-sets LLMREPLAY_HMAC_KEY={DEFAULT_LOCAL_HMAC} if unset")
        print("  # keep your ANTHROPIC_API_KEY in the environment")
        print(f"  llmreplay run --mode record --cassette {cass_disp} \\")
        print("    --upstream https://api.anthropic.com -- claude --print 'say hi'")
        print(f"  llmreplay run --mode replay --cassette {cass_disp} \\")
        print("    -- claude --print 'say hi'")
        print("")
        return 0
    finally:
        stub_server.should_exit = True
        stub_thread.join(timeout=3)
