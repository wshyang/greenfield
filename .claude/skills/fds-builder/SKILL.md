---
name: fds-builder
description: Interactive Functional Design Specification (FDS) construction, audit, and refinement architect executing a 30-step granular state machine with numbered substeps, hard AskUserQuestion stop gates, codified NFR archetypes, R1-R8 structural audits, and atomic DC-NNN rollback. Auto-invocable whenever drafting, reverse-intaking, auditing, or finalizing a Functional Design Specification.
when_to_use: When the user asks to create, draft, structure, audit, review, refine, or finalize a Functional Design Specification (FDS), product/system functional spec, object-and-surface contract spec, or "/fds-builder". Exists independently alongside FDS_BUILDER.md and greenfield-spec-and-plan.
argument-hint: "[new|intake|audit|resume] [spec-path-or-topic]"
arguments:
  - mode
  - target
allowed-tools:
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - AskUserQuestion
  - TaskCreate
  - TaskUpdate
  - TaskList
  - Bash(${CLAUDE_SKILL_DIR}/scripts/fds-state.sh *)
  - Bash(${CLAUDE_SKILL_DIR}/scripts/audit-fds.sh *)
hooks:
  PostToolUse:
    - matcher: "Edit|Write"
      hooks:
        - type: command
          command: "\"${CLAUDE_SKILL_DIR}\"/scripts/audit-fds.sh"
---

# FDS Builder — 30-Step Granular FDS Construction Architect

Constructs, audits, and finalizes canonical 16-section **Functional Design Specifications (`.md`)** through **30 atomic granular steps (`0.1` → `6.1`)** with numbered substeps, mechanical `done when` gates, and per-step progressive reference loading. Standalone inside `sidequest/.claude/skills/fds-builder/` (independent of `sidequest/FDS_BUILDER.md` and `greenfield-spec-and-plan`).

Inputs: `$ARGUMENTS` (`mode`: `$0`, `target`: `$1`)

## Granular Execution Laws (Survives Compaction)

1. **One Granular Step per Turn (`Never Bundle Domains`):** Run `"${CLAUDE_SKILL_DIR}/scripts/fds-state.sh" current-step`, execute **only** that step's numbered substeps in order, and advance strictly via `fds-state.sh complete-step <step_id>` (which mechanically verifies `done when` on disk before unlocking the next step).
2. **Hard Stop Gates (`[GATE]`):** At every `[GATE]` step, call **`AskUserQuestion`** (`1–4` single-theme questions max; `2–5` word `label` marking `(Recommended Default)` where relevant; `1–2` sentence consequence + `because` trade-off `description`; `allowCustomResponse: true`) and **stop the turn immediately**. Questions are never asked inline: a reply never ends with a numbered list of questions or a prose question. Never silently adopt any NFR preset, `R3` deletion rule, or threshold.
3. **Just-In-Time Single Reference Loading:** Read **only** the single `5–7 KB` file (`${CLAUDE_SKILL_DIR}/references/step-*.md`) named for the active step — never preload later references or paste the 310-line template into chat (`fds-state.sh seed-spec` writes `<spec_path>` directly).
4. **Synchronized Native Tasks (`TaskCreate` / `TaskUpdate`):** Materialize granular step and batch tasks via `TaskCreate` (never 6 coarse phase buckets). Keep **at most ONE** task `in_progress` via `TaskUpdate`.
5. **Immediate Persistence After Every Gate:** Upon each user reply: *(a)* `fds-state.sh add-dc`, *(b)* surgical `Edit` to `<spec_path>` (+ Section 15 Changelog), *(c)* `fds-state.sh complete-step <step_id>`.
6. **Banner & Tags:** Start every FDS reply with `Phase: <step> | Progress: <summary>` (`D11`). Tag unconfirmed drafts `[DRAFT — {source}]` (`D1`), custom rules `[CUSTOM: <decision> because <rationale>]` (`D7`), skips with 1-line `D9` `because` notices, and rollbacks via `fds-state.sh rollback-dc DC-NNN`.
7. **Zero Diagrams (`D15`), Agnostic Pseudocode (`D16`), Synthetic Data (`D17`):** No Mermaid/PlantUML/Graphviz/SVG/ASCII boxes or language-locked code fences (`python`/`ts`/`go`/`rust`/`sql`/`bash`). Verbatim diagram refusal: `"I'm unable to generate diagrams as the mermaid diagram feature is currently disabled for this bot."`

