# `sidequest/.claude` — Modular Greenfield Skills, Path-Scoped Rules & Hooks

This directory converts the monolithic `GREENFIELD-{GO,NODE,RUST}.md` standing-instruction templates (`1,200–3,700` lines / `15k–45k` tokens per turn) into a **progressive-disclosure Claude Code `.claude/` architecture** that cuts idle context usage by **~96%** while making hard invariants deterministic via hooks.

## Why 4 Layers Instead of One Giant `CLAUDE.md` or One Giant `SKILL.md`

1. **Monolithic `CLAUDE.md` (`~45k` tokens)** consumes ~22% of a 200k context window before Turn 1 and triggers *lost-in-the-middle* instruction drop-off.
2. **Monolithic `SKILL.md` (`~45k` tokens)** hits Claude Code's **5,000-token per-skill post-compaction re-injection cap** (`code.claude.com/docs/en/context-window`), truncating ~89% of the file on the first `/compact`.
3. **This `.claude/` layout splits `GREENFIELD-<lang>` by lifecycle:**
   - **Lean `CLAUDE.md` (`<= 130` lines, unpacked from `skills/greenfield-bootstrap/assets/CLAUDE.lean-template.md`)** — `~1,200` tokens, 100% re-injected from disk after compaction.
   - **Path-scoped `.claude/rules/*.md` (`0` tokens at startup)** — auto-loaded only when touching SQL/migrations, `.tsx`/Playwright, `Dockerfile*`/`*.shiphats`, or `.sh` scripts.
   - **5 Progressive-Disclosure Skills (`.claude/skills/*/SKILL.md`, each `< 220` lines)** — `greenfield-bootstrap` and `greenfield-port` set `disable-model-invocation: true` (`0` startup tokens); `greenfield-spec-and-plan`, `greenfield-implement`, and `greenfield-verify` cost `~270` startup tokens combined and load only the active language's Tier 3 `references/*.md` on demand.
   - **Project & Skill Hooks (`0` prompt tokens)** — `settings.json` + skill frontmatter `hooks:` block generated-file/locked-migration edits, catch Go/Node/Rust/Bash-3.2 anti-patterns in `< 50 ms` on every edit, lock golden fixtures during ports, require `DR-00` addendum `0001` before scaffolding code, and re-inject project state after compaction.

## How to Use

- **Inside `sidequest/`:** Start Claude Code in `sidequest/` (or pass `--add-dir sidequest`). Hooks and skills activate automatically.
- **Seeding a new Go / Node / Rust repository:**
  1. Copy `.claude/` and `initial-templates/` from `sidequest/` into the new repository.
  2. Run `/greenfield-bootstrap` — Claude runs the `DR-00` language router + chosen language's `DR-01..DR-11` interview, writes `docs/decisions/0001-*.md`…`NNNN-*.md`, renders a `< 130`-line `CLAUDE.md` from `CLAUDE.lean-template.md`, and deletes unused template menus.
- **Reviewing & planning a Node → Go (or Rust) port:**
  1. From the legacy Node repository, start Claude Code with `claude --add-dir /path/to/sidequest` (or copy `sidequest/.claude/` in).
  2. Run `/greenfield-port go .` — Claude executes `scripts/scan-node-for-port.sh` (`scan-node-repo.ts` under Node 22+, `0` script-source tokens) to inventory routes, status codes, 3-bucket test classifications, shared client/server TS modules, `replicas = 1` state, and `HZ-01`…`HZ-08` determinism sites, then drafts a validated two-cut porting plan from `assets/port-plan-template.md`.
