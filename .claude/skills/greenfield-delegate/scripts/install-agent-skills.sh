#!/bin/bash
# install-agent-skills.sh — greenfield-delegate toolchain installer (run by greenfield-bootstrap Step 2b).
# Bash 3.2 compatible (see .claude/rules/bash32-root-scripts.md).
#
# Installs into the CURRENT repository (git top level):
#   1. ECC (affaan-m/ECC, MIT): only the chosen language pack, copied flat from a
#      pinned commit. The skills go to .claude/skills/, plus the build/review agents
#      and commands. This is the "hybrid" mode: ECC's own installer pulls a 500+ file
#      baseline, and the full plugin lists 314 skills in the main thread.
#   2. GitNexus (abhigyanpatwari/GitNexus): `npx gitnexus@<pin> analyze --skip-agents-md --no-stats`
#      builds the .gitnexus/ index (self-gitignored) and installs the standard
#      gitnexus-* skills into .claude/skills/. It leaves the lean CLAUDE.md untouched.
#      The GitNexus MCP server is NOT added to .mcp.json. The gf-* agents declare it
#      inline (`mcpServers:`), so its tool descriptions never enter the main thread.
#   3. modularity (vladikk/modularity): declared as a project-scope plugin in
#      .claude/settings.json (extraKnownMarketplaces + enabledPlugins). It is also
#      installed with `claude plugin install --scope project` when the claude CLI is on PATH.
#   4. Checks the static .claude/agents/gf-{planner,implementer,reviewer}.md shipped with
#      .claude/ (language-agnostic: they list every language pack, and Claude Code
#      skips preloads that are not installed). Re-pins their gitnexus@<version> to
#      GITNEXUS_VERSION and lints them with lint-agents.py. Sets
#      env.CLAUDE_CODE_FORK_SUBAGENT=0 so Claude waits for each stage and never forks.
#   5. Writes .claude/agent-skills.lock and gitignores .claude/main-edit.allow.
#
# Usage:
#   install-agent-skills.sh <go|node|rust> [--force] [--skip-index]
#   install-agent-skills.sh <go|node|rust> --check   # verify only; exit 1 on any gap
#   install-agent-skills.sh rust --frontend react   # force the React pack (or: none | auto, default auto)
#
# Frontend pack (automatic). Every Greenfield backend may ship a React frontend
# (DR-05 = A: React + Vite in frontend/ for Go and Rust; Node's component/hook rules
# assume React). When it does, the ECC React pack is vendored alongside the backend pack:
# react-patterns, react-testing, vite-patterns, react-reviewer, react-build-resolver,
# /react-build, /react-review, /react-test (+ typescript-patterns and typescript-reviewer
# for Go/Rust). Detection order: --frontend flag > the DR-05 record in docs/decisions/
# (frontmatter `choice:`, else its H1 title) > a react/next dependency in any package.json
# (depth <= 3) > the documented default (react). --check reuses the locked value.
#
# Pins (override via env): ECC_REF, GITNEXUS_VERSION.
set -euo pipefail

ECC_REPO="${ECC_REPO:-https://github.com/affaan-m/ECC.git}"
ECC_REF="${ECC_REF:-b38be6a7f6350964d59328b52f0624e1d1d552d1}"   # ECC v2.2.3 line, 2026-10-29
GITNEXUS_VERSION="${GITNEXUS_VERSION:-1.6.12}"
MOD_MARKETPLACE="vladikk-modularity"
MOD_REPO="vladikk/modularity"
MOD_PLUGIN="modularity@vladikk-modularity"

LANG_ARG="${1:-}"
shift || true
MODE="install"; FORCE=0; SKIP_INDEX=0; FRONTEND_ARG="auto"
while [ $# -gt 0 ]; do
  case "$1" in
    --check) MODE="check" ;;
    --force) FORCE=1 ;;
    --skip-index) SKIP_INDEX=1 ;;
    --frontend) shift; FRONTEND_ARG="${1:-}" ;;
    --frontend=*) FRONTEND_ARG="${1#--frontend=}" ;;
    *) echo "unknown option: $1" >&2; exit 2 ;;
  esac
  shift
