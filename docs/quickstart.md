# Quickstart

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
# Or from PyPI (no clone): pip install llm-replay
# Stable scrub placeholders across record/replay (required for ci/strict record):
export LLMREPLAY_HMAC_KEY=dev-local-hmac
llmreplay doctor
```

## Hermetic first win (recommended)

```bash
./scripts/smoke.sh
# Or full reproducibility suite (parallel tools, chains, 10× identical replay):
bash scripts/repro_stress.sh
```

These use an in-process fake upstream — no Ollama, no paid APIs. If smoke is green, the match/proxy path works.

## Manual agent wiring (after smoke)

```bash
# Prefer free stack if you have Ollama+CCR:
eval "$(llmreplay keys create --free --print-env)"
llmreplay record --free --cassette .llmreplay/demo

# Or point at any Anthropic/OpenAI-compatible stub:
# llmreplay record --cassette .llmreplay/demo --upstream http://127.0.0.1:3456

# Agent env (Claude):
export ANTHROPIC_BASE_URL=http://127.0.0.1:7432
export ANTHROPIC_API_KEY="${ANTHROPIC_API_KEY:-unused-local}"
# run one agent turn — if cassette stays empty, traffic missed the proxy
# Ctrl-C the record proxy when done

llmreplay replay --check --cassette .llmreplay/demo
llmreplay replay --cassette .llmreplay/demo --profile ci
```

On a miss:

```bash
llmreplay why --cassette .llmreplay/demo --request .llmreplay/demo/requests/<id>.json
```

See [free-test-stack.md](free-test-stack.md), [integrations/claude-code.md](integrations/claude-code.md).
