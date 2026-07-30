#!/usr/bin/env bash
# Coverage floor on critical modules (≥95% over the full hermetic suite).
# Named historically; this is NOT full mutmut kill-rate mutation testing.
# Full mutmut can be added on self-hosted nightly runners.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
# shellcheck disable=SC1091
source .venv/bin/activate 2>/dev/null || true

python -m pytest -q \
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
