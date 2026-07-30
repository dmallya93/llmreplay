"""Hook process entry — read stdin, decide, write stdout (fail closed)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from llmreplay.config.profiles import load_llmreplay_yaml
from llmreplay.hooks.models import HookDecision
from llmreplay.hooks.protocol import (
    HookProtocolError,
    emit_decision,
    fail_closed,
    parse_hook_request,
)
from llmreplay.hooks.recorder import record_decision, replay_decision, tool_stub_response
from llmreplay.store.cassette import CassetteStore


def _default_policy(request_id: str) -> HookDecision:
    return HookDecision(id=request_id, decision="allow", reason="default allow")


def run_hook_main(*, mode: str | None = None, raw: bytes | None = None) -> int:
    """CLI/process entry used by installed hook scripts. Returns process exit code."""
    mode = (mode or os.environ.get("LLMREPLAY_HOOK_MODE") or "record").lower()
    cassette_dir = Path(os.environ.get("LLMREPLAY_CASSETTE", ".llmreplay/cassette"))
    config_path = os.environ.get("LLMREPLAY_CONFIG")
    cfg = load_llmreplay_yaml(Path(config_path) if config_path else None)
    if raw is None:
        raw = sys.stdin.buffer.read()
    try:
        request = parse_hook_request(raw)
    except HookProtocolError as exc:
        sys.stdout.write(emit_decision(fail_closed("unknown", str(exc))))
        return 0

    cassette = CassetteStore(cassette_dir)
    if mode == "replay":
        decision = replay_decision(
            cassette,
            request,
            live_tools=cfg.live_tools(),
        )
        if decision.decision in {"deny", "error"}:
            print(tool_stub_response(request.tool_name), file=sys.stderr)
    else:
        force = os.environ.get("LLMREPLAY_HOOK_FORCE")
        if force == "allow":
            decision = HookDecision(id=request.id, decision="allow", reason="forced by env")
        elif force == "deny":
            decision = HookDecision(id=request.id, decision="deny", reason="forced by env")
        elif force == "error":
            decision = HookDecision(id=request.id, decision="error", reason="forced by env")
        else:
            decision = _default_policy(request.id)
        record_decision(cassette, request, decision)

    sys.stdout.write(emit_decision(decision))
    return 0
