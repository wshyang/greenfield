# GREENFIELD-RUST.md — CLAUDE.md template for new Rust projects

**Standalone.** This is the Rust variant of the greenfield template set; you
reached it from the language question in `GREENFIELD.md`, and it is the Rust
sibling of `GREENFIELD-NODE.md`. Nothing here depends on reading either file. It
is a **standing-instructions template** to copy into a new repository's
`CLAUDE.md` (and later split into focused section files). It is deliberately
project-agnostic — no product name, no feature references, no hardcoded service
names.

It does three jobs:

1. **It fixes the invariants** that are cheap on day one and expensive to
   retrofit: real-database tests, soft deletion, UUIDv7, twin schema files, a
   strictness profile, a container contract, honest validation.
2. **It stops the agent from silently choosing on the user's behalf.** Rust has
   several equally defensible answers for the data layer, the wire contract, the
   UI, auth, and the runtime image. §0.3 defines a **decision interview**: the
   agent must ask the user, present each option with a real code example and its
   trade-offs, recommend one, and record the answer as an addendum. This
   document ships the ten question cards (`DR-01`…`DR-10`), ready to send.
3. **It settles the code-level idioms that reviewers argue about.** §13 is the
   `strictest`-equivalent lint and compiler profile; §14 covers signatures,
   naming, derives, and `#[non_exhaustive]`; §15 is the pattern allow-list and
   deny-list; §16 covers async correctness and telemetry; §17 covers performance
   and adversarial testing. These are stated as rules, not suggestions, because
   every one of them is cheaper to adopt before the first thousand lines.

**Versions verified October 2026** (Rust 1.99 stable; 1.100 lands 12 November
2026): `axum` 0.8.x, `sqlx` 0.9.x, `diesel` 2.3.x + `diesel-async` 0.9.x,
`sea-orm` 2.0.x, `utoipa` 5.x, `tower-sessions` 0.15.x, `leptos` 0.7.x,
`opentelemetry` 0.31.x. Pin exact versions in `Cargo.toml`; treat every version
in this file as "verified then", not "latest forever".

**Contents.** §0 how to use it and the decision interview · §1 decisions and the
living spec · §2 tests · §3 test infrastructure · §4 database discipline · §5
schema evolution · §6 code conventions · §7 function and module design · §8
honest validation · §9 local dev · §10 containers and SHIP-HATS · §11 day-one
checklist · §12 the ten decision cards · §13 the strictness profile · §14 API and
idiom rules · §15 design patterns · §16 async and observability · §17 performance
and adversarial testing · §18 architecture in Rust · §19 keeping this
template honest.

---

## 0. How to use this template

### 0.1 Copy, then unpack

- Copy this whole file as `CLAUDE.md` in the new Rust repository, delete the
  greenfield set's other files (the router and the Node variant) in the same
  commit, then replace every `<placeholder>`. Keep the `DR-` identifiers intact:
  they are referenced by addenda, CI checks, and code comments.
- Splitting each `##` section into `CLAUDE-rust-<area>.md`
  (`CLAUDE-rust-database.md`, `CLAUDE-rust-deployment.md`, …) behind a top-level
  index is **optional**, not a bootstrap step. Do it when one file stops being
  readable in a single pass; agents then `grep` one focused file instead of
  loading the corpus. Until then, one file is simpler to keep honest.
- If you do split, keep §0 (the interview), §1 (decisions), and §2 (tests) in the
  *first* file an agent reads. They prevent the most rework.
- Copy the deployment starters from `initial-templates/` in the greenfield
  repository when they exist, then contextualise them against §10.1. The Rust
  `Dockerfile` in §10.1 is the reference implementation; do not copy the Node
  template's `npm`/`dist` assumptions into a Rust image.

### 0.2 Two classes of rule: invariants vs. forks

Not every choice is the user's to make at kickoff. Mixing the two is how a
"please decide" prompt turns into an interrogation and how a load-bearing
discipline gets traded away for speed.

| Class | Meaning | Agent behaviour |
| --- | --- | --- |
| **Invariant** | Fixed by this document because the cost of retrofitting is high and the answer does not vary by project (soft delete, UUIDv7, real-DB tests, no mocked repositories, twin schema files, port 3000 on `0.0.0.0`, no hand-written mappers, no `unwrap` in request paths). | Implement as written. If the project genuinely cannot comply, **stop and ask**; if approved, record an addendum that names the invariant being waived and why. Never waive silently. |
| **Fork** | Two or three defensible Rust answers with different costs, and no way to infer the team's preference from the repo (`DR-01`…`DR-10`). | **Ask before writing the first line in that area.** Use the question card from §12. Record the answer. |

The invariants live in §2, §4, §5, §6, §7, §8, §10, and §13–§17. The forks are
exactly `DR-01`…`DR-10`, listed in §0.7.

§15 is a hybrid: the pattern allow-list is a default, but each pattern names the
condition under which it is **wrong** ("use an enum instead when…"). Applying
typestate to a dynamic state graph is a violation, not a preference — the
exceptions are written down so an agent cannot cite the pattern as cover for
over-engineering.

### 0.3 The decision interview (hard rules)

This section is an instruction to the agent, not advice.

1. **Ask before code, not after.** Before implementing anything that touches a
   `DR-` area, the user must have answered that `DR-`. "I'll pick something
   sensible and we can revisit" is not an answer; if the user says it, use the
   recommendation, record `decided_by: agent`, and flag it in the PR.
2. **One decision per question.** Never bundle "which ORM and which frontend"
   into one prompt; the answer to one biases the other.
3. **Batch at most four questions per message**, in the three batches of §0.7.
   A wall of ten questions gets rubber-stamped.
4. **Every option gets all five parts**: a one-line shape, a real example the
   user could paste into the project (a code or config excerpt in the project's
   own vocabulary — never a toy `foo`/`bar` stub), pros, costs, and a "choose
   this if" line. For options whose difference *is* configuration (image bases,
   lint posture), the excerpt is the config, not a function.
5. **Always recommend one option and say why**, in one sentence, tied to the
   project's actual constraints (team language, deployment target, deadline).
   An unranked menu pushes the decision back onto the user.
6. **Always offer the escape hatch**: "reply `all recommendations`".
7. **Record the answer before implementing it** (§0.5). The addendum is the
   contract; the chat message is not.
8. **Never re-litigate a recorded decision** without new information. Supersede
   it with a new numbered addendum; do not edit history.
9. **If an answer violates an invariant**, say which invariant, why it exists,
   and what it would cost. Do not implement it quietly.
10. **Re-ask only the affected `DR-`** when scope changes (e.g. the project gains
    a second binary, or a government SSO requirement appears). Do not re-run the
    whole interview.

**Opening message shape.** One line stating the batch, the number of decisions,
and the escape hatch; then one card per decision, each ending with its own
question; then stop. No preamble about how exciting the project is, and no
"meanwhile I'll scaffold the repo" — scaffolding *is* the choice being asked
about.

```text
Three foundation decisions before I write any code. Each card ends with a
recommendation; reply A/B/C per card, or "all recommendations".

DR-01 · HTTP framework
…
DR-02 · Data access
…
DR-03 · Crate layout
…
```

**Definition of Ready.** No feature code is written until: `DR-01`…`DR-03` are
answered (the foundation batch), and for the specific feature, the `DR-`
decisions it touches are answered. Documentation, schema sketches, and spike
branches are allowed before that; `src/` is not.

### 0.4 The question card (copy this shape)

Send exactly this shape. If the agent's harness has a structured question
widget, put the option labels there and the card text in the body; otherwise send
the card as plain text. Either way the example must be visible — an option label
("B: diesel") is not a trade-off. A bullet list of adjectives is not a decision
aid either; the code is what makes the choice legible.

```text
DR-02 · Data access layer — question 2 of batch 1

How should the server talk to Postgres?

A. sqlx 0.9 — SQL first, checked at compile time
   Real example:
       let row = sqlx::query_as!(
           RequestRow,
           r#"SELECT id, title, owner_id, created_at
                FROM requests
               WHERE id = $1 AND owner_id = $2 AND expires_at IS NULL"#,
           id, actor.0,
       ).fetch_optional(pool).await?;
   Pros:  SQL stays visible; a typo or renamed column fails `cargo check`;
          no DSL to learn; easy to review in a PR.
   Costs: needs a live DB or a committed `.sqlx/` cache to compile;
          `.sqlx/` must be regenerated whenever SQL changes;
          view columns come back as nullable unless overridden.
   Choose if: your team thinks in SQL and wants the query to be the artefact.

B. diesel 2.3 + diesel-async 0.9 — typed DSL over a generated schema
   Real example:
       requests::table
           .filter(requests::id.eq(req_id))
           .filter(requests::owner_id.eq(actor.0))
           .filter(requests::expires_at.is_null())
           .select(RequestRow::as_select())
           .first(conn).await.optional()?
   Pros:  Illegal columns/joins fail to compile without any database;
          closest literal twin to Drizzle's schema-as-source-of-truth;
          query pipelining.
   Costs: `schema.rs` must be generated and kept in step; heavier compile
          times on wide schemas; the DSL is a second language.
   Choose if: you want the type system to be the schema and accept codegen.

C. sea-orm 2.0 — entities and relations
   Real example:
       requests::Entity::find_by_id(req_id)
           .filter(requests::Column::OwnerId.eq(actor.0))
           .filter(requests::Column::ExpiresAt.is_null())
           .one(db).await?
   Pros:  Nested graph loading (`EntityLoader`) without hand-written joins;
          fastest path to a CRUD-heavy domain.
   Costs: runtime (not compile-time) schema checking; largest dependency
          tree and build time of the three; entity drift is a real failure.
   Choose if: your reads are mostly object graphs and you want less SQL.

Recommendation: A — the team writes SQL already, and `.sqlx/` gives us
compile-time checking without a DSL.
Reply A/B/C, or "all recommendations".
```

### 0.5 Recording the answer

Every answer becomes a **numbered addendum** in the same change that starts the
work. YAML front matter is mandatory so a script can prove coverage:

```markdown
---
id: 0007
decision: DR-02
status: accepted          # accepted | superseded
decided_by: user          # user | agent
date: 2026-10-23
supersedes: null
---

# 0007 — Data access: sqlx

## Decision
sqlx 0.9 with `query_as!`, a committed `.sqlx/` offline cache, and `#[sqlx::test]`.

## Why
<the user's stated reason, not the agent's reconstruction>

## Rejected
- diesel 2.3: <the actual reason this project declined it>
- sea-orm 2.0: <…>

## Impact
- Every query lives in `src/<domain>/queries.rs`; handlers never hold SQL.
- CI runs `cargo sqlx prepare --check` and fails on a stale `.sqlx/`.
- §2's test pattern is `#[sqlx::test]`; §5's migrator is `sqlx::migrate!`.
```

Rules for the addendum: it names the **rejected** options and why. Six months
later "why didn't we use diesel?" is the question that gets asked, and the chat
log is gone.

### 0.6 When no human answers

An unattended run (nightly agent, sandbox with no user) must not stall and must
not pretend it had consent:

- take each recommendation, set `decided_by: agent`, and add a `## Review`
  section listing every defaulted `DR-` with one line of justification;
- put the same list in the pull-request description under **Decisions taken
  without the user**;
- if a defaulted decision later proves wrong, supersede it with a new addendum
  that states the migration cost actually paid.

### 0.7 Decision register

Ask in this order. Foundation decisions constrain everything after them; asking
about the frontend before the wire contract produces answers that have to be
revisited.

| ID | Decision | Options | Default | Affects | Reversal cost |
| --- | --- | --- | --- | --- | --- |
| `DR-01` | HTTP framework | axum 0.8 · actix-web 4 | axum | §2, §6, §10 | Medium — handlers, extractors, middleware, tests |
| `DR-02` | Data access | sqlx 0.9 · diesel 2.3 + diesel-async · sea-orm 2.0 | sqlx | §2, §4, §5, §9 | **Very high** — every query, every test, the migration story |
| `DR-03` | Crate layout | single crate · Cargo workspace | single crate | §7, §8, CI times | Medium — module paths and build graph |
| `DR-04` | Wire contract | `utoipa` → OpenAPI → TS · `ts-rs` types only · hand-written | `utoipa` | §6, §8 | High after the frontend exists |
| `DR-05` | Frontend | React + Vite · Leptos 0.7 · Askama/Maud + HTMX | React + Vite | §3, §6, §7 | High — it is a rewrite |
| `DR-06` | Auth | server sessions · stateless JWT · delegated OIDC only | sessions, OIDC when SSO is mandated | §2, §4, §10 | High — every authorization check |
| `DR-07` | Error wire shape | RFC 9457 `problem+json` · simple envelope · bare status | RFC 9457 | §6, §8 | Medium — every client branch |
| `DR-08` | Background work | DB outbox + in-process worker · `apalis` · none yet | outbox | §4, §9, §10 | Medium — job semantics |
| `DR-09` | Runtime image | distroless (glibc) · debian-slim · alpine (musl) | distroless | §10.1 | Low — one Dockerfile stage |
| `DR-10` | Dev orchestration | `just` · `cargo xtask` · `make` | `just` + thin xtask | §9, §10.4 | Low — developer muscle memory |

**Batch 1 (foundation):** `DR-01`, `DR-02`, `DR-03`.
**Batch 2 (product surface):** `DR-04`, `DR-05`, `DR-06`, `DR-07`.
**Batch 3 (operations):** `DR-08`, `DR-09`, `DR-10`.

The sections below are written against the **defaults** in that table. If the
user picks a different option, the named section changes; nothing else does.

### 0.8 Cross-decision consistency

Answers interact, and some combinations quietly contradict the sections that
follow. Check these before recording the addenda; raise the conflict instead of
writing code that satisfies neither answer.

| Combination | Consequence | Resolution |
| --- | --- | --- |
| `DR-01 = actix-web` + `DR-06 = sessions` | `tower-sessions` layers are `tower` middleware; actix-web has its own session middleware and extractors | use `actix-session` with a Redis/Postgres store, and say so in addendum `DR-06` |
| `DR-02 = diesel` + §2 test pattern | `#[sqlx::test]` is a sqlx macro; the per-test database isolation must come from somewhere else | use `diesel_async` + a `#[fixture]` that creates a schema-per-test database, and keep the same isolation guarantee |
| `DR-05 = Leptos`/Askama + `DR-04 = utoipa` | OpenAPI → TypeScript buys little when the client is Rust or server-rendered HTML | downgrade `DR-04` to `ts-rs` only if a TypeScript island remains, else record "no generated client" with the route-registration test kept |
| `DR-02 = sea-orm` + §4.3 views | sea-orm entities must model the `active_*` view or the base table consistently | pick one per entity, and put the liveness filter in a single `find_active` scope |
| `DR-09 = alpine` + `DR-01 = axum` | musl + some TLS/C crates need explicit targets and allocator tuning | only if the team has measured it; otherwise distroless |

If two answers cannot be reconciled, the later one wins and the earlier addendum
is superseded — never left in place contradicting its successor.

---

## 1. Record every decision, up front, in a living spec (addendum discipline)

The expensive failure mode is a spec that drifts from the binary: the only
remaining description of intent is a commit message and a Slack thread. Rust
gives this discipline teeth, because decisions can be *checked* rather than
remembered.

- Keep a **living functional/design specification** (the product contract) plus a
  **sequentially-numbered addenda register** in `docs/decisions/NNNN-*.md` for
  every decision the base spec does not dictate. The `DR-` answers of §0 are
  addenda `0001`…`000n`.
- Write the addendum **in the same commit that makes the decision**, never as a
  follow-up. Each covers what was decided, why, which spec section it touches,
  and what a future reader must do differently because of it. Use the front
  matter in §0.5; `decision:` is a `DR-` id or `spec §<n>`.
- Number addenda **independently of the spec's own numbering**, so the base spec
  stays stable and addenda append forever. Gaps are forbidden; supersession is a
  new number with `supersedes: <id>`.
- Make the register machine-checkable, not a convention:
  - `scripts/check-decisions.sh` fails when a number is duplicated, a
    `supersedes:` points at a missing id, or a `DR-` answered in a merged PR has
    no addendum;
  - the same script asserts every `TODO(DR-xx)` marker in `src/` resolves to an
    accepted addendum — an unresolved marker is a decision still being taken in
    code, which is exactly what this section forbids.
- **Rustdoc is part of the spec.** The domain crate carries
  `#![deny(missing_docs)]`, and every module's doc comment cites the addendum
  that governs it (`//! Governing decision: 0007 (DR-02).`). `cargo doc` runs in
  CI with `RUSTDOCFLAGS="-D warnings"`, so a public API that loses its rationale
  fails the build rather than degrading silently.
- `CLAUDE.md` must instruct future agents to do all of the above unprompted.
  That instruction is the difference between a codebase you can reason about and
  a puzzle box.

---

## 2. Write tests first, and keep them real (no mocks where it counts)

*Decisions: `DR-01` (the framework the tests drive), `DR-02` (the database they hit).*

Tests are the only mechanism that actually catches the bugs this template cares
about. The rules below are **invariants**, not preferences.

### 2.1 Integration tests run against a real Postgres

- Use a **separate test database**, never the dev database. `#[sqlx::test]`
  creates and drops a uniquely named database per test; `sqlx::test(migrations =
  "./migrations")` applies the real migrations, so the test schema is the shipped
  schema.
- **Exercise the real router through a real request**, without opening a
  listening socket. Axum's `Router` implements `tower::Service`, so `oneshot`
  replaces the "app object" pattern from the Node template:

