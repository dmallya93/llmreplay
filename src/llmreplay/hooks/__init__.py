"""Hooks package."""

from llmreplay.hooks.digest import digest_script, verify_hook_digests
from llmreplay.hooks.install import install_claude_hooks
from llmreplay.hooks.models import HookDecision, HookRequest, HookVerifyResult
from llmreplay.hooks.protocol import emit_decision, parse_hook_request
from llmreplay.hooks.recorder import record_decision, replay_decision, tool_stub_response

__all__ = [
    "HookDecision",
    "HookRequest",
    "HookVerifyResult",
    "digest_script",
    "emit_decision",
    "install_claude_hooks",
    "parse_hook_request",
    "record_decision",
    "replay_decision",
    "tool_stub_response",
    "verify_hook_digests",
]
