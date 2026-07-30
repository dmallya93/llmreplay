# Threat model

Trust boundaries: agent CLI, hooks, LLMReplay proxy, CCR, Ollama/provider, shared cassette storage.

## Threats and mitigations

| Threat | Mitigation |
|---|---|
| Secret capture in cassettes | HMAC scrub + residual refuse on ci/strict; scrubbed `bundle` default |
| Open-proxy / SSRF | Loopback bind for record **and** replay unless `--allow-remote` **with** `--free` (free-key auth); route allowlist (SPEC S5) |
| Cassette tampering | Atomic writes, exclusive lock, checksums |
| Path traversal in snapshots | `resolve_under_root` + archive member checks |
| Token leakage | Auth headers scrubbed; free keys loopback-only unless `--allow-remote --free` |
| Malicious hooks | Digest verify (`hooks verify`); fail-closed protocol; limited env |
| Replay escape to upstream | Unmarked replay does not forward; `ci`/`strict` refuse `mark-live __llm__` without `--allow-live` |
| Unstable scrub across CI jobs | `ci`/`strict` record requires `LLMREPLAY_HMAC_KEY` |

See [SECURITY.md](../SECURITY.md) for reporting and [alpha-limitations.md](alpha-limitations.md) for known gaps.