```rust
// tests/requests.rs
use axum::body::Body;
use axum::http::{Request, StatusCode};
use tower::ServiceExt; // oneshot

#[sqlx::test(fixtures("fixtures/actors.sql"))]
async fn owner_can_read_own_request(pool: sqlx::PgPool) {
    let app = app::router(pool, app::Config::for_test());

    let response = app
        .oneshot(
            Request::get("/api/requests/0192f3c4-0000-7000-8000-000000000001")
                .header("cookie", session_cookie_for("alice"))
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();

    assert_eq!(response.status(), StatusCode::OK);
}
```

- **Never mock the data-access layer.** A mocked repository cannot fail the way
  Postgres fails: wrong column names, `NULL` handling, FK violations, JSONB
  round-tripping, and collation-dependent ordering all live below the mock. This
  holds even when `DR-01` lands on actix-web: use `actix_web::test::call_service`
  with the real app factory and a real pool.
- Prefer **one test per behaviour with a real row** over a wide unit suite over
  a fake. `insta` snapshots are allowed for serialized payloads; they snapshot
  *real* output, not constructed output.

### 2.2 Authorization is tested negatively, per route

- Every route needs a **positive test** *and* a **session-scoping negative test**:
  a real, valid, logged-in session belonging to the *wrong party* for that
  resource, using a real id substitution (IDOR), must be rejected for that
  resource — not merely "no cookie → 401", which proves authentication and not
  authorization.
- The negative test asserts the exact status (usually `404`, not `403`, so the
  response does not disclose existence) and that **no row changed**. Assert the
  database state after a rejected write; status codes alone have let writes
  through in practice:

```rust
#[sqlx::test(fixtures("fixtures/actors.sql", "fixtures/requests.sql"))]
async fn mallory_cannot_invalidate_alices_request(pool: sqlx::PgPool) {
    let app = app::router(pool.clone(), app::Config::for_test());
    let response = app
        .oneshot(mallory_deletes("/api/requests/0192f3c4-0000-7000-8000-000000000001"))
        .await
        .unwrap();

    assert_eq!(response.status(), StatusCode::NOT_FOUND);
    let still_active = sqlx::query_scalar!(
        "SELECT expires_at IS NULL FROM requests WHERE id = $1",
        uuid::uuid!("0192f3c4-0000-7000-8000-000000000001"),
    ).fetch_one(&pool).await.unwrap();
    assert!(still_active, "rejected write mutated the row");
}
```

- Enforce it structurally: a `#[test]` that parses the router registration and
  asserts every path has a matching `<handler>_forbidden_for_other_actor` test in
  `tests/`. This is cheap and it catches the route added on a Friday.

### 2.3 Same-change rule and the security matrix

- **Add or update tests in the same change as the route, query, or component.**
  A follow-up test ticket is a test that never gets written.
- Keep an **OWASP Top 10 matrix** in `docs/security-matrix.md`: one row per
  endpoint, one column per category, each cell `tested (link)` / `n/a (reason)` /
  `gap (ticket)`. "We thought about it" is not a cell value. Decide this on day
  one; after an audit finds the gaps it is too late to look diligent.
- Frontend unit tests may mock the API boundary. End-to-end tests drive the real
  UI against the real backend with **no mocks** (§3).

### 2.4 Rust-specific test rules

- `cargo nextest run --workspace` is the default runner: process-per-test
  isolation, so a panicking or `tracing`-noisy test cannot poison a neighbour.
  `cargo test --workspace --doc` runs separately, because nextest does not run
  doctests.
- **Table tests use `rstest`**, not hand-rolled loops that stop at the first
  failure:

```rust
#[rstest]
#[case(1_000, "1 KB")]
#[case(1_048_576, "1 MB")]
#[case(0, "0 B")]
fn formats_bytes(#[case] bytes: u64, #[case] expected: &str) {
    assert_eq!(format_bytes(bytes), expected);
}
```

- **Property tests (`proptest`) for invariants that must hold for all inputs** —
  round-tripping, ordering, idempotency of the invalidate operation. Commit
  `proptest-regressions/` to the repository; a found failure that is not
  committed will be found again.
- **Time is injected, never read ambiently.** Take `clock: &dyn Clock` (or a
  `Clock` newtype) in anything that stamps `expires_at`; tests use a fixed
  clock. `tokio::time::pause()` covers timers, not business timestamps.
- **A panic in a request path is a test failure, not a 500.** Integration tests
  run with the same lint posture as release (§8), and a `CatchPanicLayer` exists
  only to keep the process alive — never to let a test pass.
- Do not test private functions to inflate coverage. Coverage is a diagnostic
  (`cargo llvm-cov nextest`), never a gate that rewards `#[cfg(test)]` laundry.

---

## 3. Test infrastructure defaults (isolation, determinism, evidence)

- **Record browser evidence by default.** Playwright video stays on for the
  frontend e2e suite, with a single documented off-switch
  (`E2E_VIDEO=off`) and `trace: "on-first-retry"`. Discovering after a flaky
  week that a suite was blind on failure is avoidable; the storage cost is
  trivial next to a day of guessing. For a Leptos/HTMX frontend the same
  Playwright suite applies — the driver does not care what compiled the HTML.
- **Isolate hard.** A separate test database; `#[sqlx::test]` per-test databases;
  unique-per-run identifiers (`{label}.{run_id}@example.test`, where `run_id`
  comes from one place); no shared state between suites; suites runnable in
  parallel on one machine.
- **Deterministic fixtures.** Named people, not `user-123`, with different name
  pools per role so failures read naturally. Load them with
  `#[sqlx::test(fixtures(…))]` (sqlx) or a `diesel_async` fixture loader; either
  way the fixture files are SQL, reviewed like code, and versioned with the
  migrations that gave them meaning.
- **Freeze the clock and seed randomness.** `Clock::fixed(...)` for business
  time, `StdRng::seed_from_u64(...)` for generated data, `insta` with
  `INSTA_UPDATE=no` in CI so an unexpected snapshot change fails instead of
  being accepted.
- **Layout by type, decided day one:** `crates/` (application), `tests/`
  (integration, one file per domain), `fixtures/` (SQL), `frontend/e2e/`,
  `frontend/src/**/*.test.tsx`. Keep it; mixed layouts are where the
  "which suite runs where" confusion lives.
- **Containers for the database, not for the code under test.** Local tests hit
  `docker compose up -d db`; CI hits a service container. Do not spin a
  testcontainers Postgres per test — it is the slowest possible way to isolate
  what `#[sqlx::test]` already isolates.

---

## 4. Database and data-access discipline (the two-source-of-truth trap)

*Decision: `DR-02`. The card, with code for all three options, is in §12.*

The costliest smell in the original project was carrying one field in two
spellings and writing hand-rolled mappers to reconcile them. Rust removes most
of the excuse: the database and the language share `snake_case`, and the only
place a naming change is legitimate is the wire boundary, where it should be a
*declarative attribute*, not a function.

### 4.1 One casing, one translation, by the compiler

- **`snake_case` everywhere in Rust and Postgres.** No `#[sqlx(rename)]`
  scaffolding to satisfy a style preference; `clippy::struct_field_names` and the
  database agree by construction.
- **The wire boundary is the single translation point**, expressed as an
  attribute on the type that crosses it:

```rust
#[derive(Debug, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct RequestSummary {
    pub id: RequestId,
    pub owner_id: ActorId,
    pub created_at: OffsetDateTime, // → "createdAt"
}
```

- **No `mappers/` module, no `into_dto()` helpers, no `#[derive(FromRow)]`
  struct plus a parallel `Request` domain struct that must be kept in step.** One
  struct per direction per endpoint: the row struct is the read shape, the input
  struct is the write shape, and both are checked against the SQL by the compiler
  (`sqlx::query_as!`) or against `schema.rs` (diesel). A `From` impl is allowed
  only where a genuine type change occurs (e.g. `Money<Currency>` from
  `amount_cents`), lives beside the type, and is unit-tested.
- Make the rule checkable: CI fails on a `src/mappers` path, on `fn into_`, and
  on any `#[serde(rename)]` outside `src/wire/`. Renaming a column then becomes
  a compile error in one place rather than a silent `undefined` on a page.
- **Do not expose the row struct on the wire on a write path.** Read projections
  may be `Serialize` directly; request bodies are their own type with their own
  validation, so a client cannot set `owner_id` or `expires_at` by posting extra
  fields. Unknown fields are rejected (`#[serde(deny_unknown_fields)]`), which is
  the mass-assignment guard the Node stack gets from a schema validator.

### 4.2 Every table goes through the chosen data layer

- **All SQL lives in the domain module that owns the table** (`src/requests/queries.rs`),
  never inline in a handler, never built by string concatenation. The handler
  receives a typed value and calls a named function.
- **Compile-time checking is the point.** With `DR-02 = sqlx`, every query is a
  `query!`/`query_as!` macro; a renamed column breaks `cargo check`. With diesel,
  every query goes through `schema.rs`. With sea-orm, entity definitions are
  generated once and reviewed. **Never mix two data layers in one workspace**
  (sqlx *and* diesel, or sea-orm *and* raw `tokio-postgres`) — two migration
  stories and two type systems is the two-source-of-truth trap wearing a
  different hat.
- **Raw SQL is an explicit escape hatch, not a style.** Analytical queries,
  `FOR UPDATE SKIP LOCKED` workers, and Postgres-specific features may use
  `sqlx::query!` (still compile-checked) or diesel's `sql_query`; the latter
  requires an addendum naming why the typed layer could not express it. There is
  no such thing as "temporary" raw SQL.

### 4.3 Soft deletion, enforced by the schema

- Every entity that can be "removed" gets a nullable `expires_at timestamptz`
  from day one, a **partial unique index** over the live rows, and an
  `invalidate` — never a `DELETE`:

```sql
CREATE TABLE requests (
    id         uuid PRIMARY KEY,
    owner_id   uuid NOT NULL,
    title      text NOT NULL,
    expires_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX requests_live_title_per_owner
    ON requests (owner_id, title)
    WHERE expires_at IS NULL;
```

- **Filter active rows on every read and every authorization check.** A read
  that forgets `expires_at IS NULL` resurrects deleted data, and an
  authorization check that forgets it lets a deactivated membership keep its
  access. Encode the filter once:
  - sqlx: an `active_requests` view, and the rule that read queries select from
    `active_*` views;
  - diesel: `fn active(conn) -> impl QueryDsl` in the domain module, used by every
    read;
  - sea-orm: a scoped `Entity::find_active()`.
- **Views are read-only by contract.** Writes and `RETURNING` go to the base
  table; a view in a `RETURNING` clause is a runtime error waiting for the first
  `invalidate` path.
- Add a test per table asserting that an invalidated row is invisible to the list
  endpoint *and* that the detail endpoint returns `404` — the two paths forget
  independently.

### 4.4 Foreign keys must reject soft-deleted targets

A plain FK proves the row existed once. It does **not** prove the target is still
active, so a deactivated actor can still be the owner of a brand-new request. The
obvious fix does not work either: Postgres cannot reference a partial unique
index, and a composite FK that smuggles the nullable `expires_at` into the child
row is silently unenforced, because `MATCH SIMPLE` treats a row with any NULL FK
column as satisfying the constraint. `MATCH FULL` does not rescue it — it rejects
the mixed case instead of validating it. Enforce the invariant with a trigger:

```sql
CREATE FUNCTION assert_actor_is_active() RETURNS trigger AS $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM actors WHERE id = NEW.owner_id AND expires_at IS NULL
    ) THEN
        RAISE EXCEPTION 'owner % is not an active actor', NEW.owner_id
            USING ERRCODE = 'foreign_key_violation';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER requests_owner_active
    BEFORE INSERT OR UPDATE OF owner_id ON requests
    FOR EACH ROW EXECUTE FUNCTION assert_actor_is_active();
```

