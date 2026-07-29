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
from llmreplay.proxy.app import create_app
from llmreplay.proxy.config import ProxyConfig
from llmreplay.store.cassette import CassetteStore

app = typer.Typer(
    name="llmreplay",
    help="VCR / time-travel replay for Claude Code and Codex.",
    no_args_is_help=True,
    add_completion=False,
)

docs_app = typer.Typer(help="Documentation generators.")
app.add_typer(docs_app, name="docs")


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
) -> ProxyConfig:
    return ProxyConfig(
        mode=mode,  # type: ignore[arg-type]
        cassette_dir=cassette,
        upstream_base=upstream,
        host=host,
        port=port,
        profile=profile,
        config_path=config_file,
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
        str,
        typer.Option("--upstream", help="Upstream base URL"),
    ] = "http://127.0.0.1:3456",
    host: Annotated[str, typer.Option("--host")] = "127.0.0.1",
    port: Annotated[int, typer.Option("--port")] = 7432,
    profile: Annotated[str, typer.Option("--profile")] = "local",
    config_file: Annotated[Path | None, typer.Option("--config")] = None,
) -> None:
    """Start the proxy in record mode (capture upstream traffic into a cassette)."""
    try:
        config = _proxy_config(
            mode="record",
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


if __name__ == "__main__":
    app()
