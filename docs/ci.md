# CI

Hermetic PR CI (no paid APIs, no live Ollama required):

```bash
pip install -e ".[dev]"
ruff check src tests
python -m llmreplay.cli.main docs gen --check --output docs/reference/cli.md
pytest -q
./scripts/release_smoke.sh
./scripts/mutation_gate.sh   # coverage floor on critical modules
```

## Workflows

| Workflow | When | What |
|---|---|---|
| `.github/workflows/ci.yml` | push/PR | ruff, docs check, pytest on Python 3.12–3.13 (ubuntu + macos) |
| `.github/workflows/nightly.yml` | schedule / `workflow_dispatch` / label | free-stack status probe + optional `--ollama` smoke |

## Network policy

Unit/contract tests MUST NOT call external LLM APIs. Set `LLMREPLAY_CI=1`. Replay mode MUST NOT open outbound sockets (except loopback health).

## Release smoke

`scripts/release_smoke.sh` creates a clean venv, installs the package, runs `llmreplay --help` / `doctor`, and offline-replays a scrubbed fixture.
