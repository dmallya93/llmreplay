# Quickstart

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
llmreplay doctor
```

## Hermetic path (no Ollama) — recommended first win

```bash
./scripts/smoke.sh
# Or: pytest -q
```

That exercises record→replay against an in-process fake upstream.

## Manual record → offline replay

```bash
# Terminal A — any Anthropic/OpenAI-compatible stub on :3456
# Terminal B:
llmreplay record --cassette .llmreplay/demo --upstream http://127.0.0.1:3456

# Wire the agent (Claude example):
export ANTHROPIC_BASE_URL=http://127.0.0.1:7432
export ANTHROPIC_API_KEY=unused-local
# run one agent turn, then stop the record proxy

llmreplay replay --check --cassette .llmreplay/demo
llmreplay replay --cassette .llmreplay/demo --profile ci
```

On a miss, point `why` at a stored request blob:

```bash
llmreplay why --cassette .llmreplay/demo --request .llmreplay/demo/requests/<id>.json
```

## Free stack (local Ollama + CCR)

```bash
llmreplay test-stack up
llmreplay test-stack status          # exit 4 if Ollama down
eval "$(llmreplay keys create --free --print-env)"
llmreplay record --free --cassette .llmreplay/demo
# agent turn with env from --print-env
llmreplay replay --cassette .llmreplay/demo --profile ci
```

Details: [free-test-stack.md](free-test-stack.md). Integrations: [integrations/claude-code.md](integrations/claude-code.md), [integrations/codex.md](integrations/codex.md).
