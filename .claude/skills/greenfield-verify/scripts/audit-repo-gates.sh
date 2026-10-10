#!/bin/bash
# Fast structural & toolchain audit for Greenfield repositories.
# Bash 3.2 compatible. Prints available toolchains, structural checks, and max reachable §8 rung.
set -euo pipefail

PROJECT_DIR="${1:-${CLAUDE_PROJECT_DIR:-$(pwd)}}"

PROJECT_DIR="$PROJECT_DIR" python3 - <<'PY'
import os
import re
import shutil
import sys
from pathlib import Path

root = Path(os.environ["PROJECT_DIR"]).resolve()
print(f"=== Greenfield Audit: {root} ===")

# 1. Toolchain inventory
tools = ["go", "node", "npm", "pnpm", "cargo", "docker", "psql", "shellcheck"]
present = [t for t in tools if shutil.which(t)]
missing = [t for t in tools if not shutil.which(t)]
print("Toolchains present:", ", ".join(present) if present else "none")
print("Toolchains absent: ", ", ".join(missing) if missing else "none")

failures = []

# 2. CLAUDE.md line-budget check (Anthropic <200 line guidance when unpacked)
claude_md = root / "CLAUDE.md"
if claude_md.is_file():
    nlines = len(claude_md.read_text(errors="ignore").splitlines())
    print(f"CLAUDE.md: {nlines} lines")
    if nlines > 250:
        failures.append(
            f"CLAUDE.md is {nlines} lines (>200 recommended ceiling); migrate procedural/reference sections into .claude/skills/ and .claude/rules/."
        )

# 3. Bash 3.2 audit across root, scripts/, and .claude/
sh_files = list(root.glob("*.sh"))
for sub in ("scripts", ".claude"):
    if (root / sub).is_dir():
        sh_files.extend((root / sub).rglob("*.sh"))

for sf in sorted(set(sh_files)):
    txt = sf.read_text(errors="ignore")
    heredoc_end = None
    for idx, line in enumerate(txt.splitlines(), 1):
        if heredoc_end is not None:
            if line.strip() == heredoc_end:
                heredoc_end = None
            continue
        hm = re.search(r"<<-?\s*['\"]?([A-Za-z0-9_]+)['\"]?\s*$", line)
        if hm:
            heredoc_end = hm.group(1)
        s = line.lstrip()
        if s.startswith("#"):
            continue
        if re.search(r"\b(declare\s+-A|mapfile|readarray)\b", s) or re.search(
            r"\$\{[A-Za-z_][A-Za-z0-9_]*,,|\$\{[A-Za-z_][A-Za-z0-9_]*\^\^", s
        ):
            failures.append(f"{sf.relative_to(root)}:{idx}: Bash 4+ syntax violates Bash 3.2 portability.")
print(f"Shell scripts audited for Bash 3.2: {len(set(sh_files))}")

# 4. Decisions register check
dec_dir = root / "docs" / "decisions"
if dec_dir.is_dir():
    decs = sorted(dec_dir.glob("[0-9][0-9][0-9][0-9]-*.md"))
    print(f"Addenda in docs/decisions/: {len(decs)}")
    for d in decs:
        txt = d.read_text(errors="ignore")
        if not txt.startswith("---\n") or "## Impact" not in txt:
            failures.append(f"{d.relative_to(root)}: missing YAML frontmatter or '## Impact' section.")

# 5. Estimate highest reachable §8 validation rung
has_db = bool(shutil.which("docker") or shutil.which("psql"))
if has_db:
    max_rung = "Rung 4–5 (Real-DB integration / E2E reachable if Postgres service is running)"
elif any(shutil.which(x) for x in ("go", "cargo", "node")):
    max_rung = "Rung 2–3 (Compiler / type-stripping / pure unit tests only — NO real Postgres detected; state caveat!)"
else:
    max_rung = "Rung 1 (Static structural checks only — state explicit caveat!)"
print("Max reachable §8 rung:", max_rung)

if failures:
    print("\nFAILURES:")
    for f in failures:
        print(" -", f)
    sys.exit(1)

print("Status: Structural audit OK")
PY
