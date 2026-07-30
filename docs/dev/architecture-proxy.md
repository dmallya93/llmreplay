# Proxy architecture

Local allowlisted reverse proxy for Claude Code / Codex base URLs. Package: `llmreplay.proxy`.

## Routes (SPEC S5)

| Method | Path |
|---|---|
| POST | `/v1/messages` |
| POST | `/v1/chat/completions` |
| POST | `/v1/responses` |
| GET | `/v1/models` |
| GET | `/healthz` |

All other paths → `404` with `LLMREPLAY_ROUTE_DENIED`.

## Modes

```bash
# Record against an upstream (e.g. CCR or a fake server)
llmreplay record --cassette .llmreplay/c --upstream http://127.0.0.1:3456 --port 7432

# Replay offline from cassette (no upstream)
llmreplay replay --cassette .llmreplay/c --port 7432 --profile ci
```

Bind is loopback-only unless `--allow-remote`. Point the agent at the proxy:

```bash
export ANTHROPIC_BASE_URL=http://127.0.0.1:7432
export OPENAI_BASE_URL=http://127.0.0.1:7432/v1
```

## Behavior notes

- Replay miss → `409` with `static_hash`; diagnose with `llmreplay why --request <cassette>/requests/<id>.json`
- `stream: true` → SSE synthesis from the stored final message (record forces non-stream upstream capture)
- `mark-live __llm__` → replay forwards to `--upstream` (needs `--allow-live` under `ci`/`strict`)
- Free keys: see [free-test-stack.md](../free-test-stack.md)
