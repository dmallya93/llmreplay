# Case studies

Narrative examples of when LLMReplay pays for itself. Names are illustrative; workflows are real product capabilities.

---

## 1. CI that stopped burning tokens

**Team:** Platform squad running Claude Code in GitHub Actions for “does the agent still complete onboarding?”

**Pain**

- Every PR called a live API → cost + rate limits
- Model/provider drift made green builds flaky
- Security hated long-lived API keys in Actions

**Move**

1. Recorded one happy-path turn locally with `llmreplay run --mode record`
2. Committed `.llmreplay/onboarding` + stable `LLMREPLAY_HMAC_KEY` secret
3. CI ran `llmreplay replay --check` (and optionally full `run --mode replay`)

**Result**

| Metric | Before | After |
|---|---|---|
| Cost per PR | Live tokens | $0 offline |
| Flakes from model drift | Common | Gone (golden is fixed) |
| Secrets in CI | Provider API key | HMAC only |

**Takeaway:** CI asserts *trajectory stability*, not model quality. Eval belongs elsewhere.

→ Tutorial: [CI goldens](tutorials/03-ci-goldens.md)

---

## 2. pytest without a mock farm

**Team:** Library authors shipping an OpenAI/Anthropic client wrapper used by agents.

**Pain**

- Hand-written `httpx` mocks drifted from real SDK payloads
- Parallel tool-call order made tests flake
- New contributors didn’t know which fields mattered

**Move**

1. Recorded real traffic once into a cassette
2. Switched tests to `@pytest.mark.llmreplay` + `ReplayTransport`
3. Documented “re-record when the wire format changes” in CONTRIBUTING

**Result**

- Tests exercise real JSON shapes
- Tool-order noise absorbed by the match pipeline
- “Update mocks” PRs became “re-record cassette” PRs

→ Tutorial: [pytest agent tests](tutorials/04-pytest-agent-tests.md)

---

## 3. The bug that only happened on turn 7

**Team:** Agent product; customer reported a wrong tool call late in a session.

**Pain**

- Re-running live never hit the same tool sequence
- Logs showed *what* happened, not a way to re-execute
- Fix attempts were guesswork

**Move**

1. Had a scrubbed cassette from an earlier repro attempt
2. Forked at turn 6, tweaked the failing tool result
3. Replayed the branch until the agent chose the correct tool
4. Locked the fixed branch as a regression cassette in CI

**Result**

- Debugging became a controlled experiment
- Regression locked without keeping a live key in CI

→ Tutorial: [Fork, tweak, assert](tutorials/05-fork-tweak.md)

---

## 4. Open-source demo day

**Maintainer:** You, presenting LLMReplay in 5 minutes.

**Script:** [Demo walkthrough](demo.md)

**Why it converts stars**

- Audience *sees* record → miss → why → replay
- Hermetic smoke needs no API key on stage
- Clear pitch: “VCR for coding agents”

---

## When *not* to use LLMReplay

| Need | Better fit |
|---|---|
| Cost/latency dashboards, live traces | [AgentReplay](compare-agentreplay.md) / observability stacks |
| Scoring model quality on a rubric | Eval harnesses |
| One-off manual chat | Just use the agent |

LLMReplay shines when you must **re-execute and assert** a trajectory.
