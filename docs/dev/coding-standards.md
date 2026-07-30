# Coding standards (enforced)

These rules apply to **all** LLMReplay code and to any agent that implements or reviews changes.

## Non-negotiables

1. **Pydantic v2 for structured data** — request/response envelopes, configs, manifests, CLI-validated options that cross module boundaries. Prefer `BaseModel` / `BaseSettings` over raw `dict[str, Any]` and ad-hoc dataclasses for serializable state.
2. **Type hints on all public functions** — including return types. Use `X | None`, not `Optional[X]`.
3. **Imports at module top** — no inline imports except documented circular-import exceptions with a comment.
4. **Double quotes**, Ruff format/lint clean (`ruff check`, `ruff format`).
5. **No secrets in fixtures, logs, or cassettes** — scrub before disk (SPEC S2).
6. **SPEC amend in the same PR** as behavior changes.
7. **Tests with the change** — unit/contract; property tests for hash/normalize/scrub.
8. **Exit codes** — use `llmreplay.core.exit_codes.ExitCode`; never invent ad-hoc integers.

## Pydantic conventions

```python
from pydantic import BaseModel, Field, ConfigDict


class CassetteTransaction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    request_ref: str
    response_ref: str
    static_hash: str = Field(min_length=64, max_length=64)
```

- `extra="forbid"` on **internal** request/response DTOs.
- On-disk cassette models: `extra="allow"` when SPEC/JSON Schema permits `additionalProperties` / `extensions`.
- Manifest / on-disk JSON: `model_dump(mode="json")` / `model_validate`.
- Settings: `pydantic_settings.BaseSettings` with `LLMREPLAY_` env prefix when added.

## Allowed exceptions

- Tight inner loops / pure algorithmic helpers may use plain dicts **locally** if converted at the boundary via Pydantic.
- Starlette/ASGI `Request`/`Response` stay framework-native; parse bodies into Pydantic immediately.

## Agent coding policy

When an agent implements a change it MUST:

1. Read `docs/SPEC.md` + this file first.
2. Prefer extending existing Pydantic models over new `dict` bags.
3. Run `ruff check` + `pytest` before claiming done.
4. Amend `docs/SPEC.md` (and `DESIGN.md` if architecture/usage changes) in the same PR.

## Agent review policy (cheap models only)

Code review and validation agents MUST use **cost-efficient** models, for example:

- `composer-2.5-fast`
- `gpt-5.6-sol-medium` / `gpt-5.6-terra-medium`
- `claude-4.6-sonnet-high-thinking` (only if needed)
- `cursor-grok-4.5-high`

**Do NOT use Claude Opus 4.6 (or other flagship Opus-class models) for routine code review or validation.** Reserve the largest models for rare architecture disputes.

Review checklist:

- [ ] Pydantic at boundaries
- [ ] SPEC compliance
- [ ] Tests cover happy + deny/miss paths
- [ ] No secret leakage
- [ ] Docs/DESIGN updated