done

# ---- language table (no associative arrays: Bash 3.2) -------------------------
case "$LANG_ARG" in
  rust)
    LANG_LABEL="Rust"
    ECC_SKILLS="rust-patterns rust-testing coding-standards"
    ECC_AGENTS="rust-build-resolver rust-reviewer"
    ECC_COMMANDS="rust-build rust-review" ;;
  go)
    LANG_LABEL="Go"
    ECC_SKILLS="golang-patterns golang-testing coding-standards"
    ECC_AGENTS="go-build-resolver go-reviewer"
    ECC_COMMANDS="go-build go-review" ;;
  node)
    LANG_LABEL="Node.js + TypeScript"
    ECC_SKILLS="typescript-patterns backend-patterns coding-standards"
    ECC_AGENTS="build-error-resolver typescript-reviewer"
    ECC_COMMANDS="build-fix" ;;
  *)
    echo "usage: $0 <go|node|rust> [--check|--force|--skip-index] [--frontend react|none|auto]" >&2; exit 2 ;;
esac
case "$FRONTEND_ARG" in
  react|none|auto) ;;
  *) echo "--frontend must be react, none or auto (got: '$FRONTEND_ARG')" >&2; exit 2 ;;
esac
GITNEXUS_SKILLS="gitnexus-impact-analysis gitnexus-exploring gitnexus-debugging gitnexus-refactoring gitnexus-guide gitnexus-cli"
GF_AGENTS="gf-planner gf-implementer gf-reviewer"

DELEGATE_DIR="$(cd "$(dirname "$0")/.." && pwd)"
ROOT="${CLAUDE_PROJECT_DIR:-}"
if [ -z "$ROOT" ]; then ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"; fi
cd "$ROOT"
LINT="$DELEGATE_DIR/scripts/lint-agents.py"

# ---- frontend detection (Bash 3.2: no associative arrays, no mapfile) -----------
# Prints "<react|none> <source>".
classify_choice() {  # $1 = free text naming the chosen option
  if printf '%s' "$1" | grep -qiE 'react|next\.?js|vite'; then echo react; else echo none; fi
}
detect_frontend() {
  local rec choice pj
  rec="$(grep -lE '^decision:[[:space:]]*DR-05([^0-9]|$)' docs/decisions/*.md 2>/dev/null | head -1 || true)"
  if [ -n "$rec" ]; then
    choice="$(sed -n '1,/^---$/{/^choice:/p;}' "$rec" | head -1 | sed 's/^choice:[[:space:]]*//' || true)"
    [ -z "$choice" ] && choice="$(awk 'NR>1 && /^---$/ {f=1; next} f && /^# / {sub(/^# /,""); print; exit}' "$rec" || true)"
    if [ -n "$choice" ]; then echo "$(classify_choice "$choice") DR-05:$rec"; return; fi
  fi
  pj="$(find . -maxdepth 3 -name package.json -not -path '*/node_modules/*' \
        -exec grep -lE '"(react|next)"[[:space:]]*:' {} + 2>/dev/null | head -1 || true)"
  if [ -n "$pj" ]; then echo "react package.json:$pj"; return; fi
  echo "react default(DR-05=A)"
}
LOCKED_FRONTEND="$(sed -n 's/^frontend=//p' .claude/agent-skills.lock 2>/dev/null | head -1 || true)"
if [ "$FRONTEND_ARG" != "auto" ]; then
  FRONTEND="$FRONTEND_ARG"; FRONTEND_SOURCE="flag"
elif [ "$MODE" = "check" ] && [ -n "$LOCKED_FRONTEND" ]; then
  FRONTEND="$LOCKED_FRONTEND"; FRONTEND_SOURCE="lock"
else
  read -r FRONTEND FRONTEND_SOURCE <<EOF
