# Step 02A — System Boundaries, Core Object Inventory & 6-Column Attribute Contracts

Load **only** during **Steps `2.01–2.03`**.

---

## 1. Semantic Anchor Prefix Standard (`D10`, `D14`, `§8.2–8.3`)

Every domain artifact across the FDS MUST define a deterministic kebab-case `{#anchor}` and be cross-linked via `[#anchor](#anchor)`:

| Artifact | Prefix | Definition Site | Example |
|---|---|---|---|
| Core / Junction Object | `#obj-` | `### 5.X Invoice {#obj-invoice}` | `[#obj-invoice](#obj-invoice)` |
| Surface (`UI/API/CLI/Job`) | `#surf-` | Section 8 `Anchor` column | `[#surf-invoice-issue](#surf-invoice-issue)` |
| Feature | `#feat-` | `### 9.X Issue Invoice {#feat-issue-invoice}` | `[#feat-issue-invoice](#feat-issue-invoice)` |
| User Flow | `#flow-` | `### 10.X Billing Run {#flow-billing-run}` | `[#flow-billing-run](#flow-billing-run)` |
| Cross-Object / `R6` / `R7` Rule | `#cstr-` | `### 7.X Rule {#cstr-invoice-balance}` | `[#cstr-invoice-balance](#cstr-invoice-balance)` |
| Day-Zero Bootstrap Step | `#boot-` | Section 11 `Step Anchor` column | `#boot-01` |
| External Integration | `#int-` | `### 12.X Gateway {#int-payment-gateway}` | `[#int-payment-gateway](#int-payment-gateway)` |
| NFR Category | `#nfr-` | `### 13.X Security {#nfr-security}` | `[#nfr-security](#nfr-security)` |
| Anti-Pattern | `#ap-` | Section 14 `ID` column | `#ap-01` |

---

## 2. Domain 1 — System Boundaries, Actors & Phase Scope (`Step 2.01`)

1. Confirm the **closed list of human and system actor roles**, explicit **in-scope vs out-of-scope boundaries**, and **`Phase 1` vs `Phase 2+` delivery split** via `AskUserQuestion` (`1–4` questions max; **STOP & WAIT**).
2. Update `Section 3` (`Target Actor Roles`, `Phase Delivery Summary`) and `Section 4` (`Phase Scope Summary` table) in `<spec_path>` via `Edit`, record `DC-NNN`, and run `fds-state.sh complete-step 2.01`.

---

## 3. Domain 2 — Core Object Inventory & Batch Registration (`Step 2.02`)

1. Propose the complete candidate `#obj-*` list (name, `#obj-<slug>`, 1-sentence responsibility, initial phase tag) via `AskUserQuestion` (`Confirm Object Inventory` vs `Split/Merge/Add Entities`; **STOP & WAIT**).
2. Group confirmed objects into **bounded batches of `1–3` tightly coupled objects** (never dump `5+` complex objects in a single unreviewed turn) and register them in both `fds-state.sh` and `TaskCreate`:
   ```bash
   "${CLAUDE_SKILL_DIR}/scripts/fds-state.sh" register-items --kind object-batch --items "#obj-org,#obj-user;#obj-invoice,#obj-line-item"
   "${CLAUDE_SKILL_DIR}/scripts/fds-state.sh" add-dc --phase "2.02" --summary "Locked core object inventory" --depends-on "DC-001"
   "${CLAUDE_SKILL_DIR}/scripts/fds-state.sh" complete-step 2.02
   ```

---

## 4. Domain 3 & `D20` — 6-Column Attribute Contracts & 4 Empty States (`Step 2.03` Per Batch)

For the active object batch (`fds-state.sh current-step` shows `batch k/N`), ask `1–4` `AskUserQuestion` cards to settle ambiguous uniqueness scopes, mutability locks, validation bounds, and list/selector exposure (**STOP & WAIT**), then write all **8 mandatory subsections** per `#obj-*` in `Section 5`:

1. **Header:** `### 5.X <Object Name> {#obj-<slug>}`
2. **Phase & Responsibility:** Single baseline phase + 1–2 sentence domain ownership.
3. **Attributes Table (`D3` — exact 6 columns, ZERO blank cells):**
   `| Attribute | Type | Phase | Constraints | Validation Rule | Error Message |`
   - **Types (`§6.2`):** `uuid`, `string(min:1, max:120)`, `decimal(12,2)`, `integer(min:0, max:10000)`, `boolean`, `timestamp(utc, iso8601)`, `enum(a|b|c)`, `reference(#obj-parent)`.
   - **Constraints:** `required` / `optional(default: ...)`, `immutable after creation`, `unique(scope: #obj-org)`, `indexed`.
   - **Validation Rule (`Appendix D`):** Deterministic predicate (`trim(value) length in 3..80 AND matches ^[A-Za-z0-9 _-]+$`) or numbered multi-clause invariant (`1. amount > 0.00; 2. currency == #obj-account.currency`). Never write `"valid email"` or `"standard validation"`.
   - **Exact Error Message (`Appendix E`):** Verbatim actionable string — never `"Invalid input"`:
     - *Format/Bounds:* `"Workspace name must be 3 to 80 characters and contain only letters, numbers, spaces, hyphens, or underscores."`
     - *Conflict:* `"An active workspace slug '{slug}' already exists in this organization. Choose a different slug."`
     - *Auth (`404` vs `403`):* State exact message and whether non-members receive `404` (anti-enumeration) or `403`.
4. **Lifecycle & State Machine (`D4`):** Initial `[DRAFT — lifecycle settled in Step 2.05]` or `None — stateless value record because attributes never gate allowed operations.`
5. **Relationships Summary:** Outbound/inbound references (linked in Step `2.04`).
6. **Edge & Failure Modes (`§6.6`):** Seed 6-row table (`Boundary`, `Invalid Input`, `Adversarial`, `Concurrency`, `Dependency Failure`, `R8 Auth Propagation`) tagged `[DRAFT — scaffold]` for Deep-Dive Step `3.02`.
7. **Empty States (`D20`):** Required whenever the object can appear in any list, table, search, dropdown, or inverse view (otherwise write `Not applicable — never rendered in a list, search, dropdown, or collection.`). Define all **4 variants**:
   - **`loaded-zero`:** Query succeeded, records exist, `0` match filter — exact copy + clear-filter CTA.
   - **`zero-permission`:** Caller lacks role/scope — exact non-leaking copy + access-request guidance.
   - **`zero-day-zero`:** Tenant/scope has `0` records yet — exact onboarding copy + create `#surf-*` CTA (if permitted) vs read-only copy.
   - **`loading-error`:** Upstream/fetch failure — exact copy, correlation ID display rule, and filter-preserving retry CTA.
8. **Notes & Design Rationale:** `[DC-NNN]` / `[CUSTOM: ... because ...]` traceability.
