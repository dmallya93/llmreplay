# ADR-0001: Field classes

## Context

Agent replays must tolerate volatile transport fields without green-passing behavioral drift.

## Decision

Use four primary classes: `static`, `ignore`, `scrub`, `live`, plus allowlisted `template`. Decision inputs are static by default. Never auto-promote mismatches to ignore.

## Consequences

Matchers and CI become teachable; users explicitly widen ignore lists. False greens from over-ignore remain a user config risk documented in SUPPORT.