$(detect_frontend)
EOF
fi
FE_SKILLS=""; FE_AGENTS=""; FE_COMMANDS=""
if [ "$FRONTEND" = "react" ]; then
  FE_SKILLS="react-patterns react-testing vite-patterns"
  FE_AGENTS="react-reviewer react-build-resolver"
  FE_COMMANDS="react-build react-review react-test"
  if [ "$LANG_ARG" != "node" ]; then   # /react-review also runs typescript-reviewer on TSX
    FE_SKILLS="typescript-patterns $FE_SKILLS"; FE_AGENTS="$FE_AGENTS typescript-reviewer"
  fi
fi
BACKEND_SKILLS="$ECC_SKILLS"
ECC_SKILLS="$ECC_SKILLS${FE_SKILLS:+ $FE_SKILLS}"
ECC_AGENTS="$ECC_AGENTS${FE_AGENTS:+ $FE_AGENTS}"
ECC_COMMANDS="$ECC_COMMANDS${FE_COMMANDS:+ $FE_COMMANDS}"

# ---- check mode ----------------------------------------------------------------
check() {
  local gaps=0 x
  for x in $ECC_SKILLS; do
    [ -f ".claude/skills/$x/SKILL.md" ] || { echo "MISSING skill: .claude/skills/$x/SKILL.md"; gaps=$((gaps+1)); }
  done
  for x in $GITNEXUS_SKILLS; do
    if [ ! -f ".claude/skills/$x/SKILL.md" ]; then
      if [ "$SKIP_INDEX" -eq 1 ]; then echo "PENDING skill (installed by gitnexus analyze): .claude/skills/$x/SKILL.md"
      else echo "MISSING skill: .claude/skills/$x/SKILL.md"; gaps=$((gaps+1)); fi
    fi
  done
  [ -f ".claude/skills/greenfield-delegate/SKILL.md" ] || { echo "MISSING skill: .claude/skills/greenfield-delegate/SKILL.md (never prune it)"; gaps=$((gaps+1)); }
  for x in $ECC_AGENTS $GF_AGENTS; do
    [ -f ".claude/agents/$x.md" ] || { echo "MISSING agent: .claude/agents/$x.md"; gaps=$((gaps+1)); }
  done
  for x in $ECC_COMMANDS; do
    [ -f ".claude/commands/$x.md" ] || { echo "MISSING command: .claude/commands/$x.md"; gaps=$((gaps+1)); }
  done
  if command -v python3 >/dev/null 2>&1; then
    python3 "$LINT" .claude/agents --gitnexus-version "$GITNEXUS_VERSION" | grep -v '^lint-agents:' || true
    python3 "$LINT" .claude/agents --gitnexus-version "$GITNEXUS_VERSION" >/dev/null || gaps=$((gaps+1))
  else
    echo "NOTE: python3 missing; agent frontmatter lint skipped"
  fi
  node -e '
    const fs=require("fs"); let g=0;
    const rd=f=>{try{return JSON.parse(fs.readFileSync(f,"utf8"))}catch(e){return null}};
    const s=rd(".claude/settings.json")||{};
    if(!(s.enabledPlugins||{})[process.argv[1]]){console.log("MISSING enabledPlugins."+process.argv[1]+" in .claude/settings.json");g++}
    const pre=JSON.stringify((s.hooks||{}).PreToolUse||[]);
    if(!pre.includes("main-thread-code-guard.sh")){console.log("MISSING PreToolUse main-thread-code-guard.sh in .claude/settings.json");g++}
    if((s.env||{}).CLAUDE_CODE_FORK_SUBAGENT!=="0"){console.log("MISSING env.CLAUDE_CODE_FORK_SUBAGENT=\"0\" in .claude/settings.json (fork mode would bypass the pipeline)");g++}
    process.exit(g?1:0);' "$MOD_PLUGIN" || gaps=$((gaps+1))
  [ -x ".claude/hooks/main-thread-code-guard.sh" ] || { echo "MISSING executable .claude/hooks/main-thread-code-guard.sh"; gaps=$((gaps+1)); }
  [ -d ".gitnexus" ] || echo "NOTE: no .gitnexus/ index yet (run: npx gitnexus@$GITNEXUS_VERSION analyze --skip-agents-md --no-stats)"
  [ -f ".claude/agent-skills.lock" ] || { echo "MISSING .claude/agent-skills.lock"; gaps=$((gaps+1)); }
  if [ "$MODE" = "check" ] && [ "$FRONTEND_ARG" = "auto" ] && [ -n "$LOCKED_FRONTEND" ]; then
    local now; now="$(detect_frontend)"
    [ "${now%% *}" = "$LOCKED_FRONTEND" ] || echo "NOTE: locked frontend=$LOCKED_FRONTEND but detection now says ${now%% *} (${now#* }); re-run without --check to update"
  fi
  if [ "$gaps" -gt 0 ]; then echo "agent-skills check: $gaps gap(s)"; return 1; fi
  echo "agent-skills check: OK ($LANG_ARG, frontend=$FRONTEND)"
}
if [ "$MODE" = "check" ]; then check; exit $?; fi

