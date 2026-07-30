# CI

Hermetic PR CI (no paid APIs, no live Ollama required).

## Local (CI-required set)

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
export LLMREPLAY_HMAC_KEY=dev-local-hmac
export LLMREPLAY_CI=1

ruff check src tests
python -m build && twine check dist/*
python -m llmreplay.cli.main docs gen --check --output docs/reference/cli.md
pytest -q
bash scripts/mutation_gate.sh    # coverage floor >=95% (not mutmut)
bash scripts/repro_stress.sh     # multi-tool / chain / 10× identical replay
bash scripts/smoke.sh
bash scripts/release_smoke.sh
```

CI generates `LLMREPLAY_HMAC_KEY` with `openssl rand -hex 32` per job (ephemeral; not committed).

## Workflows

| Workflow | When | What |
|---|---|---|
| `.github/workflows/ci.yml` | push/PR | ruff, docs, pytest, coverage, repro_stress, smoke, release_smoke — Py 3.12–3.13 × ubuntu+macos |
| `.github/workflows/nightly.yml` | schedule / label | free-stack probe + optional Ollama |
| `.github/workflows/publish.yml` | `workflow_dispatch` | manual PyPI publish |

## Consumer repos

To add LLMReplay replay verification to your own repo:

1. Copy `examples/github-actions/llmreplay-replay.yml` into `.github/workflows/`.
2. Set `LLMREPLAY_HMAC_KEY` as a repository secret.
3. Copy `examples/AGENTS.llmreplay.md` content into your `AGENTS.md` or `CLAUDE.md`.

The workflow runs `llmreplay replay --check` on every PR, verifying cassettes are valid for offline replay.

## Network policy

Unmarked replay MUST NOT open outbound sockets (except loopback health). Explicit `mark-live __llm__` may call `--upstream` (`--allow-live` under `ci`/`strict`). Non-loopback bind requires `--allow-remote` **and** `--free` (free-key auth).
