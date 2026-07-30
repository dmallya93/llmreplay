"""Typer CLI entrypoint."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer
import uvicorn
from pydantic import ValidationError

from llmreplay import __version__
from llmreplay.cli.docs_gen import check_cli_reference, write_cli_reference
from llmreplay.core.exit_codes import EXIT_CODE_HELP, ExitCode
from llmreplay.diagnose.bundle import create_bundle
from llmreplay.diagnose.doctor import run_doctor
from llmreplay.diagnose.mark import mark_ignore_fields, mark_live_tool
from llmreplay.diagnose.validate import validate_cassette
from llmreplay.diagnose.why import diagnose_miss, load_request_event
from llmreplay.hooks.digest import verify_hook_digests
from llmreplay.hooks.install import install_claude_hooks
from llmreplay.hooks.runtime import run_hook_main
from llmreplay.lineage.fork import fork_cassette
from llmreplay.lineage.sticky import maybe_sticky_write
from llmreplay.lineage.templates import apply_materializer, list_materializers
from llmreplay.lineage.tweak import tweak_transaction
from llmreplay.proxy.app import create_app
from llmreplay.proxy.config import ProxyConfig
from llmreplay.snapshot.engine import create_snapshot, extensions_fs_payload, restore_snapshot
from llmreplay.store.cassette import CassetteStore
from llmreplay.teststack.config import free_mode_env, print_env_exports
from llmreplay.teststack.keys import FreeKeyStore
from llmreplay.teststack.lifecycle import stack_down, stack_status, stack_up
from llmreplay.teststack.models import FreeStackConfig

app = typer.Typer(
    name="llmreplay",
    help="VCR / time-travel replay for Claude Code and Codex.",
    no_args_is_help=True,
    add_completion=False,
)

docs_app = typer.Typer(help="Documentation generators.")
app.add_typer(docs_app, name="docs")

test_stack_app = typer.Typer(help="Free CCR+Ollama test-stack (SPEC S8).")
app.add_typer(test_stack_app, name="test-stack")

keys_app = typer.Typer(help="Free localhost API keys.")
app.add_typer(keys_app, name="keys")

snapshot_app = typer.Typer(help="Workspace filesystem snapshots (SPEC S7).")
app.add_typer(snapshot_app, name="snapshot")

hooks_app = typer.Typer(help="Claude Code hook install/verify/decide (S12).")
app.add_typer(hooks_app, name="hooks")


def _footer(code: ExitCode) -> None:
    msg = EXIT_CODE_HELP[code]
    typer.echo(f"exit {int(code)} = {code.name} — {msg}", err=True)


@app.callback()
def main() -> None:
    """LLMReplay CLI."""


@app.command()
def version() -> None:
    """Print package version."""
    typer.echo(__version__)
    _footer(ExitCode.SUCCESS)
    raise typer.Exit(ExitCode.SUCCESS)


@app.command()
def doctor(
    json_out: Annotated[
        bool,
        typer.Option("--json", help="Emit machine-readable JSON"),
    ] = False,
    cassette: Annotated[
        Path | None,
        typer.Option("--cassette", help="Cassette directory to probe for writability"),
    ] = None,
    port: Annotated[int, typer.Option("--port", help="Proxy port to check")] = 7432,
) -> None:
    """Check local environment; print next action on failure."""
    report = run_doctor(cassette_dir=cassette, proxy_port=port)
    code = ExitCode.SUCCESS if report.ok else ExitCode.ROUTE_OR_PROTOCOL
    if json_out:
        typer.echo(json.dumps(report.model_dump(mode="json"), indent=2))
    else:
        typer.echo(f"llmreplay {__version__}")
        for check in report.checks:
            mark = "ok" if check.ok else "fail"
            typer.echo(f"  [{mark}] {check.id}: {check.detail}")
        typer.echo(f"next: {report.next}")
    _footer(code)
    raise typer.Exit(code)


@app.command("exit-codes")
def exit_codes() -> None:
    """List stable process exit codes."""
    for code in ExitCode:
        typer.echo(f"{int(code):2d}  {code.name:28s}  {EXIT_CODE_HELP[code]}")
    _footer(ExitCode.SUCCESS)
    raise typer.Exit(ExitCode.SUCCESS)


def _run_proxy(config: ProxyConfig) -> None:
    config.cassette_dir.mkdir(parents=True, exist_ok=True)
    asgi = create_app(config=config)
    typer.echo(
        f"llmreplay proxy mode={config.mode} profile={config.profile} "
        f"cassette={config.cassette_dir} http://{config.host}:{config.port}"
    )
    uvicorn.run(asgi, host=config.host, port=config.port, log_level="info")


def _proxy_config(
    *,
    mode: str,
    cassette: Path,
    upstream: str | None,
    host: str,
    port: int,
    profile: str,
    config_file: Path | None,
    free_mode: bool = False,
    free_key_store: Path | None = None,
) -> ProxyConfig:
    return ProxyConfig(
        mode=mode,  # type: ignore[arg-type]
        cassette_dir=cassette,
        upstream_base=upstream,
        host=host,
        port=port,
        profile=profile,
        config_path=config_file,
        free_mode=free_mode,
        free_key_store=free_key_store,
    )


@app.command()
def proxy(
    mode: Annotated[str, typer.Option("--mode", help="record or replay")] = "replay",
    cassette: Annotated[Path, typer.Option("--cassette")] = Path(".llmreplay/cassette"),
    upstream: Annotated[str | None, typer.Option("--upstream")] = None,
    host: Annotated[str, typer.Option("--host")] = "127.0.0.1",
    port: Annotated[int, typer.Option("--port")] = 7432,
    profile: Annotated[str, typer.Option("--profile")] = "local",
    config_file: Annotated[Path | None, typer.Option("--config")] = None,
) -> None:
    """Run the local allowlisted LLM proxy (SPEC S5)."""
    try:
        config = _proxy_config(
            mode=mode,
            cassette=cassette,
            upstream=upstream,
            host=host,
            port=port,
            profile=profile,
            config_file=config_file,
        )
    except (ValidationError, ValueError) as exc:
        typer.echo(str(exc), err=True)
        _footer(ExitCode.ROUTE_OR_PROTOCOL)
        raise typer.Exit(ExitCode.ROUTE_OR_PROTOCOL) from exc
    _run_proxy(config)


@app.command()
def record(
    cassette: Annotated[Path, typer.Option("--cassette")] = Path(".llmreplay/cassette"),
    upstream: Annotated[
        str | None,
        typer.Option("--upstream", help="Upstream base URL"),
    ] = None,
    host: Annotated[str, typer.Option("--host")] = "127.0.0.1",
    port: Annotated[int, typer.Option("--port")] = 7432,
    profile: Annotated[str, typer.Option("--profile")] = "local",
    config_file: Annotated[Path | None, typer.Option("--config")] = None,
    free: Annotated[
        bool,
        typer.Option("--free", help="Free stack: default upstream CCR + cassette test_stack"),
    ] = False,
    free_key_store: Annotated[Path | None, typer.Option("--free-key-store")] = None,
) -> None:
    """Start the proxy in record mode (capture upstream traffic into a cassette)."""
    try:
        config = _proxy_config(
            mode="record",
            cassette=cassette,
            upstream=upstream or "http://127.0.0.1:3456",
            host=host,
            port=port,
            profile=profile,
            config_file=config_file,
            free_mode=free,
            free_key_store=free_key_store,
        )
    except (ValidationError, ValueError) as exc:
        typer.echo(str(exc), err=True)
        _footer(ExitCode.ROUTE_OR_PROTOCOL)
        raise typer.Exit(ExitCode.ROUTE_OR_PROTOCOL) from exc
    if free:
        typer.echo("free-mode: upstream defaults to CCR; write test_stack fingerprint")
    _run_proxy(config)


@app.command()
def replay(
    cassette: Annotated[Path, typer.Option("--cassette")] = Path(".llmreplay/cassette"),
    host: Annotated[str, typer.Option("--host")] = "127.0.0.1",
    port: Annotated[int, typer.Option("--port")] = 7432,
    profile: Annotated[str, typer.Option("--profile")] = "ci",
    config_file: Annotated[Path | None, typer.Option("--config")] = None,
    check: Annotated[
        bool,
        typer.Option("--check", help="Validate cassette for offline replay and exit"),
    ] = False,
    free: Annotated[
        bool,
        typer.Option("--free", help="Free-mode replay (still offline; documents free path)"),
    ] = False,
    free_key_store: Annotated[Path | None, typer.Option("--free-key-store")] = None,
) -> None:
    """Start the proxy in replay mode, or `--check` cassette health offline."""
    if check:
        report = validate_cassette(cassette)
        typer.echo(json.dumps(report.model_dump(mode="json"), indent=2))
        if not report.ok:
            _footer(ExitCode.SCHEMA_OR_REPAIR_REQUIRED)
            raise typer.Exit(ExitCode.SCHEMA_OR_REPAIR_REQUIRED)
        if not CassetteStore(cassette).load_manifest().transactions:
            typer.echo("cassette has no transactions", err=True)
            _footer(ExitCode.CASSETTE_MISSING)
            raise typer.Exit(ExitCode.CASSETTE_MISSING)
        typer.echo("offline replay ready")
        _footer(ExitCode.SUCCESS)
        raise typer.Exit(ExitCode.SUCCESS)
    try:
        config = _proxy_config(
            mode="replay",
            cassette=cassette,
            upstream=None,
            host=host,
            port=port,
            profile=profile,
            config_file=config_file,
            free_mode=free,
            free_key_store=free_key_store,
        )
    except (ValidationError, ValueError) as exc:
        typer.echo(str(exc), err=True)
        _footer(ExitCode.ROUTE_OR_PROTOCOL)
        raise typer.Exit(ExitCode.ROUTE_OR_PROTOCOL) from exc
    _run_proxy(config)


@app.command()
def why(
    cassette: Annotated[Path, typer.Option("--cassette")] = Path(".llmreplay/cassette"),
    request: Annotated[
        Path,
        typer.Option("--request", help="Path to normalized request JSON"),
    ] = Path("request.json"),
    json_out: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    """Explain a static miss and suggest mark-ignore (never auto-applied)."""
    try:
        event = load_request_event(request)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        typer.echo(str(exc), err=True)
        _footer(ExitCode.ROUTE_OR_PROTOCOL)
        raise typer.Exit(ExitCode.ROUTE_OR_PROTOCOL) from exc
    result = diagnose_miss(cassette_dir=cassette, request_event=event)
    if json_out:
        typer.echo(json.dumps(result.model_dump(mode="json"), indent=2))
    else:
        typer.echo(f"matched={result.matched} hash={result.request_hash}")
        if result.closest_tx_id:
            typer.echo(f"closest_tx={result.closest_tx_id}")
        typer.echo(result.suggestion)
    if result.matched:
        _footer(ExitCode.SUCCESS)
        raise typer.Exit(ExitCode.SUCCESS)
    if not result.cassette_hashes:
        _footer(ExitCode.CASSETTE_MISSING)
        raise typer.Exit(ExitCode.CASSETTE_MISSING)
    _footer(ExitCode.STATIC_MISMATCH)
    raise typer.Exit(ExitCode.STATIC_MISMATCH)


@app.command("mark-ignore")
def mark_ignore(
    fields: Annotated[list[str], typer.Argument(help="Field names to ignore")],
    config_file: Annotated[
        Path,
        typer.Option("--config", help="llmreplay.yaml path"),
    ] = Path("llmreplay.yaml"),
    profile: Annotated[str | None, typer.Option("--profile")] = None,
) -> None:
    """Append ignore fields to llmreplay.yaml (explicit only; never auto)."""
    if not fields:
        typer.echo("provide at least one field", err=True)
        _footer(ExitCode.ROUTE_OR_PROTOCOL)
        raise typer.Exit(ExitCode.ROUTE_OR_PROTOCOL)
    mark_ignore_fields(config_file, fields, profile=profile)
    typer.echo(f"updated {config_file}: ignore += {fields}")
    _footer(ExitCode.SUCCESS)
    raise typer.Exit(ExitCode.SUCCESS)


@app.command("mark-live")
def mark_live_cmd(
    tool: Annotated[str, typer.Argument(help="Tool name to mark live")],
    config_file: Annotated[Path, typer.Option("--config")] = Path("llmreplay.yaml"),
) -> None:
    """Mark a tool as live in llmreplay.yaml."""
    mark_live_tool(config_file, tool)
    typer.echo(f"updated {config_file}: tools.{tool}.class=live")
    _footer(ExitCode.SUCCESS)
    raise typer.Exit(ExitCode.SUCCESS)


@app.command()
def validate(
    cassette: Annotated[Path, typer.Option("--cassette")] = Path(".llmreplay/cassette"),
    json_out: Annotated[bool, typer.Option("--json")] = True,
) -> None:
    """Validate cassette layout, refs, and residual secrets."""
    report = validate_cassette(cassette)
    typer.echo(json.dumps(report.model_dump(mode="json"), indent=2))
    if report.ok:
        _footer(ExitCode.SUCCESS)
        raise typer.Exit(ExitCode.SUCCESS)
    if any(i.code == "residual_secret" for i in report.issues):
        _footer(ExitCode.SECRET_SCRUB_OR_LIMIT)
        raise typer.Exit(ExitCode.SECRET_SCRUB_OR_LIMIT)
    _footer(ExitCode.SCHEMA_OR_REPAIR_REQUIRED)
    raise typer.Exit(ExitCode.SCHEMA_OR_REPAIR_REQUIRED)


@app.command()
def bundle(
    cassette: Annotated[Path, typer.Option("--cassette")] = Path(".llmreplay/cassette"),
    output: Annotated[Path, typer.Option("--output")] = Path("llmreplay-bundle.zip"),
    no_scrub: Annotated[bool, typer.Option("--no-scrub")] = False,
    include_bodies: Annotated[bool, typer.Option("--include-bodies")] = False,
) -> None:
    """Create a scrubbed, previewable diagnostic zip."""
    result = create_bundle(
        cassette,
        output,
        scrub=not no_scrub,
        include_bodies=include_bodies,
    )
    typer.echo(json.dumps(result.model_dump(mode="json"), indent=2))
    _footer(ExitCode.SUCCESS)
    raise typer.Exit(ExitCode.SUCCESS)


@docs_app.command("gen")
def docs_gen(
    check: Annotated[
        bool,
        typer.Option("--check", help="Fail if docs/reference/cli.md is stale"),
    ] = False,
    output: Annotated[
        Path,
        typer.Option("--output"),
    ] = Path("docs/reference/cli.md"),
) -> None:
    """Generate or check the CLI reference markdown."""
    if check:
        if check_cli_reference(output, app):
            typer.echo(f"ok: {output} is up to date")
            _footer(ExitCode.SUCCESS)
            raise typer.Exit(ExitCode.SUCCESS)
        typer.echo(f"stale: {output} — run `llmreplay docs gen`", err=True)
        _footer(ExitCode.SCHEMA_OR_REPAIR_REQUIRED)
        raise typer.Exit(ExitCode.SCHEMA_OR_REPAIR_REQUIRED)
    write_cli_reference(output, app)
    typer.echo(f"wrote {output}")
    _footer(ExitCode.SUCCESS)
    raise typer.Exit(ExitCode.SUCCESS)


@test_stack_app.command("up")
def test_stack_up(
    config_dir: Annotated[
        Path | None,
        typer.Option("--config-dir", help="Where to write generated CCR config"),
    ] = None,
    model: Annotated[str, typer.Option("--model")] = "qwen2.5-coder:latest",
) -> None:
    """Materialize free-stack config and print setup instructions."""
    cfg = FreeStackConfig(ollama_model=model)
    if config_dir is not None:
        cfg = cfg.model_copy(update={"config_dir": config_dir})
    result = stack_up(cfg)
    typer.echo(json.dumps(result.model_dump(mode="json"), indent=2))
    for line in result.instructions:
        typer.echo(line)
    _footer(ExitCode.SUCCESS)
    raise typer.Exit(ExitCode.SUCCESS)


@test_stack_app.command("down")
def test_stack_down(
    config_dir: Annotated[Path | None, typer.Option("--config-dir")] = None,
    purge: Annotated[bool, typer.Option("--purge", help="Delete generated files")] = False,
) -> None:
    """Tear down generated test-stack files (does not kill Ollama/CCR)."""
    cfg = FreeStackConfig()
    if config_dir is not None:
        cfg = cfg.model_copy(update={"config_dir": config_dir})
    path = stack_down(cfg, purge=purge)
    typer.echo(f"test-stack down config_dir={path} purge={purge}")
    _footer(ExitCode.SUCCESS)
    raise typer.Exit(ExitCode.SUCCESS)


@test_stack_app.command("status")
def test_stack_status_cmd(
    json_out: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    """Probe Ollama/CCR/proxy; exit 4 when unhealthy."""
    report = stack_status()
    if json_out:
        typer.echo(json.dumps(report.model_dump(mode="json"), indent=2))
    else:
        mark = "healthy" if report.healthy else "unhealthy"
        typer.echo(f"test-stack {mark} degraded={report.degraded}")
        for comp in report.components:
            typer.echo(f"  [{'ok' if comp.ok else 'fail'}] {comp.name}: {comp.detail}")
        typer.echo(f"next: {report.next}")
    if report.healthy:
        _footer(ExitCode.SUCCESS)
        raise typer.Exit(ExitCode.SUCCESS)
    _footer(ExitCode.TEST_STACK_UNHEALTHY)
    raise typer.Exit(ExitCode.TEST_STACK_UNHEALTHY)


@keys_app.command("create")
def keys_create(
    free: Annotated[
        bool,
        typer.Option("--free", help="Create a localhost-only free key"),
    ] = True,
    store: Annotated[
        Path | None,
        typer.Option("--store", help="Key store path"),
    ] = None,
    quota: Annotated[int, typer.Option("--quota")] = 10_000,
    print_env: Annotated[
        bool,
        typer.Option("--print-env", help="Print shell exports for agent wiring"),
    ] = True,
    proxy: Annotated[str, typer.Option("--proxy")] = "http://127.0.0.1:7432",
) -> None:
    """Create a free localhost key (never write the token into cassettes)."""
    if not free:
        typer.echo("only --free keys are supported in C5", err=True)
        _footer(ExitCode.ROUTE_OR_PROTOCOL)
        raise typer.Exit(ExitCode.ROUTE_OR_PROTOCOL)
    store_path = store or (Path.home() / ".llmreplay" / "free-keys.json")
    record = FreeKeyStore(store_path).create(quota=quota)
    payload = record.model_dump(mode="json")
    typer.echo(json.dumps(payload, indent=2))
    if print_env:
        env = free_mode_env(proxy_base=proxy, free_token=record.token)
        typer.echo(print_env_exports(env))
    _footer(ExitCode.SUCCESS)
    raise typer.Exit(ExitCode.SUCCESS)


@snapshot_app.command("create")
def snapshot_create(
    workspace: Annotated[Path, typer.Option("--workspace")] = Path("."),
    dest: Annotated[Path, typer.Option("--dest")] = Path(".llmreplay/cassette/snapshots"),
    snapshot_id: Annotated[str, typer.Option("--id")] = "snap",
) -> None:
    """Capture a denylisted workspace snapshot (tar.zst + json)."""
    meta = create_snapshot(workspace, dest, snapshot_id=snapshot_id)
    typer.echo(json.dumps(meta.model_dump(mode="json"), indent=2))
    typer.echo(json.dumps({"extensions.fs": extensions_fs_payload(meta)}, indent=2))
    _footer(ExitCode.SUCCESS)
    raise typer.Exit(ExitCode.SUCCESS)


@snapshot_app.command("restore")
def snapshot_restore(
    snapshot_id: Annotated[str, typer.Option("--id")] = "snap",
    dest: Annotated[Path, typer.Option("--dest")] = Path(".llmreplay/cassette/snapshots"),
    workspace: Annotated[Path, typer.Option("--workspace")] = Path("."),
    force: Annotated[bool, typer.Option("--force")] = False,
) -> None:
    """Restore a snapshot into a workspace root."""
    try:
        meta = restore_snapshot(dest, snapshot_id, workspace, force=force)
    except (OSError, RuntimeError, PermissionError) as exc:
        typer.echo(str(exc), err=True)
        _footer(ExitCode.SCHEMA_OR_REPAIR_REQUIRED)
        raise typer.Exit(ExitCode.SCHEMA_OR_REPAIR_REQUIRED) from exc
    typer.echo(json.dumps(meta.model_dump(mode="json"), indent=2))
    _footer(ExitCode.SUCCESS)
    raise typer.Exit(ExitCode.SUCCESS)


@hooks_app.command("install")
def hooks_install(
    hooks_dir: Annotated[
        Path,
        typer.Option("--dir", help="Directory for hook scripts"),
    ] = Path(".llmreplay/hooks"),
    mode: Annotated[str, typer.Option("--mode", help="record or replay")] = "record",
    cassette: Annotated[Path, typer.Option("--cassette")] = Path(".llmreplay/cassette"),
) -> None:
    """Install Claude Code Pre/PostToolUse hook wrappers and record digests."""
    result = install_claude_hooks(hooks_dir, mode=mode)
    CassetteStore(cassette).set_hook_digests(result.digests)
    typer.echo(json.dumps(result.model_dump(mode="json"), indent=2))
    _footer(ExitCode.SUCCESS)
    raise typer.Exit(ExitCode.SUCCESS)


@hooks_app.command("verify")
def hooks_verify(
    hooks_dir: Annotated[Path, typer.Option("--dir")] = Path(".llmreplay/hooks"),
    cassette: Annotated[Path, typer.Option("--cassette")] = Path(".llmreplay/cassette"),
    profile: Annotated[str, typer.Option("--profile")] = "ci",
) -> None:
    """Verify hook script digests against the cassette (exit 6 on ci/strict mismatch)."""
    scripts = {
        "PreToolUse": hooks_dir / "pre_tool_use.py",
        "PostToolUse": hooks_dir / "post_tool_use.py",
    }
    present = {k: v for k, v in scripts.items() if v.is_file()}
    result = verify_hook_digests(CassetteStore(cassette), present, profile=profile)
    typer.echo(json.dumps(result.model_dump(mode="json"), indent=2))
    if not result.ok:
        _footer(ExitCode.HOOK_OR_POLICY_DIVERGENCE)
        raise typer.Exit(ExitCode.HOOK_OR_POLICY_DIVERGENCE)
    _footer(ExitCode.SUCCESS)
    raise typer.Exit(ExitCode.SUCCESS)


@hooks_app.command("decide")
def hooks_decide(
    mode: Annotated[str, typer.Option("--mode")] = "record",
) -> None:
    """Read one hook JSON from stdin and emit a decision line (for wrapper scripts)."""
    code = run_hook_main(mode=mode)
    raise typer.Exit(code)


@app.command()
def fork(
    cassette: Annotated[Path, typer.Option("--cassette")] = Path(".llmreplay/cassette"),
    dest: Annotated[Path, typer.Option("--dest")] = Path(".llmreplay/fork"),
    seq: Annotated[int, typer.Option("--seq", help="Fork before this transaction index")] = 0,
) -> None:
    """Fork a cassette at seq N into a new run_id (shared prefix, drop suffix)."""
    try:
        run_id, manifest = fork_cassette(cassette, dest, seq=seq)
    except (OSError, ValueError, FileExistsError) as exc:
        typer.echo(str(exc), err=True)
        _footer(ExitCode.SCHEMA_OR_REPAIR_REQUIRED)
        raise typer.Exit(ExitCode.SCHEMA_OR_REPAIR_REQUIRED) from exc
    typer.echo(
        json.dumps(
            {
                "run_id": run_id,
                "transactions": len(manifest.transactions),
                "dest": str(dest),
            },
            indent=2,
        )
    )
    _footer(ExitCode.SUCCESS)
    raise typer.Exit(ExitCode.SUCCESS)


@app.command()
def tweak(
    cassette: Annotated[Path, typer.Option("--cassette")] = Path(".llmreplay/cassette"),
    seq: Annotated[int, typer.Option("--seq")] = 0,
    field: Annotated[str, typer.Option("--field")] = "model",
    value: Annotated[str, typer.Option("--value")] = "",
) -> None:
    """Patch a request field at seq and invalidate later transactions."""
    try:
        result = tweak_transaction(cassette, seq=seq, field=field, value=value)
    except (OSError, IndexError, KeyError) as exc:
        typer.echo(str(exc), err=True)
        _footer(ExitCode.SCHEMA_OR_REPAIR_REQUIRED)
        raise typer.Exit(ExitCode.SCHEMA_OR_REPAIR_REQUIRED) from exc
    typer.echo(json.dumps(result.model_dump(mode="json"), indent=2))
    _footer(ExitCode.SUCCESS)
    raise typer.Exit(ExitCode.SUCCESS)


@app.command()
def sticky(
    cassette: Annotated[Path, typer.Option("--cassette")] = Path(".llmreplay/cassette"),
    profile: Annotated[str, typer.Option("--profile")] = "debug_sticky",
    seq: Annotated[int, typer.Option("--seq")] = 0,
    field: Annotated[str, typer.Option("--field")] = "model",
    value: Annotated[str, typer.Option("--value")] = "",
    config_file: Annotated[Path | None, typer.Option("--config")] = None,
) -> None:
    """Debug sticky writeback of a mismatch (forbidden in ci/strict)."""
    result = maybe_sticky_write(
        cassette,
        profile=profile,
        seq=seq,
        field=field,
        value=value,
        config_path=config_file,
    )
    typer.echo(json.dumps(result.model_dump(mode="json"), indent=2))
    if not result.applied:
        _footer(ExitCode.HOOK_OR_POLICY_DIVERGENCE)
        raise typer.Exit(ExitCode.HOOK_OR_POLICY_DIVERGENCE)
    _footer(ExitCode.SUCCESS)
    raise typer.Exit(ExitCode.SUCCESS)


@app.command("template")
def template_cmd(
    name: Annotated[str, typer.Argument(help="Materializer name or 'list'")],
    value: Annotated[str, typer.Option("--value")] = "",
    from_path: Annotated[str | None, typer.Option("--from")] = None,
    to_path: Annotated[str | None, typer.Option("--to")] = None,
) -> None:
    """Apply an allowlisted template materializer (or list them)."""
    if name == "list":
        typer.echo(json.dumps(list_materializers(), indent=2))
        _footer(ExitCode.SUCCESS)
        raise typer.Exit(ExitCode.SUCCESS)
    ctx: dict[str, object] = {}
    if from_path is not None:
        ctx["from"] = from_path
    if to_path is not None:
        ctx["to"] = to_path
    try:
        result = apply_materializer(name, value, ctx)
    except KeyError as exc:
        typer.echo(str(exc), err=True)
        _footer(ExitCode.ROUTE_OR_PROTOCOL)
        raise typer.Exit(ExitCode.ROUTE_OR_PROTOCOL) from exc
    typer.echo(json.dumps(result.model_dump(mode="json"), indent=2))
    _footer(ExitCode.SUCCESS)
    raise typer.Exit(ExitCode.SUCCESS)


if __name__ == "__main__":
    app()
