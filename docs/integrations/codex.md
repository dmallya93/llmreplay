# Codex integration

## Base URL

```bash
export OPENAI_BASE_URL=http://127.0.0.1:7432/v1
export OPENAI_API_KEY=$(llmreplay keys create --free --print-env | …)
llmreplay record --free
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
