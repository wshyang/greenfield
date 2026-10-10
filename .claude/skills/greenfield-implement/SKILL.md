---
name: greenfield-implement
description: Enforces Greenfield architecture, domain modelling, wire contracts, post-commit effects, and function-design idioms when writing Go 1.27, Node.js 22 + TypeScript, or Rust 1.99 application code. Auto-loads when building routes, domain rules, queries, or background workers.
when_to_use: When adding or refactoring backend routes, domain modules, database queries, wire contracts, background workers, auth/session middleware, or post-commit SSE/cache effects.
paths:
  - "cmd/**"
  - "internal/**"
  - "src/**"
  - "packages/**"
  - "crates/**"
allowed-tools:
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - LSP
  - AskUserQuestion
---

# Greenfield Implementation & Architecture Skill

> **Who runs this skill:** `gf-implementer` (the `greenfield-delegate` pipeline), working from an approved `docs/plans/NNNN-*.md`. The main thread never writes code. If you are the main thread, invoke `greenfield-delegate` instead.

## Universal Invariants (Read First — Survives Compaction)

1. **Five Modular-Monolith Rules:**
   - **Boundary before distribution:** start as one deployable; extract a service only on measured ~10× resource divergence, team release blocking, compliance isolation, runtime mismatch, or established ownership — moving tables into an owned schema before moving code.
   - **Executable dependency rules:** enforce the module DAG in CI (`internal/arch_test.go` / `dependency-cruiser` / `cargo metadata` test), proven against a failing fixture.
   - **Zero-I/O `kernel` leaf:** keep cross-domain shared vocabulary (typed entity IDs, `Clock`, `Secret`, closed `Event` / `CacheTag` types) in a dependency-free leaf (`internal/kernel` / `packages/kernel` / `crates/kernel`) with zero SQL, HTTP, or business logic.
   - **One write owner per table & pattern per module:** complex core slices earn pure domain/policy functions + ports; boring CRUD slices stay handler + query + real-DB test (no *sinkhole* pass-through service layers).
   - **No abstraction without >= 2 real implementations:** never put a 1-impl repository interface in front of SQL queries (repo mocks are forbidden).
2. **Function & Module Discipline:**
   - Functions `<= 20` lines target, **`50` lines hard cap**; files `<= 400` LOC typical, **`800` LOC hard cap**.
   - Guard clauses over nesting (max depth `3`); `<= 3` parameters (introduce a parameter struct/object beyond 3); **zero boolean flag arguments**; Separate Query from Modifier.
3. **Wire, Validation & Returned Post-Commit Effects:**
   - Parse, don't validate at the boundary (validated domain types, RFC 9457 `application/problem+json`, `Idempotency-Key` on retryable `POST`s, explicit 3-state `PATCH` omitted vs `null` vs value).
   - Return post-commit in-process notifications (SSE push, cache invalidation) wrapped in an un-ignorable capability value (`effects.Outcome[T]` in Go, `MustPublish<T>` in Node, `#[must_use] Effects` in Rust); use a transactional SQL outbox inside the DB transaction when delivery must survive crashes.
4. **Same-change discipline:** ship route + positive real-DB test + IDOR negative test (asserting unchanged DB rows) + bite check + any `docs/decisions/NNNN-*.md` addendum in the same change.

## Decision Points (AI Proposes, User Decides)

Tags: **`[IDEATE]`** = draft 2–4 concrete options, each with its trade-off, mark one `(Recommended)` with a one-line reason, then ask via `AskUserQuestion` (state the skip-default). **Questions go only through `AskUserQuestion`, never inline.** A reply must not end with a list of questions or a prose question; a decision table in a doc only records what was asked. **`[GATE]`** = hard stop until the user confirms. First check `docs/spec.md` and `docs/decisions/`, and ask only what they leave open. Persist every answer the same change, as an addendum or plan edit.

1. **Slice pattern** `[IDEATE if the spec does not settle it]`: *complex core* (pure domain/policy functions + ports) vs *boring CRUD* (handler + query + real-DB test). Recommend from the slice's invariant and state-transition count.
2. **Post-commit delivery** `[IDEATE if crash-survival is unstated]`: *in-process returned effects* (`effects.Outcome[T]` / `MustPublish<T>` / `#[must_use] Effects`) vs a *transactional SQL outbox*. Recommend based on whether a lost notification is user-visible.
3. **IDOR negative status** `[IDEATE if not recorded]`: *`404`, hiding existence* (default) vs *`401`/`403`*, when existence is public or a ported client depends on it.
4. **Spec gap** `[GATE]`: Any new entity, field or endpoint that is absent from `docs/spec.md` needs 2 options and the user's pick. Then record it through `greenfield-spec-and-plan` as a new addendum in the same change.
5. **Hard-cap breach** `[IDEATE]`: When a function passes `50` lines or a file passes `800` LOC, propose 2 split lines (e.g. by sub-step vs by data shape) before refactoring.

## Load ONLY the Active Language Reference

Check `go.mod`, `package.json`, or `Cargo.toml` and read **only the one matching file** (never load unused language files into context):

- **Go `1.27+`:** read `${CLAUDE_SKILL_DIR}/references/go-idioms-and-architecture.md`
- **Node.js `22+` / TypeScript:** read `${CLAUDE_SKILL_DIR}/references/node-idioms-and-architecture.md`
- **Rust `1.99+`:** read `${CLAUDE_SKILL_DIR}/references/rust-idioms-and-architecture.md`

*(If a deeper edge case arises while working inside the `sidequest` template repo itself, consult the specific section of `GREENFIELD-{GO,NODE,RUST}.md` by line offset rather than reading the entire file.)*
