# Tutorials

Hands-on guides for humans and agents. Start at the top; skip ahead if you already have a cassette.

| # | Tutorial | Time | You will learn |
|---|---|---|---|
| 1 | [Your first cassette](01-first-cassette.md) | ~5 min | Record once, replay offline |
| 2 | [Debug a miss with `why`](02-debug-a-miss.md) | ~10 min | Read a mismatch, decide ignore vs real bug |
| 3 | [CI goldens without API keys](03-ci-goldens.md) | ~15 min | Hermetic GitHub Actions / local CI |
| 4 | [pytest agent tests](04-pytest-agent-tests.md) | ~15 min | `@pytest.mark.llmreplay` + fixture |
| 5 | [Fork, tweak, assert](05-fork-tweak.md) | ~10 min | Time-travel a trajectory at turn N |

**Related**

- [Demo walkthrough](../demo.md) — scripted demo you can present live
- [Case studies](../case-studies.md) — when teams use LLMReplay and why
- [Quickstart](../quickstart.md) — shortest path to green

```
  Journey map

  smoke.sh ──► first cassette ──► why / miss ──► CI goldens
                     │                              │
                     └────────► pytest ◄────────────┘
                                   │
                              fork / tweak
```
