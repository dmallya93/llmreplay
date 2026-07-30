#!/usr/bin/env bash
# Clean-venv release smoke: install → help → doctor → offline replay fixture.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
SMOKE_VENV="${TMPDIR:-/tmp}/llmreplay-release-smoke-venv"
rm -rf "$SMOKE_VENV"
python3 -m venv "$SMOKE_VENV"
# shellcheck disable=SC1091
source "$SMOKE_VENV/bin/activate"
python -m pip install -U pip -q
pip install -e ".[dev]" -q
llmreplay --help >/dev/null
llmreplay version
llmreplay doctor --json >/dev/null
llmreplay exit-codes >/dev/null

FIXTURE="$ROOT/fixtures/release/offline"
llmreplay replay --check --cassette "$FIXTURE"
llmreplay validate --cassette "$FIXTURE" >/dev/null
echo "release_smoke ok"
