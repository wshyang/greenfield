# GREENFIELD-NODE.md — CLAUDE.md template for new Node.js + TypeScript projects

**Standalone.** This is the Node.js/TypeScript variant of the greenfield
template. `GREENFIELD.md` is the language-neutral template it was derived from;
its lessons are folded in here, so nothing in this file depends on reading it,
and no other sibling file is assumed to exist.

This file is a **standing-instructions template** meant to be copied to a new
repository's `CLAUDE.md` (and split into focused section files as the project
grows). It distills the conventions, disciplines, and tooling choices that —
if laid out up front — avoid the avoidable pain we hit when they were learned
the hard way mid-project. It is **deliberately project-agnostic**: no product
name, no feature references, no hardcoded service names. Adjust the concrete
stack placeholders (framework, ORM, test runner) to the actual project; the
Node/TypeScript assumptions — `npm`/`pnpm`, `node:22-alpine` (Node 22 LTS with
native `.ts` type-stripping), TypeScript `strictest`, Fastify 5, Drizzle,
Vitest, Playwright, port 3000 — are already the defaults in each section.

**Versions verified October 2026:** Node.js `22.22+` LTS, TypeScript `5.x`,
Fastify `5.12+`, Drizzle ORM + `drizzle-kit`, Vitest, Playwright,
`@stryker-mutator/core` `10.x` (`@stryker-mutator/typescript-checker`),
`dependency-cruiser`, SHIP-HATS templates `v1.1.12`.

**Contents.** §0 how to use it · §1 decisions, addenda, and two-cut plans · §2
real-DB tests, bite checks, standards checker, and flakes · §3 test
infrastructure and embedded Postgres · §4 database / ORM discipline · §5 schema
evolution (twin migrations vs pre-launch snapshot gate) · §6 code conventions ·
§7 function design, hooks, and returned effects · §8 honest validation, tail
measurement, and closing bug classes · §9 local dev · §10 containers and
SHIP-HATS · §11 day-one checklist · §12 architecture in Node.js and TypeScript ·
§13 keeping this template honest · §14 porting an existing system to Node.js +
TypeScript · §15 egress-restricted sandboxes and pure-Node client/server
bootstrap.

---

## 0. How to use this template

- Copy the whole file as `CLAUDE.md`, **delete any other greenfield template
  files** copied alongside it in the same commit, then **replace every
  `<placeholder>`** with the real stack.
- **Preferred progressive-disclosure unpack (`.claude/` skills + lean `CLAUDE.md` /
  `AGENTS.md`):** to keep full-file prose out of every turn's prompt and below
  Claude Code's 5,000-token compaction cap, copy `.claude/` into the new
  repository and run `/greenfield-bootstrap node` to render a `<= 130`-line
  `CLAUDE.md` from `.claude/skills/greenfield-bootstrap/assets/CLAUDE.lean-template.md`.
  Include its compact two-column `.claude/` dispatch table (mapping tasks to
  Claude Code skills **and** to explicit `.claude/skills/*/SKILL.md`,
  `.claude/rules/*.md`, and `.claude/skills/*/scripts/*.sh` fallback paths for
  non-Claude `AGENTS.md` harnesses), prune unused `go-*.md` / `rust-*.md`
  references + `greenfield-bootstrap/` (and `greenfield-port/` if not porting),
  and maintain **one** root file (`AGENTS.md` + `@AGENTS.md` in `CLAUDE.md`, or
  a symlink — never two diverging copies).
- Splitting each `##` section into its own file (`CLAUDE-testing.md`,
  `CLAUDE-database.md`, …) behind a top-level index is **optional**, not a
  bootstrap step: do it when one file stops being readable in a single pass.
  Until then, one file is simpler to keep honest.
- Keep the "record every decision" and "write tests first" rules in the very
  first sections: they are the two that prevent the most rework.
- Copy the deployment starters from the greenfield repository's
  `initial-templates/` (`Dockerfile`, `Dockerfile.dev`,
  `Dockerfile.cloudflared`), contextualise them to the project, and add the
  SHIP-HATS pipeline inert, with its activation script (§10).

---

## 1. Record every decision, up front, in a living spec (addendum discipline)

**When you start, decide what the "source of truth" is and where decisions
get written.** The single biggest avoidable cost in a long-lived project is a
spec that silently drifts from the implemented system, forcing future readers
to reverse-engineer intent from commits and chat.

- Maintain a **living functional/design specification** (the product contract)
  plus a **sequentially-numbered addenda register** (`docs/decisions/NNNN-*.md`)
  for every decision that isn't dictated by that base spec: filling a gap,
  adding a new object/field/tool, or deviating from the spec.
- Write up each addendum **proactively, in the same change that makes the
  decision** — never as a follow-up. Use YAML front matter so CI can verify
  numbering and supersession, name rejected options explicitly, and write
  `## Impact` as verifiable checkboxes rather than prose bullets:

```markdown
---
id: 0004
decision: spec §4
status: accepted          # accepted | superseded
decided_by: user          # user | agent
date: 2026-10-27
supersedes: null
---

# 0004 — Data access: Drizzle ORM over node-postgres

## Decision
Drizzle ORM with `src/db/schema.ts` as single column-mapping source.

## Why
<the user's stated reason>

## Rejected
- Prisma: <actual reason declined>
- Kysely: <actual reason declined>

## Impact
- [ ] 0004-1 Keep all SQL/queries inside `src/*/queries.ts` — `git grep -n "db\.select\|db\.insert" src/ ':!src/*/queries.ts'` prints 0 lines — done when handlers hold zero ORM calls
- [ ] 0004-2 Enforce single-casing policy (§4) — `node scripts/check-standards.ts` passes rule `STD-002` — done when a fixture mapper file turns CI red
```

- Keep the addenda **independent of the base spec's own section numbering**, so
  the base spec stays stable and addenda append forever (supersede via a new
  numbered file with `supersedes: <id>`, never by editing history).
- `CLAUDE.md` must tell future agents to do this without being asked. It is the
  difference between a codebase you can reason about and a puzzle box.

### 1.1 Plans and designs are written in two cuts

Multi-task design docs, migration plans, and porting specs that stop at prose
cannot be tracked or verified mechanically. Write them in two passes (short
single-choice addenda need only the `2–4` `## Impact` boxes above):

1. **Cut one is the shape**: scope, packages, decisions, and trade-offs in clear
   prose.
2. **Cut two is the work**: under every prose section, a `Verify / do` list of
   checkboxes where each box has a unique id, **one** imperative verb, the exact
   file path, command, query, or count it concerns, and a measurable *done when*:

```markdown
- [ ] ST-V2.3 Move all 14 write transactions into `src/requests/queries.ts` — `git grep -c "\.transaction(" src/` prints `src/requests/queries.ts:14` — done when zero route handlers open transactions directly
```

Rules that keep the second cut honest:

- **Reject boxes naming no path, command, query, or number**, and reject vague
  lead verbs (*ensure*, *consider*, *review*, *improve*, *handle*).
- **Attach a re-check command to every survey count.** Counts copied from an
  audit or agent summary (routes, tables, `Date.now()` sites) frequently drift;
  re-run and keep the command right beside the number.
- **Link every design decision to an implementing task ID and a proving test
  name.** Rehearse boundary claims (*"adding an event touches only X and Y"*) on
  a scratch branch against `tsc --noEmit`.
- **Prove the doc checker can fail.** Run `node scripts/check-plan-docs.ts
  --check` (Node 22 runs `.ts` natively with zero build step — keep repository
  automation in TypeScript, not throwaway Python/AWK scripts) and test it once
  against a fixture that has a prose-only section, a duplicate ID, and a banned
  verb (§2.3). Mark environment-blocked boxes explicitly (`(needs docker)`).

#### 1.1.1 Every task carries its own exit criterion

- **Every leaf build task carries a measurable `done when`** (backticked command
  + expected output, exact count, test name, or path existence/absence; reject
  *"works"*, *"looks fine"*, and *"is correct"*).
- **Credit parent-child tasks once** (put `done when` on the leaf where work
  ends, not duplicated on both parent and child), run every `done when` command
  once before committing it, and count tasks missing exit criteria before
  declaring a plan ready.

## 2. Write tests first, and keep them real (no mocks where it counts)

**Tests are the mechanism that actually catches bugs — decide the discipline
before any feature ships.** The pain avoided: shipping a wrong-field bug or an
authorization hole that a manual review missed, because "the happy path works."

- **Backend:** run automated integration tests against a **real database
  (a separate test DB, never the dev DB)** through the real app entrypoint
  (e.g. Fastify `app.inject()` without opening a listening socket) — **never
  mock the data-access layer**. A mocked-repository test hides exactly the class
  of bug you care about (bad SQL, wrong column names, FK/trigger violations,
  JSONB round-tripping).
- **Every route/endpoint needs BOTH a positive test AND a session-scoping
  negative test**: a real, valid, logged-in session that is the *wrong party*
  for THIS resource (IDOR-style id substitution) must be rejected — **and the
  test must query Postgres afterwards to assert no row changed** (status codes
  alone have let writes slip through). Which status code to expect is a project
  decision recorded once: `404` when callers must not learn the resource exists
  (greenfield default), or `401`/`403` when resource existence is public or
  existing clients already depend on those codes (ports keep legacy codes until
  a separate addendum changes them, §14).
