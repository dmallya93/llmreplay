"""Tests for ``llmreplay run`` — one-process record/replay wrapper."""

from __future__ import annotations

import sys
import textwrap
from pathlib import Path
from urllib.parse import urlparse

import httpx
import pytest
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from llmreplay.cli.run_cmd import free_port, run_with_proxy
from llmreplay.proxy.config import ProxyConfig


def _fake_upstream() -> Starlette:
    async def messages(request: Request) -> JSONResponse:
        body = await request.json()
        return JSONResponse(
            {
                "id": "msg_run",
                "model": body.get("model", "fake"),
                "content": [{"type": "text", "text": "run-ok"}],
                "usage": {"input_tokens": 1, "output_tokens": 1},
            }
        )

    return Starlette(
        routes=[Route("/v1/messages", messages, methods=["POST"])],
    )


class _UpstreamClient:
    """Test-double that routes requests through a Starlette app in-process."""

    def __init__(self, upstream: Starlette) -> None:
        self._upstream = upstream

    async def __aenter__(self):  # noqa: ANN204
        return self

    async def __aexit__(self, *args):  # noqa: ANN002
        return None

    async def request(self, method, url, content=None, headers=None):  # noqa: ANN001
        parsed = urlparse(url)
        transport = httpx.ASGITransport(app=self._upstream)
        async with httpx.AsyncClient(transport=transport, base_url="http://up") as client:
            return await client.request(method, parsed.path, content=content, headers=headers or {})


@pytest.mark.contract
def test_run_record_then_replay(tmp_path: Path) -> None:
    """Record via ``run`` child, then replay the same child succeeds."""
    cassette = tmp_path / "cass"
    upstream = _fake_upstream()
    port_record = free_port()
    port_replay = free_port()

    script = tmp_path / "child.py"
    script.write_text(
        textwrap.dedent("""\
            import os, httpx, sys
            base = os.environ["ANTHROPIC_BASE_URL"]
            r = httpx.post(
                f"{base}/v1/messages",
                json={"model": "m", "messages": [{"role": "user", "content": "hi"}]},
            )
            assert r.status_code == 200, r.text
            assert r.json()["content"][0]["text"] == "run-ok"
            sys.exit(0)
        """),
        encoding="utf-8",
    )

    config = ProxyConfig(
        mode="record",
        cassette_dir=cassette,
        upstream_base="http://upstream",
        port=port_record,
    )
    exit_code = run_with_proxy(
        config=config,
        command=[sys.executable, str(script)],
        http_client_factory=lambda: _UpstreamClient(upstream),
    )
    assert exit_code == 0, f"record child exited {exit_code}"

    from llmreplay.store.cassette import CassetteStore

    store = CassetteStore(cassette)
    assert len(store.load_manifest().transactions) == 1

    replay_config = ProxyConfig(
        mode="replay",
        cassette_dir=cassette,
        port=port_replay,
    )
    exit_code2 = run_with_proxy(
        config=replay_config,
        command=[sys.executable, str(script)],
    )
    assert exit_code2 == 0


@pytest.mark.contract
def test_run_child_nonzero_exit_preserved(tmp_path: Path) -> None:
    """Child non-zero exit code is propagated through ``run``."""
    cassette = tmp_path / "cass"
    port = free_port()
    config = ProxyConfig(
        mode="replay",
        cassette_dir=cassette,
        port=port,
    )
    exit_code = run_with_proxy(
        config=config,
        command=[sys.executable, "-c", "import sys; sys.exit(42)"],
    )
    assert exit_code == 42


@pytest.mark.unit
def test_run_no_command_exits_with_error() -> None:
    """CLI ``run`` with no trailing command prints usage."""
    from typer.testing import CliRunner

    from llmreplay.cli.main import app

    runner = CliRunner()
    result = runner.invoke(app, ["run"])
    assert result.exit_code != 0
    assert "usage" in result.output.lower() or "COMMAND" in result.output


@pytest.mark.contract
def test_run_command_not_found(tmp_path: Path) -> None:
    """Non-existent command returns exit code 9 (ROUTE_OR_PROTOCOL)."""
    cassette = tmp_path / "cass"
    port = free_port()
    config = ProxyConfig(
        mode="replay",
        cassette_dir=cassette,
        port=port,
    )
    exit_code = run_with_proxy(
        config=config,
        command=["nonexistent-binary-xyz-12345"],
    )
    assert exit_code == 9


@pytest.mark.contract
def test_run_strips_hmac_from_child(tmp_path: Path) -> None:
    """LLMREPLAY_HMAC_KEY is not passed to the child process."""
    cassette = tmp_path / "cass"
    port = free_port()
    config = ProxyConfig(
        mode="replay",
        cassette_dir=cassette,
        port=port,
    )

    script = tmp_path / "check_env.py"
    script.write_text(
        textwrap.dedent("""\
            import os, sys
            if "LLMREPLAY_HMAC_KEY" in os.environ:
                sys.exit(1)
            sys.exit(0)
        """),
        encoding="utf-8",
    )

    exit_code = run_with_proxy(
        config=config,
        command=[sys.executable, str(script)],
        extra_env={"LLMREPLAY_HMAC_KEY": "test-secret"},
    )
    assert exit_code == 0


@pytest.mark.contract
def test_run_sets_openai_base_url_with_v1(tmp_path: Path) -> None:
    """OPENAI_BASE_URL includes /v1 suffix for SDK compatibility."""
    cassette = tmp_path / "cass"
    port = free_port()
    config = ProxyConfig(
        mode="replay",
        cassette_dir=cassette,
        port=port,
    )

    script = tmp_path / "check_url.py"
    script.write_text(
        textwrap.dedent("""\
            import os, sys
            url = os.environ.get("OPENAI_BASE_URL", "")
            if not url.endswith("/v1"):
                print(f"OPENAI_BASE_URL={url!r} missing /v1", file=sys.stderr)
                sys.exit(1)
            anthro = os.environ.get("ANTHROPIC_BASE_URL", "")
            if anthro.endswith("/v1"):
                print(f"ANTHROPIC_BASE_URL={anthro!r} should NOT have /v1", file=sys.stderr)
                sys.exit(2)
            sys.exit(0)
        """),
        encoding="utf-8",
    )

    exit_code = run_with_proxy(
        config=config,
        command=[sys.executable, str(script)],
    )
    assert exit_code == 0
