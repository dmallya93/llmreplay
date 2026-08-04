# Contributing

Thanks for helping build LLMReplay.

## 30-minute onboarding

1. Clone and `pip install -e ".[dev]"`.
2. Read [README.md](README.md) and field classes in [docs/SPEC.md](docs/SPEC.md).
3. Run `llmreplay demo` (one-terminal start→end; no API keys / CCR). Then `pytest -q`.
4. Skim [DESIGN.md](DESIGN.md) and [docs/dev/package-map.md](docs/dev/package-map.md).
5. Pick a good-first-issue or a subsystem from the package map.

## Local validation (required before PR)

```bash
export LLMREPLAY_HMAC_KEY=dev-local-hmac
export LLMREPLAY_CI=1
ruff check src tests
python -m llmreplay.cli.main docs gen --check --output docs/reference/cli.md
pytest -q
bash scripts/mutation_gate.sh
bash scripts/repro_stress.sh
bash scripts/smoke.sh
bash scripts/release_smoke.sh
```

## Rules

1. **SPEC first.** New behavior requires a `docs/SPEC.md` amend (and DESIGN.md if architecture/usage changes) in the same PR.
2. **Coding standards.** Follow [docs/dev/coding-standards.md](docs/dev/coding-standards.md) — **Pydantic v2** at boundaries, typed APIs, Ruff-clean.
3. **Doc-with-code.** User-facing changes update mapped docs/examples/fixtures (keep README testing section accurate).
4. **Tests required.** Unit (+ property when touching hash/scrub). Network not required in PR CI.
5. **No AI attribution** in commits (no Co-authored-by Cursor, etc.).

## Agent review policy

Routine code review / validation: **cheap models only** (e.g. Composer fast, GPT-5.6 medium, Grok, Sonnet).  
**Do not use Claude Opus 4.6** (or other Opus-class flagships) for routine review.

## PR checklist

- [ ] SPEC/DESIGN amended if behavior or architecture changed
- [ ] Pydantic models used for new structured data
- [ ] Tests added/updated
- [ ] Docs updated if user-facing (including README testing section when gates change)
- [ ] No secrets in fixtures
- [ ] Local validation commands above are green
- [ ] Reviewed with a non-Opus model (or human)
