#!/usr/bin/env bash
# Clean, GIF-friendly hermetic demo (no noisy test-stack JSON).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ -f .venv/bin/activate ]]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi

export LLMREPLAY_HMAC_KEY="${LLMREPLAY_HMAC_KEY:-dev-local-hmac}"

echo ""
echo "▶ llmreplay doctor"
llmreplay doctor
echo ""
echo "▶ hermetic record → replay (fake upstream, \$0)"
python3 - <<'PY'
import asyncio
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
            {"id": "msg", "content": [{"type": "text", "text": "hello from cassette"}]}
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
        cassette = Path(td) / "cass"
        scrubber = Scrubber(hmac_key=b"demo-gif")
        body = {"model": "claude-demo", "messages": [{"role": "user", "content": "hi"}]}

        print("  recording…")
        record = create_app(
            mode="record",
            cassette_dir=cassette,
            upstream_base="http://upstream",
            http_client_factory=Client,
            scrubber=scrubber,
        )
        transport = httpx.ASGITransport(app=record)
        async with httpx.AsyncClient(transport=transport, base_url="http://p") as client:
            r = await client.post("/v1/messages", json=body)
            assert r.status_code == 200

        print("  replaying offline…")
        replay = create_app(mode="replay", cassette_dir=cassette, scrubber=scrubber)
        transport = httpx.ASGITransport(app=replay)
        async with httpx.AsyncClient(transport=transport, base_url="http://p") as client:
            r = await client.post("/v1/messages", json=body)
            assert r.status_code == 200
            text = r.json()["content"][0]["text"]
            print(f"  ✓ match → {text!r}")
            print("  ✓ smoke ok: record→replay (fake upstream)")


asyncio.run(main())
PY
echo ""
echo "Done. Zero tokens burned."
