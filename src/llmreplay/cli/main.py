"""Typer CLI entrypoint."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Annotated

import typer

from llmreplay import __version__
from llmreplay.core.exit_codes import EXIT_CODE_HELP, ExitCode

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
    """Check local environment (C0 stub; expands in later chunks)."""
    report = {
        "llmreplay_version": __version__,
        "python": sys.version.split()[0],
        "cwd": str(Path.cwd()),
        "checks": [
            {"id": "cli_installed", "ok": True, "detail": "llmreplay importable"},
            {
                "id": "proxy",
                "ok": False,
                "detail": "proxy not started (ships in C2)",
            },
            {
                "id": "test_stack",
                "ok": False,
                "detail": "CCR+Ollama stack not configured (ships in C5)",
            },
        ],
        "next": "Install with `pip install -e .[dev]` and follow docs/quickstart.md (C5).",
    }
    if json_out:
        typer.echo(json.dumps(report, indent=2))
    else:
        typer.echo(f"llmreplay {__version__}")
        for check in report["checks"]:
            mark = "ok" if check["ok"] else "pending"
            typer.echo(f"  [{mark}] {check['id']}: {check['detail']}")
        typer.echo(f"next: {report['next']}")
    # C0: doctor succeeds as a smoke check even when later components are pending.
    _footer(ExitCode.SUCCESS)
    raise typer.Exit(ExitCode.SUCCESS)


@app.command("exit-codes")
def exit_codes() -> None:
    """List stable process exit codes."""
    for code in ExitCode:
        typer.echo(f"{int(code):2d}  {code.name:28s}  {EXIT_CODE_HELP[code]}")
    _footer(ExitCode.SUCCESS)
    raise typer.Exit(ExitCode.SUCCESS)


if __name__ == "__main__":
    app()
