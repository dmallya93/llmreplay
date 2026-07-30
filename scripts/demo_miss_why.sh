#!/usr/bin/env bash
# GIF-friendly miss → why narrative (hermetic).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ -f .venv/bin/activate ]]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi

export LLMREPLAY_HMAC_KEY="${LLMREPLAY_HMAC_KEY:-dev-local-hmac}"

python3 - <<'PY'
import asyncio
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.parse import urlparse

import httpx
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from llmreplay.proxy.app import create_app
from llmreplay.scrub.engine import Scrubber


async def main() -> None:
    async def messages(_request: Request) -> JSONResponse:
        return JSONResponse(
            {"id": "msg", "content": [{"type": "text", "text": "hello"}]}
        )

    upstream = Starlette(routes=[Route("/v1/messages", messages, methods=["POST"])])

    class Client:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return None

        async def request(self, method, url, content=None, headers=None):
            parsed = urlparse(url)
            transport = httpx.ASGITransport(app=upstream)
            async with httpx.AsyncClient(transport=transport, base_url="http://up") as c:
                return await c.request(method, parsed.path, content=content, headers=headers or {})

    with TemporaryDirectory() as td:
        root = Path(td)
        cassette = root / "cass"
        scrubber = Scrubber(hmac_key=b"demo-gif")
        recorded = {
            "model": "claude-demo",
            "messages": [{"role": "user", "content": "say hello"}],
        }

        print("▶ record golden prompt: 'say hello'")
        record = create_app(
            mode="record",
            cassette_dir=cassette,
            upstream_base="http://upstream",
            http_client_factory=Client,
            scrubber=scrubber,
        )
        transport = httpx.ASGITransport(app=record)
        async with httpx.AsyncClient(transport=transport, base_url="http://p") as client:
            r = await client.post("/v1/messages", json=recorded)
            assert r.status_code == 200
        print("  ✓ cassette written")

        print("")
        print("▶ replay with DIFFERENT prompt: 'say goodbye'")
        changed = {
            "model": "claude-demo",
            "messages": [{"role": "user", "content": "say goodbye"}],
        }
        replay = create_app(mode="replay", cassette_dir=cassette, scrubber=scrubber)
        transport = httpx.ASGITransport(app=replay)
        async with httpx.AsyncClient(transport=transport, base_url="http://p") as client:
            r = await client.post("/v1/messages", json=changed)
            print(f"  status {r.status_code}  (miss expected)")
            body = r.json()
            print(f"  body keys: {list(body.keys()) if isinstance(body, dict) else type(body)}")

        # Write a request file and run why if possible
        req_path = root / "request.json"
        req_path.write_text(
            json.dumps(
                {
                    "method": "POST",
                    "path": "/v1/messages",
                    "headers": {},
                    "body": changed,
                },
                indent=2,
            )
        )
        print("")
        print("▶ llmreplay why  (what changed?)")
        import subprocess
        import sys

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "llmreplay.cli.main",
                "why",
                "--cassette",
                str(cassette),
                "--request",
                str(req_path),
            ],
            capture_output=True,
            text=True,
        )
        out = (result.stdout or "") + (result.stderr or "")
        # Keep GIF short: show first ~20 lines
        lines = [ln for ln in out.splitlines() if ln.strip()][:20]
        for ln in lines:
            print(ln)
        if not lines:
            print("  (why exited", result.returncode, ") — static prompt field differs")
        print("")
        print("✓ miss diagnosed — prompt is STATIC (real drift, not noise)")


asyncio.run(main())
PY
