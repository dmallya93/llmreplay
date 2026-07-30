# LLMReplay

**VCR / time-travel for coding agents.** Record Claude Code or Codex once, then replay offline — stop, tweak, fork, and assert — without burning tokens or waiting on nondeterministic model runs.

[![CI](https://github.com/dmallya93/llmreplay/actions/workflows/ci.yml/badge.svg)](https://github.com/dmallya93/llmreplay/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/coding-agent-vcr.svg?logo=pypi&logoColor=white)](https://pypi.org/project/coding-agent-vcr/)
[![Python](https://img.shields.io/pypi/pyversions/coding-agent-vcr.svg?logo=python&logoColor=white)](https://pypi.org/project/coding-agent-vcr/)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)

> **Status:** Early alpha. See [docs/alpha-limitations.md](docs/alpha-limitations.md).

![LLMReplay demo: record, why, replay](https://raw.githubusercontent.com/dmallya93/llmreplay/main/docs/assets/demo-terminal.jpg)

---

## Get started in 30 seconds

```bash
pip install coding-agent-vcr
export LLMREPLAY_HMAC_KEY=dev-local-hmac
llmreplay doctor
```

> **Note:** PyPI package name is `coding-agent-vcr` (other names were taken). The CLI and import remain `llmreplay`.

---

## Record, replay, diagnose

```bash
# 1. Record an agent turn (proxy + child in one process):
llmreplay run --mode record --cassette .llmreplay/demo \
  --upstream http://127.0.0.1:3456 -- claude --print

# 2. Replay offline — deterministic, no tokens burned:
llmreplay run --mode replay --cassette .llmreplay/demo -- claude --print

# 3. On a miss — see exactly what changed:
llmreplay why --cassette .llmreplay/demo --request .llmreplay/demo/requests/<tx-id>.json

# 4. Check cassette health for CI:
llmreplay replay --check --cassette .llmreplay/demo
```

<details><summary>Two-terminal workflow (advanced)</summary>

```bash
# Terminal A — start proxy
llmreplay record --cassette .llmreplay/demo --upstream http://127.0.0.1:3456

# Terminal B — point agent at proxy
export ANTHROPIC_BASE_URL=http://127.0.0.1:7432
export ANTHROPIC_API_KEY=unused-local
# run one agent turn, then Ctrl-C the proxy

llmreplay replay --cassette .llmreplay/demo --profile ci
```

</details>

---

## Why this exists

Coding agents fail in ways unit tests miss:

| Problem | Without LLMReplay | With LLMReplay |
|---|---|---|
| Flaky tool order across runs | Re-run and hope | Sorted canonically, deterministic match |
| Prompt regressions | Unnoticed until prod | Golden cassettes catch diffs in CI |
| CI needs live API keys + tokens | Expensive, slow, brittle | Fully offline replay from fixtures |
| Can't reproduce that weird agent bug | "Works on my machine" | Fork cassette at turn N, tweak, replay |

> Observability shows *what happened*. LLMReplay decides **what must match** and **re-executes** the trajectory.

---

## Core ideas

```
            record                     replay
Agent ──→ LLMReplay Proxy ──→ LLM    Agent ──→ LLMReplay Proxy ──→ Cassette
              │                                     │
              ▼                                     ▼
          Cassette (scrubbed)              Match by SHA-256 key
```

Every request/response field is classified:

| Field class | Meaning | Example |
|---|---|---|
| **static** | Must match — drives agent behavior | `model`, `messages`, `tools` |
| **ignore** | Noise — stripped before hashing | `timestamp`, `request_id` |
| **scrub** | Secrets replaced with HMAC placeholders | API keys, tokens |
| **live** | Always hit the real tool/LLM | `mark-live Bash`, `mark-live __llm__` |

Normative rules: [SPEC.md](docs/SPEC.md). Architecture: [DESIGN.md](DESIGN.md).

---

## Integrations

| Agent | Quick start |
|---|---|
| Claude Code | `llmreplay run --mode record -- claude --print "hi"` |
| Codex | `llmreplay run --mode record -- codex --prompt "hi"` |
| pytest | `@pytest.mark.llmreplay(cassette="...")` + `llmreplay_cassette` fixture |
| GitHub Actions | Copy [`examples/github-actions/llmreplay-replay.yml`](examples/github-actions/llmreplay-replay.yml) |
| Any agent | Set `ANTHROPIC_BASE_URL` or `OPENAI_BASE_URL` to the proxy |

---

## Use as a library

```python
from llmreplay import ReplayTransport
import httpx

transport = ReplayTransport(cassette_dir=Path(".llmreplay/cassette"))
async with httpx.AsyncClient(transport=transport, base_url="http://llmreplay") as client:
    resp = await client.post("/v1/messages", json={...})
```

Full API: [docs/reference/library.md](docs/reference/library.md).

---

## Hermetic smoke test

```bash
git clone https://github.com/dmallya93/llmreplay.git && cd llmreplay
pip install -e ".[dev]"
export LLMREPLAY_HMAC_KEY=dev-local-hmac
./scripts/smoke.sh
# smoke ok: record→replay (fake upstream)
```

No Ollama, no paid APIs, no network — pure in-process replay.

---

## Documentation

| Category | Links |
|---|---|
| **Getting started** | [Quickstart](docs/quickstart.md) / [Alpha limitations](docs/alpha-limitations.md) |
| **Reference** | [CLI](docs/reference/cli.md) / [Library API](docs/reference/library.md) / [SPEC](docs/SPEC.md) |
| **Integrations** | [Claude Code](docs/integrations/claude-code.md) / [Codex](docs/integrations/codex.md) / [pytest](docs/integrations/pytest.md) |
| **Operations** | [CI](docs/ci.md) / [Portable cassettes](docs/portable-cassettes.md) / [Troubleshooting](docs/troubleshooting.md) |
| **Security** | [Threat model](docs/threat-model.md) / [SECURITY.md](SECURITY.md) |
| **Optional** | [Free test-stack](docs/free-test-stack.md) (CCR+Ollama, $0 local LLM) |
| **Contributing** | [CONTRIBUTING.md](CONTRIBUTING.md) / [Publishing](docs/publishing.md) |

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) and [docs/ci.md](docs/ci.md) for the CI-required validation commands (`pytest`, coverage gate, repro stress, smoke).

## License

Apache-2.0. See [LICENSE](LICENSE).