**Slash Commands:** `/chunked`..`/done` (`fds-state.sh chunk start|append|done|read`) • `/status` (`current-step`) • `/decisions` (`DC-NNN` table) • `/parked` (`audit-fds.sh --phase review`) • `/audit` (`audit-fds.sh --phase r5-parity`).

---

## Phase 0 — Entry & Intake (`Ref: references/step-00-entry-and-intake.md`)

### Step `0.1` — Mode Routing, Chunked Buffer & Ledger Init
1. Read `step-00-entry-and-intake.md` (§1–§2); handle bare `/fds-builder`, `/chunked`, `D15`, or `§1.3` guard, or resume `.fds-state/active.json` via `current-step`.
2. Resolve `<spec_path>` (`$target` or `1` `AskUserQuestion` card `[GATE]`), run `fds-state.sh init --spec "<spec_path>" --mode "<new|intake>"`, and create Phase 0/1 step tasks via `TaskCreate`.
- *`done when`:* `.fds-state/active.json` initialized (`chunked_mode.active == false`).

### Step `0.2` — Reverse Intake & Gap Triage *(Intake Mode Only)* `[GATE]`
1. Run `fds-state.sh seed-spec`, map explicit source facts into `#obj-*/#feat-*/#surf-*/#flow-*/#int-*/#nfr-*` blocks via `Edit`, and tag missing contracts `[DRAFT — intake-gap]`.
2. Run `audit-fds.sh "<spec_path>" --phase intake`, confirm triage via `AskUserQuestion`, mint `DC-001`, and complete `0.2`.
- *`done when`:* `<spec_path>` exists and intake `DC-NNN` recorded.

---

## Phase 1 — Intent Gate & Lineup (`Ref: references/step-01-intent-and-lineup.md`)

### Step `1.1` — 3-Order Intent Decomposition & Coherence Probes `[GATE if ambiguous]`
1. Read `step-01-intent-and-lineup.md` (§1–§2); extract `1st` (literal ask), `2nd` (daily workflow/actors), and `3rd` (governance/risk/scale/cutover) orders, challenging any flawed premise (`MUST #14`).
2. If ambiguous, ask `1–3` typed probes via `AskUserQuestion` (`D7` if custom/open), then complete `1.1`.
- *`done when`:* Coherent 1st, 2nd, and 3rd order statements ready for confirmation.

### Step `1.2` — Explicit `[INTENT_ALIGNED]` Lock (`MUST #1`) `[GATE]`
1. Confirm `1–3` sentence summary of Orders `1–3` via `AskUserQuestion`.
2. Mint `DC-NNN`, run `complete-step 1.2 --intent-aligned`, and create Phase 2 step tasks via `TaskCreate`.
- *`done when`:* `intent_aligned == true` and active `DC-NNN` recorded.

### Step `1.3` — 16-Section Lineup, Critical Weights & Spec Seeding `[GATE]`
1. Confirm conditional sections (`r6-collision`, `r7-session`, `integrations`, `data-migration`, `anti-patterns`) and `Critical` (`weight=3`) tags (`day-zero-bootstrap` locked `Critical`) via `AskUserQuestion`.
2. Run `lineup ... --approve`, `seed-spec --title "<Title>"`, mint `DC-NNN`, and complete `1.3` *(or `skip-to-deep-dive` in `intake` mode if `--phase scaffold` passes)*.
- *`done when`:* `lineup_approved == true` and `<spec_path>` seeded on disk.

---

## Phase 2 — Granular Domain Scaffold (`Steps 2.01–2.13`)

### Step `2.01` — Domain 1: Boundaries, Actors & Phase Scope (`Ref: step-02a-boundaries-and-objects.md`) `[GATE]`
1. Read `step-02a` (§1–§2); confirm actor roles, in/out boundaries, and `Phase 1` vs `Phase 2+` split via `AskUserQuestion`.
2. Edit `Sections 3 & 4`, mint `DC-NNN`, and complete `2.01`.
- *`done when`:* `Section 4` populated without template placeholders.

### Step `2.02` — Domain 2: Core Object Inventory & Batch Queue (`Ref: step-02a §3`) `[GATE]`
1. Confirm `#obj-*` inventory (`slug`, responsibility, phase) via `AskUserQuestion`.
2. Register `1–3` objects/batch via `register-items --kind object-batch --items "<b1>;<b2>"` + `TaskCreate`, mint `DC-NNN`, and complete `2.02`.
- *`done when`:* `>= 1` `object-batch` registered.

