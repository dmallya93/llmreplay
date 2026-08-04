# Quickstart

**One terminal. No CCR. No free keys. No second window.**

## 30-second win

```bash
pip install coding-agent-vcr
llmreplay demo
```

That single command:

1. Sets a local HMAC key if you do not already have one  
2. Starts a **stub LLM gateway** in the background  
3. Starts the **LLMReplay proxy**  
4. Runs a tiny agent child through the proxy (**record**)  
5. Replays the same turn **offline**  
6. Prints the exact commands to repeat with Claude Code / Codex  

```
  one terminal
  ────────────
  llmreplay demo
       │
       ├─ stub gateway  (fake LLM)
       ├─ proxy         (record → cassette)
       ├─ child agent   (one HTTP turn)
       ├─ proxy         (replay from cassette)
       └─ ✓ done
```

## Real agent (still one terminal)

`llmreplay run` starts the proxy for you, wires env vars, runs your agent, then tears down. **Do not** open a second terminal.

```bash
# Keep your real ANTHROPIC_API_KEY / OPENAI_API_KEY in the environment.
# Local HMAC defaults to dev-local-hmac when unset (set explicitly for CI).

# Record
llmreplay run --mode record --cassette .llmreplay/demo \
  --upstream https://api.anthropic.com \
  -- claude --print "say hi"

# Replay offline (no upstream, no tokens)
llmreplay run --mode replay --cassette .llmreplay/demo \
  -- claude --print "say hi"

# Cassette health (CI)
llmreplay replay --check --cassette .llmreplay/demo
```

```
  What llmreplay run does (one process tree):

  ┌────────────────────────────────────────────────────────────┐
  │  1. Start proxy on 127.0.0.1:<port>                        │
  │  2. Set ANTHROPIC_BASE_URL + OPENAI_BASE_URL for child     │
  │  3. Run your command (claude / codex / pytest / …)         │
  │  4. Exit with the child's code                             │
  │  5. Tear down proxy                                        │
  └────────────────────────────────────────────────────────────┘
```

### Upstream choices

| Upstream | When |
|---|---|
| `https://api.anthropic.com` | You have a real Anthropic key (simplest paid path) |
| `https://api.openai.com` | Codex / OpenAI (use `OPENAI_API_KEY`) |
| Your own stub / gateway | Local URL you already run |

You do **not** need CCR or `llmreplay keys create` for the happy path.

## Diagnose a miss

```bash
llmreplay why --cassette .llmreplay/demo \
  --request .llmreplay/demo/requests/<tx-id>.json
```

## Optional: free local LLM stack

Only if you want $0 local models (Ollama + CCR). More moving parts — skip until the demo works.

See [free-test-stack.md](free-test-stack.md).

<details><summary>Advanced: two-terminal proxy (not recommended)</summary>

Prefer `llmreplay run`. Two-terminal is only for debugging the proxy itself:

```bash
# Terminal A
llmreplay record --cassette .llmreplay/demo --upstream https://api.anthropic.com

# Terminal B
export ANTHROPIC_BASE_URL=http://127.0.0.1:7432
claude --print "say hi"
```

</details>

## Next steps

| What | Where |
|---|---|
| **Tutorials** | [tutorials/README.md](tutorials/README.md) |
| **Demo script (talk)** | [demo.md](demo.md) |
| **Case studies** | [case-studies.md](case-studies.md) |
| Claude Code | [integrations/claude-code.md](integrations/claude-code.md) |
| Codex | [integrations/codex.md](integrations/codex.md) |
| pytest | [integrations/pytest.md](integrations/pytest.md) |
| CI | [ci.md](ci.md) |
