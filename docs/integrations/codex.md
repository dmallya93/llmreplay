# Codex integration

## Quick start (`llmreplay run`)

```bash
# Record one Codex turn
llmreplay run --mode record --cassette .llmreplay/demo \
  --upstream http://127.0.0.1:3456 -- codex --prompt "say hi"

# Replay offline
llmreplay run --mode replay --cassette .llmreplay/demo -- codex --prompt "say hi"
```

`llmreplay run` sets `OPENAI_BASE_URL` / `OPENAI_API_KEY` automatically.

## Two-terminal workflow

```bash
export OPENAI_BASE_URL=http://127.0.0.1:7432/v1
export OPENAI_API_KEY=unused-local
llmreplay record --cassette .llmreplay/demo --upstream http://127.0.0.1:3456
```

## Responses API

- Route: `POST /v1/responses` (allowlisted)
- `previous_response_id` is **static** — must match on replay
- Multi-turn goldens: `tests/test_c9_parity.py`

## Troubleshooting

| Symptom | Fix |
|---|---|
| Miss on turn 2 | Check `previous_response_id` / path pins; run `llmreplay why` |
| Tool ID desync | Re-record; IDs are wire literals + `tool_id_map` |
| Path drift across machines | Use `llmreplay template path_rebase` / workspace env paths |

Free stack: [free-test-stack.md](../free-test-stack.md).
