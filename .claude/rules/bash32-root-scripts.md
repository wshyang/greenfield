---
paths:
  - "*.sh"
  - "scripts/**/*.sh"
  - ".claude/hooks/*.sh"
  - ".claude/skills/**/scripts/*.sh"
---

# Bash 3.2 Portability Rules for Repository Scripts

macOS ships `/bin/bash` pinned to **Bash 3.2** (GPLv2). Every `.sh` script at the repository root or inside `.claude/` must execute cleanly on Bash 3.2 under `set -euo pipefail`:

- **Forbidden Bash 4+ features:** `declare -A` (associative arrays), `mapfile` / `readarray`, `${var,,}` / `${var^^}` case modifiers, `|&`, `&>>`, and `globstar` (`**`).
- **Safe empty-array expansion under `set -u`:** Bash < 4.4 treats `"${arr[@]}"` on an empty array as an unbound variable error! Always expand possibly-empty arrays as `${arr[@]+"${arr[@]}"}`.
- **Lint & verify:** pass `shellcheck` (`shellcheck -s bash`) and test under Bash 3.2 or static Bash-4-construct checks in CI.
