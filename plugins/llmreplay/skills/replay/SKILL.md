---
description: Replay a recorded agent turn offline from a cassette
---

# Replay an agent turn

## Prerequisites

```bash
pip install coding-agent-vcr
export LLMREPLAY_HMAC_KEY=<same key used during record>
```

## Usage

Replay a recorded turn offline:

```bash
llmreplay run --mode replay --cassette .llmreplay/cassette -- claude --print "your prompt"
```

Or check cassette health without running an agent:

```bash
llmreplay replay --check --cassette .llmreplay/cassette --profile ci
```

## Options

| Flag | Default | Purpose |
|---|---|---|
| `--cassette PATH` | `.llmreplay/cassette` | Cassette to replay from |
| `--port N` | `7432` | Proxy listen port |
| `--profile NAME` | `local` | Profile (`ci` for strict) |
| `--allow-live` | off | Allow `mark-live __llm__` under ci/strict (breaks hermetic replay) |

## On a miss

If replay fails with a static mismatch, use the `why` skill to diagnose.
