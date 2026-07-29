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
2. **Coding standards.** Follow [docs/dev/coding-standards.md](docs/dev/coding-standards.md) — **Pydantic v2** at boundaries, typed APIs, Ruff-clean.
3. **Doc-with-code.** Chunk PRs update mapped docs/examples/fixtures.
4. **Tests required.** Unit (+ property when touching hash/scrub). Network denied in PR CI.
5. **One commit per completed chunk** after tests pass; update DESIGN progress in that commit.
6. **No AI attribution** in commits (no Co-authored-by Cursor, etc.).

## Agent review policy

Routine code review / validation: **cheap models only** (e.g. Composer fast, GPT-5.6 medium, Grok, Sonnet).  
**Do not use Claude Opus 4.6** (or other Opus-class flagships) for per-chunk review.

## PR checklist

- [ ] Acceptance block for the chunk (see DESIGN.md)
- [ ] DESIGN.md progress table updated
- [ ] Pydantic models used for new structured data
- [ ] Tests added/updated
- [ ] Docs updated if user-facing
- [ ] No secrets in fixtures
- [ ] Reviewed with a non-Opus model (or human)
