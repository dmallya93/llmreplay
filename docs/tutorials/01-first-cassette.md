# Tutorial 1 — Your first cassette

**Goal:** See record → cassette → offline replay in **one terminal**.

**Prereqs:** Python 3.12+, `pip`. No API keys, no CCR, no second window.

---

## Step 0 — Install and demo (30 seconds)

```bash
pip install coding-agent-vcr
llmreplay demo
```

What just happened (all in one process tree):

```
  llmreplay demo
       │
       ├─ stub gateway  (fake LLM on a free port)
       ├─ proxy         (record → cassette)
       ├─ child agent   (one HTTP turn)
       ├─ proxy         (replay from cassette)
       └─ ✓ done
```

You proved the full loop with **zero** Anthropic keys and **no** multi-terminal setup.

---

## Step 1 — Real agent (still one terminal)

`llmreplay run` **is** the gateway: it starts the proxy, runs your agent, then tears down.

```bash
# Keep ANTHROPIC_API_KEY in the environment (forwarded upstream).
# Local HMAC defaults to dev-local-hmac when unset.

llmreplay run --mode record --cassette .llmreplay/demo \
  --upstream https://api.anthropic.com \
  -- claude --print "say hello in one sentence"
```

```
  RECORD                          REPLAY
  ─────                           ──────
  Agent ──► Proxy ──► Upstream    Agent ──► Proxy ──► Cassette
               │                               │
               ▼                               ▼
           .llmreplay/demo              SHA-256 match
```

Peek:

```bash
ls .llmreplay/demo/   # cassette.json, requests/, responses/, …
llmreplay replay --check --cassette .llmreplay/demo
```
Replay offline (no upstream, no tokens):

```bash
llmreplay run --mode replay --cassette .llmreplay/demo \
  -- claude --print "say hello in one sentence"
```

---

## Optional — Hermetic smoke (contributors)

```bash
git clone https://github.com/dmallya93/llmreplay.git && cd llmreplay
pip install -e ".[dev]"
export LLMREPLAY_HMAC_KEY=dev-local-hmac
./scripts/smoke.sh
# ✓ smoke ok: record→replay (fake upstream)
```

Same loop as `llmreplay demo`, used in CI.

---

## What “helpful” looks like here

| Without LLMReplay | With this cassette |
|---|---|
| Re-run Claude to verify a fix → $$ + flake | Replay the exact turn for free |
| “It failed once in CI” | Cassette is the fixture; CI is hermetic |
| Hand-written mocks drift from reality | Recorded from real traffic, scrubbed |

---

## Next

- Miss on replay? → [Tutorial 2 — Debug a miss](02-debug-a-miss.md)
- Put it in CI → [Tutorial 3 — CI goldens](03-ci-goldens.md)