### Step `2.03` *(Loop: `object-batch`)* — Domain 3 & `D20`: Attributes & Empty States (`Ref: step-02a §4`) `[GATE]`
1. For active batch (`<= 3` objects), resolve uniqueness scopes, mutability, validation bounds, and list exposure via `AskUserQuestion`.
2. Author all 8 `#obj-*` subsections in `Section 5`: 6-col `D3` table (`0` blank cells, verbatim error copy) + 4 `D20` empty states, mint `DC-NNN`, and complete `2.03`.
- *`done when`:* `Section 5` defines real `#obj-*` contracts (`#obj-example` removed on final batch).

### Step `2.04` — Domain 5, `R1` & `R3` Pass 1: Relationship Map (`Ref: step-02b-relationships-and-lifecycles.md`) `[GATE]`
1. Read `step-02b` (§1–§3); promote `N:M` / data-carrying links to `#obj-*` and elicit `4` link surfaces (`Create|List|Remove|Inverse-View`) + `R3` `on_delete` (`CASCADE|RESTRICT|SET_NULL|SOFT_ARCHIVE`) via `AskUserQuestion`.
2. Populate 7-col `Section 6` map + narrative, add promoted `#obj-*` blocks to `Section 5`, write `Section 7` invariants, mint `DC-NNN`, and complete `2.04`.
- *`done when`:* `Section 6` specifies `on_delete` without `#obj-parent-example`.

### Step `2.05` *(Loop: `stateful-batch`)* — Domain 4 (`D4`): State Lifecycles (`Ref: step-02b §4`) `[GATE]`
1. Register stateful batches (`1–2`/batch) via `register-items --kind stateful-batch` (or `complete-step 2.05 --skip-reason "..."` if all stateless).
2. Confirm state sets, guards, terminal edit-locks, and forbidden transitions via `AskUserQuestion`, write `Section 5` lifecycle tables + `because` rationales, mint `DC-NNN`, and complete `2.05`.
- *`done when`:* Stateful `#obj-*` blocks define legal + forbidden transitions.

### Step `2.06` — `Section 8` Surface Inventory & Feature/Flow Queue (`Ref: step-02c-surfaces-features-flows.md`) `[GATE]`
1. Read `step-02c` (§1); confirm `#surf-*` checklist, single-phase `#feat-*` list (`P5`), and `#flow-*` list via `AskUserQuestion`.
2. Populate `Section 8`, register `feature-batch` (`1–3`/batch) + `flow-batch` (`1–2`/batch) queues + `TaskCreate`, mint `DC-NNN`, and complete `2.06`.
- *`done when`:* `Section 8` contains `#surf-*` rows without `#surf-example-create`.

### Step `2.07` *(Loop: `feature-batch`)* — Domain 6: BDD Features (`Ref: step-02c §2`) `[GATE]`
1. Resolve open business/auth/failure rules for active `#feat-*` batch via `AskUserQuestion`.
2. Write `Section 9` `#feat-*` blocks (single Phase, initial `R2` `IFF` trace, `Given/When/Then` Happy + Failure + Empty-State BDD, Verification Strategy when complex), sync new `#surf-*` to `Section 8`, mint `DC-NNN`, and complete `2.07`.
- *`done when`:* `Section 9` defines `#feat-*` BDD blocks without `#feat-example`.

### Step `2.08a` *(Loop: `flow-batch`, Gate A)* — Domain 7: Happy Path & Exception Pruning (`Ref: step-02c §3`) `[GATE]`
1. Draft `Actors`, `Trigger (#surf-*)`, `Preconditions`, and numbered **Happy Path** steps in `Section 10`.
2. Propose candidate Alternate + Exception branches via `AskUserQuestion` so the user prunes irrelevant branches **before** writing recovery prose, mint `DC-NNN`, and complete `2.08a`.
- *`done when`:* `Section 10` contains `#flow-*` Happy Path steps.

