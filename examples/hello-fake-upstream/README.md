# Hello (fake upstream)

Network-free demo of record → replay using the in-process harness (see `scripts/smoke.sh`).

```bash
./scripts/smoke.sh
llmreplay doctor --json
llmreplay test-stack status --json   # may exit 4 without Ollama — expected in CI
```

For a live free path, see [docs/free-test-stack.md](../../docs/free-test-stack.md).