- **The trigger fires on insert and on owner change**, so no application path —
  handler, worker, migration, or psql session — can create a reference to an
  invalidated actor. Soft-deleting the parent stays possible, which the
  composite-key alternative forbids (its FK would block the parent's `UPDATE`).
- **Triggers are invisible to the data layer**, so they carry documentation and
  tests: list every trigger in the table's doc comment, and assert in the
  integration suite that inserting a row against an invalidated target fails with
  `23503`. A trigger nobody knows about is a future "why is this insert
  failing?" bug hunt.
- **Do not soft-delete the target of a live relationship as a way to hide it.**
  Invalidate the relationship, then the entity; the trigger is the guard rail,
  not the design.
- Apply this to every relationship whose target supports soft deletion, and note
  the trigger in the schema snapshot next to the table it protects.

### 4.5 IDs, time, and actors

- **UUIDv7, minted in exactly one place.** `Uuid::now_v7()` inside the domain's
  constructor, never in a handler, never in SQL (`gen_random_uuid()` is v4 and
  defeats the index-locality argument). Wrap it: `pub struct RequestId(Uuid)` with
  `#[serde(transparent)]`, `sqlx::Type` (or diesel `AsExpression`), and a
  `FromStr` that validates the version. Newtypes stop the classic
  "passed `owner_id` where `request_id` was expected" bug at compile time.
- **Timestamps are `timestamptz` end to end** (`time::OffsetDateTime` or
  `chrono::DateTime<Utc>` — pick one and lint the other out). Never `timestamp`
  without a zone; never a string on the wire.
- **System and non-human actors are real rows**, inserted by migration, so every
  `actor_id` is a genuine FK. No `'system'` string literal, no nullable
  `actor_id` meaning "the machine did it". Decide before the first sentinel
  leaks in; retrofitting means a data migration and an audit of every
  `actor_id IS NULL` branch.
- **Authorization queries join the actor's live membership**, not a cached role
  in the session. A session that survives a role change must re-derive
  authorization on every request; caching permissions in a cookie is how
  revoked access keeps working.

---

## 5. Schema evolution (migrations and wholesale snapshot, same change)

Two halves, always in sync, landed in the same commit. Skipping either produces
exactly the drift this section exists to prevent.

1. **A wholesale snapshot** (`db/schema.sql` plus `db/seed.sql`) that a brand-new
   database applies from zero. Every `CREATE TABLE` lists every current column —
   never a base schema followed by a changelog of `ALTER`s.
2. **A numbered migration** (`migrations/0007_add_request_priority.sql`) that an
   already-provisioned database applies to catch up.

### 5.1 Rules that make the twin workflow real

- **Zero-padded, sequential, immutable.** `0007_…sql` is never edited after
  merge; a fix is `0008_…sql`. A rewritten history is a database you cannot
  rebuild.
- **Do not write `BEGIN`/`COMMIT` inside a sqlx migration.** sqlx already runs
  each file in a transaction; nesting produces a warning and a savepoint you did
  not intend. The exception is explicit: `-- no-transaction` on the first line
  for `CREATE INDEX CONCURRENTLY`, and such a file must be re-runnable.
- **Idempotent where re-run is possible** (`IF NOT EXISTS`, `ON CONFLICT DO
  NOTHING`) so a re-provision, a retried CI job, or a partially applied
  environment converges instead of wedging.
- **Apply pending migrations on boot** (`sqlx::migrate!("./migrations").run(&pool)`,
  guarded by an advisory lock so two replicas do not race) **and** expose a
  standalone command (`cargo run -p <app> -- migrate`) for operators and tests.
  `#[sqlx::test(migrations = "./migrations")]` means every test runs the real
  migration path, which is the cheapest possible check that it is not broken.
- **Prove the halves agree, in CI.** Build one database from `db/schema.sql`,
  another by running the migrations from scratch, dump both with
  `pg_dump --schema-only --no-owner`, normalise, and `diff`. A snapshot that has
  drifted from the migrations fails the build with a readable diff instead of
  surfacing as a production-only surprise:

```bash
# scripts/check-schema-parity.sh
psql "$SNAPSHOT_URL" -v ON_ERROR_STOP=1 -f db/schema.sql
sqlx database create --database-url "$MIGRATED_URL"
sqlx migrate run --database-url "$MIGRATED_URL"
diff <(normalise_schema "$SNAPSHOT_URL") <(normalise_schema "$MIGRATED_URL")
```

- **Every schema change = snapshot update + migration file**, in the same
  commit. Reviewers check both halves; the parity script is the second reviewer.

### 5.2 Destructive changes are a sequence, not a statement

Renaming or dropping a column breaks a running binary. Use expand/contract:
add the new column and dual-write in release *n*, backfill in *n+1*, switch reads
in *n+2*, drop the old column in *n+3*. Each step is its own migration and its own
addendum. A single `ALTER TABLE … RENAME COLUMN` in a monolith deploys fine and
then paged the team at 02:00 for the previous pod that was still on the old code.

---

## 6. Code conventions that prevent whole classes of bugs

*Decisions: `DR-04` (wire contract), `DR-07` (error shape).*

### 6.1 Typed wire contracts, generated not remembered

The original incident was a renamed response field: the server shipped
`ownerId`, a test helper still read `owner_id`, the value was `undefined`, and a
demo video went out showing an empty column. Rust makes the server side of that
rename a compile error — and does nothing at all for the TypeScript side unless
the contract is generated from the server.

- **The Rust types are the source; the TypeScript types are generated.** With
  `utoipa`, the router's annotations produce an OpenAPI 3.1 document, and
  `openapi-typescript` turns it into `schema.ts` that `openapi-fetch` consumes:

```rust
#[derive(Serialize, Deserialize, ToSchema)]
pub struct RequestSummary {
    /// Stable UUIDv7 identifier.
    #[schema(value_type = Uuid)]
    pub id: RequestId,
    pub title: String,
    pub status: RequestStatus,
}

#[utoipa::path(get, path = "/api/requests/{id}", tag = "requests",
    params(("id" = Uuid, Path, description = "Request id")),
    responses((status = 200, body = RequestSummary), (status = 404)))]
pub async fn get_request(
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<RequestSummary>, ApiError> {
    Ok(Json(state.requests.summary(RequestId::from(id)).await?))
}

pub fn openapi() -> utoipa::openapi::OpenApi {
    use utoipa::OpenApi;
    #[derive(OpenApi)]
    #[openapi(paths(get_request, list_requests), components(schemas(RequestSummary)))]
    struct Api;
    Api::openapi()
}
```

- **The generated document is committed and verified.** `cargo run --bin
  dump-openapi > openapi.json` runs in CI followed by `git diff --exit-code
  openapi.json`, then `npm run gen:api` followed by a second
  `git diff --exit-code frontend/src/lib/api/schema.ts`. A handler change that
  alters the wire shape cannot merge without the client types changing with it.
  Without the second diff the first is theatre.
- **Route registration is checked too.** A `#[test]` asserts every path in
  `openapi.json` exists in the `Router` (and vice versa). Registration guards
  against the handler that is annotated, tested, and never mounted.
- **Errors have one shape** (`DR-07`): `application/problem+json` per RFC 9457,
  produced by a single `IntoResponse for ApiError` impl. The client never parses
  two error conventions.
- **Validation happens at the extractor boundary**, once, and returns the same
  problem shape. `garde`/`validator` on the input struct, invoked by a custom
  `Json` extractor or inside the handler's first statement; a second validation
  pass deeper in the domain is allowed only for invariants that require a
  database read.
- **External contract keys are not yours to rename** (a webhook field spelled
  `user_id` in someone else's API stays `user_id` on the wire). Keep them in
  `src/wire/external/` and let the internal type be idiomatic; that is the one
  place a `#[serde(rename = "…")]` is correct, and the lint from §4.1 permits
  exactly that directory.
- **Idempotency for unsafe retries.** Any `POST` a client may retry takes an
  `Idempotency-Key` header stored with the response, so a double-submit cannot
  create two rows. This is a wire-contract decision, not a later feature.

### 6.2 `data-testid` at authoring time

- Every interactive element gets a `data-testid` as it is written, with the
  convention `{component-kebab}__{element-role}` (`request-table__row`,
  `request-form__submit`). Repeated rows share one testid; scope by anchor text
  first, then by `data-testid` on the container.
- Testids are a **stable contract** between the component, its unit test, and
  the Playwright suite. A missing one is a defect, not a nice-to-have; add a
  lint/test that fails when an interactive element (button, input, select, link
  rendered by a component) has no testid.
- Do not use CSS classes or generated ids as selectors. They are styling and
  hydration implementation details, and refactoring them must not break tests.

### 6.3 Copy hygiene

- **Never show internal design decisions to end users.** Rationale belongs in
  doc comments and addenda (`///`, `//!`), never in a label, tooltip, empty
  state, or error string. Scrub internal slugs, `DR-` ids, and table names from
  shipped copy.
- **Error text is user-facing copy with a separate diagnostic channel.** The
  problem document carries a stable `type` URI and a human sentence; the SQL
  error, the backtrace, and the `tracing` span carry the diagnosis. A client
  must never see `sqlx::Error::Database`.
- Keep user-facing copy user-facing and internals internal — and keep
  third-party keys exactly as the external system requires, even when they
  disagree with our casing.

---

## 7. Function design and module structure (decide on day one)

*Decisions: `DR-03` (crate layout), `DR-05` (frontend).*

Retrofitting these rules into a shipping codebase costs weeks. The limits are
enforced by `clippy` where a lint exists, because a rule with a linter survives
and a rule in prose does not.

### 7.1 Size, nesting, parameters

- **≤ 20 lines target per function body, 50 hard.** `clippy.toml`:

```toml
# clippy.toml — the limits live where the linter reads them
too-many-arguments-threshold = 3        # clippy does not count `self`
too-many-lines-threshold = 50
excessive-nesting-threshold = 3
```

- **Guard clauses over nesting.** Validate and `return` at the top; the happy
  path stays at one indentation level. Use `let … else` for shape checks, so the
  error branch cannot fall through:

```rust
fn parse_window(raw: Option<&str>) -> Result<Window, ConfigError> {
    let Some(raw) = raw else { return Ok(Window::default()) };
    raw.parse().map_err(|_| ConfigError::InvalidWindow(raw.to_owned()))
}
```

- **≤ 3 parameters** (plus `&self`), beyond which take a typed parameter object.
  **No boolean parameters** — `fn render(html: bool)` becomes `render_html` and
  `render_json`; a flag is two functions wearing one name. **Preserve the whole
  object**: `fn send(invoice: &Invoice)` beats five extracted fields that can
  arrive inconsistent.
- **Naming.** No `*Manager`, `*Service`, `*Factory`, `*Helper` nouns
  (M-WEASEL-WORDS): they collect everything and describe nothing. Domain modules
  are named for the noun (`requests`), operations for the verb
  (`requests::invalidate`). Booleans read `is_`/`has_`/`should_`/`can_`; no
  abbreviations in domain code.
- **Mutation is explicit and owned.** Prefer consuming updates
  (`fn with_title(self, title: String) -> Self`) or a `&mut` confined behind one
  function, over public mutable fields. Separate query from command: `&self`
  returns a value, `&mut self` changes state, never both in one call.

```rust
// Query: no side effects.
fn outstanding_total(&self) -> Money { self.lines.iter().map(Line::total).sum() }

// Command: mutates, returns nothing to mistake for a fresh read.
fn apply_payment(&mut self, payment: Payment) -> Result<(), LedgerError> { /* … */ }
```

### 7.2 Errors are typed at the centre and erased at the edge

- **`thiserror` for domain and library errors, `anyhow` only in `main`, CLI
  glue, and tests.** A `Result<_, anyhow::Error>` in a handler means the client
  cannot be given a stable problem type, and the match arm that distinguishes
  "not found" from "forbidden" degrades into string inspection.
- One `ApiError` enum per application maps domain errors to problem documents
  with `#[error]` + `IntoResponse`. Every new variant must decide its status and
  whether it discloses existence.
- **No `unwrap`/`expect`/`panic!`/slice indexing in request paths**, enforced by
  lints rather than review:

```rust
// src/lib.rs — applies to unit tests inside this crate; integration tests in
// tests/ are separate crates and may unwrap freely.
#![cfg_attr(
    not(test),
    deny(
        clippy::unwrap_used, clippy::expect_used, clippy::panic,
        clippy::indexing_slicing, clippy::todo, clippy::unimplemented,
        clippy::too_many_arguments, clippy::too_many_lines,
        clippy::excessive_nesting, clippy::fn_params_excessive_bools,
        clippy::allow_attributes_without_reason,
    )
)]
```

- Startup is the one place `expect` is legitimate, and it names what was
  missing: `expect("DATABASE_URL must be set; see .env.example")`. A panic in
  `main` before the server binds is a configuration error, not a request path.

### 7.3 Dependency injection without a container

- **Concrete types first, generics second, `dyn Trait` last** (M-DI-HIERARCHY).
  A handler takes `State<AppState>`; `AppState` holds `PgPool`, `Clock`, and
  config. There is no `trait RequestRepository`.
- **Traits are for two live implementations or a public API boundary**, not for
  mocking. §2 already forbids mocking the data layer, so a repository trait earns
  its indirection only when a second real backend exists (Postgres plus an
  in-memory store in a test harness that is itself under test). If you cannot
  name the second implementation, do not write the trait.
- **No global mutable state.** No `static mut`, no `lazy_static` cache without a
  stated invalidation story; `OnceLock` is for immutable process-wide data
  (regexes, compiled config) only.
- **Blocking work never runs on a runtime worker.** `argon2` hashing, filesystem
  I/O, and any synchronous driver go through `tokio::task::spawn_blocking`;
  `clippy::await_holding_lock` plus review catches the rest. A 300 ms CPU-bound
  hash on an async worker stalls every future on that thread.

### 7.4 Modules: group by domain, split by re-export

- **Group by domain feature, not by type.** `src/requests/{mod.rs, handlers.rs,
  queries.rs, model.rs}` — not `src/handlers/`, `src/models/`, `src/services/`.
  A change to the `requests` feature touches one directory.
- Files ≤ 400 LOC typical, **800 hard**. When a file must split, keep the old
  module path as the public face and re-export the moved items, so call sites do
  not move:

```rust
// src/requests/mod.rs — after splitting queries.rs into a directory
mod handlers;
mod model;
mod queries;

pub use handlers::{get_request, list_requests};
pub use model::{Request, RequestId, RequestSummary};

// No `pub use queries::*;` — glob re-exports hide where a name came from
// (M-NO-GLOB-REEXPORTS). Re-export explicitly, or `#[doc(inline)]` when the
// item belongs to this module publicly.
```

- **No circular dependencies between peer domains.** `requests` may call
  `actors`; `actors` must not call `requests`. Enforce it:
  `cargo modules dependencies --acyclic` in CI, or, once `DR-03` lands on a
  workspace, the crate graph itself refuses the cycle at compile time.
- **Workspace boundaries are the real module system.** When a domain needs its
  own release cadence, lint posture, or compile isolation, make it a crate.
  Otherwise a single crate and modules is less ceremony — which is why `DR-03`
  is a question, not a default.
- One concern per file; file names are the contract.

### 7.5 Frontend: a component renders, a hook decides

Applies to the React frontend (`DR-05 = A`) and, with `view!` substituted for
JSX, to Leptos. The rule is unchanged from the original template because the
failure it prevents is unchanged: a component that satisfies every structural
rule and still computes domain rules per render.

- **Split along the server boundary, not the "looks like state" boundary.** The
  component owns layout, view-only state, event wiring, and DOM effects. The
  hook owns anything that calls the API, computes over server data, validates, or
  fetches.
- **The hook returns a plain object; the component destructures it.** No JSX in
  the hook; no API import in the component. That import is the checkable signal:
  `grep -c "lib/api" <Component>.tsx` must be `0`.
- **Hooks live beside their tests** (`lib/hooks/use<Feature>.ts` +
  `use<Feature>.test.ts` with `renderHook`), and must not import from
  `components/`.
- **Move bodies, don't rewrite them.** A separation refactor is verifiable only
  when the extracted function diffs against the original with whitespace
  normalised; anything else is a behaviour change wearing a refactor's clothes.
- **Keep the JSX interior presentation-only.** Between `return (` and its closing
  `)` only markup, pre-computed bindings, and wiring. No
  `.filter()`/`.reduce()`/`.sort()`/`.find()`/`.some()`/`.every()` inside JSX; a
  bare `.map()` rendering a list is fine. Compute a derivation once — repeating
  `xs.filter(p)` in the empty check and the list runs the predicate twice and
  reads as two rules that happen to agree. Inline handlers are wiring only (a
  setter, a navigation, a `.focus()`); a branch or computation moves to a named
  binding or the hook. No inline `new Date()`, `.toFixed()`, or `JSON.parse` —
  use a formatter helper.
- A derivation inside JSX cannot be unit-tested without rendering; computed
  twice it drifts; buried in an `onChange` it is domain logic no test reaches.

### 7.6 Code smell → remedy

| Smell | Remedy |
| --- | --- |
| Long function (> 50 lines) | Extract Function; `clippy::too_many_lines` |
| Deep nesting (> 3 levels) | Guard Clauses, `let … else`; `clippy::excessive_nesting` |
| Long parameter list (> 3) | Parameter Object struct; `clippy::too_many_arguments` |
| Boolean parameter | Two named functions; `clippy::fn_params_excessive_bools` |
| `trait FooRepo` with one impl | Delete the trait; take the concrete type |
| `*Manager` / `*Service` / `*Factory` | Rename to the domain noun + verb |
| `impl From<Row> for Dto` chains | One struct per direction; `#[serde(rename_all)]` on the wire type |
| `sqlx::query(&format!(…))` | `query!` with bind parameters; no string-built SQL |
| `unwrap()` in a handler | `?` into `ApiError`; lint denies it |
| Blocking call in `async fn` | `spawn_blocking` or a sync boundary |
| God module (> 800 lines) | Split directory module + explicit re-exports |
| `pub use sub::*;` | Explicit re-exports (`M-NO-GLOB-REEXPORTS`) |
| Feature envy across domain modules | Move the function to the data's owner |
| Duplicated derivation in JSX | Explaining Variable above the return |
| Fat inline `onChange` with a branch | Extract Function, or move to the hook |
| Speculative generality | Delete it (YAGNI) |

Source: Martin Fowler's *Refactoring* (2nd ed.), plus Microsoft's Pragmatic Rust
Guidelines (`M-NO-GLOB-REEXPORTS`, `M-DI-HIERARCHY`, `M-WEASEL-WORDS`,
`M-ERRORS-CANONICAL-STRUCTS`, `M-SMALLER-CRATES`).

---

## 8. Validate early and honestly

*Nothing in this section is a decision. The ladder is what makes the other decisions honest.*

### 8.1 The ladder of claims

Each rung proves strictly more than the one above. **Name the rung you actually
reached**; claiming a higher one is how a broken build ships with a green
message.

| Rung | Command | Proves |
| --- | --- | --- |
| 1. Format | `cargo fmt --all --check` | Parses; style settled |
| 2. Types | `cargo check --workspace --all-targets` | Names, traits, types agree |
| 3. Lints | `cargo clippy --workspace --all-targets -- -D warnings` | Size/panic/lint rules hold |
| 4. Unit | `cargo nextest run --workspace --lib` | Pure logic, no database |
| 5. Doc | `cargo test --workspace --doc` | Examples in doc comments compile and pass |
| 6. Integration | `cargo nextest run --workspace` with `DATABASE_URL` set | Real SQL, real migrations, real authorization |
| 7. E2E | `playwright test` against the built app | Real browser, real backend |
| 8. Supply chain | `cargo deny check` + `cargo audit` | Advisories, licences, bans, sources |
| 9. Container | build, run, `curl :3000/healthz` | The contract in §10.1 |

Rules:

- **`cargo check` passing is not "tests pass".** Say "typechecked" and say what
  did not run. A sandbox without Postgres or a browser cannot reach rungs 6–7,
  and a report that blurs that boundary is worse than no report.
- **Never make CI green by disabling a test.** `#[ignore]` requires an addendum
  and a ticket link in the attribute:
  `#[ignore = "blocked on 0012; see TICKET-431"]`.
- **The merge gate is the full ladder** — format, types, lints, unit, doc,
  integration with a real database, e2e with video, supply chain. Anything less
  is a local convenience, not a gate.
- **Append the caveat to commits made under constrained tooling.** A trailer
  keeps the honest claim attached to the commit instead of living in a chat:

```text
Validation: rungs 1-4 (fmt, check, clippy, unit). Integration and e2e NOT run:
no DATABASE_URL in this environment. Run `just verify` before merge.
```

### 8.2 How the Rust gates are configured

- **Pin the toolchain.** `rust-toolchain.toml` with `channel = "1.99.0"` and
  `components = ["rustfmt", "clippy"]`, plus `rust-version = "1.99"` and
  `edition = "2024"` in `Cargo.toml`. CI and local builds use the same compiler;
  an unpinned toolchain turns a Clippy upgrade into an unrelated red build on a
  Friday.
- **`RUSTFLAGS="-D warnings"` in CI only**, never in `.cargo/config.toml`:
  setting it locally invalidates the whole dependency cache on every change and
  turns a dependency's warning into your blocked release.
- **Lint policy lives in exactly one place.** §13 is the profile: the manifest
  tables, `clippy.toml`, and the per-crate `[lints] workspace = true` opt-in.
  Do not restate it here or in a crate manifest — two copies of a lint policy
  drift, and the copy that wins is whichever one the tool happened to read.
- **`#[expect(lint, reason = "…")]` is the default suppression.** A bare
  `#[allow]` is denied by `allow_attributes_without_reason`, and an `expect`
  fails the build once the lint stops firing — so stale suppressions disappear
  instead of accumulating.
- **`cargo-deny` owns supply-chain policy** (`deny.toml`: advisories, licence
  allowlist, duplicate-version bans, crates.io-only sources). `cargo audit` is
  the quick local check; `cargo deny check` is the gate.
- **`cargo machete`** (or `cargo-udeps` on nightly) fails on an unused
  dependency — unused crates are unreviewed attack surface and build time.
- **`unsafe_code = "forbid"`** in application crates. If a dependency needs
  `unsafe`, that is the dependency's business; our code does not get an
  exception without an addendum.

---

## 9. Reproducible local dev and the environment story

*Decision: `DR-10` (dev orchestration).*

- **One command from clone to green.** `just bootstrap` installs the toolchain,
  copies `.env.example` to `.env` when absent, starts Postgres, runs migrations,
  and prints the next three commands. `just verify` runs the whole ladder of
  §8.1. `just up` runs the app; `just e2e` runs the browser suite with video on.
- **`just` is a task list, not a build system.** A `justfile` with ~10 recipes is
  discoverable and typed by autocomplete. `cargo xtask` is the alternative when
  the logic needs to be testable Rust; `make` when the team already has it.
  The choice is `DR-10` and it is recorded, not assumed — mixed `make`/`just`/shell
  entry points are where "works on my machine" lives.
- **Layers, not a pile of variables.** One `Config` struct, loaded once at
  startup by `figment`/`config`: defaults → `<env>.toml` → environment
  variables → CLI flags. Every field is typed (`Option<Url>`, `u16`, enum), so a
  malformed value fails at boot with the variable's name, not at request 400.
- **Secrets are a distinct type.** `secrecy::SecretString` for tokens and
  passwords, never `String`, so a stray `{:?}` or log line cannot print them; the
  type does not implement `Display`.
- **The env files are a three-file contract, committed as templates only:**
  - `.env.example` — every variable, with a safe placeholder and one comment
    line each;
  - `.env` — developer's real values, git-ignored;
  - `.env.test` — points at the test database, used by `just verify` and CI.
  Never one shared database between dev and test; a test that truncates the dev
  database has happened to someone on every team that skipped this.
- **Offline builds must work.** Commit `.sqlx/` (`cargo sqlx prepare
  --workspace`) and set `SQLX_OFFLINE=true` in the Docker build and CI check job,
  so compilation does not secretly require a live database. A stale `.sqlx/`
  fails `cargo sqlx prepare --check`, which is a separate, explicit CI step.
- **Toolchain choices are consistent across layers.** Rust version, Postgres
  major version, Node version for the frontend, and image digests are declared in
  one place each (`rust-toolchain.toml`, `compose.yaml`, `.nvmrc`,
  `Dockerfile`) and referenced, not restated, everywhere else.

---

## 10. Deployment and CI/CD from day one: sandbox containers + SHIP-HATS (kept inert)

Decide how the project ships before the first feature, and commit the deployment
files with the first code. Retrofitting a container contract and a government
pipeline onto a finished app surfaces every hidden assumption at once: a server
bound to `127.0.0.1`, proxy headers trusted by hop count, an unpinned base image,
a `libpq` dependency with no TLS story, a script that only runs on one shell.

### 10.1 The container contract (active from day one)

*Decision: `DR-09` (runtime image).*

- **Listen on `0.0.0.0:3000`.** Read `HOST` (default `0.0.0.0`) and `PORT`
  (default `3000`) from the environment and bind to them. A server bound to
  `127.0.0.1` inside a container is unreachable from the ingress and fails in a
  way that looks like a firewall problem:

```rust
let addr = SocketAddr::new(config.host.parse()?, config.port);
let listener = tokio::net::TcpListener::bind(addr).await?;
tracing::info!(%addr, "listening");
axum::serve(
    listener,
    app.into_make_service_with_connect_info::<SocketAddr>(), // needed for §10.1 proxy trust
).with_graceful_shutdown(shutdown_signal()).await?;
```

- **Multi-stage build from the lockfile, `cargo-chef` for layer caching,
  `--locked` everywhere**, no `cargo install` at runtime, no compiler in the
  final image. Build the binary with `rustls` instead of OpenSSL so the runtime
  layer needs no TLS shared library.
- **Runtime stage on distroless, numeric `USER`, pinned by digest.** Distroless
  has no shell, so the healthcheck must be a subcommand of the binary — which is
  a feature: it exercises the same config loader and the same database handle as
  production.

```dockerfile
# syntax=docker/dockerfile:1.7
# Pin the builder by digest in the real file; tag shown for readability.
FROM rust:1.99-bookworm AS chef
RUN cargo install cargo-chef --locked --version 0.1.71
WORKDIR /app

FROM chef AS planner
COPY . .
RUN cargo chef prepare --recipe-path recipe.json

FROM chef AS builder
COPY --from=planner /app/recipe.json recipe.json
RUN cargo chef cook --release --locked --recipe-path recipe.json
COPY . .
ENV SQLX_OFFLINE=true
RUN cargo build --release --locked --bin server

# distroless/cc is glibc-based; use distroless/static only for a musl build.
FROM gcr.io/distroless/cc-debian12:nonroot
COPY --from=builder /app/target/release/server /app/server
ENV HOST=0.0.0.0 PORT=3000
EXPOSE 3000
USER 65532:65532
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD ["/app/server", "healthcheck", "--url", "http://127.0.0.1:3000/healthz"]
ENTRYPOINT ["/app/server"]
```

- `sqlx::migrate!("./migrations")` **embeds** migrations in the binary, so the
  final image needs no `migrations/` copy; if migrations run from disk instead,
  copy the directory and say why in the Dockerfile.
- **`.dockerignore`** excludes `target/`, `.git/`, `.env*`, `frontend/node_modules/`,
  and `tests/` fixtures that are not needed at runtime. It must **not** exclude
  `viper-agent/` or any platform-supplied directory.
- **`Dockerfile.dev`** keeps the cloud-development contract the platform's VIPER
  agent expects (`COPY viper-agent/`, its entrypoint, `PORT=3000`,
  `VIPER_APP_PORT=3001`) and configures the dev server's host allowlist for a
  forwarded host name behind HTTPS. A Rust app needs no proxy allowlist — that is
  the framework's job in Node — but it does need `HOST=0.0.0.0` and a mount for
  `cargo`'s target cache, or every rebuild is cold.
- **`Dockerfile.cloudflared`** pins the cloudflared release, runs with
  `--no-autoupdate`, takes `TUNNEL_TOKEN` at runtime only, and routes the tunnel
  to the app service on port 3000.

#### Trust the proxy by address, never by hop count

The platform ingress reaches the container from a private address. Believe
`X-Forwarded-For`/`-Proto` **only** when the TCP peer is loopback, link-local, or
private; then take the **rightmost hop that is not itself a trusted proxy**.
"Trust every hop" lets a client choose its own address (rate-limit evasion).
"Trust nothing" makes every client share the proxy's address (per-client limits
become global) and hides HTTPS (no `Secure` cookies). A hop count is not a
policy: one framework's "trust 1 proxy" silently means "trust nobody" when the
chain is longer than expected.

```rust
fn client_ip(headers: &axum::http::HeaderMap, peer: IpAddr, trusted: &[IpNet]) -> IpAddr {
    if !trusted.iter().any(|net| net.contains(&peer)) {
        return peer; // not from our ingress: ignore the header entirely
    }
    headers
        .get("x-forwarded-for")
        .and_then(|value| value.to_str().ok())
        .into_iter()
        .flat_map(|value| value.split(',').rev())
        .filter_map(|hop| hop.trim().parse::<IpAddr>().ok())
        .find(|ip| !trusted.iter().any(|net| net.contains(ip)))
        .unwrap_or(peer)
}
```

`axum-ipware` (`ClientIpStrategy::rightmost_trusted_range`) and
`mogh_request_ip` implement the same semantics; use them rather than a bespoke
parser if they fit, but keep the CIDR list in configuration
(`TRUSTED_PROXY_CIDRS`), not in code. Unit-test the function with a table:
public peer + spoofed header, trusted peer + spoofed first hop, trusted peer +
all-trusted chain, malformed header.

**Test the contract, don't assert it.** Feed the image's `ENV` through the real
config loader in a unit test (a test that reads `HOST`/`PORT` from a fixture
matching the Dockerfile, so the two cannot drift). In CI, run the built image as
a service and `curl` it by network alias on port 3000. Lint Dockerfiles with
`hadolint`.

### 10.2 SHIP-HATS: what the platform requires (research, October 2026)

SHIP-HATS is GovTech's CI/CD platform in the Singapore Government Tech Stack.
Findings below come from public SHIP-HATS documentation; the platform's GitLab
and template sources need TechPass and SEED.

- **Platform.** GitLab Dedicated at `sgts.gitlab-dedicated.com` (Ultimate),
  alongside SonarQube, Nexus Repository Pro (npm, PyPI, Maven, Docker Hub, MCR,
  GHCR proxies), Nexus IQ (SCA), Fortify on Demand (SAST/DAST), Jira, Confluence.
  Code up to CONFIDENTIAL (CLOUD-ELIGIBLE) / SENSITIVE-NORMAL.
- **Templates.** `include:` the SHIP-HATS Templates from
  `innersource/sgts/ship-hats/ship-hats-templates`, **pinned to a release tag**
  (v1.1.12 as of September 2026; required for signing after Rekor's
  decommissioning on 30 September 2026). `include:` cannot take variables, so the
  ref is a literal. Hidden jobs are consumed with `extends`:
  `.build-and-push-docker-image` (Kaniko),
  `.copy-docker-image-from-one-remote-registry-to-another`,
  `.generate-gitlab-attestation`, `.sign-container`, `.verify-container`,
  `.trivy-scan`, `.nexus-iq-scan`, `.sonarqube-scan`,
  `.invoke-awscli-commands-with-assumerole` (OIDC, no long-lived keys).
- **Stage and job names are load-bearing** (inherited from the unmaintained E2E
  templates): `.pre`, `build`, `test`, `static-test`, `sign`, `runtime-test`,
  deploy stages; `build-job` and `deploy-prod-manual-job` / `deploy-final-job`
  must never be renamed.
- **Compliance is a Pipeline Execution Policy**, applied from the WOG Security
  Policy Project since March 2026 (legacy compliance pipelines ended 30 June
  2026; GitLab removes them in 20.0). Policy jobs run isolated and **never see
  the project's YAML variables**, so configure them as project/group CI/CD
  variables: `CF_LEVEL`, `SONAR_PROJECTKEY`, `SONAR_TOKEN`, `NEXUS_IQ_APP_ID`,
  `NEXUS_IQ_USERNAME`/`NEXUS_IQ_PASSWORD`, `COSIGN_PASSWORD`, `FOD_PAT`. Without
  tool credentials the framework falls back to GitLab's native scanners.
- **Compliance levels** (`CF_LEVEL` 1–4, default 4):

  | Level | Adds |
  | --- | --- |
  | 1 | Static scans (`.pre`, `static-test`) |
  | 2 | DAST and deployment gating |
  | 3 | Signing and verification |
  | 4 | SLSA L1/L2 provenance and SBOMs |

- **Runners.**

  | Runner | Tags | Notes |
  | --- | --- | --- |
  | CStack | none (default) | Kubernetes, non-root UID 65533, 4 vCPU / 8 GB; cannot build images |
  | SHIP-HATS Docker | `ship_docker`, `_med`, `_large`, `_arm` | Root, not privileged: build with Kaniko, not Docker-in-Docker |
  | GitLab-hosted (pilot) | `linux-small-amd64`, `-medium-`, `-large-` | Privileged, ephemeral VMs |

  Jobs cannot exceed two hours — which is why `cargo-chef`, `sccache`, and
  `cargo-nextest` are deployment concerns, not developer taste.

- **Supply chain.**
  - Pull images and packages through Nexus (`nexus-docker.ship.gov.sg`,
    `nexus-docker-mcr.ship.gov.sg`, `https://nexus.ship.gov.sg/repository/npm-proxy/`,
    …).
  - Since 3 June 2026 Nexus IQ **fails components younger than seven days** and
    integrity-rating violations: pin versions and let releases age a week.
  - From 1 November 2026 SHIP-HATS Docker runners **block end-of-life and
    blocklisted images**: pin the builder, the runtime, and every scanner to a
    supported release.
  - Pin scanner images to trusted releases (Trivy ≥ 0.69.3 after the March 2026
    incident). Nexus deletes artefacts after 180 days.
- **Access.** From 16 October 2026 Git over HTTPS needs a personal access token
  or an SSH key; passwords are refused. Tokens expire within 180 days. Only
  owners manage merge-request approval rules.

**Rust specifics.** A Cargo/crates.io proxy may not be available in every
SHIP-HATS tenancy. Do not assume it: confirm with the platform team, and if
egress is blocked, `cargo vendor` and commit the vendor directory with a
`.cargo/config.toml` source replacement (recorded as an addendum — it changes how
every dependency update works). If a Nexus Cargo proxy does exist:

```toml
# .cargo/config.toml — URLs are @@SHIPHATS_…@@ placeholders until activation
[source.crates-io]
replace-with = "shiphats"

[source.shiphats]
registry = "sparse+@@SHIPHATS_NEXUS_CARGO_URL@@"

[registry]
global-min-publish-age = "7 days"   # Cargo RFC 3923; matches the Nexus IQ gate
```

`global-min-publish-age` (Cargo 1.100, 12 November 2026; available on beta today)
makes the seven-day rule a resolver property rather than a reviewer's memory.
Until the toolchain is 1.100, enforce it in the pipeline by comparing each new
crate version's publish date against `cargo metadata`.

### 10.3 The discipline: SHIP-HATS files from day one, kept inert

- **Carry the pipeline from the start, inert.** Each SHIP-HATS file gets a
  `.shiphats` suffix, so GitHub, GitLab and local tooling ignore it until the
  project moves to SHIP-HATS:
  - `.gitlab-ci.yml.shiphats`;
  - `.gitlab/ci/*.gitlab-ci.yml.shiphats`;
  - `sonar-project.properties.shiphats`;
  - `.gitlab/CODEOWNERS.shiphats`;
  - `.gitlab/merge_request_templates/Default.md.shiphats`.
- **Placeholders, never secrets.** Values that differ per agency or project are
  `@@SHIPHATS_<NAME>@@`. Credentials are masked CI/CD variables and never appear
  in a rendered file.
- **A root script `activate-shiphats.sh` turns them active.** It runs on plain
  Bash 3.2+, needs no other tooling, **prompts for every value** with validation
  and defaults (`--non-interactive` reads `SHIPHATS_*` variables), renders every
  file before writing any, refuses unknown placeholders and existing files
  (`--force` overwrites), removes the inert copies (`--keep-inert` keeps them),
  and prints the GitLab settings that cannot live in files (project CI/CD
  variables, masked credentials, compliance framework, branch protection, code
  owners).
- **What the pipeline covers for a Rust service** — mirror the local ladder
  exactly, so the pipeline cannot be greener than `just verify`:
  - `static-test`: `cargo fmt --all --check`, `cargo check --workspace --all-targets`,
    `cargo clippy -- -D warnings`, `cargo deny check`, `cargo machete`;
  - `test`: `cargo nextest run --workspace` against a Postgres service, with
    `cargo sqlx prepare --check` when `DR-02 = sqlx`, then
    `cargo llvm-cov nextest --lcov --output-path lcov.info` for SonarQube
    (`sonar.rust.lcov.reportPaths=lcov.info`);
  - `build`: Kaniko image build (`--locked`, `SQLX_OFFLINE=true`) and a container
    smoke test that hits port 3000 on the container's interface;
  - `runtime-test`: Playwright e2e with video, against the built image;
  - scans, signing and provenance are left to the compliance framework (or
    GitLab's native scanners where it is not applied);
  - promotion through a manual, compliance-gated job.
- **Cache deliberately.** `cargo-chef` layer caching in the image, and
  `CARGO_HOME` + `target/` caching keyed on `Cargo.lock` in CI. Jobs cannot
  exceed two hours; an uncached Rust workspace with a heavy dependency tree can
  spend most of that compiling.
- **Keep the inert files in step, in the same change** as the scripts and tools
  they call — CI image tags matching `rust-toolchain.toml`, the nextest version
  matching the one in `justfile`, the Postgres major version matching
  `compose.yaml`. Test it: activate into a scratch directory in the test suite,
  then check that every stage, `needs`, and `extends` resolves, that the output
  passes the formatter, and that versions match. Validate the YAML against
  GitLab's CI schema with `check-jsonschema --builtin-schema vendor.gitlab-ci`.

### 10.4 Root scripts run everywhere

Scripts at the repository root (`dev.sh`, `activate-shiphats.sh`, and anything
`just` shells out to) must run on Bash 3.2, the `/bin/bash` macOS ships:

- no associative arrays, `mapfile`, or `${var,,}`;
- possibly-empty arrays expanded as `${a[@]+"${a[@]}"}`, because under `set -u`
  Bash before 4.4 calls an empty `"${a[@]}"` unbound.

Run their tests under a real Bash 3.2 (buildable from Apple's published source)
and add a static guard so Linux CI catches regressions. Lint with ShellCheck
(`pip install shellcheck-py`). A `dev.sh` that requires Bash 4 works on every
machine except the one the new joiner has.

---

## 11. What to decide before writing the first feature (checklist)

1. **Run the decision interview** (`DR-01`…`DR-03` before `src/`; the rest before
   the area they govern), and record each answer as a numbered addendum.
2. Source-of-truth spec location, addenda numbering, and
   `scripts/check-decisions.sh` wired into CI.
3. Toolchain pinned (`rust-toolchain.toml`, `rust-version`), workspace lints,
   `clippy.toml` limits, `cargo fmt` enforced.
4. Test DB isolation, `#[sqlx::test]`-style per-test databases (or the diesel
   equivalent), and a written "never mock the data layer" rule.
5. One IDOR negative test per route, asserting the exact status **and** the
   unchanged row; OWASP matrix in `docs/security-matrix.md`.
6. One data-access layer, no `mappers/` module, `active_*` filtering on every
   read and every authorization check.
7. Soft delete + partial unique indexes + trigger-enforced FK liveness + UUIDv7
   newtypes minted in one place + real actor rows.
8. Snapshot + migration twin per change, parity script in CI, migrations on boot
   behind an advisory lock, standalone `migrate` command.
9. Generated wire contract committed and diffed, route-registration test, one
   error shape, idempotency keys on retryable `POST`s.
10. `data-testid` convention, hook/component split, presentation-only JSX.
11. Test layout by type, Playwright video on by default, deterministic fixtures,
    frozen clock, seeded randomness.
12. The §8.1 ladder named honestly in every report, validation trailer on
    constrained commits, no silent `#[ignore]`.
13. One-command `just bootstrap` / `just verify`, three-file env contract,
    `SQLX_OFFLINE=true` builds.
14. Container contract (`0.0.0.0:3000`, numeric `USER`, healthcheck subcommand,
    digest-pinned bases), proxy trust by CIDR, hadolint, and a CI container test.
15. SHIP-HATS files inert with `.shiphats`, `activate-shiphats.sh`, kept in step
    in the same change, tested by activation into a scratch directory.
16. Supply chain: `cargo deny`, `cargo machete`, and a seven-day minimum release
    age at least as strict as the Nexus IQ gate.
17. The §13 strictness profile committed as four files, with every crate opting
    in via `[lints] workspace = true` and a test that proves the opt-in.
18. §14 signature rules agreed (borrowed parameters, `From` not `Into`, private
    fields, `#[non_exhaustive]` on public enums, the derive table).
19. §15 pattern decisions written down: where newtypes and parse-don't-validate
    are mandatory, and the one or two places typestate is justified.
20. §16 async invariants: bounded channels, timeouts on every outbound call, a
    named supervisor, cancel-safe `select!`, telemetry flushed on shutdown.
21. §17 baselines: release profile chosen (including the `panic` strategy), one
    benchmark with a noise budget, and the adversarial tools scheduled into
    nightly rather than wished for.

Answer these twenty-one up front and a greenfield Rust project avoids most of
the rework, silent drift, and "we should have written that down" moments this
template exists to prevent.

---

## 12. Decision cards

Send these as written — one card per decision, batched as in §0.7, always with a
recommendation. Each option's code example is real enough to compile against the
named crate version. If the user asks for an option that is not listed, take it,
note the deviation in the addendum, and say which risk it carries.

### DR-01 · HTTP framework

**Question.** Which HTTP framework serves the API?

**A. axum 0.8 — `tower`-native, extractor-based**

```rust
let app = Router::new()
    .route("/api/requests/{id}", get(get_request))
    .layer(TraceLayer::new_for_http())
    .with_state(state);

async fn get_request(
    State(state): State<AppState>,
    Path(id): Path<RequestId>,
) -> Result<Json<RequestSummary>, ApiError> {
    Ok(Json(state.requests.summary(id).await?))
}
```

- **Pros:** every service is `tower`, so timeouts, tracing, rate limits,
  compression, and auth are reuse, not rewrite; `Router` is a `tower::Service`,
  so `oneshot` tests need no socket; the largest ecosystem in 2026 and the
  default choice for new services; SQLx/diesel/utoipa/tower-sessions all ship
  axum examples first.
- **Costs:** middleware typing is famously fiddly (`from_fn` signatures,
  `State` extraction in layers); extractor ordering surprises (`Json` must be
  last); no built-in OpenAPI runtime (that is `DR-04`).
- **Choose if** you want composition, a huge middle-ground ecosystem, and a
  stack that a new Rust hire has probably seen.

**B. actix-web 4 — actor heritage, raw throughput**

```rust
#[actix_web::get("/api/requests/{id}")]
async fn get_request(
    path: web::Path<Uuid>,
    state: web::Data<AppState>,
) -> Result<web::Json<RequestSummary>, ApiError> {
    Ok(web::Json(state.requests.summary(*path).await?))
}
```

- **Pros:** excellent raw throughput and mature `#[get]` macro ergonomics;
  built-in multipart, sessions, and static files; a long production record.
- **Costs:** its own extractor/runtime idioms rather than `tower`, so the tower
  middleware ecosystem is not directly reusable; `web::Data` state plumbing is
  more ceremony than `State`; smaller share of new 2026 projects, so examples
  and answers skew older.
- **Choose if** raw request throughput is the binding constraint (unlikely for
  an internal SG government app) or the team already runs actix-web.

**Recommendation:** A. Throughput at this scale is bounded by Postgres, and
`tower` composition plus `oneshot` tests pay off on day two.

### DR-02 · Data access

Worked in full at §0.4 with all three code examples. Decision notes for this
project's context:

| Option | Wins when | Loses when |
| --- | --- | --- |
| `sqlx` 0.9 | The team writes SQL; you want compile-checked queries without a DSL | Reviewers cannot read SQL fluently; `.sqlx/` discipline slips |
| `diesel` 2.3 + `diesel-async` 0.9 | You want illegal queries to fail with no database; Drizzle-like schema-as-source | Wide schemas make `schema.rs` regeneration and compile time painful |
| `sea-orm` 2.0 | Reads are object graphs (`EntityLoader` kills N+1 by construction) | You need compile-time schema checking; the dependency tree is largest |

**Recommendation:** `sqlx`, unless the team is TypeScript-native and wants the
literal Drizzle analogue (then diesel). Do not mix two of them.

### DR-03 · Crate layout

**Question.** One crate, or a Cargo workspace from day one?

**A. Single crate with domain modules**

```text
src/
  main.rs
  lib.rs
  requests/{mod.rs, handlers.rs, queries.rs, model.rs}
  actors/{mod.rs, handlers.rs, queries.rs, model.rs}
tests/requests.rs
```

- **Pros:** fastest iteration, one `Cargo.toml`, no versioning ceremony, trivial
  `cargo test`; refactoring a module boundary is a `git mv`.
- **Costs:** one compile unit, so touching a shared type rebuilds the world; no
  per-area lint posture; nothing stops a peer-domain cycle but a CI tool.
- **Choose if** you have one binary and one team.

**B. Workspace with `domain`, `api`, `server` crates**

```toml
[workspace]
members = ["crates/domain", "crates/api", "crates/server"]
resolver = "3"
```

- **Pros:** the compiler enforces dependency direction (`api` may depend on
  `domain`; never the reverse); incremental builds only rebuild affected crates;
  `domain` can forbid `tokio`/`sqlx` and stay pure; separate lint/`deny` posture
  per crate.
- **Costs:** `cargo` path plumbing, feature-unification surprises, more files
  before the first endpoint works; overkill for a two-week tool.
- **Choose if** you expect multiple binaries (server, worker, CLI), or the domain
  must be testable without a runtime.

**Recommendation:** A, with `mod` boundaries matching the `DR-03`-B crate layout,
so promoting a module to a crate later is mechanical.

### DR-04 · Wire contract

**Question.** How do TypeScript types stay in step with Rust?

**A. `utoipa` → OpenAPI 3.1 → `openapi-typescript` + `openapi-fetch`**

```rust
#[utoipa::path(get, path = "/api/requests/{id}", tag = "requests",
    params(("id" = Uuid, Path, description = "Request id")),
    responses((status = 200, body = RequestSummary), (status = 404)))]
pub async fn get_request(
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<RequestSummary>, ApiError> {
    Ok(Json(state.requests.summary(id.into()).await?))
}
```

```ts
// generated: frontend/src/lib/api/schema.ts
const { data, error } = await client.GET("/api/requests/{id}", {
  params: { path: { id } },
});
```

- **Pros:** covers routes, path/query params, bodies, status codes, and error
  shapes; the client is typed end-to-end; the committed JSON is reviewable and
  diffable in CI; one artefact serves docs, the client, and contract tests.
- **Costs:** proc-macro annotations on every handler; generated `schema.ts` is
  verbose in review; the OpenAPI derivation can drift from actual extractors
  (hence the route-registration test in §6.1).
- **Choose if** the frontend is TypeScript and the API is the product boundary.

**B. `ts-rs` 12 — export Rust types to `.ts`**

```rust
#[derive(Serialize, TS)]
#[ts(export, export_to = "../frontend/src/lib/api/")]
pub struct RequestSummary { pub id: Uuid, pub title: String }
```

- **Pros:** zero route annotation; the generated types are minimal and readable;
  works with any frontend, including Leptos interop.
- **Costs:** types only — no paths, params, status codes, or error shapes, so the
  request URL and response status are still hand-typed on the client; no doc or
  contract-test artefact.
- **Choose if** you have a small, stable API and no need for generated clients.

**C. Hand-written TypeScript types**

- **Pros:** no build step, no macros, complete freedom.
- **Costs:** exactly the failure in §6.1 — a rename is silent until a page is
  blank. This is what the template exists to prevent.
- **Choose if** never, for an API that outlives one sprint.

**Recommendation:** A.

### DR-05 · Frontend

**Question.** What renders the UI?

**A. React + Vite + TypeScript (hybrid)**

```tsx
// lib/hooks/useRequest.ts
export function useRequest(id: string) {
  const { data, error, isLoading } = useQuery(requestQuery(id));
  return { request: data, error, isLoading };
}
```

- **Pros:** deepest hiring pool in any market; Playwright,
  testing-library, and design systems are first-class; the §7.5 hook/component
  discipline is well understood; the backend stays a pure JSON API.
- **Costs:** two languages, two toolchains, two dependency trees; the wire
  contract is a boundary that can drift (mitigated by `DR-04`); a Node runtime in
  the container build.
- **Choose if** UI velocity and hiring matter more than one-language purity.

**B. Leptos 0.7 — Rust everywhere**

```rust
#[component]
fn RequestTitle(#[prop(into)] id: RequestId) -> impl IntoView {
    let request = LocalResource::new(move || get_request(id));
    view! { <h1>{move || request.get().map(|r| r.title)}</h1> }
}
```

- **Pros:** one language and one type system across the wire; server functions
  remove the hand-written API layer; WASM bundle for interactive islands; no Node
  in the image.
- **Costs:** smaller ecosystem and hiring pool; WASM debugging is weaker than
  browser JS debugging; library churn between 0.6 and 0.7 was real; every UI
  contributor must learn Rust's borrow rules *and* reactive ownership.
- **Choose if** the team is Rust-first and the UI is modest.

**C. Askama/Maud + HTMX — server-rendered HTML**

```rust
#[derive(Template)]
#[template(path = "requests/list.html")]
struct RequestList<'a> { requests: &'a [RequestSummary] }
```

- **Pros:** least JavaScript, fastest first paint, progressive enhancement,
  trivially testable HTML, no client state to synchronise.
- **Costs:** interactivity is a request/response round trip unless you add
  islands; complex UI state gets awkward; the Playwright suite still applies but
  the component-level test story is thinner.
- **Choose if** the product is forms-and-tables, which many government internal
  tools are.

**Recommendation:** A for a product UI with a long life; C when the app is
CRUD-shaped and the team is small.

### DR-06 · Authentication

**Question.** How do users authenticate and how is the session carried?

**A. Server-side sessions in Postgres**

```rust
let session_layer = SessionManagerLayer::new(store)
    .with_secure(true)
    .with_same_site(SameSite::Lax)
    .with_expiry(Expiry::OnInactivity(Duration::hours(8)));

let app = Router::new()
    .route("/login", post(login))
    .layer(session_layer)
    .layer(CsrfLayer::new());
```

- **Pros:** revocation is a `DELETE`; no token in JavaScript, so XSS cannot steal
  a session; `tower-sessions-sqlx-store` reuses the existing pool; pairs
  naturally with `axum-login` and CSRF middleware.
- **Costs:** a database read per request (cacheable, but a real cost); CSRF
  protection is mandatory for cookie auth; horizontal scaling needs a shared
  store (which is the database you already have).
- **Choose if** you control the login form and need immediate revocation — the
  normal case for internal government tools.

**B. Stateless JWT**

```rust
let claims = Claims { sub: actor.0, exp: OffsetDateTime::now_utc() + Duration::minutes(15) };
let token = jsonwebtoken::encode(&Header::new(Algorithm::EdDSA), &claims, &keys.encoding)?;
// middleware: verify signature + exp on every request, no lookup
let Claims { sub, .. } = jsonwebtoken::decode(&token, &keys.decoding, &validation)?.claims;
```

- **Pros:** no session store; trivially scalable; usable by non-browser clients.
- **Costs:** revocation requires a denylist (which is a session store with extra
  steps); key rotation and `alg` confusion are classic footguns; token in
  `localStorage` is XSS-readable; short expiry plus refresh tokens is more moving
  parts than sessions.
- **Choose if** multiple services must validate tokens without a shared database.

**C. Delegated OIDC only (Singpass/CorpPass/Entra ID)**

```rust
let provider = openidconnect::core::CoreProviderMetadata::discover_async(
    IssuerUrl::new(config.issuer.clone())?,
    async_http_client,
)
.await?;
```

- **Pros:** no password storage, MFA and account lifecycle belong to the
  identity provider; the right answer when government SSO is mandated.
- **Costs:** redirect-flow complexity, callback URL registration per environment,
  provider-specific claims mapping, and local development needs a stub provider.
- **Choose if** the deployment mandates an external identity provider. Compose it
  with A: OIDC for identity, server session for state.

**Recommendation:** A, with C layered on when SSO is mandated. Never B for a
browser app.

### DR-07 · Error wire shape

**Question.** What does an error response look like?

**A. RFC 9457 `application/problem+json`**

```json
{ "type": "https://example.gov.sg/problems/not-found",
  "title": "Resource not found", "status": 404,
  "detail": "No request with that id is available to you.",
  "instance": "/api/requests/0192f3c4-…" }
```

- **Pros:** a standard clients and gateways already understand; `type` is a
  stable machine code; extensions (`errors[]` for field validation) are legal;
  one `IntoResponse` impl for the whole app.
- **Costs:** slightly more verbose than a bare `{ error }`; teams sometimes
  over-model `type` URIs as a public API commitment.
- **Choose if** the API is consumed by more than your own frontend.

**B. Simple envelope `{ "error": { "code", "message" } }`**

- **Pros:** trivially small; obvious to every frontend dev.
- **Costs:** bespoke, undocumented, and drifts per handler; no standard field
  validation shape; gateways and generated clients cannot infer it.
- **Choose if** the API is private, tiny, and will stay that way.

**C. Bare status codes**

```http
HTTP/1.1 404 Not Found
Content-Length: 0
```

- **Pros:** nothing to maintain.
- **Costs:** the client cannot show a specific message; tests assert only status,
  so a wrong-but-200 bug looks fine.
- **Choose if** never.

**Recommendation:** A.

### DR-08 · Background work

**Question.** How do deferred jobs run?

**A. Transactional outbox + in-process worker**

```sql
CREATE TABLE jobs (
    id           uuid PRIMARY KEY,
    kind         text NOT NULL,
    payload      jsonb NOT NULL,
    run_after    timestamptz NOT NULL DEFAULT now(),
    attempts     int NOT NULL DEFAULT 0,
    -- A lease, not a boolean: a worker that dies mid-job must not wedge it.
    locked_until timestamptz
);
```

```rust
let job = sqlx::query_as!(
    Job,
    r#"UPDATE jobs SET locked_until = now() + interval '5 minutes',
                      attempts = attempts + 1
        WHERE id = (SELECT id FROM jobs
                     WHERE run_after <= now()
                       AND (locked_until IS NULL OR locked_until < now())
                     ORDER BY run_after
                     FOR UPDATE SKIP LOCKED LIMIT 1)
        RETURNING *"#,
).fetch_optional(&pool).await?;
```

- **Pros:** the enqueue commits atomically with the business write — no lost
  jobs, no dual-write; `SKIP LOCKED` gives safe concurrency; one fewer service;
  the queue is inspectable with SQL.
- **Costs:** you own retry/backoff and a poison-job policy; a worker thread shares
  the app's lifecycle (fine until you need independent scaling).
- **Choose if** jobs are "after this write, do that" and volume is moderate.

**B. `apalis` (Redis or Postgres backend)**

- **Pros:** a real job framework — retries, scheduling, middleware, multiple
  backends, a dashboard in the paid tier; less code you own.
- **Costs:** a second infrastructure dependency (Redis) or a framework-specific
  Postgres schema; another upgrade surface; task semantics live in a library.
- **Choose if** you need cron, priorities, and dashboards on day one.

**C. No background work yet**

- **Pros:** nothing to build.
- **Costs:** the first slow operation (email, PDF, export) ends up in a request
  handler, and moving it later is a refactor across handlers.
- **Choose if** genuinely nothing is deferred — and record that you checked.

**Recommendation:** A. It is ~150 lines and it makes the first async job a
non-event.

### DR-09 · Runtime image

**Question.** What is the runtime base image?

**A. `gcr.io/distroless/cc-debian12:nonroot`**

```dockerfile
FROM gcr.io/distroless/cc-debian12:nonroot@sha256:…
COPY --from=builder /app/target/release/server /app/server
USER 65532:65532
```

- **Pros:** no shell, no package manager, minimal CVE surface; glibc, so the
  normal `x86_64-unknown-linux-gnu` build works; numeric `USER 65532` satisfies
  `runAsNonRoot`; digest-pinnable.
- **Costs:** no shell means debugging is `docker cp`/`kubectl debug`; healthcheck
  must be a binary subcommand; no `ca-certificates` unless copied.
- **Choose if** security posture and image size dominate.

**B. `debian:bookworm-slim`**

```dockerfile
FROM debian:bookworm-slim@sha256:…
RUN useradd --uid 10001 --create-home app
COPY --from=builder /app/target/release/server /app/server
USER 10001:10001
```

- **Pros:** a shell for debugging, `apt` for last-minute needs, familiar to ops.
- **Costs:** larger attack surface and image; needs explicit `useradd` and
  cleanup; more CVEs to triage in Nexus IQ and Trivy.
- **Choose if** operational debuggability outranks minimalism.

**C. `alpine` (musl)**

```dockerfile
# build target: x86_64-unknown-linux-musl
FROM alpine:3.22@sha256:…
COPY --from=builder /app/target/x86_64-unknown-linux-musl/release/server /app/server
USER 65532:65532
```

- **Pros:** smallest base; static-ish binaries.
- **Costs:** musl changes allocator behaviour and DNS resolution; some crates
  with C dependencies need `musl-dev` and a slower build; you must remember
  `rustup target add x86_64-unknown-linux-musl` and often `mimalloc` to recover
  allocation performance.
- **Choose if** you already build musl and have measured it.

**Recommendation:** A.

### DR-10 · Dev orchestration

**Question.** What is the one command a new contributor runs?

**A. `just`**

```just
verify: fmt lint test deny
fmt:
    cargo fmt --all --check
test:
    cargo nextest run --workspace
```

- **Pros:** `just --list` self-documents; no tab/`$@` archaeology; recipes are
  real shell so `cargo` knowledge transfers; one file.
- **Costs:** one more tool to install (`cargo install just` or a package);
  no dependency graph beyond ordering.
- **Choose if** you want the smallest thing that works.

**B. `cargo xtask`**

```rust
fn main() -> anyhow::Result<()> {
    match std::env::args().nth(1).as_deref() {
        Some("verify") => verify()?,
        _ => anyhow::bail!("usage: cargo xtask verify"),
    }
    Ok(())
}
```

- **Pros:** the automation is Rust — typed, testable, no shell portability
  caveats; `cargo xtask` is already a `cargo` invocation.
- **Costs:** compile step before any task; more ceremony for a `docker compose`
  wrapper; contributors must read Rust to fix CI glue.
- **Choose if** the automation has real logic (codegen, schema diffs, release).

**C. `make`**

- **Pros:** installed everywhere; familiar to ops and older CI images.
- **Costs:** tabs, `.PHONY`, and shell-escaping papercuts; no `--list` without
  hacks; recipes drift into unreadable one-liners.
- **Choose if** the organisation already standardises on Makefiles.

**Recommendation:** A, with a thin `cargo xtask` only for the schema-parity and
release logic that genuinely benefits from being Rust.

---

## 13. The strictness profile (Rust's answer to `tsconfig` `strictest`)

TypeScript has a `strictest` preset because its type system is opt-in. Rust's is
not: most of what that preset buys is the language itself. What remains is a
**compiler-and-lint policy**, and unlike a `tsconfig` it cannot be one file —
it is four, and they only work if every crate opts in.

| `tsconfig` `strictest` flag | Rust mechanism | Status |
| --- | --- | --- |
| `strict`, `noImplicitAny`, `strictNullChecks`, `useUnknownInCatchVariables` | no implicit dynamic type; `Option<T>` instead of `null`; `Result<T, E>` instead of a thrown `unknown` | **always on** |
| `noImplicitReturns`, `noFallthroughCasesInSwitch` | `if`/`match` are expressions; control flow cannot fall through | **always on** |
| `noImplicitOverride` | no inheritance to override | **n/a** |
| `noPropertyAccessFromIndexSignature` | map access is `HashMap::get` → `Option<&V>` | **always on** |
| `noUnusedLocals`, `noUnusedParameters` | `unused_variables`, `dead_code` + `-D warnings` | CI flag |
| **`noUncheckedIndexedAccess`** | `v[i]` still panics; strict form is `v.get(i)`, enforced by `clippy::indexing_slicing` | **profile** |
| **`exactOptionalPropertyTypes`** | `Option<T>` conflates "absent" and "null" on the wire; PATCH bodies need `Option<Option<T>>` + `serde_with::double_option` | **profile + convention** |
| (no analogue) | `unsafe_code = "forbid"`, `cargo-geiger`, `cargo-semver-checks`, `#[non_exhaustive]` | **extra** |

The honest summary: **Rust gives you `strict` for free and makes you configure
`strictest`.** The profile below is the closest defensible equivalent.

### 13.1 The four files

```toml
# rust-toolchain.toml — the compiler is part of the policy
[toolchain]
channel = "1.99.0"
components = ["rustfmt", "clippy"]
profile = "minimal"
```

```toml
# Cargo.toml (workspace root)
[workspace.lints.rust]
unsafe_code                   = "forbid"
missing_docs                  = "deny"      # scope note below
unreachable_pub               = "deny"
missing_debug_implementations = "warn"
elided_lifetimes_in_paths     = "warn"
trivial_casts                 = "warn"
unused_qualifications         = "warn"
unsafe_op_in_unsafe_fn        = "deny"

[workspace.lints.clippy]
all      = { level = "deny", priority = -1 }   # default-correctness lints are non-negotiable
pedantic = { level = "warn", priority = -1 }   # noisy on purpose; see §13.3
unwrap_used     = "deny"      # the panic family, as a class
expect_used     = "deny"
panic           = "deny"
indexing_slicing = "deny"     # the noUncheckedIndexedAccess analogue
as_conversions   = "deny"     # use TryFrom / From; `as` silently truncates
arithmetic_side_effects = "warn"   # integer overflow in money and counts
allow_attributes_without_reason = "deny"
undocumented_unsafe_blocks      = "deny"
missing_errors_doc              = "warn"
must_use_candidate              = "warn"
print_stdout                    = "deny"
print_stderr                    = "deny"
dbg_macro                       = "deny"
todo                            = "deny"
await_holding_lock              = "deny"
```

```toml
# clippy.toml — thresholds and the "no-restricted-imports" analogue
too-many-arguments-threshold = 3
too-many-lines-threshold = 50
excessive-nesting-threshold = 3
allow-unwrap-in-tests = true          # unit tests may unwrap; request paths may not
allow-expect-in-tests = true
allow-panic-in-tests  = true

disallowed-types = [
  { path = "chrono::Local",          reason = "every timestamp is UTC" },
  { path = "serde_json::Value",      reason = "dynamic JSON lives only in src/wire/adapters.rs" },
  { path = "rand::rngs::ThreadRng",  reason = "take an injected Rng so tests can seed it (§3)" },
]
disallowed-methods = [
  { path = "std::env::var",             reason = "config comes through figment, not ambient env (§9)" },
  { path = "std::time::SystemTime::now", reason = "inject a Clock (§2.4)" },
  { path = "std::process::exit",        reason = "return a Result from main; exit paths skip telemetry flush" },
]
```

```toml
# rustfmt.toml — stable options only; nightly-only options are not worth a toolchain pin
edition = "2024"
max_width = 100
use_field_init_shorthand = true
newline_style = "Unix"
```

`missing_docs` is enforced where the docs are a contract — the domain crate and
anything another crate imports — and relaxed with a reasoned `#[expect]` in a
binary's `main.rs`. A `//!` line on the crate is not documentation of a public
API, and `unreachable_pub` is what keeps the surface honest.

**Every crate must opt in**, or the workspace table silently does nothing:

```toml
# crates/<any>/Cargo.toml
[lints]
workspace = true
```

Add a `#[test]` that walks `crates/*/Cargo.toml` and asserts the stanza exists —
"we set the lints" and "the lints ran" are different claims, and only one of them
is checkable.

### 13.2 What each severity means

`deny` in the manifest is for rules that are **always** wrong here (a panic in a
request path, `as` truncation, an unreasoned `#[allow]`). `warn` is for rules
that are usually right and sometimes not (pedantic style, `arithmetic_side_effects`
in a loop counter). CI then runs `cargo clippy -- -D warnings`, which promotes
every `warn` to an error **in CI only** — locally the `warn` stays advisory so a
developer is not blocked by a style opinion while iterating.

That split is the whole trick: the manifest states intent, CI states enforcement.

### 13.3 Four traps

- **`clippy::restriction` is not a group to enable.** The Clippy documentation is
  explicit that it is a pick-list of mutually contradictory lints; enabling it
  wholesale is a self-inflicted outage. Opt into individual restriction lints,
  exactly as the profile does.
- **`pedantic` will produce noise on day one.** That is the design: enable it,
  then `#[expect(clippy::module_name_repetitions, reason = "domain vocabulary")]`
  the handful the team rejects. The `allow_attributes_without_reason` deny makes
  each suppression cost a sentence, which is the point.
- **`nursery` churns.** Its lints change between releases, so a toolchain bump
  becomes an unrelated red build. Leave it off; revisit per release if curious.
- **`unused_crate_dependencies` lies under `--all-targets`.** A crate used only
  by tests or benches reports as unused. Keep it out of the blanket profile and
  run `cargo machete` (§8.2) instead, which understands dev-dependencies.

### 13.4 What the profile cannot do

A clean `clippy -D warnings` means *the code is defensible*, not *the system is
correct*. It cannot catch a missing authorization check, a wrong `WHERE`
predicate, or a lost update. Those are the jobs of §2 (real-DB IDOR tests) and
§15 (types that make the state illegal). Never let a green lint run stand in for
a test suite — that is the §8.1 ladder mistake in a new costume.

---

## 14. API and idiom rules (the parts reviewers actually cite)

§7 governs the *shape* of functions. This section governs their **signatures and
types** — the decisions that leak into every call site and are expensive to
change later. The authority is the Rust API Guidelines `C-` checklist and
Google's Rust Style Guide, not personal taste.

### 14.1 Ownership at the boundary

The rule is mechanical: **choose the parameter by what the function does with the
value**, not by what the caller happens to hold.

| The function… | Parameter | Returns |
| --- | --- | --- |
| reads text | `&str` | `String` |
| reads a sequence | `&[T]` | `Vec<T>` / `Box<[T]>` |
| reads a path | `&Path` | `PathBuf` |
| stores the value | `String`, `Vec<T>`, `T` | — |
| usually borrows, sometimes owns | `&str` | `Cow<'_, str>` |
| produces a lazy sequence | — | `impl Iterator<Item = T> + '_` |
| accepts any implementation | `impl Trait` | — |
| heterogeneous, cold path | `&dyn Trait` / `Box<dyn Trait>` | — |

Four corollaries that are violated constantly:

- **Never take `&String`, `&Vec<T>`, or `&Box<T>`.** Take the borrowed form
  (`&str`, `&[T]`, `&T`): it removes a deref layer and accepts more callers. The
  exception is a signature that must name the owned type for API compatibility.
- **A getter returns a borrow, not a clone:** `fn name(&self) -> &str`, never
  `fn get_name(&self) -> String`. No `get_` prefix (`C-GETTER`).
- **`impl Into<String>` is for constructors that store; `&str` is for internals.**
  Every generic parameter is a monomorphized copy of the body, so behind a large
  public generic function, forward immediately to a private monomorphic one:

```rust
pub fn new(name: impl Into<String>) -> Self { Self::from_owned(name.into()) }
fn from_owned(name: String) -> Self { /* the real body, compiled once */ }
```

- **`&impl AsRef<str>` is a trap**: without `?Sized` it cannot accept `&str` at
  all. Prefer `impl AsRef<str>` by value, or take `&str` and let the caller
  decide. If a signature needs `#[allow(clippy::needless_pass_by_value)]` to feel
  right, it is the wrong signature.

### 14.2 Naming conversions by cost (`C-CONV`)

| Prefix | Cost | Direction |
| --- | --- | --- |
| `as_` | free | borrowed → borrowed |
| `to_` | expensive | borrowed → borrowed or owned (allocates) |
| `into_` | variable | owned → owned |

So `as_str()` is a borrow, `to_string()` allocates, `into_inner()` consumes. A
method named `as_*` that allocates is a bug in the name, and reviewers should say
so. Iterators are `iter`, `iter_mut`, `into_iter` (`C-ITER`) — never `items()`.

### 14.3 Type shape

- **Public fields are a commitment** (`C-STRUCT-PRIVATE`): they pin the
  representation and forbid invariants. Only passive data bags (a row struct, a
  config struct) get public fields, and those get `#[non_exhaustive]` if they are
  part of a public API.
- **`#[non_exhaustive]` on every public enum and growing struct that crosses a
  crate boundary** — otherwise adding a variant is a breaking change for every
  downstream match. Inside one crate it does nothing useful; across crates it is
  the difference between a minor and a major version.
- **`#[must_use]` on constructors, builder setters, pure transforms, and guard
  types** — anything whose ignored return value is a bug. `Result` already
  carries it.
- **Seal traits you do not want implemented downstream** (`C-SEALED`): a private
  empty supertrait plus a doc line saying "sealed". An extension trait is named
  `…Ext` and blanket-implemented over the upstream trait.
- **Do not implement `Deref` for a newtype.** It re-exposes every method of the
  inner type and dissolves the boundary the newtype exists to enforce
  (`C-NEWTYPE-HIDE`). `Deref` is for smart pointers.
- **Exhaustive `match` on enums you own**; a catch-all arm is legal only for
  `#[non_exhaustive]` or foreign enums, where it is mandatory.
- **`Option<Option<T>>` is the correct PATCH type** for "field omitted" versus
  "field set to null". It looks wrong for a week and then earns its keep.

### 14.4 Conversions

- Implement `From`, never `Into` — the blanket impl supplies `Into`
  (`C-CONV-TRAITS`).
- Fallible conversion is `TryFrom` with a typed error, never `as`, never `unwrap`.
- `..Default::default()` in struct literals is how fields get added without
  touching every call site — which is also why public structs need
  `#[non_exhaustive]`.

### 14.5 The required derive set

Reviewers should not have to ask; a type without these is incomplete.

| Kind of type | Derives | Notes |
| --- | --- | --- |
| value object / newtype | `Debug, Clone, PartialEq, Eq, Hash` | `Copy` only if ≤ 2 words and semantics allow |
| domain entity | `Debug, Clone` | identity compares by id, not by field equality |
| wire read model | `Debug, Serialize, ToSchema` | `Deserialize` only if it is also an input |
| wire write model | `Debug, Deserialize, ToSchema` | `#[serde(deny_unknown_fields)]`; validate on construct |
| error enum | `Debug, thiserror::Error` | `Display` comes from `#[error(...)]`; never derive `Clone` reflexively |
| config | `Debug, Deserialize` | never `Serialize` — a config dump leaks secrets |
| secret | none of the above | `secrecy::SecretString`; a hand-written `Debug` that prints `[redacted]` |

`Debug` must never be empty (`C-DEBUG-NONEMPTY`), and `Debug` is for developers
while `Display` is for users — do not print a `Debug` repr into a problem
document.

### 14.6 Docs are part of the contract

`missing_docs` is denied, so the remaining question is *which* sections exist:

- `# Errors` on every `Result`-returning public function (`missing_errors_doc`),
  naming the variants a caller must handle — not "returns an error".
- `# Panics` whenever a panic is reachable, including `expect` on an invariant.
- `# Safety` on every `unsafe fn`. Given `forbid(unsafe_code)` there should be
  none in our crates; one that exists needs an addendum naming why, plus a
  `SAFETY:` comment on the block.
- An example in the crate-level docs that `cargo test --doc` compiles. A doc
  example that does not compile is a lie with a green checkmark next to it.

### 14.7 Review checklist

1. Is any primitive carrying domain meaning? Wrap it (§15.2).
2. Does any public signature take `&String`, `&Vec<T>`, or a `&Box<T>`? Borrowed
   form instead.
3. Is a getter cloning, or prefixed `get_`? Fix it.
4. Does a name promise a cost it does not have (`as_` that allocates)?
5. Does a public struct have public fields without `#[non_exhaustive]`?
6. Is a newtype implementing `Deref`? Remove it.
7. Is a `match` on an owned enum using `_ =>`? Make it exhaustive.
8. Does a `Result` function lack `# Errors`? Add it.

---

## 15. Design patterns that earn their keep

Rust's pattern literature is thin and partly stale, so this section is
deliberately a **short allow-list plus a longer deny-list**. A pattern is here
because it removes a class of bug or a class of test; everything else is
speculative generality (§7.6).

The evidence for the two load-bearing entries is an experience report
(ACM, 2026) on functional state machines: **typestate measurably improves
faultlessness and testability but costs boilerplate and can hurt readability**,
and **newtype + "parse, don't validate" improves quality at low cost**. That is
exactly the trade this section encodes: newtypes everywhere, typestate sparingly.

### 15.1 Parse, don't validate

Validation checks a weak type and returns `bool`; parsing consumes the weak type
and returns a **strong one that cannot be wrong**. Do it once, at the boundary.

```rust
#[derive(Debug, Clone, PartialEq, Eq, Hash)]
pub struct Email(String); // private field: unforgeable outside this module

impl Email {
    pub fn parse(raw: &str) -> Result<Self, EmailError> {
        let trimmed = raw.trim();
        if trimmed.len() > 254 || !trimmed.contains('@') {
            return Err(EmailError::Malformed);
        }
        Ok(Self(trimmed.to_ascii_lowercase()))
    }

    pub fn as_str(&self) -> &str { &self.0 } // borrow, never Deref
}
```

- The domain core then takes `Email`, never `String`, and contains **zero**
  `is_valid_email` checks. If a rule is in the type, delete every `if` that
  re-checks it downstream.
- A `parse` that allocates only on `Ok` is the goal; a borrowed `EmailRef<'a>` for
  hot read paths is the optimisation, and only after measuring (§17).
- Serde is a second boundary: `#[serde(try_from = "String")]` on the newtype
  routes deserialization through `parse`, so there is exactly one validation
  implementation.

### 15.2 Newtype

Zero-cost, and the cheapest fix for the oldest bug in the book:

```rust
pub struct RequestId(Uuid);
pub struct ActorId(Uuid);

// fn approve(request: RequestId, actor: ActorId) — swapping the arguments
// is now a compile error rather than a production incident.
```

Rules: private field, `new`/`parse` constructor, `as_str`/`as_uuid` accessor,
`#[serde(transparent)]` on the wire, `sqlx::Type`/`AsExpression` for the driver,
and **no `Deref`**. Implement `Display` deliberately where a user-facing string is
genuinely needed.

### 15.3 Typestate, for sequences only

Use it when an operation is legal in one state and a bug there is expensive; not
as a default.

```rust
pub struct Draft;
pub struct Submitted;

pub struct Request<State> {
    id: RequestId,
    title: String,
    state: PhantomData<State>,
}

impl Request<Draft> {
    pub fn submit(self) -> Result<Request<Submitted>, TransitionError<Self>> {
        if self.title.trim().is_empty() {
            return Err(TransitionError::Empty(self)); // gives the draft back
        }
        Ok(Request { id: self.id, title: self.title, state: PhantomData })
    }
}

impl Request<Submitted> {
    pub fn approve(&self, actor: &ActorId) -> Result<(), ApprovalError> { /* … */ }
}
// Request<Draft> has no approve(); the illegal call does not compile.
```

- **Transitions consume `self`**, so a stale handle cannot be reused.
- **Fallible transitions return the original state in the error**
  (`TransitionError<Self>`), so the caller can retry without re-fetching.
- **Seal the state trait** if one exists, so downstream code cannot invent states.
- **Do not use typestate when** states are dynamic (read from the database),
  the graph is large or data-driven, or states must share one collection. Use an
  enum and branch at runtime; that is what enums are for.
- **Do not typestate a builder** for a struct with two optional fields. The
  boilerplate-to-bug-caught ratio is bad, and the same evidence report says so.

### 15.4 Enum with data, not `kind` plus optional fields

If a struct has `kind: Kind` and two `Option` fields that are only meaningful for
one kind, it is an enum that has not been written yet:

```rust
// No: four representable states, two of them nonsense.
struct Payment { kind: Kind, card: Option<Card>, iban: Option<Iban> }

// Yes: every state is constructible only when it is meaningful.
enum Payment {
    Card(Card),
    Transfer { iban: Iban },
}
```

- `match` on the enum is exhaustive, so adding a variant breaks every handler at
  compile time — the cheapest possible feature checklist.
- On the wire, `#[serde(tag = "kind", rename_all = "snake_case")]` keeps the JSON
  shape a client expects while the Rust side stays total.

### 15.5 Builder with validation

Parameter objects are mandatory past three parameters (§7.1); a builder is the
form they take when construction is fallible or has cross-field rules.

```rust
pub struct SearchQuery {
    term: String,
    limit: u32,
    cursor: Option<Cursor>,
}

impl SearchQuery {
    pub fn builder(term: impl Into<String>) -> SearchQueryBuilder { /* … */ }
}

impl SearchQueryBuilder {
    pub fn limit(mut self, limit: u32) -> Self { self.limit = Some(limit); self }
    pub fn build(self) -> Result<SearchQuery, QueryError> { /* cross-field rules here */ }
}
```

`build()` returns `Result`, not `Self`, whenever a rule can fail. Typestate
builders (one type per required field) are reserved for structs with three or
more *required* fields — where forgetting one is otherwise a runtime error.

### 15.6 Sealed and extension traits

```rust
mod private { pub trait Sealed {} }

/// Sealed: implemented only inside this crate.
pub trait RequestState: private::Sealed { fn label(&self) -> &'static str; }

/// Extension trait: adds a verb to a foreign type.
pub trait RequestExt {
    fn is_overdue(&self, clock: &Clock) -> bool;
}
impl RequestExt for Request<Submitted> { /* … */ }
```

- **Seal** when the trait is a closed set (states, capabilities) and a downstream
  impl would be a bug.
- **Extension trait** when a verb belongs conceptually to a type you do not own
  (`axum::extract::Request`, `sqlx::PgRow`). Naming: `…Ext`, blanket impl over
  the upstream trait.

### 15.7 RAII guard

Anything that must be undone — a transaction, a span, an advisory lock, a
concurrency permit — is a guard whose `Drop` does it. This is the only reliable
way to make cleanup survive every early `return` and `?`.

```rust
/// Records latency and decrements the in-flight gauge on every exit path,
/// including `?` and a cancelled future. No I/O, so `Drop` can do it.
struct InFlight { started: Instant, gauge: Gauge }

impl Drop for InFlight {
    fn drop(&mut self) {
        self.gauge.dec();
        metrics::histogram!("request.duration").record(self.started.elapsed());
    }
}
```

Guard rules: `Drop` never fails, never blocks, and never panics
(`C-DTOR-FAIL`, `C-DTOR-BLOCK`). Anything that needs I/O to clean up — releasing
a remote lock, marking a job failed — cannot live in `Drop`, because `Drop`
cannot await; give the guard an explicit `close(self) -> Result<(), E>` and make
the caller's happy path call it. Note that `sqlx::Transaction` already rolls back
on drop, so a hand-written transaction guard is usually redundant.

### 15.8 Functional core, imperative shell

The domain logic is a pure function over plain data; the handler is a thin shell
that parses input, calls the core, and writes the result. This is what makes
§2's tests fast and honest: the core needs no database, and the shell is thin
enough that the integration test is really testing SQL and wiring.

```rust
// core: no I/O, no clock, no Result<_, sqlx::Error>
pub fn approval_decision(r: &Request, actor: &Actor, now: OffsetDateTime) -> Decision { /* … */ }

// shell: parse → decide → persist → respond
pub async fn approve(/* … */) -> Result<Json<RequestSummary>, ApiError> { /* … */ }
```

If a domain function takes `&PgPool`, it is not domain logic; it is a repository
function wearing a domain name.

### 15.9 Choosing the dispatch mechanism

| Need | Mechanism | Cost |
| --- | --- | --- |
| one implementation, known at compile time | concrete type / `impl Trait` | zero |
| two or three implementations, chosen at boot | `enum` + `match` | no vtable, exhaustive |
| open set, plugin-style, chosen at runtime | `Box<dyn Trait>` | one indirection; must be object-safe |
| generic over a caller-supplied type | `<T: Trait>` | monomorphized code size |

Prefer concrete → generic → enum → `dyn` (`M-DI-HIERARCHY`, §7.3). A
`Box<dyn Trait>` with exactly one implementation is an abstraction with a bill
and no benefit.

### 15.10 Patterns we decline

| Pattern | Why not, here |
| --- | --- |
| Repository trait per entity | One implementation, and §2 forbids mocking it — pure ceremony |
| `*Manager` / `*Service` / `*Factory` object | Collects unrelated behaviour; names nothing (§7.1) |
| Global singleton / `static mut` | Untestable, and Rust makes the alternative easy |
| Inheritance-shaped trait hierarchies | Composition plus enums covers it without diamond problems |
| `Box<dyn Error>` in domain code | Erases the variants the caller must handle (§7.2) |
| `anyhow` in a library crate | Same reason; `anyhow` is for `main` and tests only |
| Visitor for a closed AST | `match` on an enum is shorter and exhaustive |
| Macro-first DSL | Debuggability collapses; macros are for boilerplate, not architecture |
| `Deref`-based "inheritance" | Re-exposes the inner API and breaks the invariant (§14.3) |
| Actor for every component | Supervision and message ordering you now own; use it for I/O ownership only (§16) |

---

## 16. Async correctness and observability

Async Rust fails in ways that compile cleanly: a lock held across an await, a
future dropped mid-send, a task that outlives its owner, a log line with no trace
id. Every rule below exists because the compiler cannot see the bug.

### 16.1 Runtime rules

- **One runtime per process**, created by `#[tokio::main]` or an explicit
  `Builder`. Do not nest runtimes, and do not call `block_on` inside a task.
- **Never block a worker.** CPU-bound work, `argon2`, filesystem I/O, and any
  synchronous driver go to `spawn_blocking` (§7.3). A 300 ms hash on a worker
  stalls every future scheduled on that thread.
- **Every outbound call has a timeout** (`tokio::time::timeout`), and every pool
  has a timeout. A call without one is an unbounded wait you have not measured.
- **Retries only for idempotent operations**, with jitter and a cap; a retry
  around a non-idempotent `POST` is a duplicate-write generator (§6.1 covers
  idempotency keys).
- **Do not `spawn` what you can `await`.** A detached task with no owner is a
  task whose failure nobody sees.

### 16.2 Structured concurrency

Own task lifetimes. Two mechanisms, in order of preference:

```rust
// One root token from the shutdown signal; one child per component.
let root = CancellationToken::new();

// JoinSet: a group of related tasks; dropping the set aborts them.
let mut set = JoinSet::new();
for shard in shards {
    set.spawn(run_shard(shard, root.child_token()));
}
while let Some(res) = set.join_next().await {
    match res {
        Ok(Ok(())) => {}
        Ok(Err(e)) => { tracing::error!(error = %e, "shard failed"); root.cancel(); }
        Err(join) if join.is_panic() => { tracing::error!("shard panicked"); root.cancel(); }
        Err(_) => {} // cancelled by the root; expected during shutdown
    }
}
```

- **Cancellation propagates parent → child only.** A failing child does not
  cancel the root; the supervisor observes it via `join_next()` and calls
  `root.cancel()` itself. Write that supervisor down; it is the failure policy.
- **`JoinSet` aborts its tasks when dropped**, which is why it is the default for
  request-scoped fan-out. `TaskTracker` (tokio-util) is the variant for
  long-lived background services you drain explicitly.
- **Every long-lived `await` must be cancel-aware.** `CancellationToken` does not
  wake a task parked in `rx.recv().await`; either race it in `select!` or rely on
  sender drop, and drop senders during shutdown.

### 16.3 Cancellation safety in `select!`

When one branch of `select!` completes, **the other futures are dropped at their
current poll point**. If that future had already consumed something, the
something is gone.

| Operation | Cancel-safe? | Consequence if cancelled |
| --- | --- | --- |
| `mpsc::Receiver::recv` | yes | message stays queued |
| `mpsc::Sender::send` | **no** | message may be lost |
| `Receiver::recv_many` with non-empty buffer | **no** | partial batch lost |
| `tokio::time::sleep` | yes | nothing |
| `AsyncReadExt::read` | yes (per docs) | bytes not consumed |
| `JoinSet::join_next` | yes | nothing removed from the set |

```rust
// Wrong: the send is recreated each iteration, so cancelling it loses `msg`.
loop {
    let msg = tokio::select! {
        msg = rx.recv() => match msg { Some(m) => m, None => break },
        _ = token.cancelled() => break,
    };
    tx.send(msg).await?;   // if this future is dropped, the message is gone
}

// Right: create each future once, pin it, and resume it across polls.
loop {
    let send = tx.send(next_message().await);
    tokio::pin!(send);
    tokio::select! {
        biased;
        _ = token.cancelled() => break,
        res = &mut send => res?,
    }
}
```

- **If a future is not cancel-safe, create it once outside the loop and `select!`
  over `&mut future`.** Resuming is safe; recreating is not.
- **`biased;` is for shutdown, not for fairness.** Put the shutdown branch first
  so a completed signal wins over more work; without `biased`, `select!` picks
  randomly when both are ready. For fairness among peers, random is what you
  want — do not add `biased` reflexively.
- **A cancel-unsafe operation in a request path is a data-loss bug**, not a
  performance detail. The classic case is `handle(req).await` inside a
  connection future: client disconnects, future drops mid-write, half the work is
  committed. Spawn the work so it runs to completion, or make it a transaction.

### 16.4 Backpressure is a bounded channel

An unbounded channel is a memory leak with extra steps. Every queue between a
producer and a consumer is **bounded**, and the bound is chosen from measured
memory per message, not from optimism.

```rust
let (tx, mut rx) = mpsc::channel::<WriteCmd>(64); // bound = backpressure
```

- Producers wait when the queue is full; that is the point. If waiting is
  unacceptable, the correct response is load shedding (`try_send` → `429`), not
  an unbounded buffer.
- For pipelines, take a permit before reading the next item (`reserve()`), so the
  "consume then await" window where cancellation loses data does not exist.
- Concurrency limits are `Semaphore`s, not "spawn and hope". Cap per-dependency
  concurrency so one slow upstream cannot exhaust the pool.

### 16.5 Locks

- **Never hold a lock guard across `.await`** (`clippy::await_holding_lock`). Use
  `tokio::sync::Mutex` only when the guard genuinely must live across an await;
  otherwise `std::sync::Mutex` is faster and the compiler stops you.
- **Prefer message passing to shared state.** A channel with one owner removes
  the lock, the poisoning question, and the ordering question at once.
- **Never take `std::mem::take` on a locked `Option` and then await** — a
  cancellation between the take and the restore leaves the field `None` forever.
  This is the async-mutex data-loss pattern; hold the value in a local and
  restore in a `Drop` guard.

### 16.6 Graceful shutdown

```rust
async fn shutdown_signal(root: CancellationToken) {
    if tokio::signal::ctrl_c().await.is_err() {
        tracing::warn!("ctrl-c handler unavailable; shutdown will be abrupt");
    }
    tracing::info!("shutdown requested");
    root.cancel();
}

axum::serve(listener, app.into_make_service_with_connect_info::<SocketAddr>())
    .with_graceful_shutdown(shutdown_signal(root.clone()))
    .await?;

// then, in order: stop accepting → drain handlers → flush telemetry → close pool
telemetry::shutdown().await;
pool.close().await;
```

Order matters: telemetry flushes **after** the last request and **before** the
process exits, or the traces for the shutdown itself are lost — which is exactly
the incident you will want to read. Give the drain a deadline, then abort what
remains; an unbounded drain is a deploy that hangs.

### 16.7 Instrumentation: spans, not printf

`tracing` is the API; `println!` is denied by the profile (§13) precisely so this
rule cannot be skipped.

```rust
#[tracing::instrument(
    skip(pool, body),
    fields(request_id = %id, actor_id = %actor.0, rows = tracing::field::Empty),
)]
pub async fn submit(pool: &PgPool, actor: Actor, id: RequestId, body: SubmitBody)
    -> Result<RequestSummary, ApiError>
{
    let affected = /* … */;
    tracing::Span::current().record("rows", affected); // must be declared above
    Ok(/* … */)
}
```

- **Structured fields, never string concatenation.** `tracing::info!(%id, "submitted")`
  is queryable; `format!("submitted {}", id)` is a grep.
- **Span fields must be declared up front.** `span.record()` on an undeclared
  name is silently dropped — that is what `field::Empty` is for.
- **`#[instrument(skip(...))]` on anything taking secrets, bodies, or pools.** A
  span that captures `Authorization` is a credential leak into your log store.
  `tower-http`'s `TraceLayer` does not record headers by default; keep it that way.
- **Spawned tasks do not inherit the caller's span.** Attach it:
  `tokio::spawn(work().instrument(tracing::Span::current()))`, or the task's logs
  land in an orphan trace.
- **JSON in production, pretty in development**, chosen by one env var. Log
  levels: `info` in production (raise temporarily, never permanently).

### 16.8 OpenTelemetry wiring

`tracing` is the instrumentation API; OpenTelemetry is the export format. Do not
hand-write `tracer.in_span` calls — install `tracing-opentelemetry` as a
subscriber layer and keep writing `#[instrument]`.

- **Batch exporter in production, never the simple one.** `with_batch_exporter`
  ships off the hot path on a background thread; `with_simple_exporter` blocks on
  every span end and exists for tests.
- **Sampling is parent-based** (`ParentBased(TraceIdRatioBased(0.1))`), so a
  trace kept upstream stays complete downstream instead of fragmenting.
- **Resource attributes are the ones you will filter by**:
  `service.name`, `service.version`, `deployment.environment`. Set them from the
  environment, not from a hardcoded string that silently overrides
  `OTEL_SERVICE_NAME`.
- **Shut down every provider** (tracer, meter, logger) before `main` returns.
- **Instrument boundaries, not internals**: HTTP handler, DB call, outbound HTTP,
  job execution. A span per helper function is noise that costs real money.
- **Rust status, October 2026**: metrics and logs APIs/SDKs are stable; traces
  remain beta, so pin the version and expect minor-version churn.
- **Export through a Collector** where one exists; the SDK should not know your
  vendor's endpoint, and sampling/routing then changes without a rebuild.

### 16.9 Metrics: RED, and no cardinality bombs

Start with three metrics per endpoint — **R**ate, **E**rrors, **D**uration —
plus saturation signals you actually page on. Resist instrumenting everything up
front; add a metric when a question cannot be answered by the existing ones.

| Allowed label | Forbidden label |
| --- | --- |
| route template (`/api/requests/{id}`) | the raw path with an id in it |
| method, status class | user id, request id, email, tenant name |
| job kind, queue name | free-text error message |

Every distinct label combination is a time series. The fastest way to turn a
10-line dashboard into a metrics-server outage is `path = request.uri().path()`;
always use the matched route template instead.

### 16.10 PII and secrets in telemetry

- Never log tokens, cookies, passwords, or full request bodies. `secrecy` makes
  the value unprintable, but that only helps where the type is used — review every
  `instrument` attribute and every `{:?}` on a request struct.
- Truncate anything user-authored before it enters a span, and prefer ids to
  content.
- Error responses and log lines have different audiences (§6.3): the problem
  document gets a stable type and a user sentence; the span gets the diagnosis.
- Redact at the Collector as a second line of defence (`filter` processor), not
  as the only one.

### 16.11 Health endpoints

Two endpoints, two meanings — conflating them is how a slow database restarts
every pod:

| Endpoint | Checks | Used by |
| --- | --- | --- |
| `/healthz` (liveness) | the process is running and the runtime is not wedged | orchestrator restart policy, §10.1 `HEALTHCHECK` |
| `/readyz` (readiness) | dependencies reachable, with a short cached result | load balancer / ingress |

A liveness probe that queries Postgres means a database blip kills every replica
at once. Keep liveness dependency-free, and make readiness cheap enough to be
called every few seconds.

### 16.12 Async review checklist

1. Does any `async fn` block, hash, or do sync I/O? Move it to `spawn_blocking`.
2. Is any `spawn` unowned? Use `JoinSet` or a `TaskTracker`.
3. Is a non-cancel-safe future recreated inside a `select!` loop?
4. Is any channel unbounded?
5. Is a lock guard held across an `.await`?
6. Does every outbound call have a timeout?
7. Is there a supervisor that turns a child failure into a root cancellation?
8. Does shutdown flush telemetry **before** exit?
9. Does every spawned task carry the caller's span?
10. Does any span attribute contain a secret, a body, or a high-cardinality id?

---

## 17. Performance and adversarial testing

Rust's reputation for speed is not a licence to optimise by intuition. The
default answer to "should we optimise this?" is **measure, and the bottleneck is
probably Postgres**.

### 17.1 Measure first

- **Profile before changing.** `samply` (sampling profiler, Firefox Profiler UI)
  or `cargo flamegraph` for CPU; `dhat`/`heaptrack` for allocation; `tokio-console`
  for task stalls and queue depth. A guess about a hot path is wrong often enough
  that guessing is the expensive option.
- **Benchmark the thing you will change.** `criterion` for statistical rigour,
  `divan` for a lighter harness. Benchmarks live in `benches/`, run on a fixed
  machine or not at all, and compare against a stored baseline.
- **Never micro-benchmark in the abstract.** A `Vec` versus `SmallVec` result on
  synthetic data says nothing about a handler whose cost is a 4 ms query.

### 17.2 The release profile

```toml
[profile.release]
opt-level = 3
lto = "thin"          # ~most of fat LTO's gain, far less compile time
codegen-units = 1     # cross-module inlining; slows the build, not the binary
panic = "unwind"      # see below — abort is faster but kills CatchPanicLayer
strip = "symbols"
debug = "line-tables-only"   # keep enough to symbolise a production backtrace
overflow-checks = true       # cheap insurance for money and counts (measure the cost)

[profile.dist]        # the tagged-release build, if you need the last few %
inherits = "release"
lto = "fat"
```

- **`panic = "abort"` is not free.** It removes unwinding, shrinks the binary, and
  makes `CatchPanicLayer` impossible — so a panic in one handler becomes a dead
  process instead of a 500. For a server that must stay up, keep `unwind`; for a
  CLI, `abort` is the right default. Decide it, write it in the addendum, and do
  not let it drift between the profile and §7.2.
- **Expected effects, measured, not promised:** LTO is typically ~5–20% and
  ~10–20% binary size; `codegen-units = 1` ~5–10%; PGO another ~5–15% on hot
  services and is worth it only for a tagged release build (it needs a training
  workload in CI, which is a real maintenance cost).
- **`debug = "line-tables-only"` is the compromise** between a 100 MB binary with
  full DWARF and a backtrace that is a list of addresses.

### 17.3 The allocator

```rust
#[global_allocator]
static GLOBAL: mimalloc::MiMalloc = mimalloc::MiMalloc;
```

Two lines, and for allocation-heavy services the largest single win available —
mimalloc is the usual choice in 2026 (v3 shipped January 2026). Measure before
and after; for an I/O-bound CRUD service the curve is usually flat, and adding a
C dependency for nothing is a supply-chain cost (§8.2).

### 17.4 What usually matters more than any of this

In order: **the query plan and indexes**, the number of round trips (N+1), the
payload size, connection-pool sizing, then the runtime. A Rust service doing five
sequential 2 ms queries is slower than the same service doing one 3 ms query, and
no compiler flag changes that. Profile the database before the binary.

### 17.5 Adversarial testing: pick the tool for the bug class

| Command | Finds | Run | Cost |
| --- | --- | --- | --- |
| `cargo test` with `proptest` | invariant violations over generated inputs (§2.4) | every PR | seconds |
| `cargo +nightly fuzz run` | panics, hangs, and memory errors in **untrusted parsers** | nightly | hours; corpus committed |
| `cargo +nightly miri test` | UB in `unsafe` code: aliasing, OOB, uninit reads, data races | every PR touching `unsafe` | 10–100× slower; nightly-only |
| `cargo test` with `loom` | interleaving bugs in **lock-free** code and custom sync primitives | nightly | very slow; scope to the module |
| `cargo mutants` | tests that assert nothing (surviving mutants) | nightly, scoped to changed files | CPU-hungry: a build per mutant |
| `cargo semver-checks` | accidental breaking changes in a published crate | on release | fast |
| `cargo hack --feature-powerset check` | code that only compiles with all features on | nightly | slow |
| `cargo msrv verify` | the declared `rust-version` is a lie | on release | slow |

Rules that keep these honest:

- **Fuzz the parsers, not the handlers.** Any function that consumes untrusted
  bytes — webhook payloads, CSV import, file upload, a custom wire format — gets
  a fuzz target and a committed corpus. Fuzzing found real bugs in `serde`,
  `regex`, and `image`; it will find yours.
- **Miri is not a test runner.** It cannot interpret FFI or most syscalls, and it
  proves nothing about code it did not execute. Run it on the crate that contains
  `unsafe`; a clean Miri run plus a review is the bar, not a proof of soundness.
- **Loom is for atomics you wrote.** `Mutex` and `RwLock` are already tested;
  hand-rolled lock-free structures and `Arc`-swap tricks are not.
- **Mutation testing scores the tests, not the code.** A surviving mutant in an
  authorization check is a finding; a surviving mutant in a `Display` impl is
  noise. Scope it to `src/requests/`, `src/auth/`, and money — the places where a
  wrong assertion is an incident.
- **`cargo-semver-checks` matters only if you publish a crate.** For a binary,
  the wire contract (§6.1) is the API that needs protecting, not the Rust surface.
- **Coverage stays a diagnostic** (§2.4). A line executed by a test that asserts
  nothing is worse than an uncovered line, because it looks covered.

### 17.6 What goes in CI, and when

| Gate | Every PR | Nightly | Release tag |
| --- | --- | --- | --- |
| `cargo bench` vs baseline | — | ✓ (noise-tolerant threshold) | ✓ |
| `cargo miri test` | ✓ on `unsafe` crates | ✓ full | — |
| `cargo fuzz run` | — | ✓ (time-boxed) | — |
| `cargo mutants` | — | ✓ scoped | — |
| `cargo semver-checks` | — | — | ✓ (published crates) |
| `cargo hack --feature-powerset` | — | ✓ | ✓ |
| container smoke test (§10.1) | ✓ | — | ✓ |

A performance gate without a noise budget is a flaky test that teaches the team
to re-run CI. Compare medians over several runs, allow a threshold (e.g. 5%),
and fail only on a regression that exceeds it twice in a row.

---

## 18. Architecture in Rust

The router's §5 fixes the cross-language decisions: boundary before
distribution, executable dependency rules, one owner per table, pattern per
module, abstraction needs a second implementation. This section is the Rust
mechanism for each — and Rust gets one of them for free that Node does not.

### 18.1 The compiler is the boundary

**Crates form an acyclic dependency graph, and only `pub` items cross a crate
boundary.** That is not a convention to be remembered; it is a build error
waiting to happen. Put each layer in its own crate and the dependency rule stops
being a diagram:

```toml
# crates/api/Cargo.toml — api may depend on domain; domain cannot depend on api
[dependencies]
domain = { path = "../domain" }
axum = { workspace = true }
```

```toml
# crates/domain/Cargo.toml — no axum, no sqlx, no tokio
[dependencies]
serde = { workspace = true }
time = { workspace = true }
```

`crates/domain` cannot import the HTTP layer, because the HTTP layer is not in
its dependency list. There is no lint to configure, no CI job to forget, and no
review comment that can be overruled at 23:00 before a release.

Three consequences worth stating, because they are the whole reason this works:

- **Modules inside a crate may be cyclic.** `mod a` can use `mod b` which uses
  `mod a`, so an intra-crate module boundary is social, reinforced only by
  visibility and `cargo modules dependencies --acyclic` (§7.4). If a boundary
  matters, make it a crate.
- **Visibility is checked, not advisory.** `pub(crate)`, `pub(super)`, and
  `pub(in crate::requests)` are enforced by the compiler, so a module's surface
  can be smaller than the crate's.
- **The cost is `pub` surface.** Anything shared across a crate boundary must be
  public, which is a permanent API commitment (`C-STRUCT-PRIVATE`, §14.3). If
  splitting a crate forces you to make internals public, the split is drawing the
  line in the wrong place.

### 18.2 When a crate split pays, and when it is vanity

Crate boundaries buy enforcement and incremental compilation; they cost
boilerplate, `pub` exposure, and some cross-crate inlining. The 2026 guidance is
consistent and worth quoting against your own instincts: *do not split a project
into many crates just because it looks architectural* — boundaries are worth it
when they enforce meaningful separation, and a good target is roughly **4–6
layered crates, not dozens**.

| Split when | Do not split when |
| --- | --- |
| the dependency direction must be enforced, not agreed | the reason is "layers look tidy" |
| a module is released, deployed, or consumed by another binary | it is one binary and one team |
| the domain must stay free of `tokio`/`axum`/`sqlx` | the crate would only re-export another crate |
| compile time is dominated by one huge compilation unit | the split forces `pub` on internals |
| a proc-macro or build script needs its own crate | you are under ~10k lines total |

The re-export crate is the tell: if `crates/http` contains nothing but
`pub use api::*`, it is a folder with a `Cargo.toml`.

### 18.3 The port: trait, enum, or nothing

Rust gives three ways to express the same architectural seam, and choosing the
wrong one is the language's signature architecture mistake.

```rust
// A. Trait object: open set, chosen at runtime (a plugin, a vendor SDK)
pub trait EventSink: Send + Sync {
    fn publish(&self, event: &DomainEvent) -> Result<(), SinkError>;
}

// B. Enum: closed set, known at compile time — exhaustive, no vtable
pub enum Notification {
    Email(EmailNotification),
    Sms(SmsNotification),
}

// C. Concrete type: one implementation, no seam at all
pub struct RequestService { db: PgPool, clock: Clock }
```

| Mechanism | Choose when | Cost |
| --- | --- | --- |
| concrete type | one implementation, no second adapter on the horizon | none — and this is the right answer most of the time |
| `enum` + `match` | the set is closed and you want exhaustive handling | adding a variant touches every match (which is the point) |
| `Box<dyn Trait>` / `&dyn Trait` | the implementation is chosen at runtime, or the set is open | 16-byte pointer, one indirection, and the trait must be dyn-compatible |
| `<T: Trait>` generic | the caller picks the type and it is monomorphized | "generic infection": the parameter spreads to every struct and function that holds it |

Two rules that keep this honest:

- **A trait with one implementation and no second adapter is a prediction, not a
  port** (router §5.5). In Rust it is also a bill: `async fn` in a trait is not
  dyn-compatible, so the moment you want `Box<dyn Port>` you need `#[async_trait]`
  or a hand-rolled boxed future, and the `Send + Sync` bounds become viral
  through every impl and every struct that holds it.
- **Generics belong at the leaf, `dyn` at the boundary.** Prefer `&dyn`/`Box<dyn>`
  at a composition seam so the type parameter does not infect `AppState`;
  monomorphize inside the leaf function where it actually helps. Practice from
  hexagonal-in-Rust write-ups is blunt about the alternative: generic parameters
  on structs are "very infectious" and are usually the reason a Rust port quietly
  costs more than the thing it abstracts.

### 18.4 State: concrete, not a shared god object

```rust
// The composition root owns the graph; handlers take a concrete AppState.
#[derive(Clone)]
pub struct AppState {
    pub db: PgPool,
    pub clock: Clock,
    pub mailer: Arc<dyn Mailer>,   // the one genuinely swappable seam
}

pub async fn submit(
    State(state): State<AppState>,
    Json(body): Json<SubmitRequest>,
) -> Result<Json<RequestSummary>, ApiError> { /* … */ }
```

`Arc<Mutex<HashMap<String, T>>>` as application state is the Rust-flavoured
version of a global variable: every reader contends for one lock, the invariants
live in whichever task holds it last, and the tests cannot run in parallel
without racing. Prefer a typed field per dependency, a channel when something
must be serialized, and a database when the state must survive a restart.

If a dependency genuinely needs runtime swapping, use `Arc<dyn Trait>` for *that
one* field and say why in a comment. An `AppState` where every field is a trait
object is the Node service locator wearing Rust's clothes.

### 18.5 Layered workspace, with the dependency rule in the manifest

```text
crates/
  domain/      # entities, invariants, pure decisions — no I/O, no async runtime
  application/ # use cases: orchestrates domain + ports
  adapters/    # sqlx, http clients, mail, oidc — implements application's ports
  server/      # axum wiring, config, telemetry, main
```

- **Arrows only point inward**: `server → adapters → application → domain`.
  Enforce it with the manifests, not a document.
- **`domain` stays pure.** No `sqlx`, no `tokio`, no `axum`. That is what makes
  §2's unit tests instant and what makes a future typestate (§15.3) possible.
- **`application` owns the ports** (the traits it needs), and `adapters`
  implements them. A port defined in `adapters` and imported by `application`
  inverts the dependency and defeats the whole layout.
- **Only `server` constructs the graph.** One `main.rs`, one place where
  `PgPool`, `Clock`, and concrete adapters are assembled.

Migration is mechanical when the time comes: because `domain` and `application`
already have no infrastructure dependencies, promoting a crate to a service is a
deployment change, not a rewrite (router §5.1).

### 18.6 Rust-specific anti-patterns

| Anti-pattern | Why it bites here | Fix |
| --- | --- | --- |
| **Trait per entity, one impl** | `trait RequestRepository` + `PgRequestRepository` and nothing else: indirection with no second adapter, plus `async_trait` bounds | delete the trait; take the concrete type |
| **Generic parameter on every struct** | goes viral through impls, `Send + Sync` bounds, and compile times | concrete in the struct, generic in the leaf function |
| **`Arc<Mutex<AppState>>`** | one global lock, no parallelism, tests cannot share it | typed fields; channel or DB for real shared state |
| **`pub` everywhere "so crates can see it"** | leaks internals into a permanent API commitment | fix the boundary; move the item, do not widen it |
| **A crate that only re-exports** | a folder with a `Cargo.toml`; adds build time and `pub` surface for nothing | put the items in the crate they belong to |
| **Premature workspace split** | dozens of crates, `pub` sprawl, slower builds from lost inlining | start as modules; split on a §18.2 trigger |
| **`cfg(feature)` as architecture** | `#[cfg]` branches become the module system; every build is a different program | features for optional deps only; separate crates for separate products |
| **Enum dispatch for an open set** | every new adapter edits the core's enum | `Box<dyn>` for open sets, enum for closed ones |
| **Boxing in a hot path "for flexibility"** | one indirection per call in the loop that matters | measure (§17.1); monomorphize the hot path |
| **An interface for the database** | the second impl would be a mock, which §2 forbids | `sqlx` queries in the owning module, no trait |

### 18.7 Review checklist

1. Does the dependency direction appear in `Cargo.toml`, or only in a document?
2. Does `domain` import anything from `adapters`, `axum`, or `sqlx`?
3. Does every trait in `application` have a second, real implementation?
4. Is any struct generic purely to hold an injected dependency?
5. Is application state concrete, or one `Arc<Mutex<_>>` away from a global?
6. Does any crate contain only re-exports?
7. Is `pub` minimal at each crate boundary?
8. Would extracting this crate into a service change a manifest, or a design?

**Sources (checked October 2026).** [Rust at scale: packages, crates, and
modules](https://mmapped.blog/posts/03-rust-packages-crates-modules) for the
module-vs-crate trade (cycles inside a crate, parallelism across crates); the
module-organization guidance for the visibility ladder and "do not split just
because it looks architectural"; [Master hexagonal architecture in
Rust](https://www.howtocodeit.com/guides/master-hexagonal-architecture-in-rust)
and its critique thread for the `Send + Sync` and generic-infection costs; the
Rust API Guidelines (`C-STRUCT-PRIVATE`, `C-SEALED`) for the visibility
commitment a crate boundary creates.

---

## 19. Keeping this template honest

This file is itself a living document, and it decays in specific, predictable
ways. Maintain it the way it asks you to maintain a project:

- **Re-verify the versions and the platform facts quarterly.** The `DR-02` and
  `DR-04` ecosystems move fastest; the SHIP-HATS rules in §10.2 have changed four
  times in 2026 alone (Rekor decommissioning, Nexus IQ's seven-day gate, EOL
  image blocking, PAT-only Git over HTTPS). A date at the top of the file plus a
  calendar reminder beats discovering a stale rule during a release.
- **Never renumber a `DR-` or an addendum.** Teams will have cited them in code
  comments, PRs, and audit responses. If a decision changes, add a new card
  variant or a superseding addendum; do not edit the identifier's meaning.
- **When a default flips, change the sections that assume it in the same commit.**
  §2, §4, §5, §9, and §10 each name an option. A default that changes in §0.7 but
  not in §4 is worse than no default, because the agent will follow whichever it
  reads first.
- **Add a card only when the choice is genuinely open.** Every new question costs
  the user's attention at kickoff. If the answer does not vary by project, it is
  an invariant — put it in a section, not in a card.
- **Keep the examples compiling.** A card whose snippet no longer type-checks
  against the current crate version teaches the wrong lesson. Treat the snippets
  as a doc-test suite: a scratch crate that compiles every Rust example in this
  file is cheap to maintain and catches an ecosystem rename before a user does.
- **Re-verify §13 against the pinned Clippy.** Lints are added, renamed, and
  removed between releases; `unwrap_used` in the wrong group, or a threshold in
  `clippy.toml` that no longer exists, fails the build for a reason that has
  nothing to do with the code. Run `cargo clippy -- -W help` after a toolchain
  bump and diff the lint list.
- **Re-verify the β labels in §16.8.** OpenTelemetry's Rust traces were still
  beta in October 2026 while metrics and logs were stable; a status change
  should update that sentence, not be discovered by a compile error.
- **Do not let §15 grow into a catalogue.** A pattern earns its place only by
  naming a bug class it removes and the condition under which it is wrong. A
  pattern with no deny-condition is a preference, and preferences belong in the
  team's style review, not in a standing instruction that an agent must obey.

If a rule here conflicts with the language you actually chose, you are in the
wrong variant: `GREENFIELD-NODE.md` is the Node.js/TypeScript sibling, and
[`GREENFIELD.md`](GREENFIELD.md) is the router that asks the language question
and explains how to write a new variant.
