# Portable cassettes

Cassettes should work across machines, CI runners, and contributors. Follow this checklist:

## Checklist

1. **HMAC key** — Set `LLMREPLAY_HMAC_KEY` consistently across record and replay environments. CI should use a repository secret; local dev should use a stable key shared among contributors.

2. **Adapter** — Cassettes recorded with one adapter (Anthropic Messages vs OpenAI Chat) replay on the same adapter. The adapter id is recorded in the cassette metadata.

3. **Scrub** — Ensure all secrets are scrubbed before committing cassettes. Run `llmreplay validate --cassette PATH` to check for residual secrets.

4. **Path rebase** — If cassettes contain absolute workspace paths, use `llmreplay template path_rebase --from /old/path --to /new/path` to adjust.

5. **Profile** — Record with `--profile local`, replay with `--profile ci` (stricter).

## Anti-patterns

- Committing cassettes recorded without `LLMREPLAY_HMAC_KEY` — scrub placeholders will differ per-process.
- Recording with `--free` and replaying without it — the `test_stack` fingerprint causes a miss.
- Using different ignore/scrub configs between record and replay environments.
