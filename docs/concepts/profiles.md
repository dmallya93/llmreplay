# Profiles

Built-in profiles (see [llmreplay-yaml.md](../reference/llmreplay-yaml.md)):

| Profile | `ignore_drift` | Sticky | Residual secrets |
|---|---|---|---|
| `local` | warn | allowed | scrub; do not refuse write |
| `ci` | fail | **forbidden** | refuse cassette write (422) |
| `strict` | fail | **forbidden** | refuse cassette write (422) |

Select with `llmreplay proxy|record|replay --profile …` and optional `--config llmreplay.yaml`.
