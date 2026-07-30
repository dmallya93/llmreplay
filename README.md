# LLMReplay

**VCR / time-travel for coding agents.** Record Claude Code or Codex once, then replay offline — stop, tweak, fork, and assert — without burning tokens or waiting on nondeterministic model runs.

[![CI](https://github.com/dmallya93/llmreplay/actions/workflows/ci.yml/badge.svg)](https://github.com/dmallya93/llmreplay/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/coding-agent-vcr.svg?logo=pypi&logoColor=white)](https://pypi.org/project/coding-agent-vcr/)
[![Python](https://img.shields.io/pypi/pyversions/coding-agent-vcr.svg?logo=python&logoColor=white)](https://pypi.org/project/coding-agent-vcr/)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)

> **Status:** Early alpha. See [docs/alpha-limitations.md](docs/alpha-limitations.md).

![LLMReplay demo: record, why, replay](https://raw.githubusercontent.com/dmallya93/llmreplay/main/docs/assets/demo-terminal.jpg)

## Install

```bash
pip install coding-agent-vcr
export LLMREPLAY_HMAC_KEY=dev-local-hmac   # recommended; required for ci/strict record
llmreplay doctor
```

> PyPI package name is **`coding-agent-vcr`** (`llmreplay` / `llm-replay` were taken or blocked as too similar). The CLI and Python import remain `llmreplay`.

## 60-second hermetic win

```bash
# Clone for the smoke script, or use record/replay against your own stub:
git clone https://github.com/dmallya93/llmreplay.git && cd llmreplay
pip install -e ".[dev]"
export LLMREPLAY_HMAC_KEY=dev-local-hmac
./scripts/smoke.sh
# → smoke ok: record→replay (fake upstream)
```

## Record → offline replay

```bash
# Terminal A — CCR (:3456) or any Anthropic/OpenAI-compatible stub
llmreplay record --cassette .llmreplay/demo --upstream http://127.0.0.1:3456

# Terminal B — point Claude Code at the proxy
export ANTHROPIC_BASE_URL=http://127.0.0.1:7432
export ANTHROPIC_API_KEY=unused-local
# run one agent turn, then stop record

llmreplay replay --check --cassette .llmreplay/demo
llmreplay replay --cassette .llmreplay/demo --profile ci

# On a miss:
llmreplay why --cassette .llmreplay/demo --request .llmreplay/demo/requests/<tx-id>.json
```

Prefer free CCR+Ollama: [docs/free-test-stack.md](docs/free-test-stack.md). Longer path: [docs/quickstart.md](docs/quickstart.md).

## Why this exists

Coding agents fail in ways unit tests miss: flaky tool order, prompt regressions, CI that needs live API keys, and bugs you cannot replay. Observability shows *what happened*. LLMReplay decides **what must match** and **re-executes** the trajectory from fixtures.

| You want… | Use |
|---|---|
| Deterministic offline replay + CI goldens | **LLMReplay** |
| Live traces, evals, cost dashboards | [AgentReplay](https://agentreplay.dev/) ([compare](docs/compare-agentreplay.md)) |

## Core ideas

- **static** — must match (drives agent behavior)
- **ignore** — noise (timestamps, request ids); advisory only
- **scrub** — secrets → HMAC placeholders before disk
- **live** — always hit the real tool/LLM for that step (`mark-live`)

Normative rules: [docs/SPEC.md](docs/SPEC.md). Architecture: [DESIGN.md](DESIGN.md).

## Documentation

- [docs/quickstart.md](docs/quickstart.md) — first green replay
- [docs/publishing.md](docs/publishing.md) — PyPI Trusted Publisher + social preview
- [docs/alpha-limitations.md](docs/alpha-limitations.md) — what alpha does / does not claim
- [docs/ci.md](docs/ci.md) — CI / release smoke / nightly
- [docs/compatibility.md](docs/compatibility.md) — supported matrix
- [docs/threat-model.md](docs/threat-model.md) — security boundaries
- [docs/troubleshooting.md](docs/troubleshooting.md) — miss / doctor / bundle
- [docs/reference/cli.md](docs/reference/cli.md) — CLI reference
- [docs/free-test-stack.md](docs/free-test-stack.md) — CCR + Ollama
- [CONTRIBUTING.md](CONTRIBUTING.md) — contributor path & local gates
- [SECURITY.md](SECURITY.md) — reporting & secret handling

## Contributing / local gates

See [CONTRIBUTING.md](CONTRIBUTING.md) and [docs/ci.md](docs/ci.md) for the CI-required validation commands (`pytest`, coverage gate, repro stress, smoke).

## License

Apache-2.0. See [LICENSE](LICENSE).