### Step `2.08b` *(Loop: `flow-batch`, Gate B)* — Domain 7: Surviving Exceptions & Postconditions (`Ref: step-02c §3`)
1. Write numbered recovery steps strictly for surviving branches + explicit Happy/Exception rollback **Postconditions** in `Section 10`.
2. Complete `2.08b` (cycles to `2.08a` for next `flow-batch`, else advances to `2.09`).
- *`done when`:* `Section 10` defines `#flow-*` Postconditions without `#flow-example`.

### Step `2.09` — Domains 8, 10, 11 & Conditional `R6`/`R7` (`Ref: step-02d-integrations-and-conditionals.md`) `[GATE]`
1. Read `step-02d`; skip via `--skip-reason` if all conditional domains were excluded in `1.3`.
2. Otherwise elicit included specs (`Retention`, `R6` collision + reserved literals, `R7` 7-point session continuity, `#int-*` failure matrix, or 7-part migration) via `AskUserQuestion` (`<= 4` questions/call), edit `Sections 7 & 12`, mint `DC-NNN`, and complete `2.09`.
- *`done when`:* `0` sections remain `"pending"` in ledger.

### Step `2.10` — Domain 9 Batch A: Mandatory `SEC`, `PERF`, `LOG` + `SCALE` (`Ref: step-02e-nfr-core-batch-a.md`) `[GATE]`
1. Read `step-02e`; ask `4` `AskUserQuestion` cards for `SEC-1..7`, `PERF-1..5`, `LOG-1..5` (mandatory) and `SCALE-1..5` vs explicit skip.
2. Record via `set-nfr` + `add-dc`, write `Section 13.1–13.4` (5 numeric metrics if `SCALE` active; tag unconfirmed presets `[DRAFT — archetype default]`), and complete `2.10`.
- *`done when`:* `SEC`, `PERF`, `LOG`, `SCALE` all `!= "unconfirmed"`.

### Step `2.11` — Domain 9 Batch B: Conditional `A11Y`, `OBS`, `I18N`, `PRIV` & `§7.4` Tables (`Ref: step-02f-nfr-conditional-batch-b.md`) `[GATE]`
1. Read `step-02f`; ask `4` `AskUserQuestion` cards for `A11Y-1..5`, `OBS-1..4`, `I18N-1..4`, `PRIV-1..4` (each with explicit skip option).
2. Record via `set-nfr` + `add-dc`, write `Section 13.5–13.8` **including `#nfr-observability-components` (`OBS-2+`) and `#nfr-pii-inventory` (`PRIV-2+`)**, and complete `2.11`.
- *`done when`:* All 8 NFRs settled and `OBS-2+` / `PRIV-2+` sub-tables present.

### Step `2.12` — `R4` Day-Zero Bootstrap Draft & Anti-Patterns (`Ref: step-03-deep-dive-and-audits.md` §1) `[GATE]`
1. Read `step-03` (§1); trace `#boot-01..#boot-NN` from `0` DB rows to every actor role and confirm `[SEED]` mechanism via `AskUserQuestion`.
2. Populate `Section 11` and `Section 14`, mint `DC-NNN`, and complete `2.12`.
- *`done when`:* `Section 11` defines `#boot-01`+ rows without `#surf-example-create`.

### Step `2.13` — Phase 2 Scaffold Exit Audit
1. Run `audit-fds.sh "<spec_path>" --phase scaffold --ledger "<ledger>"`, fix any structural finding until exit `0`, and complete `2.13`.
- *`done when`:* `--phase scaffold` exits `0`.

---

## Phase 3 — Weakness-Ranked Deep-Dive (`Ref: references/step-03-deep-dive-and-audits.md`)

### Step `3.01` — Weakness Ranking & Triage Approval `[GATE]`
1. Run `audit-fds.sh "<spec_path>" --phase deep-dive-plan --ledger "<ledger>"`, confirm priority order via `AskUserQuestion`, register `weakness-object-batch` / `weakness-feature-batch` queues + `TaskCreate`, mint `DC-NNN`, and complete `3.01`.
- *`done when`:* Deep-Dive priority triage confirmed.

### Step `3.02` *(Loop: `weakness-object-batch`)* — 6-Category Sweep, `R8` & `R1`/`R3` Pass 2 `[GATE]`
1. Audit active `#obj-*` batch across all 6 failure categories + 4-part `R8` Auth Propagation + `R8` quantitative alignment + `R1`/`R3` Pass 2 via `AskUserQuestion`.
2. Replace `[DRAFT — scaffold]` stubs in `Sections 5–7`, mint `DC-NNN`, and complete `3.02`.
- *`done when`:* `0` `[DRAFT — scaffold]` stubs remain in `Section 5`.

