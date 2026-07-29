# Free test-stack (CCR + Ollama)

Local $0 LLM path for record/replay (SPEC S8):

```text
Agent → LLMReplay proxy → CCR → Ollama
```

## Quick path

```bash
llmreplay test-stack up
# follow printed instructions: ollama pull, install CCR, copy config

llmreplay test-stack status --json   # exit 4 if Ollama down
llmreplay keys create --free --print-env
# eval the printed exports, then:
llmreplay record --upstream http://127.0.0.1:3456
```

Free keys are **localhost-only** and quota-limited. Tokens must never appear in cassettes (scrub / drop auth headers already).

## Degraded mode

If CCR is down but Ollama is up, point `--upstream` at Ollama’s OpenAI-compatible API (`http://127.0.0.1:11434/v1`) for Chat Completions. Anthropic Messages may need CCR or a translator.

## CI / smoke

PR CI stays hermetic (fake upstream). Optional local/nightly:

```bash
./scripts/smoke.sh          # uses fake upstream if Ollama unavailable
./scripts/smoke.sh --ollama # require real Ollama
```

See `examples/hello-fake-upstream/` for a network-free demo.
