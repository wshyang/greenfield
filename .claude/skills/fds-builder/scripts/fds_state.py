#!/usr/bin/env python3
"""Compaction-resilient granular step machine & DC ledger for the fds-builder skill.

Manages:
  - 30-step ordered granular execution DAG (0.1 .. 6.1) with per-batch sub-loops
    (object-batch, stateful-batch, feature-batch, two-gate flow-batch 2.08a/2.08b,
    and weakness-ranked Deep-Dive batches)
  - Mechanical leaf 'done when' verification on every complete-step transition
  - Just-in-time single-file step reference routing (references/step-*.md)
  - Deterministic template seeding (seed-spec) with D9 exclusion stubs
  - D11 Phase | Progress status banner
  - MUST #1 3-order intent alignment gate before Phase 2 scaffold
  - Dynamic Section Lineup & locked Critical Sections (Day-Zero Bootstrap locked critical)
  - NFR Archetype decision tracking (§7.5 mandatory vs explicit-skip conditional)
  - Decision Context (DC-NNN) registry & atomic transitive rollback (§5.10, P13)
  - D8 Friction Event logging & §10 root-cause clustering
  - Verbatim Chunked Mode accumulator (/chunked .. /done)
"""

from __future__ import annotations

import argparse
import contextlib
import datetime as dt
import io
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import audit_fds  # noqa: E402

MANDATORY_NFR = {"SEC", "PERF", "LOG"}
CONDITIONAL_NFR = {"SCALE", "A11Y", "OBS", "I18N", "PRIV"}
ALL_NFR = MANDATORY_NFR | CONDITIONAL_NFR

VALID_ARCHETYPES = {
    "SEC": {f"SEC-{i}" for i in range(1, 8)},
    "PERF": {f"PERF-{i}" for i in range(1, 6)},
    "LOG": {f"LOG-{i}" for i in range(1, 6)},
    "SCALE": {f"SCALE-{i}" for i in range(1, 6)},
    "A11Y": {f"A11Y-{i}" for i in range(1, 6)},
    "OBS": {f"OBS-{i}" for i in range(1, 5)},
    "I18N": {f"I18N-{i}" for i in range(1, 5)},
    "PRIV": {f"PRIV-{i}" for i in range(1, 5)},
}

FRICTION_CATEGORIES = {
    "terminology",
    "structure",
    "scope",
    "granularity",
    "surface_gaps",
    "auth_complexity",
    "bootstrap_complexity",
}

STRUCTURAL_FRICTION = {"surface_gaps", "auth_complexity", "bootstrap_complexity", "structure"}

LOOP_KINDS = {
    "object-batch",
    "stateful-batch",
    "feature-batch",
    "flow-batch",
    "weakness-object-batch",
    "weakness-feature-batch",
}

DEFAULT_SECTIONS = {
    "metadata": {"status": "included", "critical": False, "weight": 1, "rationale": "Canonical metadata header (§8.5)"},
    "toc": {"status": "included", "critical": False, "weight": 1, "rationale": "Multi-section navigation (§8.4)"},
    "executive-summary": {"status": "included", "critical": False, "weight": 1, "rationale": "Stakeholder overview (§9.6)"},
    "phase-scope": {"status": "included", "critical": False, "weight": 2, "rationale": "Phase boundary summary (§6.5)"},
    "core-objects": {"status": "included", "critical": False, "weight": 2, "rationale": "Domain object contracts (§6.1)"},
    "relationship-map": {"status": "included", "critical": False, "weight": 2, "rationale": "Central relationship & R1/R3 map (§6.3)"},
    "cross-object-constraints": {"status": "included", "critical": False, "weight": 2, "rationale": "Multi-object invariants (§6.3)"},
    "r6-collision": {"status": "pending", "critical": False, "weight": 2, "rationale": "Conditional on routes/slugs (§6.9)"},
    "r7-session": {"status": "pending", "critical": False, "weight": 2, "rationale": "Conditional on authenticated/session state (§6.7)"},
    "surface-inventory": {"status": "included", "critical": False, "weight": 2, "rationale": "Mandatory R5 parity checklist (§9.4)"},
    "features": {"status": "included", "critical": False, "weight": 2, "rationale": "BDD & R2 authz feature specs (§9.1)"},
    "user-flows": {"status": "included", "critical": False, "weight": 2, "rationale": "End-to-end actor flows (§9.2)"},
    "day-zero-bootstrap": {
        "status": "included",
        "critical": True,
        "locked_critical": True,
        "weight": 3,
        "rationale": "Mandatory critical empty-DB path (§4.2, D21, R4)",
    },
    "integrations": {"status": "pending", "critical": False, "weight": 2, "rationale": "Conditional on external providers (§9.3)"},
    "data-migration": {"status": "pending", "critical": False, "weight": 2, "rationale": "Conditional on legacy data (§6.8)"},
    "nfr": {"status": "included", "critical": False, "weight": 2, "rationale": "SEC/PERF/LOG + conditional NFRs (§7)"},
    "anti-patterns": {"status": "pending", "critical": False, "weight": 1, "rationale": "Conditional register (§9.5)"},
    "changelog": {"status": "included", "critical": False, "weight": 1, "rationale": "DC-NNN audit trail (§8.6)"},
    "appendices": {"status": "included", "critical": False, "weight": 1, "rationale": "Accepted-as-draft & glossary (§4.5)"},
}

CORE_LOCKED_INCLUDED = {
    "metadata",
    "toc",
    "executive-summary",
    "phase-scope",
    "core-objects",
    "relationship-map",
    "surface-inventory",
    "features",
    "user-flows",
    "day-zero-bootstrap",
    "nfr",
    "changelog",
}

