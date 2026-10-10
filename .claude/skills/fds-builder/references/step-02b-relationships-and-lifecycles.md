# Step 02B — Central Relationship Map (`R1`, `R3`) & State Machine Lifecycles (`D4`)

Load **only** during **Steps `2.04–2.05`**.

---

## 1. Central Relationship Map (`Step 2.04`, Section 6, `D5`)

Populate `Section 6` with the canonical **7-column Relationship Map** followed by a concise prose **Relationship Narrative** explaining multi-hop domain invariants:

```markdown
| Object A | Cardinality | Object B | Relationship Name | Constraints (`on_delete` required) | Data-Carrying? | Surface Coverage |
|---|---|---|---|---|---|---|
| [#obj-user](#obj-user) | N:M | [#obj-project](#obj-project) | ProjectMembership ([#obj-project-membership](#obj-project-membership)) | unique(user, project); on_delete(user: CASCADE, project: CASCADE); min 1 active owner per project | Yes (`role`, `invited_by`, `joined_at`) | Create: [#surf-member-add](#surf-member-add); List: [#surf-project-members](#surf-project-members); Remove: [#surf-member-remove](#surf-member-remove); Inverse-View: [#surf-user-projects](#surf-user-projects) |
```

---

## 2. `R1` — Junction Object & 4-Surface Promotion Audit (`Step 2.04`, `D18`)

Whenever **Cardinality is `N:M` (`M:N`)** OR **`Data-Carrying?` is `Yes`** (link stores `role`, `status`, `quantity`, `sort_order`, `effective_from`, `approved_by`, etc.):

1. **Promote to First-Class `#obj-*`:** Add a full `#obj-<junction>` block to `Section 5` with its own 6-column `D3` attribute table, constraints, and `D20` empty states.
2. **Elicit All 4 Link Surfaces via `AskUserQuestion` (`STOP & WAIT`):**
   - **Creation (`Associate`):** Which `#surf-*` (or `[SEED: #boot-*]`) creates the link?
   - **Listing (`Forward View`):** Given Object A, which `#surf-*` lists linked Object Bs?
   - **Removal (`Disassociate`):** Which `#surf-*` removes/revokes the link — or `[CUSTOM: immutable link because <rationale>]`?
   - **Inverse-View (`Reverse Lookup`):** Given Object B, which `#surf-*` lists linked Object As — or `[CUSTOM: inverse view omitted because <rationale>]`?

*(Any unexcused missing link surface becomes `[ORPHAN-CAPABILITY]` at Step `3.06`.)*

---

## 3. `R3` — Cross-Object Referential & Deletion Integrity (`Step 2.04`, Sections 6–7)

Every relationship row in `Section 6` (and every `reference(#obj-*)` attribute in `Section 5`) MUST declare an explicit `on_delete` rule inside `Constraints` — confirmed via `AskUserQuestion` whenever audit history or child records could conflict with deletion:

- **`CASCADE`:** Child/junction records delete atomically with parent in one transaction.
- **`RESTRICT`:** Parent deletion rejected with verbatim error copy while dependent child records exist (e.g., `"Cannot delete project '{name}' because {count} issued invoices reference it. Archive the project instead."`).
- **`SET_NULL`:** Nullable foreign key cleared to `null`; historical child row preserved.
- **`SOFT_ARCHIVE`:** Hard `DELETE` prohibited; parent transitions to terminal/archived state (`D4`) with explicit child visibility and edit-lock rules documented in `Section 7` (`#cstr-*`).

---

## 4. Domain 4 (`D4`) — State Machine Lifecycles (`Step 2.05` Per Stateful Batch)

1. **Classify Stateful vs Stateless Objects:**
   - If an object's attributes never gate allowed mutations, transitions, or visibility, mark its `Lifecycle & State Machine` subsection in `Section 5`: `None — stateless value/reference record because attributes never gate allowed operations.`
   - Register stateful object batches (`1–2` stateful objects per batch) via `fds-state.sh register-items --kind stateful-batch --items "..."` (if `0` stateful objects exist, complete `2.05` with `--skip-reason "All objects confirmed stateless in DC-NNN"`).
2. **Elicit Guards, Terminal Locks & Forbidden Transitions (`AskUserQuestion` -> `STOP & WAIT`):**
   - Common starter patterns (`Appendix B` — always present as selectable/customizable choices, never silent):
     - *Approval:* `draft` [initial] → `pending_review` → `approved` | `changes_requested` | `rejected` → `archived` [terminal]
     - *Async Job:* `queued` [initial] → `leased` → `succeeded` [terminal] | `retry_scheduled` | `dead_lettered` | `cancelled` [terminal]
     - *Membership:* `invited` [initial] → `active` → `suspended` → `revoked` [terminal] | `expired` [terminal]
3. **Author Complete 4-Part Lifecycle Contract in `Section 5`:**
   - **Valid State Set:** Closed enum identifying `[initial]` and `[terminal]` state(s).
   - **Legal Transition Table:**
     `| From State | To State | Trigger (#surf-* / Job) | Deterministic Guard Condition | Post-Transition Side Effects |`
   - **Forbidden Transitions + Rationale (`D4` Mandatory — `>= 1` row required on every stateful object):**
     `| Attempted From -> To | Exact Rejection Error Message | Rationale (because ...) |`
   - **State-Dependent Field Mutability:** Exact list of fields editable vs frozen in each state (especially terminal edit-locks).
