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

Denied tools are forced from the cassette decision log (`hooks/decisions.jsonl`); live tool execution is stubbed.
