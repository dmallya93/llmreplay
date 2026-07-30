#!/usr/bin/env bash
# Hermetic-by-default smoke: fake upstream record→replay.
# Pass --ollama to require a live Ollama (exit 4 if unhealthy).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ -f .venv/bin/activate ]]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi

if command -v python3 >/dev/null 2>&1; then
  PY=python3
elif command -v python >/dev/null 2>&1; then
  PY=python
else
  echo "smoke: python3/python not found on PATH" >&2
  exit 1
fi

REQUIRE_OLLAMA=0
if [[ "${1:-}" == "--ollama" ]]; then
  REQUIRE_OLLAMA=1
fi

"$PY" - <<'PY'
from llmreplay.teststack.status import status
from llmreplay.core.exit_codes import ExitCode
import sys
st = status()
print(st.model_dump_json(indent=2))
if not st.healthy:
    print("test-stack unhealthy — continuing with fake upstream unless --ollama", file=sys.stderr)
    sys.exit(0)
sys.exit(0)
PY

if [[ "$REQUIRE_OLLAMA" -eq 1 ]]; then
  "$PY" -m llmreplay.cli.main test-stack status --json || {
    echo "Ollama required (--ollama) but unhealthy" >&2
    exit 4
  }
fi

"$PY" - <<'PY'
"""Inline hermetic record→replay (same as C4 harness)."""
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
        return JSONResponse({"id": "msg", "content": [{"type": "text", "text": "smoke-ok"}]})

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
        scrubber = Scrubber(hmac_key=b"smoke")
        record = create_app(
            mode="record",
            cassette_dir=cassette,
            upstream_base="http://upstream",
            http_client_factory=Client,
            scrubber=scrubber,
        )
        body = {"model": "m", "messages": [{"role": "user", "content": "hi"}]}
        transport = httpx.ASGITransport(app=record)
        async with httpx.AsyncClient(transport=transport, base_url="http://p") as client:
            r = await client.post("/v1/messages", json=body)
            assert r.status_code == 200, r.text
        replay = create_app(mode="replay", cassette_dir=cassette, scrubber=scrubber)
        transport = httpx.ASGITransport(app=replay)
        async with httpx.AsyncClient(transport=transport, base_url="http://p") as client:
            r = await client.post("/v1/messages", json=body)
            assert r.status_code == 200
            assert r.json()["content"][0]["text"] == "smoke-ok"
        print("smoke ok: record→replay (fake upstream)")


asyncio.run(main())
PY
