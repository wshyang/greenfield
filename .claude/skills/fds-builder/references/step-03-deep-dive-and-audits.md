# Step 03 — `R4` Day-Zero Bootstrap, Weakness-Ranked Deep-Dive & `R2`/`R5`/`R8` Audits

Load **only** during **Step `2.12`** and **Steps `3.01–3.06`**.

---

## 1. `R4` — Day-Zero Bootstrap Sequence (`Step 2.12` Draft & `Step 3.05` Verification, Section 11)

**Always Critical (`weight = 3`, `D21`):** Trace the deterministic path from an **empty database (`0` rows)** to the first usable workflow for **every actor role**:

```markdown
| Step Anchor | Order | Actor | Surface or `[SEED]` Mechanism | Object / Relationship Populated | Capability / Role Unlocked | Status |
|---|---|---|---|---|---|---|
| `#boot-01` | 1 | System Installer | `[SEED]` CLI command reading `BOOTSTRAP_ADMIN_EMAIL` | `#obj-user` (`status=active`, `global_role=super_admin`) | Unlocks `[#surf-admin-login](#surf-admin-login)` | Confirmed |
| `#boot-02` | 2 | Super Admin | `[#surf-org-create](#surf-org-create)` | `#obj-org` + `#obj-org-membership` (`role=org_owner`) | Unlocks tenant admin surfaces | Confirmed |
```

- **Zero Circular Dependencies:** Never require Role `X` to invoke `#surf-create-X` unless `#boot-01` seeds the initial holder via an explicit `[SEED]` mechanism (CLI command, env bootstrap, or idempotent startup seed). Flag any missing link `[BLOCKED — missing bootstrap surface for <role>]` and resolve via `AskUserQuestion` (**STOP & WAIT**).

---

## 2. Weakness-Ranked Deep-Dive Triage (`Step 3.01`, `§4.3` Entry)

1. Run `"${CLAUDE_SKILL_DIR}/scripts/audit-fds.sh" "<spec_path>" --phase deep-dive-plan --ledger "<ledger_path>"` (`priority = draft_count * section_weight`, `Critical = 3`, `[BLOCKED]` items first).
2. Present the ranked priority order via `AskUserQuestion` (`Approve Priority Order` vs `Reorder Focus`; **STOP & WAIT**), register object/feature batches via `fds-state.sh register-items`, and create granular Deep-Dive tasks via `TaskCreate`.

---

## 3. 6-Category Defensive Sweep, `R8` Auth Propagation & `R1`/`R3` Pass 2 (`Step 3.02` Per Object Batch)

For each `#obj-*` batch in weakness order, replace `[DRAFT — scaffold]` stubs by auditing all **6 mandatory failure categories (`§6.6`)** + `R1`/`R3` Pass 2 consistency (confirming policy forks via `AskUserQuestion` -> **STOP & WAIT**):
1. **Boundary Conditions:** Min/max length, `0`/negative/ceiling numbers, empty collections, pagination page-size caps, UTC/timezone date boundaries.
2. **Invalid Input:** Malformed types, missing required fields, unknown enum values, broken `#obj-*` foreign refs, whitespace-only strings.
3. **Adversarial Input:** Cross-tenant IDOR `#obj-*` tampering, HTML/SQL/header injection strings, oversized payloads, enumeration/replay probes.
4. **Concurrency & Race Conditions:** Duplicate-submit idempotency keys, simultaneous state transition (`version` optimistic lock / row lock), concurrent unique-slug create race.
5. **Dependency Failure:** DB transaction rollback, queue/storage/webhook outage mid-operation (outbox/compensation atomicity rule).
6. **`R8` Authorization-Change Propagation (all 4 sub-items required when auth-scoped) + Quantitative NFR Alignment:**
   - **In-Flight Work:** Fate of open multi-step drafts or queued submissions when role/membership is revoked.
   - **Active Session:** Immediate session termination vs token refresh vs next-request scope strip.
   - **Auth Cache / Token TTL:** Per-write DB check vs bounded claim TTL (`<= N seconds`, aligned quantitatively with `PERF`/`SCALE` budgets).
   - **Propagation Window & Rationale:** Exact max delay + `because {reason}`.

---

## 4. `R2` Authorization Derivation Audit (`IFF`) & BDD Hardening (`Step 3.03` Per Feature Batch)

For every role-, membership-, or ownership-gated `#feat-*` in `Section 9`:
1. Write a complete **`IF-AND-ONLY-IF` (`IFF`)** predicate chaining concrete `#obj-*` attributes/junctions, citing the exact population `#surf-*` or `[SEED: #boot-*]` for **every** clause:
   ```text
   Actor (#obj-user U) may invoke #feat-approve-claim on #obj-claim C IF-AND-ONLY-IF:
     1. U.status == "active" (populated via #surf-user-activate or [SEED: #boot-01]); AND
     2. EXISTS #obj-org-membership M WHERE M.user == U.id AND M.org == C.org AND M.status == "active" (populated via #surf-invite-accept); AND
     3. M.role IN {"approver", "org_owner"} (populated via #surf-role-assign); AND
     4. C.submitted_by != U.id (self-approval guard).
   ```
2. If any clause lacks a population surface in `Section 8`, mark `[BLOCKED — missing population surface for <clause>]`, surface options via `AskUserQuestion` (**STOP & WAIT**), and resolve before completing `3.03`.

---

## 5. Flows, Integrations & NFR Draft Hardening (`Step 3.04`)

Confirm or customize remaining `[DRAFT — archetype default]` rows in `Section 13` (`fds-state.sh set-nfr --family <FAM> --status confirmed`), verify `OBS-2+` / `PRIV-2+` / `SCALE` numeric completeness, and verify `Section 10` rollback postconditions + `Section 12` retry/idempotency rules via `AskUserQuestion` (**STOP & WAIT**).

---

## 6. `R5` Backend/Surface Parity Exit Gate (`Step 3.06`, `§4.3` Hard Exit)

Run `"${CLAUDE_SKILL_DIR}/scripts/audit-fds.sh" "<spec_path>" --phase r5-parity --ledger "<ledger_path>"`. Every model capability (`Create`, `List/Read`, `Update`, state `Transition`, or `R1` link op) missing from `Section 8` is flagged `[ORPHAN-CAPABILITY]`. Present exact resolution options via `AskUserQuestion` (**STOP & WAIT**):
1. **Add `#surf-*` now** (update `Section 8` + `#feat-*`/`#flow-*`) • 2. **Defer by Phase** • 3. **Remove capability** • 4. **Headless internal rule** (`[CUSTOM: no user surface because <rationale>]`).
Re-run `--phase r5-parity` until exit code `0` (`0` `[ORPHAN-CAPABILITY]`, `0` `[BLOCKED]`).
