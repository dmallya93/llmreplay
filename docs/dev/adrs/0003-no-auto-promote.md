# ADR-0003: No auto-promote

## Context

Mismatches on timestamps tempt tools to auto-mark fields dynamic.

## Decision

Auto-promotion is forbidden. Failures must suggest explicit `mark-ignore` / `mark-live` / `tweak` commands.

## Consequences

Slightly more user friction; much higher cassette trust and reviewability.
