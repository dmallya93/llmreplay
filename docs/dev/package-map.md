# Package map

Where code and docs live for each subsystem (see also [DESIGN.md](../../DESIGN.md)).

| Package | Responsibility | Docs |
|---|---|---|
| `llmreplay.cli`, `llmreplay.core.exit_codes` | CLI, exit codes (`run` wrapper) | README, SPEC, SUPPORT, reference/cli |
| `llmreplay.core.match`, `llmreplay.store` | Match / cassette store | concepts/field-classes, cassette schema |
| `llmreplay.proxy` | Allowlisted proxy + SSE | architecture in DESIGN, ProxyConfig |
| `llmreplay.adapters` | ProtocolAdapter registry (Anthropic / OpenAI SSE) | DESIGN package map, tests/test_adapters |
| `llmreplay.transport` | In-process `ReplayTransport` / `RecordTransport` | reference/library |
| `llmreplay.pytest_plugin` | pytest marker + `llmreplay_cassette` fixture | integrations/pytest |
| `llmreplay.scrub`, `llmreplay.config` | HMAC scrub, profiles | llmreplay-yaml reference |
| `llmreplay.diagnose` | why / doctor / validate / bundle / mark-* | troubleshooting, quickstart |
| `llmreplay.teststack` | CCR + Ollama + free keys | free-test-stack.md, examples |
| `llmreplay.snapshot` | FS snapshots | concepts/snapshots |
| `llmreplay.hooks` | Claude Code hooks | integrations/claude-code |
| `llmreplay.lineage` | fork / tweak / sticky | concepts/fork-tweak |
| `llmreplay.session` | Nested cassette digests | DESIGN nested sessions |
| `llmreplay.parity` | Agent protocol goldens | integrations/* |
| `llmreplay.migrate` | Schema migrate | ci.md, compatibility |
| `plugins/llmreplay` | Claude Code plugin + skills | integrations/claude-code |
