# Functional Design Specification: <System Name>

## 1. Document Metadata & Conventions {#sec-metadata}

| Field | Value |
|---|---|
| **Document Version** | `0.1.0-draft` |
| **Date** | `YYYY-MM-DD` |
| **Status** | `Scaffold` (`Scaffold` \| `Deep-Dive` \| `Review` \| `Finalized`) |
| **Meta Prompt Version** | `FDS-Builder-Skill 2.0 (2026-10-29)` |
| **Session Metrics** | `Objects: 0 \| Surfaces: 0 \| Features: 0 \| Flows: 0 \| Decision Contexts: 1 \| Open Drafts: 0` |

### Tag & Anchor Conventions (`§8.2`, `§8.7`)
- `[DRAFT — {source}]`: Unconfirmed AI-drafted assumption or archetype default awaiting user decision.
- `[ACCEPTED-AS-DRAFT] — Implementation may require clarification`: User-acknowledged open item carried into final output.
- `[CUSTOM: {decision} because {rationale}]`: User-defined rule synthesized outside standard options (`D7` / `R1` / `R5`).
- **Anchor Prefixes (`D10`):** `#obj-` (Object), `#surf-` (Surface), `#feat-` (Feature), `#flow-` (User Flow), `#cstr-` (Cross-Object/Collision/Session Rule), `#boot-` (Bootstrap Step), `#int-` (Integration), `#nfr-` (Non-Functional Requirement), `#ap-` (Anti-Pattern).

---

## 2. Table of Contents {#sec-toc}

