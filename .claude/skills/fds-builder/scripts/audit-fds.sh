#!/bin/bash
# Deterministic FDS static auditor & PostToolUse validator for /fds-builder.
# Bash 3.2 compatible. Delegates to zero-dependency Python 3 implementation (`audit_fds.py`)
# so zero script source tokens are loaded into Claude's context window.
#
# Modes:
#   1. PostToolUse hook (0 CLI args, JSON on stdin): <40ms D1/D7/D15/D16 invariant guard
#   2. CLI gate: audit-fds.sh <spec.md> --phase intake|scaffold|deep-dive-plan|r5-parity|review|finalize [--ledger <json>] [--json]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

if ! command -v python3 >/dev/null 2>&1; then
  exit 0
fi

exec python3 "$SCRIPT_DIR/audit_fds.py" ${1+"$@"}
