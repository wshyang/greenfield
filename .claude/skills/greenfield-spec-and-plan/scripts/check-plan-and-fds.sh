#!/bin/bash
# Skill-scoped PostToolUse validator (and standalone CLI) for /greenfield-spec-and-plan.
# Bash 3.2 compatible. Checks edited plan docs (`docs/plans/*.md`), addenda (`docs/decisions/*.md`),
# and FDS files (`*fds*.md` / `docs/spec.md`) for:
#   - Duplicate checkbox IDs, banned vague lead verbs, and leaf checkboxes missing `done when`
#   - Mermaid / ASCII diagram blocks inside FDS documents (`D15`)
set -euo pipefail

if ! command -v python3 >/dev/null 2>&1; then
  exit 0
fi

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}"
CLI_FILE="${1:-}"
PAYLOAD=""
if [ -z "$CLI_FILE" ]; then
  PAYLOAD="$(cat)"
fi

PROJECT_DIR="$PROJECT_DIR" CLI_FILE="$CLI_FILE" PAYLOAD="$PAYLOAD" python3 - <<'PY'
import json
import os
import re
import sys
from pathlib import Path

cli_file = os.environ.get("CLI_FILE", "")
if cli_file:
    raw_path = cli_file
else:
    try:
        data = json.loads(os.environ.get("PAYLOAD", "{}"))
    except Exception:
        sys.exit(0)
    ti = data.get("tool_input") or {}
    raw_path = ti.get("file_path") or ti.get("path") or ""

if not raw_path or not raw_path.endswith(".md"):
    sys.exit(0)

root = Path(os.environ["PROJECT_DIR"]).resolve()
target = Path(raw_path)
if not target.is_absolute():
    target = (root / target).resolve()
if not target.is_file():
    sys.exit(0)

try:
    rel = target.relative_to(root).as_posix()
except ValueError:
    rel = target.as_posix()

is_plan = bool(re.search(r"(^|/)docs/(plans|decisions)/", rel) or rel.endswith("-plan.md"))
is_fds = bool(re.search(r"(?i)(fds|docs/spec\.md$)", rel))
if not (is_plan or is_fds):
    sys.exit(0)

text = target.read_text(errors="ignore")
lines = text.splitlines()
issues = []

# 1. FDS D15: no mermaid diagrams
if is_fds and re.search(r"^```mermaid\b", text, flags=re.M | re.I):
    issues.append(f"{rel}: contains a ```mermaid block, violating FDS D15 (no diagrams).")

# 2. Plan & Addendum checkbox discipline
if is_plan:
    seen_ids = set()
    banned = {"ensure", "consider", "review", "improve", "handle"}
    in_fence = False
    for idx, line in enumerate(lines):
        if line.strip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        m = re.match(r"^(\s*)- \[[ xX]\]\s+(\S+)\s+(\S+)(.*)$", line)
        if not m:
            continue
        indent, box_id, first_word, rest = m.groups()
        # Check whether next line is a deeper indented child checkbox
        has_child = False
        if idx + 1 < len(lines):
            nxt = re.match(r"^(\s*)- \[[ xX]\]\s+", lines[idx + 1])
            if nxt and len(nxt.group(1)) > len(indent):
                has_child = True

        if box_id in seen_ids:
            issues.append(f"{rel}:{idx+1}: duplicate checkbox ID '{box_id}'.")
        seen_ids.add(box_id)

        lead = re.sub(r"[^a-zA-Z]", "", first_word).lower()
        if lead in banned:
            issues.append(
                f"{rel}:{idx+1}: checkbox '{box_id}' starts with banned vague verb '{first_word}'; use a concrete imperative verb (§1.1)."
            )
        if not has_child and "done when" not in line.lower():
            issues.append(
                f"{rel}:{idx+1}: leaf checkbox '{box_id}' is missing '— done when <measurable exit criterion>' (§1.1.1)."
            )

if issues:
    msg = "Spec/Plan check flagged issue(s):\n" + "\n".join("- " + x for x in issues[:8])
    if cli_file:
        sys.stderr.write(msg + "\n")
        sys.exit(1)
    print(json.dumps({"decision": "block", "reason": msg}))
PY