GRANULAR_STEPS: List[Dict[str, Any]] = [
    {
        "id": "0.1",
        "phase_label": "0.1 (Entry & Ledger Init)",
        "title": "Mode Routing, Chunked Buffer & Session Ledger Init",
        "ref": "references/step-00-entry-and-intake.md",
        "hard_gate": False,
        "skippable": False,
        "loop_kind": None,
        "substeps": [
            "Handle /chunked../done, /status|/decisions|/parked|/audit, D15 diagram refusal, or §1.3 out-of-scope refusal.",
            "Confirm <spec_path> (from $target or 1 AskUserQuestion path card) and run fds-state.sh init.",
            "Materialize initial Phase 0/1 granular steps in TaskCreate and mark the active step in_progress.",
        ],
        "done_when": "Session ledger initialized with chunked_mode.active == false and spec_path recorded.",
    },
    {
        "id": "0.2",
        "phase_label": "0.2 (Reverse Intake)",
        "title": "Existing-Artifact Reverse Intake & Gap Tagging",
        "ref": "references/step-00-entry-and-intake.md",
        "hard_gate": True,
        "skippable": True,
        "loop_kind": None,
        "substeps": [
            "Read references/step-00-entry-and-intake.md (§3) and run fds-state.sh seed-spec if <spec_path> is absent.",
            "Extract explicit facts into #obj-*/#feat-*/#surf-*/#flow-*/#int-*/#nfr-* blocks and tag missing contracts [DRAFT — intake-gap].",
            "Run audit-fds.sh <spec_path> --phase intake --ledger <ledger>.",
            "Present extracted inventory vs missing contracts via AskUserQuestion (HARD GATE -> STOP & WAIT), then record DC-NNN.",
        ],
        "done_when": "<spec_path> exists on disk and intake triage DC-NNN is recorded.",
    },
    {
        "id": "1.1",
        "phase_label": "1.1 (3-Order Intent Probes)",
        "title": "Three-Order Intent Decomposition & Coherence Probing",
        "ref": "references/step-01-intent-and-lineup.md",
        "hard_gate": True,
        "skippable": False,
        "loop_kind": None,
        "substeps": [
            "Read references/step-01-intent-and-lineup.md (§1–§2).",
            "Decompose 1st Order (literal ask), 2nd Order (daily actors/workflow), and 3rd Order (governance/risk/scale/cutover); flag premise contradictions (MUST #14).",
            "If any order is ambiguous, ask 1–3 typed probes via AskUserQuestion (HARD GATE -> STOP & WAIT).",
        ],
        "done_when": "1st, 2nd, and 3rd order intent statements are non-contradictory and ready for confirmation.",
    },
    {
        "id": "1.2",
        "phase_label": "1.2 (Intent Gate Lock)",
        "title": "Explicit [INTENT_ALIGNED] Confirmation Gate (MUST #1)",
        "ref": "references/step-01-intent-and-lineup.md",
        "hard_gate": True,
        "skippable": False,
        "loop_kind": None,
        "substeps": [
            "Present crisp 1–3 sentence summary of 1st, 2nd, and 3rd order intent via AskUserQuestion (HARD GATE -> STOP & WAIT).",
            "Mint DC-001 via fds-state.sh add-dc.",
            "Complete Step 1.2 with --intent-aligned and materialize Phase 2 granular step tasks via TaskCreate.",
        ],
        "done_when": "intent_aligned == true in ledger and >= 1 active DC-NNN recorded.",
    },
    {
        "id": "1.3",
        "phase_label": "1.3 (Section Lineup & Seed)",
        "title": "Dynamic 16-Section Lineup, Critical Weights & Template Seeding",
        "ref": "references/step-01-intent-and-lineup.md",
        "hard_gate": True,
        "skippable": False,
        "loop_kind": None,
        "substeps": [
            "Evaluate conditional sections (r6-collision, r7-session, integrations, data-migration, anti-patterns) and Critical weight=3 candidates (day-zero-bootstrap locked Critical).",
            "Confirm lineup + Critical tags via AskUserQuestion (HARD GATE -> STOP & WAIT).",
            "Run fds-state.sh lineup ... --approve, run fds-state.sh seed-spec --title '<System Name>', and mint DC-NNN.",
        ],
        "done_when": "lineup_approved == true and <spec_path> exists on disk with 16 canonical sections.",
    },
    {
        "id": "2.01",
        "phase_label": "2.01 (Boundaries & Phases)",
        "title": "Domain 1 — System Boundaries, Actor Roles & Phase Scope (Section 4)",
        "ref": "references/step-02a-boundaries-and-objects.md",
        "hard_gate": True,
        "skippable": False,
        "loop_kind": None,
        "substeps": [
            "Read references/step-02a-boundaries-and-objects.md (§1–§2).",
            "Confirm actor roles, in/out-of-scope boundaries, and Phase 1 vs Phase 2+ split via AskUserQuestion (1–4 questions; HARD GATE -> STOP & WAIT).",
            "Edit Sections 3 & 4 in <spec_path> and mint DC-NNN.",
        ],
        "done_when": "Section 4 Phase Scope Summary in <spec_path> is populated without template placeholders.",
    },
    {
        "id": "2.02",
        "phase_label": "2.02 (Object Inventory)",
        "title": "Domain 2 — Core Object Inventory Lock & Batch Queue",
        "ref": "references/step-02a-boundaries-and-objects.md",
        "hard_gate": True,
        "skippable": False,
        "loop_kind": None,
        "substeps": [
            "Propose complete #obj-* inventory (slug, 1-line responsibility, phase tag) via AskUserQuestion (HARD GATE -> STOP & WAIT).",
            "Register bounded batches of 1–3 objects via fds-state.sh register-items --kind object-batch --items '<b1>;<b2>' and TaskCreate.",
            "Mint DC-NNN and advance to Step 2.03.",
        ],
        "done_when": ">= 1 object-batch registered in ledger.",
    },
    {
        "id": "2.03",
        "phase_label": "2.03 (Object Attributes & D20)",
        "title": "Domain 3 & D20 — 6-Column Attribute Contracts & 4 Empty States (Section 5)",
        "ref": "references/step-02a-boundaries-and-objects.md",
        "hard_gate": True,
        "skippable": False,
        "loop_kind": "object-batch",
        "substeps": [
            "For the active object batch (max 3 objects), ask 1–4 AskUserQuestion cards on uniqueness scopes, mutability, validation bounds, and list exposure (HARD GATE -> STOP & WAIT).",
            "Write all 8 subsections per #obj-* in Section 5: 6-column D3 table (0 blank cells, verbatim error copy) + 4 D20 empty states when list-exposed.",
            "Mint DC-NNN and run fds-state.sh complete-step 2.03 (iterates until all object batches finish).",
        ],
        "done_when": "Section 5 defines concrete #obj-* blocks with 6-column attribute tables and zero template #obj-example stubs.",
    },
    {
        "id": "2.04",
        "phase_label": "2.04 (Relationships & R1/R3)",
        "title": "Domain 5, R1 Pass 1 & R3 Pass 1 — Central Relationship Map & Deletion Integrity (Sections 6–7)",
        "ref": "references/step-02b-relationships-and-lifecycles.md",
        "hard_gate": True,
        "skippable": False,
        "loop_kind": None,
        "substeps": [
            "Read references/step-02b-relationships-and-lifecycles.md (§1–§3).",
            "Identify all cardinalities, promote every N:M or data-carrying link to #obj-* with 4 surfaces (R1), and elicit on_delete policies (R3) via AskUserQuestion (HARD GATE -> STOP & WAIT).",
            "Populate 7-column Section 6 Relationship Map + narrative, add promoted junction #obj-* blocks to Section 5, and mint DC-NNN.",
        ],
        "done_when": "Section 6 Relationship Map defines explicit on_delete policies without template #obj-parent-example placeholders.",
    },
    {
        "id": "2.05",
        "phase_label": "2.05 (Lifecycles & D4)",
        "title": "Domain 4 (D4) — State Machine Lifecycles, Guards & Forbidden Transitions (Section 5)",
        "ref": "references/step-02b-relationships-and-lifecycles.md",
        "hard_gate": True,
        "skippable": True,
        "loop_kind": "stateful-batch",
        "substeps": [
            "Classify stateful vs stateless #obj-* records (register stateful batches via register-items --kind stateful-batch, or pass --skip-reason if all stateless).",
            "For the active stateful batch (1–2 objects), confirm state sets, transition guards, terminal locks, and forbidden transitions via AskUserQuestion (HARD GATE -> STOP & WAIT).",
            "Write Valid States, Legal Transition Table, Forbidden Transitions + 'because' Rationale, and Field Mutability into Section 5; mint DC-NNN.",
        ],
        "done_when": "Section 5 stateful #obj-* blocks include legal + forbidden transition rules (or explicit stateless rationale).",
    },
    {
        "id": "2.06",
        "phase_label": "2.06 (Surface Inventory)",
        "title": "Section 8 Surface Inventory Baseline & Feature/Flow Queue Lock",
        "ref": "references/step-02c-surfaces-features-flows.md",
        "hard_gate": True,
        "skippable": False,
        "loop_kind": None,
        "substeps": [
            "Read references/step-02c-surfaces-features-flows.md (§1).",
            "Confirm candidate #surf-* checklist, single-phase #feat-* capabilities (P5), and #flow-* journeys via AskUserQuestion (HARD GATE -> STOP & WAIT).",
            "Populate Section 8 Surface Inventory and register feature-batch + flow-batch queues via fds-state.sh register-items and TaskCreate.",
        ],
        "done_when": "Section 8 contains concrete #surf-* rows without #surf-example-create placeholders.",
    },
    {
        "id": "2.07",
        "phase_label": "2.07 (BDD Features)",
        "title": "Domain 6 — Feature Specs, Preliminary R2 Authz & BDD Scenarios (Section 9)",
        "ref": "references/step-02c-surfaces-features-flows.md",
        "hard_gate": True,
        "skippable": False,
        "loop_kind": "feature-batch",
        "substeps": [
            "For the active #feat-* batch (1–3 features), elicit open business rules, role gates, and failure copy via AskUserQuestion (HARD GATE -> STOP & WAIT).",
            "Author Section 9 #feat-* blocks with single Phase tag, preliminary R2 IFF trace, Given/When/Then BDD (Happy + Failure + Empty-State), and Verification Strategy when complex.",
            "Sync any newly discovered #surf-* to Section 8 and mint DC-NNN.",
        ],
        "done_when": "Section 9 defines concrete #feat-* blocks with Given/When/Then BDD scenarios and zero #feat-example placeholders.",
    },
    {
        "id": "2.08a",
        "phase_label": "2.08a (Flow Happy Path & Prune)",
        "title": "Domain 7 Gate A — User Flow Happy Path Lock & Candidate Exception Pruning (§5.7)",
        "ref": "references/step-02c-surfaces-features-flows.md",
        "hard_gate": True,
        "skippable": False,
        "loop_kind": "flow-batch",
        "substeps": [
            "For the active #flow-* batch, draft Actors, Trigger (#surf-*), Preconditions, and numbered Happy Path steps in Section 10.",
            "Present candidate Alternate + Exception branches via AskUserQuestion so the user prunes irrelevant branches BEFORE recovery prose is written (HARD GATE -> STOP & WAIT).",
            "Mint DC-NNN and run fds-state.sh complete-step 2.08a to unlock surviving exception authoring (2.08b).",
        ],
        "done_when": "Section 10 defines concrete #flow-* heading(s) and numbered Happy Path steps.",
    },
    {
        "id": "2.08b",
        "phase_label": "2.08b (Flow Exceptions & Postconditions)",
        "title": "Domain 7 Gate B — Surviving Alternate/Exception Recovery & Postconditions (Section 10)",
        "ref": "references/step-02c-surfaces-features-flows.md",
        "hard_gate": False,
        "skippable": False,
        "loop_kind": "flow-batch",
        "substeps": [
            "Write numbered recovery steps strictly for the surviving user-confirmed Alternate & Exception branches in Section 10 (ask AskUserQuestion only if a retry/rollback rule remains ambiguous).",
            "Write explicit Happy-Path and Exception rollback/non-mutation Postconditions.",
            "Run fds-state.sh complete-step 2.08b (cycles to next flow-batch at 2.08a if remaining, else advances to 2.09).",
        ],
        "done_when": "Section 10 defines concrete #flow-* Postconditions without #flow-example placeholders.",
    },
    {
        "id": "2.09",
        "phase_label": "2.09 (Conditionals & Integrations)",
        "title": "Domains 8, 10, 11 & Conditional R6/R7 Specs (Sections 7 & 12)",
        "ref": "references/step-02d-integrations-and-conditionals.md",
        "hard_gate": True,
        "skippable": True,
        "loop_kind": None,
        "substeps": [
            "Read references/step-02d-integrations-and-conditionals.md.",
            "For each included conditional spec (Retention, R6 route/slug collision + reserved literals, R7 7-point session continuity, #int-* integrations, or 7-part data migration), elicit choices via AskUserQuestion (<= 4 questions/call; HARD GATE -> STOP & WAIT).",
            "Populate Sections 7 & 12 (ensuring D9 skip notices exist for excluded ones) and mint DC-NNN.",
        ],
        "done_when": "Zero sections remain in 'pending' status in ledger and included Section 7/12 blocks contain no template placeholders.",
    },
    {
        "id": "2.10",
        "phase_label": "2.10 (Core NFR Batch A)",
        "title": "Domain 9 Batch A — Mandatory Core NFRs (SEC, PERF, LOG) & Quantitative SCALE (Section 13)",
        "ref": "references/step-02e-nfr-core-batch-a.md",
        "hard_gate": True,
        "skippable": False,
        "loop_kind": None,
        "substeps": [
            "Read references/step-02e-nfr-core-batch-a.md.",
            "Present 4 AskUserQuestion cards for SEC-1..7, PERF-1..5, LOG-1..5 (mandatory) and SCALE-1..5 vs explicit skip (HARD GATE -> STOP & WAIT).",
            "Record choices via fds-state.sh set-nfr + add-dc, and write Section 13.1–13.4 blocks (including all 5 numeric metrics if SCALE active; tag unconfirmed preset values [DRAFT — archetype default]).",
        ],
        "done_when": "SEC, PERF, LOG, and SCALE are all != 'unconfirmed' in ledger.",
    },
    {
        "id": "2.11",
        "phase_label": "2.11 (Conditional NFR Batch B)",
        "title": "Domain 9 Batch B — Conditional NFRs (A11Y, OBS, I18N, PRIV) & §7.4 Sub-Tables (Section 13)",
        "ref": "references/step-02f-nfr-conditional-batch-b.md",
        "hard_gate": True,
        "skippable": False,
        "loop_kind": None,
        "substeps": [
            "Read references/step-02f-nfr-conditional-batch-b.md.",
            "Present 4 AskUserQuestion cards for A11Y-1..5, OBS-1..4, I18N-1..4, and PRIV-1..4, each offering tiers OR explicit skip confirmation (HARD GATE -> STOP & WAIT).",
            "Record via fds-state.sh set-nfr + add-dc, and write Section 13.5–13.8 including mandatory #nfr-observability-components (OBS-2+) and #nfr-pii-inventory (PRIV-2+) tables.",
        ],
        "done_when": "All 8 NFR families are != 'unconfirmed' in ledger and mandatory OBS-2+ / PRIV-2+ sub-tables exist in <spec_path>.",
    },
    {
        "id": "2.12",
        "phase_label": "2.12 (Day-Zero Bootstrap Draft)",
        "title": "R4 Day-Zero Bootstrap Draft (Section 11) & Anti-Pattern Register (Section 14)",
        "ref": "references/step-03-deep-dive-and-audits.md",
        "hard_gate": True,
        "skippable": False,
        "loop_kind": None,
        "substeps": [
            "Read references/step-03-deep-dive-and-audits.md (§1).",
            "Trace #boot-01..#boot-NN from an empty DB (0 rows) to every actor role's first workflow and confirm [SEED] mechanism via AskUserQuestion (HARD GATE -> STOP & WAIT).",
            "Populate Section 11 Day-Zero Bootstrap and Section 14 #ap-* entries (or D9 exclusion stub), then mint DC-NNN.",
        ],
        "done_when": "Section 11 defines #boot-01+ bootstrap steps without #surf-example-create placeholders.",
    },
    {
        "id": "2.13",
        "phase_label": "2.13 (Scaffold Exit Gate)",
        "title": "Deterministic Phase 2 Scaffold Exit Audit (Appendix G)",
        "ref": "references/step-03-deep-dive-and-audits.md",
        "hard_gate": False,
        "skippable": False,
        "loop_kind": None,
        "substeps": [
            "Run audit-fds.sh <spec_path> --phase scaffold --ledger <ledger>.",
            "Fix any structural defect (blank 6-col D3 cell, missing D4 forbidden transition, missing D20 empty state, broken format) until exit code 0.",
            "Run fds-state.sh complete-step 2.13.",
        ],
        "done_when": "audit-fds.sh --phase scaffold passes with 0 issues.",
    },
    {
        "id": "3.01",
        "phase_label": "3.01 (Weakness Ranking)",
        "title": "Phase 3 Entry — Deterministic Weakness Ranking & Triage Approval (§4.3)",
        "ref": "references/step-03-deep-dive-and-audits.md",
        "hard_gate": True,
        "skippable": False,
        "loop_kind": None,
        "substeps": [
            "Run audit-fds.sh <spec_path> --phase deep-dive-plan --ledger <ledger>.",
            "Present weakness-ranked priority queue to user via AskUserQuestion (HARD GATE -> STOP & WAIT).",
            "Optionally register weakness-object-batch / weakness-feature-batch queues, create Phase 3 tasks in TaskCreate, and mint DC-NNN.",
        ],
        "done_when": "Deep-dive priority triage confirmed in ledger.",
    },
    {
        "id": "3.02",
        "phase_label": "3.02 (6-Cat Failure & R8 Sweep)",
        "title": "6-Category Defensive Sweep, R8 Auth Propagation & R1/R3 Pass 2 (Sections 5–7)",
        "ref": "references/step-03-deep-dive-and-audits.md",
        "hard_gate": True,
        "skippable": False,
        "loop_kind": "weakness-object-batch",
        "substeps": [
            "Audit active #obj-* batch across all 6 failure categories (Boundary, Invalid Input, Adversarial/IDOR, Concurrency, Dependency Failure, and 4-part R8 Auth Propagation) + R8 quantitative alignment + R1/R3 Pass 2.",
            "Confirm edge/revocation policy forks via AskUserQuestion (HARD GATE -> STOP & WAIT).",
            "Replace [DRAFT — scaffold] failure rows in Sections 5–7 with deterministic rules and mint DC-NNN.",
        ],
        "done_when": "Section 5 #obj-* blocks contain hardened 6-category + R8 rules with zero '[DRAFT — scaffold]' stubs.",
    },
    {
        "id": "3.03",
        "phase_label": "3.03 (R2 Authz IFF Audit)",
        "title": "R2 Authorization Derivation Audit (IFF) & BDD/Verification Hardening (Section 9)",
        "ref": "references/step-03-deep-dive-and-audits.md",
        "hard_gate": True,
        "skippable": False,
        "loop_kind": "weakness-feature-batch",
        "substeps": [
            "Verify every role/ownership-gated #feat-* carries an IF-AND-ONLY-IF (IFF) predicate whose every clause maps to a #surf-* or [SEED: #boot-*].",
            "Resolve any [BLOCKED] authz gap or complex Verification Strategy fork via AskUserQuestion (HARD GATE -> STOP & WAIT).",
            "Update Sections 8 & 9 and mint DC-NNN.",
        ],
        "done_when": "Section 9 has 0 [BLOCKED] tags and gated features contain IFF authorization traces.",
    },
    {
        "id": "3.04",
        "phase_label": "3.04 (Flows, Int & NFR Hardening)",
        "title": "Flows, Integrations & NFR [DRAFT — archetype default] Hardening (Sections 10, 12, 13)",
        "ref": "references/step-03-deep-dive-and-audits.md",
        "hard_gate": True,
        "skippable": False,
        "loop_kind": None,
        "substeps": [
            "Confirm or customize remaining [DRAFT — archetype default] NFR parameters and integration retry/idempotency rules via AskUserQuestion (HARD GATE -> STOP & WAIT).",
            "Promote confirmed NFR families via fds-state.sh set-nfr --status confirmed, update Sections 10/12/13, and mint DC-NNN.",
        ],
        "done_when": "Mandatory NFRs (SEC, PERF, LOG) are settled and Sections 10/12/13 pass table structure checks.",
    },
    {
        "id": "3.05",
        "phase_label": "3.05 (R4 Bootstrap Verify)",
        "title": "R4 Day-Zero Bootstrap End-to-End Verification (Section 11)",
        "ref": "references/step-03-deep-dive-and-audits.md",
        "hard_gate": False,
        "skippable": False,
        "loop_kind": None,
        "substeps": [
            "Walk #boot-01..#boot-NN against Section 8 & Section 9 R2 predicates from 0 DB rows to every actor role's first workflow.",
            "If any circular dependency or missing seed surface exists, resolve via AskUserQuestion; update Section 11 Status to Confirmed.",
        ],
        "done_when": "Section 11 Day-Zero Bootstrap has 0 [BLOCKED] markers and valid #boot-01+ links.",
    },
    {
        "id": "3.06",
        "phase_label": "3.06 (R5 Parity Exit Gate)",
        "title": "R5 Backend/Surface Parity Exit Audit (§4.3 Hard Exit)",
        "ref": "references/step-03-deep-dive-and-audits.md",
        "hard_gate": True,
        "skippable": False,
        "loop_kind": None,
        "substeps": [
            "Run audit-fds.sh <spec_path> --phase r5-parity --ledger <ledger>.",
            "If any [ORPHAN-CAPABILITY] or [BLOCKED] item appears, resolve with user via AskUserQuestion (Add #surf-*, Defer Phase, Remove, or [CUSTOM: ... because ...]; HARD GATE -> STOP & WAIT).",
            "Re-run --phase r5-parity until exit code 0, then complete Step 3.06.",
        ],
        "done_when": "audit-fds.sh --phase r5-parity passes with 0 issues (0 [ORPHAN-CAPABILITY], 0 [BLOCKED]).",
    },
    {
        "id": "4.1",
        "phase_label": "4.1 (Residual DRAFT Sweep)",
        "title": "Phase 4 — Automated Residual [DRAFT] Inventory & Clean-Section Sign-Off",
        "ref": "references/step-04-review-finalize-retro.md",
        "hard_gate": False,
        "skippable": False,
        "loop_kind": None,
        "substeps": [
            "Read references/step-04-review-finalize-retro.md (§1) and run audit-fds.sh <spec_path> --phase review --ledger <ledger>.",
            "Emit '<Section Name>: all confirmed, moving on.' for every 0-draft section.",
            "Run fds-state.sh complete-step 4.1 (auto-skips 4.2 to 5.1 if 0 [DRAFT] tags remain).",
        ],
        "done_when": "Residual [DRAFT] inventory executed on <spec_path>.",
    },
    {
        "id": "4.2",
        "phase_label": "4.2 (DRAFT Resolution Loop)",
        "title": "Phase 4 — Batched Residual [DRAFT] Confirmation / [ACCEPTED-AS-DRAFT] Loop",
        "ref": "references/step-04-review-finalize-retro.md",
        "hard_gate": True,
        "skippable": True,
        "loop_kind": None,
        "substeps": [
            "Present 1–4 remaining [DRAFT — ...] items per turn via AskUserQuestion (Confirm / Replace / Accept As Draft; HARD GATE -> STOP & WAIT).",
            "Remove [DRAFT — ...] on confirmed rules or replace with exact '[ACCEPTED-AS-DRAFT] — Implementation may require clarification' (logged in Section 16 Appendix A).",
            "Repeat until audit-fds.sh --phase review reports 0 remaining [DRAFT] tags.",
        ],
        "done_when": "0 raw [DRAFT] tags remain in <spec_path>.",
    },
    {
        "id": "5.1",
        "phase_label": "5.1 (Canonical Finalize Gate)",
        "title": "Phase 5 — Canonical 16-Section Assembly, Metadata/TOC Sync & Finalize Audit Gate",
        "ref": "references/step-04-review-finalize-retro.md",
        "hard_gate": False,
        "skippable": False,
        "loop_kind": None,
        "substeps": [
            "Read references/step-04-review-finalize-retro.md (§2–§3); sync Section 1 Metadata (Status: Finalized, counts), Section 2 TOC, Section 3 Executive Summary, and Section 15 Changelog.",
            "Run audit-fds.sh <spec_path> --phase finalize --ledger <ledger> and fix any anchor, fluff, diagram, code-block, or table defect until exit code 0.",
            "Run fds-state.sh complete-step 5.1.",
        ],
        "done_when": "audit-fds.sh --phase finalize passes with 0 issues.",
    },
    {
        "id": "5.2",
        "phase_label": "5.2 (Spec Delivery)",
        "title": "Phase 5 — Finalized Spec Delivery & Optional D12 In-Chat Streaming",
        "ref": "references/step-04-review-finalize-retro.md",
        "hard_gate": True,
        "skippable": False,
        "loop_kind": None,
        "substeps": [
            "Present passing finalize audit summary + <spec_path> and confirm via AskUserQuestion whether on-disk delivery suffices or D12 section-chunked streaming is requested (HARD GATE -> STOP & WAIT).",
            "If D12 streaming requested, emit logical section groups pausing for user acknowledgment per chunk.",
            "Run fds-state.sh complete-step 5.2.",
        ],
        "done_when": "Finalized FDS delivery confirmed by user.",
    },
    {
        "id": "6.1",
        "phase_label": "6.1 (Friction Retrospective)",
        "title": "Phase 6 — D8 Friction Clustering & Bounded Self-Improvement Retrospective (§10)",
        "ref": "references/step-04-review-finalize-retro.md",
        "hard_gate": True,
        "skippable": False,
        "loop_kind": None,
        "substeps": [
            "Run fds-state.sh friction-report --ledger <ledger>.",
            "Present clustered friction summary via AskUserQuestion (Confirm & Close vs Log Missed Friction / Propose Bounded Preset Tweak; HARD GATE -> STOP & WAIT).",
            "Run fds-state.sh complete-step 6.1 to mark the session 100% complete.",
        ],
        "done_when": "Friction retrospective reviewed with user and session closed.",
    },
]