command -v git >/dev/null 2>&1 || { echo "git is required" >&2; exit 1; }
command -v node >/dev/null 2>&1 || { echo "node (>= 20) is required for GitNexus and JSON merges" >&2; exit 1; }
mkdir -p .claude/skills .claude/agents .claude/commands .claude/vendor

# ---- 1. ECC language pack (sparse fetch of a pinned commit) --------------------
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
SPARSE="/LICENSE"
for x in $ECC_SKILLS; do SPARSE="$SPARSE /skills/$x/"; done
for x in $ECC_AGENTS; do SPARSE="$SPARSE /agents/$x.md"; done
for x in $ECC_COMMANDS; do SPARSE="$SPARSE /commands/$x.md"; done
(
  cd "$TMP"
  git init -q ecc && cd ecc
  git remote add origin "$ECC_REPO"
  git config core.sparseCheckout true
  # shellcheck disable=SC2086
  git sparse-checkout set --no-cone $SPARSE
  git fetch -q --depth 1 --filter=blob:none origin "$ECC_REF"
  git checkout -q FETCH_HEAD
)
SRC="$TMP/ecc"

copy_one() {  # copy_one <src> <dest>
  if [ -e "$2" ] && [ "$FORCE" -ne 1 ] && ! diff -rq "$1" "$2" >/dev/null 2>&1; then
    echo "CONFLICT: $2 exists and differs from ECC@${ECC_REF:0:7} (re-run with --force to overwrite)" >&2
    return 1
  fi
  rm -rf "$2"; cp -R "$1" "$2"
}
for x in $ECC_SKILLS; do copy_one "$SRC/skills/$x" ".claude/skills/$x"; done
for x in $ECC_AGENTS; do copy_one "$SRC/agents/$x.md" ".claude/agents/$x.md"; done
for x in $ECC_COMMANDS; do copy_one "$SRC/commands/$x.md" ".claude/commands/$x.md"; done
cp "$SRC/LICENSE" .claude/vendor/ECC-LICENSE
echo "ECC ($LANG_LABEL, frontend=$FRONTEND via $FRONTEND_SOURCE): vendored [$ECC_SKILLS] + agents [$ECC_AGENTS] + commands [$ECC_COMMANDS] @ ${ECC_REF:0:7}"
if [ "$FRONTEND" = "none" ] && [ -d .claude/skills/react-patterns ]; then
  echo "NOTE: frontend=none but an earlier React pack is still vendored; remove .claude/skills/{react-patterns,react-testing,vite-patterns}, .claude/agents/react-*.md and .claude/commands/react-*.md if the frontend really went away"
fi

# ---- 2. GitNexus index + skills ------------------------------------------------
if [ "$SKIP_INDEX" -eq 1 ]; then
  echo "GitNexus: --skip-index given; run later: npx -y gitnexus@$GITNEXUS_VERSION analyze --skip-agents-md --no-stats"
else
  npx -y "gitnexus@$GITNEXUS_VERSION" analyze --skip-agents-md --no-stats
fi

# ---- 3. settings.json merge (idempotent) ---------------------------------------
node - "$MOD_MARKETPLACE" "$MOD_REPO" "$MOD_PLUGIN" <<'JS'
const fs = require("fs");
const [mkt, repo, plugin] = process.argv.slice(2);
const read = (f, d) => { try { return JSON.parse(fs.readFileSync(f, "utf8")); } catch (e) { return d; } };
const write = (f, o) => fs.writeFileSync(f, JSON.stringify(o, null, 2) + "\n");

