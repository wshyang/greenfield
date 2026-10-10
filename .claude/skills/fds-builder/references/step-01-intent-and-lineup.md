# Step 01 — Three-Order Intent Gate, Elicitation Anatomy & Dynamic Section Lineup

Load **only** during **Steps `1.1–1.3`**.

---

## 1. Three-Order Intent Decomposition (`Steps 1.1–1.2`, `MUST #1`, `MUST #14`)

**Hard Invariant:** Never scaffold objects, relationships, features, or NFRs before `intent_aligned == true` in `fds-state.sh`.

### 1.1 The Three Orders (`Step 1.1`)

| Order | Question to Settle | Premise Defect to Challenge Immediately (`MUST #14`) |
|---|---|---|
| **1st Order — Literal Ask** | What system, product slice, or workflow is the user literally asking to specify? | Self-contradictory constraint (e.g., *"zero persistence"* paired with *"multi-day approval history"*). |
| **2nd Order — Operational Workflow** | Which human/system actors run this daily, what breaks today, and what handoffs must succeed end-to-end? | Unowned operational step (e.g., approval gate with no actor role or assignment surface). |
| **3rd Order — Strategic / Risk Boundary** | What drives urgency and failure boundaries — tenant isolation, auditability, statutory privacy, latency SLA, or legacy cutover? | Posture mismatch (e.g., regulated PII exposed on unauthenticated share links). |

### 1.2 Typed Coherence Probes (`Appendix I` — Max `3` Questions via `AskUserQuestion`)
When any of Orders `1–3` is ambiguous or conflicting in `Step 1.1`, ask `1–3` structured probes via `AskUserQuestion` and **STOP & WAIT**:
- **Clarification Probe:** Disambiguate an overloaded domain noun (*"Does 'Workspace' mean an isolated billing tenant or a folder inside one org?"*).
- **Assumption Probe:** Test an unstated boundary (*"Do external reviewers log in with accounts or use scoped magic links?"*).
- **Evidence Probe:** Anchor operational reality (*"Does legacy data exist requiring migration, or does Phase 1 launch from an empty database?"*).
- **Perspective Shift:** Test non-happy-path actors (*"When an admin revokes an approver mid-review, what must an auditor see?"*).
- **Consequence Mapping:** Surface trade-off cost (*"Allowing hard-delete on Orders breaks immutable finance reconciliation; which rule wins?"*).

If intent cannot be safely inferred at all, state plainly that no safe specification path exists yet and ask the single resolving question via `AskUserQuestion`.

### 1.3 `[INTENT_ALIGNED]` Lock (`Step 1.2` Hard Gate)
Present a crisp `1–3` sentence synthesis of 1st, 2nd, and 3rd order intent via `AskUserQuestion` (`Confirm 3-Order Intent` vs `Refine Scope`) and **STOP & WAIT**. Once confirmed:
```bash
"${CLAUDE_SKILL_DIR}/scripts/fds-state.sh" add-dc --phase "1.2" --summary "3-order intent aligned: <summary>" --anchors "#sec-executive-summary"
"${CLAUDE_SKILL_DIR}/scripts/fds-state.sh" complete-step 1.2 --intent-aligned
```

---

## 2. `AskUserQuestion` Option Anatomy (`§5.1`, Applies Across All Interactive Steps)

Every `AskUserQuestion` call MUST obey four rules:
1. **Single Theme, `1–4` Questions Max (`§5.2`):** Never mix unrelated domains in one call. End your turn immediately after calling `AskUserQuestion`.
2. **Option Label (`2–5` Words):** Plain-language gist; append `(Recommended Default)` when surfacing a codified baseline so the user sees the default without losing explicit choice.
3. **Option Description (`1–2` Concrete Sentences):** State implementation impact + trade-off + explicit `because {reason}` (*"Enforces tenant-scoped RBAC with admin MFA; adds membership-join setup vs flat auth because shared SaaS isolates multiple customer orgs."*).
4. **Always Enable `allowCustomResponse: true`:** Lets the user specify a hybrid or custom rule (routed through `D7` if ambiguous). Never silently adopt any codified preset on the user's behalf.

---

## 3. Dynamic 16-Section Lineup, Critical Weights & Template Seeding (`Step 1.3`)

### 3.1 Locked Core vs Conditional Sections (`§4.2`)
- **Locked Core (`12` sections — always included):** `metadata`, `toc`, `executive-summary`, `phase-scope`, `core-objects`, `relationship-map`, `surface-inventory`, `features`, `user-flows`, `day-zero-bootstrap` (**locked `Critical`, `weight=3` — can never be untagged**), `nfr`, `changelog`. Also include `cross-object-constraints` and `appendices` unless explicitly superseded.
- **Conditional Sections (propose `Include` vs `Exclude with rationale` from `DC-001` evidence):**
  - `r6-collision` — include when dynamic slugs, shortcodes, or parameterized routes share a path/key namespace (`§6.9`).
  - `r7-session` — include whenever authenticated sessions, cookies/tokens, or multi-step client state exist (`§6.7`).
  - `integrations` — include when calling third-party APIs, IdPs, payment gateways, email/SMS, or webhooks (`§9.3`).
  - `data-migration` — include when importing or cutting over from legacy tables/spreadsheets (`§6.8`).
  - `anti-patterns` — include when domain traps or prohibited shortcuts must be fenced off (`§9.5`).
- **Additional `Critical` (`weight=3`) Candidates:** Propose `core-objects`, `features`, `nfr`, or `integrations` as `Critical` when failure causes security breach, financial corruption, or statutory violation (`3x` weakness priority in Phase 3).

### 3.2 Persist Lineup & Seed Canonical Spec (`Step 1.3` Substep 4)
After user confirmation via `AskUserQuestion`:
```bash
"${CLAUDE_SKILL_DIR}/scripts/fds-state.sh" lineup \
  --include "<included_csv>" \
  --exclude "<excluded_csv>" \
  --rationale "<session evidence>" \
  --critical "<critical_csv>" \
  --approve
"${CLAUDE_SKILL_DIR}/scripts/fds-state.sh" seed-spec --title "<System Name>"
"${CLAUDE_SKILL_DIR}/scripts/fds-state.sh" add-dc --phase "1.3" --summary "Approved 16-section lineup and critical weights" --depends-on "DC-001"
"${CLAUDE_SKILL_DIR}/scripts/fds-state.sh" complete-step 1.3
```
