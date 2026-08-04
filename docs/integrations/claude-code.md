# Claude Code integration

## Zero-config first

```bash
pip install coding-agent-vcr
llmreplay demo
```

## Quick start (`llmreplay run`) — one terminal

```bash
# keep ANTHROPIC_API_KEY in the environment (HMAC defaults locally)

llmreplay run --mode record --cassette .llmreplay/demo \
  --upstream https://api.anthropic.com -- claude --print "say hi"

llmreplay run --mode replay --cassette .llmreplay/demo -- claude --print "say hi"
```

`llmreplay run` starts the proxy, sets `ANTHROPIC_BASE_URL` / `OPENAI_BASE_URL` in the child env, runs the command, and exits with the child's exit code. No second terminal.

<details><summary>Advanced: two-terminal proxy (not recommended)</summary>

```bash
export ANTHROPIC_BASE_URL=http://127.0.0.1:7432
llmreplay record --upstream https://api.anthropic.com
# other terminal: claude --print "say hi"
```

Optional free stack (CCR+Ollama): `--free`. See [free-test-stack.md](../free-test-stack.md).

</details>

## Hooks (C7 / SPEC S12)

Install PreToolUse / PostToolUse wrappers:

```bash
llmreplay hooks install --dir .llmreplay/hooks --mode record --cassette .llmreplay/cassette
# Merge settings_snippet.hooks into ~/.claude/settings.json (or project settings)
export LLMREPLAY_CASSETTE=$PWD/.llmreplay/cassette
export LLMREPLAY_HOOK_MODE=record
export LLMREPLAY_CONFIG=$PWD/llmreplay.yaml   # required for mark-live tools on replay
```

Protocol:

- stdin: one UTF-8 JSON `{"version":1,"id":"...","event":"PreToolUse|PostToolUse",...}`
- stdout: one JSON line `{"id":"...","decision":"allow|deny|error",...}`
- Max 1 MiB; fail closed on invalid input
- Digests of hook scripts stored in cassette `hook_digests`
- `llmreplay hooks verify --profile ci` → exit **6** (`HOOK_OR_POLICY_DIVERGENCE`) on mismatch (manual gate; not auto at proxy start)

Replay:

```bash
llmreplay hooks install --mode replay
export LLMREPLAY_HOOK_MODE=replay
export LLMREPLAY_CONFIG=$PWD/llmreplay.yaml
llmreplay hooks verify --profile ci
```

`mark-live Bash` in `llmreplay.yaml` makes PreToolUse for Bash return `allow` on replay (real tool runs). Without `LLMREPLAY_CONFIG`, live marks are ignored.

## Troubleshooting

| Symptom | Fix |
|---|---|
| Tool ID desync on replay | Re-record; IDs are wire literals + `tool_id_map` |
| Hook digest mismatch | `llmreplay hooks verify --profile ci` |
| Path pin drift | `llmreplay template path_rebase` / sandbox env paths |

Denied tools are forced from `hooks/decisions.jsonl`. The decision line on stdout is what Claude Code honors; a stub note is added to `reason` (and echoed on stderr) — there is no protocol to inject a fake tool body.

Hermetic multi-turn goldens: `tests/test_c9_parity.py`. Example walkthrough: `examples/claude-code-hello/`.

## Plugin + skills (alpha)

LLMReplay ships a Claude Code plugin with skill files for `record`, `replay`, and `why`:

```bash
# Load the plugin from a local path
claude --plugin-dir /path/to/llmreplay/plugins/llmreplay
```

Skills are discoverable via `/llmreplay:record`, `/llmreplay:replay`, `/llmreplay:why` once the plugin is loaded.
