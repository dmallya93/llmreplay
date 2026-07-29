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
| C0 | OSS bootstrap, SPEC, CLI skeleton, exit codes | **Done** |
| C1 | Field model, cassette store, match/hash | Planned |
| C2 | Local proxy (Anthropic + OpenAI + Responses) | Planned |
| C3 | HMAC scrub + profiles | Planned |
| C4 | `record` / `replay` / `why` / `doctor` / `bundle` | Planned |
| C5 | Free test-stack (CCR + Ollama) | Planned |
| C6–C10 | Snapshots, hooks, fork/tweak, agent parity, release | Planned |

## Quick start (C0)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
llmreplay --help
llmreplay version
llmreplay doctor
```

Full free-stack record/replay lands in **C5**. Until then, the CLI exposes version, doctor stubs, and the exit-code contract.

## Core ideas

- **static** — must match (drives agent behavior)
- **ignore** — noise (timestamps, request ids); advisory only
- **scrub** — secrets → HMAC placeholders before disk
- **live** — always hit the real tool/LLM for that step

Normative rules: [docs/SPEC.md](docs/SPEC.md).

## Documentation

- [DESIGN.md](DESIGN.md) — architecture + progress tracker
- [docs/SPEC.md](docs/SPEC.md) — normative implementation contract
- [CONTRIBUTING.md](CONTRIBUTING.md) — 30-minute contributor path
- [SUPPORT.md](SUPPORT.md) — what we will / will not support
- [SECURITY.md](SECURITY.md) — reporting & secret handling

## License

Apache-2.0. See [LICENSE](LICENSE).
