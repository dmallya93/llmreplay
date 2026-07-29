# Field classes

| Class | Match behavior | Inject on replay | Examples |
|---|---|---|---|
| **static** | Must equal after normalize | Recorded literal | model, tools, messages, tool args/results, finish_reason, tool_use IDs |
| **ignore** | Excluded from hash; advisory only | Recorded literal | usage, latency, request ids, Date headers |
| **scrub** | Placeholder must equal | `«REDACTED:hmac:…»` | Authorization, API keys |
| **live** | Never served from cassette | Real LLM/tool call | Explicit per-tool/step |
| **template** | Static after allowlisted materialize | Rematerialized value | path rebase, uuid (opt-in) |

**Rule:** If a field influences what the agent does next, it is **static**.

When people say “dynamic,” they mean **ignore** (noise) or **live** (must hit the world)—pick one. LLMReplay never auto-promotes a mismatch to ignore.

Implementation: `llmreplay.core.match.match_key` + `llmreplay.core.volatility`.
