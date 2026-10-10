#!/bin/bash
# PreToolUse hook for Edit|Write|MultiEdit|NotebookEdit.
# Bash 3.2 compatible. Enforces the delegated-coding discipline
# (.claude/skills/greenfield-delegate/SKILL.md):
#
#   * The MAIN THREAD never edits code. Hook payloads carry `agent_id` only when
#     the call comes from a subagent, so a payload without `agent_id` is the main
#     thread.
#   * The planner (gf-planner) and reviewer (gf-reviewer) subagents never edit code
#     either. They write only docs/plans/ and docs/reviews/.
#   * Code edits are allowed only from gf-implementer, or from another named
#     subagent the orchestrator spawned (e.g. ECC's *-build-resolver).
#
# Armed whenever .claude/agents/gf-implementer.md exists. It ships in sidequest/.claude/agents/,
# so a seeded repo is guarded from its first session. It is inert in a repo without the agents.
# Emergency override: create .claude/main-edit.allow (gitignored). The hook then
# allows the edit and the agent must say so in its reply.
set -euo pipefail

if ! command -v python3 >/dev/null 2>&1; then
  exit 0
fi

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}"
PAYLOAD="$(cat)"

PROJECT_DIR="$PROJECT_DIR" PAYLOAD="$PAYLOAD" python3 - <<'PY'
import json
import os
import sys
from pathlib import Path

try:
    data = json.loads(os.environ.get("PAYLOAD", "{}"))
except Exception:
    sys.exit(0)

root = Path(os.environ["PROJECT_DIR"]).resolve()
if not (root / ".claude/agents/gf-implementer.md").is_file():
    sys.exit(0)  # pipeline not installed: inert

tool_input = data.get("tool_input") or {}
raw_path = tool_input.get("file_path") or tool_input.get("notebook_path") or tool_input.get("path") or ""
if not raw_path:
    sys.exit(0)

target = Path(raw_path)
if not target.is_absolute():
    target = (root / target).resolve()
try:
    rel = target.relative_to(root).as_posix()
except ValueError:
    sys.exit(0)  # outside the repo: not ours to police

CODE_DIRS = (
    "src/", "internal/", "cmd/", "crates/", "packages/", "apps/", "bins/",
    "web/", "frontend/", "tests/", "test/", "e2e/", "migrations/", "db/",
    "pkg/", "lib/", "benches/", "examples/",
)
CODE_FILES = {
    "Cargo.toml", "Cargo.lock", "go.mod", "go.sum", "package.json",
    "package-lock.json", "pnpm-lock.yaml", "yarn.lock", "tsconfig.json",
    "build.rs", "Makefile", "justfile", ".dockerignore",
}
is_code = rel.startswith(CODE_DIRS) or rel in CODE_FILES or rel.startswith("Dockerfile")
if not is_code:
    sys.exit(0)  # docs/, CLAUDE.md, .claude/, plans and reviews stay editable

if (root / ".claude/main-edit.allow").exists():
    print("main-thread-code-guard: override file .claude/main-edit.allow present; "
          "edit to %s allowed. State this override in your reply." % rel, file=sys.stderr)
    sys.exit(0)

agent_id = data.get("agent_id")
agent_type = (data.get("agent_type") or "").strip().lower()


def deny(reason):
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": reason,
    }}))
    sys.exit(0)


if not agent_id:
    deny(
        "Delegated-coding discipline: the main thread never edits code (%s). "
        "Run the pipeline from greenfield-delegate instead: spawn gf-planner, which "
        "writes docs/plans/NNNN-*.md, then gf-implementer with that plan path, then "
        "gf-reviewer on the diff. Pass file paths, not contents. Never use "
        "subagent_type 'fork'." % rel
    )
if agent_type in ("gf-planner", "gf-reviewer"):
    deny(
        "%s is read-only for code (%s). Planner writes docs/plans/, reviewer writes "
        "docs/reviews/. Return the finding to the orchestrator; gf-implementer makes "
        "code changes." % (agent_type, rel)
    )
sys.exit(0)
PY
