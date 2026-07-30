"""Install Claude Code Pre/PostToolUse hook scripts."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict

from llmreplay.hooks.digest import digest_script

RECORD_HOOK = '''#!/usr/bin/env python3
"""LLMReplay record hook — logs allow/deny via llmreplay hooks decide --mode record."""
import os
import sys

from llmreplay.hooks.runtime import run_hook_main

if __name__ == "__main__":
    sys.exit(run_hook_main(mode=os.environ.get("LLMREPLAY_HOOK_MODE", "record")))
'''

REPLAY_HOOK = '''#!/usr/bin/env python3
"""LLMReplay replay hook — forces recorded allow/deny decisions."""
import os
import sys

from llmreplay.hooks.runtime import run_hook_main

if __name__ == "__main__":
    sys.exit(run_hook_main(mode=os.environ.get("LLMREPLAY_HOOK_MODE", "replay")))
'''


class InstallResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    hooks_dir: str
    scripts: dict[str, str]
    digests: dict[str, str]
    settings_snippet: dict


def install_claude_hooks(
    hooks_dir: Path,
    *,
    mode: str = "record",
) -> InstallResult:
    """Write PreToolUse/PostToolUse wrapper scripts and return settings snippet."""
    hooks_dir.mkdir(parents=True, exist_ok=True)
    body = RECORD_HOOK if mode == "record" else REPLAY_HOOK
    scripts: dict[str, Path] = {
        "PreToolUse": hooks_dir / "pre_tool_use.py",
        "PostToolUse": hooks_dir / "post_tool_use.py",
    }
    digests: dict[str, str] = {}
    for _name, path in scripts.items():
        path.write_text(body, encoding="utf-8")
        path.chmod(path.stat().st_mode | 0o111)
        digests[_name] = digest_script(path)
    snippet = {
        "hooks": {
            "PreToolUse": [{"type": "command", "command": str(scripts["PreToolUse"])}],
            "PostToolUse": [{"type": "command", "command": str(scripts["PostToolUse"])}],
        }
    }
    return InstallResult(
        hooks_dir=str(hooks_dir),
        scripts={k: str(v) for k, v in scripts.items()},
        digests=digests,
        settings_snippet=snippet,
    )
