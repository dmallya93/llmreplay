# Threat model (stub — expanded in C10)

## Assets

Free keys, HMAC key, prompts, tool I/O, snapshots, cassette integrity.

## Trust boundaries

Agent CLI → hooks → LLMReplay proxy → CCR → Ollama/provider; shared cassette storage.

## Threats

Secret capture, open-proxy/SSRF, cassette tampering, path traversal, token leakage, malicious hooks, replay escaping to upstream.

## Mitigations

Localhost bind default, route allowlist, redact-before-disk, network deny in replay, checksums, scrub before bundle, atomic writes.
