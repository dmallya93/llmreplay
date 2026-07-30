"""Allowlisted template materializers (field class ``template``)."""

from __future__ import annotations

import re
import uuid
from collections.abc import Callable
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict

Materializer = Callable[[Any, dict[str, Any]], Any]

_ALLOWED: dict[str, Materializer] = {}


def materializer(name: str) -> Callable[[Materializer], Materializer]:
    def deco(fn: Materializer) -> Materializer:
        _ALLOWED[name] = fn
        return fn

    return deco


@materializer("uuid.v4")
def _uuid_v4(_value: Any, _ctx: dict[str, Any]) -> str:
    return str(uuid.uuid4())


@materializer("path_rebase")
def _path_rebase(value: Any, ctx: dict[str, Any]) -> str:
    if not isinstance(value, str):
        raise TypeError("path_rebase expects a string path")
    old = str(ctx.get("from", ""))
    new = str(ctx.get("to", ""))
    if not old:
        raise ValueError("path_rebase requires ctx['from']")
    return value.replace(old, new)


class MaterializeResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    output: Any


def apply_materializer(
    name: str, value: Any, ctx: dict[str, Any] | None = None
) -> MaterializeResult:
    if name not in _ALLOWED:
        raise KeyError(f"unknown materializer {name!r}; allowlist={sorted(_ALLOWED)}")
    out = _ALLOWED[name](value, ctx or {})
    return MaterializeResult(name=name, output=out)


def list_materializers() -> list[str]:
    return sorted(_ALLOWED)


_TEMPLATE_RE = re.compile(r"\{\{([a-zA-Z0-9_.]+)(?::([^}]+))?\}\}")


def expand_templates(text: str, ctx: dict[str, Any] | None = None) -> str:
    """Expand ``{{uuid.v4}}`` / ``{{path_rebase:/old}}`` style tokens."""

    def repl(match: re.Match[str]) -> str:
        name = match.group(1)
        arg = match.group(2)
        local = dict(ctx or {})
        if name == "path_rebase" and arg is not None:
            local.setdefault("from", arg)
        return str(apply_materializer(name, arg or "", local).output)

    return _TEMPLATE_RE.sub(repl, text)


def materialize_file(path: Path, ctx: dict[str, Any] | None = None) -> str:
    text = path.read_text(encoding="utf-8")
    return expand_templates(text, ctx)
