---
description: Record agent LLM interactions into a cassette for offline replay
---

# Record an agent turn

## Prerequisites

```bash
pip install coding-agent-vcr
export LLMREPLAY_HMAC_KEY=dev-local-hmac   # use a stable key; must match replay/CI
# First win with no keys: llmreplay demo
```

## Usage

Record a single agent turn with `llmreplay run` (one terminal — proxy + child):

```bash
llmreplay run --mode record --cassette .llmreplay/cassette \
  --upstream https://api.anthropic.com -- claude --print "your prompt here"
```

This starts the proxy, sets `ANTHROPIC_BASE_URL` / `OPENAI_BASE_URL` on the child, runs the command, and saves the cassette.

## Options

| Flag | Default | Purpose |
|---|---|---|
| `--cassette PATH` | `.llmreplay/cassette` | Where to save recordings |
| `--upstream URL` | required for record | Real LLM endpoint (or use `--free` for CCR) |
| `--port N` | `7432` | Proxy listen port |
| `--profile NAME` | `local` | Profile for scrub/ignore rules |
| `--free` | off | Use free-stack (CCR+Ollama) defaults |

## After recording

Verify the cassette is replay-ready:

```bash
llmreplay replay --check --cassette .llmreplay/cassette
```
