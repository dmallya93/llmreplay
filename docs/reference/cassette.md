# Cassette format (v1)

On-disk layout (SPEC S4):

```text
<cassette-root>/
  cassette.json
  cassette.json.bak.<n>
  requests/<id>.json
  responses/<id>.json
  bodies/<sha256>.bin
  snapshots/<id>.tar.zst
  snapshots/<id>.json
  hooks/decisions.jsonl
  locks/cassette.lock
```

## Manifest

Validated by [`schemas/cassette.v1.json`](../../schemas/cassette.v1.json).

Required fields: `schema_version`, `cassette_id`, `transactions`.

Each transaction requires: `id`, `request_ref`, `response_ref`, `static_hash`.

Optional / extensions: `extensions` (FS + `session` nested digests), `tool_id_map`, `hook_digests`, `test_stack`, `checksums`.

## Writing

Use `llmreplay.store.cassette.CassetteStore` — exclusive lock, tmp → fsync → rename.

## Migrate

```bash
llmreplay migrate --cassette path/to/cassette --dry-run
llmreplay migrate --cassette path/to/cassette
```

Current schema: **1**. Legacy manifests without `schema_version` are treated as **0** and upgraded (`request`/`response` → `request_ref`/`response_ref`). A backup `cassette.json.bak.pre-migrate-vN` is written.
