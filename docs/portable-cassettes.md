# Portable cassettes

Cassettes should work across machines, CI runners, and contributors. Follow this checklist:

## Checklist

1. **HMAC key** — Set `LLMREPLAY_HMAC_KEY` consistently across record and replay environments. CI should use a repository secret; local dev should use a stable key shared among contributors.

2. **Protocol / path** — Replay must hit the same wire protocol as record (`/v1/messages` vs `/v1/chat/completions` vs `/v1/responses`). Mixing Anthropic Messages cassettes with OpenAI Chat clients will miss. Match keys are path-aware; there is no separate adapter-id field in cassette metadata today.

3. **Scrub** — Ensure all secrets are scrubbed before committing cassettes. Run `llmreplay validate --cassette PATH` to check for residual secrets.

4. **Path rebase** — If cassettes contain absolute workspace paths, use
   `llmreplay template path_rebase --value /old/repo --from /old --to /new`
   (see [concepts/fork-tweak.md](concepts/fork-tweak.md)).

5. **Profile** — Record with `--profile local`, replay with `--profile ci` (stricter).

## Anti-patterns

- Committing cassettes recorded without `LLMREPLAY_HMAC_KEY` — scrub placeholders will differ per-process.
- Recording with `--free` and replaying without it — the `test_stack` fingerprint causes a miss.
- Using different ignore/scrub configs between record and replay environments.