STEP_BY_ID: Dict[str, Dict[str, Any]] = {s["id"]: s for s in GRANULAR_STEPS}
STEP_INDEX: Dict[str, int] = {s["id"]: idx for idx, s in enumerate(GRANULAR_STEPS)}
TOTAL_STEPS = len(GRANULAR_STEPS)


def utc_today() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d")


def utc_now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def slugify(value: str) -> str:
    stem = Path(value).stem if ("/" in value or value.endswith(".md")) else value
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "-", stem.strip().lower()).strip("-")
    return cleaned or "fds-session"


def project_root() -> Path:
    env_dir = os.environ.get("CLAUDE_PROJECT_DIR", "").strip()
    return Path(env_dir).resolve() if env_dir else Path.cwd().resolve()


def resolve_spec_path(spec_rel_or_abs: str) -> Path:
    p = Path(spec_rel_or_abs)
    return p.resolve() if p.is_absolute() else (project_root() / p).resolve()


def resolve_ledger_path(explicit_ledger: str | None, slug: str | None = None) -> Path:
    root = project_root()
    if explicit_ledger:
        p = Path(explicit_ledger)
        return p.resolve() if p.is_absolute() else (root / p).resolve()
    state_dir = root / ".fds-state"
    pointer = state_dir / "active.json"
    if slug:
        return (state_dir / f"{slug}.json").resolve()
    if pointer.is_file():
        try:
            meta = json.loads(pointer.read_text(encoding="utf-8"))
            lp = meta.get("ledger_path", "")
            if lp:
                cand = Path(lp)
                return cand if cand.is_absolute() else (root / cand).resolve()
        except Exception:
            pass
    return (state_dir / "fds-session.json").resolve()