const s = read(".claude/settings.json", {});
s.extraKnownMarketplaces = s.extraKnownMarketplaces || {};
s.extraKnownMarketplaces[mkt] = { source: { source: "github", repo } };
s.enabledPlugins = s.enabledPlugins || {};
s.enabledPlugins[plugin] = true;
s.env = s.env || {};
s.env.CLAUDE_CODE_FORK_SUBAGENT = "0";
s.hooks = s.hooks || {};
s.hooks.PreToolUse = s.hooks.PreToolUse || [];
if (!JSON.stringify(s.hooks.PreToolUse).includes("main-thread-code-guard.sh")) {
  s.hooks.PreToolUse.unshift({
    matcher: "Edit|Write|MultiEdit|NotebookEdit",
    hooks: [{ type: "command", command: "\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/main-thread-code-guard.sh", timeout: 10 }],
  });
}
write(".claude/settings.json", s);
JS
if command -v claude >/dev/null 2>&1; then
  claude plugin install "$MOD_PLUGIN" --marketplace "$MOD_REPO" --scope project \
    || echo "modularity: CLI install failed; Claude Code will offer it from .claude/settings.json on trust."
else
  echo "modularity: declared in .claude/settings.json; Claude Code offers the install when the project is trusted (or run /plugin install $MOD_PLUGIN)."
fi

# ---- 4. Pipeline agents: present, pinned, linted --------------------------------
for a in $GF_AGENTS; do
  [ -f ".claude/agents/$a.md" ] || cp "$DELEGATE_DIR/../../agents/$a.md" ".claude/agents/$a.md" 2>/dev/null \
    || { echo "MISSING .claude/agents/$a.md (copy sidequest/.claude/agents/ into the repo)" >&2; exit 1; }
  GNV="$GITNEXUS_VERSION" node -e '
    const fs = require("fs"); const f = process.argv[1];
    const t = fs.readFileSync(f, "utf8");
    const u = t.replace(/gitnexus@[0-9][^\s"'"'"'\]]*/g, "gitnexus@" + process.env.GNV);
    if (u !== t) fs.writeFileSync(f, u);' ".claude/agents/$a.md"
done
chmod +x .claude/hooks/main-thread-code-guard.sh 2>/dev/null || true
echo "Agents: [$GF_AGENTS] present, gitnexus pinned to $GITNEXUS_VERSION, fork mode off (CLAUDE_CODE_FORK_SUBAGENT=0)"

# ---- 5. Lock + gitignore -------------------------------------------------------
{
  echo "# Generated by greenfield-delegate/scripts/install-agent-skills.sh; re-run to update."
  echo "lang=$LANG_ARG"
  echo "frontend=$FRONTEND"
  echo "frontend_source=$FRONTEND_SOURCE"
  echo "backend_skills=$BACKEND_SKILLS"
  echo "ecc_repo=$ECC_REPO"
  echo "ecc_ref=$ECC_REF"
  echo "ecc_skills=$ECC_SKILLS"
  echo "ecc_agents=$ECC_AGENTS"
  echo "ecc_commands=$ECC_COMMANDS"
  echo "gitnexus_version=$GITNEXUS_VERSION"
  echo "gitnexus_skills=$GITNEXUS_SKILLS"
  echo "modularity_plugin=$MOD_PLUGIN"
  echo "modularity_marketplace=github:$MOD_REPO"
  echo "pipeline_agents=$GF_AGENTS"
  echo "gitnexus_mcp=inline in .claude/agents/gf-*.md (not .mcp.json)"
} > .claude/agent-skills.lock
touch .gitignore
grep -qxF ".claude/main-edit.allow" .gitignore || echo ".claude/main-edit.allow" >> .gitignore
grep -qxF ".claude/settings.local.json" .gitignore || echo ".claude/settings.local.json" >> .gitignore

check
