# Tutorial 4 — pytest agent tests

**Goal:** Assert agent HTTP traffic hermetically inside pytest — no port binding, no live LLM.

**Prereqs:** `coding-agent-vcr`, `pytest`, `pytest-asyncio`. Cassette from [Tutorial 1](01-first-cassette.md).

---

## Install

```bash
pip install coding-agent-vcr pytest pytest-asyncio
export LLMREPLAY_HMAC_KEY=dev-local-hmac   # same key used at record time
```

The plugin registers automatically via the `pytest11` entry point.

---

## Marker + fixture

```python
import pytest

@pytest.mark.llmreplay(cassette=".llmreplay/demo", profile="ci")
async def test_agent_greeting(llmreplay_cassette):
    resp = await llmreplay_cassette.post(
        "/v1/messages",
        json={
            "model": "claude-test",
            "messages": [{"role": "user", "content": "say hello in one sentence"}],
            "max_tokens": 64,
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["content"][0]["text"]  # exact text depends on your cassette
```

```
  Test process
       │
       ▼
  llmreplay_cassette ──► ReplayTransport ──► ASGI proxy app
       │                        │
       │                        └── cassette on disk
       └── httpx.AsyncClient (no TCP bind)
```

---

## Library form (no marker)

Useful when you want an explicit transport:

```python
from pathlib import Path
import httpx
from llmreplay import ReplayTransport

async def test_with_transport():
    transport = ReplayTransport(
        cassette_dir=Path(".llmreplay/demo"),
        profile="ci",
    )
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://llmreplay",
    ) as client:
        resp = await client.post("/v1/messages", json={...})
        assert resp.status_code == 200
```

---

## When this is better than mocking

| Hand mocks | LLMReplay cassette |
|---|---|
| You invent JSON shapes | Shapes come from real traffic |
| Drift when the SDK updates | Re-record once, commit |
| Hard to test tool-order bugs | Match key sorts parallel tools |
| Secrets often leak into fixtures | Scrub + HMAC placeholders |

---

## Tips

- Prefer `profile="ci"` in tests (stricter than `local`)
- Missing marker → `UsageError` (fixture requires `@pytest.mark.llmreplay`)
- Async tests need `pytest-asyncio` (`asyncio_mode = auto` recommended)
- Full reference: [integrations/pytest.md](../integrations/pytest.md)

---

## Next

- Mutate a trajectory → [Tutorial 5](05-fork-tweak.md)
- Case study: [pytest without a mock farm](../case-studies.md#2-pytest-without-a-mock-farm)
