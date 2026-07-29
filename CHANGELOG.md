# Changelog

All notable changes to this project are documented here.

Format inspired by [Keep a Changelog](https://keepachangelog.com/). Cassette `schema_version` bumps are called out explicitly.

## [Unreleased]

### Added

- C3: HMAC scrub engine, `llmreplay.yaml` profiles (`local`/`ci`/`strict`), residual-secret refuse on ci/strict, proxy `--profile`/`--config`.
- C2: Allowlisted local proxy (record/replay) for Messages, Chat Completions, Responses.
- Standards: Pydantic-first coding standards + cheap-model-only review policy (no Opus for routine review).
- C1: RFC 8785 match/hash pipeline, volatility ignore/thinking strip, cassette store with exclusive lock.
- C0: project bootstrap — Apache-2.0, SPEC, DESIGN progress tracker, CLI (`version`, `doctor`, `exit-codes`), CI skeleton.
