"""Pydantic models for cassette manifests (on-disk contract)."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class CassetteTransaction(BaseModel):
    model_config = ConfigDict(extra="allow")  # forward-compatible with schema

    id: str
    request_ref: str
    response_ref: str
    static_hash: str = Field(min_length=64, max_length=64)


class CassetteManifest(BaseModel):
    """cassette.json root object."""

    model_config = ConfigDict(extra="allow")  # SPEC extensions + schema additionalProperties

    schema_version: int = Field(ge=1)
    cassette_id: str = Field(min_length=1)
    extensions: dict[str, Any] = Field(default_factory=dict)
    transactions: list[CassetteTransaction] = Field(default_factory=list)
    checksums: dict[str, str] = Field(default_factory=dict)
    tool_id_map: dict[str, str] = Field(default_factory=dict)
    hook_digests: dict[str, str] = Field(default_factory=dict)
    test_stack: dict[str, Any] = Field(default_factory=dict)
