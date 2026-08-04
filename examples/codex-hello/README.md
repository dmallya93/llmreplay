# Codex hello

**One terminal. No free keys. No second window.**

```bash
pip install coding-agent-vcr
llmreplay demo   # zero-config start→end

llmreplay run --mode record --cassette .llmreplay/codex-hello \
  --upstream https://api.openai.com -- codex --prompt "say hi"
llmreplay run --mode replay --cassette .llmreplay/codex-hello \
  -- codex --prompt "say hi"
```

`previous_response_id` is static in the match key — see `tests/test_c9_parity.py`.

Optional CCR+Ollama: [free-test-stack.md](../../docs/free-test-stack.md).

See [codex.md](../../docs/integrations/codex.md).
