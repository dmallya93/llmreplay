# LLMReplay

**VCR / time-travel for coding agents.** Record Claude Code or Codex sessions once, then replay them offline — stop, tweak, fork, and assert — without burning tokens or waiting on nondeterministic model runs.

[![CI](https://github.com/dmallya93/llmreplay/actions/workflows/ci.yml/badge.svg)](https://github.com/dmallya93/llmreplay/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)

> **Status:** Early alpha. See [docs/alpha-limitations.md](docs/alpha-limitations.md) and [DESIGN.md](DESIGN.md).

## Motivation

Coding agents fail in ways unit tests miss: flaky tool order, prompt regressions, CI that needs live API keys, and bugs you cannot replay. Observability tools show *what happened*. LLMReplay decides **what must match** and **re-executes** the trajectory from fixtures.

| You want… | Use |
|---|---|
| Deterministic offline replay + CI goldens | **LLMReplay** |
| Live traces, evals, cost dashboards | [AgentReplay](https://agentreplay.dev/) (see [compare](docs/compare-agentreplay.md)) |

## Quick start

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
llmreplay doctor
./scripts/smoke.sh    # hermetic record→replay (fake upstream)
```

### Wire an agent (after smoke is green)

```bash
# Record against a real upstream (CCR default :3456, or any OpenAI/Anthropic-compatible stub)
llmreplay record --cassette .llmreplay/demo --upstream http://127.0.0.1:3456

# Claude Code — point at the proxy (separate terminal)
export ANTHROPIC_BASE_URL=http://127.0.0.1:7432
export ANTHROPIC_API_KEY=unused-local
# run one agent turn, then stop record

llmreplay replay --check --cassette .llmreplay/demo
llmreplay replay --cassette .llmreplay/demo --profile ci

# On a miss — use a stored request blob from the cassette:
llmreplay why --cassette .llmreplay/demo --request .llmreplay/demo/requests/<tx-id>.json
llmreplay bundle --cassette .llmreplay/demo --output /tmp/llmreplay-bundle.zip
```

Free CCR+Ollama: [docs/free-test-stack.md](docs/free-test-stack.md). Full path: [docs/quickstart.md](docs/quickstart.md).

See [docs/troubleshooting.md](docs/troubleshooting.md) and [docs/reference/cli.md](docs/reference/cli.md).

## Core ideas

- **static** — must match (drives agent behavior)
- **ignore** — noise (timestamps, request ids); advisory only
- **scrub** — secrets → HMAC placeholders before disk
- **live** — always hit the real tool/LLM for that step

Normative rules: [docs/SPEC.md](docs/SPEC.md).

## Documentation

- [docs/alpha-limitations.md](docs/alpha-limitations.md) — what alpha does / does not claim
- [docs/ci.md](docs/ci.md) — CI / release smoke / nightly
- [docs/compatibility.md](docs/compatibility.md) — supported matrix
- [docs/threat-model.md](docs/threat-model.md) — security boundaries
- [docs/troubleshooting.md](docs/troubleshooting.md) — miss / doctor / bundle starters
- [docs/reference/cli.md](docs/reference/cli.md) — generated CLI reference
- [docs/reference/llmreplay-yaml.md](docs/reference/llmreplay-yaml.md) — profile config
- [docs/free-test-stack.md](docs/free-test-stack.md) — CCR + Ollama
- [DESIGN.md](DESIGN.md) — architecture, design locks, and usage
- [docs/SPEC.md](docs/SPEC.md) — normative implementation contract
- [CONTRIBUTING.md](CONTRIBUTING.md) — 30-minute contributor path
- [SUPPORT.md](SUPPORT.md) — what we will / will not support
- [SECURITY.md](SECURITY.md) — reporting & secret handling

## License

Apache-2.0. See [LICENSE](LICENSE).
