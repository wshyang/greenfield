# Step 02C — Surface Inventory, BDD Feature Specs & Two-Gate User Flows

Load **only** during **Steps `2.06–2.08b`**.

---

## 1. Surface Inventory Baseline & Feature/Flow Queue Lock (`Step 2.06`, Section 8)

1. Synthesize every UI screen/modal, API endpoint, webhook receiver, CLI command, and scheduled/background job implied by `Sections 4–6` into candidate `#surf-*` entries, alongside candidate `#feat-*` capabilities (**strictly one Phase tag per `#feat-*` per `P5`** — split multi-phase capabilities into separate `#feat-*` blocks) and `#flow-*` actor journeys.
2. Confirm the surface/feature/flow inventory via `AskUserQuestion` (`Confirm Inventory` vs `Add/Defer Surfaces or Features`; **STOP & WAIT**).
3. Populate `Section 8` (`Surface Inventory`) using the canonical 7-column table (`§9.4`):
   ```markdown
   | # | Surface | Anchor | Permitted Roles | Target Object / Relationship | CRUD / Associate | Phase |
   |---|---|---|---|---|---|---|
   | 1 | Issue Invoice Action | `#surf-invoice-issue` | `finance_manager`, `org_owner` | `#obj-invoice` (`draft -> issued`) | Update (Transition) | Phase 1 |
   ```
4. Register bounded batches (`1–3` features per batch; `1–2` flows per batch) in `fds-state.sh` + `TaskCreate`:
   ```bash
   "${CLAUDE_SKILL_DIR}/scripts/fds-state.sh" register-items --kind feature-batch --items "#feat-create-invoice,#feat-issue-invoice;#feat-void-invoice"
   "${CLAUDE_SKILL_DIR}/scripts/fds-state.sh" register-items --kind flow-batch --items "#flow-monthly-billing;#flow-dispute-refund"
   "${CLAUDE_SKILL_DIR}/scripts/fds-state.sh" complete-step 2.06
   ```

---

## 2. Domain 6 — Feature Specifications & BDD Acceptance (`Step 2.07` Per Feature Batch)

For the active `#feat-*` batch (`1–3` features):
1. Ask `1–4` `AskUserQuestion` cards to resolve open business calculation rules, role/ownership gates, idempotency, or failure copy (**STOP & WAIT**).
2. Author each `### 9.X <Feature Name> {#feat-<slug>}` block in `Section 9` containing:
   - **Phase:** Single phase tag (`Phase 1` — never `Phase 1 / Phase 2`).
   - **Involved Objects & Surfaces:** Linked `[#obj-*](#obj-*)` and `[#surf-*](#surf-*)` anchors (adding any newly discovered `#surf-*` to `Section 8` in the same edit).
   - **Preconditions & User Stories.**
   - **Authorization Derivation Trace (`R2`, `D19`):** Whenever gated by role, membership, or ownership, write an `IF-AND-ONLY-IF` (`IFF`) predicate chaining `#obj-*` attributes/links and citing the `#surf-*` or `[SEED: #boot-*]` that populates each link (hardened in Step `3.03`).
   - **BDD Acceptance Criteria (`§5.8` — numbered `Given / When / Then`):**
     1. **Happy Path:** Valid actor input → deterministic mutation → exact visible confirmation.
     2. **Validation / Guard / Auth Failure Path:** Exact rejection error string + zero partial state write.
     3. **Empty-State Path (`D20`):** Mandatory whenever the feature lists, searches, or filters records.
   - **Verification Strategy *(mandatory when feature involves concurrency, money/math, multi-step workflow, external callback, or security boundary)*:** `Test Type` | `Key Scenarios` | `Synthetic Data Needs (D17)` | `Stubbing / Environment Dependencies`.

---

## 3. Domain 7 — Two-Gate User Flow Construction (`Steps 2.08a` & `2.08b`, `§5.7`, Section 10)

**Never write full exception-recovery prose before letting the user prune the exception list (`§5.7`).** Every `#flow-*` batch executes across **two distinct gated substeps**:

### Step `2.08a` — Happy Path Lock & Candidate Alternate/Exception Pruning *(HARD GATE 1)*
1. Draft the flow header (`Actors`, `Trigger [#surf-*]`, `Preconditions`) and **numbered Happy Path steps** (`Actor Action -> #surf-* -> Validation & #obj-* Mutation -> Visible Response`) in `Section 10`.
2. Propose the candidate list of **Alternate Paths** (including empty-state alternate when applicable) and **Exception Paths** (validation failure, concurrent-edit race, upstream timeout, mid-flow role/session loss) via `AskUserQuestion` so the user selects which branches apply vs prune (**STOP & WAIT**).
3. Record pruning `DC-NNN` and run `fds-state.sh complete-step 2.08a`.

### Step `2.08b` — Surviving Alternate/Exception Recovery & Postconditions
1. Write numbered recovery steps **strictly for the user-confirmed surviving Alternate & Exception branches** in `Section 10` (ask a follow-up `AskUserQuestion` `*(HARD GATE)*` only if a surviving exception's compensation/retry policy is still ambiguous).
2. Write **Explicit Postconditions per Path** (`Happy Path` persisted `#obj-*` states + side effects; `Exception Paths` explicit rollback / zero-partial-mutation guarantee).
3. Run `fds-state.sh complete-step 2.08b` (cycles to next `flow-batch` at `2.08a` if more batches remain, else advances to `2.09`).
