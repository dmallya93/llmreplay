# Quickstart

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
llmreplay doctor
```

## Fake upstream (CI / no Ollama)

```bash
./scripts/smoke.sh
```

## Free stack (local Ollama + CCR)

```bash
llmreplay test-stack up
llmreplay test-stack status          # exit 4 if Ollama down
llmreplay keys create --free --print-env
# eval printed exports, then:
llmreplay record --free --cassette .llmreplay/demo
llmreplay replay --free --cassette .llmreplay/demo
```

Details: [free-test-stack.md](free-test-stack.md).
