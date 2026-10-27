---
name: greenfield-spec-and-plan
description: Authors numbered decision addenda (docs/decisions/NNNN-*.md), two-cut engineering plans with measurable leaf exit criteria, and Functional Design Specifications (FDS). Use whenever recording an architectural/product decision, writing a design doc or implementation plan, or building an FDS.
when_to_use: When the user asks to write a spec, FDS, design doc, migration plan, roadmap, task breakdown, or decision addendum, or when making a choice not dictated by docs/spec.md.
argument-hint: "[addendum|plan|fds] [topic]"
hooks:
  PostToolUse:
    - matcher: "Edit|Write"
      hooks:
        - type: command
          command: "\"${CLAUDE_SKILL_DIR}\"/scripts/check-plan-and-fds.sh"
---

# Greenfield Spec, Addendum & Two-Cut Plan Skill

## Top Rules (Survives Compaction)

1. **Same-change addendum discipline:** Every decision filling a spec gap, adding an entity/field/endpoint, or deviating from `docs/spec.md` gets a new sequentially-numbered `docs/decisions/NNNN-<slug>.md` **in the same commit** — never edit an accepted addendum in place (write a new one with `supersedes: NNNN`).
2. **Plans and multi-task designs are written in TWO cuts:**
   - **Cut 1 (Shape):** scope, boundaries, decisions, and trade-offs in crisp prose.
   - **Cut 2 (`Verify / do`):** under every prose section, checkboxes with a unique ID, **one concrete imperative verb**, an exact file path / command / query / count, and `— done when <measurable check>`.
3. **Banned vague lead verbs in checkboxes:** never lead a checkbox with *ensure*, *consider*, *review*, *improve*, *handle*, *verify that everything*, or *make sure*.
4. **FDS mode (`fds`):** when authoring a Functional Design Specification, read `${CLAUDE_SKILL_DIR}/references/fds-builder-condensed.md` (and `FDS_BUILDER.md` if present in the repo) **before** drafting: enforce the 3-order intent gate, MCQ-only discovery (`D2`), `[DRAFT — {source}]` tags (`D1`), 4-part attribute contracts (`D3`), explicit state transition guards (`D4`), and **zero diagrams of any kind (`D15`)**.

## Mode Dispatch

- **Recording an addendum (`docs/decisions/NNNN-*.md`):** read `${CLAUDE_SKILL_DIR}/references/addendum-and-two-cut-rules.md` (§1) and run `"${CLAUDE_SKILL_DIR}"/scripts/check-plan-and-fds.sh <file>` if validating manually.
- **Writing a multi-task design or migration plan (`docs/plans/*.md`):** read `${CLAUDE_SKILL_DIR}/references/addendum-and-two-cut-rules.md` (§2–§3):
  - Attach a re-check shell command to every codebase count (routes, tables, `Date.now()` sites).
  - Rehearse change-vector boundary claims (*"adding X touches only A and B"*) on a scratch branch against the compiler.
  - Put `done when` on **leaf tasks only** (do not double-count parent + child).
- **Constructing a Functional Design Spec (`docs/spec.md` / FDS):** read `${CLAUDE_SKILL_DIR}/references/fds-builder-condensed.md`.
