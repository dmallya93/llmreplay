"""Hook protocol models (DESIGN S12 / SPEC)."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

HookEventName = Literal["PreToolUse", "PostToolUse"]
HookDecisionKind = Literal["allow", "deny", "error"]


class HookRequest(BaseModel):
    """One UTF-8 JSON object on hook stdin."""

    model_config = ConfigDict(extra="allow")

    version: int = 1
    id: str = Field(min_length=1)
    event: HookEventName
    tool_name: str | None = None
    tool_input: dict[str, Any] = Field(default_factory=dict)
    tool_use_id: str | None = None


class HookDecision(BaseModel):
    """One JSON line on hook stdout."""

    model_config = ConfigDict(extra="forbid")

    id: str
    decision: HookDecisionKind
    reason: str | None = None


class RecordedHookDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    event: HookEventName
    tool_name: str | None = None
    decision: HookDecisionKind
    reason: str | None = None


class HookVerifyResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ok: bool
    mismatches: dict[str, str] = Field(default_factory=dict)
    message: str
