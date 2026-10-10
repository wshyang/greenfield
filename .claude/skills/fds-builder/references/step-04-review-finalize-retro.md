# Step 04 — Residual `[DRAFT]` Review, Canonical 16-Section Finalize & Friction Retrospective

Load **only** during **Steps `4.1–4.2`, `5.1–5.2`, and `6.1`** (or when fixing banned-fluff / representation findings flagged by `audit-fds.sh`).

---

## 1. Phase 4 — Residual `[DRAFT]` Inventory & Resolution (`Steps 4.1–4.2`, `§4.4`)

1. **Deterministic Sweep (`Step 4.1`):**
   ```bash
   "${CLAUDE_SKILL_DIR}/scripts/audit-fds.sh" "<spec_path>" --phase review --ledger "<ledger_path>"
   ```
   - For every included section with **`0` `[DRAFT]` tags**, state explicitly: `<Section Name>: all confirmed, moving on.`
   - If total remaining `[DRAFT]` count is `0`, `fds-state.sh complete-step 4.1` automatically marks `4.2` skipped (`D9`) and advances to `Step 5.1`.
2. **Batched Confirmation (`Step 4.2`, `1–4` Drafts per `AskUserQuestion` Turn -> `STOP & WAIT`):**
   - Offer three choices per `[DRAFT — ...]` item: **(a) Confirm Draft Value** (strip `[DRAFT — ...]`), **(b) Replace Value** (write user's exact rule + `DC-NNN`), or **(c) Acknowledge Open Item** (replace with exact string `[ACCEPTED-AS-DRAFT] — Implementation may require clarification` and list in `Section 16 Appendix A`).
   - Repeat `1–4` items per turn until `audit-fds.sh "<spec_path>" --phase review` reports `0` raw `[DRAFT]` tags.

---

## 2. Phase 5 — Canonical 16-Section Assembly & Delivery (`Steps 5.1–5.2`, `§4.5`)

### 2.1 Exact 16-Section Canonical Order (`Step 5.1`)
`1. Metadata` → `2. Table of Contents` → `3. Executive Summary` → `4. Phase Scope Summary` → `5. Core Objects` → `6. Central Relationship Map` → `7. Cross-Object Constraints, Collision & Session Rules` → `8. Surface Inventory` → `9. Features` → `10. User Flows` → `11. Day-Zero Bootstrap Sequence` → `12. External Integrations & Data Migration` → `13. Non-Functional Requirements` → `14. Anti-Pattern Register` → `15. Changelog` → `16. Appendices`.

- Sync `Section 1` (`Status: Finalized`, `Date`, `Session Metrics` counts), `Section 2` TOC links, `Section 3` Executive Summary, and `Section 15` Changelog (`DC-001..DC-NNN`).
- Run `"${CLAUDE_SKILL_DIR}/scripts/audit-fds.sh" "<spec_path>" --phase finalize --ledger "<ledger_path>"` and fix every finding until exit code **`0` (`PASS`)**.

### 2.2 Delivery & Optional `D12` Chunked In-Chat Stream (`Step 5.2` Hard Gate)
Present the passing `finalize` audit summary + `<spec_path>` via `AskUserQuestion` (`Accept On-Disk Finalized FDS` vs `Also Stream Sections In-Chat per D12`; **STOP & WAIT**). If streaming in chat (`D12`), emit logical section groups (`1–4`, `5–7`, `8–11`, `12–16`), pausing after each chunk for user acknowledgment and recording any last-mile tweak as a new `DC-NNN` before continuing.

---

## 3. Representation Rules & Banned Fluff Lexicon (`D15–D17`, `MUST NOT #6`)

Enforced continuously by the `PostToolUse` hook and at `--phase finalize`:

1. **`D15` Zero Diagrams:** No `mermaid`/`plantuml`/`graphviz`/`d2`/SVG, Unicode box characters (`┌ ─ ┐ │ └ ┘`), or ASCII box arrows (`+---+` / `-->`).
2. **`D16` Language-Agnostic Pseudocode Only:** No fenced code blocks tagged `python`, `ts`, `typescript`, `js`, `go`, `rust`, `java`, `sql`, `bash`, `sh`, `tsx`, `csharp`, `ruby`, or `php`. Use tables, prose, or ```` ```pseudocode ```` / ```` ```text ````.
3. **`D17` Synthetic Examples Only:** Use `@example.com` / `@acme.invalid`, fictional names, and synthetic IDs (`usr_01J9EXAMPLE01`).
4. **Banned Vague Phrases (Replace Deterministically):**
   - `"must scale"` / `"highly scalable"` → 5 numeric `SCALE-*` metrics (`RPS`, horizon, burst, concurrency, cost ratio).
   - `"user stays logged in"` / `"remains logged in"` → 7-part `R7` Session Continuity spec.
   - `"handle gracefully"` / `"fail gracefully"` → exact status, rollback guarantee, retry CTA, and error string.
   - `"appropriate error message"` / `"clear error"` → exact quoted error copy (`D3`).
   - `"seamless"` / `"intuitive"` / `"user-friendly"` / `"modern UI"` → concrete step count, `A11Y` focus rule, `PERF` target, or `D20` CTA.
   - `"fast response"` / `"real-time"` *(unqualified)* → `p50/p95/p99` ms (`PERF-*`) or `<= N s` propagation ceiling.
   - `"as needed"` / `"if appropriate"` / `"where applicable"` / `"etc."` / `"standard validation"` → closed enum or `IF <predicate> THEN ...` rule.

---

## 4. Phase 6 — Post-Delivery Friction Retrospective (`Step 6.1`, `§10`)

1. Run `"${CLAUDE_SKILL_DIR}/scripts/fds-state.sh" friction-report --ledger "<ledger_path>"` to cluster logged `D8` friction across the 7 root-cause buckets (`terminology`, `structure`, `scope`, `granularity`, `surface_gaps`, `auth_complexity`, `bootstrap_complexity`).
2. Present the clustered summary via `AskUserQuestion` (`Confirm Retrospective & Close Session` vs `Record Missed Friction / Bounded Preset Calibration`; **STOP & WAIT**).
3. Propose bounded calibration (`question phrasing`, `template starter`, `archetype default`) **only** when a cluster occurred `>= 2` times or exposed a structural gap (`§10.4`) — never altering `D1–D21` tags, `#anchor` prefixes, or `R1–R8` audit gates (`§10.5`). Complete `Step 6.1` via `fds-state.sh complete-step 6.1`.
