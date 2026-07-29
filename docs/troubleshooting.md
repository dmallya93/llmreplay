# Troubleshooting

Quick starters for common failures. Always prefer `llmreplay doctor --json` + a scrubbed `llmreplay bundle` when filing issues.

| Symptom | Likely exit | Next step |
|---|---|---|
| Replay returns 409 / miss | `1 STATIC_MISMATCH` | `llmreplay why --request <event.json>` then consider `mark-ignore` only for non-behavioral noise |
| Empty cassette | `2 CASSETTE_MISSING` | `llmreplay record --upstream …` then re-run the agent |
| Upstream / live tool error | `3 LIVE_OR_UPSTREAM_ERROR` | Check upstream URL; free stack health is C5 |
| Corrupt / missing blobs | `5 SCHEMA_OR_REPAIR_REQUIRED` | `llmreplay validate --cassette …` |
| Residual secrets on write (ci/strict) | `7 SECRET_SCRUB_OR_LIMIT` | Tighten scrub patterns; set `LLMREPLAY_HMAC_KEY` |
| Route / protocol denied | `9 ROUTE_OR_PROTOCOL` | Only allowlisted paths (SPEC S5) |

## Doctor

```bash
llmreplay doctor --json
```

Fails when a hard check fails (port in use, cassette not writable). Soft checks (`agent_env`, `test_stack`) print guidance but do not fail the process until you wire agents / C5.

## Bundle for support

```bash
llmreplay bundle --cassette .llmreplay/cassette --output /tmp/llmreplay-bundle.zip
```

Scrubs by default; omit bodies unless `--include-bodies`.
