# Troubleshooting

Prefer `llmreplay doctor --json` + a scrubbed `llmreplay bundle` when filing issues.

| Symptom | Likely exit | Next step |
|---|---|---|
| Replay returns 409 / miss | `1 STATIC_MISMATCH` | `llmreplay why --cassette … --request <cassette>/requests/<id>.json` then consider `mark-ignore` only for non-behavioral noise |
| Empty cassette | `2 CASSETTE_MISSING` | `llmreplay record --upstream …` then re-run the agent so traffic hits the proxy |
| Upstream / live tool error | `3 LIVE_OR_UPSTREAM_ERROR` | Check `--upstream`; `llmreplay test-stack status` for free stack |
| Test stack down | `4 TEST_STACK_UNHEALTHY` | Start Ollama + CCR; see [free-test-stack.md](free-test-stack.md) |
| Corrupt / missing blobs | `5 SCHEMA_OR_REPAIR_REQUIRED` | `llmreplay validate --cassette …`; `llmreplay migrate` if schema stale |
| Hook digest mismatch | `6 HOOK_OR_POLICY_DIVERGENCE` | `llmreplay hooks verify --profile ci` |
| Residual secrets on write (ci/strict) | `7 SECRET_SCRUB_OR_LIMIT` | Tighten scrub; set `LLMREPLAY_HMAC_KEY` |
| Network denied / live refused | `8` / config error | Unmarked replay is hermetic; `mark-live __llm__` needs `--upstream` and `--allow-live` under ci/strict |
| Route / protocol denied | `9 ROUTE_OR_PROTOCOL` | Only allowlisted paths (SPEC S5); non-loopback needs `--allow-remote` |

## Doctor

```bash
llmreplay doctor --json
```

Hard failures: port in use, cassette not writable. Soft checks (`agent_env`, `hmac_key`, `test_stack`) print guidance.

## Why a miss

```bash
llmreplay why --cassette .llmreplay/demo --request .llmreplay/demo/requests/<tx-id>.json --config llmreplay.yaml
```

## Bundle for support

```bash
llmreplay bundle --cassette .llmreplay/cassette --output /tmp/llmreplay-bundle.zip
```

Scrubs by default (including `--include-bodies` when scrub=True).

## Live tools / LLM

```bash
llmreplay mark-live Bash --config llmreplay.yaml          # hooks need LLMREPLAY_CONFIG
llmreplay mark-live __llm__ --config llmreplay.yaml       # replay --upstream … [--allow-live]
export LLMREPLAY_CONFIG=$PWD/llmreplay.yaml
```