def default_loop_queues() -> Dict[str, Dict[str, Any]]:
    return {k: {"items": [], "cursor": 0} for k in sorted(LOOP_KINDS)}


def ensure_step_machine(data: Dict[str, Any]) -> None:
    """Backfills step-machine fields if loading an older v2.0 ledger."""
    if "loop_queues" not in data:
        data["loop_queues"] = default_loop_queues()
    else:
        for k in LOOP_KINDS:
            data["loop_queues"].setdefault(k, {"items": [], "cursor": 0})
    data.setdefault("completed_steps", ["0.1"])
    data.setdefault("skipped_steps", {})
    data.setdefault("session_completed", False)
    if "current_step" not in data:
        data["current_step"] = "0.2" if data.get("mode") == "intake" else "1.1"


def sync_banner_from_step(data: Dict[str, Any]) -> None:
    ensure_step_machine(data)
    if data.get("session_completed"):
        data["phase"] = "6.1 (Complete)"
        data["progress"] = f"{TOTAL_STEPS}/{TOTAL_STEPS} granular steps complete — FDS finalized & retrospective closed"
        return

    step_id = data["current_step"]
    step = STEP_BY_ID.get(step_id)
    if not step:
        return
    idx_num = STEP_INDEX[step_id] + 1
    batch_suffix = ""
    lk = step.get("loop_kind")
    if lk:
        q = data["loop_queues"].get(lk, {"items": [], "cursor": 0})
        items = q.get("items") or []
        cur = q.get("cursor", 0)
        if items and 0 <= cur < len(items):
            batch_suffix = f" [batch {cur + 1}/{len(items)}: {items[cur]}]"
    data["phase"] = step["phase_label"]
    data["progress"] = f"Step {idx_num}/{TOTAL_STEPS} — {step['title']}{batch_suffix}"


def save_ledger(path: Path, data: Dict[str, Any], update_pointer: bool = True) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data["updated_at"] = utc_now_iso()
    path.write_text(json.dumps(data, indent=2, sort_keys=False) + "\n", encoding="utf-8")
    if update_pointer:
        pointer = path.parent / "active.json"
        pointer.write_text(
            json.dumps({"ledger_path": str(path), "updated_at": data["updated_at"]}, indent=2) + "\n",
            encoding="utf-8",
        )


def load_ledger(path: Path) -> Dict[str, Any]:
    if not path.is_file():
        sys.stderr.write(f"Error: FDS ledger not found at '{path}'. Run 'fds-state.sh init --spec <path>' first.\n")
        sys.exit(1)
    data = json.loads(path.read_text(encoding="utf-8"))
    ensure_step_machine(data)
    return data


def format_banner(data: Dict[str, Any]) -> str:
    return f"Phase: {data['phase']} | Progress: {data['progress']}"


def split_csv(raw: str | None) -> List[str]:
    if not raw:
        return []
    return [item.strip() for item in raw.split(",") if item.strip()]


def split_batches(raw: str | None) -> List[str]:
    if not raw:
        return []
    if ";" in raw:
        return [b.strip() for b in raw.split(";") if b.strip()]
    return [b.strip() for b in raw.split(",") if b.strip()]


def run_quiet_audit(spec_file: Path, phase: str, ledger_path: Path) -> Tuple[int, str]:
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        rc = audit_fds.run_cli_gate(spec_file, phase, str(ledger_path), as_json=False)
    return rc, buf.getvalue().strip()


def format_step_guidance(data: Dict[str, Any]) -> str:
    ensure_step_machine(data)
    lines = [format_banner(data)]
    if data.get("session_completed"):
        lines.append("Active Step: COMPLETE — All 30 granular steps finished.")
        return "\n".join(lines)

    step_id = data["current_step"]
    step = STEP_BY_ID[step_id]
    lk = step.get("loop_kind")
    batch_line = ""
    if lk:
        q = data["loop_queues"].get(lk, {"items": [], "cursor": 0})
        items = q.get("items") or []
        cur = q.get("cursor", 0)
        if items and 0 <= cur < len(items):
            batch_line = f" (Batch {cur + 1}/{len(items)}: {items[cur]})"

    gate_str = "YES — AskUserQuestion (max 4 single-theme questions), then STOP & WAIT" if step["hard_gate"] else "NO — deterministic check/synthesis step"
    lines.append(f"Active Step: {step['id']} — {step['title']}{batch_line}")
    lines.append(f"Step Reference (load ONLY this file now): {step['ref']}")
    lines.append(f"Hard Gate: {gate_str}")
    lines.append("Numbered Substeps:")
    for i, sub in enumerate(step["substeps"], 1):
        lines.append(f"  {i}. {sub}")
    lines.append(f"Done When: {step['done_when']}")
    return "\n".join(lines)


