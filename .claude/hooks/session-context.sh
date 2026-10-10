#!/bin/bash
# SessionStart hook (fires on startup, resume, and after context compaction).
# Bash 3.2 compatible. Re-injects active project stack, schema mode, and pending
# addendum Impact checkboxes in ~10 lines so critical state never falls out of context.
set -euo pipefail

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}"

if ! command -v python3 >/dev/null 2>&1; then
  exit 0
fi

PROJECT_DIR="$PROJECT_DIR" python3 - <<'PY'
import json
import os
import re
from pathlib import Path

root = Path(os.environ["PROJECT_DIR"])
lines = []

# 1. Detect mode: Greenfield template source repo vs unpacked application repo
if (root / "GREENFIELD.md").exists():
    lines.append(
        "Repo mode: Greenfield template source. Keep variants standalone; verify § cross-refs after edits."
    )

stacks = []
if (root / "go.mod").exists():
    stacks.append("Go (go.mod)")
if (root / "Cargo.toml").exists():
    stacks.append("Rust (Cargo.toml)")
if (root / "package.json").exists():
    stacks.append("Node/TS (package.json)")
if stacks:
    lines.append("Detected stack: " + ", ".join(stacks))

# 2. Detect schema evolution mode (Option A twin migrations vs Option B single snapshot)
has_schema = (root / "db" / "schema.sql").exists()
has_migrations = (root / "migrations").is_dir()
if has_schema and not has_migrations:
    lines.append(
        "Schema mode: DR-11 Option B (single db/schema.sql + schema_state gate; migrations/ directory forbidden)."
    )
elif has_schema and has_migrations:
    lines.append(
        "Schema mode: DR-11 Option A (update db/schema.sql + forward-only migrations/ in the same commit)."
    )

# 2b. Delegated-coding discipline (on whenever .claude/agents/gf-implementer.md exists)
if (root / ".claude" / "agents" / "gf-implementer.md").exists():
    plans = root / "docs" / "plans"
    open_plans = 0
    if plans.is_dir():
        for f in plans.glob("[0-9][0-9][0-9][0-9]-*.md"):
            if re.search(r"^\s*- \[ \] ", f.read_text(errors="ignore"), flags=re.M):
                open_plans += 1
    lines.append(
        "Delegated coding ON: main thread orchestrates only (greenfield-delegate). Code changes go "
        "gf-planner -> gf-implementer -> gf-reviewer; pass paths, never fork; subagents never ask the user. "
        f"Plans with open leaves: {open_plans}."
    )

# 3. Summarize active decisions and unchecked Impact tasks
dec_dir = root / "docs" / "decisions"
if dec_dir.is_dir():
    md_files = sorted(dec_dir.glob("[0-9][0-9][0-9][0-9]-*.md"))
    open_boxes = 0
    for f in md_files:
        txt = f.read_text(errors="ignore")
        open_boxes += len(re.findall(r"^- \[ \] ", txt, flags=re.M))
    lines.append(
        f"Decisions register: {len(md_files)} addenda in docs/decisions/ ({open_boxes} open Impact checkboxes)."
    )

lines.append(
    "Standing invariants: real-DB tests (zero repo mocks) + IDOR negative test + bite check; record non-spec choices in docs/decisions/ in the same change; state exact §8 validation rung."
)

print(
    json.dumps(
        {
            "hookSpecificOutput": {
                "hookEventName": "SessionStart",
                "additionalContext": "\n".join(lines),
            }
        }
    )
)
PY
