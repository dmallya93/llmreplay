# Changelog

All notable changes to this project are documented here.

Format inspired by [Keep a Changelog](https://keepachangelog.com/). Cassette `schema_version` bumps are called out explicitly.

## [Unreleased]

### Added

- C10: `migrate` (v0→v1), release smoke, CI OS matrix, nightly workflow, ci/compatibility/threat-model docs.
- C9: Multi-turn Claude/Codex parity harness + goldens; `examples/claude-code-hello` + `codex-hello`; Codex integration docs.
- C8: `fork` / `tweak` / `sticky` / `template` allowlist; `debug_sticky` profile; fork-tweak docs.

### Schema

- Cassette `schema_version` **1** is current. Use `llmreplay migrate` for legacy (v0) manifests.
- C7: Claude Code hooks (`hooks install|verify|decide`), digests, decision force on replay, integration docs.
- C6: Workspace FS snapshots (`snapshot create|restore`), denylist, path-traversal guards, `docs/concepts/snapshots.md`.
- C5: Free test-stack (`test-stack up/down/status`), localhost free keys, CCR config helper, `scripts/smoke.sh`, free-test-stack docs.
- C4: CLI `record`/`replay`/`why`/`mark-ignore`/`mark-live`/`validate`/`bundle`/`docs gen`; expanded `doctor`; troubleshooting + generated CLI reference.
- C3: HMAC scrub engine, `llmreplay.yaml` profiles (`local`/`ci`/`strict`), residual-secret refuse on ci/strict, proxy `--profile`/`--config`.
- C2: Allowlisted local proxy (record/replay) for Messages, Chat Completions, Responses.
- Standards: Pydantic-first coding standards + cheap-model-only review policy (no Opus for routine review).
- C1: RFC 8785 match/hash pipeline, volatility ignore/thinking strip, cassette store with exclusive lock.
- C0: project bootstrap — Apache-2.0, SPEC, DESIGN progress tracker, CLI (`version`, `doctor`, `exit-codes`), CI skeleton.
