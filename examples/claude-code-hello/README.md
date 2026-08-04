# Claude Code hello

**One terminal. No free keys. No second window.**

```bash
pip install coding-agent-vcr
llmreplay demo   # zero-config start→end

# Real agent (proxy starts + tears down with the child):
llmreplay run --mode record --cassette .llmreplay/claude-hello \
  --upstream https://api.anthropic.com -- claude --print "say hi"
llmreplay run --mode replay --cassette .llmreplay/claude-hello \
  -- claude --print "say hi"
```

Optional CCR+Ollama free stack: [free-test-stack.md](../../docs/free-test-stack.md).

Protocol goldens for multi-turn tool_use live in `tests/test_c9_parity.py` (hermetic).

See [claude-code.md](../../docs/integrations/claude-code.md).
