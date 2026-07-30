# Security Policy

## Reporting

Report vulnerabilities via **[GitHub Security Advisories](https://github.com/dmallya93/llmreplay/security/advisories/new)** for this repository (do **not** open a public issue for vulnerabilities or leaked secrets).

Target acknowledgment: **5 business days**.

## Secret handling

- Cassettes MUST be scrubbed before sharing (`scrub` class + residual scan).
- Never commit `.env`, API keys, or raw production recordings.
- Diagnostic `bundle` defaults exclude bodies; opt-in only after preview.
- HMAC keys stay in keyring / `LLMREPLAY_HMAC_KEY` — never in git.

## Scope

In scope: recording, scrubbing, proxy open-relay risks, path traversal in snapshots, cassette integrity.

Out of scope: vulnerabilities solely in Claude Code, Codex, CCR, or Ollama upstreams (report upstream; we document workarounds when relevant).

## Threat model

See [docs/threat-model.md](docs/threat-model.md) for trust boundaries and mitigations.
