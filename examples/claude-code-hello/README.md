# Claude Code hello

Minimal wiring (after free stack is up):

```bash
llmreplay test-stack up
llmreplay keys create --free --print-env   # eval exports
llmreplay hooks install --mode record
llmreplay record --free --cassette .llmreplay/claude-hello
# Run Claude Code with ANTHROPIC_BASE_URL pointing at the proxy
llmreplay replay --cassette .llmreplay/claude-hello --profile ci
```

Protocol goldens for multi-turn tool_use live in `tests/test_c9_parity.py` (hermetic).

See [claude-code.md](../../docs/integrations/claude-code.md).
