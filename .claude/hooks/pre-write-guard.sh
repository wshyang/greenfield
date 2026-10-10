#!/bin/bash
# PreToolUse hook for Edit|Write.
# Bash 3.2 compatible. Deterministically blocks:
#   1. Direct edits to generated artifacts (*.sql.go, *_templ.go, */generated/*, openapi.json)
#   2. Creating migrations/* when DR-11 Option B (.schema-single-snapshot or db/schema.sql without migrations/) is locked,
#      or modifying already-committed SQL migrations under Option A
#   3. Writing literal credentials instead of @@SHIPHATS_<NAME>@@ placeholders in *.shiphats
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
import subprocess
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
    rel = target.as_posix()


def deny(reason: str) -> None:
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": reason,
                }
            }
        )
    )
    sys.exit(0)


# 1. Block direct edits to generated artifacts
generated_patterns = [
    r"\.sql\.go$",
    r"_templ\.go$",
    r"(^|/)generated/",
    r"(^|/)gen/.*\.(pb\.go|connect\.go|ts)$",
]
for pat in generated_patterns:
    if re.search(pat, rel):
        deny(
            f"Blocked direct write to generated file '{rel}'. Edit the source schema/SQL/template and run the generator instead (§4 / §6)."
        )

# 2. Enforce DR-11 migration discipline
if rel.startswith("migrations/") or "/migrations/" in rel:
    # Option B marker: .schema-option-b or CLAUDE.md declaring DR-11 = B
    claude_md = root / "CLAUDE.md"
    option_b = (root / ".schema-option-b").exists()
    if claude_md.exists():
        txt = claude_md.read_text(errors="ignore")
        if re.search(r"DR-11\s*[:=|]\s*B\b|Schema evolution mode:\s*Option B", txt):
            option_b = True
    if option_b:
        deny(
            f"Blocked write to '{rel}': repository is in DR-11 Option B (single snapshot + schema_state gate; migrations/ is forbidden until the exit trigger addendum lands)."
        )

    # Option A: committed SQL migrations are immutable forward-only history
    if rel.endswith(".sql") and target.exists():
        res = subprocess.run(
            ["git", "-C", str(root), "ls-files", "--error-unmatch", rel],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        if res.returncode == 0:
            deny(
                f"Blocked edit to committed migration '{rel}'. Migrations are forward-only; add a new numbered migration + update db/schema.sql in the same commit (§5)."
            )

# 3. Guard *.shiphats inert files against hardcoded tokens/passwords
if rel.endswith(".shiphats"):
    body = (tool_input.get("content") or "") + "\n" + (tool_input.get("new_string") or "")
    secret_hit = re.search(
        r"(?i)(glpat-[A-Za-z0-9_\-]{10,}|ghp_[A-Za-z0-9]{20,}|SONAR_TOKEN\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{12,}|NEXUS_IQ_PASSWORD\s*[:=]\s*['\"]?[^@\s'\"$]{6,})",
        body,
    )
    if secret_hit:
        deny(
            f"Blocked secret-like literal in inert SHIP-HATS file '{rel}'. Use @@SHIPHATS_<NAME>@@ placeholders or masked GitLab CI variables (§10.3)."
        )
PY
