"""Record and force hook allow/deny decisions."""

from __future__ import annotations

import json
from pathlib import Path

from llmreplay.hooks.models import HookDecision, HookRequest, RecordedHookDecision
from llmreplay.hooks.protocol import fail_closed
from llmreplay.store.cassette import CassetteStore


def decisions_path(cassette: CassetteStore) -> Path:
    path = cassette.root / "hooks" / "decisions.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def record_decision(cassette: CassetteStore, request: HookRequest, decision: HookDecision) -> None:
    entry = RecordedHookDecision(
        id=decision.id,
        event=request.event,
        tool_name=request.tool_name,
        decision=decision.decision,
        reason=decision.reason,
    )
    path = decisions_path(cassette)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(entry.model_dump_json() + "\n")


def load_decisions(cassette: CassetteStore) -> list[RecordedHookDecision]:
    path = decisions_path(cassette)
    if not path.is_file():
        return []
    out: list[RecordedHookDecision] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        out.append(RecordedHookDecision.model_validate(json.loads(line)))
    return out


def replay_decision(
    cassette: CassetteStore,
    request: HookRequest,
    *,
    live_tools: frozenset[str] | None = None,
) -> HookDecision:
    """Force the recorded decision for this hook id; deny if missing (fail closed).

    Tools listed in ``live_tools`` (from ``mark-live``) bypass cassette force and
    return ``allow`` so the real tool runs (SPEC live field class).
    """
    if live_tools and request.tool_name and request.tool_name in live_tools:
        return HookDecision(
            id=request.id,
            decision="allow",
            reason=f"mark-live:{request.tool_name}",
        )
    for entry in load_decisions(cassette):
        if entry.id == request.id:
            return HookDecision(
                id=entry.id,
                decision=entry.decision,
                reason=entry.reason or "forced from cassette",
            )
    # Match by event+tool when id differs across runs (teaching fallback).
    for entry in load_decisions(cassette):
        if entry.event == request.event and entry.tool_name == request.tool_name:
            return HookDecision(
                id=request.id,
                decision=entry.decision,
                reason=entry.reason or "forced from cassette (tool match)",
            )
    return fail_closed(request.id, "no recorded hook decision")


def tool_stub_response(tool_name: str | None) -> dict[str, str]:
    """Stub tool result used when replay forces deny/error without live execution."""
    name = tool_name or "unknown"
    return {
        "type": "tool_result",
        "content": f"[llmreplay] tool stub — {name} not executed on replay",
    }
