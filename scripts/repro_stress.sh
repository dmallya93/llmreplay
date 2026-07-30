#!/usr/bin/env bash
# Stress hermetic reproducibility: multi-tool chains + N-fold replay (pytest).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ -f .venv/bin/activate ]]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi

if command -v python3 >/dev/null 2>&1; then
  PY=python3
elif command -v python >/dev/null 2>&1; then
  PY=python
else
  echo "repro_stress: python not found" >&2
  exit 1
fi

export LLMREPLAY_CI="${LLMREPLAY_CI:-1}"
export LLMREPLAY_HMAC_KEY="${LLMREPLAY_HMAC_KEY:-llmreplay-repro-stress-hmac}"

echo "repro_stress: running tests/test_reproducibility.py (+ parity)"
"$PY" -m pytest -q tests/test_reproducibility.py tests/test_c9_parity.py tests/test_c1_match_store.py
echo "repro_stress ok"
