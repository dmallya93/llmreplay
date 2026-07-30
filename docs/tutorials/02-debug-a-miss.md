# Tutorial 2 — Debug a miss with `why`

**Goal:** When replay returns a mismatch, understand *exactly* what changed and whether it is noise or a real regression.

**Prereqs:** A cassette from [Tutorial 1](01-first-cassette.md).

---

## What a miss means

```
  Agent request ──► Proxy ──► compute match key ──► lookup cassette
                                                      │
                                          ┌───────────┴───────────┐
                                          ▼                       ▼
                                       HIT (200)              MISS (409)
                                       return body            why?
```

A **miss** is not “the tool is broken.” It means the **static projection** of this request does not match any recorded transaction.

---

## Reproduce a miss (on purpose)

Change something that *should* be static — e.g. the user prompt:

```bash
# Cassette was recorded with "say hello in one sentence"
llmreplay run --mode replay --cassette .llmreplay/demo \
  -- claude --print "say goodbye in one sentence"
```

You should see a miss / non-zero exit (exact surface depends on the agent).

---

## Run `why`

Find the failing request payload under the cassette (or the path printed by the proxy):

```bash
llmreplay why --cassette .llmreplay/demo \
  --request .llmreplay/demo/requests/<tx-id>.json
```

`why` shows:

- Which fields differ in the **static** projection
- What was stripped as **ignore**
- Whether scrub placeholders are stable (`LLMREPLAY_HMAC_KEY` must match record)

```
  Decision tree

  Diff in messages / tools / model ?
      YES → real behavior change (prompt/tool regression). Update cassette
            deliberately with a new record, or fix the agent.
      NO  → check ignore / scrub
              │
              ├─ timestamp / request_id → should already be ignore
              ├─ secret-looking string → scrub pattern / HMAC key mismatch
              └─ tool block order only → should already be sorted; file a bug
```

---

## Common fixes

| Symptom | Fix |
|---|---|
| Diff is only timestamps / ids | Already ignored — if not, see [field-classes](../concepts/field-classes.md) |
| Scrub placeholders differ across machines | Same `LLMREPLAY_HMAC_KEY` at record *and* replay ([portable cassettes](../portable-cassettes.md)) |
| Prompt changed on purpose | Re-record, or fork the cassette ([Tutorial 5](05-fork-tweak.md)) |
| Tool order only | Match pipeline sorts parallel tools — if still failing, open an issue |

**Do not** blindly `mark-ignore` a field that drives agent behavior. That hides real regressions.

---

## Safety notes for agents

- Never auto-apply `mark-ignore` without human confirmation
- Never use `--allow-remote` unless free-stack / local stubs
- Prefer `mark-live __llm__` only when a step *must* hit a real LLM under `ci`/`strict`

---

## Next

- Lock the green cassette in CI → [Tutorial 3](03-ci-goldens.md)
- Assert in pytest → [Tutorial 4](04-pytest-agent-tests.md)
