# Quickstart

```bash
pip install coding-agent-vcr
# Or for development: pip install -e ".[dev]"
export LLMREPLAY_HMAC_KEY=dev-local-hmac
llmreplay doctor
```

## Hermetic first win (recommended)

```bash
# Clone + smoke (no Ollama, no paid APIs):
git clone https://github.com/dmallya93/llmreplay.git && cd llmreplay
pip install -e ".[dev]"
export LLMREPLAY_HMAC_KEY=dev-local-hmac
./scripts/smoke.sh
```

## One-command record + replay

```bash
# Record an agent turn against any upstream:
llmreplay run --mode record --cassette .llmreplay/demo \
  --upstream http://127.0.0.1:3456 -- claude --print "say hi"

# Replay offline:
llmreplay run --mode replay --cassette .llmreplay/demo -- claude --print "say hi"

# Verify cassette health:
llmreplay replay --check --cassette .llmreplay/demo
```

## Two-terminal workflow

```bash
# Terminal A — start proxy:
llmreplay record --cassette .llmreplay/demo --upstream http://127.0.0.1:3456

# Terminal B — point agent at proxy:
export ANTHROPIC_BASE_URL=http://127.0.0.1:7432
export ANTHROPIC_API_KEY="${ANTHROPIC_API_KEY:-unused-local}"
# run one agent turn, then Ctrl-C the proxy

llmreplay replay --check --cassette .llmreplay/demo
llmreplay replay --cassette .llmreplay/demo --profile ci
```

On a miss:

```bash
llmreplay why --cassette .llmreplay/demo --request .llmreplay/demo/requests/<id>.json
```

## Free stack (optional)

If you have Ollama + CCR available, you can use the free test stack:

```bash
eval "$(llmreplay keys create --free --print-env)"
llmreplay record --free --cassette .llmreplay/demo
```

See [free-test-stack.md](free-test-stack.md) for setup.

## Next steps

- [integrations/claude-code.md](integrations/claude-code.md) — Claude Code hooks and plugin
- [integrations/codex.md](integrations/codex.md) — Codex / OpenAI Responses
- [integrations/pytest.md](integrations/pytest.md) — pytest plugin
- [reference/library.md](reference/library.md) — Python API
