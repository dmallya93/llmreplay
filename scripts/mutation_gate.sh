#!/usr/bin/env bash
# Coverage floor on critical modules (>=95% over the full hermetic suite).
# Named historically; this is NOT full mutmut kill-rate mutation testing.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ -f .venv/bin/activate ]]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi

# Prefer python3 (macOS Actions / Homebrew); fall back to python.
if command -v python3 >/dev/null 2>&1; then
  PY=python3
elif command -v python >/dev/null 2>&1; then
  PY=python
else
  echo "mutation_gate: python3/python not found on PATH" >&2
  exit 1
fi

echo "mutation_gate: using $($PY -c 'import sys; print(sys.executable)')"

"$PY" -m pytest -q \
  --cov=llmreplay.core \
  --cov=llmreplay.scrub \
  --cov=llmreplay.store \
  --cov=llmreplay.migrate \
  --cov=llmreplay.proxy.sse \
  --cov=llmreplay.proxy.config \
  --cov=llmreplay.session \
  --cov=llmreplay.hooks.recorder \
  --cov-report=term-missing:skip-covered \
  --cov-fail-under=95
