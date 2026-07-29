"""Typer CLI entrypoint."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Annotated

import typer
import uvicorn

from llmreplay import __version__
from llmreplay.core.exit_codes import EXIT_CODE_HELP, ExitCode
from llmreplay.proxy.app import create_app
from llmreplay.proxy.routes import is_allowed

app = typer.Typer(
    name="llmreplay",
    help="VCR / time-travel replay for Claude Code and Codex.",
    no_args_is_help=True,
    add_completion=False,
)


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
) -> None:
    """Check local environment."""
    report = {
        "llmreplay_version": __version__,
        "python": sys.version.split()[0],
        "cwd": str(Path.cwd()),
        "checks": [
            {"id": "cli_installed", "ok": True, "detail": "llmreplay importable"},
            {
                "id": "proxy_routes",
                "ok": is_allowed("GET", "/healthz"),
                "detail": "allowlist loaded (GET /healthz)",
            },
            {
                "id": "test_stack",
                "ok": False,
                "detail": "CCR+Ollama stack not configured (ships in C5)",
            },
        ],
        "next": "Run `llmreplay proxy --help` (C2). Free stack lands in C5.",
    }
    if json_out:
        typer.echo(json.dumps(report, indent=2))
    else:
        typer.echo(f"llmreplay {__version__}")
        for check in report["checks"]:
            mark = "ok" if check["ok"] else "pending"
            typer.echo(f"  [{mark}] {check['id']}: {check['detail']}")
        typer.echo(f"next: {report['next']}")
    _footer(ExitCode.SUCCESS)
    raise typer.Exit(ExitCode.SUCCESS)


@app.command("exit-codes")
def exit_codes() -> None:
    """List stable process exit codes."""
    for code in ExitCode:
        typer.echo(f"{int(code):2d}  {code.name:28s}  {EXIT_CODE_HELP[code]}")
    _footer(ExitCode.SUCCESS)
    raise typer.Exit(ExitCode.SUCCESS)


@app.command()
def proxy(
    mode: Annotated[
        str,
        typer.Option("--mode", help="record or replay"),
    ] = "replay",
    cassette: Annotated[
        Path,
        typer.Option("--cassette", help="Cassette directory"),
    ] = Path(".llmreplay/cassette"),
    upstream: Annotated[
        str | None,
        typer.Option("--upstream", help="Upstream base URL (record mode)"),
    ] = None,
    host: Annotated[str, typer.Option("--host")] = "127.0.0.1",
    port: Annotated[int, typer.Option("--port")] = 7432,
) -> None:
    """Run the local allowlisted LLM proxy (SPEC S5)."""
    if mode not in {"record", "replay"}:
        typer.echo("mode must be record or replay", err=True)
        _footer(ExitCode.ROUTE_OR_PROTOCOL)
        raise typer.Exit(ExitCode.ROUTE_OR_PROTOCOL)
    if mode == "record" and not upstream:
        typer.echo("--upstream is required in record mode", err=True)
        _footer(ExitCode.ROUTE_OR_PROTOCOL)
        raise typer.Exit(ExitCode.ROUTE_OR_PROTOCOL)

    cassette.mkdir(parents=True, exist_ok=True)
    asgi = create_app(mode=mode, cassette_dir=cassette, upstream_base=upstream)  # type: ignore[arg-type]
    typer.echo(f"llmreplay proxy mode={mode} cassette={cassette} http://{host}:{port}")
    uvicorn.run(asgi, host=host, port=port, log_level="info")


if __name__ == "__main__":
    app()
