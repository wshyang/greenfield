---
name: greenfield-bootstrap
description: Bootstraps a new Go 1.27, Node.js 22 + TypeScript, or Rust 1.99 repository using the Greenfield decision interview (DR-00 through DR-11), records initial addenda in docs/decisions/, contextualises container and inert SHIP-HATS templates, and generates a lean <130-line CLAUDE.md. Invoke with /greenfield-bootstrap when starting or unpacking a repository.
argument-hint: "[go|node|rust]"
arguments:
  - lang
disable-model-invocation: true
allowed-tools:
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - AskUserQuestion
  - Agent
  - Bash(${CLAUDE_PROJECT_DIR}/.claude/skills/greenfield-delegate/scripts/install-agent-skills.sh *)
hooks:
  PreToolUse:
    - matcher: "Edit|Write"
      hooks:
        - type: command
          command: "\"${CLAUDE_SKILL_DIR}\"/scripts/require-dr00-before-code.sh"
---

# Greenfield Bootstrap (`/greenfield-bootstrap`)

## Critical Invariants (Read First — Survives Compaction)

1. **Never choose a language or unresolved `DR-` fork silently.** Ask the user first, via the `AskUserQuestion` tool and never as inline prose or a numbered list of questions in the reply, (unless already stated in `$lang` or the prompt), then write `docs/decisions/0001-backend-language.md` **before** creating any file under `src/`, `internal/`, `cmd/`, or `crates/` (enforced by this skill's `PreToolUse` hook).
2. **Generate a lean `CLAUDE.md` (`<= 130` lines) from `${CLAUDE_SKILL_DIR}/assets/CLAUDE.lean-template.md` — do NOT paste a 3,700-line `GREENFIELD-<LANG>.md` monolith as `CLAUDE.md`.** Keep `.claude/` (skills, path-scoped rules, hooks) alongside the lean `CLAUDE.md` so deep rules load on demand instead of taxing every turn.
3. **Prune unused menus in the same commit.** Delete unchosen template variants and replace every `<placeholder>`.
4. **Install the delegated-coding toolchain before any code exists (Step 2b).**
   - Run `greenfield-delegate/scripts/install-agent-skills.sh <lang>`. It vendors the ECC language pack, indexes the repo with GitNexus (installing the `gitnexus-*` skills), declares the `modularity` project plugin, pins and lints the shipped `.claude/agents/gf-{planner,implementer,reviewer}.md`, and turns fork mode off (`CLAUDE_CODE_FORK_SUBAGENT=0`). `main-thread-code-guard.sh` is armed from the first session, because the agents ship with `.claude/`.
   - From then on, the main thread never writes code. Every code change, including Day-1 scaffolding, runs through the `greenfield-delegate` pipeline.
5. **Enforce the architectural leaf & fitness test on Day 1:** create the zero-I/O `kernel` leaf (`internal/kernel` in Go, `packages/kernel` in Node, `crates/kernel` in Rust) plus an executable dependency-graph test proven to fail on a synthetic violation.

## Step-by-Step Procedure

### Step 0 — Egress-Restricted Sandbox Check (When `rustc` / `go` / `chromium` Are Missing)

If running inside a firewall-restricted container where `sh.rustup.rs`, `index.crates.io`, `go.dev`, or `proxy.golang.org` fail TLS (`SSL_ERROR_SYSCALL`), read `${CLAUDE_SKILL_DIR}/references/egress-sandbox-bootstrap.md` first to install Rust 1.99, Go 1.27.3, and offline Chromium 150 from allowed `registry.npmjs.org` / `pypi.org` mirrors without exceeding workspace snapshot limits.

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
- Write one `docs/decisions/NNNN-<slug>.md` file per settled decision. Give the `DR-05` (frontend) record a `choice:` frontmatter line naming the option (e.g. `choice: React + Vite SPA (frontend/)`, `choice: askama + HTMX`, `choice: headless`). Step 2b reads it to decide whether to install the ECC React pack. Node has no DR-05 card, so record `decision: DR-05` with `choice: headless` if a Node repo has no React frontend. If `DR-11 = B` (pre-launch single snapshot + `schema_state` gate), also touch `.schema-option-b` or record `DR-11: B` in `CLAUDE.md` so `.claude/hooks/pre-write-guard.sh` blocks accidental `migrations/` files.

### Step 2b — Install the Delegated-Coding Toolchain (Discipline, Every Repo)

1. Make one commit first (GitNexus indexes the git tree). Then run `"$CLAUDE_PROJECT_DIR"/.claude/skills/greenfield-delegate/scripts/install-agent-skills.sh <go|node|rust>` via `Bash`. It installs:
   - **ECC (`affaan-m/ECC`)**, from a pinned commit, the chosen language pack only:
     - `rust-patterns` + `rust-testing`, `golang-patterns` + `golang-testing`, or `typescript-patterns` + `backend-patterns`;
     - plus `coding-standards`, the build and review agents, and the `/rust-build` · `/go-build` · `/build-fix` and `/rust-review` · `/go-review` commands;
     - **plus the React frontend pack, automatically, when DR-05 is React** (Go and Rust default; Node by default): `react-patterns`, `react-testing`, `vite-patterns`, `react-reviewer`, `react-build-resolver`, `/react-build` · `/react-review` · `/react-test` (+ `typescript-patterns` / `typescript-reviewer` for Go and Rust). Override with `--frontend react|none`. The lock records `frontend=` and its source.
   - **GitNexus (`abhigyanpatwari/GitNexus`):** `npx gitnexus@<pin> analyze --skip-agents-md --no-stats` builds the `.gitnexus/` index and installs `gitnexus-impact-analysis` and its sibling skills. It never touches the lean `CLAUDE.md`. Its MCP server is declared **inline in the agents** (`mcpServers:`), not in `.mcp.json`, so its tool descriptions stay out of the main thread.
   - **modularity (`vladikk/modularity`):** declared under `extraKnownMarketplaces` and `enabledPlugins` in the committed `.claude/settings.json`, which makes `modularity:design` and `modularity:review` available.
   - **The pipeline agents** (`.claude/agents/gf-*.md`, static and language-agnostic, spec in `greenfield-delegate/references/agent-config-spec.md`): the installer re-pins their `gitnexus@` version and runs `lint-agents.py`.
2. Run `install-agent-skills.sh <lang> --check`. It must print `agent-skills check: OK`. A `--skip-index` run (e.g. an offline sandbox) lists the GitNexus skills as `PENDING`. Re-run without the flag once the network is available.
3. Commit `.claude/`, `.gitignore` and `.claude/agent-skills.lock` together. Tell the user that Claude Code will offer to install the `modularity` plugin when the project is trusted.
4. `[IDEATE if the network blocks GitHub or npm]`: Offer to *run with `--skip-index` now and index later*, to *install from a mirror via the `ECC_REPO` / `GITNEXUS_VERSION` overrides*, or to *stop and hand off*. Never mark the toolchain installed when `--check` fails.

### Step 3 — Unpack Lean `CLAUDE.md` / `AGENTS.md`, Prune `.claude/`, Containers & Inert SHIP-HATS

1. Render `CLAUDE.md` from `${CLAUDE_SKILL_DIR}/assets/CLAUDE.lean-template.md`, filling in the settled decisions, exact repo commands, active `<go|node|rust>` reference path, and package DAG (strictly `<= 130` lines, zero `<placeholder>` tokens). If the team uses multiple coding agents, put the unpacked file at `AGENTS.md` and write `@AGENTS.md` in `CLAUDE.md` (never maintain two separate copies).
2. **Prune unchosen `.claude/` files in the seeded repo:** delete the other two languages' reference files (`references/<other-lang>-*.md`), delete `greenfield-bootstrap/` once unpacking finishes, and delete `greenfield-port/` if the repo is greenfield (not a port). **Never delete `greenfield-delegate/`.** Its installer, `--check` and the agent lint live there.
3. **Delegate** (in the Day-1 pipeline run of item 4) contextualising `Dockerfile`, `Dockerfile.dev`, `Dockerfile.cloudflared`, and `.dockerignore` (`0.0.0.0:3000`, numeric `USER`, CIDR proxy trust, `HEALTHCHECK`), plus inert `*.shiphats` files and Bash 3.2-compatible `activate-shiphats.sh`.
4. **Delegate** creating the `kernel` leaf, the dependency-graph test (plus a violating fixture), `.env.example` / `.env.test`, and the `check-standards` skeleton. Items 3–4 are the first `greenfield-delegate` pipeline run: `gf-planner` writes `docs/plans/0001-day1-scaffold.md`, then `gf-implementer` builds it, then `gf-reviewer` reviews it. The main thread does not write these files.
5. State the exact §8 validation rung executed before finishing.
