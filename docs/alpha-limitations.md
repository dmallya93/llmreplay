# Alpha limitations

Public **alpha** status for LLMReplay after C0–C10. Hermetic JSON proxy + CLI are usable; agent-facing edges still incomplete relative to [SPEC.md](SPEC.md).

## Works today

- Record / replay for `/v1/messages`, `/v1/chat/completions`, `/v1/responses` (JSON).
- SSE **synthesis** on replay when the client sends `stream: true` (minimal Anthropic / OpenAI shapes).
- HMAC scrub, profiles (`local` / `ci` / `strict`), `mark-ignore` → yaml → match keys.
- Free test-stack keys (`llmreplay-free-…`) → proxy → CCR → Ollama.
- Migrate v0→v1, doctor, validate, bundle, fork/tweak, FS snapshots, Claude Code hooks install/verify.
- Offline release smoke + hermetic CI.

## Known gaps (not blockers for local alpha)

| Area | Gap |
|---|---|
| Streaming fidelity | Synthesize-only; no exact provider event replay / thinking chunk boundaries |
| Nested sessions | Parent/child cassette abort not fully wired |
| `mark-live` | Yaml mutation exists; proxy live-pass-through for tools is incomplete |
| Repair CLI | Not shipped |
| Taint / sticky writeback | Partial vs SPEC |
| Coverage gate | Focused on match/scrub/migrate; proxy/hooks/snapshot not in ≥95% gate |
| Windows CI | Not in matrix yet |
| Nightly Ollama | Documented; not required on every PR |

## Security posture (alpha)

- Replay binds loopback by default; non-loopback requires explicit `allow_non_loopback`.
- Set `LLMREPLAY_HMAC_KEY` in CI; unset → random per-process key (doctor warns).
- Free keys are localhost auth only — never vendor upstream keys.

See [threat-model.md](threat-model.md) and [compatibility.md](compatibility.md).