def verify_step_done_when(step_id: str, data: Dict[str, Any], ledger_path: Path) -> Optional[str]:
    """Returns None when the step's exit criterion passes, or an actionable error message."""
    spec_file = resolve_spec_path(data["spec_path"])
    active_dcs = [d for d in data["decision_contexts"] if d.get("status") == "active"]

    if step_id == "0.1":
        if data["chunked_mode"]["active"]:
            return "Chunked Mode is still active; finish with '/done' ('fds-state.sh chunk done') first."
        return None

    if step_id == "0.2":
        if not spec_file.is_file():
            return f"Target spec '{spec_file}' does not exist yet. Run 'fds-state.sh seed-spec' and map intake facts first."
        if not active_dcs:
            return "Record intake triage confirmation via 'fds-state.sh add-dc' before completing Step 0.2."
        return None

    if step_id == "1.1":
        return None

    if step_id == "1.2":
        if not data.get("intent_aligned"):
            return "MUST #1 violation: pass --intent-aligned only after the user confirms 1st/2nd/3rd-order intent."
        if not active_dcs:
            return "Mint DC-001 via 'fds-state.sh add-dc' capturing confirmed 3-order intent before completing Step 1.2."
        return None

    if step_id == "1.3":
        if not data.get("lineup_approved"):
            return "Approve section lineup first via 'fds-state.sh lineup ... --approve'."
        if not spec_file.is_file():
            return f"Target spec '{spec_file}' has not been seeded yet. Run 'fds-state.sh seed-spec'."
        return None

    if not data.get("intent_aligned"):
        return "MUST #1 violation: intent_aligned is false."

    if not spec_file.is_file():
        return f"Target spec '{spec_file}' is missing on disk."

    text = spec_file.read_text(encoding="utf-8", errors="ignore")
    lines = text.splitlines()
    h2_secs = audit_fds.split_h2_sections(lines)
    sec_by_key = {s["key"]: s for s in h2_secs if s["key"]}

    if step_id == "2.01":
        p_sec = sec_by_key.get("phase-scope")
        if not p_sec:
            return "Section 4 (Phase Scope Summary) is missing from spec."
        p_body = "\n".join(p_sec["lines"])
        if "<Minimum complete end-to-end workflow>" in p_body:
            return "Section 4 still contains unedited template placeholder '<Minimum complete end-to-end workflow>'."
        return None

    if step_id == "2.02":
        items = data["loop_queues"]["object-batch"]["items"]
        if not items:
            return "Register >= 1 object batch first via 'fds-state.sh register-items --kind object-batch --items \"#obj-...\"'."
        return None

    if step_id == "2.03":
        c_sec = sec_by_key.get("core-objects")
        if not c_sec:
            return "Section 5 (Core Objects) is missing from spec."
        c_body = "\n".join(c_sec["lines"])
        q = data["loop_queues"]["object-batch"]
        is_last_batch = (not q["items"]) or (q["cursor"] >= len(q["items"]) - 1)
        if is_last_batch and "{#obj-example}" in c_body:
            return "Section 5 still contains template stub '{#obj-example}'. Replace it with real domain #obj-* blocks."
        if not re.search(r"\{#obj-[a-z0-9-]+\}", c_body):
            return "Section 5 has no '{#obj-<slug>}' object definitions yet."
        return None

    if step_id == "2.04":
        r_sec = sec_by_key.get("relationship-map")
        if not r_sec:
            return "Section 6 (Central Relationship Map) is missing from spec."
        r_body = "\n".join(r_sec["lines"])
        if "#obj-parent-example" in r_body:
            return "Section 6 still contains template placeholder '#obj-parent-example'."
        if "on_delete" not in r_body.lower() and "none" not in r_body.lower():
            return "Section 6 must specify explicit R3 'on_delete' rules (or explicit 'None' for single-object scope)."
        return None

    if step_id == "2.05":
        c_sec = sec_by_key.get("core-objects")
        c_body = "\n".join(c_sec["lines"]) if c_sec else ""
        q = data["loop_queues"]["stateful-batch"]
        is_last = (not q["items"]) or (q["cursor"] >= len(q["items"]) - 1)
        if is_last and "[DRAFT — lifecycle settled in Step 2.05]" in c_body:
            return "Section 5 still has unresolved '[DRAFT — lifecycle settled in Step 2.05]' placeholders."
        if "forbidden" not in c_body.lower() and "stateless" not in c_body.lower():
            return "Section 5 must specify Forbidden Transitions (D4) for stateful objects or 'None — stateless'."
        return None

    if step_id == "2.06":
        s_sec = sec_by_key.get("surface-inventory")
        s_body = "\n".join(s_sec["lines"]) if s_sec else ""
        if "#surf-example-create" in s_body or "#surf-" not in s_body:
            return "Section 8 (Surface Inventory) must contain concrete '#surf-*' rows (remove '#surf-example-create')."
        return None

    if step_id == "2.07":
        f_sec = sec_by_key.get("features")
        f_body = "\n".join(f_sec["lines"]) if f_sec else ""
        q = data["loop_queues"]["feature-batch"]
        is_last = (not q["items"]) or (q["cursor"] >= len(q["items"]) - 1)
        if is_last and "{#feat-example}" in f_body:
            return "Section 9 still contains template stub '{#feat-example}'."
        if not re.search(r"\{#feat-[a-z0-9-]+\}", f_body) or "Given" not in f_body:
            return "Section 9 must define '#feat-*' blocks with Given/When/Then BDD scenarios."
        return None

    if step_id == "2.08a":
        fl_sec = sec_by_key.get("user-flows")
        fl_body = "\n".join(fl_sec["lines"]) if fl_sec else ""
        if not re.search(r"\{#flow-[a-z0-9-]+\}", fl_body):
            return "Draft the active '#flow-*' header and Happy Path steps in Section 10 before completing Step 2.08a."
        return None

    if step_id == "2.08b":
        fl_sec = sec_by_key.get("user-flows")
        fl_body = "\n".join(fl_sec["lines"]) if fl_sec else ""
        q = data["loop_queues"]["flow-batch"]
        is_last = (not q["items"]) or (q["cursor"] >= len(q["items"]) - 1)
        if is_last and "{#flow-example}" in fl_body:
            return "Section 10 still contains template stub '{#flow-example}'."
        if "postcondition" not in fl_body.lower():
            return "Section 10 must state explicit Postconditions for Happy and Exception paths."
        return None

    if step_id == "2.09":
        pending = [k for k, v in data["sections"].items() if v.get("status") == "pending"]
        if pending:
            return f"Conditional sections still 'pending' in ledger: {', '.join(pending)}. Include or exclude via 'fds-state.sh lineup'."
        return None

    if step_id == "2.10":
        unset = [f for f in ("SEC", "PERF", "LOG", "SCALE") if data["nfr"][f]["status"] == "unconfirmed"]
        if unset:
            return f"Step 2.10 Batch A NFRs still unconfirmed in ledger: {', '.join(unset)}. Record via 'fds-state.sh set-nfr'."
        return None

    if step_id == "2.11":
        unset = [f for f in sorted(ALL_NFR) if data["nfr"][f]["status"] == "unconfirmed"]
        if unset:
            return f"Step 2.11 NFR families still unconfirmed in ledger: {', '.join(unset)}. Record via 'fds-state.sh set-nfr'."
        if data["nfr"]["OBS"]["archetype"] in {"OBS-2", "OBS-3", "OBS-4"} and "#nfr-observability-components" not in text:
            return "OBS-2+ selected (§7.4): Section 13.6 must include '#### Observability Component Matrix {#nfr-observability-components}'."
        if data["nfr"]["PRIV"]["archetype"] in {"PRIV-2", "PRIV-3", "PRIV-4"} and "#nfr-pii-inventory" not in text:
            return "PRIV-2+ selected (§7.4): Section 13.8 must include '#### PII Inventory {#nfr-pii-inventory}'."
        return None

    if step_id == "2.12":
        b_sec = sec_by_key.get("day-zero-bootstrap")
        b_body = "\n".join(b_sec["lines"]) if b_sec else ""
        if "#boot-01" not in b_body or "#surf-example-create" in b_body:
            return "Section 11 (Day-Zero Bootstrap) must define real '#boot-01' rows without '#surf-example-create'."
        return None

    if step_id == "2.13":
        rc, out = run_quiet_audit(spec_file, "scaffold", ledger_path)
        if rc != 0:
            return f"Phase 2 Scaffold exit audit failed:\n{out}"
        return None

    if step_id == "3.01":
        return None

    if step_id == "3.02":
        c_sec = sec_by_key.get("core-objects")
        c_body = "\n".join(c_sec["lines"]) if c_sec else ""
        q = data["loop_queues"]["weakness-object-batch"]
        is_last = (not q["items"]) or (q["cursor"] >= len(q["items"]) - 1)
        if is_last and "[DRAFT — scaffold]" in c_body:
            return "Section 5 still contains unhardened '[DRAFT — scaffold]' failure stubs; complete the 6-category + R8 sweep."
        return None

    if step_id == "3.03":
        f_sec = sec_by_key.get("features")
        f_body = "\n".join(f_sec["lines"]) if f_sec else ""
        q = data["loop_queues"]["weakness-feature-batch"]
        is_last = (not q["items"]) or (q["cursor"] >= len(q["items"]) - 1)
        if is_last and "[BLOCKED" in f_body:
            return "Section 9 still contains unresolved '[BLOCKED...]' authorization markers."
        return None

    if step_id == "3.04":
        return None

    if step_id == "3.05":
        b_sec = sec_by_key.get("day-zero-bootstrap")
        b_body = "\n".join(b_sec["lines"]) if b_sec else ""
        if "[BLOCKED" in b_body:
            return "Section 11 Day-Zero Bootstrap still contains '[BLOCKED...]' markers."
        return None

    if step_id == "3.06":
        rc, out = run_quiet_audit(spec_file, "r5-parity", ledger_path)
        if rc != 0:
            return f"Phase 3 R5 Parity exit audit failed:\n{out}"
        return None

    if step_id == "4.1":
        return None

    if step_id == "4.2":
        tags = audit_fds.extract_active_tags(lines)
        if tags["draft"]:
            first_ln, first_tok = tags["draft"][0]
            return (
                f"{len(tags['draft'])} unresolved [DRAFT] tag(s) remain (e.g., L{first_ln}: {first_tok}). "
                "Confirm and strip tag, or convert to '[ACCEPTED-AS-DRAFT] — Implementation may require clarification'."
            )
        return None

    if step_id == "5.1":
        rc, out = run_quiet_audit(spec_file, "finalize", ledger_path)
        if rc != 0:
            return f"Phase 5 Finalize audit failed:\n{out}"
        return None

    if step_id in {"5.2", "6.1"}:
        return None

    return None


def advance_step_pointer(data: Dict[str, Any], completed_id: str, spec_file: Optional[Path] = None) -> None:
    """Advances current_step accounting for per-batch loops and two-gate flow-batch (2.08a <-> 2.08b)."""
    step = STEP_BY_ID[completed_id]
    lk = step.get("loop_kind")

    # Special paired two-gate loop for Domain 7 User Flows: 2.08a (batch k) -> 2.08b (batch k) -> 2.08a (batch k+1) -> 2.09
    if completed_id == "2.08a":
        data["current_step"] = "2.08b"
        if completed_id not in data["completed_steps"]:
            data["completed_steps"].append(completed_id)
        sync_banner_from_step(data)
        return

    if completed_id == "2.08b":
        q = data["loop_queues"]["flow-batch"]
        items = q.get("items") or []
        if items and q["cursor"] + 1 < len(items):
            q["cursor"] += 1
            data["current_step"] = "2.08a"
            sync_banner_from_step(data)
            return
        if "2.08b" not in data["completed_steps"]:
            data["completed_steps"].append("2.08b")
        data["current_step"] = "2.09"
        sync_banner_from_step(data)
        return

    # Standard single-step batch loops (2.03, 2.05, 2.07, 3.02, 3.03)
    if lk:
        q = data["loop_queues"][lk]
        items = q.get("items") or []
        if items and q["cursor"] + 1 < len(items):
            q["cursor"] += 1
            sync_banner_from_step(data)
            return

    if completed_id not in data["completed_steps"]:
        data["completed_steps"].append(completed_id)

    if completed_id == "6.1":
        data["session_completed"] = True
        sync_banner_from_step(data)
        return

    next_idx = STEP_INDEX[completed_id] + 1
    next_id = GRANULAR_STEPS[next_idx]["id"]

    # Auto-skip 0.2 in 'new' mode with explicit D9 record
    if next_id == "0.2" and data.get("mode") == "new":
        data["skipped_steps"]["0.2"] = "Skipped Step 0.2 (Reverse Intake) because session initialized in greenfield 'new' mode."
        next_id = "1.1"

    # Auto-skip 4.2 when Step 4.1 finds 0 residual [DRAFT] tags
    if completed_id == "4.1" and spec_file and spec_file.is_file():
        tags = audit_fds.extract_active_tags(spec_file.read_text(encoding="utf-8", errors="ignore").splitlines())
        if not tags["draft"]:
            data["skipped_steps"]["4.2"] = "Skipped Step 4.2 (Residual DRAFT Loop) because Step 4.1 confirmed 0 remaining [DRAFT] tags."
            if "4.2" not in data["completed_steps"]:
                data["completed_steps"].append("4.2")
            next_id = "5.1"

    data["current_step"] = next_id
    sync_banner_from_step(data)


def cmd_init(args: argparse.Namespace) -> None:
    slug = args.slug or slugify(args.spec)
    ledger_path = resolve_ledger_path(args.ledger, slug=slug)

    nfr_status = {}
    for fam in sorted(ALL_NFR):
        posture = "mandatory" if fam in MANDATORY_NFR else "conditional"
        nfr_status[fam] = {
            "posture": posture,
            "status": "unconfirmed",
            "archetype": None,
            "note": "",
        }

    skipped: Dict[str, str] = {}
    first_step = "0.2"
    if args.mode == "new":
        first_step = "1.1"
        skipped["0.2"] = "Skipped Step 0.2 (Reverse Intake) because session initialized in greenfield 'new' mode."

    data: Dict[str, Any] = {
        "schema_version": "2.1",
        "meta_prompt_version": f"FDS-Builder-Skill 2.1 ({utc_today()})",
        "slug": slug,
        "mode": args.mode,
        "spec_path": args.spec,
        "current_step": first_step,
        "completed_steps": ["0.1"],
        "skipped_steps": skipped,
        "session_completed": False,
        "loop_queues": default_loop_queues(),
        "phase": "",
        "progress": "",
        "intent_aligned": False,
        "lineup_approved": False,
        "chunked_mode": {"active": False, "chunks": []},
        "sections": json.loads(json.dumps(DEFAULT_SECTIONS)),
        "nfr": nfr_status,
        "decision_contexts": [],
        "friction_log": [],
        "created_at": utc_now_iso(),
        "updated_at": utc_now_iso(),
    }
    sync_banner_from_step(data)
    save_ledger(ledger_path, data, update_pointer=True)
    print(format_step_guidance(data))
    print(f"Ledger initialized: {ledger_path}")


