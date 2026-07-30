# Support

## Community (default)

| | |
|---|---|
| **Channels** | [GitHub Discussions](https://github.com/dmallya93/llmreplay/discussions) (usage), [Issues](https://github.com/dmallya93/llmreplay/issues) (bugs), private security reports via [SECURITY.md](SECURITY.md) |
| **SLA** | None — best effort. Security acknowledgment target: 5 business days |

### We support

- Latest stable LLMReplay
- Documented Claude Code / Codex / CCR / Ollama / OS combinations — see [docs/compatibility.md](docs/compatibility.md)
- Reproducible failures with scrubbed cassette or `llmreplay bundle` + `llmreplay doctor --json`
- Matcher, migrate, scrub, and security defects

### We do not support

- Arbitrary application or prompt debugging
- Model quality / Ollama performance tuning
- Provider billing, quotas, or outages
- Undocumented agent forks
- Raw production secrets in public issues
- Guarantees that replay reproduces **uncaptured** external side effects (remote MCP, DBs, etc.)

## Issue template essentials

Include: `llmreplay doctor --json`, versions, profile/mode, OS, scrubbed minimal cassette or bundle, expected vs actual, `why` output when available.

## Optional paid support

Not offered at launch. If added later, it buys responsiveness (CI rollout, scrub review, training) — not gated core bugfixes.
