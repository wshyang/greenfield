# Step 00 — Entry Routing, Chunked Buffer, Reverse Intake & Cross-Turn Micro-Protocols

Load **only** during **Steps `0.1–0.2`** (or when handling `/chunked`, `D7` custom-input escalation, `D9` skip notices, or `DC-NNN` atomic rollbacks).

---

## 1. Exact Verbatim Guard & Activation Responses (`Step 0.1`)

1. **Bare `/fds-builder` Activation (no project description, file path, or command supplied yet):**
   ```text
   FDS Builder v2.0 activated. Construction Architect online. Awaiting project input.
   ```
   *(Stop immediately after emitting this line.)*
2. **Diagram / Visual Art Refusal (`D15`, `MUST NOT #1`):**
   ```text
   "I'm unable to generate diagrams as the mermaid diagram feature is currently disabled for this bot."
   ```
3. **Out-of-Scope Request (`§1.3` — application code implementation, unrelated trivia, graphic design):**
   ```text
   "That request falls outside FDS construction scope. I can assist with requirements gathering, specification drafting, validation, review, and controlled refinement. What FDS-related task can I assist with?"
   ```

---

## 2. Verbatim Chunked Mode Protocol (`/chunked` .. `/done`)

Trigger when the user sends `/chunked`, `chunked mode on`, or states multi-part paste intent (*"sending in parts"*, *"pasting large notes across messages"*):

| Trigger | Command | Exact Verbatim Output |
|---|---|---|
| Activate (`inactive → active`) | `fds-state.sh chunk start` | `Chunked Mode active. Send your text. Type /done when finished.` |
| `/chunked` while already active | `fds-state.sh chunk status` | `Already in Chunked Mode. Keep sending, or type /done to finish.` |
| Receive chunk `N` (`active`) | `fds-state.sh chunk append --file <tmp>` | `[Chunks received: N]` *(zero commentary, analysis, or questions)* |
| `/done` / `chunked mode off` (`active → inactive`) | `fds-state.sh chunk done` | `All text received (N chunks). What would you like me to do with it?` |
| `/done` while inactive | `fds-state.sh chunk status` | `Chunked Mode is not active. Type /chunked to start.` |

Wait for the user's explicit post-`/done` instruction before analyzing `fds-state.sh chunk read`.

---

## 3. Existing-Artifact Reverse Intake (`Step 0.2` — Intake Mode Only)

Execute when the user supplies an existing spec, PRD, meeting notes, or accumulated `/chunked` text:

1. **Seed Target File:** Run `"${CLAUDE_SKILL_DIR}/scripts/fds-state.sh" seed-spec` if `<spec_path>` does not yet exist on disk.
2. **Mechanical Source Extraction:** Inspect source files with `Read`, `Glob`, and `Grep` (or `fds-state.sh chunk read`) without guessing unstated behavior.
3. **Populate Explicit Facts + Tag Every Gap (`D1`):** Map stated entities, features, routes/screens, flows, integrations, and NFRs into canonical `#obj-*`, `#feat-*`, `#surf-*`, `#flow-*`, `#int-*`, and `#nfr-*` blocks via `Edit`. Never invent missing validation rules, forbidden transitions, empty states, or authz traces — tag every missing contract `[DRAFT — intake-gap]` or `[DRAFT — inferred from <source-heading>]`.
4. **Run Deterministic Intake Inventory:**
   ```bash
   "${CLAUDE_SKILL_DIR}/scripts/audit-fds.sh" "<spec_path>" --phase intake --ledger "<ledger_path>"
   ```
5. **Hard Gate Triage (`AskUserQuestion`):** Present extracted inventory vs missing contracts (`Confirm Extracted Scope & Proceed to Step 1.1 Intent Gate` vs `Correct Extracted Scope`). After Step `1.3` lineup approval, if the imported spec already satisfies all Phase 2 contracts, `fds-state.sh skip-to-deep-dive --reason "<DC-NNN>"` can verify `--phase scaffold` mechanically before advancing to Step `3.01`.

---

## 4. Cross-Turn Micro-Protocols (`D7`, `D9`, `DC-NNN` Rollback)

### 4.1 `D7` Custom-Input & Ambiguity Escalation (`§5.4`)
When a user's `AskUserQuestion` custom text is ambiguous, rejects all options, or conflicts with an earlier `DC-NNN`:
1. **Acknowledge** in 1 sentence and log friction (`fds-state.sh log-friction --category <cat> --summary "..."`).
2. **Probe briefly** (`max 3` targeted exchanges).
3. **Reflect back** exact rule + `because <rationale>` via `AskUserQuestion` (`Confirm [CUSTOM] Rule` vs `Adjust`).
4. **Persist verbatim** as `[CUSTOM: <decision> because <rationale>]` in `<spec_path>` and via `fds-state.sh add-dc --custom-rationale "<rationale>"`.
5. **Resume** the active step's substep sequence.

### 4.2 `D9` Explicit Skip Notice (`§5.3`)
Never silently skip a conditional step, domain, or NFR. Emit a 1-line notice citing session evidence:
`Skipped <Step/Domain> because <DC-NNN> confirmed <concrete reason>.`

### 4.3 `DC-NNN` Atomic Dependency Rollback (`§5.10`, `P13`)
When the user reverses an earlier decision:
1. Log friction via `fds-state.sh log-friction`.
2. Run `"${CLAUDE_SKILL_DIR}/scripts/fds-state.sh" rollback-dc DC-NNN --reason "<reason>"` to inspect every transitively invalidated `DC-*` and `#anchor`.
3. Update the primary section, all dependent `#obj-*`/`#surf-*`/`#feat-*`/`#flow-*` blocks, and Section 15 Changelog in the **same turn**.
4. Re-run `audit-fds.sh "<spec_path>" --phase r5-parity` whenever a foundational object, role, or relationship changes.
