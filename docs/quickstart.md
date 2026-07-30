# Quickstart

## Install

```bash
pip install coding-agent-vcr
export LLMREPLAY_HMAC_KEY=dev-local-hmac
llmreplay doctor
```

## Hermetic first win (recommended)

No Ollama, no API keys, no network — just clone and smoke:

```bash
git clone https://github.com/dmallya93/llmreplay.git && cd llmreplay
pip install -e ".[dev]"
export LLMREPLAY_HMAC_KEY=dev-local-hmac
./scripts/smoke.sh
# ✓ smoke ok: record→replay (fake upstream)
```

## One-command record + replay

The `llmreplay run` command starts the proxy, runs your agent, and tears everything down:

```bash
# Record an agent turn against any upstream:
llmreplay run --mode record --cassette .llmreplay/demo \
  --upstream http://127.0.0.1:3456 -- claude --print "say hi"

# Replay offline — deterministic, zero cost:
llmreplay run --mode replay --cassette .llmreplay/demo -- claude --print "say hi"

# Verify cassette health:
llmreplay replay --check --cassette .llmreplay/demo
```

```
  What happens under the hood:

  ┌────────────────────────────────────────────────────────────┐
  │  llmreplay run                                             │
  │    1. Start proxy on 127.0.0.1:7432                        │
  │    2. Set ANTHROPIC_BASE_URL + OPENAI_BASE_URL for child   │
  │    3. Run your command (claude, codex, pytest, etc.)        │
  │    4. Propagate child exit code                             │
  │    5. Tear down proxy                                       │
  └────────────────────────────────────────────────────────────┘
```

## Diagnose a miss

When replay doesn't match, `why` shows you the diff:

```bash
llmreplay why --cassette .llmreplay/demo \
  --request .llmreplay/demo/requests/<tx-id>.json
```

<details><summary><b>Two-terminal workflow (advanced)</b></summary>

```bash
# Terminal A — start proxy:
llmreplay record --cassette .llmreplay/demo --upstream http://127.0.0.1:3456

# Terminal B — point agent at proxy:
export ANTHROPIC_BASE_URL=http://127.0.0.1:7432
export ANTHROPIC_API_KEY="${ANTHROPIC_API_KEY:-unused-local}"
claude --print "say hi"
# then Ctrl-C the proxy

llmreplay replay --check --cassette .llmreplay/demo
llmreplay replay --cassette .llmreplay/demo --profile ci
```

</details>

## Free stack (optional)

If you have Ollama + CCR available, you can use the free test stack:

```bash
eval "$(llmreplay keys create --free --print-env)"
llmreplay record --free --cassette .llmreplay/demo
```

See [free-test-stack.md](free-test-stack.md) for setup.

## Next steps

| What | Where |
|---|---|
| Claude Code integration | [integrations/claude-code.md](integrations/claude-code.md) |
| Codex / OpenAI Responses | [integrations/codex.md](integrations/codex.md) |
| pytest plugin | [integrations/pytest.md](integrations/pytest.md) |
| Python library API | [reference/library.md](reference/library.md) |
| CI setup | [ci.md](ci.md) |
| Portable cassettes | [portable-cassettes.md](portable-cassettes.md) |
