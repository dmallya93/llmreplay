# Changelog

All notable changes to this project are documented here.

Format inspired by [Keep a Changelog](https://keepachangelog.com/). Cassette `schema_version` bumps are called out explicitly.

## [Unreleased]

## [0.2.1] — 2026-08-04

### Added

- `llmreplay demo` — one-terminal start→end showcase (stub gateway + record + replay; no API keys / CCR).

### Changed

- `llmreplay run` / local `record` / `replay` auto-set `LLMREPLAY_HMAC_KEY=dev-local-hmac` when unset (stable local default).
- `llmreplay run --mode record` and `llmreplay record` require explicit `--upstream` or `--free` (no silent CCR `:3456` default).
- Docs / examples / hero GIF lead with `llmreplay demo` / one-terminal `run`; two-terminal + free-stack demoted.

## [0.2.0] — 2026-07-30

### Added

- `llmreplay run` — single-process proxy + child lifecycle (`ANTHROPIC_BASE_URL`, `OPENAI_BASE_URL` with `/v1`, HMAC stripped from child env).
- Public library API: `ReplayTransport`, `RecordTransport`, lazy top-level exports.
- `ProtocolAdapter` registry (Anthropic Messages / OpenAI Chat+Responses); proxy SSE routes through adapters.
- pytest plugin: `@pytest.mark.llmreplay` + async `llmreplay_cassette` fixture.
- Consumer GitHub Action template + `examples/AGENTS.llmreplay.md`.
- Claude Code plugin skills (`record` / `replay` / `why`).
- Portable-cassette guidance; free-stack demoted to optional.

### Schema

- Cassette `schema_version` **1** remains current (no bump in 0.2.0).

## [0.1.0] — 2026-07-30

### Added

- C10: `migrate` (v0→v1), release smoke, CI OS matrix, nightly workflow, ci/compatibility/threat-model docs.
- C9: Multi-turn Claude/Codex parity harness + goldens; `examples/claude-code-hello` + `codex-hello`; Codex integration docs.
- C8: `fork` / `tweak` / `sticky` / `template` allowlist; `debug_sticky` profile; fork-tweak docs.
- C7: Claude Code hooks (`hooks install|verify|decide`), digests, decision force on replay, integration docs.
- C6: Workspace FS snapshots (`snapshot create|restore`), denylist, path-traversal guards, `docs/concepts/snapshots.md`.
- C5: Free test-stack (`test-stack up/down/status`), localhost free keys, CCR config helper, `scripts/smoke.sh`, free-test-stack docs.
- C4: CLI `record`/`replay`/`why`/`mark-ignore`/`mark-live`/`validate`/`bundle`/`docs gen`; expanded `doctor`; troubleshooting + generated CLI reference.
- C3: HMAC scrub engine, `llmreplay.yaml` profiles (`local`/`ci`/`strict`), residual-secret refuse on ci/strict, proxy `--profile`/`--config`.
- C2: Allowlisted local proxy (record/replay) for Messages, Chat Completions, Responses.
- C1: RFC 8785 match/hash pipeline, volatility ignore/thinking strip, cassette store with exclusive lock.
- C0: project bootstrap — Apache-2.0, SPEC, DESIGN, CLI (`version`, `doctor`, `exit-codes`), CI skeleton.

### Schema

- Cassette `schema_version` **1** is current. Use `llmreplay migrate` for legacy (v0) manifests.
