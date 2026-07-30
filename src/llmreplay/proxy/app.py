"""Starlette ASGI proxy application."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

import httpx
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Route

from llmreplay.adapters import adapter_for_path
from llmreplay.config.profiles import STRICT_PROFILES, LLMReplayFileConfig, load_llmreplay_yaml
from llmreplay.core.match import match_key
from llmreplay.core.volatility import DEFAULT_IGNORE_KEYS
from llmreplay.proxy.config import ProxyConfig, ProxyMode
from llmreplay.proxy.free_auth import enforce_free_key
from llmreplay.proxy.normalize import normalize_request_event
from llmreplay.proxy.routes import ROUTE_DENIED_BODY, is_allowed
from llmreplay.proxy.sse import (
    parse_openai_sse,
    strip_stream_flag,
    synthesize_sse,
    wants_stream,
)
from llmreplay.scrub.engine import Scrubber, residual_hits_in_payload
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
        scrubber: Scrubber | None = None,
        profile: str = "local",
        file_config: LLMReplayFileConfig | None = None,
        fail_on_residual_secrets: bool = False,
        free_mode: bool = False,
        free_key_store: Path | None = None,
        ollama_model: str = "qwen2.5-coder:latest",
        ignore_keys: frozenset[str] | None = None,
        llm_live: bool = False,
        allow_remote: bool = False,
    ) -> None:
        self.mode = mode
        self.cassette = cassette
        self.upstream_base = (upstream_base or "").rstrip("/")
        self.strict_routes = strict_routes
        self.http_client_factory = http_client_factory or (lambda: httpx.AsyncClient(timeout=60.0))
        self.scrubber = scrubber or Scrubber()
        self.profile = profile
        self.file_config = file_config or LLMReplayFileConfig()
        self.fail_on_residual_secrets = fail_on_residual_secrets
        self.free_mode = free_mode
        self.free_key_store = free_key_store
        self.ollama_model = ollama_model
        self.ignore_keys = ignore_keys if ignore_keys is not None else DEFAULT_IGNORE_KEYS
        self.llm_live = llm_live
        self.allow_remote = allow_remote
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

    def index_put(self, static_hash: str, response: dict[str, Any]) -> None:
        """O(1) index update after a successful record write."""
        if self._hash_index is None:
            self.rebuild_index()
        assert self._hash_index is not None
        self._hash_index[static_hash] = response

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
    scrubber: Scrubber | None = None,
    file_config: LLMReplayFileConfig | None = None,
) -> Starlette:
    if config is None:
        if mode is None or cassette_dir is None:
            raise ValueError("config or (mode, cassette_dir) required")
        config = ProxyConfig(
            mode=mode,
            cassette_dir=cassette_dir,
            upstream_base=upstream_base,
        )
    yaml_cfg = file_config or load_llmreplay_yaml(config.config_path)
    profile = yaml_cfg.resolved_profile(config.profile)
    fail_residual = yaml_cfg.fail_on_residual_secrets(config.profile)
    ignore_keys = frozenset(yaml_cfg.merged_ignore(config.profile)) | DEFAULT_IGNORE_KEYS
    if config.mode == "record" and config.profile in STRICT_PROFILES:
        if not os.environ.get("LLMREPLAY_HMAC_KEY"):
            raise ValueError(
                f"profile {config.profile!r} requires LLMREPLAY_HMAC_KEY "
                "(stable scrub placeholders for CI)"
            )
    llm_live = yaml_cfg.is_llm_live()
    if llm_live and config.profile in STRICT_PROFILES and not config.allow_live:
        raise ValueError(
            f"profile {config.profile!r} refuses mark-live __llm__ without "
            "allow_live=True / --allow-live (breaks hermetic replay)"
        )
    built_scrubber = scrubber or Scrubber(
        extra_scrub_paths=yaml_cfg.merged_scrub_paths(config.profile),
    )
    state = ProxyState(
        mode=config.mode,
        cassette=CassetteStore(config.cassette_dir),
        upstream_base=config.upstream_base,
        strict_routes=config.strict_routes,
        http_client_factory=http_client_factory,
        scrubber=built_scrubber,
        profile=config.profile,
        file_config=yaml_cfg,
        fail_on_residual_secrets=fail_residual,
        free_mode=config.free_mode,
        free_key_store=config.free_key_store,
        ollama_model=config.ollama_model,
        ignore_keys=ignore_keys,
        llm_live=llm_live,
        allow_remote=config.allow_non_loopback,
    )
    # Touch resolved profile so sticky/ci validation runs at startup.
    _ = profile
    if config.free_mode and config.mode == "record":
        digest = hashlib.sha256(
            f"ccr|{config.ollama_model}|{config.upstream_base}".encode()
        ).hexdigest()[:16]
        state.cassette.set_test_stack(
            {
                "router": "ccr",
                "ollama_model": config.ollama_model,
                "digest": digest,
                "upstream": config.upstream_base,
            }
        )
    if config.mode == "replay":
        state.rebuild_index()

    async def healthz(_request: Request) -> JSONResponse:
        return JSONResponse(
            {"ok": True, "mode": state.mode, "profile": state.profile},
        )

    async def models(request: Request) -> Response:
        if state.mode == "replay":
            event = normalize_request_event(
                method="GET",
                path="/v1/models",
                headers=dict(request.headers),
                body=None,
            )
            key = match_key(
                state.scrubber.scrub_event(event),
                ignore_keys=state.ignore_keys,
            )
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

        denied = enforce_free_key(
            request,
            store_path=state.free_key_store,
            require_free_key=state.free_mode,
            allow_remote=state.allow_remote,
        )
        if denied is not None:
            return denied

        stream = wants_stream(body, dict(request.headers))
        # ``stream`` is in DEFAULT_IGNORE_KEYS — match ignores transport mode.
        event = normalize_request_event(
            method=method,
            path=path,
            headers=dict(request.headers),
            body=body,
        )
        scrubbed_event = state.scrubber.scrub_event(event)
        key = match_key(scrubbed_event, ignore_keys=state.ignore_keys)

        if state.mode == "replay":
            if state.llm_live:
                if not state.upstream_base:
                    return JSONResponse(
                        {
                            "error": {
                                "type": "llmreplay_live",
                                "message": (
                                    "503 LLMREPLAY_LIVE — tools.__llm__ is live but "
                                    "upstream_base is unset (pass --upstream)"
                                ),
                            }
                        },
                        status_code=503,
                    )
                return await _upstream_call(
                    request,
                    body=body,
                    raw=raw,
                    scrubbed_event=scrubbed_event,
                    key=key,
                    stream=stream,
                    write_cassette=False,
                )
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
            if stream:
                adapter = adapter_for_path(path)
                sse_body = adapter.synthesize_sse(hit) if adapter else synthesize_sse(path, hit)
                return Response(
                    content=sse_body,
                    status_code=200,
                    media_type="text/event-stream",
                    headers={"Cache-Control": "no-cache"},
                )
            return JSONResponse(hit)

        return await _upstream_call(
            request,
            body=body,
            raw=raw,
            scrubbed_event=scrubbed_event,
            key=key,
            stream=stream,
            write_cassette=True,
        )

    async def _upstream_call(
        request: Request,
        *,
        body: Any,
        raw: bytes | None,
        scrubbed_event: dict[str, Any],
        key: str,
        stream: bool,
        write_cassette: bool,
    ) -> Response:
        # force non-streaming upstream; synthesize SSE to client if needed
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
        method = request.method.upper()
        path = request.url.path
        upstream_body = strip_stream_flag(body) if isinstance(body, dict) else body
        upstream_raw = (
            json.dumps(upstream_body).encode("utf-8") if isinstance(upstream_body, dict) else raw
        )
        url = f"{state.upstream_base}{path}"
        headers = {
            k: v for k, v in request.headers.items() if k.lower() not in {"host", "content-length"}
        }
        try:
            async with state.http_client_factory() as client:
                upstream = await client.request(
                    method,
                    url,
                    content=upstream_raw,
                    headers=headers,
                )
        except httpx.HTTPError as exc:
            return JSONResponse(
                {
                    "error": {
                        "type": "llmreplay_upstream_error",
                        "message": f"503 LLMREPLAY_UPSTREAM — {exc}",
                    }
                },
                status_code=503,
            )
        content_type = (upstream.headers.get("content-type") or "").lower()
        try:
            if "text/event-stream" in content_type:
                resp_body: Any = parse_openai_sse(upstream.text)
            else:
                resp_body = upstream.json()
        except json.JSONDecodeError:
            resp_body = {"raw_text": upstream.text}

        if write_cassette and upstream.status_code < 400:
            stored_response = resp_body if isinstance(resp_body, dict) else {"data": resp_body}
            scrubbed_response = state.scrubber.scrub_response(stored_response)
            residual = residual_hits_in_payload(
                {"request": scrubbed_event, "response": scrubbed_response},
                state.scrubber.patterns,
            )
            if residual and state.fail_on_residual_secrets:
                return JSONResponse(
                    {
                        "error": {
                            "type": "llmreplay_secret",
                            "message": (
                                "422 LLMREPLAY_SECRET — residual secrets after scrub; "
                                "refusing cassette write (ci/strict)"
                            ),
                            "patterns": residual,
                            "profile": state.profile,
                        }
                    },
                    status_code=422,
                )
            state.cassette.append_transaction(
                request=scrubbed_event,
                response=scrubbed_response,
                static_hash=key,
            )
            state.index_put(key, scrubbed_response)

        if stream and isinstance(resp_body, dict):
            adapter = adapter_for_path(path)
            sse_body = (
                adapter.synthesize_sse(resp_body) if adapter else synthesize_sse(path, resp_body)
            )
            return Response(
                content=sse_body,
                status_code=upstream.status_code,
                media_type="text/event-stream",
                headers={"Cache-Control": "no-cache"},
            )
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
