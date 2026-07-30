# Tutorial 3 — CI goldens without API keys

**Goal:** Fail the build when agent traffic drifts — with **no** live Anthropic/OpenAI keys in CI.

**Prereqs:** A checked-in cassette + stable `LLMREPLAY_HMAC_KEY` (repo secret).

---

## Why this helps

```
  Before                         After
  ──────                         ─────
  CI job                         CI job
   ├─ needs API key               ├─ LLMREPLAY_HMAC_KEY (secret)
   ├─ burns tokens every run      ├─ llmreplay replay --check
   ├─ flakes on model drift       ├─ offline, deterministic
   └─ slow                        └─ seconds
```

You are not evaluating model quality in CI. You are asserting: **“this agent trajectory still matches the golden cassette.”**

---

## 1. Commit the cassette

```bash
# After a good local record:
git add .llmreplay/demo
git commit -m "test: golden cassette for onboarding agent turn"
```

Confirm portability first: [portable-cassettes.md](../portable-cassettes.md).

---

## 2. Store the HMAC secret

In GitHub → Settings → Secrets:

```
LLMREPLAY_HMAC_KEY = <same value used when recording>
```

Use a **stable** key for the project — not `openssl rand` per job (that breaks scrub placeholders).

---

## 3. Add a workflow

Copy the consumer template:

[`examples/github-actions/llmreplay-replay.yml`](../../examples/github-actions/llmreplay-replay.yml)

Minimal shape:

```yaml
name: llmreplay
on: [push, pull_request]
jobs:
  cassette:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install coding-agent-vcr
      - run: llmreplay replay --check --cassette .llmreplay/demo --profile ci
        env:
          LLMREPLAY_HMAC_KEY: ${{ secrets.LLMREPLAY_HMAC_KEY }}
```

`--check` validates cassette health without launching an agent. For a full agent golden, use:

```bash
llmreplay run --mode replay --cassette .llmreplay/demo --profile ci \
  -- your-agent-command
```

---

## 4. What should fail the PR

| Change | Expected CI |
|---|---|
| Unrelated docs | Green |
| Prompt / tool schema drift | Miss → red |
| Accidental secret in cassette | Scrub / residual checks → red |
| Broken cassette files | `--check` → red |

---

## Agent tip (AGENTS.md)

Drop in [`examples/AGENTS.llmreplay.md`](../../examples/AGENTS.llmreplay.md) so coding agents in the consumer repo know to run `replay --check` / `why` instead of inventing mocks.

---

## Next

- Wire pytest → [Tutorial 4](04-pytest-agent-tests.md)
- Case study: [CI cost cliff](../case-studies.md#1-ci-that-stopped-burning-tokens)
