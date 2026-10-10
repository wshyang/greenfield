# Handoff Contract — Delegated-Coding Pipeline

Load this file only when you spawn a stage or parse a reply.

## 1. Why this shape (context budget)

- A subagent runs in its **own** context window. Its tool calls, file reads, diffs and preloaded skills stay there, and they are discarded when it returns. Only its final message reaches the main thread.
- So the main thread's growth per change is about 3 spawn prompts plus 3 replies of ≤25 lines each. That is roughly 1–2k tokens, against the tens of thousands a main-thread implementation burns on reads, diffs and build output. This is what keeps auto-compaction rare.
- What breaks it:
  - A `fork` subagent, which inherits the full parent conversation.
  - Asking a subagent to "paste the diff" or "show the plan".
  - The main thread `Read`ing the plan or review files in full.
  - Putting all three stages in one subagent, so the review sees the implementer's reasoning and is no longer independent.
- Hand-offs go through files on disk (`docs/plans/`, `docs/reviews/`, the working tree). They are durable, they survive compaction, and the user can review them in the PR.

## 2. Spawn prompts (copy, fill, send; keep each ≤ 15 lines)

**Planner**
```
subagent_type: gf-planner
CHANGE: <one paragraph, in the user's terms>
PLAN_PATH: docs/plans/NNNN-<slug>.md
CONSTRAINTS: <known decisions / addenda IDs / "none">
GATE_ANSWERS: <only on resume: G1=<option>, G2=<option>>
```

**Implementer**
```
subagent_type: gf-implementer
PLAN_PATH: docs/plans/NNNN-<slug>.md
REVIEW_PATH: <fix round only: docs/reviews/NNNN-<slug>-rK.md; fix MUST findings; also SHOULD: <ids or none>>
```

**Reviewer**
```
subagent_type: gf-reviewer
PLAN_PATH: docs/plans/NNNN-<slug>.md
BASE: <sha recorded in preflight>
REVIEW_PATH: docs/reviews/NNNN-<slug>-rK.md
```

## 3. Replies (what the main thread acts on)

| Stage | Status values | Main-thread action |
| --- | --- | --- |
| plan | `READY` | `[GATE]` if RISK ≥ HIGH, a coupling imbalance or a new addendum; otherwise spawn the implementer |
| plan | `GATED` | Ask the `G#` items via `AskUserQuestion` → resume the planner |
| implement | `DONE` | Spawn the reviewer |
| implement | `BLOCKED` | Ask the BLOCKER question → send the answer to the **planner** to amend the plan → spawn a fresh implementer |
| review | `PASS` | Commit and push → report |
| review | `CHANGES-REQUIRED` | Fresh implementer (fix round) → fresh reviewer `r(K+1)`; `[GATE]` after 2 rounds |

A reply that breaks the format (for example, it pastes code) is still acted on. The next spawn prompt of that type then adds: `Reply only in the contract format.`

## 4. Resuming vs respawning

- **Resume (preferred, documented):** `SendMessage` to the planner's agent ID with `GATE_ANSWERS`. A resumed subagent keeps its full history and tool set. The planner keeps its own context, and the main thread pays only for the message.
- **Respawn (fallback):** write the answers under `## Gate answers` in the plan (a docs edit, so the hook allows it), then spawn a fresh `gf-planner` with the same `PLAN_PATH`. It re-reads the plan from disk.
- Implementers and reviewers are **always fresh**, never resumed across rounds. A reviewer must not inherit a previous round's reasoning, and an implementer must not carry stale assumptions.

## 5. Language map (static agents pick the row from `lang=` in `.claude/agent-skills.lock`)

| Lang | ECC skills vendored | ECC build (plan: diagnostics; implement: gate) | ECC review checklist | ECC agents vendored |
| --- | --- | --- | --- | --- |
| rust | `rust-patterns`, `rust-testing`, `coding-standards` | `/rust-build` | `/rust-review` | `rust-build-resolver`, `rust-reviewer` |
| go | `golang-patterns`, `golang-testing`, `coding-standards` | `/go-build` | `/go-review` | `go-build-resolver`, `go-reviewer` |
| node | `typescript-patterns`, `backend-patterns`, `coding-standards` | `/build-fix` | `typescript-reviewer` agent checklist | `build-error-resolver`, `typescript-reviewer` |
| + react (frontend, when `frontend=react`) | `react-patterns`, `react-testing`, `vite-patterns` (+ `typescript-patterns` for go/rust) | `/react-build` (tests: `/react-test`) | `/react-review` | `react-reviewer`, `react-build-resolver` (+ `typescript-reviewer` for go/rust) |

**One set of agents for every language.** The backend row comes from `lang=`. The React row is **added** (not swapped) when `frontend=react`, and agents choose it by file path (`frontend/**`, `*.tsx`/`*.jsx`, `lib/hooks/**`, `components/**`, `vite.config.*`). The installer picks `frontend=` in this order: `--frontend` flag > the DR-05 record (`choice:` frontmatter, else its H1 title) > a `react`/`next` dependency in a `package.json` > the documented default (React). `vite-patterns` is installed but not preloaded; agents load it via `Skill` when they touch Vite config. `react-testing`'s MSW mocks are limited to frontend unit tests at the API boundary (GREENFIELD-<LANG> §2). E2E tests stay mock-free.

Every language also gets the GitNexus skills (`gitnexus-impact-analysis`, `-exploring`, `-debugging`, `-refactoring`, `-guide`, `-cli`) and the modularity plugin (`modularity:design`, `modularity:review`, plus the internal `balanced-coupling` and `document`).

## 6. Known limits (state them honestly; don't paper over them)

- The guard hook sees `Edit`/`Write`/`MultiEdit`/`NotebookEdit` only. A main-thread `Bash` write such as `sed -i` or `cat >` is a discipline breach the hook cannot see. Invariant 1 forbids it.
- The guard relies on hook payloads carrying `agent_id` for subagent calls. If a future Claude Code release changes that field, re-check the hook: `install-agent-skills.sh <lang> --check` and a manual main-thread edit attempt should both show the deny.
- `modularity:*` arrives as a project-scope plugin. Until a teammate trusts the project and accepts the install prompt (or runs `/plugin install modularity@vladikk-modularity`), the planner and reviewer must report `modularity: unavailable`. They must not invent a coupling assessment.
- Background subagents (the default) bring their permission prompts to the main session, naming the agent. A grant that lasts beyond one tool call applies to the whole session. Prefer project `permissions.allow` rules for the build and test commands.
- GitNexus MCP is inline in each agent, so it starts with each stage (an `npx` start-up per spawn) and needs the project folder to be trusted. GitNexus works without its MCP server through the CLI (`npx gitnexus@<pin> impact|detect-changes|analyze`). Full-text search needs the LadybugDB FTS extension. Without it, graph queries still work and keyword search is disabled.
