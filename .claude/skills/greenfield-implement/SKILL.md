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
---

# Greenfield Implementation & Architecture Skill

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

## Load ONLY the Active Language Reference

Check `go.mod`, `package.json`, or `Cargo.toml` and read **only the one matching file** (never load unused language files into context):

- **Go `1.27+`:** read `${CLAUDE_SKILL_DIR}/references/go-idioms-and-architecture.md`
- **Node.js `22+` / TypeScript:** read `${CLAUDE_SKILL_DIR}/references/node-idioms-and-architecture.md`
- **Rust `1.99+`:** read `${CLAUDE_SKILL_DIR}/references/rust-idioms-and-architecture.md`

*(If a deeper edge case arises while working inside the `sidequest` template repo itself, consult the specific section of `GREENFIELD-{GO,NODE,RUST}.md` by line offset rather than reading the entire file.)*
