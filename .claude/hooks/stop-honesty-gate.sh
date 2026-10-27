#!/bin/bash
# Stop hook: runs when Claude finishes responding.
# Bash 3.2 compatible. Avoids infinite loops via `stop_hook_active`, checks whether
# schema/route edits landed without companion tests/migrations, and injects a concise
# non-error reminder only when an invariant gap is visible in `git status`.
set -euo pipefail

if ! command -v python3 >/dev/null 2>&1; then
  exit 0
fi

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}"
PAYLOAD="$(cat)"

PROJECT_DIR="$PROJECT_DIR" PAYLOAD="$PAYLOAD" python3 - <<'PY'
import json
import os
import subprocess
import sys
from pathlib import Path

try:
    data = json.loads(os.environ.get("PAYLOAD", "{}"))
except Exception:
    sys.exit(0)

# Prevent infinite Stop continuation loops
if data.get("stop_hook_active"):
    sys.exit(0)

root = Path(os.environ["PROJECT_DIR"]).resolve()
res = subprocess.run(
    ["git", "-C", str(root), "status", "--porcelain", "-uall"],
    capture_output=True,
    text=True,
)
if res.returncode != 0 or not res.stdout.strip():
    sys.exit(0)

changed = []
for ln in res.stdout.splitlines():
    if len(ln) > 3:
        changed.append(ln[3:].strip().strip('"'))

warnings = []

# Check Option A twin schema parity: migration added without db/schema.sql (or vice versa)
if (root / "migrations").is_dir() and (root / "db" / "schema.sql").exists():
    touched_mig = any(p.startswith("migrations/") and p.endswith(".sql") for p in changed)
    touched_snap = "db/schema.sql" in changed
    if touched_mig and not touched_snap:
        warnings.append(
            "A file under migrations/ changed without updating db/schema.sql in the same change (§5 Option A twin-file rule)."
        )

# Check route/handler edits without any test file touched
code_routes = [
    p for p in changed
    if any(tok in p for tok in ("handlers", "routes", "router"))
    and p.endswith((".go", ".ts", ".rs"))
    and not p.endswith(("_test.go", ".test.ts", ".spec.ts"))
]
tests_touched = any(
    p.endswith(("_test.go", ".test.ts", ".spec.ts", ".test.tsx"))
    or p.startswith(("tests/", "e2e/"))
    for p in changed
)
if code_routes and not tests_touched:
    warnings.append(
        f"Route/handler file(s) changed ({', '.join(code_routes[:3])}) with no test file modified — remember positive + IDOR negative real-DB tests and the bite check (§2)."
    )

if warnings:
    msg = (
        "Greenfield pre-stop check:\n- "
        + "\n- ".join(warnings)
        + "\nAlso confirm your response states the exact §8 validation rung actually executed."
    )
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "Stop",
                    "additionalContext": msg,
                }
            }
        )
    )
PY
