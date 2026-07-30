# LLMReplay Normative Specification

**Status:** Locked (architecture score 10/10).  
**Language:** MUST / MUST NOT / SHOULD.  
**Process:** Any new behavior requires an amend to this document in the same PR as code.

See [DESIGN.md](../DESIGN.md) for motivation, chunks, validation, and customer/support model.

---

## Field classes

| Class | Match | Inject | Examples |
|---|---|---|---|
| `static` | Must equal after normalize | Recorded literal | model, tools, messages, tool args/results, finish_reason, hook decisions, tool_use IDs |
| `ignore` | Excluded from hash; advisory diff | Recorded literal | usage, latency, `x-request-id` |
| `scrub` | Placeholder must equal | `«REDACTED:hmac:…»` | Authorization, API keys |
| `live` | Never from cassette | Real call | Explicit per-tool/step |
| `template` | Static after materialize | Allowlisted rematerializers only | path rebase, uuid.v4 |

**Rule:** If a field influences what the agent does next, it is **static**. User “dynamic” means **ignore** or **live** — pick one. Never auto-promote mismatch → ignore.

---

## S1. Canonicalization and hashing

- MUST canonicalize JSON per **RFC 8785 (JCS)** via pinned `rfc8785`.
- MUST encode UTF-8; Unicode NFC for path strings.
- **Static projection:** deep-copy → delete `ignore` paths → keep `static` + `scrub` placeholders → JCS bytes.
- **Match key:** `SHA-256(static_projection_jcs_bytes)` hex lowercase.
- MUST sort parallel `tool_use` / `tool_result` by `(name, JCS(input), tool_use_id)` before projection; store raw order; strip annotations before forwarding.
- Thinking/reasoning blocks MUST be excluded from hash; stored under `thinking_blocks`; not required for match.

## S2. Scrub and stream redact

- MUST scrub request/response **before cassette write** and before any log that includes body content.
- For buffered JSON proxy requests (current default), MUST apply regex + sensitive-key scrub to the normalized event immediately after parse; raw upstream forward may keep original bytes.
- Full SSE **byte-stream** ingress redact MUST land with streaming capture (S6); until then, synthesized SSE from scrubbed final messages is sufficient.
- Placeholder: `«REDACTED:hmac:<hex16>»` = first 16 hex chars of `HMAC-SHA-256(key, secret_utf8)`.
- HMAC key from `LLMREPLAY_HMAC_KEY` (required in CI) or OS keyring (doctor surface, C4+); MUST NOT appear in cassettes/default bundles/logs. Local-only ephemeral fallback is allowed when unset.
- Detection: packaged `default_patterns.yaml` — `sensitive_keys` + dotted `scrub_paths` (starter path pack) + regex (JWT, `AKIA`, `ghp_`, `sk-`, PEM, `xox*`); residual detector **MUST fail** `strict`/`ci` record (HTTP 422 `llmreplay_secret`, exit `SECRET_SCRUB_OR_LIMIT`) if secrets remain after scrub. `local` MAY warn/allow.

## S3. Step-level taint

- Taint `{clean|live|unknown}` per step. Live taints successors until snapshot restore.
- `strict`/`ci` MUST fail if clean replay consumes tainted predecessor without explicit live chain.
- Value-level taint tracking MUST NOT.

## S4. Cassette layout

```text
<cassette-root>/
  cassette.json
  cassette.json.bak.<n>
  requests/<id>.json
  responses/<id>.json
  bodies/<sha256>.bin
  snapshots/<id>.tar.zst
  snapshots/<id>.json
  locks/cassette.lock
```

Atomic tmp → fsync → rename; exclusive writer lock; repair MUST NOT invent transactions.

## S5. Proxy routes

Allowlist only: `POST /v1/messages`, `POST /v1/chat/completions`, `POST /v1/responses`, `GET /v1/models`, `GET /healthz`.  
Others → `404 LLMREPLAY_ROUTE_DENIED`. Replay MUST NOT open outbound sockets (except loopback health).

## S6. Streaming

Default synthesize valid SSE from final message (same tool IDs / block order). Turn-atomic commit.

## S7. Snapshots

`tar.zst` + `snapshot.json`; workspace roots only; denylist secrets; safe restore (no `/`, `$HOME`, path escape).

## S8. Free-mode startup

`test-stack` healthy → free key → proxy on loopback → agent env → CCR → Ollama. Free key never in cassette.

- `llmreplay test-stack up|down|status` materializes CCR config and probes health; unhealthy → exit `TEST_STACK_UNHEALTHY` (4).
- `llmreplay keys create --free` issues localhost-only quota keys; refuse non-loopback peers.
- Degraded mode: Ollama up without CCR MAY use Ollama OpenAI-compatible `/v1` as upstream for Chat Completions.

## S12. Hook protocol (Claude Code)

- Hook stdin: one UTF-8 JSON `{"version":1,"id":"...","event":"PreToolUse|PostToolUse",...}`; stdout: one JSON line decision `allow|deny|error` echoing `id`.
- Max 1 MiB; fail closed on timeout/invalid.
- Record `hook_digests` SHA-256 of hook script bytes; `ci`/`strict` → exit `HOOK_OR_POLICY_DIVERGENCE` (6) on digest mismatch (`llmreplay hooks verify`).
- Recorded decisions in `hooks/decisions.jsonl` are forced on replay; denied tools use a stub result.

## S15 addendum — sticky / templates

- `debug_sticky` profile may set `sticky_writeback: true`; `ci`/`strict` MUST reject sticky writeback.
- Template field class uses allowlisted materializers only (`uuid.v4`, `path_rebase`); unknown names MUST fail.
- `fork --seq N` shares prefix transactions and assigns a new `run_id`; `tweak` invalidates the suffix.

## S10 addendum — agent parity

- Claude Messages multi-turn: `tool_use` / `tool_result` ids are static wire literals.
- Codex Responses: `previous_response_id` is static when present.
- Hermetic goldens live under `tests/test_c9_parity.py`; examples under `examples/claude-code-hello` and `examples/codex-hello`.

## S16. Compatibility / migrate

- Cassette `schema_version` is an integer independent of CLI semver.
- `llmreplay migrate [--dry-run]` upgrades through registered steps to the current version (now **1**).
- CLI MUST support current and previous two schema majors via migrate (v0→v1 ships in C10).

---

## Exit codes

| Code | Name |
|---|---|
| 0 | SUCCESS |
| 1 | STATIC_MISMATCH |
| 2 | CASSETTE_MISSING |
| 3 | LIVE_OR_UPSTREAM_ERROR |
| 4 | TEST_STACK_UNHEALTHY |
| 5 | SCHEMA_OR_REPAIR_REQUIRED |
| 6 | HOOK_OR_POLICY_DIVERGENCE |
| 7 | SECRET_SCRUB_OR_LIMIT |
| 8 | NETWORK_DENIED |
| 9 | ROUTE_OR_PROTOCOL |
