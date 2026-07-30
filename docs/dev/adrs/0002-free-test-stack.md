# ADR-0002: Free test stack

## Context

Contributors and CI need agent record/replay without paid Anthropic/OpenAI keys.

## Decision

Mint localhost free client keys (`llmreplay-free-…`). Agents talk to LLMReplay proxy; proxy chains to Claude Code Router (CCR) → Ollama. Optional ccg-router fallback.

## Consequences

TTFR depends on Ollama tool capability (degraded mode in SPEC). Nightly smoke uses pinned model digests; PR CI stays hermetic with fake upstreams.
