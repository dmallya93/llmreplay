# LLMReplay — deterministic agent replay

This project uses [LLMReplay](https://github.com/dmallya93/llmreplay) for hermetic agent testing.

## Quick commands

```bash
# Install
pip install coding-agent-vcr
export LLMREPLAY_HMAC_KEY=<your-key>   # required for ci/strict profile

# Record an agent turn
llmreplay run --mode record --cassette .llmreplay/cassette \
  --upstream http://127.0.0.1:3456 -- claude --print "your prompt"

# Replay offline
llmreplay run --mode replay --cassette .llmreplay/cassette -- claude --print "your prompt"

# Verify cassette health
llmreplay replay --check --cassette .llmreplay/cassette --profile ci

# Diagnose a miss
llmreplay why --cassette .llmreplay/cassette --request .llmreplay/cassette/requests/<tx>.json
```

## Cassette directory

Cassettes live in `.llmreplay/cassette/`. Commit them to the repo for CI replay.

## CI

The `.github/workflows/llmreplay-replay.yml` workflow runs `replay --check` on every PR.
Set `LLMREPLAY_HMAC_KEY` as a repository secret.

## Library usage (pytest)

```python
import pytest


@pytest.mark.llmreplay(cassette=".llmreplay/cassette")
async def test_agent(llmreplay_cassette):
    resp = await llmreplay_cassette.post("/v1/messages", json={...})
    assert resp.status_code == 200
```