def cmd_current_step(args: argparse.Namespace) -> None:
    ledger_path = resolve_ledger_path(args.ledger)
    data = load_ledger(ledger_path)
    if args.json:
        step_id = data["current_step"]
        step = STEP_BY_ID.get(step_id)
        lk = step.get("loop_kind") if step else None
        q = data["loop_queues"].get(lk) if lk else None
        print(
            json.dumps(
                {
                    "banner": format_banner(data),
                    "session_completed": data.get("session_completed", False),
                    "current_step": step,
                    "loop_queue": q,
                    "completed_steps": data["completed_steps"],
                    "skipped_steps": data["skipped_steps"],
                },
                indent=2,
            )
        )
        return
    print(format_step_guidance(data))


def cmd_register_items(args: argparse.Namespace) -> None:
    ledger_path = resolve_ledger_path(args.ledger)
    data = load_ledger(ledger_path)
    kind = args.kind.strip()
    items = split_batches(args.items)
    if not items:
        sys.stderr.write("Error: --items must contain at least one batch (separate batches with ';').\n")
        sys.exit(1)
    data["loop_queues"][kind] = {"items": items, "cursor": 0}
    sync_banner_from_step(data)
    save_ledger(ledger_path, data)
    print(f"Registered {len(items)} batch(es) for '{kind}':")
    for idx, b in enumerate(items, 1):
        print(f"  Batch {idx}/{len(items)}: {b}")
    print(format_banner(data))


def cmd_complete_step(args: argparse.Namespace) -> None:
    ledger_path = resolve_ledger_path(args.ledger)
    data = load_ledger(ledger_path)
    req_step = args.step_id.strip()

    if req_step not in STEP_BY_ID:
        valid = ", ".join(s["id"] for s in GRANULAR_STEPS)
        sys.stderr.write(f"Error: Unknown step_id '{req_step}'. Valid granular steps: {valid}\n")
        sys.exit(1)

    # Idempotent allowance for 0.1 (auto-completed during init)
    if req_step == "0.1" and "0.1" in data["completed_steps"]:
        print(format_step_guidance(data))
        return

    cur_step = data["current_step"]
    if req_step != cur_step:
        sys.stderr.write(
            f"Error (Granular Step Order): Cannot complete Step '{req_step}' while active step is '{cur_step}'. "
            f"Run 'fds-state.sh current-step' and finish '{cur_step}' first.\n"
        )
        sys.exit(1)

    if args.intent_aligned:
        data["intent_aligned"] = True

    step_meta = STEP_BY_ID[req_step]
    spec_file = resolve_spec_path(data["spec_path"])

    if args.skip_reason:
        if not step_meta["skippable"]:
            sys.stderr.write(f"Error: Step '{req_step}' ({step_meta['title']}) is mandatory and cannot be skipped.\n")
            sys.exit(1)
        reason = args.skip_reason.strip()
        data["skipped_steps"][req_step] = reason
        if req_step not in data["completed_steps"]:
            data["completed_steps"].append(req_step)
        next_idx = STEP_INDEX[req_step] + 1
        data["current_step"] = GRANULAR_STEPS[next_idx]["id"]
        sync_banner_from_step(data)
        save_ledger(ledger_path, data)
        print(f"D9 Skip Recorded for Step {req_step}: {reason}")
        print(format_step_guidance(data))
        return

    err = verify_step_done_when(req_step, data, ledger_path)
    if err is not None:
        sys.stderr.write(f"Error (Step {req_step} 'done when' check not met): {err}\n")
        sys.exit(1)

    advance_step_pointer(data, req_step, spec_file=spec_file)
    save_ledger(ledger_path, data)
    for auto_k in ("0.2", "4.2"):
        if auto_k in data.get("skipped_steps", {}) and req_step in {"0.1", "4.1"}:
            print(f"D9 Notice: {data['skipped_steps'][auto_k]}")
    print(format_step_guidance(data))


def cmd_skip_to_deep_dive(args: argparse.Namespace) -> None:
    ledger_path = resolve_ledger_path(args.ledger)
    data = load_ledger(ledger_path)
    if not data.get("intent_aligned") or not data.get("lineup_approved"):
        sys.stderr.write("Error: Complete Phase 1 Intent Gate (1.2) and Section Lineup (1.3) before skipping to Deep-Dive.\n")
        sys.exit(1)

    spec_file = resolve_spec_path(data["spec_path"])
    rc, out = run_quiet_audit(spec_file, "scaffold", ledger_path)
    if rc != 0:
        sys.stderr.write(
            "Error: Existing spec does not yet pass Phase 2 Scaffold audit; fill missing Scaffold domains first:\n"
            f"{out}\n"
        )
        sys.exit(1)

    reason = args.reason.strip()
    for s in GRANULAR_STEPS:
        if s["id"].startswith("2."):
            data["skipped_steps"][s["id"]] = f"Fast-forwarded in intake mode ({reason}); verified by --phase scaffold PASS."
            if s["id"] not in data["completed_steps"]:
                data["completed_steps"].append(s["id"])
    data["current_step"] = "3.01"
    sync_banner_from_step(data)
    save_ledger(ledger_path, data)
    print(f"D9 Intake Fast-Forward Verified (--phase scaffold PASS): {reason}")
    print(format_step_guidance(data))


def cmd_seed_spec(args: argparse.Namespace) -> None:
    ledger_path = resolve_ledger_path(args.ledger)
    data = load_ledger(ledger_path)
    spec_file = resolve_spec_path(data["spec_path"])

    if spec_file.is_file() and not args.force:
        print(f"Spec already exists on disk (use --force to overwrite): {spec_file}")
        return

    tpl_path = SKILL_DIR / "assets" / "fds-16-section-template.md"
    if not tpl_path.is_file():
        sys.stderr.write(f"Error: Template missing at '{tpl_path}'.\n")
        sys.exit(1)

    content = tpl_path.read_text(encoding="utf-8")
    title = (args.title or data["slug"].replace("-", " ").title()).strip()
    today = utc_today()
    active_dcs = [d for d in data["decision_contexts"] if d.get("status") == "active"]
    dc1_summary = active_dcs[0]["summary"] if active_dcs else "Established 3-order intent alignment and initial system boundary"

    content = content.replace("<System Name>", title)
    content = content.replace("`YYYY-MM-DD`", f"`{today}`")
    content = content.replace("FDS-Builder-Skill 2.0 (2026-10-29)", data["meta_prompt_version"])
    content = content.replace(
        "Established 3-order intent alignment and initial system boundary",
        dc1_summary,
    )

    secs = data["sections"]
    if secs["integrations"]["status"] == "excluded":
        rat = secs["integrations"]["rationale"]
        content = re.sub(
            r"### 12\.1 External Integrations \{#int-overview\}\n\n<Populate[^\n]+>",
            f"### 12.1 External Integrations {{#int-overview}}\n\nExcluded per approved lineup because {rat}",
            content,
        )
    if secs["data-migration"]["status"] == "excluded":
        rat = secs["data-migration"]["rationale"]
        content = re.sub(
            r"### 12\.2 Legacy Data Migration \(`§6\.8`\) \{#int-data-migration\}\n\n<Populate[^\n]+>",
            f"### 12.2 Legacy Data Migration (`§6.8`) {{#int-data-migration}}\n\nExcluded per approved lineup because {rat}",
            content,
        )
    if secs["anti-patterns"]["status"] == "excluded":
        rat = secs["anti-patterns"]["rationale"]
        content = re.sub(
            r"## 14\. Anti-Pattern Register \{#sec-anti-patterns\}\n\n\| ID \|.*?\n\| `#ap-01` \|[^\n]+",
            f"## 14. Anti-Pattern Register {{#sec-anti-patterns}}\n\nExcluded per approved lineup because {rat}",
            content,
            flags=re.DOTALL,
        )

    spec_file.parent.mkdir(parents=True, exist_ok=True)
    spec_file.write_text(content, encoding="utf-8")
    print(f"Seeded canonical 16-section FDS skeleton: {spec_file}")


def cmd_status(args: argparse.Namespace) -> None:
    ledger_path = resolve_ledger_path(args.ledger)
    data = load_ledger(ledger_path)
    if args.json:
        print(json.dumps(data, indent=2))
        return

    active_dcs = [d for d in data["decision_contexts"] if d.get("status") == "active"]
    rolled_dcs = [d for d in data["decision_contexts"] if d.get("status") == "rolled_back"]
    unconfirmed_nfr = [k for k, v in data["nfr"].items() if v["status"] == "unconfirmed"]
    crit_secs = [k for k, v in data["sections"].items() if v.get("critical")]

    print(format_banner(data))
    print(f"Spec Path: {data['spec_path']} | Active Granular Step: {data['current_step']} ({len(data['completed_steps'])}/{TOTAL_STEPS} done)")
    print(
        f"Intent Aligned: {data['intent_aligned']} | Lineup Approved: {data['lineup_approved']} "
        f"| Chunked Mode: {data['chunked_mode']['active']} ({len(data['chunked_mode']['chunks'])} chunks)"
    )
    print(f"Critical Sections: {', '.join(crit_secs)}")
    print(
        f"Decision Contexts: {len(active_dcs)} active ({len(rolled_dcs)} rolled back) "
        f"| Unresolved NFR Families: {', '.join(unconfirmed_nfr) if unconfirmed_nfr else 'None'} "
        f"| Friction Events: {len(data['friction_log'])}"
    )


def cmd_set_phase(args: argparse.Namespace) -> None:
    ledger_path = resolve_ledger_path(args.ledger)
    data = load_ledger(ledger_path)
    if args.intent_aligned:
        data["intent_aligned"] = True

    phase_str = args.phase.strip()
    major_match = re.match(r"^(\d+)", phase_str)
    if major_match:
        major = int(major_match.group(1))
        if major >= 2 and not data["intent_aligned"]:
            sys.stderr.write(
                "Error (MUST #1): Cannot enter Phase 2+ before 3-Order Intent Alignment Gate passes. "
                "Complete Step 1.2 and pass --intent-aligned once confirmed by user.\n"
            )
            sys.exit(1)

    step_prefix = phase_str.split()[0]
    if step_prefix in STEP_BY_ID:
        data["current_step"] = step_prefix
        sync_banner_from_step(data)
    data["phase"] = phase_str
    if args.progress:
        data["progress"] = args.progress.strip()
    save_ledger(ledger_path, data)
    print(format_banner(data))


