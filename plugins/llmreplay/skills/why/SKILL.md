---
description: Diagnose a cassette miss — explain why a request did not match
---

# Diagnose a miss

## When to use

After a replay miss (HTTP 404 from the proxy or `--check` failure), use `why` to see what differed.

## Usage

```bash
llmreplay why --cassette .llmreplay/cassette \
  --request .llmreplay/cassette/requests/<tx-id>.json
```

For JSON output:

```bash
llmreplay why --cassette .llmreplay/cassette \
  --request .llmreplay/cassette/requests/<tx-id>.json --json
```

## Output

- `matched=True/False` — whether the request hash matched a recorded transaction
- `closest_tx=<id>` — the nearest recorded transaction (by hash distance)
- Suggestion text explaining what fields caused the mismatch

## Common fixes

| Cause | Fix |
|---|---|
| Timestamp/request-id drift | `llmreplay mark-ignore <field>` |
| Tool order changed | Already handled by sort pipeline |
| Path pin drift | `llmreplay template path_rebase` |
| Live tool needed | `llmreplay mark-live <tool>` |

## Do not

- Never auto-apply `mark-ignore` — always review the suggestion first.
- Never use `--allow-remote` without `--free`.
