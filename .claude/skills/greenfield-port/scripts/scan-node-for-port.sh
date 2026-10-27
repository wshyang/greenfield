#!/bin/bash
# Mechanical Node.js / TypeScript repository scanner for /greenfield-port.
# Bash 3.2 compatible. Runs bundled zero-dependency `scan-node-repo.ts` under Node 22+
# without loading scanner source code into Claude's context window.
#
# Usage:
#   scan-node-for-port.sh [repo-dir] [--target go|rust] [--format markdown|json] [--out file]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

if ! command -v node >/dev/null 2>&1; then
  echo "Error: 'node' (>=22.6) is required on PATH to run scan-node-repo.ts." >&2
  exit 1
fi

NODE_VER="$(node -p 'process.versions.node')"
NODE_MAJOR="${NODE_VER%%.*}"
NODE_REST="${NODE_VER#*.}"
NODE_MINOR="${NODE_REST%%.*}"

if [ "$NODE_MAJOR" -lt 22 ]; then
  echo "Error: Node >=22.6 required for native TypeScript execution (found v$NODE_VER)." >&2
  exit 1
fi

if [ "$NODE_MAJOR" -eq 22 ] && [ "$NODE_MINOR" -lt 18 ]; then
  exec node --experimental-strip-types "$SCRIPT_DIR/scan-node-repo.ts" ${1+"$@"}
else
  exec node "$SCRIPT_DIR/scan-node-repo.ts" ${1+"$@"}
fi
