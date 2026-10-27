#!/bin/bash
# Skill-scoped PreToolUse hook for /greenfield-bootstrap.
# Blocks creating application source files under src/, internal/, cmd/, crates/, or packages/
# until docs/decisions/0001-*.md (DR-00 backend language addendum) exists on disk.
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

tool_input = data.get("tool_input") or {}
raw_path = tool_input.get("file_path") or tool_input.get("path") or ""
if not raw_path:
    sys.exit(0)

root = Path(os.environ["PROJECT_DIR"]).resolve()
target = Path(raw_path)
if not target.is_absolute():
    target = (root / target).resolve()

try:
    rel = target.relative_to(root).as_posix()
except ValueError:
    sys.exit(0)

# Only gate application code directories
if not re.match(r"^(src|internal|cmd|crates|packages)/", rel):
    sys.exit(0)

dec_dir = root / "docs" / "decisions"
has_0001 = dec_dir.is_dir() and any(dec_dir.glob("0001-*.md"))
if not has_0001:
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": (
                        f"Cannot create '{rel}' before recording DR-00 in docs/decisions/0001-*.md. "
                        "Confirm the backend language with the user and write addendum 0001 first."
                    ),
                }
            }
        )
    )
PY
