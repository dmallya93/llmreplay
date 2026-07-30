"""HMAC scrubbing (SPEC S2)."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import secrets
from copy import deepcopy
from typing import Any

from llmreplay.scrub.patterns import ScrubPatterns, load_scrub_patterns

PLACEHOLDER_PREFIX = "«REDACTED:hmac:"
PLACEHOLDER_SUFFIX = "»"
_PLACEHOLDER_RE = re.compile(
    re.escape(PLACEHOLDER_PREFIX) + r"[0-9a-f]{16}" + re.escape(PLACEHOLDER_SUFFIX)
)
_PROCESS_HMAC_KEY: bytes | None = None


def resolve_hmac_key(explicit: bytes | None = None) -> bytes:
    """Resolve HMAC key from arg, env, or random per-process key.

    SPEC prefers OS keyring or ``LLMREPLAY_HMAC_KEY``. CI MUST set the env var
    for stable placeholders across runs.
    """
    global _PROCESS_HMAC_KEY
    if explicit is not None:
        return explicit
    env = os.environ.get("LLMREPLAY_HMAC_KEY")
    if env:
        return env.encode("utf-8")
    # Random per-process key — not stable across restarts (doctor warns).
    if _PROCESS_HMAC_KEY is None:
        _PROCESS_HMAC_KEY = secrets.token_bytes(32)
    return _PROCESS_HMAC_KEY


def hmac_placeholder(secret: str, key: bytes) -> str:
    digest = hmac.new(key, secret.encode("utf-8"), hashlib.sha256).hexdigest()[:16]
    return f"{PLACEHOLDER_PREFIX}{digest}{PLACEHOLDER_SUFFIX}"


def _mask_placeholders(text: str) -> str:
    """Strip known placeholders so residual regexes do not false-positive."""
    return _PLACEHOLDER_RE.sub("", text)


class Scrubber:
    """Scrub secrets from headers and nested JSON values."""

    def __init__(
        self,
        *,
        patterns: ScrubPatterns | None = None,
        hmac_key: bytes | None = None,
        extra_sensitive_keys: list[str] | None = None,
        extra_scrub_paths: list[str] | None = None,
    ) -> None:
        self.patterns = patterns or load_scrub_patterns()
        self.hmac_key = resolve_hmac_key(hmac_key)
        self._compiled = [
            (item.name, re.compile(item.pattern)) for item in self.patterns.secret_regexes
        ]
        self._header_keys = {k.lower() for k in self.patterns.scrub_header_keys}
        keys = list(self.patterns.sensitive_keys)
        if extra_sensitive_keys:
            keys.extend(extra_sensitive_keys)
        self._sensitive_keys = {k.lower() for k in keys}
        paths = list(self.patterns.scrub_paths)
        if extra_scrub_paths:
            paths.extend(extra_scrub_paths)
        self._scrub_paths = paths

    def scrub_string(self, value: str) -> str:
        out = value
        for _name, cre in self._compiled:

            def _repl(match: re.Match[str]) -> str:
                return hmac_placeholder(match.group(0), self.hmac_key)

            out = cre.sub(_repl, out)
        return out

    def scrub_headers(self, headers: dict[str, str]) -> dict[str, str]:
        cleaned: dict[str, str] = {}
        for key, value in headers.items():
            if key.lower() in self._header_keys:
                cleaned[key] = hmac_placeholder(value, self.hmac_key)
            else:
                cleaned[key] = self.scrub_string(value)
        return cleaned

    def scrub_value(self, value: Any, *, key_hint: str | None = None) -> Any:
        if isinstance(value, str):
            if key_hint and key_hint.lower() in self._sensitive_keys:
                return hmac_placeholder(value, self.hmac_key)
            return self.scrub_string(value)
        if isinstance(value, dict):
            return {str(k): self.scrub_value(v, key_hint=str(k)) for k, v in value.items()}
        if isinstance(value, list):
            return [self.scrub_value(v) for v in value]
        return value

    def _scrub_dotted_path(self, data: dict[str, Any], path: str) -> None:
        parts = [p for p in path.lstrip("$.").split(".") if p]
        if not parts:
            return
        cur: Any = data
        for part in parts[:-1]:
            if isinstance(cur, dict) and part in cur:
                cur = cur[part]
            elif isinstance(cur, list) and part.isdigit():
                idx = int(part)
                if 0 <= idx < len(cur):
                    cur = cur[idx]
                else:
                    return
            else:
                return
        leaf = parts[-1]
        if isinstance(cur, dict) and leaf in cur and isinstance(cur[leaf], str):
            cur[leaf] = hmac_placeholder(cur[leaf], self.hmac_key)
        elif isinstance(cur, list) and leaf.isdigit():
            idx = int(leaf)
            if 0 <= idx < len(cur) and isinstance(cur[idx], str):
                cur[idx] = hmac_placeholder(cur[idx], self.hmac_key)

    def scrub_event(self, event: dict[str, Any]) -> dict[str, Any]:
        """Return a deep-scrubbed copy of a normalized request event."""
        data = deepcopy(event)
        if isinstance(data.get("headers"), dict):
            data["headers"] = self.scrub_headers(
                {str(k): str(v) for k, v in data["headers"].items()}
            )
        if "body" in data:
            data["body"] = self.scrub_value(data["body"])
        if "path" in data and isinstance(data["path"], str):
            data["path"] = self.scrub_string(data["path"])
        if "query" in data:
            data["query"] = self.scrub_value(data["query"])
        for path in self._scrub_paths:
            self._scrub_dotted_path(data, path)
        return data

    def scrub_response(self, response: dict[str, Any]) -> dict[str, Any]:
        data = self.scrub_value(deepcopy(response))
        if isinstance(data, dict):
            for path in self._scrub_paths:
                self._scrub_dotted_path(data, path)
        return data

    def scrub_raw_text(self, text: str) -> str:
        """Scrub a raw buffer (stream-ingress / log-safe)."""
        return self.scrub_string(text)


def residual_secret_hits(text: str, patterns: ScrubPatterns | None = None) -> list[str]:
    """Return pattern names that still match (post-scrub detector)."""
    cfg = patterns or load_scrub_patterns()
    probe = _mask_placeholders(text)
    hits: list[str] = []
    for item in cfg.secret_regexes:
        if re.search(item.pattern, probe):
            hits.append(item.name)
    return hits


def residual_hits_in_payload(
    payload: Any,
    patterns: ScrubPatterns | None = None,
) -> list[str]:
    """Scan a JSON-serializable payload for residual secrets."""
    text = json.dumps(payload, ensure_ascii=False, default=str)
    return residual_secret_hits(text, patterns)
