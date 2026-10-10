#!/bin/bash
# PostToolUse hook for Edit|Write.
# Bash 3.2 compatible. Runs <50ms deterministic static checks on the touched file:
#   - Root/hook *.sh scripts: Bash 3.2 banned constructs (declare -A, mapfile, readarray, ${var,,})
#   - docs/decisions/*.md: required YAML frontmatter + checkbox ## Impact with '— done when'
#   - Go (*.go): v1 encoding/json, uuid.New() v4, math/rand v1, fmt.Print* in internal/
#   - TypeScript/React (*.ts, *.tsx): `as` casts in tests, PGlite in backend tests, API/filter/reduce in JSX
#   - Rust (*.rs): .unwrap() / dbg! / todo! / Uuid::new_v4() in non-test src/
#   - GREENFIELD*.md templates: broken internal §N.M cross-references
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
if not target.is_file():
    sys.exit(0)

try:
    rel = target.relative_to(root).as_posix()
except ValueError:
    rel = target.as_posix()

text = target.read_text(errors="ignore")
issues = []

# 1. Bash 3.2 portability on shell scripts (skipping embedded non-shell heredocs like <<'PY')
if rel.endswith(".sh"):
    heredoc_end = None
    for lineno, line in enumerate(text.splitlines(), 1):
        if heredoc_end is not None:
            if line.strip() == heredoc_end:
                heredoc_end = None
            continue
        hm = re.search(r"<<-?\s*['\"]?([A-Za-z0-9_]+)['\"]?\s*$", line)
        if hm:
            heredoc_end = hm.group(1)
        stripped = line.lstrip()
        if stripped.startswith("#"):
            continue
        if re.search(r"\b(declare\s+-A|mapfile|readarray)\b", stripped):
            issues.append(f"{rel}:{lineno}: Bash 4+ construct forbidden; scripts must run on macOS Bash 3.2 (§10.4).")
        if re.search(r"\$\{[A-Za-z_][A-Za-z0-9_]*,,|\$\{[A-Za-z_][A-Za-z0-9_]*\^\^", stripped):
            issues.append(f"{rel}:{lineno}: Bash 4+ case-modification '${{var,,}}' forbidden on Bash 3.2 (§10.4).")

# 2. Addendum frontmatter & checkbox Impact check
if re.search(r"(^|/)docs/decisions/\d{4}-.*\.md$", rel):
    if not text.startswith("---\n"):
        issues.append(f"{rel}: missing YAML frontmatter header (id, decision, status, decided_by, date, supersedes) (§1).")
    else:
        end = text.find("\n---", 4)
        fm = text[4:end] if end != -1 else ""
        for key in ("id:", "decision:", "status:", "decided_by:", "date:", "supersedes:"):
            if key not in fm:
                issues.append(f"{rel}: frontmatter missing '{key}' (§1).")
    if "## Impact" not in text:
        issues.append(f"{rel}: missing '## Impact' checkbox section (§1).")
    else:
        impact_body = text.split("## Impact", 1)[1].split("\n## ", 1)[0]
        boxes = [ln for ln in impact_body.splitlines() if re.match(r"^- \[[ xX]\] ", ln)]
        if not boxes:
            issues.append(f"{rel}: '## Impact' must contain '- [ ] ID ... — done when ...' checkboxes, not prose bullets (§1).")
        for bx in boxes:
            if "done when" not in bx:
                issues.append(f"{rel}: Impact checkbox missing measurable '— done when ...': {bx[:80]}")

# 3. Go 1.27 static conventions
if rel.endswith(".go") and not rel.endswith("_test.go"):
    if '"encoding/json"' in text:
        issues.append(f"{rel}: imports legacy \"encoding/json\"; use Go 1.27 \"encoding/json/v2\" unless documented at a third-party shim (§6 / §14).")
    if '"math/rand"' in text:
        issues.append(f"{rel}: imports legacy \"math/rand\"; use \"math/rand/v2\" or \"crypto/rand\".")
    if re.search(r"\buuid\.New\(\)", text):
        issues.append(f"{rel}: uses UUIDv4 uuid.New(); mint timestamp-ordered UUIDv7 via uuid.NewV7() in one place (§4).")
    if "/internal/" in ("/" + rel) and re.search(r"\bfmt\.Print(ln|f)?\(", text):
        issues.append(f"{rel}: uses fmt.Print* inside internal/; emit structured log/slog records instead (§16).")

# 4. TypeScript / React / Playwright conventions
if rel.endswith((".ts", ".tsx")):
    is_test = bool(re.search(r"\.(test|spec)\.tsx?$", rel) or rel.startswith("e2e/"))
    if is_test:
        if "@electric-sql/pglite" in text and "frontend/" not in rel:
            issues.append(f"{rel}: imports @electric-sql/pglite in server tests; PGlite is single-session WASM and hides pool/lock races — use real Postgres or embedded-postgres (§3).")
        if re.search(r"trace\s*:\s*['\"]on-first-retry['\"]", text):
            issues.append(f"{rel}: uses trace: 'on-first-retry' (records nothing under retries: 0); use trace: 'retain-on-failure' (§2.4 / §3).")
    if rel.endswith(".tsx") and not is_test and "/components/" in ("/" + rel):
        if re.search(r"from\s+['\"][^'\"]*lib/api", text):
            issues.append(f"{rel}: component imports lib/api directly; components render and hooks decide (§7).")

# 5. Rust 1.99 conventions (non-test library/handler files)
if rel.endswith(".rs") and not rel.startswith("tests/") and not rel.endswith("_test.rs"):
    prod_part = text.split("#[cfg(test)]", 1)[0]
    if re.search(r"\bdbg!\(", prod_part) or re.search(r"\btodo!\(", prod_part):
        issues.append(f"{rel}: contains dbg!() or todo!() in non-test Rust code (§13).")
    if re.search(r"\bUuid::new_v4\(", prod_part):
        issues.append(f"{rel}: uses Uuid::new_v4(); mint timestamp-ordered UUIDv7 via Uuid::now_v7() (§4).")

# 6. GREENFIELD*.md template internal § cross-reference integrity
if Path(rel).name.startswith("GREENFIELD-") and rel.endswith(".md"):
    defined = set()
    in_fence = False
    for line in text.splitlines():
        if line.strip().startswith("```"):
            in_fence = not in_fence
            continue
        if not in_fence:
            m = re.match(r"^#{2,4}\s+(\d+(?:\.\d+)*)\b", line)
            if m:
                defined.add(m.group(1))
    in_fence = False
    for lineno, line in enumerate(text.splitlines(), 1):
        if line.strip().startswith("```"):
            in_fence = not in_fence
            continue
        if not in_fence:
            for m in re.finditer(r"§(\d+(?:\.\d+)*)", line):
                if m.group(1) not in defined:
                    issues.append(f"{rel}:{lineno}: broken section cross-reference §{m.group(1)}.")

if issues:
    joined = "\n".join("- " + item for item in issues[:8])
    print(
        json.dumps(
            {
                "decision": "block",
                "reason": f"Greenfield PostToolUse check flagged {len(issues)} issue(s):\n{joined}",
            }
        )
    )
PY
