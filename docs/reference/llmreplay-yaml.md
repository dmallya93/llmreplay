# `llmreplay.yaml` reference

```yaml
version: 1
unknown_tool_policy: fail   # static | fail | prompt_user
defaults:
  ignore:
    - usage
    - latency_ms
    - x-request-id
    - date
  scrub: []                 # dotted paths merged into scrubber (e.g. body.custom_token)
profiles:
  local:
    ignore_drift: warn
  ci:
    ignore_drift: fail      # residual secrets → refuse cassette write (422)
  strict:
    ignore_drift: fail
tools: {}                  # mark-live Bash / __llm__ → {class: live}
```

## Live tools

- `llmreplay mark-live Bash` — on hook **replay**, PreToolUse for `Bash` returns `allow` (real tool runs) instead of forcing the cassette decision.
- `llmreplay mark-live __llm__` — proxy **replay** forwards every LLM call to `--upstream` and does **not** read/write the cassette for those calls. Requires `replay --upstream …`.
- Set `LLMREPLAY_CONFIG` when using installed hooks so live tool lists are loaded.

## Precedence

`CLI flags > env > llmreplay.yaml profile > defaults` (SPEC S15).

Profile `ignore` / `scrub` lists are **merged after** `defaults` (deduped, defaults first).

## Sticky writeback

`sticky_writeback: true` is **forbidden** for `ci` and `strict` profiles.

## Residual secrets

Profiles `ci` and `strict` fail record with `llmreplay_secret` (HTTP 422) when post-scrub residual regexes still match. `local` does not refuse (scrub still runs before disk).

Load via `llmreplay.config.profiles.load_llmreplay_yaml`. Proxy: `--profile` / `--config`.
