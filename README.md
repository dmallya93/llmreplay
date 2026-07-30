# LLMReplay

**VCR / time-travel for coding agents.** Record Claude Code or Codex sessions once, then replay them offline — stop, tweak, fork, and assert — without burning tokens or waiting on nondeterministic model runs.

[![CI](https://github.com/dmallya93/llmreplay/actions/workflows/ci.yml/badge.svg)](https://github.com/dmallya93/llmreplay/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)

> **Status:** Early alpha. Chunks ship incrementally. See [DESIGN.md](DESIGN.md) for architecture and progress.

## Motivation

Coding agents fail in ways unit tests miss: flaky tool order, prompt regressions, CI that needs live API keys, and bugs you cannot replay. Observability tools show *what happened*. LLMReplay decides **what must match** and **re-executes** the trajectory from fixtures.

| You want… | Use |
|---|---|
| Deterministic offline replay + CI goldens | **LLMReplay** |
| Live traces, evals, cost dashboards | [AgentReplay](https://agentreplay.dev/) (see [compare](docs/compare-agentreplay.md)) |

## Deliverables (roadmap)

| Chunk | Capability | Status |
|---|---|---|
| C0 | OSS bootstrap, SPEC, CLI skeleton, exit codes | **Done** (`3056aca`) |
| C1 | Field model, cassette store, match/hash | **Done** (`6f35e2e`) |
| C2 | Local proxy (Anthropic + OpenAI + Responses) | **Done** (`23da04d`) |
| C3 | HMAC scrub + profiles | **Done** (`3f2486f`) |
| C4 | `record` / `replay` / `why` / `doctor` / `bundle` | **Done** (`07586ae`) |
| C5 | Free test-stack (CCR + Ollama) | **Done** (`ddd979c`) |
| C6–C10 | Snapshots, hooks, fork/tweak, agent parity, release | C6–C8 **Done** (pending); C9–C10 planned |

## Quick start

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
llmreplay doctor
```

### Vertical demo (fake upstream → record → replay)

```bash
# Terminal A — fake upstream (any OpenAI/Anthropic-compatible stub)
# Terminal B — record into a cassette
llmreplay record --cassette .llmreplay/demo --upstream http://127.0.0.1:3456

# Point ANTHROPIC_BASE_URL / OPENAI_BASE_URL at http://127.0.0.1:7432 and run the agent once.
# Then replay offline (no upstream):
llmreplay replay --cassette .llmreplay/demo --profile ci
llmreplay replay --check --cassette .llmreplay/demo

# On a miss:
llmreplay why --cassette .llmreplay/demo --request /path/to/request.json
llmreplay bundle --cassette .llmreplay/demo --output /tmp/llmreplay-bundle.zip
```

Contract tests cover the same harness without a live server. Free CCR+Ollama stack lands in **C5**.

See [docs/troubleshooting.md](docs/troubleshooting.md), [docs/reference/cli.md](docs/reference/cli.md), and [docs/free-test-stack.md](docs/free-test-stack.md).

## Core ideas

- **static** — must match (drives agent behavior)
- **ignore** — noise (timestamps, request ids); advisory only
- **scrub** — secrets → HMAC placeholders before disk
- **live** — always hit the real tool/LLM for that step

Normative rules: [docs/SPEC.md](docs/SPEC.md).

## Documentation

- [docs/troubleshooting.md](docs/troubleshooting.md) — miss / doctor / bundle starters
- [docs/reference/cli.md](docs/reference/cli.md) — generated CLI reference
- [docs/reference/llmreplay-yaml.md](docs/reference/llmreplay-yaml.md) — profile config
- [DESIGN.md](DESIGN.md) — architecture + progress tracker
- [docs/SPEC.md](docs/SPEC.md) — normative implementation contract
- [CONTRIBUTING.md](CONTRIBUTING.md) — 30-minute contributor path
- [SUPPORT.md](SUPPORT.md) — what we will / will not support
- [SECURITY.md](SECURITY.md) — reporting & secret handling

## License

Apache-2.0. See [LICENSE](LICENSE).
