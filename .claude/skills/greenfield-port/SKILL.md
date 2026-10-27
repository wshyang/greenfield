---
name: greenfield-port
description: Mechanically audits a legacy repository and guides porting it to Go 1.27, Node.js 22 + TypeScript, or Rust 1.99 using scan-node-for-port.sh, executable legacy oracles, 3-bucket test ledgers, golden fixtures, determinism audits, divergence logs, and twin-DB shadow diffing. Invoke with /greenfield-port when reviewing, planning, or executing a system port.
argument-hint: "[go|node|rust] [legacy-repo-path]"
arguments:
  - lang
  - repo_path
disable-model-invocation: true
hooks:
  PreToolUse:
    - matcher: "Edit|Write"
      hooks:
        - type: command
          command: "\"${CLAUDE_SKILL_DIR}\"/scripts/lock-golden-fixtures.sh"
---

# Greenfield System Porting Playbook (`/greenfield-port`)

## Core Porting Rules (Read First — Survives Compaction)

1. **Scan mechanically before writing prose or code.** When porting from a Node.js/TypeScript codebase, run `"${CLAUDE_SKILL_DIR}"/scripts/scan-node-for-port.sh "${repo_path:-.}" --target "${lang:-go}"` via `Bash` first (`0` script-source tokens) so route counts, 3-bucket test classifications, shared client/server imports, `replicas = 1` state, and `HZ-01`…`HZ-08` determinism counts come from an AST/comment-stripped scan rather than ad-hoc grep guesses.
2. **The running legacy system is the specification.** Answer *"what does legacy do on input X?"* by executing the legacy system against `X`, never by eye-reading dynamic code.
3. **Preserve wire & status parity (`401`/`403` vs `404`) at every unchanged client boundary** until a post-cutover addendum explicitly changes it; maintain a **divergence log** (*kept for parity* · *changed by addendum NNNN* · *to decide*) rather than silently cleaning up quirks mid-port.
4. **Never hand-write or hand-edit golden fixtures (`fixtures/golden/**`).** Export `{input, expectedOutput}` + normalised validator error keys via a repeatable script against the legacy code (manual `Edit|Write` on `fixtures/golden/**` is blocked by `lock-golden-fixtures.sh`).
5. **Prove the twin-DB shadow harness fails before trusting `0` diffs:** run legacy-vs-legacy (`0` false positives) and legacy-vs-sabotaged-legacy (flipped status, mutated field, reordered list, dropped SSE frame — every mutation caught!).

## Workflow

### Phase A — Mechanical Review & Two-Cut Port Plan (Before Scaffolding)
1. Execute `"${CLAUDE_SKILL_DIR}"/scripts/scan-node-for-port.sh "${repo_path:-.}" --target "${lang:-go}" --out /tmp/port-scan.md` and read `/tmp/port-scan.md`.
2. Read **only** the target language's hazard reference:
   - **Go `1.27`:** `${CLAUDE_SKILL_DIR}/references/go-porting-hazards.md`
   - **Node `22` + TS:** `${CLAUDE_SKILL_DIR}/references/node-porting-hazards.md`
   - **Rust `1.99`:** `${CLAUDE_SKILL_DIR}/references/rust-porting-hazards.md`
3. Copy the structure of `${CLAUDE_SKILL_DIR}/assets/port-plan-template.md` and invoke `greenfield-spec-and-plan` to author `docs/plans/<lang>-port-plan.md` with exact scanned counts, re-check commands, and leaf `— done when ...` checkboxes. Stop for user approval before writing target-language code.

### Phase B — Bootstrap, Vertical-Slice Port, Shadow Run & Cutover
1. Once the plan is approved, invoke `/greenfield-bootstrap <lang>` to settle `DR-01`…`DR-11` and render the target repo's lean `CLAUDE.md`.
2. Port `internal/kernel` (or `packages/kernel` / `crates/kernel`) + dependency-graph test first, then golden-fixture helpers, then vertical domain slices backed by real-Postgres tests (`greenfield-verify`) and twin-DB shadow runs.
3. Freeze schema during the shadow window, rehearse staging rollback to the legacy image, cut over on objective gates (`0` unexplained shadow diffs + same-host `p50/p95/p99/max` parity), and retire legacy code + shadow shims in one clean commit.