1. [Document Metadata & Conventions](#sec-metadata)
2. [Table of Contents](#sec-toc)
3. [Executive Summary](#sec-executive-summary)
4. [Phase Scope Summary](#sec-phase-scope)
5. [Core Objects](#sec-core-objects)
6. [Central Relationship Map](#sec-relationship-map)
7. [Cross-Object Constraints, Collision & Session Rules](#sec-cross-object-constraints)
8. [Surface Inventory](#sec-surface-inventory)
9. [Features](#sec-features)
10. [User Flows](#sec-user-flows)
11. [Day-Zero Bootstrap Sequence](#sec-day-zero-bootstrap)
12. [External Integrations & Data Migration](#sec-integrations)
13. [Non-Functional Requirements](#sec-nfr)
14. [Anti-Pattern Register](#sec-anti-patterns)
15. [Changelog](#sec-changelog)
16. [Appendices](#sec-appendices)

---

## 3. Executive Summary {#sec-executive-summary}

- **System Purpose:** <1–2 sentences capturing aligned 1st, 2nd, and 3rd order intent (`DC-001`).>
- **Target Actor Roles:** <Closed list of human and system roles.>
- **Core Capabilities:** <Concise summary of capabilities delivered.>
- **Key Domain Objects:** <Anchor links to `#obj-*` entities.>
- **Total Reachable Surfaces:** `<N>` surfaces across `<M>` phases (see [Surface Inventory](#sec-surface-inventory)).
- **Phase Delivery Summary:** <Summary of Phase 1 vs subsequent phases.>
- **External Dependencies:** <Summary of `#int-*` dependencies or `None`.>
- **Day-Zero Bootstrap Summary:** <How empty DB reaches first usable state (`#sec-day-zero-bootstrap`).>
- **Foundational Decisions:** <Top `DC-NNN` architectural/product commitments.>

---

## 4. Phase Scope Summary {#sec-phase-scope}

| Phase | Target Outcome | Included Features (`#feat-*`) | Newly Introduced Objects / Attributes | Newly Activated Surfaces (`#surf-*`) |
|---|---|---|---|---|
| `Phase 1` | <Minimum complete end-to-end workflow> | `[#feat-example](#feat-example)` | `[#obj-example](#obj-example)` (all `Phase 1` attributes) | `[#surf-example-create](#surf-example-create)` |

---

## 5. Core Objects {#sec-core-objects}

### 5.1 <Object Name> {#obj-example}

- **Baseline Phase:** `Phase 1`
- **Description:** <Deterministic domain responsibility and ownership scope.>

#### Attributes (`D3`)

| Attribute | Type | Phase | Constraints | Validation Rule | Error Message |
|---|---|---|---|---|---|
| `id` | `uuid` | `Phase 1` | `required`, `primary_key`, `immutable` | Generated server-side on creation; caller-supplied values rejected | `"Identifier is system-assigned and cannot be set manually."` |

#### Lifecycle & State Machine (`D4`)

- **Valid States:** `draft` (initial), `active`, `archived` (terminal)

| From State | To State | Trigger (`#surf-*`) | Guard Condition | Post-Transition Side Effects |
|---|---|---|---|---|
| `draft` | `active` | `[#surf-example-create](#surf-example-create)` | Actor holds active role AND all required attributes pass validation | Records `activated_at` UTC timestamp and emits audit record |

- **Forbidden Transitions (`D4`):**

| Attempted From → To | Rejection Error Message | Rationale (`because ...`) |
|---|---|---|
| `archived → active` | `"Archived records cannot be reactivated. Create a new record instead."` | Forbidden because archived records freeze historical audit snapshots. |

#### Relationships

- Outbound / Inbound links defined in [Central Relationship Map](#sec-relationship-map) (or state `None` explicitly).

#### Edge & Failure Modes (`§6.6` — 6 Categories + `R8`)

| Category | Scenario | Deterministic System Behavior & Error Copy |
|---|---|---|
| `1. Boundary` | <Max field length / zero / pagination boundary> | <Exact handling> |
| `2. Invalid Input` | <Malformed type / missing required field / unknown enum> | <Exact 4xx status + verbatim error message> |
| `3. Adversarial Input` | <Cross-tenant ID tampering / script payload / replay> | <Exact non-leaking rejection + audit event> |
| `4. Race Condition` | <Concurrent edit / duplicate submission> | <Idempotency key or optimistic version conflict rule> |
| `5. Dependency Failure` | <DB transaction abort / downstream timeout> | <Atomic rollback guarantee; zero partial writes> |
| `6. Auth-Change Propagation (R8)` | <Actor role revoked mid-edit or during active session> | <In-flight request rule, active session rule, auth cache TTL, propagation SLA + `because` rationale> |

#### Empty States (`D20`)

| Variant | Trigger Condition | Exact User-Facing Copy & Primary Action |
|---|---|---|
| `loaded-zero` | Filter/search returns `0` matching rows while tenant rows exist | `"No matching records found for your current filters."` + `Clear Filters` action |
| `zero-permission` | Caller lacks role/scope to view records in this context | `"You do not have permission to view records in this workspace."` + `Request Access` / scope switch |
| `zero-day-zero` | Tenant/workspace has `0` records created since bootstrap | `"No records have been created yet."` + primary CTA `[#surf-example-create](#surf-example-create)` for authorized roles |
| `loading-error` | Query timeout or upstream failure | `"Unable to load records right now (Reference: {request_id})."` + `Retry` action preserving filter state |

#### Notes

- Traceability: `DC-001`.

---

## 6. Central Relationship Map {#sec-relationship-map}

| Object A | Cardinality | Object B | Relationship Name | Constraints (`incl. R3 on_delete`) | Data-Carrying? | Surface Coverage (`R1` / `R5`) |
|---|---|---|---|---|---|---|
| `[#obj-example](#obj-example)` | `1:N` | `[#obj-example](#obj-example)` | `ExampleLink` | `on_delete: RESTRICT` | `No` | Create: `[#surf-example-create](#surf-example-create)`; List: `[#surf-example-list](#surf-example-list)`; Remove: `[CUSTOM: immutable link because audit history requires permanent lineage]` |

### Relationship Narrative

<Human-readable explanation of object graph invariants and any `R1` promoted junction objects.>

---

## 7. Cross-Object Constraints, Collision & Session Rules {#sec-cross-object-constraints}

### 7.1 Multi-Object Invariants {#cstr-invariants}

1. <Cross-object invariant referencing `#obj-*` anchors.>

### 7.2 Path & Identifier Collision Rules (`R6`) {#cstr-collision-rules}

| Precedence | Pattern | Target Surface / Handler | Shadowing Guard & Reserved Literals |
|---|---|---|---|
| `1 (Literal)` | `/settings` | `#surf-example-list` | Reserved literal; rejected in slug validation (`admin`, `api`, `auth`, `healthz`, `login`, `logout`, `me`, `new`, `settings`) |

### 7.3 Session Continuity Contract (`R7`) {#cstr-session-continuity}

| Dimension | Deterministic Contract |
|---|---|
| **Storage Medium & Cookie/Key Flags** | <e.g., `HttpOnly; Secure; SameSite=Lax` cookie `__Host-session`> |
| **Absolute & Idle Timeouts** | <e.g., `12h` absolute, `30m` idle sliding renewal> |
| **Reload Behavior While Valid** | <Route + URL query state preserved> |
| **Reload / Submit Behavior After Expiry** | <Redirect to login with `return_to` path; exact session-expired banner> |
| **Deactivation / Role-Change Behavior** | <Cross-reference `R8` propagation window> |
| **Client Rehydration Order** | <1. Session verify → 2. Tenant/role context → 3. Route query fetch> |
| **Pre-Rehydration UI State** | <Neutral auth gate skeleton; zero flash of unauthorized data> |

---

## 8. Surface Inventory {#sec-surface-inventory}

| # | Surface | Anchor | Permitted Roles | Target Object / Relationship | CRUD / Associate | Phase |
|---|---|---|---|---|---|---|
| 1 | Create Example Record | `#surf-example-create` | `admin` | `[#obj-example](#obj-example)` | `Create` | `Phase 1` |
| 2 | List Example Records | `#surf-example-list` | `admin`, `viewer` | `[#obj-example](#obj-example)` | `Read / List` | `Phase 1` |

---

## 9. Features {#sec-features}

### 9.1 Create Example Record {#feat-example}

- **Phase:** `Phase 1` *(single phase tag only — `P5`)*
- **Involved Objects & Surfaces:** `[#obj-example](#obj-example)`, `[#surf-example-create](#surf-example-create)`, `[#surf-example-list](#surf-example-list)`
- **Preconditions:** System completed `[#boot-01](#boot-01)`; caller is authenticated.
- **User Story:** As an `admin`, I create an Example Record so downstream workflows have a validated entity.

#### Authorization Derivation Trace (`R2`, `D19`)

- **Rule (`IF-AND-ONLY-IF`):** Actor `U` may execute `#feat-example` **IF-AND-ONLY-IF** `U` corresponds to `#obj-example`admin bootstrap identity (`[SEED: #boot-01]`) with `status == "active"`.

#### Acceptance Criteria (`BDD`, `§5.8`)

1. **Scenario 1 — Happy Path:**
   - **Given** an authenticated `admin` on `[#surf-example-create](#surf-example-create)` with valid attribute inputs
   - **When** the `admin` submits the creation request
   - **Then** the system persists `[#obj-example](#obj-example)` in state `active` and renders it in `[#surf-example-list](#surf-example-list)`.
2. **Scenario 2 — Validation / Permission Failure Path:**
   - **Given** an authenticated `viewer` lacking `admin` permission (or invalid payload)
   - **When** the caller submits `[#surf-example-create](#surf-example-create)`
   - **Then** the system rejects the mutation with zero database writes and displays the exact `D3` / `403` error message.
3. **Scenario 3 — Empty-State Path (`D20`):**
   - **Given** `0` `[#obj-example](#obj-example)` records exist after `[#boot-01](#boot-01)`
   - **When** an `admin` opens `[#surf-example-list](#surf-example-list)`
   - **Then** the surface renders the `zero-day-zero` state with primary action linking to `[#surf-example-create](#surf-example-create)`.

#### Verification Strategy *(Required when complex)*

- **Test Type:** Integration & authorization boundary verification
- **Key Scenarios:** Authorized creation, unauthorized `viewer` rejection, duplicate/concurrent submission
- **Synthetic Data Needs:** Fictional `admin@example.com` and `viewer@example.com` accounts (`D17`)
- **Environment Dependencies:** Relational test database seeded through `#boot-01`

#### Edge Cases & Notes

- Duplicate submission with identical `Idempotency-Key` within `24h` returns original created record without duplicate insert.

---

## 10. User Flows {#sec-user-flows}

### 10.1 Primary Onboarding & Creation Flow {#flow-example}

- **Actors:** `admin`
- **Trigger:** Navigating to `[#surf-example-list](#surf-example-list)` after `[#boot-01](#boot-01)`
- **Preconditions:** Database initialized via Section 11.

#### Happy Path
1. `admin` opens `[#surf-example-list](#surf-example-list)` and views `zero-day-zero` empty state.
2. `admin` activates `[#surf-example-create](#surf-example-create)`, enters valid fields, and submits.
3. System validates `D3` contract, writes `[#obj-example](#obj-example)`, records audit event, and redirects to `[#surf-example-list](#surf-example-list)`.

#### Alternate & Empty-State Paths
- **Alt 1 (`loaded-zero` filter):** Applying a non-matching search term displays `loaded-zero` copy with `Clear Filters` control.

#### Exception Paths
- **Ex 1 (Validation failure):** Invalid field input halts at Step 3, preserves user-entered form values, and highlights field-level `D3` error copy.

#### Postconditions
- **Happy Path:** Exactly `1` active `#obj-example` row and `1` audit row persisted.
- **Exception Path:** `0` `#obj-example` mutations persisted.

---

## 11. Day-Zero Bootstrap Sequence {#sec-day-zero-bootstrap}

> **Critical Section (`D21`, `R4`):** Deterministic path from an empty database (`0` rows) to first usable state for every actor role.

| Step Anchor | Order | Actor | Surface or `[SEED]` Mechanism | Object / Relationship Populated | Capability / Role Unlocked | Status |
|---|---|---|---|---|---|---|
| `#boot-01` | 1 | System Installer | `[SEED]` One-shot CLI command reading `BOOTSTRAP_ADMIN_EMAIL` | Initial `admin` credential record (`status=active`) | Unlocks `[#surf-example-create](#surf-example-create)` & `[#surf-example-list](#surf-example-list)` | Confirmed |

---

## 12. External Integrations & Data Migration {#sec-integrations}

### 12.1 External Integrations {#int-overview}

<Populate `#int-*` blocks per `references/step-02d-integrations-and-conditionals.md` §4, or state `Excluded per approved lineup (DC-NNN) because system has zero external third-party integrations in Phase 1.`>

### 12.2 Legacy Data Migration (`§6.8`) {#int-data-migration}

<Populate 7-part migration contract when legacy data exists, or state `Excluded per approved lineup (DC-NNN) because system launches greenfield from an empty database.`>

---

## 13. Non-Functional Requirements {#sec-nfr}

### 13.1 Security {#nfr-security}
- **Selected Archetype:** `<SEC-1..7>`
- **Parameter Table, Testable Requirements, BDD Checks & Stress Notes:** *(Populate from `references/step-02e-nfr-core-batch-a.md` & `references/step-02f-nfr-conditional-batch-b.md`)*

### 13.2 Performance {#nfr-performance}
- **Selected Archetype:** `<PERF-1..5>`

### 13.3 Audit & Logging {#nfr-logging}
- **Selected Archetype:** `<LOG-1..5>`

### 13.4 Scalability (`§7.3` Quantitative Metrics Required When Active) {#nfr-scalability}
- **Selected Archetype:** `<SCALE-1..5 or Explicitly Skipped per DC-NNN>`

### 13.5 Accessibility {#nfr-accessibility}
- **Selected Archetype:** `<A11Y-1..5 or Explicitly Skipped per DC-NNN>`

### 13.6 Observability (`OBS-2+` Requires Component Matrix `§7.4`) {#nfr-observability}
- **Selected Archetype:** `<OBS-1..4 or Explicitly Skipped per DC-NNN>`

### 13.7 Internationalization & Localization {#nfr-i18n}
- **Selected Archetype:** `<I18N-1..4 or Explicitly Skipped per DC-NNN>`

### 13.8 Privacy & Data Lifecycle (`PRIV-2+` Requires PII Inventory `§7.4`) {#nfr-privacy}
- **Selected Archetype:** `<PRIV-1..4 or Explicitly Skipped per DC-NNN>`

---

## 14. Anti-Pattern Register {#sec-anti-patterns}

| ID | Anti-Pattern | Description | Why Prohibited (`because ...`) | Detection Signal |
|---|---|---|---|---|
| `#ap-01` | <Name> | <What must not be built> | <Concrete failure/security/audit consequence> | <Observable code/test smell> |

---

## 15. Changelog {#sec-changelog}

| Decision Context | Date | Version | Phase | Summary of Substantive Change | Affected Anchors |
|---|---|---|---|---|---|
| `DC-001` | `YYYY-MM-DD` | `0.1.0-draft` | `Phase 1.3` | Established 3-order intent alignment and initial system boundary | `#sec-executive-summary` |

---

## 16. Appendices {#sec-appendices}

### Appendix A — Accepted-As-Draft Register
- `None` *(or list of `[ACCEPTED-AS-DRAFT] — Implementation may require clarification` items acknowledged in Phase 4).*

### Appendix B — Domain Glossary
| Term | Exact Definition | Canonical Anchor |
|---|---|---|
| <Term> | <Single unambiguous meaning across all sections> | `[#obj-example](#obj-example)` |