def cmd_lineup(args: argparse.Namespace) -> None:
    ledger_path = resolve_ledger_path(args.ledger)
    data = load_ledger(ledger_path)
    sections = data["sections"]

    inc_list = split_csv(args.include)
    exc_list = split_csv(args.exclude)
    crit_list = split_csv(args.critical)
    untag_list = split_csv(args.untag_critical)

    for sec in inc_list + exc_list + crit_list + untag_list:
        if sec not in sections:
            valid = ", ".join(sorted(sections.keys()))
            sys.stderr.write(f"Error: Unknown section id '{sec}'. Valid ids: {valid}\n")
            sys.exit(1)

    for sec in exc_list:
        if sec == "day-zero-bootstrap":
            sys.stderr.write("Error (§4.2, D21): 'day-zero-bootstrap' is mandatory critical and cannot be excluded.\n")
            sys.exit(1)
        if sec in CORE_LOCKED_INCLUDED:
            sys.stderr.write(f"Error: Core canonical section '{sec}' cannot be excluded.\n")
            sys.exit(1)
        if not args.rationale:
            sys.stderr.write(f"Error (P10, §4.2): Excluding '{sec}' requires --rationale citing session evidence.\n")
            sys.exit(1)
        sections[sec]["status"] = "excluded"
        sections[sec]["rationale"] = args.rationale.strip()

    for sec in inc_list:
        sections[sec]["status"] = "included"
        if args.rationale:
            sections[sec]["rationale"] = args.rationale.strip()

    for sec in untag_list:
        if sec == "day-zero-bootstrap" or sections[sec].get("locked_critical"):
            sys.stderr.write("Error (§4.2, §5.6): 'day-zero-bootstrap' is permanently critical and cannot be untagged.\n")
            sys.exit(1)
        sections[sec]["critical"] = False
        sections[sec]["weight"] = 2 if sec not in {"metadata", "toc", "executive-summary", "anti-patterns", "changelog", "appendices"} else 1

    for sec in crit_list:
        sections[sec]["critical"] = True
        sections[sec]["weight"] = 3

    sections["day-zero-bootstrap"]["status"] = "included"
    sections["day-zero-bootstrap"]["critical"] = True
    sections["day-zero-bootstrap"]["weight"] = 3

    if args.approve:
        for sec, info in sections.items():
            if info["status"] == "pending":
                info["status"] = "included"
        data["lineup_approved"] = True

    save_ledger(ledger_path, data)
    included = [k for k, v in sections.items() if v["status"] == "included"]
    excluded = [k for k, v in sections.items() if v["status"] == "excluded"]
    critical = [k for k, v in sections.items() if v["critical"]]
    print(f"Lineup updated (approved={data['lineup_approved']}):")
    print(f"  Included ({len(included)}): {', '.join(included)}")
    print(f"  Excluded ({len(excluded)}): {', '.join(excluded) if excluded else 'None'}")
    print(f"  Critical ({len(critical)}): {', '.join(critical)}")


def cmd_set_nfr(args: argparse.Namespace) -> None:
    ledger_path = resolve_ledger_path(args.ledger)
    data = load_ledger(ledger_path)
    fam = args.family.strip().upper()
    if fam not in ALL_NFR:
        sys.stderr.write(f"Error: Unknown NFR family '{fam}'. Choose from: {', '.join(sorted(ALL_NFR))}\n")
        sys.exit(1)

    status = args.status.strip().lower()
    if status == "skipped":
        if fam in MANDATORY_NFR:
            sys.stderr.write(f"Error (§7.5): NFR family '{fam}' is ALWAYS active and cannot be skipped.\n")
            sys.exit(1)
        if not (args.note and args.note.strip()):
            sys.stderr.write(
                f"Error (§7.5, D9): Skipping conditional NFR '{fam}' requires explicit user confirmation recorded via --note.\n"
            )
            sys.exit(1)
        data["nfr"][fam]["status"] = "skipped"
        data["nfr"][fam]["archetype"] = None
        data["nfr"][fam]["note"] = args.note.strip()
    else:
        arch = (args.archetype or "").strip().upper()
        if not arch:
            sys.stderr.write(f"Error: Status '{status}' for NFR '{fam}' requires --archetype (e.g., {fam}-2 or CUSTOM).\n")
            sys.exit(1)
        if arch != "CUSTOM" and arch not in VALID_ARCHETYPES[fam]:
            valid_tiers = ", ".join(sorted(VALID_ARCHETYPES[fam]))
            sys.stderr.write(f"Error: Invalid archetype '{arch}' for {fam}. Valid tiers: {valid_tiers}, CUSTOM\n")
            sys.exit(1)
        data["nfr"][fam]["status"] = status
        data["nfr"][fam]["archetype"] = arch
        if args.note:
            data["nfr"][fam]["note"] = args.note.strip()

    save_ledger(ledger_path, data)
    entry = data["nfr"][fam]
    extra = ""
    if fam == "PRIV" and entry["archetype"] in {"PRIV-2", "PRIV-3", "PRIV-4"}:
        extra = " [NOTE §7.4: PRIV-2+ selected -> PII Inventory table is MANDATORY]"
    elif fam == "OBS" and entry["archetype"] in {"OBS-2", "OBS-3", "OBS-4"}:
        extra = " [NOTE §7.4: OBS-2+ selected -> Observability Component table is MANDATORY]"
    elif fam == "SCALE" and entry["status"] != "skipped":
        extra = " [NOTE §7.3: Quantitative QPS/TPS, horizon, burst, concurrency & scaling ratio are MANDATORY]"
    print(f"NFR {fam}: status={entry['status']}, archetype={entry['archetype']}{extra}")


def cmd_add_dc(args: argparse.Namespace) -> None:
    ledger_path = resolve_ledger_path(args.ledger)
    data = load_ledger(ledger_path)

    next_num = len(data["decision_contexts"]) + 1
    dc_id = f"DC-{next_num:03d}"
    anchors = split_csv(args.anchors)
    deps = split_csv(args.depends_on)
    known_ids = {d["id"] for d in data["decision_contexts"]}
    for dep in deps:
        if dep not in known_ids:
            sys.stderr.write(f"Error: Unknown upstream dependency '{dep}'. Known DCs: {', '.join(sorted(known_ids)) or 'None'}\n")
            sys.exit(1)

    summary = args.summary.strip()
    custom_rat = (args.custom_rationale or "").strip()
    if "[CUSTOM" in summary and "because" not in summary.lower() and not custom_rat:
        sys.stderr.write("Error (MUST #13, D7): [CUSTOM] decisions must state a 'because <reason>' rationale.\n")
        sys.exit(1)

    phase_val = (args.phase or data["current_step"]).strip()
    record = {
        "id": dc_id,
        "phase": phase_val,
        "date": utc_today(),
        "summary": summary,
        "custom_rationale": custom_rat,
        "anchors": anchors,
        "depends_on": deps,
        "status": "active",
        "created_at": utc_now_iso(),
    }
    data["decision_contexts"].append(record)
    save_ledger(ledger_path, data)

    anchor_str = ", ".join(f"`{a}`" for a in anchors) if anchors else "`#sec-metadata`"
    print(f"Minted {dc_id} (Step {phase_val}): {summary}")
    print(f"Changelog row: | `{dc_id}` | `{record['date']}` | `draft` | `Step {phase_val}` | {summary} | {anchor_str} |")


def cmd_rollback_dc(args: argparse.Namespace) -> None:
    ledger_path = resolve_ledger_path(args.ledger)
    data = load_ledger(ledger_path)
    target_id = args.dc_id.strip().upper()

    by_id = {d["id"]: d for d in data["decision_contexts"]}
    if target_id not in by_id:
        sys.stderr.write(f"Error: Decision Context '{target_id}' not found in ledger.\n")
        sys.exit(1)

    impacted: List[str] = [target_id]
    seen: Set[str] = {target_id}
    changed = True
    while changed:
        changed = False
        for d in data["decision_contexts"]:
            if d["id"] not in seen and any(parent in seen for parent in d.get("depends_on", [])):
                seen.add(d["id"])
                impacted.append(d["id"])
                changed = True

    affected_anchors: List[str] = []
    for dc_key in impacted:
        rec = by_id[dc_key]
        rec["status"] = "rolled_back"
        rec["rollback_reason"] = args.reason.strip()
        rec["rolled_back_at"] = utc_now_iso()
        for anc in rec.get("anchors", []):
            if anc not in affected_anchors:
                affected_anchors.append(anc)

    save_ledger(ledger_path, data)
    print(f"Atomic Rollback Executed (P13 / §5.10) for {target_id}:")
    print(f"  Rolled-back Decision Contexts ({len(impacted)}): {', '.join(impacted)}")
    print(f"  Downstream Anchors Requiring Immediate Propagation: {', '.join(affected_anchors) if affected_anchors else '(inspect spec sections)'}")
    print("  Mandatory Post-Rollback Gates: Re-run R2 (authz traces), R4 (Day-Zero bootstrap), and R5 (audit-fds.sh --phase r5-parity).")


def cmd_log_friction(args: argparse.Namespace) -> None:
    ledger_path = resolve_ledger_path(args.ledger)
    data = load_ledger(ledger_path)
    cat = args.category.strip().lower()
    if cat not in FRICTION_CATEGORIES:
        valid = ", ".join(sorted(FRICTION_CATEGORIES))
        sys.stderr.write(f"Error: Invalid friction category '{cat}'. Valid categories: {valid}\n")
        sys.exit(1)

    fid = f"FR-{len(data['friction_log']) + 1:03d}"
    entry = {
        "id": fid,
        "category": cat,
        "phase": data["phase"],
        "dc_id": (args.dc or "").strip() or None,
        "summary": args.summary.strip(),
        "created_at": utc_now_iso(),
    }
    data["friction_log"].append(entry)
    save_ledger(ledger_path, data)
    print(f"Logged friction {fid} [{cat}]: {entry['summary']}")


def cmd_friction_report(args: argparse.Namespace) -> None:
    ledger_path = resolve_ledger_path(args.ledger)
    data = load_ledger(ledger_path)
    clusters: Dict[str, List[Dict[str, Any]]] = {}
    for item in data["friction_log"]:
        clusters.setdefault(item["category"], []).append(item)

    report = []
    for cat in sorted(clusters.keys()):
        events = clusters[cat]
        significant = len(events) >= 2 or cat in STRUCTURAL_FRICTION
        report.append(
            {
                "category": cat,
                "count": len(events),
                "significant_for_refinement": significant,
                "disposition": (
                    "SIGNIFICANT — candidate for bounded §10.4 template/MCQ/archetype refinement after user confirmation"
                    if significant
                    else "ONE-OFF — review with user; do not over-fit process rules (§10.4)"
                ),
                "events": events,
            }
        )

    if args.json:
        print(json.dumps({"total_events": len(data["friction_log"]), "clusters": report}, indent=2))
        return

    if not report:
        print("Friction Retrospective (§10): 0 friction events logged during this session.")
        return

    print(f"Friction Retrospective (§10): {len(data['friction_log'])} event(s) across {len(report)} root-cause cluster(s):")
    for cl in report:
        print(f"- {cl['category']} ({cl['count']} event(s)) -> {cl['disposition']}")
        for ev in cl["events"]:
            dc_note = f" [{ev['dc_id']}]" if ev.get("dc_id") else ""
            print(f"    * {ev['id']} ({ev['phase']}){dc_note}: {ev['summary']}")


