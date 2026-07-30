# Profiles

Built-in profiles (see [llmreplay-yaml.md](../reference/llmreplay-yaml.md)):

| Profile | `ignore_drift` | Sticky writeback | Residual secrets |
|---|---|---|---|
| `local` | warn | off by default | scrub; do not refuse write |
| `debug_sticky` | warn | **on** (local debug only) | scrub; do not refuse write |
| `ci` | fail | **forbidden** | refuse cassette write (422) |
| `strict` | fail | **forbidden** | refuse cassette write (422) |

Select with `llmreplay proxy|record|replay --profile …` and optional `--config llmreplay.yaml`.

Sticky writeback via `llmreplay sticky --profile debug_sticky` — never use in CI.
