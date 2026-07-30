# Codex hello

```bash
llmreplay test-stack up
llmreplay keys create --free --print-env
export OPENAI_BASE_URL=http://127.0.0.1:7432/v1
llmreplay record --free --cassette .llmreplay/codex-hello
# Run Codex against the proxy
llmreplay replay --cassette .llmreplay/codex-hello --profile ci
```

`previous_response_id` is static in the match key — see `tests/test_c9_parity.py`.

See [codex.md](../../docs/integrations/codex.md).
