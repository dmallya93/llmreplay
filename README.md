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

## Install

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
export LLMREPLAY_HMAC_KEY=dev-local-hmac   # required for ci/strict record; recommended always
llmreplay doctor
```

## Quick start

```bash
# Hermetic first win (fake upstream, no Ollama / paid APIs)
./scripts/smoke.sh
```

### Record → offline replay (agent wiring)

```bash
# Terminal A — prefer free stack if available; else any Anthropic/OpenAI-compatible stub
# eval "$(llmreplay keys create --free --print-env)"
# llmreplay record --free --cassette .llmreplay/demo
llmreplay record --cassette .llmreplay/demo --upstream http://127.0.0.1:3456

# Terminal B — point Claude Code at the proxy
export ANTHROPIC_BASE_URL=http://127.0.0.1:7432
export ANTHROPIC_API_KEY=unused-local
# run one agent turn, then stop record

llmreplay replay --check --cassette .llmreplay/demo
llmreplay replay --cassette .llmreplay/demo --profile ci

# On a miss — use a stored request from the cassette:
llmreplay why --cassette .llmreplay/demo --request .llmreplay/demo/requests/<tx-id>.json
llmreplay bundle --cassette .llmreplay/demo --output /tmp/llmreplay-bundle.zip
```

Free CCR+Ollama: [docs/free-test-stack.md](docs/free-test-stack.md). Longer path: [docs/quickstart.md](docs/quickstart.md).

## Testing & validation

### CI-required (PR / push)

Same as `.github/workflows/ci.yml` (HMAC is generated per job in CI):

```bash
export LLMREPLAY_HMAC_KEY=dev-local-hmac
export LLMREPLAY_CI=1

ruff check src tests
python -m llmreplay.cli.main docs gen --check --output docs/reference/cli.md
pytest -q
bash scripts/mutation_gate.sh      # coverage floor (>=95%); not mutmut
bash scripts/repro_stress.sh       # multi-tool chains + 10× replay identity
bash scripts/smoke.sh              # fake-upstream record→replay
bash scripts/release_smoke.sh      # clean venv install + offline fixture
```

| Check | What it proves |
|---|---|
| `pytest -q` | Unit + contract suite |
| `mutation_gate.sh` | Coverage floor on critical modules |
| `repro_stress.sh` | Parallel tools, chains, OpenAI tools, 10× identical replay |
| `smoke.sh` | End-to-end record→replay with fake upstream |
| `release_smoke.sh` | Installable package; offline fixture replay |
| `docs gen --check` | Generated CLI reference is not stale |

CI matrix: Ubuntu + macOS × Python 3.12/3.13. Details: [docs/ci.md](docs/ci.md).

## Core ideas

- **static** — must match (drives agent behavior)
- **ignore** — noise (timestamps, request ids); advisory only
- **scrub** — secrets → HMAC placeholders before disk
- **live** — always hit the real tool/LLM for that step (`mark-live`)

Normative rules: [docs/SPEC.md](docs/SPEC.md).

## Documentation

- [docs/quickstart.md](docs/quickstart.md) — first green replay
- [docs/alpha-limitations.md](docs/alpha-limitations.md) — what alpha does / does not claim
- [docs/ci.md](docs/ci.md) — CI / release smoke / nightly
- [docs/compatibility.md](docs/compatibility.md) — supported matrix
- [docs/threat-model.md](docs/threat-model.md) — security boundaries
- [docs/troubleshooting.md](docs/troubleshooting.md) — miss / doctor / bundle
- [docs/reference/cli.md](docs/reference/cli.md) — generated CLI reference
- [docs/reference/llmreplay-yaml.md](docs/reference/llmreplay-yaml.md) — profile config
- [docs/free-test-stack.md](docs/free-test-stack.md) — CCR + Ollama
- [DESIGN.md](DESIGN.md) — architecture, design locks, and usage
- [docs/SPEC.md](docs/SPEC.md) — normative implementation contract
- [CONTRIBUTING.md](CONTRIBUTING.md) — contributor path
- [SUPPORT.md](SUPPORT.md) — what we will / will not support
- [SECURITY.md](SECURITY.md) — reporting & secret handling

## License

Apache-2.0. See [LICENSE](LICENSE).
