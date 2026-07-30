# CI

Hermetic PR CI (no paid APIs, no live Ollama required). Set `LLMREPLAY_HMAC_KEY` (CI workflow sets a fixed test key).

## Local (same as CI)

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
export LLMREPLAY_HMAC_KEY=dev-local-hmac
export LLMREPLAY_CI=1

ruff check src tests
python -m llmreplay.cli.main docs gen --check --output docs/reference/cli.md
pytest -q
bash scripts/mutation_gate.sh    # coverage floor >=95% on critical modules
bash scripts/release_smoke.sh    # clean venv install + offline fixture
bash scripts/smoke.sh            # optional: fake-upstream record→replay
```

## Workflows

| Workflow | When | What |
|---|---|---|
| `.github/workflows/ci.yml` | push/PR | ruff, docs check, pytest, coverage gate, release smoke — Python 3.12–3.13 on ubuntu + macos |
| `.github/workflows/nightly.yml` | schedule / `workflow_dispatch` / label | free-stack status probe + optional `--ollama` smoke |
| `.github/workflows/publish.yml` | `workflow_dispatch` | manual PyPI publish |

## Network policy

Unit/contract tests MUST NOT call external LLM APIs. Set `LLMREPLAY_CI=1`. Unmarked replay MUST NOT open outbound sockets (except loopback health). Explicit `mark-live __llm__` may call `--upstream` (requires `--allow-live` under `ci`/`strict`).

## Release smoke

`scripts/release_smoke.sh` creates a clean venv, installs the package, runs `llmreplay --help` / `doctor`, and offline-replays `fixtures/release/offline`.

## Coverage gate

`scripts/mutation_gate.sh` is a **coverage floor** (not mutmut). It fails the job if critical modules drop below 95%.