- **Add/update tests in the same change as the route** — never as a follow-up.
- Frontend unit tests may mock the API boundary; e2e tests drive the real UI
  against a real backend with **no mocks**.
- Adopt a security-test matrix (e.g. OWASP Top 10 in `docs/security-matrix.md`)
  for every endpoint, with an explicit applicability assessment per category —
  decide this on day one, not after an audit finds gaps.

### 2.1 What the assertion must look at

A green test that runs broken code certifies the bug:

- **Assert the state that outlives the test**, not only the `app.inject()` JSON
  body or optimistic UI state. Re-read the row from Postgres or fetch it via a
  second `GET` endpoint.
- **Exercise the path users take first** when two routes achieve one outcome,
  assert visual/computed presentation in a real Playwright browser (not a
  handler test), and **write the failing test before the fix** so you watch it
  fail for the expected reason.
- **Type-check every test fixture with `satisfies`, never `as`.** Writing `const
  expected = { ... } as RequestSummary` silences missing or renamed wire fields!
  Always write `const expected = { ... } satisfies RequestSummary` so a contract
  change fails `tsc --noEmit` immediately, and run the whole verification suite
  via one command.

### 2.2 Sabotage every test and watch it fail (the bite check)

A test you have never seen fail is a hypothesis. When a new test goes green,
sabotage each promise it guards — one break at a time — watch it fail, and
revert immediately:

