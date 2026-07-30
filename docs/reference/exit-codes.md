# Exit codes

Stable process exit codes for LLMReplay. Also available via `llmreplay exit-codes`.

| Code | Name | Meaning | Typical next step |
|---|---|---|---|
| 0 | `SUCCESS` | Success | — |
| 1 | `STATIC_MISMATCH` | Static field mismatch on replay | `llmreplay why` → `mark-*` / `tweak` / re-record |
| 2 | `CASSETTE_MISSING` | Cassette or step missing | `llmreplay record` |
| 3 | `LIVE_OR_UPSTREAM_ERROR` | Live step or upstream (CCR/Ollama) failed | `llmreplay test-stack status` |
| 4 | `TEST_STACK_UNHEALTHY` | Free stack not ready | `llmreplay test-stack up` |
| 5 | `SCHEMA_OR_REPAIR_REQUIRED` | Schema migrate or cassette repair needed | `llmreplay migrate` / `repair` |
| 6 | `HOOK_OR_POLICY_DIVERGENCE` | Hook digest or policy mismatch | Fix hooks or re-record |
| 7 | `SECRET_SCRUB_OR_LIMIT` | Secret residual or resource limit | Scrub config / reduce size |
| 8 | `NETWORK_DENIED` | Outbound blocked in `ci`/`strict` | Expected if live attempted |
| 9 | `ROUTE_OR_PROTOCOL` | Proxy route denied or protocol error | Fix base URL / client |

Stderr footers always print `exit N = NAME — …`.

**Note:** Click/Typer may use exit code `2` for CLI usage errors. Application-level `CASSETTE_MISSING` is reserved for successful CLI parse with missing cassette data. Prefer structured `.llmreplay/last-failure.json` when both could apply.
