# Claude Code integration

## Base URL

Point Claude Code at the LLMReplay proxy:

```bash
export ANTHROPIC_BASE_URL=http://127.0.0.1:7432
llmreplay record --free   # or --upstream <CCR>
```

Free keys: `llmreplay keys create --free --print-env`.

## Hooks (C7 / SPEC S12)

Install PreToolUse / PostToolUse wrappers:

```bash
llmreplay hooks install --dir .llmreplay/hooks --mode record --cassette .llmreplay/cassette
# Merge settings_snippet.hooks into ~/.claude/settings.json (or project settings)
export LLMREPLAY_CASSETTE=$PWD/.llmreplay/cassette
export LLMREPLAY_HOOK_MODE=record
```

Protocol:

- stdin: one UTF-8 JSON `{"version":1,"id":"...","event":"PreToolUse|PostToolUse",...}`
- stdout: one JSON line `{"id":"...","decision":"allow|deny|error",...}`
- Max 1 MiB; fail closed on invalid input
- Digests of hook scripts stored in cassette `hook_digests`
- `llmreplay hooks verify --profile ci` → exit **6** (`HOOK_OR_POLICY_DIVERGENCE`) on mismatch

Replay:

```bash
llmreplay hooks install --mode replay
export LLMREPLAY_HOOK_MODE=replay
llmreplay hooks verify --profile ci
```

## Troubleshooting

| Symptom | Fix |
|---|---|
| Tool ID desync on replay | Re-record; IDs are wire literals + `tool_id_map` |
| Hook digest mismatch | `llmreplay hooks verify --profile ci` |
| Path pin drift | `llmreplay template path_rebase` / sandbox env paths |

Denied tools are forced from `hooks/decisions.jsonl`; live execution is stubbed on replay.

Hermetic multi-turn goldens: `tests/test_c9_parity.py`. Example walkthrough: `examples/claude-code-hello/`.
