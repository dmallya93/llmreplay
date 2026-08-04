# Codex integration

## Zero-config first

```bash
pip install coding-agent-vcr
llmreplay demo
```

## Quick start (`llmreplay run`) — one terminal

```bash
# keep OPENAI_API_KEY in the environment (HMAC defaults locally)

llmreplay run --mode record --cassette .llmreplay/demo \
  --upstream https://api.openai.com -- codex --prompt "say hi"

llmreplay run --mode replay --cassette .llmreplay/demo -- codex --prompt "say hi"
```

`llmreplay run` sets `OPENAI_BASE_URL` / `OPENAI_API_KEY` for the child and tears the proxy down when the child exits. No second terminal.

<details><summary>Advanced: two-terminal proxy (not recommended)</summary>

```bash
export OPENAI_BASE_URL=http://127.0.0.1:7432/v1
export OPENAI_API_KEY=unused-local
llmreplay record --cassette .llmreplay/demo --upstream https://api.openai.com
```

</details>

## Responses API

- Route: `POST /v1/responses` (allowlisted)
- `previous_response_id` is **static** — must match on replay
- Multi-turn goldens: `tests/test_c9_parity.py`

## Troubleshooting

| Symptom | Fix |
|---|---|
| Miss on turn 2 | Check `previous_response_id` / path pins; run `llmreplay why` |
| Tool ID desync | Re-record; IDs are wire literals + `tool_id_map` |
| Empty cassette | Ensure traffic hit the proxy (`OPENAI_BASE_URL` set by `run`) |
