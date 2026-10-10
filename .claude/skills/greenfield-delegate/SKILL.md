---
name: greenfield-delegate
description: Delegated-coding discipline for Greenfield repos. The main thread never writes code. It runs every code change as a gf-planner → gf-implementer → gf-reviewer subagent pipeline, passing file paths instead of contents, so each stage's context is thrown away and the main context stays small. Use whenever a request needs code to be written, changed, refactored, fixed or reviewed.
when_to_use: Before any change under src/, internal/, cmd/, crates/, packages/, tests/, migrations/ or a build manifest; when the user asks to implement, fix, refactor, port or review code; when a plan exists and needs executing.
argument-hint: "[change request]"
allowed-tools:
  - Read
  - Glob
  - Grep
  - Agent
  - SendMessage
  - AskUserQuestion
  - TaskCreate
  - TaskUpdate
  - Bash(git status*)
  - Bash(git diff --stat*)
  - Bash(git log*)
  - Bash(git add*)
  - Bash(git commit*)
  - Bash(git push*)
  - Bash(git rev-parse*)
  - Bash(${CLAUDE_SKILL_DIR}/scripts/install-agent-skills.sh *)
---

# Greenfield Delegated Coding (`greenfield-delegate`)

## Critical Invariants (Read First — Survives Compaction)

1. **The main thread is the orchestrator, never the coder.**
   - It talks to the user, asks every question through `AskUserQuestion`, spawns the three pipeline subagents in sequence, reads only their short replies, commits and pushes.
   - It never edits code. `.claude/hooks/main-thread-code-guard.sh` denies main-thread `Edit`/`Write` on code paths, and denies them to `gf-planner` and `gf-reviewer` too.
   - Do not get around the hook with Bash heredocs or `sed -i`. That breaks the discipline even where the hook cannot see it.
2. **Plan → implement → review, every time.** Each stage is a fresh named subagent: `gf-planner`, then `gf-implementer`, then `gf-reviewer`.
   - **Never use `subagent_type: "fork"`**: a fork inherits the whole main conversation, which defeats the self-contained context.
   - Never ask one subagent to do two stages.
3. **Pass paths, not payloads.**
   - The plan lives in `docs/plans/NNNN-<slug>.md` and the review in `docs/reviews/NNNN-<slug>-rK.md`. Each stage reads the previous stage's file from disk.
   - The main thread never `Read`s a full plan, diff or review into its own context. It acts on the subagent's ≤25-line reply (format in `references/handoff-contract.md`).
   - It may read one named section, such as `## Gates`, only when a reply points to it.
4. **Subagents never ask the user.**
   - They return questions in their reply (`GATES:` or `QUESTIONS:`, ready for `AskUserQuestion`).
   - The main thread asks them through `AskUserQuestion`, then resumes the same subagent with `SendMessage`. If it cannot be resumed, the main thread writes the answers under the plan's `## Gate answers` and spawns a fresh planner.
