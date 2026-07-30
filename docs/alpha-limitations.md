# Alpha limitations

Public **alpha** status for LLMReplay. Hermetic JSON proxy + CLI are usable; agent-facing edges still incomplete relative to [SPEC.md](SPEC.md). See [DESIGN.md](../DESIGN.md) for architecture and usage.

## Works today

- Record / replay for `/v1/messages`, `/v1/chat/completions`, `/v1/responses` (JSON).
- SSE **synthesis** on replay when the client sends `stream: true` (minimal Anthropic / OpenAI shapes).
- HMAC scrub, profiles (`local` / `ci` / `strict`), `mark-ignore` → yaml → match keys.
- Free test-stack keys (`llmreplay-free-…`) → proxy → CCR → Ollama.
- `mark-live` tools bypass hook cassette force (needs `LLMREPLAY_CONFIG`); `mark-live __llm__` live-proxies LLM on replay (`--upstream`; `--allow-live` under ci/strict).
- Nested session digests (`extensions.session`) + child verify helpers.
- Template **CLI** materializers (`uuid.v4`, `path_rebase`) — not yet auto-applied as a match field class.
- Migrate v0→v1, doctor, validate, bundle, fork/tweak, FS snapshots, Claude Code hooks install/verify.
- Offline release smoke + hermetic CI.
- Loopback bind for record and replay unless `--allow-remote`.

## Known gaps (not blockers for local alpha)

| Area | Gap |
|---|---|
| Streaming fidelity | Synthesize-only; no exact provider event replay / thinking chunk boundaries |
| Nested sessions | Digest link + verify shipped; depth-first orchestration still manual; `verify_children` no-ops if parent has no `extensions.session` |
| Hook deny stub | Decision `reason` + stderr note only — no protocol to inject fake tool_result bodies |
| Hook digests | Enforced via `llmreplay hooks verify`, not automatic at proxy start |
| Template field class | CLI materializers exist; not wired into match projection automatically |
| Taint tracking | SPEC S3 partial — no per-step clean/live gate yet |
| Repair CLI | Not shipped |
| Coverage gate | Critical modules + sse/config/session/hooks.recorder; full `proxy/app` / CLI not in ≥95% gate |
| Windows CI | Not in matrix yet |
| Nightly Ollama | Documented; not required on every PR |

## Security posture (alpha)

- Record/replay bind loopback by default; non-loopback requires `--allow-remote`.
- Set `LLMREPLAY_HMAC_KEY` in CI; `ci`/`strict` **record** refuses to start if unset.
- `ci`/`strict` refuse `mark-live __llm__` unless `--allow-live`.
- Free keys are localhost auth only — never vendor upstream keys.
- `bundle` scrubs manifest/requests/responses/bodies when scrub=True (default).

See [threat-model.md](threat-model.md) and [compatibility.md](compatibility.md).
