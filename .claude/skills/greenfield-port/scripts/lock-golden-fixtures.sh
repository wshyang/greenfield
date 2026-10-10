#!/bin/bash
# Skill-scoped PreToolUse hook for /greenfield-port.
# Bash 3.2 compatible. Blocks manual Edit|Write on exported golden fixture files
# (`fixtures/golden/**` or `**/testdata/golden/**`) so golden expectations are only
# ever produced by running the export script against the live legacy oracle.
set -euo pipefail

if ! command -v python3 >/dev/null 2>&1; then
  exit 0
fi

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}"
PAYLOAD="$(cat)"

PROJECT_DIR="$PROJECT_DIR" PAYLOAD="$PAYLOAD" python3 - <<'PY'
import json
import os
import re
import sys
from pathlib import Path

try:
    data = json.loads(os.environ.get("PAYLOAD", "{}"))
except Exception:
    sys.exit(0)

ti = data.get("tool_input") or {}
raw_path = ti.get("file_path") or ti.get("path") or ""
if not raw_path:
    sys.exit(0)

root = Path(os.environ["PROJECT_DIR"]).resolve()
target = Path(raw_path)
if not target.is_absolute():
    target = (root / target).resolve()

try:
    rel = target.relative_to(root).as_posix()
except ValueError:
    rel = target.as_posix()

if re.search(r"(^|/)(fixtures|testdata)/golden/", rel):
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": (
                        f"Blocked manual edit/write to golden fixture '{rel}'. "
                        "Golden fixtures must be exported mechanically from the live legacy oracle via Bash, never hand-edited (§20.2 / §14.2)."
                    ),
                }
            }
        )
    )
PY
