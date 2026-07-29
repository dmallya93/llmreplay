# Contributing

Thanks for helping build LLMReplay.

## 30-minute onboarding

1. Clone and `pip install -e ".[dev]"`.
2. Read [README.md](README.md) “Core ideas” and the field-class table in [docs/SPEC.md](docs/SPEC.md).
3. Run `llmreplay doctor` and `pytest`.
4. Open [DESIGN.md](DESIGN.md) progress table; pick the next **planned** chunk (or a good-first-issue).
5. Open [docs/dev/chunk-map.md](docs/dev/chunk-map.md) for package ownership.

## Rules

1. **SPEC first.** New behavior requires a `docs/SPEC.md` / `DESIGN.md` amend in the same PR.
2. **Doc-with-code.** Chunk PRs update mapped docs/examples/fixtures.
3. **Tests required.** Unit (+ property when touching hash/scrub). Network denied in PR CI.
4. **Multi-check.** `ruff check`, `pytest` green before review.
5. **No AI attribution** in commits (no Co-authored-by Cursor, etc.).

## PR checklist

- [ ] Acceptance block for the chunk (see DESIGN.md)
- [ ] DESIGN.md progress table updated
- [ ] Tests added/updated
- [ ] Docs updated if user-facing
- [ ] No secrets in fixtures