def cmd_chunk(args: argparse.Namespace) -> None:
    ledger_path = resolve_ledger_path(args.ledger)
    act = args.action
    if not ledger_path.is_file():
        if act == "start":
            slug = "fds-session"
            ledger_path = resolve_ledger_path(args.ledger, slug=slug)
            data = {
                "schema_version": "2.1",
                "meta_prompt_version": f"FDS-Builder-Skill 2.1 ({utc_today()})",
                "slug": slug,
                "mode": "intake",
                "spec_path": "docs/fds.md",
                "current_step": "0.1",
                "completed_steps": [],
                "skipped_steps": {},
                "session_completed": False,
                "loop_queues": default_loop_queues(),
                "phase": "0.1 (Chunked Intake)",
                "progress": "Chunked buffer active",
                "intent_aligned": False,
                "lineup_approved": False,
                "chunked_mode": {"active": True, "chunks": []},
                "sections": json.loads(json.dumps(DEFAULT_SECTIONS)),
                "nfr": {
                    fam: {"posture": "mandatory" if fam in MANDATORY_NFR else "conditional", "status": "unconfirmed", "archetype": None, "note": ""}
                    for fam in sorted(ALL_NFR)
                },
                "decision_contexts": [],
                "friction_log": [],
                "created_at": utc_now_iso(),
                "updated_at": utc_now_iso(),
            }
            save_ledger(ledger_path, data)
            print("Chunked Mode active. Send your text. Type /done when finished.")
            return
        elif act == "done":
            print("Chunked Mode is not active. Type /chunked to start.")
            return
        elif act == "status":
            print(json.dumps({"active": False, "chunk_count": 0}))
            return
        elif act == "read":
            return
        else:
            print("Chunked Mode is not active. Type /chunked to start.")
            sys.exit(1)

    data = load_ledger(ledger_path)
    cm = data["chunked_mode"]

    if act == "start":
        if cm["active"]:
            print("Already in Chunked Mode. Keep sending, or type /done to finish.")
        else:
            cm["active"] = True
            cm["chunks"] = []
            save_ledger(ledger_path, data)
            print("Chunked Mode active. Send your text. Type /done when finished.")
    elif act == "append":
        if not cm["active"]:
            print("Chunked Mode is not active. Type /chunked to start.")
            sys.exit(1)
        payload = ""
        if args.file:
            payload = Path(args.file).read_text(encoding="utf-8")
        elif args.text is not None:
            payload = args.text
        else:
            payload = sys.stdin.read()
        cm["chunks"].append(payload)
        save_ledger(ledger_path, data)
        print(f"[Chunks received: {len(cm['chunks'])}]")
    elif act == "done":
        if not cm["active"]:
            print("Chunked Mode is not active. Type /chunked to start.")
        else:
            count = len(cm["chunks"])
            cm["active"] = False
            if data.get("current_step") == "0.1":
                data["completed_steps"] = ["0.1"]
                data["current_step"] = "0.2"
                sync_banner_from_step(data)
            save_ledger(ledger_path, data)
            print(f"All text received ({count} chunks). What would you like me to do with it?")
    elif act == "status":
        print(json.dumps({"active": cm["active"], "chunk_count": len(cm["chunks"])}))
    elif act == "read":
        sys.stdout.write("\n".join(cm["chunks"]))
        if cm["chunks"]:
            sys.stdout.write("\n")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="FDS Builder granular step machine & atomic DC ledger manager")
    sub = p.add_subparsers(dest="subcommand", required=True)

    p_init = sub.add_parser("init", help="Initialize FDS session ledger and granular step queue")
    p_init.add_argument("--spec", required=True, help="Target FDS markdown path (e.g., docs/fds.md)")
    p_init.add_argument("--slug", help="Optional session slug")
    p_init.add_argument("--mode", choices=["new", "intake"], default="new")
    p_init.add_argument("--ledger", help="Explicit ledger JSON file path")
    p_init.set_defaults(func=cmd_init)

    p_cur = sub.add_parser("current-step", help="Show active granular step, single step reference file, numbered substeps & done-when check")
    p_cur.add_argument("--ledger", help="Explicit ledger JSON file path")
    p_cur.add_argument("--json", action="store_true")
    p_cur.set_defaults(func=cmd_current_step)

    p_reg = sub.add_parser("register-items", help="Register per-batch loop items (; separated batches)")
    p_reg.add_argument("--kind", required=True, choices=sorted(LOOP_KINDS))
    p_reg.add_argument("--items", required=True, help="Semicolon-separated batch labels, e.g. '#obj-org,#obj-user;#obj-invoice'")
    p_reg.add_argument("--ledger", help="Explicit ledger JSON file path")
    p_reg.set_defaults(func=cmd_register_items)

    p_comp = sub.add_parser("complete-step", help="Verify active step's done-when exit criterion and advance to the next granular step")
    p_comp.add_argument("step_id", help="Active granular step ID, e.g. 1.2, 2.03, 2.08a, 3.06")
    p_comp.add_argument("--intent-aligned", action="store_true", help="Mark 3-order intent gate passed (Step 1.2)")
    p_comp.add_argument("--skip-reason", help="Explicit D9 skip rationale for skippable conditional/empty steps (0.2, 2.05, 2.09, 4.2)")
    p_comp.add_argument("--ledger", help="Explicit ledger JSON file path")
    p_comp.set_defaults(func=cmd_complete_step)

    p_ff = sub.add_parser("skip-to-deep-dive", help="Intake mode fast-forward from 1.3 to 3.01 (requires --phase scaffold PASS)")
    p_ff.add_argument("--reason", required=True, help="Session DC-NNN rationale for fast-forwarding past Scaffold")
    p_ff.add_argument("--ledger", help="Explicit ledger JSON file path")
    p_ff.set_defaults(func=cmd_skip_to_deep_dive)

    p_seed = sub.add_parser("seed-spec", help="Deterministically copy 16-section FDS skeleton to spec_path with metadata & D9 exclusions")
    p_seed.add_argument("--title", help="System / feature title")
    p_seed.add_argument("--force", action="store_true", help="Overwrite existing spec file")
    p_seed.add_argument("--ledger", help="Explicit ledger JSON file path")
    p_seed.set_defaults(func=cmd_seed_spec)

    p_stat = sub.add_parser("status", help="Show D11 Phase | Progress banner and state summary")
    p_stat.add_argument("--ledger", help="Explicit ledger JSON file path")
    p_stat.add_argument("--json", action="store_true")
    p_stat.set_defaults(func=cmd_status)

    p_phase = sub.add_parser("set-phase", help="Synchronize phase/step label and update progress banner")
    p_phase.add_argument("phase", help="Step/phase identifier, e.g. '2.03'")
    p_phase.add_argument("--progress", help="Progress string override for D11 banner")
    p_phase.add_argument("--intent-aligned", action="store_true", help="Mark 3-order intent gate passed")
    p_phase.add_argument("--ledger", help="Explicit ledger JSON file path")
    p_phase.set_defaults(func=cmd_set_phase)

    p_lineup = sub.add_parser("lineup", help="Manage dynamic section lineup and critical tags")
    p_lineup.add_argument("--include", help="Comma-separated section IDs to include")
    p_lineup.add_argument("--exclude", help="Comma-separated conditional section IDs to exclude")
    p_lineup.add_argument("--rationale", help="Session-evidence rationale (required for exclusions)")
    p_lineup.add_argument("--critical", help="Comma-separated section IDs to mark critical (weight=3)")
    p_lineup.add_argument("--untag-critical", help="Comma-separated section IDs to untag critical")
    p_lineup.add_argument("--approve", action="store_true", help="Lock user approval of section lineup")
    p_lineup.add_argument("--ledger", help="Explicit ledger JSON file path")
    p_lineup.set_defaults(func=cmd_lineup)

    p_nfr = sub.add_parser("set-nfr", help="Record NFR archetype choice or explicit conditional skip")
    p_nfr.add_argument("--family", required=True, help="SEC|PERF|LOG|SCALE|A11Y|OBS|I18N|PRIV")
    p_nfr.add_argument("--status", required=True, choices=["draft-default", "confirmed", "skipped"])
    p_nfr.add_argument("--archetype", help="Archetype ID, e.g. SEC-3, PRIV-2, OBS-3, or CUSTOM")
    p_nfr.add_argument("--note", help="Rationale or explicit user skip confirmation")
    p_nfr.add_argument("--ledger", help="Explicit ledger JSON file path")
    p_nfr.set_defaults(func=cmd_set_nfr)

    p_dc = sub.add_parser("add-dc", help="Mint sequential Decision Context (DC-NNN)")
    p_dc.add_argument("--summary", required=True, help="Substantive decision summary")
    p_dc.add_argument("--phase", help="Step label override (defaults to current_step)")
    p_dc.add_argument("--anchors", help="Comma-separated affected #anchors")
    p_dc.add_argument("--depends-on", help="Comma-separated parent DC-NNN IDs")
    p_dc.add_argument("--custom-rationale", help="Explicit 'because ...' rationale for [CUSTOM] choices")
    p_dc.add_argument("--ledger", help="Explicit ledger JSON file path")
    p_dc.set_defaults(func=cmd_add_dc)

    p_rb = sub.add_parser("rollback-dc", help="Atomically roll back a DC-NNN and all transitive dependents")
    p_rb.add_argument("dc_id", help="Decision Context ID, e.g. DC-003")
    p_rb.add_argument("--reason", required=True, help="Reason for reversal")
    p_rb.add_argument("--ledger", help="Explicit ledger JSON file path")
    p_rb.set_defaults(func=cmd_rollback_dc)

    p_fr = sub.add_parser("log-friction", help="Log a D8 process friction event")
    p_fr.add_argument("--category", required=True, help="Root-cause category (§10.2)")
    p_fr.add_argument("--summary", required=True, help="Observed friction / correction / gap")
    p_fr.add_argument("--dc", help="Related DC-NNN ID")
    p_fr.add_argument("--ledger", help="Explicit ledger JSON file path")
    p_fr.set_defaults(func=cmd_log_friction)

    p_fr_rep = sub.add_parser("friction-report", help="Cluster friction events for Phase 6 retrospective")
    p_fr_rep.add_argument("--ledger", help="Explicit ledger JSON file path")
    p_fr_rep.add_argument("--json", action="store_true")
    p_fr_rep.set_defaults(func=cmd_friction_report)

    p_chunk = sub.add_parser("chunk", help="Manage verbatim Chunked Mode buffer")
    p_chunk.add_argument("action", choices=["start", "append", "done", "status", "read"])
    p_chunk.add_argument("--text", help="Chunk text")
    p_chunk.add_argument("--file", help="Path to file containing chunk text")
    p_chunk.add_argument("--ledger", help="Explicit ledger JSON file path")
    p_chunk.set_defaults(func=cmd_chunk)

    return p


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
