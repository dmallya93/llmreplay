"""Tests for Pydantic coding-standards enforcement."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from llmreplay.proxy.config import ProxyConfig
from llmreplay.store.models import CassetteManifest, CassetteTransaction


@pytest.mark.unit
def test_proxy_config_requires_upstream_for_record(tmp_path) -> None:  # noqa: ANN001
    with pytest.raises(ValidationError):
        ProxyConfig(mode="record", cassette_dir=tmp_path)


@pytest.mark.unit
def test_proxy_config_replay_ok(tmp_path) -> None:  # noqa: ANN001
    cfg = ProxyConfig(mode="replay", cassette_dir=tmp_path)
    assert cfg.upstream_base is None


@pytest.mark.unit
def test_transaction_static_hash_length() -> None:
    with pytest.raises(ValidationError):
        CassetteTransaction(
            id="x",
            request_ref="requests/x.json",
            response_ref="responses/x.json",
            static_hash="too-short",
        )


@pytest.mark.unit
def test_manifest_roundtrip() -> None:
    m = CassetteManifest(schema_version=1, cassette_id="abc")
    restored = CassetteManifest.model_validate(m.model_dump())
    assert restored.cassette_id == "abc"
