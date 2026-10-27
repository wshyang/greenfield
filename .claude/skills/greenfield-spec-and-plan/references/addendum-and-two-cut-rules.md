# Addendum Template & Two-Cut Plan Rules

## 1. Canonical Addendum Shape (`docs/decisions/NNNN-<slug>.md`)

Short single-choice addenda stay concise (`<= 45` lines) with `2–4` verifiable `## Impact` checkboxes:

```markdown
---
id: 0007
decision: DR-11
status: accepted          # accepted | superseded
decided_by: user          # user | agent
date: 2026-10-27
supersedes: null          # or 0003
---

# 0007 — Pre-launch schema gate: single snapshot + schema_state

## Decision
Use Option B (`db/schema.sql` + `schema_state(version, sha256)` advisory-locked boot gate) until staging holds persistent data.

## Why
<user's stated reason or agent delegation check>

## Rejected
- Option A (numbered migrations now): adds early migration churn while zero persistent DBs exist.

## Impact
- [ ] 0007-1 Implement `EnsureSchema` boot gate in `internal/platform/db/schema.go` — `go test ./internal/platform/db -run TestSchemaGate` — done when boot-twice and older-stamp refusal tests pass
- [ ] 0007-2 Forbid `migrations/` in `cmd/check-standards` rule `STD-009` — `go test ./cmd/check-standards` — done when a synthetic `migrations/0001.sql` fixture fails CI
```

When changing a consequential test/security rule, record the **watched bite-check sabotages** inside the addendum.

## 2. Two-Cut Multi-Task Design & Plan Rules (`docs/plans/*.md`)

Every `##` section of a multi-task engineering plan carries:
1. **Cut 1 — Prose shape:** boundaries, data ownership, and trade-offs.
2. **Cut 2 — `### Verify / do`:** checkboxes matching:
   `- [ ] <UNIQUE-ID> <ImperativeVerb> <target path / command / query / count> — done when <verifiable command or state>`

### Hard Rules for Checkboxes

- **Reject vague verbs:** `ensure`, `consider`, `review`, `improve`, `handle`, `support`, `clean up`. Use `Add`, `Move`, `Delete`, `Replace`, `Run`, `Extract`, `Gate`, `Measure`.
- **Re-check every survey count:** write `(14 sites: git grep -c "time\.Now()" internal/)` and run the command before committing the doc.
- **Link every design decision** to at least one task ID and a named proving test.
- **Leaf-only `done when`:** if a parent task decomposes into child checkboxes, put `— done when ...` on each leaf child, not duplicated on the parent.
- **Mark sandbox-blocked checks honestly:** append `(needs docker)` or `(needs go toolchain)` rather than silently ticking `[x]`.
- **Keep project checker scripts in the repo's primary language** (`./cmd/devtask check-plan-docs` in Go, `node scripts/check-plan-docs.ts` in Node 22, `cargo xtask check-plan-docs` in Rust) and prove the checker fails on a violating fixture.
