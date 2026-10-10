#!/bin/bash
# Compaction-resilient session state ledger & Decision Context manager for /fds-builder.
# Bash 3.2 compatible. Delegates to zero-dependency Python 3 implementation (`fds_state.py`)
# so zero script source tokens are loaded into Claude's context window.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

if ! command -v python3 >/dev/null 2>&1; then
  echo "Error: 'python3' is required on PATH to run fds-state.sh." >&2
  exit 1
fi

exec python3 "$SCRIPT_DIR/fds_state.py" ${1+"$@"}