5. **Greenfield beats ECC on conflict.** If vendored ECC guidance clashes with a Greenfield rule (e.g. mocking the data layer vs zero repo mocks, or ECC's coverage targets vs the bite check), the `CLAUDE.md` §4 invariants and the `greenfield-*` skills win.

## Toolchain (installed by bootstrap Step 2b; `install-agent-skills.sh <lang> --check` verifies it)

| Stage | Agent | Skills it runs (preloaded via the agent's `skills:` list) |
| --- | --- | --- |
| 1 Plan | `gf-planner` | `gitnexus-impact-analysis`, `gitnexus-exploring`, `modularity:design` (delta mode) + `modularity:balanced-coupling`, ECC `<lang>-patterns`, `coding-standards`, ECC build command as **diagnostics-only baseline** (`/rust-build`, `/go-build`, `/build-fix`), `greenfield-spec-and-plan` (two-cut format) |
| 2 Implement | `gf-implementer` | `greenfield-implement`, `greenfield-verify`, ECC `<lang>-patterns` + `<lang>-testing` (Node: `backend-patterns`), ECC build command **as the build gate**, `gitnexus-impact-analysis` (impact before each edit; `detect_changes` before return) |
| 3 Review | `gf-reviewer` | `modularity:review` + `modularity:document`, ECC `<lang>-patterns`, `coding-standards`, ECC review checklist (`/rust-review`, `/go-review`, `typescript-reviewer`), `gitnexus-impact-analysis` (scope = diff + d=1) |

The agents are static project subagents in `.claude/agents/gf-*.md`, written to the Claude Code spec. The field-by-field rationale is in `references/agent-config-spec.md`, and `scripts/lint-agents.py` checks them. Each lists every language's ECC pack plus the React pack; only the installed ones preload (`lang=` and `frontend=` in `.claude/agent-skills.lock`). Three agent types serve every language; frontend files use the React row by path. GitNexus MCP is declared inline per agent. `.claude/settings.json` sets `CLAUDE_CODE_FORK_SUBAGENT=0`, so Claude waits for each stage and never forks.

The ECC language packs are vendored flat, so their names have no `ecc:` prefix: `rust-patterns` is `ecc:rust-patterns` and `/rust-build` is `/ecc:rust-build`. modularity is a project-scope plugin (`modularity:*`). The GitNexus skills are installed by `gitnexus analyze`.

## Procedure (one change request)

1. **Preflight.**
   - Run `install-agent-skills.sh <lang> --check`. On a gap, run it without `--check`, after asking first if the language is not recorded in `docs/decisions/0001-*`.
   - Record `BASE=$(git rev-parse HEAD)`.
   - Pick the next `NNNN` from `docs/plans/` and a kebab-case `<slug>`.
   - `TaskCreate` three tasks: plan, implement, review.
2. **Plan.** Spawn `gf-planner` with: the change request (one paragraph), `PLAN_PATH`, and any known constraints.
   - On `STATUS: GATED`: ask each `G#` via `AskUserQuestion` (1–4 per call, `(Recommended)` first), then resume the planner with the answers (invariant 4). Repeat until `STATUS: READY`.
   - `[GATE]` If the reply shows `RISK: HIGH|CRITICAL`, any coupling imbalance, or a new `docs/decisions/` addendum: confirm the Shape with the user via `AskUserQuestion` before implementing.
3. **Implement.** Spawn `gf-implementer` with `PLAN_PATH` only.
   - On `STATUS: BLOCKED`: ask its suggested question via `AskUserQuestion`, then send the answer back to the **planner** (to amend the plan), never to the implementer. Then spawn a fresh implementer.
4. **Review.** Spawn `gf-reviewer` with `PLAN_PATH`, `BASE` and `REVIEW_PATH` (round `r1`).
   - `PASS`: go to step 5.
   - `CHANGES-REQUIRED`: spawn a **fresh** `gf-implementer` with `PLAN_PATH` + `REVIEW_PATH` (fixing MUST findings only), then a fresh `gf-reviewer` as round `r2`.
   - `[GATE]` After **2 fix rounds** without a PASS, stop. Show the user the remaining MUST findings and offer: one more round (Recommended only if the count is falling), re-plan, or accept with an addendum.
5. **Close.**
   - Commit the code, the ticked plan and the reviews in one commit referencing `NNNN`, then push.
   - Report to the user in ≤ 10 lines: plan path, verdict, the rung reached (from the implementer reply), and any open SHOULD findings.

Run independent change requests as separate pipelines. Never mix two plans in one implementer. Stages may run in the background; wait for each stage's completion notice before spawning the next.

## Decision Points (AI Proposes, User Decides)

Tags: **`[IDEATE]`** = draft 2–4 concrete options, each with its trade-off, mark one `(Recommended)` with a one-line reason, then ask via `AskUserQuestion` (state the skip-default). **Questions go only through `AskUserQuestion`, never inline.** A reply must not end with a list of questions or a prose question; a decision table in a doc only records what was asked. **`[GATE]`** = hard stop until the user confirms. First check `docs/spec.md` and `docs/decisions/`, and ask only what they leave open. Persist every answer the same change, as an addendum or plan edit.

1. **Trivial-change fast path** `[IDEATE]`: For a change of ≤ 5 lines with no new symbol (a typo, a config value, a version bump), offer to *run the full pipeline* (default) or *skip review only*. Planning and implementing stay delegated either way. The main thread never edits code.
2. **Emergency override** `[GATE]`: Only the user creates `.claude/main-edit.allow`. Never create it yourself. When it is present, say so in every reply until the user removes it.

## Reference

- `references/handoff-contract.md`: the reply formats, the spawn prompts, the resume and fix-round patterns, and why this saves context.
- `references/agent-config-spec.md`: the Claude Code subagent file format (all frontmatter fields, skip rules, tool filters, fork mode, resume) and why each `gf-*` field is set as it is.
