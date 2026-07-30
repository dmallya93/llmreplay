"""Parse/emit Claude Code hook stdin/stdout protocol (S12)."""

from __future__ import annotations

import json
from typing import Any

from pydantic import ValidationError

from llmreplay.hooks.models import HookDecision, HookRequest

MAX_HOOK_BYTES = 1 * 1024 * 1024  # 1 MiB


class HookProtocolError(ValueError):
    """Invalid hook request/response."""


def parse_hook_request(raw: bytes | str) -> HookRequest:
    if isinstance(raw, str):
        data = raw.encode("utf-8")
    else:
        data = raw
    if len(data) > MAX_HOOK_BYTES:
        raise HookProtocolError("hook request exceeds 1 MiB")
    try:
        payload: Any = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HookProtocolError("invalid JSON") from exc
    try:
        return HookRequest.model_validate(payload)
    except ValidationError as exc:
        raise HookProtocolError(str(exc)) from exc


def emit_decision(decision: HookDecision) -> str:
    return decision.model_dump_json() + "\n"


def fail_closed(request_id: str, reason: str) -> HookDecision:
    return HookDecision(id=request_id, decision="deny", reason=reason)
