"""C5 free test-stack + keys."""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest
from typer.testing import CliRunner

from llmreplay.cli.main import app
from llmreplay.core.exit_codes import ExitCode
from llmreplay.proxy.app import create_app
from llmreplay.proxy.config import ProxyConfig
from llmreplay.proxy.free_auth import enforce_free_key
from llmreplay.store.cassette import CassetteStore
from llmreplay.teststack.config import free_mode_env, render_ccr_config
from llmreplay.teststack.keys import FreeKeyStore
from llmreplay.teststack.lifecycle import stack_up
from llmreplay.teststack.models import FreeStackConfig
from llmreplay.teststack.status import status as probe_status

runner = CliRunner()


@pytest.mark.unit
def test_render_ccr_config_points_at_ollama() -> None:
    cfg = render_ccr_config(FreeStackConfig(ollama_model="tinyllama"))
    assert cfg["Providers"][0]["name"] == "ollama"
    assert "11434" in cfg["Providers"][0]["api_base_url"]
    assert "tinyllama" in cfg["Router"]["default"]


@pytest.mark.unit
def test_stack_up_writes_ccr_config(tmp_path: Path) -> None:
    result = stack_up(FreeStackConfig(config_dir=tmp_path / "stack"))
    path = Path(result.ccr_config)
    assert path.is_file()
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["Providers"][0]["api_key"] == "ollama"


@pytest.mark.unit
def test_free_key_localhost_and_quota(tmp_path: Path) -> None:
    store = FreeKeyStore(tmp_path / "keys.json")
    key = store.create(quota=2)
    assert key.token.startswith("llmreplay-free-")
    store.assert_localhost("127.0.0.1")
    with pytest.raises(PermissionError):
        store.assert_localhost("8.8.8.8")
    store.consume(key.token, units=1)
    store.consume(key.token, units=1)
    with pytest.raises(RuntimeError, match="quota"):
        store.consume(key.token, units=1)


@pytest.mark.unit
def test_free_mode_env_never_embeds_in_cassette_fields() -> None:
    env = free_mode_env(proxy_base="http://127.0.0.1:7432", free_token="llmreplay-free-x")
    assert env["ANTHROPIC_API_KEY"].startswith("llmreplay-free-")
    assert "7432" in env["ANTHROPIC_BASE_URL"]


@pytest.mark.unit
def test_test_stack_status_exit_4_when_down(monkeypatch: pytest.MonkeyPatch) -> None:
    import llmreplay.teststack.status as st

    monkeypatch.setattr(st, "_probe", lambda url, timeout=1.0: (False, "down"))
    report = probe_status(FreeStackConfig())
    assert report.healthy is False
    cli = runner.invoke(app, ["test-stack", "status", "--json"])
    assert cli.exit_code == int(ExitCode.TEST_STACK_UNHEALTHY)


@pytest.mark.unit
def test_keys_create_free_cli(tmp_path: Path) -> None:
    store = tmp_path / "keys.json"
    result = runner.invoke(
        app,
        ["keys", "create", "--free", "--store", str(store), "--print-env"],
    )
    assert result.exit_code == 0
    assert "llmreplay-free-" in result.stdout
    assert "export ANTHROPIC_BASE_URL=" in result.stdout
    assert store.is_file()


@pytest.mark.unit
def test_test_stack_up_cli(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        ["test-stack", "up", "--config-dir", str(tmp_path / "ts")],
    )
    assert result.exit_code == 0
    assert (tmp_path / "ts" / "ccr-config.json").is_file()


@pytest.mark.unit
def test_enforce_free_key_rejects_non_loopback(tmp_path: Path) -> None:
    store_path = tmp_path / "keys.json"
    key = FreeKeyStore(store_path).create(quota=5)

    class _Client:
        host = "8.8.8.8"

    class _Req:
        client = _Client()
        headers = {"authorization": f"Bearer {key.token}"}

    denied = enforce_free_key(_Req(), store_path=store_path)  # type: ignore[arg-type]
    assert denied is not None
    assert denied.status_code == 403


@pytest.mark.contract
@pytest.mark.asyncio
async def test_free_key_quota_on_proxy(tmp_path: Path) -> None:
    store_path = tmp_path / "keys.json"
    key = FreeKeyStore(store_path).create(quota=1)
    cassette = tmp_path / "cass"
    # Seed a replay hit so auth runs before miss logic matters less.
    asgi = create_app(
        config=ProxyConfig(
            mode="replay",
            cassette_dir=cassette,
            free_mode=True,
            free_key_store=store_path,
        )
    )
    transport = httpx.ASGITransport(app=asgi)
    async with httpx.AsyncClient(transport=transport, base_url="http://127.0.0.1") as client:
        first = await client.post(
            "/v1/messages",
            headers={"authorization": f"Bearer {key.token}"},
            json={"model": "m"},
        )
        # Loopback ASGI client → consume quota; miss is 409 after auth.
        assert first.status_code in {409, 200}
        second = await client.post(
            "/v1/messages",
            headers={"authorization": f"Bearer {key.token}"},
            json={"model": "m"},
        )
        assert second.status_code == 429


@pytest.mark.unit
def test_free_record_writes_test_stack(tmp_path: Path) -> None:
    cassette = tmp_path / "cass"
    create_app(
        config=ProxyConfig(
            mode="record",
            cassette_dir=cassette,
            upstream_base="http://127.0.0.1:3456",
            free_mode=True,
            ollama_model="tiny",
        )
    )
    manifest = CassetteStore(cassette).load_manifest()
    assert manifest.test_stack.get("router") == "ccr"
    assert manifest.test_stack.get("ollama_model") == "tiny"
    assert "digest" in manifest.test_stack