- **Record the watched sabotages in the addendum** for consequential changes
  (*"dropped `isNull(requests.expiresAt)` filter; swapped `ownerId`; omitted
  `reason` on wire — each turned its test red"*).
- **Use `@stryker-mutator/core` (`v10.x`) + `@stryker-mutator/vitest-runner` on
  nightly CI**, scoped strictly to incident-grade modules (authorization,
  billing/money, state machines).
- **Mandatory Vitest/Stryker trap fix (`checkers: ["typescript"]`):** Vitest
  transpiles TypeScript with esbuild/SWC *without* type-checking, so a naive
  Stryker run executes non-compiling mutants as JavaScript and misclassifies
  them as survivors or timeouts! Always enable
  `@stryker-mutator/typescript-checker`. Also pin N+1 / cost promises with a
  Drizzle query-logger counter rather than flaky `performance.now()` timers,
  sabotage each half of `a || b` separately, re-run lone anomalies, and verify
  `git diff --exit-code` after manual sabotages.

### 2.3 Make the suite enforce its own rules

- **Maintain `node scripts/check-standards.ts`** with append-only numbered rule
  IDs (`STD-001`, …) for invariants ESLint and `dependency-cruiser` cannot
  express (no raw SQL `DELETE` outside retention cleanup, every Drizzle table
  present in `db/schema.sql`, no user-facing copy inlined outside copy modules).
- **Prove every rule fails on a fixture.** Ship a violating fixture per rule
  (covering single quotes, double quotes, and multi-line template literals!)
  with a Vitest test asserting `check-standards` flags it, **and** assert target
  directories/files exist so moved paths never pass vacuously.
- **Let completeness matrices enumerate reality.** Walk Fastify's `onRoute`
  registry and iterate union/enum constants so adding a route without its IDOR
  negative test breaks CI automatically.
- **Coverage is a ratchet, not a 100% vanity target.** Commit measured repeatable
  floors in `vitest.config.ts` (`coverage.thresholds`, `autoUpdate: false`);
  raise floors in the PR that earns them, and require a numbered addendum to
  lower one.

### 2.4 Stubs and flakes

- **Test optional/external capabilities when absent**, plus one opt-in flagged
  run against the live dependency read by a human. State every active stub when
  ≥ 2 capabilities are stubbed, and remember that stubbing `fetch` leaves
  WebSocket / SSE streaming transports untouched.
- **Never mask flaky tests with retries.** Set `retries: 0` in both Vitest and
  Playwright (paired with `trace: "retain-on-failure"`, §3). A wait timing out
  on a *stable wrong value* is a missed delivery, not a slow runner. Keep outer
  test timeouts larger than inner `waitFor` polls, assert preconditions when
  several causes can fail one check, and **set timeouts from single-iteration
  measurements** rather than generous 60-second guesses that hide per-item
  re-initialisation bugs.

## 3. Test infrastructure defaults (video, isolation, determinism)

- **Record Playwright video by default**, with a single documented env-var
  off-switch (`E2E_VIDEO=off`), `retries: 0`, and **`trace:
  "retain-on-failure"`** (never `"on-first-retry"` when retries are `0`, or
  failed runs record no trace!).
- **Isolate environments hard** (flakes, stubs, and timeouts are §2.4): a
  separate test DB, per-worker schemas/databases, unique-per-run test
  identifiers (`{label}.{runId}@example.test` minted from one helper), injected
  `Clock`, and no module-global state so suites run safely in parallel.
- Use **realistic, deterministic fixture data** (named people like `alice`,
  `bob`, `mallory`, not `user-123`), with distinct name pools per actor role so
  failures read naturally.
- Decide the **test layout by type** on day one (`backend/`, `frontend/unit`,
  `frontend/e2e`, `fixtures/`) and keep it consistent.
- **Real Postgres via Docker/service container — or `embedded-postgres`, never
  WASM `PGlite` for server concurrency.** Local dev uses `docker compose up -d
  db` and CI uses a Postgres service container (avoid spinning a new
  `testcontainers` container per test file). When an environment has no Docker
  daemon, use the `embedded-postgres` binary wrapper (one real multi-process
  Postgres server per test worker, pinned major version matching prod, pre-cached
  archive path in `.env.test`, isolated data dir/port per worker, falling back to
  a service container via superseding addendum if CI cannot cache the archive).
  **Do not substitute `@electric-sql/pglite` for server integration tests:**
  PGlite runs Postgres in WASM single-user mode (one backend session with an
  internal transaction mutex), so concurrent transactions, deadlocks, session
  advisory locks, and `FOR UPDATE SKIP LOCKED` worker races cannot occur!

## 4. Database / ORM discipline (the two-source-of-truth trap)

**The single costliest architectural smell in this project was carrying the
same field in two spellings** (snake_case at the DB, camelCase in TypeScript)
and building hand-written mappers to translate between them. Lay out the
policy up front:

- **One casing, one mapper, by the ORM — never hand-written mappers.** If you
  use an ORM with a property→column mapping (e.g. Drizzle), the ORM is the
  *only* translation you write. Pick one casing for the TypeScript domain
  (camelCase) and let the ORM map to snake_case DB columns. **Do not add a
  second, redundant mapper layer** — it is a two-sources-of-truth trap that
  every field must keep in agreement by hand.
- **Every new table/data-access object uses the ORM** — no hand-written raw
  SQL for CRUD. Keep the schema definitions, the data-access layer, and the
  typed domain objects in sync in the same change.
- **Soft deletion, not hard `DELETE`.** Give every relationship/entity that
  can be "removed" a nullable `expires_at`/`deleted_at` from day one, a
  partial unique index (`WHERE expires_at IS NULL`), an `invalidate` (not
  `delete`) repo method, and active-row filtering on every read and every
  authorization check. Retroactively adding soft-delete + re-checking every
  "is it still active" gate is high-effort and bug-prone.
- **Timestamp-ordered IDs** (e.g. UUIDv7, not v4) for index locality on
  high-insert tables — decide the ID scheme on day one and mint IDs in exactly
  one place.
- **System/non-human actors are real rows**, never sentinel string constants —
  so every `actor_id` is a genuine FK. Decide this before any `'system'`/`'unknown'`
  literal leaks in.
- **Foreign-key validity at write time must consider soft-deleted rows**: a
  column that references another row must reject both nonexistent AND
  invalidated targets (enforced via a Postgres `BEFORE INSERT OR UPDATE`
  liveness trigger raising `23503`, because a plain DB FK only proves the row
  once existed).

## 5. Schema evolution (twin migrations vs pre-launch snapshot gate)

Choose **one** schema mode in an addendum before creating the first table:
**Option B** while no database holds data worth keeping; **Option A** the day
any staging, demo, or production database holds data that must upgrade in place.

### 5.1 Option A: wholesale snapshot + numbered migrations (once data is persistent)

- **Two always-in-sync halves, landed in the same commit:**
  (1) a wholesale, self-contained schema/seed snapshot (`db/schema.sql`,
  exported from `src/db/schema.ts` via `drizzle-kit export --sql` plus triggers/views)
  that a brand-new DB applies from zero;
  (2) a sequentially-numbered forward-only migration file (`migrations/0007_*.sql`,
  idempotent where re-runnable) that an already-provisioned DB applies to catch up.
- **Every schema change = `src/db/schema.ts` + `db/schema.sql` + migration file
  in the same commit**, verified by a `pg_dump --schema-only` parity check in CI.
- Apply pending migrations automatically on boot under a Postgres session
  advisory lock, provide a standalone `migrate` CLI command, and use 4-step
  expand/contract sequences for column renames or drops.

### 5.2 Option B: single Drizzle-exported snapshot + version gate (nothing deployed yet)

Use this before any environment holds data worth preserving, avoiding early
migration-history churn **without** opening a two-source-of-truth gap with
Drizzle:

- **`src/db/schema.ts` generates `db/schema.sql`** (`drizzle-kit export --sql` +
  trigger DDL, diff-checked in CI) — never hand-maintain `db/schema.sql`
  independently of `schema.ts`, and **never** run interactive `drizzle-kit push`
  silently at app startup.
- **Stamp `schema_state(version, sha256)` under a Postgres advisory lock, and
  refuse mismatches.** On an empty DB, apply `db/schema.sql` and write the
  stamp; when the stamp matches `SCHEMA_VERSION` + `sha256`, verify expected
  tables exist (supporting DDL-restricted runtime roles cleanly); when an
  existing DB carries an older version or hash, **exit non-zero immediately
  naming `npm run db:reset`** rather than running new queries against an old
  table shape.
- **Make Option B un-erodable:** test boot-twice idempotency and older-stamp
  refusal; fail `check-standards` (§2.3) if a `migrations/` folder appears; and
  write down the exit trigger in the addendum (when triggered, `db/schema.sql`
  becomes `migrations/0001_initial.sql` under Option A).

## 6. Code conventions that prevent whole classes of bugs

- **`data-testid` on every interactive element** at authoring time, with a
  documented naming convention (`{component-kebab}__{element-role}`). Repeated
  rows share one testid; scope by anchor text first. This makes testids a
  stable contract the unit and e2e suites rely on — gaps defeat the point.
- **Stable, typed wire contracts** between backend and frontend — define the
  response shapes once (shared Zod/TypeBox schema or generated OpenAPI types,
  diff-checked in CI) and type both sides from them, with a single error
  envelope (RFC 9457 `application/problem+json` recommended) and
  `Idempotency-Key` support on retryable `POST`s.
- **One definition for any rule shared by the server and a browser/Service
  Worker.** Because both sides are TypeScript, do not copy-paste or codegen TS
  from TS: place shared immutable-asset path rules, upload bounds, allowed
  alphabets, and validation copy keys in a **zero-I/O workspace package
  (`packages/shared-rules`)** imported by both Fastify and the Service Worker,
  guarded by `dependency-cruiser` forbidding any `node:*` or DB import (§12.3).
- **Don't show internal design decisions to end users.** Keep rationale and
  "why this is done this way" notes in code comments and docs, never in
  user-facing labels or descriptions. Scrub internal slugs / design references
  from shipped copy.
- **Keep user-facing copy user-facing, internals internal** — and keep third-
  party/external contract keys isolated at the adapter boundary exactly as the
  external system requires, even when they don't match your internal camelCase.

## 7. Function design and module structure (decide on day one)

Establish these rules before the first line of application code ships; retrofitting
them into an existing codebase is expensive.

### Function size and extraction
- **≤ 20 lines** target per function body; **50 lines hard limit**.
- If you need a comment to explain a block, extract the block as a named function.
- A function does one thing at one level of abstraction — no orchestration code
  mixed with implementation detail inside the same function.

### Guard clauses over nesting
- Exit early with guard clauses at the top; never nest `if/if` for the happy path.
- Maximum nesting depth: **3 levels**. Beyond 3, extract to a function.

### Parameter discipline
- **≤ 3 parameters**. Beyond 3, introduce a Parameter Object (typed interface).
- No boolean/flag parameters — split into two named functions.
- Preserve Whole Object: pass the domain object, not extracted fields.

### Naming
- Names reveal intent. Rename liberally as understanding evolves.
- Booleans: `is`, `has`, `should`, `can` prefix.
- Functions: verb + noun (`getUser`, `validateEmail`).
- No abbreviations in domain code.

### Encapsulation and mutation
- **Never mutate in place** — always produce a new object (`{ ...old, field: value }`).
- Separate Query from Modifier: a function either returns a value OR has a side
  effect, never both.
- Encapsulate Variable: mutable state lives behind a function boundary, not exposed
  as raw mutable fields.

### Frontend: a component renders, a hook decides

Decide this before the first component ships — retrofitting it across a
codebase costs weeks (we spent 22 extractions getting there).

- **Split along the server boundary, not the "looks like state" boundary.**
  The component owns layout/JSX, view-only state, event *wiring*, and DOM-only
  side effects. The hook owns anything calling the API layer, any computation
  over server data, any validation, and any fetching effect.
- **The hook returns a plain object; the component destructures it.** No JSX in
  the hook, and no API import in the component — that import is the checkable
  signal: `grep -c "lib/api" <Component>.tsx` must be `0`.
- **Hooks live beside their tests** (`lib/hooks/use<Feature>.ts` +
  `use<Feature>.test.ts` using `renderHook`) and must not import from
  `components/`.
- **Move bodies, don't rewrite them.** A separation refactor has to be
  verifiable by diffing the extracted function against the original with
  whitespace normalised. Anything not byte-identical is a behaviour change
  wearing a refactor's clothes.

**And keep the JSX interior presentation-only.** This is the half that gets
missed, because a component can satisfy every rule above and still compute
domain rules per render — and most static gates never look inside the `return`.

- Between `return (` and its closing `)`: only markup, bindings already computed
  above the return, and wiring.
- No `.filter()` / `.reduce()` / `.sort()` / `.find()` / `.some()` / `.every()`
  in JSX. A bare `.map()` that renders a list is fine.
- **Compute a derivation once.** `{xs.filter(p).length === 0 ? <Empty/> :
  xs.filter(p).map(…)}` runs the predicate twice and reads as two rules that
  happen to agree.
- Inline handlers are wiring only — a setter, a navigation, a `.focus()`. The
  moment one needs a branch or a computation, name it above the return.
- No inline `new Date()` / `.toFixed()` / `JSON.parse` — use a formatter helper.

A derivation inside JSX cannot be unit-tested without rendering; computed twice
it can drift; and a cascade rule buried in an `onChange` is domain logic no test
can reach.

### Module and directory structure
- **Group by domain feature, not by type** (`routes-requests/`, `db/entities/`,
  not `controllers/`, `models/`, `services/`).
- Files ≤ 400 LOC typical; **800 LOC hard limit**. Files above 800 must be split
  before merge.
- When a file must be split, use the **barrel pattern**: extract per-domain files,
  replace the original with `export * from './sub/index.tsx'` — zero call-site churn.
- No circular dependencies between peer-domain files.
- One concern per file; file names are the contract.

### Code smell → remedy (quick reference)

| Smell | Remedy |
|---|---|
| Long Function (> 50 lines) | Extract Function |
| Deep Nesting (> 3 levels) | Guard Clauses |
| Long Parameter List (> 3) | Introduce Parameter Object |
| Boolean parameter | Remove Flag Argument |
| Feature Envy | Move Function |
| Message Chain | Hide Delegate |
| God Module (> 800 lines) | Per-domain split + barrel |
| Mutable Data | Encapsulate Variable, Separate Query from Modifier |
| Duplicated Code | Extract Function |
| Logic inside JSX (`filter`/`reduce` in the `return`) | Extract to a named binding above the return, or into the hook |
| Same derivation computed twice in one expression | Introduce Explaining Variable |
| Fat inline `onChange`/`onClick` carrying a branch or a computation | Extract Function (or move to the hook if it touches server data) |
| Speculative Generality | Remove (YAGNI) |

Source: Martin Fowler's *Refactoring* (2nd ed.) via
[5-minutes-or-less-refactoring](https://github.com/mikaelvesavuori/5-minutes-or-less-refactoring).
For full details, see `CLAUDE-function-design.md` in project repos that carry this template.

### Effects as a returned value (write-then-publish)

When a SQL transaction commits and must notify SSE subscribers, invalidate an
in-memory cache, or emit a post-commit notification, **do not fire-and-forget
inside the query module, and do not return a plain `{ scan, effects }` object
whose `effects` field a handler can forget to destructure**:

```ts
// packages/kernel/src/effects.ts — zero-I/O post-commit effect vocabulary
export type DomainEvent =
  | { readonly kind: "scan.completed"; readonly scanId: string; readonly tenantId: string }
  | { readonly kind: "cache.invalidate"; readonly tag: string };

export interface EffectPublisher {
  publishAll(events: readonly DomainEvent[]): Promise<void>;
}

/**
 * Wraps a committed domain value together with post-commit effects.
 * `#value` and `#effects` are ECMAScript private fields: callers CANNOT read
 * the domain value without explicitly calling `.publish(bus)` or `.discard(why)`.
 */
export class MustPublish<T> {
  readonly #value: T;
  readonly #effects: readonly DomainEvent[];

  private constructor(value: T, effects: readonly DomainEvent[]) {
    this.#value = value;
    this.#effects = effects;
  }

  static of<T>(value: T, effects: readonly DomainEvent[]): MustPublish<T> {
    return new MustPublish(value, effects);
  }

  async publish(bus: EffectPublisher): Promise<T> {
    await bus.publishAll(this.#effects);
    return this.#value;
  }

  discard(_reason: string): T {
    return this.#value;
  }
}
```

- **When to use `MustPublish<T>` vs a transactional SQL outbox:** use
  `MustPublish<T>` for best-effort post-commit in-process notifications (SSE
  fan-out, cache-tag invalidation). When delivery must survive a process crash
  between `COMMIT` and `publish()` (webhooks, emails, billing), insert into a
  Postgres `outbox_events` table **inside the same Drizzle transaction** instead.
- Add `@typescript-eslint/no-floating-promises` (already required) plus a rule
  in `check-standards.ts` forbidding `MustPublish<void>` returns that callers
  ignore without binding.

## 8. Validate early and honestly

- **Static checking layer is not a substitute for real tests.** When the real
  toolchain (compiler, test runner, DB) is unavailable in a sandbox, run
  per-file syntax checks, execute pure modules (`node file.ts` on Node 22+), and
  grep structural invariants — but **say exactly which layer you ran** and never
  claim "tests pass."
- The real gate, before merge, is always: full type-check (`tsc -b`), full lint,
  `dependency-cruiser`, `check-standards.ts`, and the full Vitest + Playwright
  suites against a real Postgres DB/browser.
- Append the validation caveat to commits made under constrained tooling so a
  reviewer knows what still must run.

### 8.1 Measure the claim; do not assert it

Any numeric latency, throughput, or memory target in a spec or PR requires a
committed load script (`autocannon` or `k6` in `bench/`) and a repeatable report:

- **Drive the route inside a realistic traffic mix** (concurrent reads, writes,
  SSE connections, and auth checks), not an isolated single-endpoint loop.
- **Report `p50`, `p95`, `p99`, and `max`**, plus **cold-cache / freshly-booted
  first-request latency** (V8 JIT warm-up and cold pool connections hide behind
  warm averages).
- **Measure rewrites and ports on the same machine, dataset, and session**,
  committing the raw JSON summary into the addendum.

### 8.2 Close the class, not the instance

- **Every bug fix triggers a whole-repo sweep for sibling instances** of the
  same pattern (`git grep`, AST query, or `check-standards.ts` rule) — fix them
  together and list the swept paths in the commit/addendum.
- **Turn recurring review catches into a lint or `check-standards` rule** in the
  same PR.
- **Search `docs/decisions/` before deleting "dead" code** — an unreferenced
  type or table column may be an approved Phase 2 seam.

## 9. Reproducible local dev + environment story

- Provide a one-command way to stand up the entire local environment
  (database, backend, frontend, and any test doubles) so a new contributor or
  agent can go from clone to running tests without tribal knowledge.
- Separate secrets from config: committed `.env.example`-style templates,
  uncommitted real `.env` files, and a distinct `.env.test` pointing at the
  test DB — never a shared DB between dev and test.
- Decide and document the toolchain choices up front (package manager, runtime,
  ORM, test runners, CI) and make them **consistent across backend, frontend,
  and tooling** — mixed/retrofit choices are where the friction lives.
- In egress-restricted cloud sandboxes where external binary CDNs and GitHub
  Release redirects (`objects.githubusercontent.com`) are TLS-blocked, lean on
  Node 22.22's built-in TypeScript stripping, `node:sqlite`, `node:test`, and
  the offline Chromium playbook in §15.

## 10. Deployment and CI/CD from day one: sandbox containers + SHIP-HATS (kept inert)

**Decide how the project ships before the first feature, and commit the
deployment files with the first code.** Retrofitting a container contract and a
government CI/CD pipeline onto a finished app surfaces every hidden assumption
at once: a server bound to `localhost`, proxy headers trusted wrongly, unpinned
images, secrets in config, scripts that only run on one shell.

### 10.1 Container files for the sandbox platform (active from day one)

- Start from the initial templates in
  [`wshyang/greenfield/initial-templates/`](https://github.com/wshyang/greenfield/tree/main/initial-templates)
  (`Dockerfile`, `Dockerfile.dev`, `Dockerfile.cloudflared`) and
  **contextualise them**; never copy them blind. The generic `Dockerfile`
  guesses the app type from files on disk (a `dist/` without `dist/index.js` is
  served as a static site), which is wrong for any app with its own server.
  Place the results at the repository root, next to a `.dockerignore`.
- **The contract**: the app listens on **port 3000 on the container's
  interface (`0.0.0.0`)**, never only on `localhost` inside the container. The
  image sets `HOST=0.0.0.0` and `PORT=3000` (or the framework's spelling, e.g.
  `HOSTNAME` for Next.js) and `EXPOSE 3000`, and the app reads them.
- Production image: multi-stage, built from source with the lockfile
  (`npm ci`, `--ignore-scripts` where the tree allows); a runtime stage holding
  only what runs; an unprivileged **numeric** `USER` (platforms enforcing
  `runAsNonRoot` cannot verify a name); base images pinned to an exact version
  and distro release, never `latest`; a `HEALTHCHECK`.
- `.dockerignore` keeps `.env*`, `.git`, `node_modules` and build output out of
  every image, and must not exclude platform-supplied directories such as
  `viper-agent/`.
- `Dockerfile.dev` (cloud development through the platform's VIPER agent):
  keep the agent contract (`COPY viper-agent/`, its entrypoint, `PORT=3000`,
  `VIPER_APP_PORT=3001`), and configure the dev server for a forwarded host
  name behind HTTPS (the dev server's host allowlist, proxy trust).
- `Dockerfile.cloudflared`: pin the release, run with `--no-autoupdate`, take
  `TUNNEL_TOKEN` at runtime only, route the tunnel to the app's service on port
  3000.
- **Behind a proxy, trust it by address, not by hop count.** The platform's
  ingress reaches the container from a private address: believe
  `X-Forwarded-For`/`-Proto` only from loopback, link-local and private ranges.
  "Trust every hop" lets a client choose its own address (rate-limit evasion).
  "Trust nothing" makes every client share the proxy's address (per-client
  limits become global) and hides HTTPS (no `Secure` cookies). Check what your
  framework does with a hop count: Fastify 5.12 silently reads one as "trust
  nobody".
- **Test the contract.** Feed the image's `ENV` through the app's real config
  loader in a unit test; in CI, run the built image as a service and reach it by
  its network alias on port 3000. Lint the Dockerfiles with hadolint.

### 10.2 SHIP-HATS: what the platform requires (research, October 2026)

SHIP-HATS is GovTech's CI/CD platform within the Singapore Government Tech
Stack. These findings come from the public SHIP-HATS documentation; the
platform's GitLab and template sources need TechPass and SEED.

- **Platform.** GitLab Dedicated at `sgts.gitlab-dedicated.com` (Ultimate
  tier). Alongside it: SonarQube (Community and Enterprise), Nexus Repository
  Pro (proxies for npm, PyPI, Maven, Docker Hub, MCR, GHCR and more), Nexus IQ
  (SCA), Fortify on Demand (SAST, DAST), Jira and Confluence. It holds code
  classified up to CONFIDENTIAL (CLOUD-ELIGIBLE) / SENSITIVE-NORMAL.
- **Templates.** `include:` the SHIP-HATS Templates from
  `innersource/sgts/ship-hats/ship-hats-templates`, **pinned to a release tag**
  (v1.1.12 as of September 2026; it is required for signing after the Rekor
  decommissioning on 30 September 2026). `include:` cannot take variables, so
  the ref must be a literal. The hidden jobs are used with `extends`:
  - `.build-and-push-docker-image` (Kaniko);
  - `.copy-docker-image-from-one-remote-registry-to-another`;
  - `.generate-gitlab-attestation`;
  - `.sign-container` and `.verify-container`;
  - `.trivy-scan`, `.nexus-iq-scan`, `.sonarqube-scan`;
  - `.invoke-awscli-commands-with-assumerole` (OIDC, no long-lived keys).
- **E2E templates and their conventions.** The E2E templates (web app, Docker
  single and multi service, Docker image CI) are no longer maintained after
  v1.1.0, but they set the conventions the compliance framework relies on:
  - stage names: `.pre`, `build`, `test`, `static-test`, `sign`,
    `runtime-test`, deploy stages;
  - job names, never to be renamed: `build-job`, and `deploy-prod-manual-job`
    or `deploy-final-job`.
- **Compliance is a Pipeline Execution Policy.** Since March 2026 it comes
  from the WOG Security Policy Project; support for the old compliance
  pipelines ended on 30 June 2026, and GitLab removes them in 20.0. Policy jobs
  run in isolation and **never see the project's YAML variables**. Configure
  them through project or group CI/CD variables: `CF_LEVEL`,
  `SONAR_PROJECTKEY`, `SONAR_TOKEN`, `NEXUS_IQ_APP_ID`,
  `NEXUS_IQ_USERNAME`/`NEXUS_IQ_PASSWORD`, `COSIGN_PASSWORD`, `FOD_PAT`. Without
  tool credentials, the framework falls back to GitLab's native scanners.
- **Compliance levels.** `CF_LEVEL` runs from 1 to 4, default 4:

  | Level | Adds                                                   |
  | ----- | ------------------------------------------------------ |
  | 1     | Static scans (`.pre` and `static-test` stages)         |
  | 2     | DAST and deployment gating                             |
  | 3     | Signing and verification                               |
  | 4     | SLSA L1/L2 provenance and SBOMs                        |

- **Runners.**

  | Runner                    | Tags                                             | Notes                                                                                   |
  | ------------------------- | ------------------------------------------------ | --------------------------------------------------------------------------------------- |
  | CStack                    | none (the default)                               | Kubernetes, non-root UID 65533, 4 vCPU / 8 GB; cannot build images                      |
  | SHIP-HATS Docker runners  | `ship_docker`, `_med`, `_large`, `_arm`           | Root but not privileged: build images with Kaniko, not Docker-in-Docker                 |
  | GitLab-hosted (pilot)     | `linux-small-amd64`, `-medium-`, `-large-`       | Privileged, ephemeral VMs                                                               |

  Jobs cannot exceed two hours.
- **Supply chain.**
  - Pull images and packages through the Nexus proxies
    (`nexus-docker.ship.gov.sg`, `nexus-docker-mcr.ship.gov.sg`,
    `https://nexus.ship.gov.sg/repository/npm-proxy/` and the others).
  - Since 3 June 2026, Nexus IQ **fails components younger than seven days**
    and integrity-rating violations: pin versions and let new releases age a
    week.
  - From 1 November 2026, SHIP-HATS Docker runners **block end-of-life and
    blocklisted images**.
  - Pin scanner images to trusted releases (Trivy ≥ 0.69.3 after the March
    2026 incident).
  - Nexus deletes artefacts after 180 days.
- **Access.**
  - From 16 October 2026, Git over HTTPS needs a personal access token or an
    SSH key; passwords are refused.
  - Tokens expire within 180 days.
  - Only owners manage merge-request approval rules.

### 10.3 The discipline: SHIP-HATS files from day one, kept inert

- **Carry the pipeline from the start, inert.** Each SHIP-HATS file gets a
  `.shiphats` suffix (e.g. `file` becomes `file.shiphats`), so GitHub, GitLab
  and local tooling ignore it until the project moves to SHIP-HATS:
  - `.gitlab-ci.yml.shiphats`;
  - `.gitlab/ci/*.gitlab-ci.yml.shiphats`;
  - `sonar-project.properties.shiphats`;
  - `.gitlab/CODEOWNERS.shiphats`;
  - `.gitlab/merge_request_templates/Default.md.shiphats`.
- **Placeholders, never secrets.** Values that differ per agency or project
  are `@@SHIPHATS_<NAME>@@` placeholders. No secrets, ever: those are masked
  CI/CD variables.
- **A root script `activate-shiphats.sh` turns them active.**
  - It runs locally on any remote environment: plain Bash 3.2+, no other
    tooling.
  - It **prompts for every value it needs**, with validation and defaults;
    `--non-interactive` reads `SHIPHATS_*` variables.
  - It renders every file before writing any, and refuses unknown placeholders
    and existing files (`--force` overwrites).
  - It removes the inert copies (`--keep-inert` keeps them).
  - It prints the GitLab settings that cannot live in files: project CI/CD
    variables, masked credentials, the compliance framework, branch protection
    and code owners.
- **What the pipeline covers.**
  - It mirrors the local gates: typecheck, lint, format, unit and integration
    tests with coverage for SonarQube (lcov), and end-to-end tests with video.
  - It builds the image with Kaniko and smoke-tests the container contract
    (port 3000 on the container's interface).
  - It leaves scans, signing and provenance to the compliance framework, or
    runs GitLab's scanners where the framework is not applied.
  - It promotes images through a manual, compliance-gated job.
- **Keep the inert files in step, in the same change** as the scripts and
  tools they call, e.g. CI image tags matching the installed test runner. Test
  it: activate into a scratch directory in the test suite, then check that
  every stage, `needs` and `extends` resolves, that the output passes the
  formatter, and that versions match. Validate against GitLab's CI schema with
  `check-jsonschema --builtin-schema vendor.gitlab-ci`.

### 10.4 Root scripts run everywhere

Scripts at the repository root (`dev.sh`, `activate-shiphats.sh`) must run on
Bash 3.2, the `/bin/bash` macOS ships:

- no associative arrays, `mapfile` or `${var,,}`;
- possibly-empty arrays expanded as `${a[@]+"${a[@]}"}`, because under `set -u`
  Bash before 4.4 calls an empty `"${a[@]}"` unbound.

Run their tests under a real Bash 3.2, which can be built from Apple's
published source, and add a static guard so Linux CI catches regressions. Lint
them with ShellCheck (`pip install shellcheck-py`).

## 11. What to decide before writing the first feature (checklist)

1. Source-of-truth spec location + addenda numbering (`docs/decisions/NNNN-*.md`
   with checkbox `## Impact`, §1).
2. Test DB isolation (Docker / service container, or `embedded-postgres` real
   binary when Docker is absent — never WASM `PGlite` for server concurrency, §3)
   + "tests-first, real DB, no repo mocks" + recorded negative-authz status
   (`404` vs `401`/`403`) asserting unchanged DB rows (§2).
3. ORM + one-casing policy (no hand-written mappers, §4).
4. Soft-delete + UUIDv7 + real-actor-rows object model (§4).
5. Schema evolution mode (§5): **Option A** (Drizzle-exported snapshot +
   numbered migrations in lockstep) once any DB holds persistent data, or
   **Option B** (single Drizzle-exported `db/schema.sql` + `schema_state` hash
   gate that refuses mismatches, with a written trigger to switch to Option A).
6. `data-testid` convention + typed wire contracts + pure `packages/shared-rules`
   for any rule shared with browser/Service Worker (§6).
7. Test layout by type + Playwright video-on default, `retries: 0`, and
   `trace: "retain-on-failure"` (§2.4, §3).
8. Realistic fixture-name pools + unique-per-run identifiers + injected `Clock` (§3).
9. Static-check fallback discipline + validation caveat + measured tail-latency
   claims and whole-repo bug-class sweeps (§8).
10. One-command local env setup + `.env`/`.env.test` separation (§9).
11. Function design rules: ≤ 50-line functions, guard clauses, ≤ 3 params, no flag args,
    no mutation, Separate Query from Modifier, component-renders / hook-decides
    split, domain-based module grouping, 800-LOC file hard limit, barrel-split
    pattern for god modules (§7).
12. Container contract (port 3000 on `0.0.0.0`, proxies trusted by address) and
    the contextualised `Dockerfile`, `Dockerfile.dev`, `Dockerfile.cloudflared`,
    `.dockerignore` at the repository root, tested (§10.1).
13. SHIP-HATS pipeline files kept inert (`*.shiphats`) with `activate-shiphats.sh`,
    in step with the local gates, tested; root scripts Bash 3.2 compatible (§10.2–§10.4).
14. Assertion, bite-check, and standards-ratchet discipline: persisted-row
    assertions, `satisfies` typed fixtures (never `as`), watched sabotages +
    scoped Stryker with `@stryker-mutator/typescript-checker`, `check-standards.ts`
    proven to fail on fixtures, and Vitest coverage thresholds as a ratchet (§2.1–§2.4).
15. Post-commit effects returned as `MustPublish<T>` (`#private` fields) for
    in-process SSE/cache notifications, and transactional SQL outbox rows when
    crash-durable delivery is required (§7).
16. Package dependency DAG enforced by `dependency-cruiser` (tested against a
    violating fixture) with a zero-I/O `packages/kernel` leaf for shared IDs and
    event types (§12).
17. Two-cut multi-task design/plan docs with `Verify / do` checkboxes, leaf
    `done when` exit criteria, and `node scripts/check-plan-docs.ts --check` (§1.1).
18. *(Porting an existing system only)* Live legacy server kept runnable as
    oracle, mechanical 3-bucket test ledger, exported golden fixtures, Node/JS
    determinism audit, divergence log, and twin-DB shadow harness proven to
    catch planted mutations (§14).

Answer these eighteen up front and a greenfield (or ported) project avoids most
of the rework, silent drift, and "we should have written that down" moments this
template exists to prevent.

## 12. Architecture in Node.js and TypeScript

Five architecture rules hold in any language:

1. **Boundary before distribution** — build a modular monolith first; extract a
   service only on measured ~10× resource divergence, team release blocking,
   compliance isolation, runtime mismatch, or established ownership, moving
   tables into an owned schema before moving code.
2. **Executable dependency rules** — a boundary not enforced by CI does not exist.
3. **One write owner per table** — cross-module reads go through exported query
   functions or a deliberate read model, never ad-hoc cross-module mutations.
4. **A pattern per module, not per codebase** — give complex core domains pure
   domain functions + ports; keep boring CRUD modules thin (handler + Drizzle
   query + real-DB test) without *sinkhole* service layers.
5. **An abstraction needs a second real implementation** — an `interface` with
   one implementation (plus a banned mock) is dead ceremony.

This section is the Node.js mechanism for each — starting with one uncomfortable
fact that changes how much you get for free.

**Establish `packages/kernel` and test the dependency graph on day one.** Before
creating domain modules, place **only** cross-domain shared vocabulary — branded
entity IDs (`RequestId`, `ActorId`), `Clock`, `MustPublish<T>`, and `DomainEvent`
unions — in a zero-dependency leaf (`packages/kernel` or `src/kernel`, forbidden
from importing `node:*`, Fastify, Drizzle, or any domain module), wire
`dependency-cruiser` in CI, and keep one tiny fixture proving `depcruise` fails
on a forbidden import (§2.3).

### 12.1 The uncomfortable fact: TypeScript has no module boundary

`export` is a compile-time courtesy. Nothing stops `src/reporting` from importing
`src/billing/internal/ledger.ts`, and nothing fails when it does — the import
resolves, the build passes, and the coupling is now permanent. Node's resolver
has no notion of "private module", and TypeScript's visibility is erased before a
line of code runs.

Worse, some boundaries are invisible *because* the type system merges them:
`declare module "fastify"` augments globally, so two workspace packages that each
add a request property collide the moment they share a compilation context, and
the failure appears in whichever package compiled second.

Consequences, all of which the rest of this section follows from:

- **A boundary you did not enforce with tooling does not exist** (Rule 2 above).
- **`interface` costs nothing and therefore proves nothing** on its own; a port
  is only real if a second implementation exists (Rule 5 above).
- **The reliable unit of isolation is a package**, not a folder.

| Concern | Node/TypeScript mechanism | Enforced by |
| --- | --- | --- |
| Module boundary | separate workspace package + `package.json` `exports` | the resolver, at build and runtime |
| Dependency rule | `dependency-cruiser` (or Nx `enforce-module-boundaries`) | CI |
| Build isolation | `tsconfig` project references, `composite: true` | `tsc -b` |
| Runtime scoping of hooks/state | Fastify encapsulation context | Fastify itself |
| A port | a TS `interface` + at least one non-mock implementation | review, tests |
| Dependency injection | explicit constructor/argument passing at a composition root | the type checker |
| Cross-module reads | a published query function or a read model, never a raw join | dependency-cruiser |

### 12.2 Boundaries: package first, folders second

A folder is a naming convention. A package is a wall.

```jsonc
// packages/requests/package.json
{
  "name": "@app/requests",
  "type": "module",
  "exports": {
    ".": "./src/index.ts",
    "./testing": "./src/testing.ts"
  }
}
```

Everything not listed in `exports` is unreachable from another package — the
subpath not exported cannot be imported, at runtime or in the type checker. That
is the closest Node has to `pub(crate)`, and it costs one build step.

Inside a single package, structure by domain and treat the directory layout as
documentation rather than enforcement (§7, §12.1). Do not pretend a folder
called `internal/` is private; add the dependency-cruiser rule in the same commit
that creates it.

### 12.3 The dependency rule, as a failing build

```js
// dependency-cruiser.config.cjs — four rules that earn their place
module.exports = {
  forbidden: [
    {
      name: "kernel-is-pure-leaf",
      severity: "error",
      from: { path: "^(packages/kernel|src/kernel)" },
      to: { path: "^(src/(?!kernel)|packages/(?!kernel)|node:)" },
    },
    {
      name: "no-cross-module-internals",
      severity: "error",
      from: { path: "^src/([^/]+)" },
      to: { path: "^src/(?!$1)[^/]+/internal" },
    },
    {
      name: "domain-does-not-import-infra",
      severity: "error",
      from: { path: "^src/.*/domain" },
      to: { path: "^src/.*/(db|http|adapters)" },
    },
    { name: "no-circular", severity: "error", from: {}, to: { circular: true } },
  ],
  options: { doNotFollow: { path: "node_modules" }, tsConfig: { fileName: "tsconfig.json" } },
};
```

Run it in `static-test` next to lint (§10), test it once against a violating
fixture (§2.3), and make the message actionable — "reporting may not import
billing/internal" is a rule a reviewer can act on; "architecture violation" is
not.

Two practical notes from real modular-monolith work: the rule that catches the
most is the cross-module *internal* one, and the first violation is almost always
someone reaching for a private table type "just for a dashboard". The fitness
function is what turns that from a debate into a red build.

### 12.4 Fastify encapsulation is a real boundary — of state, not of imports

Fastify's `register()` creates a **child context**: decorators and hooks added
inside it are visible to its descendants, invisible to its siblings and its
parent. That is a genuine runtime boundary, and the closest thing Node has to a
module system — but be precise about what it isolates:

```ts
// src/requests/routes.ts — everything this module decorates stays in its subtree
export default async function requestsRoutes(app: FastifyInstance) {
  app.decorate("requests", new RequestService(app.db));      // not visible to siblings
  app.addHook("preHandler", requireSession);                 // scoped to this plugin
  app.get("/api/requests/:id", getRequest);
}

// src/app.ts — the composition root is the only file that wires modules
await app.register(import("./db/plugin.ts"), { /* fp-wrapped: pool + config */ });
await app.register(import("./requests/routes.ts"), { prefix: "/api" });
await app.register(import("./billing/routes.ts"), { prefix: "/api" });
```

- **It isolates decorated state and hooks, not imports.** `requests/routes.ts`
  can still `import { ledger } from "../billing/internal"` and Fastify will not
  notice. Encapsulation plus dependency-cruiser is the pair; either alone is
  half a boundary.
- **Break encapsulation deliberately and narrowly.** A `fastify-plugin`-wrapped
  plugin decorates the parent scope — correct for a pool, a logger, an auth
  decorator, and wrong for anything module-specific. The raw
  `Symbol.for("skip-override")` escape hatch skips the semver and dependency
  metadata checks as well; do not use it.
- **Do not reach for a DI container instead.** Constructor arguments from one
  composition root are visible, testable, and typed; a container that resolves
  dependencies by string key is the service-locator anti-pattern (§12.7).

### 12.5 Ports, and when an interface is a lie

```ts
// src/requests/domain/order-store.ts — the port speaks the domain, not SQL
export interface OrderStore {
  findOpen(customerId: CustomerId): Promise<Order[]>;
  save(order: Order): Promise<void>;
}
```

That interface is erased at build time and enforces nothing at runtime. It is
worth writing when:

- **a second adapter exists** — an in-memory store used by fast domain tests, or
  a second vendor; or
- **the compiler needs help at a seam** you are about to cross with a `dyn`-like
  choice (a queue, an email provider).

It is **not** worth writing for the database, because §2 forbids mocking the data
layer: the only other implementation would be a mock, and the test suite never
uses it. In that case the honest design is a module that owns its SQL, exported
as functions — `db/queries/requests.ts` — with no interface in front of it.

Where a port is real, keep the mapping in one place: the adapter converts row →
domain, and nothing downstream sees a `snake_case` column name (§4).

### 12.6 Composition root, not service locator

```ts
// src/app.ts — one place constructs the graph
const db = createDb(config.databaseUrl);
const mailer = config.smtp ? new SmtpMailer(config.smtp) : new LogMailer(logger);
const requests = new RequestService(db, mailer, clock);

app.decorate("requests", requests);
```

The dependency graph is readable in one file, and `grep "new SmtpMailer"` finds
every construction site. A `container.resolve("RequestService")` call scattered
through handlers hides the graph, defeats the compiler at the seam, and turns a
missing registration into a runtime error instead of a type error.

### 12.7 Node-specific anti-patterns

| Anti-pattern | Why it bites here | Fix |
| --- | --- | --- |
| **Service-locator container** | hidden deps; missing registration fails at runtime, not compile time | explicit arguments from one composition root |
| **Sinkhole service layer** | `getX()` forwards to `repo.getX()`; three files, zero logic | collapse the layer, or keep it where the 20% with rules live |
| **Fat controller with SQL** | business rule, query, and HTTP shape in one function; untestable without a request | move the rule into a domain function; keep the handler to parse → call → respond |
| **`any` at the boundary** | `req.json()` is `any`; the compiler's silence is the bug | parse to a domain type with Zod/Valibot at the edge, then pass the type |
| **Fire-and-forget `forEach(async …)`** | prints "done" before the work starts; rejections vanish | `for…of await` (sequential) or `Promise.all(map)` (parallel, all-settled if tolerated) |
| **N+1 ORM loop** | one query per row, invisible until production volume | one join / `with` / `inArray`, and a query-count assertion in tests |
| **Module-level mutable singleton** | `let db` in a module is shared by every test in the process, and ordering matters | construct in the composition root; pass down |
| **Barrel re-exporting `internal/`** | reassembles the public API of things meant to be private, and defeats the `exports` wall | export only the module's real surface |
| **`utils/` god module** | becomes the seam everyone imports; it is a boundary-less module by design | move each helper to the domain that owns it |
| **One deployment per feature, "for scale"** | adds a network hop, a queue, and a failure mode for load a single process handles | `worker_threads` for CPU work first; a service only on a §12 Rule 1 trigger |

### 12.8 Review checklist

1. Does this module have a public surface, or is everything importable?
2. Is the boundary a package, or a folder pretending to be one?
3. Do the four `dependency-cruiser` rules run in `static-test`, with a fixture proving they fail?
4. Is `packages/kernel` / `src/kernel` strictly free of I/O, ORM, HTTP, and domain logic?
5. Does any port have a second, non-mock implementation? If not, delete it.
6. Is the dependency graph constructible in one composition-root file?
7. Does any handler contain a business rule *and* SQL *and* a response shape?
8. Is any `async` call unawaited without an explicit, logged rejection path, or any post-commit effect returned unwrapped instead of `MustPublish<T>`?
9. Would this still be one deployable if the feature halved in traffic?

**Sources (checked October 2026).** [Fastify
Encapsulation](https://fastify.dev/docs/latest/Reference/Encapsulation/) and the
Plugins reference for the child-context model and `fastify-plugin` caveats;
dependency-cruiser and Nx boundary docs for the rule syntax; the Fastify monorepo
discussion on `declare module` collisions across workspace packages; the
modular-monolith field guide for the dependency-cruiser case study; and the stock
layered-architecture guidance for the sinkhole and fat-controller anti-patterns,
curated here down to what actually bites in Node.

---

## 13. Keeping this template honest

A `CLAUDE.md` that nobody prunes rots faster than the code it governs: agents
follow dead rules religiously or learn to ignore all of them. Maintain this file
under the same discipline it asks of a project:

- **Every rule here has an automated backstop** — `tsc -b`, ESLint,
  `dependency-cruiser`, `check-standards.ts`, `check-plan-docs.ts`, Drizzle
  snapshot export diff, Fastify `onRoute` IDOR completeness test, Vitest
  coverage thresholds, or `hadolint`. Never add a prose rule without naming the
  gate that turns red when it breaks.
- **Re-verify versions and SHIP-HATS rules quarterly.** Node LTS point releases,
  Fastify 5, Drizzle, Vitest, Playwright, `@stryker-mutator/*`, and SHIP-HATS
  policies (§10.2: Rekor decommissioning, Nexus IQ's seven-day package-age gate,
  EOL image blocks, PAT-only Git over HTTPS) move independently; retire
  third-party helpers once Node 22+ / Web-standard APIs (`crypto.randomUUID`,
  native `.ts` execution, `fetch`, `Intl.Segmenter`) cover them cleanly.
- **Never renumber an addendum or checklist item.** Append new items or
  supersede old addenda (`supersedes: <id>`) so PR, commit, and audit references
  stay stable.
- **Keep every code snippet executable.** Run TypeScript/JavaScript excerpts in
  this file through `node` (`v22.22+` native type-stripping) and `tsc --noEmit`
  whenever touching a pattern so broken syntax never ships in the template.
- **State what each revision of this template actually verified.** The October
  2026 revision adding §1.1, §2.1–§2.4, §3 (`embedded-postgres` vs `PGlite`),
  §5.2, §6 (`packages/shared-rules`), §7 (`MustPublish<T>`), §8.1–§8.2, and §14
  executed every TypeScript code excerpt (`MustPublish<T>`, `satisfies` fixture
  typing, `dependency-cruiser` config) under `node v22.22.3` and checked all
  internal `§` cross-references by script, in a sandbox without `npm` packages
  installed (`tsc`, Fastify, Drizzle, Vitest, and Stryker APIs were verified
  against upstream October 2026 documentation).

If a rule here conflicts with the language you actually chose, you are in the
wrong variant. [`GREENFIELD.md`](GREENFIELD.md) is the language-neutral
template; to write a variant for another language, keep its section order,
replace each mechanism with the target language's idiomatic equivalent, and
preserve every language-independent invariant (real-database tests, soft
deletion, bite checks, honest validation, single-source decisions).

---

## 14. Porting an existing system to Node.js + TypeScript

Everything in §0–§13 assumes a greenfield repository. Porting a live Python,
Ruby, PHP, Java, legacy Express/CommonJS, or Go system to Node.js + TypeScript
is harder in one specific way: **the running legacy system is the specification**,
and JavaScript's IEEE-754 numbers, UTF-16 strings, and silent `JSON.stringify`
omissions will quietly alter edge-case behaviour unless pinned down first. Apply
these rules **on top of** §0–§13.

### 14.1 Scope, then the oracle

- **Fix the port boundary before writing code.** State which components are
  being replaced (HTTP API, background workers, shared rules) and which stay
  unchanged (e.g. an existing SPA or mobile app). Unchanged clients dictate
  exact wire shapes and existing `401`/`403` vs `404` status codes (§2) until an
  explicit post-cutover addendum changes them.
- **Keep the legacy service runnable as the executable oracle.** Never guess
  legacy edge cases by reading old dynamic code when you can send the input to
  the running legacy process and record its actual response.
- **Classify every legacy test file mechanically before porting:**
  1. *Pure black-box HTTP / Playwright E2E* — repoint via `TARGET_BACKEND=legacy|node`;
  2. *HTTP tests with internal DB/model setup* — port assertions, rewrite setup
     against Drizzle + real Postgres fixtures (§3);
  3. *White-box unit tests coupled to legacy classes/mocks* — replace with
     golden-fixture tests (§14.2) and real-DB integration tests.
  Commit the classification ledger so zero legacy test files vanish silently.

### 14.2 Golden fixtures exported from the legacy implementation

- **Export `{input, expectedOutput}` JSON/NDJSON fixtures directly from the
  legacy code** across representative and boundary inputs for every calculation,
  validator, parser, and slugifier, together with a fixture-count manifest.
- **Assert normalised values and error codes/keys**, not just boolean validity,
  and regenerate fixtures only via a committed script — never by hand-editing
  JSON to appease a failing Vitest assertion.

### 14.3 Determinism hazards when porting to Node.js + TypeScript

Audit every calculation, sort, key order, and JSON boundary against these eight
JavaScript / V8 traps:

| Hazard | Legacy behaviour (Python / Java / SQL / Go) | Node.js 22 + TypeScript rule |
| --- | --- | --- |
| **64-bit integers & money (`> 2^53 - 1`)** | Exact `int64` / `BIGINT` / `Decimal` (`9007199254740993` is distinct) | JS `number` is IEEE-754 float64: **`9007199254740992 === 9007199254740993` is `true`!** Map Postgres `bigint` / `numeric` to `bigint` or `decimal.js` / minor-unit `bigint`, and serialise IDs/decimals as strings on JSON wires |
| **`Array.prototype.sort()` default comparator** | Numeric sort (`[2, 10]`) | **`[10, 2].sort()` returns `[10, 2]`** (converts elements to UTF-16 strings)! Always pass an explicit total comparator `(a, b) => a - b` or `localeCompare` with explicit locale/options (V8's sort is stable since ES2019) |
| **Object key iteration order** | Pure insertion order (Python `dict`) or sorted keys | JS plain objects `{}` iterate **non-negative integer-index keys (`"0"`, `"2"`, `"10"`) in ascending numeric order first**, *then* string keys in insertion order! Use `Map` or an array of `[key, value]` tuples whenever key order matters |
| **`JSON.stringify` silent drops & `BigInt` throw** | Explicit serialisation errors or `null` fields | `JSON.stringify` **silently omits object properties with `undefined` values**, turns `NaN` and `±Infinity` into **`null`**, and **throws `TypeError` on `BigInt`**! Validate outbound DTOs with Zod/TypeBox (`satisfies`) at the boundary |
| **Rounding `.5` ties (`Math.round`)** | Half-away-from-zero (`-0.5 → -1`) or half-to-even (`-0.5 → 0`, Python/SQL bankers) | **`Math.round(-0.5)` returns `-0`** (rounds toward $+\infty$)! Write one golden-tested rounding helper (`decimal.js` with explicit `ROUND_HALF_EVEN` or `ROUND_HALF_UP`) matching the legacy contract |
| **String `.length` & slicing** | Unicode code points (Python `len`) or UTF-8 bytes (Go/Rust) | JS `str.length` and `.slice()` count **UTF-16 code units** (`"🙂".length === 2`, family emoji `> 7`)! Use `[...str].length` for code points or `new Intl.Segmenter("en", { granularity: "grapheme" })` for user-perceived characters |
| **`Date` parsing & timezone defaults** | Explicit naive vs aware timestamps | `new Date("2026-10-27")` parses as **UTC midnight**, whereas `new Date("2026-10-27T00:00:00")` (no `Z`) parses in the **host's local timezone**! Require explicit ISO-8601 offsets/`Z` or UTC epoch ms everywhere |
| **Ambient `Date.now()` & `Math.random()`** | Inline clock/RNG calls | Count every `Date.now()`, `new Date()`, and `Math.random()` in the legacy repo; inject `Clock` and a seeded PRNG in domain modules |

### 14.4 The shadow run: diffing legacy and Node live

- **Replay traffic against both servers backed by identically-seeded twin
  Postgres databases**, diffing HTTP status, headers, JSON bodies, SSE/WebSocket
  frames, **and persisted Postgres table state**.
- **Centralise all non-determinism in one unit-tested normaliser:** window-bounded
  timestamps (`<NOW>`, flagging out-of-window drift!), order-of-appearance UUIDv7
  aliases (`<ID_1>`), format-checked random tokens, explicit unordered-set paths,
  and exact numeric/decimal comparison.
- **Require a numbered addendum ID on every allow-listed divergence**, and
  **prove the shadow harness fails** (§2.2) by running legacy-vs-legacy (`0`
  diffs) and legacy-vs-mutated-legacy (status flip, dropped property, reordered
  array, dropped SSE event — all caught).
- **Gate any deterministic replay seed behind a non-production env/module guard**
  tested in CI so production never boots with fixed randomness.

### 14.5 Sharing domain rules with the browser (pure TypeScript package, zero WASM)

Node's natural superpower in a port is sharing exact TypeScript validation and
calculation logic with the browser **without** a WASM compilation toolchain or
runtime binary payload:

- Place pure client/server domain rules in a **zero-I/O workspace package
  (`packages/domain-engine`)** enforced by `dependency-cruiser` (zero `node:*`,
  Fastify, Drizzle, or `process.env` imports, §12.3).
- Run the exact same legacy golden-fixture suite (§14.2) against
  `packages/domain-engine` in Vitest.
- **Guard browser bundle weight and persisted state:** add a CI byte-size
  ratchet on the Vite client chunk so heavy server-only libraries never sneak in,
  and stamp a `schemaVersion` field on any payload persisted to `IndexedDB` or
  `localStorage`.

### 14.6 Surfacing quiet legacy assumptions before designing

Audit and record each legacy assumption in an addendum before coding:

- **In-process memory assuming `replicas = 1`** (in-memory rate limiters, SSE
  Maps, `setInterval` jobs, upload temp dirs): either move state to Postgres or
  acquire a **Postgres session advisory lock on startup** so a second container
  instance fails fast instead of silently splitting state.
- **Ad-hoc post-write hooks:** replace with `MustPublish<T>` (§7) or a
  transactional SQL outbox.
- **Tempting "while we're here" cleanups:** log every legacy quirk in a
  **divergence register** (*kept for parity* · *changed by addendum NNNN* · *to
  decide*) rather than silently altering behaviour mid-port.
- **Single-session test-DB workarounds:** remove legacy serialisation hacks once
  running against real multi-session Postgres (§3).
- **Auxiliary shell/Python ops scripts:** fold seed, healthcheck, and maintenance
  entrypoints into typed `node` CLI subcommands inside the container image.

### 14.7 Package dependency graph first

Define the workspace/module DAG (`packages/kernel` → `packages/shared-rules` /
`packages/domain-engine` → domain modules → `src/app.ts` composition root) in
`dependency-cruiser.config.cjs` (§12.3) with its failing-cycle fixture before
porting the first route.

### 14.8 Cutover and retirement

- **Cut over on measured gates, never a calendar date:** 100% golden-fixture
  pass, zero unexplained shadow divergences across full scenarios, and §8.1
  same-machine tail-latency (`p50`/`p95`/`p99`/`max` + cold-start) parity.
- **Rehearse rollback against staging** while keeping the database schema
  backward-compatible during the shadow window.
- **Delete legacy code, parity shims, and the shadow harness in one clean
  commit** once the rollback window closes.

---

## 15. Egress-restricted sandboxes and pure-Node client/server bootstrap

Cloud coding sandboxes (such as Arena / E2B Debian 12 `bookworm` `x86_64`
containers) ship with Node.js `v22.22+` and `npm` `10.9+` preinstalled and allow
HTTPS to `registry.npmjs.org`, yet still break standard Node/Next.js/Playwright
muscle memory whenever an `npm install` lifecycle hook reaches outside the SNI
allowlist or a dev server rejects proxied preview `Host` headers.

### 15.1 Sandbox baseline and `npm install` postinstall traps

| Layer | Present / Succeeds (`HTTP 200`) | Missing / Fails TLS (`SSL_ERROR_SYSCALL`) |
| --- | --- | --- |
| **Runtime & system** | `node` (`v22.22.3`), `npm` (`10.9.8`), `npx`, `gcc`, `python3`, `git`, `gh` | Preinstalled `chromium`, `apt-get` (`deb.debian.org` blocked) |
| **npm packages that work cleanly** | Pure-JS packages (`typescript`, `@types/node`, `fastify`, `drizzle-orm`, `vitest`, `playwright-core`) and npm-hosted optional platform packages (`esbuild` via `@esbuild/linux-x64`, `vite` via `@rollup/rollup-linux-x64-gnu`, `@toolchain-bin/aimeeting-sandbox-chromium`) | Packages whose `postinstall` fetches binaries from external CDNs or GitHub Releases (`playwright` hitting `cdn.playwright.dev`, `puppeteer`, `cypress`, `prebuild-install` packages hitting `github.com/.../releases/download` → blocked `objects.githubusercontent.com`) |
| **Snapshot exclusions** | `/tmp/*` plus `node_modules`, `dist`, `build`, `.arena`, `.cache`, `.local`, `.vite` | Non-excluded directories under `/home/user` (e.g., `~/.aimeeting-browser`, `~/.cache` siblings) count toward the ~128 MB / 10,000-file snapshot cap |

**Rule of thumb:** before adding a dependency in an egress-restricted sandbox,
prefer Node 22 built-ins first, pure-JS npm packages second, and npm-tarball
platform packages third; never install full `playwright` without
`PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1` (prefer `playwright-core`).

### 15.2 Node 22.22 built-ins that replace bundlers, test runners, and native addons

When building a pure-Node backend and pure client-side TypeScript frontend from
scratch (no Next.js), Node `22.22+` already ships every runtime primitive needed
with *zero* runtime dependencies (`npm install --save-dev typescript @types/node`
in ~2 s is only needed for strict `tsc --noEmit`):

1. **Flagless native `.ts` execution and `node:test`.** Node 22.18+ enables
   type-stripping by default: `node src/server/main.ts` and
   `node --test test/*.test.ts` execute `.ts` modules directly in ~200 ms with
   zero `tsx` or `ts-node` loader.
2. **Zero-bundler client TypeScript via `node:module.stripTypeScriptTypes`.**
   Built-in `stripTypeScriptTypes(tsSource, { mode: "strip" })` erases TypeScript
   syntax in `< 1 ms` while preserving exact line/column offsets with whitespace:
   - **Dev / single-process server:** whitelist `src/client/*.ts` and
     `src/shared/*.ts`, strip types once into `Buffer`s at boot, and serve them
     with `Content-Type: text/javascript; charset=utf-8`. Browser
     `<script type="module" src="/client/app.ts">` then loads shared `.ts`
     specifiers (`import { render } from "../shared/render.ts"`) natively with
     identical paths across `node --test`, `tsc --noEmit`, and Chromium ES
     modules.
   - **Static `dist/` build:** run a 20-line `scripts/build-dist.ts` using
     `stripTypeScriptTypes(src, { mode: "strip" }).replaceAll('.ts"', '.js"')` to
     emit zero-dependency ES2024 assets (`~4.5 KB` total).
3. **Embedded persistence via `node:sqlite` (`DatabaseSync`) — watch
   `SQLITE_DQS=0`.** Built-in `import { DatabaseSync } from "node:sqlite"` avoids
   `better-sqlite3` C++ `node-gyp` builds and blocked GitHub Release prebuilds.
   Two details matter immediately:
   - **Strict ANSI quoting (`SQLITE_DQS=0`):** Node compiles SQLite with
     double-quoted string literals *disabled*. `"ok"` is parsed strictly as a SQL
     identifier and throws `ERR_SQLITE_ERROR: no such column: "ok"`. Always use
     single quotes (`'ok'`) or `?` prepared-statement parameters
     (`db.prepare("INSERT INTO probes (ts) VALUES (?)").run(now)`).
   - Pass `--disable-warning=ExperimentalWarning` in `package.json` scripts to
     keep test and server output clean.

### 15.3 Dual strict `tsconfig` layout for pure client + server TypeScript

Split browser and server global scopes cleanly while sharing `src/shared/*.ts`
and enforcing erasable syntax compatible with `stripTypeScriptTypes`:

```json
// tsconfig.base.json
{
  "compilerOptions": {
    "target": "ES2024",
    "module": "NodeNext",
    "moduleResolution": "NodeNext",
    "strict": true,
    "noUncheckedIndexedAccess": true,
    "exactOptionalPropertyTypes": true,
    "noImplicitOverride": true,
    "verbatimModuleSyntax": true,
    "erasableSyntaxOnly": true,
    "allowImportingTsExtensions": true,
    "noEmit": true,
    "skipLibCheck": true
  }
}
```

- `tsconfig.server.json` extends `tsconfig.base.json` with
  `"lib": ["ES2024"], "types": ["node"]` covering `src/server`, `src/shared`,
  `scripts`, and `test`.
- `tsconfig.client.json` extends `tsconfig.base.json` with
  `"lib": ["ES2024", "DOM", "DOM.Iterable"], "types": []` covering `src/client`
  and `src/shared` — guaranteeing client code never references `process` or
  `Buffer`, server code never touches `document`, and `erasableSyntaxOnly: true`
  rejects `enum`/`namespace`/parameter properties at typecheck time before
  `stripTypeScriptTypes` ever sees them.

### 15.4 Live-preview networking (`0.0.0.0`, Vite `allowedHosts`) and offline Chromium E2E

1. **Pure `node:http` / Fastify preview rules:**
   - Bind to `0.0.0.0` (`server.listen(port, "0.0.0.0")`), never `127.0.0.1`.
   - Serve `GET /favicon.ico -> 204` so browser E2E checks observe zero console
     404 errors, avoid localhost-only `Host`/`Origin` checks so
     `https://{port}-{sandboxId}.e2b.app` succeeds, and call strictly relative
     `/api/*` URLs from client code.
2. **If using Vite for a larger SPA, configure `allowedHosts` and `proxy` on day
   one:** Vite 6+ blocks unknown proxy `Host` headers by default
   (`Blocked request. This host ("5173-<id>.e2b.app") is not allowed`). Always
   configure `vite.config.ts` with:

   ```ts
   export default defineConfig({
     server: {
       host: "0.0.0.0",
       allowedHosts: [".e2b.app"],
       proxy: { "/api": "http://127.0.0.1:3001" },
     },
   });
   ```

3. **Headless Chromium 150 E2E inside the sandbox:** install `playwright-core`
   and `@toolchain-bin/aimeeting-sandbox-chromium` from `registry.npmjs.org`,
   **always** set `export AIMEETING_BROWSER_HOME="/tmp/aimeeting-browser"` (so
   the `394 MiB` unpacked browser + Debian 12 `lib/*.so` closure stays outside
   `/home/user` snapshots), and launch with:

   ```js
   const browserPkg = require("@toolchain-bin/aimeeting-sandbox-chromium");
   const { chromium } = require("playwright-core");
   const browser = await chromium.launch({
     executablePath: browserPkg.executablePath(),
     args: ["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"],
     env: {
       ...process.env,
       LD_LIBRARY_PATH: [browserPkg.libraryPath(), process.env.LD_LIBRARY_PATH]
         .filter(Boolean)
         .join(":"),
     },
   });
   ```


