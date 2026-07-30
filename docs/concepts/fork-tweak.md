# Fork, tweak, sticky, templates

## Fork

```bash
llmreplay fork --cassette .llmreplay/cassette --dest .llmreplay/fork-a --seq 3
```

Creates a new `run_id`, copies transactions `[0..seq)`, records lineage in `extensions.lineage`, and drops the suffix.

## Tweak

```bash
llmreplay tweak --cassette .llmreplay/fork-a --seq 2 --field model --value gpt-test
```

Patches the request at `seq` and **invalidates** later transactions (never auto-promote mismatches to ignore).

## Sticky (debug only)

```bash
llmreplay sticky --profile debug_sticky --cassette … --seq 0 --field model --value …
```

`sticky_writeback` is **forbidden** for `ci` / `strict` (exit 6). Use `debug_sticky` locally only.

## Templates

Allowlisted materializers only:

```bash
llmreplay template list
llmreplay template uuid.v4
llmreplay template path_rebase --value /old/repo --from /old --to /new
```

Unknown materializers are rejected.
