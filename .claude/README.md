# `sidequest/.claude` — Modular Greenfield Skills, Path-Scoped Rules & Hooks

This directory converts the monolithic `GREENFIELD-{GO,NODE,RUST}.md` standing-instruction templates (`1,200–3,700` lines / `15k–45k` tokens per turn) into a **progressive-disclosure Claude Code `.claude/` architecture** that cuts idle context usage by **~96%** while making hard invariants deterministic via hooks.

## Why 4 Layers Instead of One Giant `CLAUDE.md` or One Giant `SKILL.md`

1. **Monolithic `CLAUDE.md` (`~45k` tokens)** consumes ~22% of a 200k context window before Turn 1 and triggers *lost-in-the-middle* instruction drop-off.
2. **Monolithic `SKILL.md` (`~45k` tokens)** hits Claude Code's **5,000-token per-skill post-compaction re-injection cap** (`code.claude.com/docs/en/context-window`), truncating ~89% of the file on the first `/compact`.
3. **This `.claude/` layout splits `GREENFIELD-<lang>` by lifecycle:**
   - **Lean `CLAUDE.md` (`<= 130` lines, unpacked from `skills/greenfield-bootstrap/assets/CLAUDE.lean-template.md`)** — `~1,200` tokens, 100% re-injected from disk after compaction.
   - **Path-scoped `.claude/rules/*.md` (`0` tokens at startup)** — auto-loaded only when touching SQL/migrations, `.tsx`/Playwright, `Dockerfile*`/`*.shiphats`, or `.sh` scripts.
   - **7 Progressive-Disclosure Skills (`.claude/skills/*/SKILL.md`, each `< 220` lines)** — `greenfield-bootstrap` and `greenfield-port` set `disable-model-invocation: true` (`0` startup tokens); `fds-builder`, `greenfield-spec-and-plan`, `greenfield-delegate`, `greenfield-implement`, and `greenfield-verify` auto-invoke when relevant, load only the active phase or language's Tier 3 `references/*.md` on demand, and declare least-privilege `allowed-tools` (including scoped `Bash(${CLAUDE_SKILL_DIR}/scripts/... *)` grants matching their bundled scripts).
   - **Project & Skill Hooks (`0` prompt tokens)** — `settings.json` + skill frontmatter `hooks:` block generated-file/locked-migration edits, catch Go/Node/Rust/Bash-3.2 anti-patterns in `< 50 ms` on every edit, lock golden fixtures during ports, require `DR-00` addendum `0001` before scaffolding code, and re-inject project state after compaction.

## Delegated Coding & Agent Toolchain (Every Seeded Repo)

`greenfield-bootstrap` Step 2b runs `skills/greenfield-delegate/scripts/install-agent-skills.sh <go|node|rust>`, which installs three toolsets **into the new repository**:

| Toolset | How it lands | What the pipeline uses |
| --- | --- | --- |
| **ECC** (`affaan-m/ECC`, MIT) | Language pack vendored flat from a pinned commit (*hybrid* mode). ECC's own installer brings a 500+ file baseline, and the full plugin lists 314 skills in the main thread. | `<lang>-patterns`, `<lang>-testing` / `backend-patterns`, `coding-standards`, `/rust-build` · `/go-build` · `/build-fix`, `/rust-review` · `/go-review` · `typescript-reviewer` |
| **modularity** (`vladikk/modularity`) | Project-scope plugin (`extraKnownMarketplaces` + `enabledPlugins` in `.claude/settings.json`) | `modularity:design`, `modularity:review` |
| **GitNexus** (`abhigyanpatwari/GitNexus`) | `npx gitnexus@<pin> analyze --skip-agents-md --no-stats` builds the `.gitnexus/` index and the `gitnexus-*` skills; the MCP server is declared **inline in the agents**, not `.mcp.json` | `gitnexus-impact-analysis` (impact before edits, `detect_changes` before return) |

The pipeline agents ship as **static project subagents** in `agents/gf-planner.md`, `gf-implementer.md` and `gf-reviewer.md`. They follow the Claude Code subagent spec: `name`, a trigger-focused `description`, an allowlisted `tools` list, `model`, `effort`, `color`, `maxTurns`, `permissionMode`, `skills` preloads and inline `mcpServers`. The field rationale is in `skills/greenfield-delegate/references/agent-config-spec.md`, and `scripts/lint-agents.py` lints them. The script re-pins their GitNexus version and sets `CLAUDE_CODE_FORK_SUBAGENT=0`. When DR-05 is React (the default), it also installs the ECC React pack (`react-patterns`, `react-testing`, `vite-patterns`, `react-reviewer`, `/react-review` and so on). The same three agents then apply the React row to frontend files by path, so no per-language or per-frontend agent types are needed. Because the agents exist, `hooks/main-thread-code-guard.sh` is armed: from then on the **main thread never edits code**. Every change is plan (subagent) → implement (subagent) → review (subagent). The stages hand off through `docs/plans/` and `docs/reviews/`, and the main thread sees only ≤25-line replies. Each stage's context is thrown away when it returns, which keeps the main context from needing auto-compaction. The procedure is in `skills/greenfield-delegate/SKILL.md`; the reply formats and known limits are in `references/handoff-contract.md`. Verify with `install-agent-skills.sh <lang> --check`.

## How to Use

- **Inside `sidequest/`:** Start Claude Code in `sidequest/` (or pass `--add-dir sidequest`). Hooks and skills activate automatically.
- **Seeding a new Go / Node / Rust repository:**
  1. Copy `.claude/` and `initial-templates/` from `sidequest/` into the new repository.
  2. Run `/greenfield-bootstrap` — Claude runs the `DR-00` language router + chosen language's `DR-01..DR-11` interview, installs the agent toolchain (Step 2b, above), delegates Day-1 scaffolding to the `gf-*` pipeline, writes `docs/decisions/0001-*.md`…`NNNN-*.md`, renders a `< 130`-line `CLAUDE.md` from `CLAUDE.lean-template.md`, and deletes unused template menus.
- **Reviewing & planning a Node → Go (or Rust) port:**
  1. From the legacy Node repository, start Claude Code with `claude --add-dir /path/to/sidequest` (or copy `sidequest/.claude/` in).
  2. Run `/greenfield-port go .` — Claude executes `scripts/scan-node-for-port.sh` (`scan-node-repo.ts` under Node 22+, `0` script-source tokens) to inventory routes, status codes, 3-bucket test classifications, shared client/server TS modules, `replicas = 1` state, and `HZ-01`…`HZ-08` determinism sites, then drafts a validated two-cut porting plan from `assets/port-plan-template.md`.
- **Constructing or auditing a standalone Functional Design Specification (`fds-builder`):**
  1. Auto-invokes on FDS requests or run `/fds-builder [new|intake|resume|audit] [spec-path-or-topic]` (standalone and independent of `FDS_BUILDER.md` and `greenfield-*`).
  2. Executes a **30-step granular state machine (`0.1` → `6.1`)** with numbered substeps, per-step `5–7 KB` progressive reference files (`references/step-*.md`), `[GATE]` single-theme `AskUserQuestion` stops, `TaskCreate`/`TaskUpdate` batch tracking, `scripts/fds-state.sh` (`current-step` / `complete-step` leaf `done when` verifier + `seed-spec` + `DC-NNN` atomic rollback), and `scripts/audit-fds.sh` (`D1–D21` & `R1–R8` CLI + `PostToolUse` checks).
