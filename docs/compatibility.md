# Compatibility matrix

| Component | Supported |
|---|---|
| Python | 3.12, 3.13 |
| OS (CI) | Ubuntu (required), macOS (CI matrix) |
| Agents | Claude Code (Anthropic Messages), Codex (OpenAI Chat Completions + Responses) |
| Free stack | CCR + Ollama (`qwen2.5-coder` class models with tool calling preferred) |
| Cassette schema | `schema_version` **1** (migrate from 0 via `llmreplay migrate`) |

Unknown agent versions: require `--allow-unknown-agent` (future) and mark cassette `unverified`.

Replay only reproduces what was captured — uncaptured MCP/DB side effects are out of scope ([SUPPORT.md](../SUPPORT.md)).
