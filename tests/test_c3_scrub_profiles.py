"""C3 scrub + profile tests."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx
import pytest
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from llmreplay.config.profiles import LLMReplayFileConfig, load_llmreplay_yaml
from llmreplay.proxy.app import create_app
from llmreplay.proxy.config import ProxyConfig
from llmreplay.scrub.engine import (
    Scrubber,
    hmac_placeholder,
    residual_hits_in_payload,
    residual_secret_hits,
)
from llmreplay.scrub.patterns import ScrubPatterns, SecretRegex
from llmreplay.store.cassette import CassetteStore


@pytest.mark.unit
def test_hmac_placeholder_stable() -> None:
    key = b"test-key"
    a = hmac_placeholder("sk-secretvalue0123456789", key)
    b = hmac_placeholder("sk-secretvalue0123456789", key)
    assert a == b
    assert a.startswith("«REDACTED:hmac:")
    assert "sk-secret" not in a


@pytest.mark.unit
def test_scrubber_redacts_openai_key_and_bearer() -> None:
    scrubber = Scrubber(hmac_key=b"unit-test-key")
    text = "Authorization: Bearer sk-abcdefghijklmnopqrstuvwxyz0123"
    out = scrubber.scrub_string(text)
    assert "sk-abcdefghijklmnopqrstuvwxyz0123" not in out
    assert "REDACTED:hmac:" in out
    assert residual_secret_hits(out) == []


@pytest.mark.unit
def test_scrub_sensitive_key_whole_value() -> None:
    scrubber = Scrubber(hmac_key=b"unit-test-key")
    cleaned = scrubber.scrub_value({"api_key": "not-a-regex-shaped-secret", "ok": "x"})
    assert cleaned["api_key"].startswith("«REDACTED:hmac:")
    assert cleaned["ok"] == "x"


@pytest.mark.unit
def test_scrub_event_headers_and_path_query() -> None:
    scrubber = Scrubber(hmac_key=b"unit-test-key")
    event = {
        "method": "POST",
        "path": "/v1/messages?token=sk-abcdefghijklmnopqrstuvwxyz0123",
        "headers": {"authorization": "Bearer super-secret-token-value", "x-custom": "ok"},
        "body": {
            "api_key": "sk-abcdefghijklmnopqrstuvwxyz0123",
            "tool_result": {"content": "ghp_abcdefghijklmnopqrstuvwxyz0123456789"},
        },
    }
    cleaned = scrubber.scrub_event(event)
    blob = json.dumps(cleaned)
    assert "super-secret" not in blob
    assert "sk-abcdefghijklmnopqrstuvwxyz0123" not in blob
    assert "ghp_abcdefghijklmnopqrstuvwxyz0123456789" not in blob
    assert cleaned["headers"]["x-custom"] == "ok"


@pytest.mark.unit
def test_profile_sticky_forbidden_in_ci_and_strict() -> None:
    for name in ("ci", "strict"):
        cfg = LLMReplayFileConfig.model_validate(
            {"profiles": {name: {"ignore_drift": "fail", "sticky_writeback": True}}}
        )
        with pytest.raises(ValueError, match="sticky_writeback"):
            cfg.resolved_profile(name)


@pytest.mark.unit
def test_profile_precedence_merged_ignore_and_scrub() -> None:
    cfg = LLMReplayFileConfig.model_validate(
        {
            "defaults": {"ignore": ["usage"], "scrub": ["body.a"]},
            "profiles": {
                "local": {
                    "ignore_drift": "warn",
                    "ignore": ["latency_ms"],
                    "scrub": ["body.b"],
                }
            },
        }
    )
    assert cfg.merged_ignore("local") == ["usage", "latency_ms"]
    assert cfg.merged_scrub_paths("local") == ["body.a", "body.b"]
    assert cfg.fail_on_residual_secrets("ci") is True
    assert cfg.fail_on_residual_secrets("local") is False


@pytest.mark.unit
def test_load_yaml_file(tmp_path: Path) -> None:
    path = tmp_path / "llmreplay.yaml"
    path.write_text(
        "version: 1\nprofiles:\n  local:\n    ignore_drift: warn\n",
        encoding="utf-8",
    )
    cfg = load_llmreplay_yaml(path)
    assert cfg.version == 1
    assert cfg.resolved_profile("local").ignore_drift == "warn"


@pytest.mark.unit
def test_residual_hits_after_scrub_clean() -> None:
    scrubber = Scrubber(hmac_key=b"k")
    payload = scrubber.scrub_event(
        {
            "headers": {"authorization": "Bearer sk-abcdefghijklmnopqrstuvwxyz0123"},
            "body": {"x": "sk-abcdefghijklmnopqrstuvwxyz0123"},
        }
    )
    assert residual_hits_in_payload(payload) == []


class _PassthroughScrubber(Scrubber):
    """Leaves secrets intact so residual detector can fire."""

    def scrub_event(self, event: dict[str, Any]) -> dict[str, Any]:
        return deepcopy(event)

    def scrub_response(self, response: dict[str, Any]) -> dict[str, Any]:
        return deepcopy(response)


def _upstream_factory(upstream: Starlette) -> Any:
    class _UpstreamClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):  # noqa: ANN002, ARG002
            return None

        async def request(self, method, url, content=None, headers=None):  # noqa: ANN001
            parsed = urlparse(url)
            transport = httpx.ASGITransport(app=upstream)
            async with httpx.AsyncClient(transport=transport, base_url="http://up") as client:
                return await client.request(
                    method, parsed.path, content=content, headers=headers or {}
                )

    return _UpstreamClient


@pytest.mark.contract
@pytest.mark.asyncio
async def test_record_scrubs_secrets_on_disk(tmp_path: Path) -> None:
    async def messages(request: Request) -> JSONResponse:
        return JSONResponse({"id": "msg", "content": [{"type": "text", "text": "ok"}]})

    upstream = Starlette(routes=[Route("/v1/messages", messages, methods=["POST"])])
    cassette = tmp_path / "cass"
    scrubber = Scrubber(hmac_key=b"cassette-test-key")
    record_app = create_app(
        mode="record",
        cassette_dir=cassette,
        upstream_base="http://upstream",
        http_client_factory=_upstream_factory(upstream),
        scrubber=scrubber,
    )
    transport = httpx.ASGITransport(app=record_app)
    secret = "sk-abcdefghijklmnopqrstuvwxyz012345"
    async with httpx.AsyncClient(transport=transport, base_url="http://proxy") as client:
        resp = await client.post(
            "/v1/messages",
            headers={"authorization": f"Bearer {secret}"},
            json={"model": "m", "messages": [{"role": "user", "content": secret}]},
        )
        assert resp.status_code == 200

    for path in cassette.rglob("*"):
        if path.is_file():
            text = path.read_text(encoding="utf-8", errors="ignore")
            assert secret not in text, f"secret leaked in {path}"

    store = CassetteStore(cassette)
    assert len(store.load_manifest().transactions) == 1


@pytest.mark.contract
@pytest.mark.asyncio
async def test_ci_profile_refuses_residual_secret_write(tmp_path: Path) -> None:
    async def messages(request: Request) -> JSONResponse:
        return JSONResponse({"id": "msg", "content": [{"type": "text", "text": "ok"}]})

    upstream = Starlette(routes=[Route("/v1/messages", messages, methods=["POST"])])
    cassette = tmp_path / "cass"
    patterns = ScrubPatterns(
        secret_regexes=[
            SecretRegex(name="openai_sk", pattern=r"sk-[A-Za-z0-9]{20,}"),
        ]
    )
    scrubber = _PassthroughScrubber(patterns=patterns, hmac_key=b"k")
    record_app = create_app(
        config=ProxyConfig(
            mode="record",
            cassette_dir=cassette,
            upstream_base="http://upstream",
            profile="ci",
        ),
        http_client_factory=_upstream_factory(upstream),
        scrubber=scrubber,
    )
    transport = httpx.ASGITransport(app=record_app)
    secret = "sk-abcdefghijklmnopqrstuvwxyz012345"
    async with httpx.AsyncClient(transport=transport, base_url="http://proxy") as client:
        resp = await client.post(
            "/v1/messages",
            json={"model": "m", "messages": [{"role": "user", "content": secret}]},
        )
        assert resp.status_code == 422
        assert resp.json()["error"]["type"] == "llmreplay_secret"

    assert not (cassette / "cassette.json").exists()


@pytest.mark.contract
@pytest.mark.asyncio
async def test_local_profile_allows_record_when_scrubbed(tmp_path: Path) -> None:
    async def messages(request: Request) -> JSONResponse:
        return JSONResponse({"id": "msg", "ok": True})

    upstream = Starlette(routes=[Route("/v1/messages", messages, methods=["POST"])])
    cassette = tmp_path / "cass"
    record_app = create_app(
        config=ProxyConfig(
            mode="record",
            cassette_dir=cassette,
            upstream_base="http://upstream",
            profile="local",
        ),
        http_client_factory=_upstream_factory(upstream),
        scrubber=Scrubber(hmac_key=b"local-key"),
    )
    transport = httpx.ASGITransport(app=record_app)
    secret = "sk-abcdefghijklmnopqrstuvwxyz012345"
    async with httpx.AsyncClient(transport=transport, base_url="http://proxy") as client:
        resp = await client.post(
            "/v1/messages",
            json={"model": "m", "content": secret},
        )
        assert resp.status_code == 200
    assert CassetteStore(cassette).load_manifest().transactions


@pytest.mark.unit
def test_fixtures_dir_has_no_live_secret_patterns() -> None:
    """CI secret scan on fixtures/ (DESIGN C3 acceptance)."""
    root = Path(__file__).resolve().parents[1] / "fixtures"
    if not root.is_dir():
        pytest.skip("no fixtures dir")
    patterns = ScrubPatterns(
        secret_regexes=[
            SecretRegex(name="openai_sk", pattern=r"sk-[A-Za-z0-9]{20,}"),
            SecretRegex(name="aws_access_key", pattern=r"AKIA[0-9A-Z]{16}"),
            SecretRegex(name="github_pat", pattern=r"gh[pousr]_[A-Za-z0-9_]{20,}"),
        ]
    )
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        hits = residual_secret_hits(text, patterns)
        assert hits == [], f"secret-like pattern in {path}: {hits}"
