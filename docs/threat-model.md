# Threat model (C10)

Trust boundaries: agent CLI, hooks, LLMReplay proxy, CCR, Ollama/provider, shared cassette storage.

## Threats and mitigations

| Threat | Mitigation |
|---|---|
| Secret capture in cassettes | HMAC scrub + residual refuse on ci/strict; scrubbed `bundle` default |
| Open-proxy / SSRF | Loopback bind default; route allowlist (SPEC S5) |
| Cassette tampering | Atomic writes, exclusive lock, checksums (expandable) |
| Path traversal in snapshots | `resolve_under_root` + archive member checks |
| Token leakage | Auth headers dropped from match; free keys localhost-only |
| Malicious hooks | Digest verify; fail-closed protocol; limited env |
| Replay escape to upstream | Replay mode does not forward; network deny in ci/strict |

See [SECURITY.md](../SECURITY.md) for reporting.
