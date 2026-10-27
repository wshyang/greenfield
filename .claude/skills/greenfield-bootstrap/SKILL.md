---
name: greenfield-bootstrap
description: Bootstraps a new Go 1.27, Node.js 22 + TypeScript, or Rust 1.99 repository using the Greenfield decision interview (DR-00 through DR-11), records initial addenda in docs/decisions/, contextualises container and inert SHIP-HATS templates, and generates a lean <130-line CLAUDE.md. Invoke with /greenfield-bootstrap when starting or unpacking a repository.
argument-hint: "[go|node|rust]"
arguments:
  - lang
disable-model-invocation: true
hooks:
  PreToolUse:
    - matcher: "Edit|Write"
      hooks:
        - type: command
          command: "\"${CLAUDE_SKILL_DIR}\"/scripts/require-dr00-before-code.sh"
---

# Greenfield Bootstrap (`/greenfield-bootstrap`)

## Critical Invariants (Read First — Survives Compaction)

1. **Never choose a language or unresolved `DR-` fork silently.** Ask the user first (unless already stated in `$lang` or the prompt), then write `docs/decisions/0001-backend-language.md` **before** creating any file under `src/`, `internal/`, `cmd/`, or `crates/` (enforced by this skill's `PreToolUse` hook).
2. **Generate a lean `CLAUDE.md` (`<= 130` lines) from `${CLAUDE_SKILL_DIR}/assets/CLAUDE.lean-template.md` — do NOT paste a 3,700-line `GREENFIELD-<LANG>.md` monolith as `CLAUDE.md`.** Keep `.claude/` (skills, path-scoped rules, hooks) alongside the lean `CLAUDE.md` so deep rules load on demand instead of taxing every turn.
3. **Prune unused menus in the same commit.** Delete unchosen template variants and replace every `<placeholder>`.
4. **Enforce the architectural leaf & fitness test on Day 1:** create the zero-I/O `kernel` leaf (`internal/kernel` in Go, `packages/kernel` in Node, `crates/kernel` in Rust) plus an executable dependency-graph test proven to fail on a synthetic violation.

## Step-by-Step Procedure

### Step 1 — Settle `DR-00` (Backend Language)

- If `$lang` (`$0`) or the user's message already names `go`, `node`, or `rust`, confirm it in one sentence without re-asking.
- Otherwise, read `${CLAUDE_SKILL_DIR}/references/dr00-language-router.md` and present the `DR-00` card as its own message (never bundled with framework/ORM questions).
- Record the answer immediately as `docs/decisions/0001-backend-language.md` with YAML frontmatter (`id`, `decision: DR-00`, `status: accepted`, `decided_by`, `date`, `supersedes: null`) and checkbox `## Impact` lines (`- [ ] 0001-1 ... — done when ...`).

### Step 2 — Run ONLY the Chosen Language's Decision Interview

Read **only** the matching reference file (never load the other two languages into context):

- **Go 1.27:** read `${CLAUDE_SKILL_DIR}/references/go-decisions-dr01-dr11.md`
- **Node.js 22 + TypeScript:** read `${CLAUDE_SKILL_DIR}/references/node-decisions-checklist.md`
- **Rust 1.99 (2024 edition):** read `${CLAUDE_SKILL_DIR}/references/rust-decisions-dr01-dr11.md`

Interview rules:
- Skip any `DR-` question the user already answered; confirm and record it.
- Group at most `3–4` related cards per message (e.g. HTTP + Data + Wire; Jobs + Auth + Frontend; Schema mode `DR-11` + Runtime image).
- If the user replies *"defaults"* or *"you choose"*, adopt the documented default for every remaining card with `decided_by: agent` and explicit rationale.
- Write one `docs/decisions/NNNN-<slug>.md` file per settled decision. If `DR-11 = B` (pre-launch single snapshot + `schema_state` gate), also touch `.schema-option-b` or record `DR-11: B` in `CLAUDE.md` so `.claude/hooks/pre-write-guard.sh` blocks accidental `migrations/` files.

### Step 3 — Unpack Lean `CLAUDE.md` / `AGENTS.md`, Prune `.claude/`, Containers & Inert SHIP-HATS

1. Render `CLAUDE.md` from `${CLAUDE_SKILL_DIR}/assets/CLAUDE.lean-template.md`, filling in the settled decisions, exact repo commands, active `<go|node|rust>` reference path, and package DAG (strictly `<= 130` lines, zero `<placeholder>` tokens). If the team uses multiple coding agents, put the unpacked file at `AGENTS.md` and write `@AGENTS.md` in `CLAUDE.md` (never maintain two separate copies).
2. **Prune unchosen `.claude/` files in the seeded repo:** delete the other two languages' reference files (`references/<other-lang>-*.md`), delete `greenfield-bootstrap/` once unpacking finishes, and delete `greenfield-port/` if the repo is greenfield (not a port).
3. Contextualise `Dockerfile`, `Dockerfile.dev`, `Dockerfile.cloudflared`, and `.dockerignore` (`0.0.0.0:3000`, numeric `USER`, CIDR proxy trust, `HEALTHCHECK`), plus inert `*.shiphats` files and Bash 3.2-compatible `activate-shiphats.sh`.
4. Create the `kernel` leaf, dependency-graph test (plus violating fixture), `.env.example` / `.env.test`, and `check-standards` skeleton.
5. State the exact §8 validation rung executed before finishing.
