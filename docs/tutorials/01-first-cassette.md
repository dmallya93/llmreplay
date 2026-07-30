# Tutorial 1 — Your first cassette

**Goal:** Record one agent turn, then replay it offline with zero tokens.

**Prereqs:** Python 3.12+, `pip`, and either Claude Code / Codex *or* the hermetic smoke script (no agent required).

---

## Option A — Hermetic (no agent, no API)

Best first win. Pure in-process fake upstream.

```bash
git clone https://github.com/dmallya93/llmreplay.git && cd llmreplay
pip install -e ".[dev]"
export LLMREPLAY_HMAC_KEY=dev-local-hmac
./scripts/smoke.sh
# ✓ smoke ok: record→replay (fake upstream)
```

You just proved the full loop: **record → cassette on disk → replay match**.

---

## Option B — Real agent (`llmreplay run`)

```bash
pip install coding-agent-vcr
export LLMREPLAY_HMAC_KEY=dev-local-hmac
llmreplay doctor
```

```
  RECORD                          REPLAY
  ─────                           ──────
  Agent ──► Proxy ──► Upstream    Agent ──► Proxy ──► Cassette
               │                               │
               ▼                               ▼
           .llmreplay/demo              SHA-256 match
```

### 1. Record

Point `--upstream` at whatever serves Anthropic/OpenAI-compatible traffic
(CCR, a stub, or a paid API gateway you control):

```bash
llmreplay run --mode record --cassette .llmreplay/demo \
  --upstream http://127.0.0.1:3456 \
  -- claude --print "say hello in one sentence"
```

What `run` does for you:

1. Starts a loopback proxy on `:7432`
2. Sets `ANTHROPIC_BASE_URL` / `OPENAI_BASE_URL` for the child
3. Runs your command
4. Tears the proxy down and exits with the child's code

### 2. Peek at the cassette

```bash
ls .llmreplay/demo/
# index.json  requests/  responses/  ...
llmreplay replay --check --cassette .llmreplay/demo
```

### 3. Replay offline

No upstream needed:

```bash
llmreplay run --mode replay --cassette .llmreplay/demo \
  -- claude --print "say hello in one sentence"
```

Same prompt → same matched response → deterministic agent turn.

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
