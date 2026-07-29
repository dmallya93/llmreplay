# Snapshots (FS)

Workspace filesystem snapshots (`tar.zst` + `snapshot.json`) pin the tree the agent saw (SPEC S7).

## Semantics

- Capture tracked files under a workspace root (Unicode NFC paths).
- **Denylist** excludes secrets (`.env`, SSH keys, AWS credentials, …) from the blob.
- Restore refuses a dirty destination unless `--force`.
- Path traversal (`..`, absolute members) is rejected.
- `manifest_hash` is SHA-256 over relative path + file bytes; restore MUST match.
- Cassette header may record `extensions.fs` with `{snapshot_id, manifest_hash, file_count}`.

Match keys may include the snapshot hash when FS is part of the static projection (wired as agents adopt snapshot boundaries in C7+).
