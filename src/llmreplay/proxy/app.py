"""Starlette ASGI proxy application."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Route

from llmreplay.core.match import match_key
from llmreplay.proxy.config import ProxyConfig, ProxyMode
from llmreplay.proxy.normalize import normalize_request_event
from llmreplay.proxy.routes import ROUTE_DENIED_BODY, is_allowed
from llmreplay.store.cassette import CassetteStore

Mode = ProxyMode

SYNTHETIC_MODELS = {
    "object": "list",
    "data": [
        {"id": "llmreplay-synthetic", "object": "model", "owned_by": "llmreplay"},
    ],
}


HttpClientFactory = Any  # callable returning async context manager with .request()


class ProxyState:
    def __init__(
        self,
        *,
        mode: Mode,
        cassette: CassetteStore,
        upstream_base: str | None,
        strict_routes: bool = True,
        http_client_factory: HttpClientFactory | None = None,
    ) -> None:
        self.mode = mode
        self.cassette = cassette
        self.upstream_base = (upstream_base or "").rstrip("/")
        self.strict_routes = strict_routes
        self.http_client_factory = http_client_factory or (lambda: httpx.AsyncClient(timeout=60.0))
        self._hash_index: dict[str, dict[str, Any]] | None = None

    def rebuild_index(self) -> dict[str, dict[str, Any]]:
        index: dict[str, dict[str, Any]] = {}
        manifest = self.cassette.load_manifest()
        for tx in manifest.transactions:
            path = self.cassette.root / tx.response_ref
            if path.is_file():
                index[tx.static_hash] = json.loads(path.read_text(encoding="utf-8"))
        self._hash_index = index
        return index

    @property
    def hash_index(self) -> dict[str, dict[str, Any]]:
        if self._hash_index is None:
            return self.rebuild_index()
        return self._hash_index


def create_app(
    *,
    mode: Mode | None = None,
    cassette_dir: Path | None = None,
    upstream_base: str | None = None,
    http_client_factory: HttpClientFactory | None = None,
    config: ProxyConfig | None = None,
) -> Starlette:
    if config is None:
        if mode is None or cassette_dir is None:
            raise ValueError("config or (mode, cassette_dir) required")
        config = ProxyConfig(
            mode=mode,
            cassette_dir=cassette_dir,
            upstream_base=upstream_base,
        )
    state = ProxyState(
        mode=config.mode,
        cassette=CassetteStore(config.cassette_dir),
        upstream_base=config.upstream_base,
        strict_routes=config.strict_routes,
        http_client_factory=http_client_factory,
    )
    if config.mode == "replay":
        state.rebuild_index()

    async def healthz(_request: Request) -> JSONResponse:
        return JSONResponse({"ok": True, "mode": state.mode})

    async def models(request: Request) -> Response:
        if state.mode == "replay":
            # Prefer cassette hit; else synthetic catalog (SPEC S5).
            event = normalize_request_event(
                method="GET",
                path="/v1/models",
                headers=dict(request.headers),
                body=None,
            )
            key = match_key(event)
            if key in state.hash_index:
                return JSONResponse(state.hash_index[key])
            return JSONResponse(SYNTHETIC_MODELS)
        return await _forward_or_record(request, body=None)

    async def post_handler(request: Request) -> Response:
        raw = await request.body()
        try:
            body: Any = json.loads(raw.decode("utf-8")) if raw else None
        except json.JSONDecodeError:
            return JSONResponse(
                {"error": {"type": "llmreplay_protocol", "message": "invalid JSON body"}},
                status_code=400,
            )
        return await _forward_or_record(request, body=body, raw=raw)

    async def _forward_or_record(
        request: Request,
        *,
        body: Any,
        raw: bytes | None = None,
    ) -> Response:
        method = request.method.upper()
        path = request.url.path
        if not is_allowed(method, path):
            return JSONResponse(ROUTE_DENIED_BODY, status_code=404)

        event = normalize_request_event(
            method=method,
            path=path,
            headers=dict(request.headers),
            body=body,
        )
        key = match_key(event)

        if state.mode == "replay":
            hit = state.hash_index.get(key)
            if hit is None:
                return JSONResponse(
                    {
                        "error": {
                            "type": "llmreplay_miss",
                            "message": "409 LLMREPLAY_MISS — no cassette entry",
                            "static_hash": key,
                            "path": path,
                        }
                    },
                    status_code=409,
                )
            return JSONResponse(hit)

        # record mode
        if not state.upstream_base:
            return JSONResponse(
                {
                    "error": {
                        "type": "llmreplay_config",
                        "message": "upstream_base required in record mode",
                    }
                },
                status_code=500,
            )
        url = f"{state.upstream_base}{path}"
        headers = {
            k: v for k, v in request.headers.items() if k.lower() not in {"host", "content-length"}
        }
        async with state.http_client_factory() as client:
            upstream = await client.request(
                method,
                url,
                content=raw if raw is not None else None,
                headers=headers,
            )
        try:
            resp_body: Any = upstream.json()
        except json.JSONDecodeError:
            resp_body = {"raw_text": upstream.text}

        if upstream.status_code < 400:
            state.cassette.append_transaction(
                request=event,
                response=resp_body if isinstance(resp_body, dict) else {"data": resp_body},
                static_hash=key,
            )
            state.rebuild_index()

        if isinstance(resp_body, dict):
            return JSONResponse(resp_body, status_code=upstream.status_code)
        return Response(content=upstream.content, status_code=upstream.status_code)

    async def denied(request: Request) -> JSONResponse:
        return JSONResponse(ROUTE_DENIED_BODY, status_code=404)

    routes = [
        Route("/healthz", healthz, methods=["GET"]),
        Route("/v1/models", models, methods=["GET"]),
        Route("/v1/messages", post_handler, methods=["POST"]),
        Route("/v1/chat/completions", post_handler, methods=["POST"]),
        Route("/v1/responses", post_handler, methods=["POST"]),
        Route("/{path:path}", denied, methods=["GET", "POST", "PUT", "DELETE", "PATCH"]),
    ]
    app = Starlette(routes=routes)
    app.state.llmreplay = state  # type: ignore[attr-defined]
    return app
