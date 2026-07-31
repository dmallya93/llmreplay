#!/usr/bin/env bash
# Render short demo GIFs with VHS (https://github.com/charmbracelet/vhs).
# Run from the repo root (or set LLMREPLAY_ROOT to the checkout path).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ -f .venv/bin/activate ]]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi

if ! command -v vhs >/dev/null 2>&1; then
  echo "vhs not found — install with: brew install vhs" >&2
  exit 1
fi

export LLMREPLAY_ROOT="$ROOT"
export LLMREPLAY_HMAC_KEY="${LLMREPLAY_HMAC_KEY:-dev-local-hmac}"
export PATH="$ROOT/.venv/bin:/opt/homebrew/bin:$PATH"

for tape in docs/assets/tapes/*.tape; do
  echo "▶ rendering $tape"
  vhs "$tape"
done

ls -lh docs/assets/*.gif
echo "done"
