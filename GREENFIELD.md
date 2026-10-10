# GREENFIELD.md — CLAUDE.md template for new projects

This file is a **standing-instructions template** meant to be copied to a new
repository's `CLAUDE.md` (and split into focused section files as the project
grows). It distills the conventions, disciplines, and tooling choices that —
if laid out up front — avoid the avoidable pain we hit when they were learned
the hard way mid-project. It is **deliberately project-agnostic**: no product
name, no feature references, no hardcoded service names. Adjust the concrete
stack placeholders (language, framework, ORM, test runner) to the actual
project.

---

## 0. How to use this template

- Copy the whole file as `CLAUDE.md`, then **replace every `<placeholder>`**
  with the real stack.
- As the project grows past a few hundred lines, split each `##` section into
  its own file (`CLAUDE-testing.md`, `CLAUDE-database.md`, …) with a
  top-level `CLAUDE.md` index, so agents `grep` a focused section instead of
  loading the whole corpus. A top-level index + sectioned files is a
  *documentation architecture*, decided on day one — retrofitting it later is
  churn you don't need.
- Keep the "record every decision" and "write tests first" rules in the very
  first sections: they are the two that prevent the most rework.

---

## 1. Record every decision, up front, in a living spec (addendum discipline)

**When you start, decide what the "source of truth" is and where decisions
get written.** The single biggest avoidable cost in a long-lived project is a
spec that silently drifts from the implemented system, forcing future readers
to reverse-engineer intent from commits and chat.

- Maintain a **living functional/design specification** (the product contract)
  plus a **sequentially-numbered addenda register** for every decision that
  isn't dictated by that base spec: filling a gap, adding a new
  object/field/tool, or deviating from the spec.
- Write up each addendum **proactively, in the same change that makes the
  decision** — never as a follow-up. Each covers: (1) what was decided,
  (2) why, (3) which spec section it relates to, (4) practical impact and what
  a future reader must know.
- Keep the addenda **independent of the base spec's own section numbering**, so
  the base spec stays stable and addenda append forever.
- `CLAUDE.md` must tell future agents to do this without being asked. It is the
  difference between a codebase you can reason about and a puzzle box.

## 2. Write tests first, and keep them real (no mocks where it counts)

**Tests are the mechanism that actually catches bugs — decide the discipline
before any feature ships.** The pain avoided: shipping a wrong-field bug or an
authorization hole that a manual review missed, because "the happy path works."

- **Backend:** run automated integration tests against a **real database
  (a separate test DB, never the dev DB)** through the real app entrypoint
  (e.g. an app/router object that can be exercised without a listening
  socket) — **never mock the data-access layer**. A mocked-repository test
  hides exactly the class of bug you care about (bad SQL, wrong column names,
  FK violations, JSONB round-tripping).
- **Every route/endpoint needs BOTH a positive test AND a session-scoping
  negative test**: a real, valid, logged-in session that is the *wrong party*
  for THIS resource (IDOR-style id substitution) must be rejected. A generic
  "no token → 401" proves auth, not authorization scoping.
- **Add/update tests in the same change as the route** — never as a follow-up.
- Frontend unit tests may mock the API boundary; e2e tests drive the real UI
  against a real backend with **no mocks**.
- Adopt a security-test matrix (e.g. OWASP Top 10) for every endpoint, with an
  explicit applicability assessment per category — decide this on day one,
  not after an audit finds gaps.

## 3. Test infrastructure defaults (video, isolation, determinism)

- **Record Playwright video by default**, with a single documented env-var
  off-switch. Retroactively discovering a whole e2e suite was "blind on
  failure" because video was off is avoidable.
- **Isolate environments hard**: a separate test DB, unique-per-run test
  identifiers (e.g. `{label}.{runId}@example.test`), and self-contained
  provisioning so suites are repeatable and runnable in parallel.
- Use **realistic, deterministic fixture data** (named people, not `user-123`),
  with pools that reflect the domain (e.g. different name pools per actor
  role/affiliation) so test output reads naturally while remaining unique.
- Decide the **test layout by type** on day one (`backend/`, `frontend/unit`,
  `frontend/e2e`, `fixtures/`) and keep it consistent.

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
  invalidated targets — a DB FK only proves the row once existed.

## 5. Schema evolution (migrations + wholesale snapshot, same change)

- **Two always-in-sync halves, landed in the same commit:**
  (1) a wholesale, self-contained schema/seed snapshot that a brand-new DB
  applies from zero (every `CREATE TABLE` lists every current column — never
  `ALTER`s that turn it into "current shape + a changelog of patches");
  (2) a sequentially-numbered migration file (zero-padded, idempotent,
  `BEGIN`/`COMMIT`, records itself in a `schema_migrations` table) that an
  already-provisioned DB applies to catch up.
- **Every schema change = snapshot update + migration file, in the same commit.**
  Skipping either half causes the exact drift this discipline eliminates.
- Apply pending migrations automatically on app boot, and provide a standalone
  migration command.

## 6. Code conventions that prevent whole classes of bugs

- **`data-testid` on every interactive element** at authoring time, with a
  documented naming convention (`{component-kebab}__{element-role}`). Repeated
  rows share one testid; scope by anchor text first. This makes testids a
  stable contract the unit and e2e suites rely on — gaps defeat the point.
- **Stable, typed wire contracts** between backend and frontend — define the
  response shapes once and type both sides from them, so a field rename is a
  compile error, not a runtime `undefined` that silently breaks a test or a
  page. (We hit a demo-video outage purely from a wire-field rename that the
  test helper still read under the old name.)
- **Don't show internal design decisions to end users.** Keep rationale and
  "why this is done this way" notes in code comments and docs, never in
  user-facing labels or descriptions. Scrub internal slugs / design references
  from shipped copy.
- **Keep user-facing copy user-facing, internals internal** — and keep third-
  party/external contract keys exactly as the external system requires,
  even when they don't match your internal casing. Not everything is yours to
  rename (external payload keys, notification-template placeholders).

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

## 8. Validate early and honestly

- **Static checking layer is not a substitute for real tests.** When the real
  toolchain (compiler, test runner, DB) is unavailable in a sandbox, run
  per-file syntax checks, execute pure modules, and grep structural invariants —
  but **say exactly which layer you ran** and never claim "tests pass."
- The real gate, before merge, is always: full type-check, full lint, and the
  full test suites against a real DB/browser.
- Append the validation caveat to commits made under constrained tooling so a
  reviewer knows what still must run.

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

## 10. What to decide before writing the first feature (checklist)

1. Source-of-truth spec location + addenda numbering.
2. Test DB isolation + "tests-first, real DB, no repo mocks" rule.
3. ORM + one-casing policy (no hand-written mappers).
4. Soft-delete + UUIDv7 + real-actor-rows object model.
5. Schema snapshot + migration twin-file workflow.
6. `data-testid` convention + typed wire contracts.
7. Test layout by type + Playwright video-on default.
8. Realistic fixture-name pools + unique-per-run identifiers.
9. Static-check fallback discipline + validation caveat.
10. One-command local env setup + `.env`/.env.test separation.
11. Function design rules: ≤ 50-line functions, guard clauses, ≤ 3 params, no flag args,
    no mutation, Separate Query from Modifier, domain-based module grouping, 800-LOC
    file hard limit, barrel-split pattern for god modules.

Answer these eleven up front and a greenfield project avoids most of the rework,
silent drift, and "we should have written that down" moments this template
exists to prevent.
