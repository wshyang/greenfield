---
name: greenfield-verify
description: Runs and audits Greenfield verification gates — real-Postgres positive + IDOR negative tests, bite-check sabotages, scoped mutation testing, standards/coverage ratchets, mixed-load tail-latency benchmarks, and honest §8 validation rung reporting. Use when writing tests, auditing a PR, or preparing to finish a task.
when_to_use: When adding or fixing tests, running pre-commit or pre-merge checks, executing a bite check, setting up mutation testing or load benchmarks, or reporting validation status.
argument-hint: "[audit|bite-check|perf]"
---

# Greenfield Verification, Bite-Check & Honest Reporting Skill

## Non-Negotiable Verification Rules (Survives Compaction)

1. **Real Postgres, zero repository mocks:** exercise the real router/entrypoint (`httptest` / `app.inject()` / `tower::ServiceExt::oneshot`) against an isolated real Postgres test DB — **never mock the data layer** and **never use WASM `@electric-sql/pglite` for server concurrency suites**.
2. **Positive + IDOR negative test per route, asserting persisted DB state:**
   - Re-read Postgres rows (or call a second `GET`) rather than trusting HTTP status codes alone.
   - Authenticate as a *valid, logged-in wrong-party session*, attempt cross-actor access/mutation, assert the project's recorded negative status (`404` default when hiding existence; `401`/`403` when existence is public or a port preserves legacy contracts), **and query Postgres to assert zero rows changed**.
3. **The Bite Check (sabotage every new test):**
   - Break each guarded clause one at a time (e.g. drop `expires_at IS NULL`, swap `owner_id`, drop wire field), watch the test fail for the right reason, revert cleanly (`git diff --exit-code`), and record watched sabotages in consequential addenda.
4. **Zero retry-masking & typed fixtures:** `retries: 0` across unit, integration, and Playwright (`trace: "retain-on-failure"`, video on by default); type-check fixtures (`satisfies` in TS, `json/v2` typed structs in Go); derive timeouts from single-iteration measurements.
5. **Close the bug class & report the exact §8 validation rung:** sweep the whole repo for sibling instances of every fixed bug, and state explicitly which rung ran:
   - *Rung 1:* Static syntax / structural audit (`"${CLAUDE_SKILL_DIR}"/scripts/audit-repo-gates.sh`)
   - *Rung 2:* Full compiler + linter + `arch_test` / `depcruise` + `check-standards`
   - *Rung 3:* Pure unit / property / `synctest` tests (no DB)
   - *Rung 4:* Real-Postgres integration tests + schema parity/gate check
   - *Rung 5:* Full Playwright E2E against real backend + container smoke test

## Workflow

1. Run `"${CLAUDE_SKILL_DIR}"/scripts/audit-repo-gates.sh` via `Bash` (`0` script-source tokens) to inspect available toolchains, structural invariants, and the highest reachable validation rung in this environment.
2. Read `${CLAUDE_SKILL_DIR}/references/testing-bite-and-perf.md` when configuring embedded Postgres, mutation testing (`gremlins` / Stryker / `cargo-mutants`), `check-standards` fixture proofs, coverage ratchets, or `p50/p95/p99/max` load benchmarks.
