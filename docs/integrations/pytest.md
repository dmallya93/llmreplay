# pytest integration

LLMReplay ships a pytest plugin (auto-loaded via entry point) that provides hermetic cassette replay without starting a proxy server.

## Quick start

```python
import pytest


@pytest.mark.llmreplay(cassette=".llmreplay/cassette", profile="ci")
async def test_agent_turn(llmreplay_cassette):
    resp = await llmreplay_cassette.post(
        "/v1/messages",
        json={"model": "claude-test", "messages": [{"role": "user", "content": "hi"}]},
    )
    assert resp.status_code == 200
    assert resp.json()["content"][0]["text"] == "hello"
```

## How it works

The `llmreplay_cassette` fixture creates an `httpx.AsyncClient` backed by a `ReplayTransport` — no port binding, no uvicorn. Requests are matched against the cassette using the same SHA-256 static key pipeline as the proxy.

## Marker options

| Kwarg | Default | Description |
|---|---|---|
| `cassette` | `.llmreplay/cassette` | Path to cassette directory |
| `profile` | `ci` | Profile for ignore/scrub rules |
| `allow_live` | `False` | Allow mark-live tools during replay |

## Dependencies

Consumer repos need `pytest-asyncio` (or `anyio`) for async test functions:

```bash
pip install coding-agent-vcr pytest-asyncio
```

## CI tips

- Set `LLMREPLAY_HMAC_KEY` in your CI secrets for stable scrub placeholders.
- Use `profile="ci"` (the default) for strict replay — misses fail the test.
- The plugin does not require network access; all replay is from local fixtures.