### Step `3.03` *(Loop: `weakness-feature-batch`)* — `R2` `IFF` Authz Audit & BDD Hardening `[GATE]`
1. Verify every gated `#feat-*` carries an `IF-AND-ONLY-IF` (`IFF`) trace mapped to `#surf-*` / `[SEED: #boot-*]`; resolve any `[BLOCKED]` gap via `AskUserQuestion`, update `Sections 8–9`, mint `DC-NNN`, and complete `3.03`.
- *`done when`:* `Section 9` has `0` `[BLOCKED]` markers.

### Step `3.04` — Flows, Integrations & NFR Draft Hardening `[GATE]`
1. Confirm/customize remaining `[DRAFT — archetype default]` NFR rows and integration retry/idempotency contracts via `AskUserQuestion`, update `Sections 10/12/13` (`set-nfr --status confirmed`), mint `DC-NNN`, and complete `3.04`.
- *`done when`:* Active NFRs and flow/integration failure rules hardened.

### Step `3.05` — `R4` Day-Zero Bootstrap End-to-End Verification
1. Verify `#boot-01..#boot-NN` satisfies every role's `R2` preconditions from `0` DB rows with zero circularity, set `Status = Confirmed`, and complete `3.05`.
- *`done when`:* `Section 11` has `0` `[BLOCKED]` markers.

### Step `3.06` — `R5` Backend/Surface Parity Exit Audit `[GATE if orphans]`
1. Run `audit-fds.sh "<spec_path>" --phase r5-parity --ledger "<ledger>"`; resolve any `[ORPHAN-CAPABILITY]` / `[BLOCKED]` item via `AskUserQuestion` (`Add #surf-*`, `Defer Phase`, `Remove`, or `[CUSTOM: ... because ...]`) until exit `0`, then complete `3.06`.
- *`done when`:* `--phase r5-parity` exits `0`.

---

## Phases 4–6 — Review, Finalize & Retrospective (`Ref: references/step-04-review-finalize-retro.md`)

### Step `4.1` — Residual `[DRAFT]` Inventory & Clean-Section Sign-Off
1. Read `step-04` (§1), run `audit-fds.sh "<spec_path>" --phase review --ledger "<ledger>"`, emit `<Section>: all confirmed, moving on.` for zero-draft sections, and complete `4.1` (auto-skips `4.2` to `5.1` if `0` `[DRAFT]` tags remain).
- *`done when`:* Residual `[DRAFT]` count inventoried.

### Step `4.2` — Batched Residual `[DRAFT]` Resolution Loop `[GATE]`
1. Resolve `1–4` `[DRAFT — ...]` items/turn via `AskUserQuestion` (`Confirm` → strip tag | `Replace` → edit + `DC-NNN` | `Accept` → `[ACCEPTED-AS-DRAFT] — Implementation may require clarification` + `Appendix A`) until `--phase review` shows `0` `[DRAFT]` tags, then complete `4.2`.
- *`done when`:* `0` raw `[DRAFT]` tags remain.

### Step `5.1` — Canonical 16-Section Assembly & Finalize Gate
1. Sync `Section 1` (`Status: Finalized`, metrics), `Section 2` TOC, `Section 3` Executive Summary, and `Section 15` Changelog; run `audit-fds.sh "<spec_path>" --phase finalize --ledger "<ledger>"` and fix any finding (`step-04` §2–§3) until exit `0`, then complete `5.1`.
- *`done when`:* `--phase finalize` exits `0`.

### Step `5.2` — Finalized Spec Delivery & Optional `D12` Stream `[GATE]`
1. Confirm on-disk delivery vs optional `D12` chunked in-chat streaming via `AskUserQuestion` (pausing per chunk if streamed), then complete `5.2`.
- *`done when`:* Delivery acknowledged by user.

### Step `6.1` — `D8` Friction Clustering & Calibration Retrospective (`§10`) `[GATE]`
1. Run `fds-state.sh friction-report --ledger "<ledger>"`, review clustered findings via `AskUserQuestion` (bounded `§10.4` proposals only for `>= 2` or structural clusters), and run `complete-step 6.1`.
- *`done when`:* Session marked `100%` complete in `fds-state.sh` and `TaskUpdate`.
