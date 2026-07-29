# Proxy (C2)

Local allowlisted reverse proxy for Claude Code / Codex base URLs.

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
llmreplay proxy --mode record --cassette .llmreplay/c \
  --upstream http://127.0.0.1:3456 --port 7432

# Replay offline from cassette (no upstream)
llmreplay proxy --mode replay --cassette .llmreplay/c --port 7432
```

Point the agent at the proxy:

```bash
export ANTHROPIC_BASE_URL=http://127.0.0.1:7432
export OPENAI_BASE_URL=http://127.0.0.1:7432/v1
```

Replay misses return `409` with `static_hash` for diagnostics (full `why` lands in C4).
