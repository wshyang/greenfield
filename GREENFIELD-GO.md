# GREENFIELD-GO.md — CLAUDE.md template for new Go projects

**Standalone.** This is the Go variant of the greenfield template.
`GREENFIELD.md` is the language-neutral template it was derived from; its
lessons are folded in here, so nothing in this file depends on reading it, and
no other sibling file is assumed to exist. It is a **standing-instructions
template** to copy into a new repository's `CLAUDE.md` (and later split into
focused section files). It is deliberately project-agnostic — no product name,
no feature references, no hardcoded service names.

It does three jobs:

1. **It fixes the invariants** that are cheap on day one and expensive to
   retrofit: real-database tests, soft deletion, UUIDv7, a schema checked
   against what the code expects (twin files, or a single snapshot with a
   version+hash gate while nothing is deployed — `DR-11`), a strictness profile,
   a container contract, honest validation.
2. **It stops the agent from silently choosing on the user's behalf.** Go has
   several equally defensible answers for the router, the data layer, the wire
   contract, the UI, auth, background jobs, schema evolution, and the runtime
   image. §0.3 defines a **decision interview**: the agent must ask the user,
   present each option with a real code example and its trade-offs, recommend
   one, and record the answer as an addendum. This document ships the eleven
   question cards (`DR-01`…`DR-11`), ready to send.
3. **It settles the code-level idioms that reviewers argue about.** §13 is the
   `strictest`-equivalent Go compiler and `golangci-lint` v2 + `nilaway`
   profile; §14 covers value/pointer signatures, naming, unexported struct
   fields, and `PATCH` tri-state fields; §15 is the pattern allow-list and
   deny-list; §16 covers goroutine correctness and OpenTelemetry; §17 covers
   performance and adversarial testing; §18 covers modular-monolith architecture
   in Go. These are stated as rules, not suggestions, because every one of them
   is cheaper to adopt before the first thousand lines.

**Versions verified October 2026** (Go `1.27` stable, `go1.27.3` released
October 2026; Go `1.28` lands February 2027): `go-chi/chi/v5` `v5.3.2`,
`jackc/pgx/v5` `v5.11.0`, `sqlc` `v1.31.1`, `pressly/goose/v3` `v3.29.0`,
`peterldowns/pgtestdb` `v0.1.1`, `fergusstrange/embedded-postgres` `v1.34.0`,
`danielgtaylor/huma/v2` `v2.39.1`, `oapi-codegen/v2` `v2.8.0`,
`connectrpc.com/connect` `v1.21.1` (`v2.0.2`), `a-h/templ` `v0.3.1070`,
`alexedwards/scs/v2` `v2.9.0`, `coreos/go-oidc/v3` `v3.21.0`,
`riverqueue/river` `v0.49.0`, `go.opentelemetry.io/otel` `v1.47.0` (`otelslog`
`v0.21.0`, `otelhttp` `v0.72.0`, `exaring/otelpgx` `v0.12.0`),
`golangci-lint/v2` `v2.14.0`, `govulncheck` `v1.9.0`. Pin exact versions in
`go.mod`; treat every version in this file as "verified then", not "latest
forever".

**Contents.** §0 how to use it and the decision interview · §1 decisions and the
living spec · §2 tests · §3 test infrastructure · §4 database discipline · §5
schema evolution · §6 code conventions · §7 function and package design · §8
honest validation · §9 local dev · §10 containers and SHIP-HATS · §11 day-one
checklist · §12 the eleven decision cards · §13 the strictness profile · §14 API
and idiom rules · §15 design patterns · §16 concurrency and observability · §17
performance and adversarial testing · §18 architecture in Go · §19 keeping this
template honest · §20 porting an existing system to Go · §21 egress-restricted
sandboxes and pure-Go Wasm bootstrap.

---

## 0. How to use this template

### 0.1 Copy, then unpack

- Copy this whole file as `CLAUDE.md` in the new Go repository, delete any other
  greenfield template files copied alongside it in the same commit, then replace
  every `<placeholder>`. Keep the `DR-` identifiers intact: they are referenced
  by addenda, CI checks, and doc comments.
- **Preferred progressive-disclosure unpack (`.claude/` skills + lean `CLAUDE.md` /
  `AGENTS.md`):** because a 3,700-line `CLAUDE.md` taxes every turn and exceeds
  Claude Code's 5,000-token post-compaction skill cap, copy `.claude/` alongside
  this repository and run `/greenfield-bootstrap go` to render a `<= 130`-line
  `CLAUDE.md` from `.claude/skills/greenfield-bootstrap/assets/CLAUDE.lean-template.md`.
  Keep a compact two-column `.claude/` dispatch table in that unpacked file
  (mapping tasks to Claude Code skills **and** to explicit `.claude/skills/*/SKILL.md`,
  `.claude/rules/*.md`, and `.claude/skills/*/scripts/*.sh` fallback paths for
  non-Claude `AGENTS.md` harnesses that lack auto-loaders/hooks), prune unused
  `node-*.md` / `rust-*.md` references + `greenfield-bootstrap/` (and
  `greenfield-port/` if not porting), and maintain **one** root file (`AGENTS.md`
  with `@AGENTS.md` in `CLAUDE.md`, or a symlink — never two diverging copies).
- Splitting each `##` section into `CLAUDE-go-<area>.md`
  (`CLAUDE-go-database.md`, `CLAUDE-go-deployment.md`, …) behind a top-level
  index is **optional**, not a bootstrap step. Do it when one file stops being
  readable in a single pass; agents then `grep` one focused file instead of
  loading the corpus. Until then, one file is simpler to keep honest.
- If you do split, keep §0 (the interview), §1 (decisions), and §2 (tests) in
  the *first* file an agent reads. They prevent the most rework.
- Copy the deployment starters from `initial-templates/` in the greenfield
  repository when they exist, then contextualise them against §10.1. The Go
  `Dockerfile` in §10.1 is the reference implementation; do not copy runtime
  auto-detection assumptions into a compiled Go image.

### 0.2 Two classes of rule: invariants vs. forks

Not every choice is the user's to make at kickoff. Mixing the two is how a
"please decide" prompt turns into an interrogation and how a load-bearing
discipline gets traded away for speed.

| Class | Meaning | Agent behaviour |
| --- | --- | --- |
| **Invariant** | Fixed by this document because the cost of retrofitting is high and the answer does not vary by project (soft delete, UUIDv7, real-DB tests, no mocked repositories, a schema checked against the code (`DR-11` picks the mechanism), port 3000 on `0.0.0.0`, no hand-written mappers, no request-path `panic`, `-race` enabled). | Implement as written. If the project genuinely cannot comply, **stop and ask**; if approved, record an addendum that names the invariant being waived and why. Never waive silently. |
| **Fork** | Two or three defensible Go answers with different costs, and no way to infer the team's preference from the repo (`DR-01`…`DR-11`). | **Ask before writing the first line in that area.** Use the question card from §12. Record the answer. |

The invariants live in §2, §4, §5, §6, §7, §8, §10, and §13–§18. The forks are
exactly `DR-01`…`DR-11`, listed in §0.7.

§15 is a hybrid: the pattern allow-list is a default, but each pattern names the
condition under which it is **wrong** ("use a status enum instead when…", "use a
plain config struct instead of Functional Options when…"). Applying typestate to
a dynamic database-driven workflow is a violation, not a preference — the
exceptions are written down so an agent cannot cite the pattern as cover for
over-engineering.

### 0.3 The decision interview (hard rules)

This section is an instruction to the agent, not advice.

1. **Ask before code, not after.** Before implementing anything that touches a
   `DR-` area, the user must have answered that `DR-`. "I'll pick something
   sensible and we can revisit" is not an answer; if the user says it, use the
   recommendation, record `decided_by: agent`, and flag it in the PR.
2. **One decision per question.** Never bundle "which SQL layer and which
   frontend" into one prompt; the answer to one biases the other.
3. **Batch at most four questions per message**, in the three batches of §0.7.
   A wall of ten questions gets rubber-stamped.
4. **Every option gets all five parts**: a one-line shape, a real example the
   user could paste into the project (a code or config excerpt in the project's
   own vocabulary — never a toy `foo`/`bar` stub), pros, costs, and a "choose
   this if" line. For options whose difference *is* configuration (image bases,
   task runners), the excerpt is the config, not a function.
5. **Always recommend one option and say why**, in one sentence, tied to the
   project's actual constraints (team background, deployment target, deadline).
   An unranked menu pushes the decision back onto the user.
6. **Always offer the escape hatch**: "reply `all recommendations`".
7. **Record the answer before implementing it** (§0.5). The addendum is the
   contract; the chat message is not.
8. **Never re-litigate a recorded decision** without new information. Supersede
   it with a new numbered addendum; do not edit history.
9. **If an answer violates an invariant**, say which invariant, why it exists,
   and what it would cost. Do not implement it quietly.
10. **Re-ask only the affected `DR-`** when scope changes (e.g. the project
    gains a second binary, or a Singpass/TechPass OIDC requirement appears). Do
    not re-run the whole interview.

**Definition of Ready for `cmd/` and `internal/`.** No Go application code is
scaffolded until Batch 1 (`DR-01`, `DR-02`, `DR-03`) is answered and recorded in
`docs/decisions/`.

**Opening message shape.** One line stating the batch, the number of decisions,
and the escape hatch; then one card per decision, each ending with its own
question; then stop. No preamble about how exciting the project is, and no
"meanwhile I'll scaffold `go.mod` and the server" — scaffolding *is* the choice
being asked about.

```text
Three foundation decisions before I write any code. Each card ends with a
recommendation; reply A/B/C per card, or "all recommendations".

DR-01 · HTTP router
…
DR-02 · Data access
…
DR-03 · Module and package layout
…
```

### 0.4 The question card (copy this shape)

Send exactly this shape. If the agent's harness has a structured question
widget, put the option labels there and the card text in the body; otherwise
send the card as plain text. Either way the example must be visible — an option
label ("B: bob") is not a trade-off. A bullet list of adjectives is not a
decision aid either; the code is what makes the choice legible.

```text
DR-02 · Data access layer — question 2 of batch 1

How should the server talk to Postgres?

A. sqlc 1.31 + pgx/v5 5.11 — SQL first, compiled into typed Go
   Real example:
       -- internal/requests/queries.sql
       -- name: GetActiveRequest :one
       SELECT id, title, owner_id, created_at
         FROM active_requests
        WHERE id = $1 AND owner_id = $2;

       // caller in internal/requests/handlers.go:
       row, err := q.GetActiveRequest(ctx, GetActiveRequestParams{
           ID:      id.UUID(),
           OwnerID: actor.ID().UUID(),
       })
   Pros:  SQL stays visible and reviewable; sqlc parses db/schema.sql so a
          typo or renamed column fails `sqlc compile` with no live database;
          zero runtime reflection on the native pgx/v5 binary wire protocol.
   Costs: generated `*.sql.go` files must be regenerated and committed when
          queries change; dynamic multi-facet `WHERE` filters need `sqlc.narg`
          or a small companion builder; SQL view columns need non-null
          overrides in `sqlc.yaml`.
   Choose if: your team reads SQL fluently and wants the query to be the
          source of truth.

B. stephenafamo/bob + pgx/v5 — typed SQL builder generated from schema
   Real example:
       row, err := models.ActiveRequests.Query(
           sm.Where(models.ActiveRequests.Columns.ID.EQ(psql.Arg(id.UUID()))),
           sm.Where(models.ActiveRequests.Columns.OwnerID.EQ(psql.Arg(actor.ID().UUID()))),
       ).One(ctx, db)
   Pros:  composable dynamic filters without string concatenation; column
          names and types generated from Postgres schema; the schema is the
          single source of the generated Go types, as in schema-first query
          builders.
   Costs: a second DSL to learn on top of SQL; larger generated model tree on
          wide schemas; complex CTEs are harder to read than raw `.sql`.
   Choose if: endpoints are dominated by dynamic filter/sort combinations and
          you accept schema codegen.

C. ent (entgo.io/ent) or uptrace/bun — graph / struct ORM
   Real example:
       row, err := client.Request.Query().
           Where(
               request.IDEQ(id.UUID()),
               request.OwnerIDEQ(actor.ID().UUID()),
               request.ExpiresAtIsNil(),
           ).Only(ctx)
   Pros:  ent gives strongly typed graph traversal and eager-loading without
          hand-written joins; fastest path for deeply nested entity graphs.
   Costs: heaviest codegen footprint (`ent`) or runtime reflection (`bun`);
          hardest to keep strictly aligned with raw `db/schema.sql` triggers
          and partial indexes (§4.3–§4.4). (Note: GORM is not offered — its
          silent zero-value update behaviour and reflection magic violate §4.)
   Choose if: reads are mostly deep object graphs and you want less SQL.

Recommendation: A — `sqlc` + `pgx/v5` gives compile-time SQL verification with
zero live DB needed at build time and zero ORM reflection.
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
date: 2026-10-27
supersedes: null
---

# 0007 — Data access: sqlc + pgx/v5

## Decision
`sqlc` v1.31.1 generating `pgx/v5` (`v5.11.0`) code from `db/schema.sql` and
`internal/<domain>/queries.sql`, tested per-test via `peterldowns/pgtestdb`.

## Why
<the user's stated reason, not the agent's reconstruction>

## Rejected
- bob + pgx/v5: <the actual reason this project declined it>
- ent / bun: <…>

## Impact
<!-- Boxes, not prose (§1.1): an id, one action, the exact file or command, a done-when. -->
- [ ] 0007-1 Keep every SQL statement in `internal/<domain>/queries.sql` — `git grep -n "pool\.Query" internal/ ':!internal/platform/'` prints 0 lines — done when handlers hold zero SQL
- [ ] 0007-2 Gate CI on stale generated query code — CI job runs `go tool sqlc diff && go tool sqlc vet` — done when editing a query without regenerating turns CI red
- [ ] 0007-3 Wire `pgtestdb` per-test databases (§2.1) and the chosen `DR-11` schema path (§5) — done when both run in the first `*_integration_test.go` and `cmd/server/main.go`
```

Rules for the addendum: it names the **rejected** options and why. Six months
later "why didn't we use Ent?" is the question that gets asked, and the chat
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
| `DR-01` | HTTP router | `go-chi/chi/v5` · stdlib `net/http.ServeMux` · `labstack/echo` | `chi/v5` | §2, §6, §10 | Medium — route mounting, middleware, tests |
| `DR-02` | Data access | `sqlc` + `pgx/v5` · `bob` + `pgx/v5` · `ent` / `bun` | `sqlc` + `pgx/v5` | §2, §4, §5, §9 | **Very high** — every query, every test, codegen |
| `DR-03` | Module & package layout | single `go.mod` domain packages · single `go.mod` layered packages · `go.work` workspace | single `go.mod` domain packages | §7, §8, §18 | Medium — import paths and `arch_test.go` |
| `DR-04` | Wire contract | `huma/v2` → OpenAPI 3.1 → TS · `oapi-codegen/v2` spec-first · `connectrpc` + Buf | `huma/v2` → OpenAPI → TS | §6, §8 | High after the frontend exists |
| `DR-05` | Frontend | React + Vite · `a-h/templ` + HTMX · stdlib `html/template` + HTMX | React + Vite | §3, §6, §7 | High — it is a rewrite |
| `DR-06` | Auth | `scs/v2` Postgres sessions + stdlib CSRF · stateless JWT · `coreos/go-oidc/v3` | sessions, + OIDC when SSO is mandated | §2, §4, §10 | High — every authorization check |
| `DR-07` | Error wire shape | RFC 9457 `problem+json` · simple envelope · bare status | RFC 9457 | §6, §8 | Medium — every client branch |
| `DR-08` | Background work | SQL outbox + `SKIP LOCKED` worker · `riverqueue/river` (`InsertTx`) · none yet | SQL outbox | §4, §9, §16 | Medium — job semantics |
| `DR-09` | Runtime image | `distroless/static-debian12:nonroot` · `debian:bookworm-slim` · `alpine:3.22` | `distroless/static` | §10.1, §17.2 | Low — one Dockerfile stage |
| `DR-10` | Dev orchestration | `just` · `go run ./cmd/devtask` · `make` | `just` | §9, §10.4 | Low — developer muscle memory |
| `DR-11` | Schema evolution | twin snapshot + numbered migrations · single snapshot with version+hash gate (nothing deployed yet) | single snapshot before persistent data; twin migrations once anything is deployed | §5, §8, §9 | Medium — adding migrations later is cheap; reconstructing history is not |

**Batch 1 (foundation):** `DR-01`, `DR-02`, `DR-03`.
**Batch 2 (product surface):** `DR-04`, `DR-05`, `DR-06`, `DR-07`.
**Batch 3 (operations):** `DR-08`, `DR-09`, `DR-10`, `DR-11`.

The sections below are written against the **defaults** in that table. If the
user picks a different option, the named section changes; nothing else does.

### 0.8 Cross-decision consistency

Answers interact, and some combinations quietly contradict the sections that
follow. Check these before recording the addenda; raise the conflict instead of
writing code that satisfies neither answer.

| Combination | Consequence | Resolution |
| --- | --- | --- |
| `DR-01 = echo` + `DR-06 = sessions` | `alexedwards/scs/v2` and Go 1.25 `http.CrossOriginProtection` wrap `net/http.Handler`, while Echo uses `echo.MiddlewareFunc` | wrap via `echo.WrapMiddleware`, or choose `DR-01 = chi/v5` / `ServeMux` so standard `http.Handler` middleware composes directly |
| `DR-01 = ServeMux` + `DR-04 = huma/v2` | `humachi` expects a `chi.Mux` | switch adapter to `github.com/danielgtaylor/huma/v2/adapters/humago` and note it in addendum `DR-04` |
| `DR-05 = templ`/HTMX + `DR-04 = huma/v2` | OpenAPI → TypeScript client buys nothing when Go renders HTML directly | skip `openapi-typescript` generation unless a TS island or external API consumer exists; keep the route-security test (§2.2) |
| `DR-04 = connectrpc` + `DR-07 = RFC 9457` | ConnectRPC defines its own wire error JSON (`code`, `message`, `details[]`) by protocol spec | let Connect routes speak native `connect.Error` codes while any plain REST webhook routes still emit RFC 9457; record in `DR-07` |
| `DR-09 = distroless/static` + CI `-race` | `CGO_ENABLED=0` produces a pure static production binary, whereas `go test -race` requires `CGO_ENABLED=1` and a C toolchain | set `CGO_ENABLED=0` only in `Dockerfile` / release builds and `CGO_ENABLED=1` in test/CI jobs (§8.1, §10.1) |
| `DR-11 = B` + any CI job that restores a DB dump | a restored dump carries an older `schema_state` stamp/hash, so the boot gate will (correctly) refuse to start | restore only into a throwaway database, then reset; never restore over a database protected by the gate |
| `DR-11 = B` + `DR-02 = sqlc` | `sqlc` compiles directly from `db/schema.sql` offline, so editing `db/schema.sql` without regenerating leaves stale `*.sql.go` structs | bump `SchemaVersion`, regenerate `sqlc generate`, and keep `go tool sqlc diff` in CI in the same commit |

If two answers cannot be reconciled, the later one wins and the earlier addendum
is superseded — never left in place contradicting its successor.

---

## 1. Record every decision, up front, in a living spec (addendum discipline)

The expensive failure mode is a spec that drifts from the binary: the only
remaining description of intent is a commit message and a Slack thread. Go's
toolchain and simple AST tooling make this discipline mechanically verifiable.

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
  - the same script scans `cmd/` and `internal/` and asserts every
    `TODO(DR-xx)` marker resolves to an accepted addendum — an unresolved marker
    is a decision still being taken in code, which is what this section forbids.
- **Go doc comments (`godoc`) are part of the spec.** Every package under
  `internal/` carries a `doc.go` (or primary file header) with a `// Package
  <name> …` comment citing its governing addendum (`// Governing decision: 0007
  (DR-02).`). `revive` rules `package-comments` and `exported` in `.golangci.yml`
  (§13) fail CI when exported domain types or functions lose their contracts, and
  testable `func Example…()` functions in `*_test.go` compile and verify
  documented usage on every `go test` run.
- `CLAUDE.md` must instruct future agents to do all of the above unprompted.
  That instruction is the difference between a codebase you can reason about and
  a puzzle box.

### 1.1 Plans and designs are written in two cuts

A multi-step design document, migration plan, or porting spec that stops at
readable prose cannot be tracked, handed to an agent, or audited. Write every
multi-task plan, feature spec, and porting document in two passes (single-choice
`DR-` addenda need only the `2–4` concrete `## Impact` boxes of §0.5):

1. **Cut one is the shape**: scope, packages, decisions, and trade-offs in clear
   prose a reviewer can read in one pass.
2. **Cut two is the work**: under every prose section, a `Verify / do` list of
   checkboxes. Each box carries a unique id, **one** imperative verb, the exact
   file path, command, SQL query, or count it concerns, and an observable *done
   when*:

```markdown
- [ ] ST-V2.3 Move all 18 write transactions into `internal/requests` — `git grep -c "pool\.Begin(" internal/` prints `internal/requests/store.go:18` — done when zero other domain files open raw transactions
```

Rules that keep the second cut honest:

- **A box naming no path, command, query, or number is not a task.** Reject
  weasel lead verbs: *ensure*, *consider*, *review*, *improve*, *handle*.
- **Every number copied from a survey or agent summary gets a re-check command.**
  Reported counts (routes, tables, `time.Now` call sites, cache sites) are
  claims until re-run; keep the exact command beside the number so the next
  reader can re-verify it in one second.
- **Every design decision names the task ID that implements it and the test name
  (`Test…`) that proves it.** A decision with neither is a wish — assign both or
  delete it.
- **Rehearse change-vector claims.** Verify *"adding a new event kind touches
  only `internal/kernel` and `internal/requests`"* by making the edit on a
  throwaway branch and checking `go build ./...` compiler errors against the
  claim.
- **Prove the doc checker can fail.** Run a small pure-Go checker (`go run
  ./cmd/devtask check-plan-docs --check`, or `TestPlanDocs` in `internal/`) that
  flags prose-only sections, duplicate IDs, and banned lead verbs, and test it
  against a fixture in `testdata/` that violates all three (§2.7). Verify cited
  `Test…` IDs exist *and* read each cited test beside its claim.
- **Mark blocked boxes explicitly** (`(needs docker)`, `(needs go)`), so *"all
  boxes green"* never silently means *"all boxes that could run here"*.

#### 1.1.1 Every task carries its own exit criterion

Build task lists slip even faster than design docs because a specific-sounding
task title says nothing about when it is done:

- **Every leaf task has a measurable `done when`** containing at least one of: a
  backticked command + expected output, an exact number, a `Test…` identifier
  that must pass, or a file path that must exist or be absent. Reject *"works"*,
  *"looks fine"*, *"is clean"*, and *"is correct"*.
- **Credit parent-child tasks once.** Put the `done when` on the leaf where work
  finishes (or on the parent when indivisible), never duplicated on both levels,
  so missing-criterion counts reflect the true gap.
- **Run every `done when` command once before committing it**, and measure how
  many tasks still lack a measurable exit criterion before calling a plan ready.
- **Keep the checker in Go.** Repository automation lives in `./cmd/devtask` (or
  `*_test.go` using Go stdlib `bufio`/`regexp`), never an unpinned Python or AWK
  script in a second runtime.

---

## 2. Write tests first, and keep them real (no mocks where it counts)

*Decisions: `DR-01` (the router the tests drive), `DR-02` (the database they hit).*

Tests are the only mechanism that actually catches the bugs this template cares
about. The rules below are **invariants**, not preferences.

### 2.1 Integration tests run against a real Postgres

- Use a **separate test database**, never the dev database. Use
  `github.com/peterldowns/pgtestdb`: it hashes `migrations/*.sql` (or the
  embedded `db/schema.sql` snapshot under `DR-11 = B`, applied through the exact
  same boot helper production uses) plus optional seed fixtures, builds a
  template database once under a Postgres advisory lock, and clones a fresh
  isolated database per `t.Parallel()` test via `CREATE DATABASE … TEMPLATE` in
  **~10–30 ms**. Do **not** wrap handlers in a single rolled-back transaction to
  fake isolation — that breaks the moment production code calls `pool.Begin(ctx)`
  or relies on commit-time triggers.
- **Exercise the real `http.Handler` through a real request**, without opening a
  listening TCP socket. Every Go router (`chi.Router`, `http.ServeMux`, Huma)
  implements `net/http.Handler`, so `httptest.NewRecorder()` drives the full
  middleware + router + SQL stack in memory:

```go
// internal/requests/requests_integration_test.go
package requests_test

import (
	"net/http"
	"net/http/httptest"
	"testing"
)

func TestOwnerCanReadOwnRequest(t *testing.T) {
	t.Parallel()
	pool := testdb.NewPool(t, "fixtures/actors.sql", "fixtures/requests.sql")
	app := server.NewHandler(pool, server.TestConfig())

	req := httptest.NewRequestWithContext(
		t.Context(),
		http.MethodGet,
		"/api/requests/0192f3c4-0000-7000-8000-000000000001",
		nil,
	)
	req.AddCookie(testauth.SessionCookieFor(t, pool, "alice"))
	rec := httptest.NewRecorder()

	app.ServeHTTP(rec, req)

	if rec.Code != http.StatusOK {
		t.Fatalf("status = %d, want 200; body = %s", rec.Code, rec.Body.String())
	}
}
```

- **Never mock the data-access layer.** Do not introduce `pgxmock`, `sqlmock`,
  SQLite-in-memory stand-ins, or fake `RequestRepository` mocks. A mock cannot
  fail the way Postgres fails: wrong column names, `NULL` scans, trigger
  exceptions (`23503`), partial unique indexes, JSONB containment, and collation
  ordering all live below the mock.
- Prefer **one test per behaviour with a real row** over a wide unit suite over
  a fake. Golden JSON comparisons (`google/go-cmp`) assert *real* handler
  responses, never hand-built structs.

### 2.2 Authorization is tested negatively, per route

- Every route needs a **positive test** *and* a **session-scoping negative
  test**: a real, valid, logged-in session belonging to the *wrong party* for
  that resource, using a real id substitution (IDOR), must be rejected for that
  resource — not merely "no cookie → 401", which proves authentication and not
  authorization.
- The negative test asserts the exact status **and** that **no row changed**.
  Which status to return is a project decision recorded once and kept consistent:
  `404` when the caller must not learn the resource exists (this template's
  default), or `401`/`403` when resource existence is public or existing clients
  already branch on those codes (a port of an existing system preserves the old
  codes until a separate addendum changes them, §20). Always assert the database
  state after a rejected write; status codes alone have let writes through in
  practice:

```go
func TestMalloryCannotInvalidateAlicesRequest(t *testing.T) {
	t.Parallel()
	pool := testdb.NewPool(t, "fixtures/actors.sql", "fixtures/requests.sql")
	app := server.NewHandler(pool, server.TestConfig())

	req := httptest.NewRequestWithContext(
		t.Context(),
		http.MethodDelete,
		"/api/requests/0192f3c4-0000-7000-8000-000000000001",
		nil,
	)
	req.AddCookie(testauth.SessionCookieFor(t, pool, "mallory"))
	rec := httptest.NewRecorder()

	app.ServeHTTP(rec, req)

	if rec.Code != http.StatusNotFound {
		t.Fatalf("status = %d, want 404", rec.Code)
	}
	var stillActive bool
	err := pool.QueryRow(
		t.Context(),
		"SELECT expires_at IS NULL FROM requests WHERE id = $1",
		"0192f3c4-0000-7000-8000-000000000001",
	).Scan(&stillActive)
	if err != nil || !stillActive {
		t.Fatalf("rejected write mutated row (stillActive=%v, err=%v)", stillActive, err)
	}
}
```

- Enforce it structurally: a `TestEveryRouteHasNegativeAuthzTest` meta-test
  walks the router (`chi.Walk`) and asserts every mounted `(method, pattern)`
  outside `/healthz` and `/readyz` has a registered
  `Test*ForbiddenForOtherActor` / IDOR test entry. This is 35 lines of Go and it
  catches the route added on a Friday afternoon.

### 2.3 Same-change rule and the security matrix

- **Add or update tests in the same change as the route, query, or component.**
  A follow-up test ticket is a test that never gets written.
- Keep an **OWASP Top 10 matrix** in `docs/security-matrix.md`: one row per
  endpoint, one column per category, each cell `tested (link)` / `n/a (reason)` /
  `gap (ticket)`. "We thought about it" is not a cell value. Decide this on day
  one; after an audit finds the gaps it is too late to look diligent.
- Frontend unit tests may mock the API boundary. End-to-end tests drive the real
  UI against the real Go backend with **no mocks** (§3).

### 2.4 Go-specific test rules

- **Run with `-race -shuffle=on` everywhere.** Go compiles each package's test
  binary in isolation; `-race` activates ThreadSanitizer and `-shuffle=on`
  randomises test execution order inside each package so hidden ordering
  dependencies fail immediately. Always use Go 1.24+'s `t.Context()` (cancelled
  automatically right before `t.Cleanup` runs).
- **Table tests use `t.Run` subtests**, never bare `for` loops that abort on the
  first `t.Fatal` and hide the remaining broken cases:

```go
func TestFormatBytes(t *testing.T) {
	t.Parallel()
	cases := []struct {
		name  string
		bytes uint64
		want  string
	}{
		{"kilobyte", 1_000, "1 KB"},
		{"megabyte", 1_048_576, "1 MB"},
		{"zero", 0, "0 B"},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			t.Parallel()
			if got := formatBytes(tc.bytes); got != tc.want {
				t.Errorf("formatBytes(%d) = %q, want %q", tc.bytes, got, tc.want)
			}
		})
	}
}
```

- **Property tests (`pgregory.net/rapid`) for invariants that must hold across
  generated inputs** — round-tripping, cursor ordering, idempotency of
  `Invalidate`. Commit failure reproduction files under `testdata/rapid/` to git
  so shrunk counterexamples replay on every future `go test`.
- **Time is injected, never read ambiently.** Pass `Clock` (`type Clock interface
  { Now() time.Time }` or `func() time.Time`) into anything that stamps
  `expires_at` or checks expiry (`time.Now` outside `cmd/` and `platform/clock`
  is banned by `.golangci.yml`, §13). For timer/retry mechanics, use Go 1.25+'s
  deterministic `testing/synctest` (§17.5).
- **A panic in a request path is a test failure, not a 500.** `Recoverer`
  middleware keeps production pods alive, but `server.TestConfig()` sets
  `RePanicInTests: true` so a nil-pointer dereference crashes the offending test
  loudly instead of masquerading as a passing `5xx` assertion.
- **Test black-box behaviour (`package requests_test`) first.** Do not write
  white-box unit tests over 3-line unexported helpers just to pad coverage;
  coverage (`-coverprofile=coverage.out`) is enforced as a **ratchet** (§2.7),
  never a vanity 100% target.

### 2.5 What the assertion must look at

A test that runs broken code and turns green certifies the defect. Settle these
before the first feature:

- **Assert the state that outlives the test**, not only the HTTP response body or
  optimistic UI preview. Read the row back from Postgres (`pool.QueryRow`) or
  fetch it through a second `GET` endpoint — cached views and response DTOs can
  look right while the stored column is wrong.
- **Exercise the path the user takes first.** Where two endpoints reach one
  outcome (e.g. a dedicated `POST /confirm` button and a generic `PATCH`), test
  the route users actually hit first.
- **Visual behaviour is asserted in a real browser** as computed presentation; a
  Go `httptest` handler test cannot see CSS layout or hidden elements.
- **Write the failing end-to-end or integration test before the fix** and watch
  it fail for the expected reason; tests written afterwards unconsciously mirror
  whatever was built.
- **Construct fixtures from typed Go wire structs, never hand-typed JSON
  strings.** Populate `wire.RequestSummary{…}` and marshal via `jsonv2.Marshal`
  so a renamed or tightened field fails `go test -run='^$'` at compile time
  instead of leaving stale JSON literals behind. Run the full gate via a single
  command (`just verify`).

### 2.6 Sabotage every test and watch it fail (the bite check)

A test you have never watched fail is an unverified hypothesis. Whenever a new
test turns green, break the exact production promise it guards — one sabotage at
a time — watch the test turn red, and revert immediately:

- **Record the sabotages in the addendum** for every consequential change
  (*"omitted `expires_at IS NULL` in `GetActiveRequest`; swapped `owner_id` check;
  dropped `reason` from wire response — each turned its named test red"*).
  Writing that sentence surfaces whichever promise still has no test holding it.
- **Run periodic 20–30 mutation sweeps** across a critical package, recording
  surviving mutations as the actual findings list.
- **Use `go-gremlins/gremlins` for mechanical mutation runs**, scoped strictly
  to packages where a weak assertion is an incident (`authn`, `policy.go`,
  billing/money, state transitions) on nightly CI (§17.5) — mutating `String()`
  formatters is noise.
- **Five mutation-harness traps that make sweeps lie:**
  1. A mutant that fails `go build` is **invalid**, never a "survivor" or clean
     pass.
  2. Confirm any lone unexpected result by re-running the owning `go test -run`
     multiple times.
  3. Mutations that only degrade performance (extra allocations, N+1 queries)
     survive functional tests — pin cost promises deterministically with Go's
     stdlib `testing.AllocsPerRun` or a `pgx.QueryTracer` statement counter,
     never flaky wall-clock sleeps.
  4. Sabotage each half of a compound condition (`a || b`, `a && b`) separately.
  5. Restore the tree and verify `git diff --exit-code` after every manual
     sabotage.

### 2.7 Make the suite enforce its own rules

Conventions unchecked by CI decay under deadline pressure:

- **Maintain a pure-Go repo standards checker** (`go run ./cmd/devtask
  check-standards` or `internal/standards_test.go`) for project invariants no
  off-the-shelf linter expresses: package layering (§18.5), "no SQL `DELETE`
  outside retention cleanup", "every `sqlc` table exists in `db/schema.sql`",
  "no user-facing copy inlined outside the copy catalogue". Cite rules by
  append-only ID (`STD-001`, `STD-002`, …); never renumber.
- **Parse Go ASTs (`go/ast`, `go/types`) rather than regexes where possible, and
  prove every rule fails on a fixture.** Regex scanners written for `"double"`
  quotes miss `` `raw backtick` `` or multi-line SQL strings and report clean
  forever. Every `STD-*` rule ships with a violating fixture under
  `testdata/standards/` (covering alternate quoting/multiline/generated shapes)
  that a unit test asserts is flagged, **and** asserts its scanned input paths
  are non-empty so a moved directory never passes vacuously.
- **Make completeness matrices self-enumerating.** Walk `chi.Walk` routes,
  iterate typed `Status`/`Role`/`Event` slices, and fail the build automatically
  when a new route or enum variant has no row in the test/security matrix.
- **Coverage is a ratchet.** Pin per-package floor thresholds (`coverage.ratchet`
  checked against `go tool cover -func=coverage.out`) to today's *measured,
  repeatable* numbers; floors rise in the PR that earns them and may only be
  lowered via a numbered addendum. A ratchet guards structural reach, while §2.6
  guards assertion bite.

### 2.8 Stubs and flakes

- **A stub that always succeeds proves nothing.** For any capability that may be
  absent or degraded in production (an OIDC provider, object store, webhook
  target, SSE stream), test the **unavailable/timeout** case explicitly and keep
  one opt-in flagged test against the genuine dependency whose output a human
  reads.
- **Declare every active stub in multi-stub tests** so a test targeting one
  failure path does not accidentally pass via a second unstubbed fallback.
- **Stubbing `*http.Client` does not stub streaming transports** (WebSockets,
  SSE, gRPC streams); verify which transport the code under test actually opens.
- **A flaky test is an unread bug report — never mask it with test retries.**
  Keep Playwright `retries: 0` (paired with `trace: "retain-on-failure"`, §3)
  and Go test retries at `1`. A poll timing out on a *stable wrong value* means
  an event/write never arrived, not that CI was slow. Always verify the outer
  deadline (`go test -timeout` and `t.Context()`) exceeds any inner wait, and
  assert preconditions up front when an assertion has multiple failure modes.
- **Set timeouts from measurement.** Measure one real iteration, set the timeout
  tightly above it, log progress (*items processed*), and fail fast rather than
  letting a broken loop burn a 10-minute `go test` timeout.

---

## 3. Test infrastructure defaults (isolation, determinism, evidence)

- **Record browser evidence by default.** Playwright video stays on for the
  frontend e2e suite (`E2E_VIDEO=off` switch for local opt-out) with
  `retries: 0` and **`trace: "retain-on-failure"`** (do not use
  `"on-first-retry"` when retries are banned per §2.8, or failures record zero
  traces!). For a `templ` + HTMX frontend (`DR-05 = B`) the exact same
  Playwright suite applies — the browser does not care what rendered the HTML.
- **Isolate hard** (flakes, stubs, and timeouts are §2.8). A separate test
  database; `pgtestdb` per-test cloned databases; unique-per-run identifiers
  (`{label}.{run_id}@example.test`, where `run_id` comes from one place); no
  shared package-global state between tests; `go test -parallel` safe on one
  laptop.
- **Deterministic fixtures.** Named people (`alice`, `bob`, `mallory`), not
  `user-123`, with distinct name pools per role so failures read naturally.
  Store fixtures as plain `.sql` files in `testdata/fixtures/`, reviewed like
  code and versioned alongside the schema that gave them meaning.
- **Freeze the clock and seed randomness.** `clock.Fixed(...)` for business
  time; Go's `math/rand/v2` `rand.New(rand.NewPCG(1, 2))` for generated test
  data (unseeded `math/rand` v1 is banned in `.golangci.yml`); golden snapshot
  helpers fail when `UPDATE_GOLDEN` is unset in CI (`UPDATE_GOLDEN=false`).
- **Layout by type, decided day one:** `cmd/` (entrypoints), `internal/`
  (domain vertical packages + co-located `*_test.go` unit/integration suites),
  `testdata/fixtures/` (SQL), `frontend/e2e/`, `frontend/src/**/*.test.tsx`.
- **Containers for the database, not for the code under test.** Local tests hit
  `docker compose up -d db`; CI hits a Postgres service container. Do **not**
  boot a fresh `testcontainers-go` Postgres container per test — `pgtestdb`
  clones databases in 15 ms on one shared Postgres instance instead of burning
  3 seconds per container boot.
- **Or an embedded real Postgres server, when "one command, no Docker" is
  required.** `github.com/fergusstrange/embedded-postgres` (`v1.34.0`) unpacks a
  real Postgres postmaster binary once per package `TestMain`, with `pgtestdb`
  cloning per-test databases inside it. Decide its four operational constraints
  up front rather than discovering them in CI:
  1. Treat the binary archive as a **pinned build input**: match production's
     Postgres major version (use `>= 18.3.0` on macOS Apple Silicon for native
     universal binaries without Rosetta 2), pre-populate `CachePath` on
     restricted SHIP-HATS runners (configured via `.env.test`), and never fetch
     from Maven Central live during air-gapped CI runs.
  2. Give each package `TestMain` its own `RuntimePath` data directory and a
     dynamically allocated localhost port (`go test ./...` runs multiple package
     test binaries concurrently!).
  3. Embedded Zonky archives ship **vanilla Postgres only** (no `postgis` or
     `pgvector`); if the schema requires non-core extensions, or CI cannot cache
     the archive, use the Docker/service-container path and record a superseding
     addendum.
  4. When migrating off a legacy single-writer in-process DB (SQLite / PGlite),
     catalog and delete serial-file / single-slot workarounds explicitly (§20.6).

---

## 4. Database and data-access discipline (the two-source-of-truth trap)

*Decision: `DR-02`. The card, with code for all three options, is in §0.4 / §12.*

The costliest smell in web backends is carrying one field in three spellings and
writing hand-rolled mapper layers to reconcile them. Go + `sqlc` eliminates that
tax: SQL is `snake_case`, `sqlc` generates idiomatic `PascalCase` Go fields once,
and the wire boundary translates via declarative struct tags — never via mapper
functions.

### 4.1 One casing, one translation, by the compiler

- **`snake_case` in Postgres, `PascalCase` in Go, `camelCase` at the JSON wire
  edge.** Do not maintain parallel `RequestRow`, `RequestModel`, and
  `RequestDTO` structs that copy identical fields back and forth:

```go
// Wire read projection — declarative json tags are the single translation point.
type RequestSummary struct {
	ID        RequestID `json:"id"`
	OwnerID   ActorID   `json:"ownerId"`
	Title     string    `json:"title"`
	CreatedAt time.Time `json:"createdAt"`
}
```

- **No `internal/mappers/` package, no `toDTO()` / `fromEntity()` chains.** One
  struct per direction per endpoint: read queries project directly into the read
  shape (`sqlc`), write endpoints decode into a dedicated write-input struct,
  and both are verified against `db/schema.sql` (`sqlc compile`) and OpenAPI
  (`DR-04`). A constructor conversion (`MoneyFromMinorUnits(cents int64)`) is
  allowed only where a genuine domain invariant or type change occurs, lives
  beside the domain type, and is unit-tested.
- Make the rule mechanical: CI fails on any `internal/mappers` directory, on
  `func toDTO` / `func fromDTO`, and on custom `json:` snake_case overrides
  outside `internal/wire/external/`.
- **Never decode write payloads into a database row struct.** Write bodies use a
  dedicated input struct decoded with Go 1.27's
  `jsonv2.UnmarshalRead(r.Body, &in, jsonv2.RejectUnknownMembers(true))` (or
  Huma `additionalProperties: false`), so a client posting extra `ownerId` or
  `expiresAt` fields gets an immediate `422` instead of a mass-assignment
  vulnerability.

### 4.2 Every table goes through the chosen data layer

- **All SQL lives in the domain package that owns the table**
  (`internal/requests/queries.sql`), never inline in an HTTP handler, never
  assembled via `fmt.Sprintf` or `+` concatenation. The handler parses typed
  inputs and calls a domain function.
- **Compile-time checking is the point.** With `DR-02 = sqlc`, `sqlc compile`
  parses `db/schema.sql` and every `queries.sql` file; a renamed column or wrong
  parameter type fails before `go build` even starts, with **no live database
  required**. Configure `sqlc.yaml` once at the repo root (mapping Postgres
  `uuid` to Go 1.27's stdlib `"uuid"` package):

```yaml
# sqlc.yaml
version: "2"
sql:
  - engine: "postgresql"
    schema: "db/schema.sql"
    queries: "internal/requests/queries.sql"
    gen:
      go:
        package: "requests"
        out: "internal/requests"
        sql_package: "pgx/v5"
        emit_pointers_for_null_types: true
        emit_pointers_for_null_enum_types: true
        overrides:
          - db_type: "uuid"
            nullable: false
            go_type: { import: "uuid", type: "UUID" }
          - db_type: "uuid"
            nullable: true
            go_type: { import: "uuid", type: "UUID", pointer: true }
          - db_type: "timestamptz"
            nullable: false
            go_type: "time.Time"
          - db_type: "timestamptz"
            nullable: true
            go_type: { type: "time.Time", pointer: true }
```

- **Never mix two data layers in one module** (`sqlc` *and* `bun`, or `pgx/v5`
  *and* `database/sql` `lib/pq`). One pool (`*pgxpool.Pool`), one migrator
  (`goose/v3`), one type system.
- **Hand-written `pool.Query` SQL is an explicit escape hatch, not a style.**
  Analytical `COPY` streams or dynamic facet queries that `sqlc` cannot express
  require a numbered addendum explaining why, still use `$1..$n` bind
  parameters, and still live inside `internal/<domain>/`. There is no such thing
  as "temporary" `fmt.Sprintf` SQL.

### 4.3 Soft deletion, enforced by the schema

- Every entity that can be "removed" gets a nullable `expires_at timestamptz`
  from day one, a **partial unique index** over the live rows, and an
  `Invalidate` command — never a SQL `DELETE`:

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

CREATE VIEW active_requests AS
    SELECT id, owner_id, title, created_at
      FROM requests
     WHERE expires_at IS NULL;
```

- **Filter active rows on every read and every authorization check.** A read
  that forgets `expires_at IS NULL` resurrects deleted data, and an
  authorization check that forgets it lets a deactivated membership keep its
  access. Encode the filter once:
  - `sqlc`: read queries select from `active_requests` (note: Postgres catalog
    views do not propagate `NOT NULL` metadata automatically, so mark non-null
    view columns in `sqlc.yaml` `column` overrides when needed);
  - `bob` / `ent` / `bun`: a single `ActiveRequests` scope / mixin used by every
    read.
- **Views are read-only by contract.** `INSERT`, `UPDATE`, and `RETURNING` hit
  the base `requests` table; referencing `active_requests` on an `Invalidate`
  `UPDATE … RETURNING` fails or returns zero rows the instant `expires_at`
  becomes non-null.
- Add an integration test per table asserting that an invalidated row vanishes
  from the list endpoint *and* returns `404` on the detail endpoint — the two
  queries forget independently.

### 4.4 Foreign keys must reject soft-deleted targets

A plain FK proves the row existed once. It does **not** prove the target is
still active, so a deactivated actor can still be assigned as the owner of a
brand-new request. Postgres cannot reference a partial unique index, and a
composite FK smuggling nullable `expires_at` is silently skipped under `MATCH
SIMPLE`. Enforce liveness with a `BEFORE INSERT OR UPDATE` trigger:

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

- **The trigger fires on insert and on owner change** across every path —
  handler, background worker, migration, or `psql` session — while still
  allowing the parent actor to be soft-deleted later (after invalidating live
  relationships).
- **Triggers are invisible to Go types**, so document every trigger in the
  owning package's doc comment and assert in integration tests that inserting
  against an invalidated actor returns `pgconn.PgError` with `Code ==
  pgerrcode.ForeignKeyViolation` (`"23503"`), unwrapped cleanly via Go 1.26's
  `errors.AsType[*pgconn.PgError](err)`.

### 4.5 IDs, time, and actors

- **UUIDv7, minted in exactly one place.** Use Go 1.27's standard-library
  `"uuid"` package (`uuid.NewV7()`, RFC 9562) inside the domain constructor —
  never in an HTTP handler, never in SQL (`gen_random_uuid()` is random v4 and
  fragments B-tree pages). Wrap every entity ID in its own unexported-field
  struct (`type RequestID struct { v uuid.UUID }`, `type ActorID struct { v
  uuid.UUID }`) implementing `MarshalText`/`UnmarshalText` and validating the
  version nibble (`(u[6] >> 4) == 7`) in `ParseRequestID`. Passing `actorID`
  where `requestID` was expected becomes a compile error.
- **Timestamps are UTC `timestamptz` end to end.** Always normalise Go
  `time.Time` with `.UTC()` (`time.Local` is banned by `.golangci.yml`). Never
  store `timestamp` without time zone, and never pass ad-hoc formatted strings
  around domain code.
- **System and non-human actors are real rows**, inserted by seed/migration into
  `actors`, so every `actor_id` is a genuine FK. No `'system'` string literal,
  no nullable `actor_id` meaning "cron did it".
- **Authorization queries join the actor's live membership** (`WHERE
  m.expires_at IS NULL`), never a role string cached inside a session cookie.
  Revoking a membership takes effect on the very next request.

---

## 5. Schema evolution (migrations and wholesale snapshot, same change)

*Decision: `DR-11`. §5.1–§5.2 govern Option A (twin files, once any environment
holds data worth keeping). Option B — for a project with nothing deployed yet —
is §5.3.*

Two halves, always in sync, landed in the same commit. Skipping either produces
the drift this section exists to prevent.

1. **A wholesale snapshot** (`db/schema.sql` plus `db/seed.sql`) that a
   brand-new database applies from zero and that `sqlc.yaml` reads directly.
   Every `CREATE TABLE` lists every current column — never a base schema
   followed by a changelog of `ALTER`s.
2. **A numbered forward-only migration** (`migrations/00007_add_request_priority.sql`)
   that an already-provisioned database applies via `pressly/goose/v3` to catch
   up.

### 5.1 Rules that make the twin workflow real

- **Zero-padded, sequential, immutable.** `00007_…sql` is never edited after
  merge; a fix is `00008_…sql`. Omit `-- +goose Down` sections in production
  migrations — rollbacks in live databases are forward compensating migrations,
  never destructive `DROP` scripts.
- **Do not write manual `BEGIN`/`COMMIT` inside a `goose` migration.** `goose`
  already runs each file inside a transaction. The single explicit exception is
  `-- +goose NO TRANSACTION` on line 1 for `CREATE INDEX CONCURRENTLY`, written
  idempotently (`IF NOT EXISTS`).
- **Idempotent where re-run is possible** (`IF NOT EXISTS`, `ON CONFLICT DO
  NOTHING`) so retried CI setups or partial non-transactional index builds
  converge cleanly.
- **Embed migrations via `//go:embed` and apply under a Postgres lock on boot**,
  plus expose `/app/server migrate` as a standalone CLI subcommand. Use
  `stdlib.OpenDB` from `pgx/v5/stdlib` (explicit, zero blank-import side
  effects) with `lock.NewPostgresSessionLocker()` (or
  `lock.NewPostgresTableLocker()` when connecting exclusively behind
  transaction-mode PgBouncer):

```go
// migrations/embed.go
package migrations

import "embed"

//go:embed *.sql
var FS embed.FS
```

```go
func RunMigrations(ctx context.Context, directDSN string, log *slog.Logger) error {
	connCfg, err := pgx.ParseConfig(directDSN)
	if err != nil {
		return fmt.Errorf("parse migration dsn: %w", err)
	}
	sqlDB := stdlib.OpenDB(*connCfg)
	defer func() { _ = sqlDB.Close() }()
	sqlDB.SetMaxOpenConns(1)

	locker, err := lock.NewPostgresSessionLocker()
	if err != nil {
		return fmt.Errorf("create session locker: %w", err)
	}
	provider, err := goose.NewProvider(
		goose.DialectPostgres,
		sqlDB,
		migrations.FS,
		goose.WithSessionLocker(locker),
		goose.WithSlog(log),
	)
	if err != nil {
		return fmt.Errorf("create goose provider: %w", err)
	}
	_, err = provider.Up(ctx)
	return err
}
```

- **Prove the halves agree, in CI.** Apply `db/schema.sql` to one database and
  run `goose up` from zero on a second database, dump both with `pg_dump
  --schema-only --no-owner`, strip `goose_db_version`, normalise, and `diff`:

```bash
# scripts/check-schema-parity.sh
psql "$SNAPSHOT_URL" -v ON_ERROR_STOP=1 -f db/schema.sql
go run ./cmd/server migrate --database-url "$MIGRATED_URL"
diff -u <(normalise_schema "$SNAPSHOT_URL") <(normalise_schema "$MIGRATED_URL")
```

- **Every schema change = `db/schema.sql` update + `migrations/NNNNN_*.sql` +
  `sqlc generate`**, in the same commit.

### 5.2 Destructive changes are a sequence, not a statement

Renaming or dropping a column breaks pods still running the previous binary
during a rolling deploy. Use expand/contract: add the nullable column and
dual-write in release *n*, backfill in *n+1*, switch `sqlc` reads and add `NOT
NULL` (`NOT VALID` then `VALIDATE CONSTRAINT`) in *n+2*, drop the old column in
*n+3*. Each step has its own migration and its own addendum.

### 5.3 Option B: one snapshot, no migrations (`DR-11 = B`)

Use this while **no** environment holds data worth preserving. §5.1's `goose`
migration rules do not apply; these replace them — and pair cleanly with `sqlc`,
which already compiles directly from `db/schema.sql` offline:

- **One file is the schema.** `db/schema.sql` defines every current table, view,
  trigger, and index, embedded directly into the Go binary (`//go:embed
  schema.sql`) so the binary and its schema can never deploy out of step.
- **Stamp `(version, sha256)` in `schema_state`, and refuse mismatches at boot.**
  Postgres lacks `CREATE TYPE IF NOT EXISTS` for `ENUM`/`DOMAIN`s, and `CREATE
  TABLE IF NOT EXISTS` silently ignores altered column types, new `NOT NULL`
  constraints, or tightened `CHECK` clauses on an already-created table. Do not
  blindly re-execute `db/schema.sql` over an existing database:
  - if `schema_state` is absent (brand-new DB), apply `db/schema.sql` inside a
    Postgres advisory lock and insert `(SchemaVersion, sha256(schemaSQL))`;
  - if `schema_state` matches both `SchemaVersion` and `sha256`, verify expected
    catalog tables exist and continue boot without re-running DDL;
  - if `schema_state` carries an older `version` or a different `sha256`, **exit
    non-zero immediately** with a message naming the exact reset command
    (`just db-reset`). Never "try anyway" against a stale table shape.
- **Separate DDL roles cleanly.** When the runtime DB role lacks `CREATE`
  privileges, the boot gate runs in verify-only mode (checking expected tables +
  `schema_state` match) and logs that DDL was verified rather than applied.
- **Serialise concurrent boots** with a bounded-wait Postgres session advisory
  lock (`pg_try_advisory_lock` retry loop with context deadline) so two replicas
  or parallel test binaries never race initial schema creation.
- **Make Option B un-erodable.** `check-standards` (§2.7) fails CI if a
  `migrations/` directory appears while `DR-11 = B` is active, and fails if
  `sqlc` references any table/column absent from `db/schema.sql` (or vice versa).
  Also keep an integration test that boots twice against the same database (no
  error) and a second test that seeds `(SchemaVersion - 1)` and asserts boot
  refuses with the reset command.
- **Record the exit trigger in the `DR-11` addendum** (e.g. *"the day staging or
  demo holds user-created rows we will not wipe"*). On that day, supersede
  `DR-11` to Option A and copy `db/schema.sql` verbatim as
  `migrations/00001_initial.sql`.

---

## 6. Code conventions that prevent whole classes of bugs

*Decisions: `DR-04` (wire contract), `DR-07` (error shape).*

### 6.1 Typed wire contracts, generated not remembered

Go's compiler catches a renamed struct field everywhere inside `internal/` — and
catches **nothing** across the JSON boundary to a TypeScript frontend unless the
TypeScript client is generated directly from the Go server's contract.

- **The Go types (or OpenAPI / Protobuf spec) are the single source; TypeScript
  types are generated.** With the default `DR-04 = A` (`huma/v2`), handler
  input/output structs generate an OpenAPI 3.1 document directly, and
  `openapi-typescript` generates `schema.ts` for `openapi-fetch`:

```go
type GetRequestInput struct {
	ID string `path:"id" format:"uuid" doc:"Stable UUIDv7 request identifier"`
}

type GetRequestOutput struct {
	Body RequestSummary
}

func RegisterRoutes(api huma.API, d *Deps) {
	huma.Register(api, huma.Operation{
		OperationID: "get-request",
		Method:      http.MethodGet,
		Path:        "/api/requests/{id}",
		Summary:     "Fetch an active request visible to the caller",
		Tags:        []string{"requests"},
	}, d.Requests.GetHandler)
}
```

- **The generated document is committed and double-diffed in CI.** Run
  `go run ./cmd/server dump-openapi > openapi.json` followed by
  `git diff --exit-code openapi.json`, then `npm --prefix frontend run gen:api`
  followed by `git diff --exit-code frontend/src/lib/api/schema.ts`. A Go wire
  change cannot merge without updating the TypeScript client in the same commit.
- **Route registration is checked too.** A Go test compares every path in
  `openapi.json` against `chi.Walk` on the live router (and vice versa),
  catching handlers defined on paper or tested in isolation without ever being
  mounted.
- **Errors have one shape** (`DR-07`): `application/problem+json` per RFC 9457,
  emitted by a single `problem.Write` / Huma error mapper across the entire
  binary. Clients never parse two competing error envelopes.
- **Validation happens once at the boundary** and returns the same RFC 9457
  problem document (`errors[]` field violations). Domain constructors (`§15.1`)
  parse into strong Go types at handler entry; deeper code only checks state
  invariants that require reading Postgres.
- **External contract keys are not yours to rename.** Third-party webhook
  payloads with `user_id` or `PascalCase` keys live exclusively in
  `internal/wire/external/` and convert immediately into domain types; custom
  casing tags are banned everywhere else (§4.1).
- **Idempotency for unsafe retries.** Any `POST` a client or webhook may retry
  takes an `Idempotency-Key` header persisted atomically with a payload SHA-256
  hash and response snapshot inside the write `pgx.Tx` — replaying duplicates
  and rejecting payload mismatches with `409 Conflict`.
- **One definition for any rule evaluated by both Go and a browser/Service
  Worker.** When both the Go server and a Service Worker or client form evaluate
  the same rule (immutable hashed-asset path prefixes, upload MIME/size bounds,
  allowed code alphabets, user-facing validation copy), hand-maintaining two
  copies guarantees silent cache or validation drift. Define the catalogue once
  in Go, emit `frontend/src/lib/generated/rules.ts` via `./cmd/server
  gen-shared-rules` (diff-checked in CI), and run a parity test evaluating both
  sides over the same sampled edge-case inputs (§20.5).

### 6.2 `data-testid` at authoring time

- Every interactive UI element (`button`, `input`, `select`, actionable `a`,
  whether JSX or `.templ`) gets a `data-testid` as it is written using
  `{component-kebab}__{element-role}` (`request-table__row`,
  `request-form__submit`). Repeated rows share one testid; scope by visible
  anchor text first, then by container `data-testid`.
- Testids are a **stable contract** between the component, unit tests, and
  Playwright. Add a lint/test failing when interactive elements omit
  `data-testid`; never select by Tailwind classes or generated DOM IDs.

### 6.3 Copy hygiene

- **Never show internal design decisions to end users.** Architectural rationale
  belongs in `//` Go doc comments and `docs/decisions/`, never in UI labels,
  tooltips, empty states, or error messages. Scrub internal slugs, `DR-` IDs,
  and SQL table/constraint names from shipped copy.
- **Error text is user-facing copy with a separate diagnostic channel.** The RFC
  9457 problem response carries a stable `type` URI, `request_id`, `trace_id`,
  and a safe human sentence; the `pgconn.PgError`, wrapped call stack, and OTel
  span attributes stay strictly in server-side `slog` / trace storage. A client
  must **never** see `ERROR: insert or update on table "requests" violates
  foreign key constraint` on the wire.

---

## 7. Function design and module structure (decide on day one)

*Decisions: `DR-03` (module/package layout), `DR-05` (frontend).*

Retrofitting structural limits onto a 50,000-line Go repo costs weeks. Enforce
every threshold in `.golangci.yml` (§13) from commit one, because a rule backed
by `golangci-lint` survives and a rule in prose erodes.

### 7.1 Size, nesting, parameters

- **≤ 20 lines target per function body, 50 lines / 35 statements hard**
  (`funlen` in `.golangci.yml`).
- **Guard clauses over `else` pyramids** (`nestif` max nesting `3`, `gocognit`
  max `15`, `revive` `early-return` and `superfluous-else`). Handle `if err !=
  nil` and edge conditions at the top and return early so the happy path stays
  flush-left at one tab stop:

```go
func parseWindow(raw string) (Window, error) {
	if raw == "" {
		return DefaultWindow(), nil
	}
	d, err := time.ParseDuration(raw)
	if err != nil || d <= 0 {
		return Window{}, &InvalidWindowError{Raw: raw}
	}
	return Window{Duration: d}, nil
}
```

- **≤ 3 domain parameters** (plus leading `ctx context.Context`, so `revive`
  `argument-limit` is `4`); beyond three, pass a typed parameter struct
  (`SubmitParams`). **No boolean flag parameters** (`revive` `flag-parameter`) —
  `render(w, true)` becomes `renderHTML(w)` and `renderJSON(w)`. **Preserve the
  whole object**: `send(ctx, invoice)` beats five loose primitives that can
  arrive out of order.
- **Naming.** No `*Manager`, `*Service` grab-bags, `*Factory`, `*Helper`, or
  `utils`/`common`/`misc` packages (`revive` `var-naming` flags meaningless
  package names!). Name packages as short lowercase singular/plural domain nouns
  (`requests`, `actors`, `authn`) and **never stutter** (`requests.Summary` and
  `requests.Invalidate`, never `requests.RequestSummary` or
  `requests.InvalidateRequest`). Booleans read `is`/`has`/`should`/`can`.
- **Separate query from modifier.** Methods that compute a value (`Total()
  Money`) do not mutate receiver state; methods that mutate (`ApplyPayment(p
  Payment) error`) return `error` (or a new immutable value), never both a
  mutated receiver and a stale query value in one call.

### 7.2 Errors are typed at the centre and erased at the edge

- **Structured error types and `errors.New` sentinels inside `internal/`, plain
  `fmt.Errorf("…: %w", err)` chains only in `main`, CLI subcommands, and tests.**
  Returning ad-hoc `fmt.Errorf("not found: %s", id)` from domain code forces
  handlers into brittle `strings.Contains(err.Error(), …)` checks. Define domain
  error types (`*NotFoundError`, `*ConflictError`, `*ValidationError`, or a
  closed `*apperr.Error` carrying a `Kind` enum) and unwrap them with Go 1.26's
  compile-checked **`errors.AsType[*apperr.Error](err)`** and `errors.Is`.
- **One `problem.Write` / `ApiError` mapper per binary** converts domain errors
  into RFC 9457 responses, deciding the exact HTTP status and ensuring `404` vs
  `403` never leaks resource existence unintentionally.
- **No `panic`, `must*` helpers, unchecked type assertions (`x.(T)`), or
  unguarded slice indexing (`s[i]`) in request paths**, enforced by `forbidigo`,
  `errcheck` (`check-type-assertions: true`), and `nilaway`.
- Startup in `cmd/server/main.go` before the listener binds is the sole place a
  fatal configuration error exits immediately — and even there, return `error`
  from `run(ctx)` so `defer` cleanup runs cleanly before `os.Exit(1)`.

### 7.3 Dependency injection without a container

- **Concrete types first, small consumer interfaces second, reflection DI
  never.** Do **not** pull in `uber-go/dig`, `samber/do`, or global `var DB
  *pgxpool.Pool`. Assemble a concrete `Deps` / `Server` struct explicitly in
  `cmd/server/main.go` (`run(ctx)`), holding `*pgxpool.Pool`, `Clock`, `Config`,
  and only the genuinely swappable external adapters (`Mailer`).
- **Interfaces earn existence only with ≥ 2 real, non-mock implementations** (or
  to break an import cycle between two peer domains). §2.1 forbids mocking the
  data layer, so exporting `type RequestRepository interface` alongside a single
  Postgres store is Java ceremony in Go clothes — delete the interface and call
  the domain's `Queries` / concrete store directly. When an interface *is*
  earned, define it in the **consuming** package (`1–3` methods) and assert
  compliance with `var _ Mailer = (*SESMailer)(nil)`.
- **Zero mutable globals and zero `func init()`** (`gochecknoinits` enabled in
  §13). Use `sync.OnceValue` only for pure, deterministic lazy compilation (e.g.
  static templates or regexes when `regexp.MustCompile` at package scope isn't
  suitable).
- **Bound CPU-heavy work (`argon2id`, PDF rendering, large compression).** Go's
  M:N runtime preempts goroutines and handles blocking syscalls without Tokio's
  thread-starvation trap, **but** 50 concurrent `argon2id` password hashes (`64
  MiB` each) will OOM the container in 100 ms. Gate CPU/memory-heavy operations
  behind `golang.org/x/sync/semaphore.Weighted` (`Acquire(ctx, 1)`).

### 7.4 Packages: group by domain, split by file (zero re-exports!)

- **Group by domain feature, not by technical layer.** `internal/requests/`
  contains `model.go`, `handlers.go`, `policy.go`, `queries.sql`, and
  `queries.sql.go` — never `internal/controllers/`, `internal/services/`,
  `internal/repositories/`, `internal/models/`. A change to `requests` touches
  one directory.
- **Files ≤ 400 lines typical, 800 lines hard.** Here Go gives you a major
  ergonomic gift over Rust and TypeScript: **every `.go` file in
  `internal/requests/` already shares `package requests`**. Splitting a growing
  `handlers.go` into `handlers_read.go` and `handlers_write.go` requires **zero
  barrel files, zero `pub use` re-exports, and zero caller import changes**!
- **Zero circular dependencies — enforced by `go build`.** The Go compiler
  refuses to compile any package import cycle. Keep the domain DAG unidirectional
  (`requests` may depend on `actors`; `actors` cannot depend on `requests`), and
  enforce layer purity via `internal/arch_test.go` (§18.5).

### 7.5 Frontend: a component renders, a hook decides

Applies to the React frontend (`DR-05 = A`), and by direct analogy to Go
`templ` components (`DR-05 = B`, where a pure Go view-model builder computes all
derived state before invoking `templ.Component` — `.templ` templates must never
query the database, format raw timestamps inline, or run domain branching).

- **Split along the server boundary.** The React component owns layout,
  view-only state, event wiring, and DOM focus. The hook (`lib/hooks/use<Feature>.ts`)
  owns API calls, server-data derivations, and validation.
- **The hook returns a plain object; the component destructures it.** No JSX in
  hooks; no API import in components (`grep -c "lib/api" <Component>.tsx` must
  equal `0`).
- **Hooks live beside `renderHook` tests** and never import from `components/`.
- **Move bodies byte-identically during extraction refactors** before changing
  behaviour.
- **Presentation-only JSX / `.templ` interiors.** No `.filter()`, `.reduce()`,
  `.sort()`, `.find()`, `new Date()`, `.toFixed()`, or `JSON.parse` inside JSX
  return blocks — compute named bindings once above `return (`.

### 7.6 Code smell → remedy

| Smell | Remedy & Go Enforcement |
| --- | --- |
| Long function (> 50 lines) | Extract Function; `funlen` (`lines: 50`, `statements: 35`) |
| Deep nesting (> 3 levels) / `else` after `return` | Guard Clauses; `nestif` + `gocognit` + `revive` (`early-return`, `superfluous-else`) |
| Long parameter list (> 3 + `ctx`) | Parameter Struct (`SubmitParams`); `revive` (`argument-limit: 4`) |
| Boolean flag parameter | Split into two named functions; `revive` (`flag-parameter`) |
| `type RequestRepository interface` with 1 impl | Delete interface; take concrete `*Queries` / `*pgxpool.Pool` (§7.3) |
| `*Manager` / `*Service` / `*Helper` / `pkg/utils` | Rename to domain noun package + verb function (`requests.Invalidate`) |
| Package stutter (`requests.RequestSummary`) | Drop repeated prefix (`requests.Summary`); `revive` (`stuttering`) |
| `toDTO()` / `fromModel()` mapper chains | Single struct per direction + `json:"camelCase"` wire tags (§4.1) |
| `fmt.Sprintf("SELECT … %s", col)` | `sqlc` parameterized query (`$1`); `gosec` `G201`/`G202` |
| Ignored error `_ = f()` or bare `x.(T)` | Propagate `%w` or handle explicitly; `errcheck` (`check-blank`, `check-type-assertions`) |
| `var target *MyErr; errors.As(err, &target)` | Go 1.26 `if target, ok := errors.AsType[*MyErr](err); ok`; `modernize` |
| `panic(...)` or `http.DefaultClient` in handler | Return typed `error`; use timeout `*http.Client`; `forbidigo` + `noctx` |
| `func init()` or mutable `var db *pgxpool.Pool` | Construct explicitly in `cmd/server` `run(ctx)`; `gochecknoinits` |
| God file (> 800 lines) | Split into focused `.go` files in the **same** package directory (§7.4) |
| Duplicated derivation / fat `onChange` in JSX | Explaining variable above `return` or extract to `use<Feature>` hook |
| Speculative generics (`type Store[T any]`) | Delete type parameter until ≥ 2 concrete domain types genuinely share the algorithm |

Sources: Martin Fowler's *Refactoring* (2nd ed.), Google Go Style Guide, Uber Go
Style Guide, and Effective Go.

---

## 8. Validate early and honestly

*Nothing in this section is a decision. The ladder is what makes the other decisions honest.*

### 8.1 The ladder of claims

Each rung proves strictly more than the one above. **Name the rung you actually
reached**; claiming a higher one is how a broken build ships with a green
message.

| Rung | Command | Proves |
| --- | --- | --- |
| 1. Format | `golangci-lint fmt --diff` | `gofumpt` + `goimports` canonical formatting |
| 2. Types | `go build ./... && go test -run='^$' ./...` | Production + test packages compile and type-check |
| 3. Lints | `golangci-lint run ./... && nilaway -include-pkgs="<module>" ./...` | Size, error, context, security, and inter-procedural nil-safety hold |
| 4. Unit | `CGO_ENABLED=1 go test -race -short -shuffle=on ./...` | Pure domain, property (`rapid`), fuzz seed, and `synctest` suites pass race-free |
| 5. Examples | `CGO_ENABLED=1 go test -race -run='^Example' ./...` | `godoc` `Example*()` contracts compile and match `// Output:` |
| 6. Integration | `CGO_ENABLED=1 go test -race -shuffle=on ./...` with `DATABASE_URL` set | Real Postgres (`pgtestdb`), the real schema path (`goose` migrations or `DR-11 = B` snapshot), triggers, and IDOR checks pass |
| 7. E2E | `npx playwright test` against the running binary | Real browser, real Go backend, video recorded |
| 8. Supply chain | `govulncheck ./... && go-licenses check ./... && go mod verify && go mod tidy -diff` | Zero reachable CVEs (deps + stdlib), clean licences, verified checksums |
| 9. Container | `docker build`, run, `/app/server healthcheck` on `:3000/healthz` | The container contract in §10.1 |

Rules:

- **`go build ./...` passing is not "tests pass".** Say "compiled and linted
  (rungs 1–3)" and state plainly what could not run (e.g. no `go` toolchain or
  no Postgres daemon in the current sandbox).
- **Never make CI green by skipping a failing test.** `t.Skip(...)` (outside
  `if testing.Short()` gating real-DB rungs during rung 4) requires an addendum
  and a ticket ID in the skip string (`t.Skip("blocked on 0012; see TICKET-431")`),
  enforced by a `grep` check in CI.
- **The merge gate is the full ladder** — rungs 1 through 9, plus schema parity
  (§5.1) and OpenAPI/TS client diff (§6.1).
- **Append the caveat to commits made under constrained tooling** using a git
  trailer so reviewers see the exact verification boundary in `git log`:

```text
Validation: rungs 1-4 (fmt, build, golangci-lint, nilaway, short unit).
Integration and e2e NOT run: no Postgres service in this sandbox. Run `just verify` before merge.
```

### 8.2 How the Go gates are configured

- **Pin the Go version and patch toolchain in `go.mod`.** Declare both `go 1.27`
  and `toolchain go1.27.3` in `go.mod` (`GOTOOLCHAIN=local` in deterministic
  Docker/CI images built from `golang:1.27.3-*`), and pin codegen CLIs (`sqlc`,
  `goose`, `templ`, `oapi-codegen`) via Go 1.24+ `tool` directives in `go.mod`
  (`go get -tool`).
- **Lint policy lives in one `.golangci.yml` (`version: "2"`).** §13 is the
  single profile. Do not scatter tool flags across shell scripts and IDE settings
  that disagree with CI.
- **`//nolint:<specific-linter> // <reason>` is the only legal suppression.**
  `nolintlint` (`require-specific: true`, `require-explanation: true`,
  `allow-unused: false`) fails CI on bare `//nolint`, unexplained suppressions,
  and stale `//nolint` directives once the underlying code no longer triggers
  the warning!
- **`govulncheck` + `go-licenses` + `go mod tidy -diff` own supply-chain
  policy.** `govulncheck` (`v1.9.0+`) builds the call graph so stdlib advisories
  (like `GO-2026-6809` in `crypto/x509`) and reachable dependency CVEs fail CI
  with near-zero false-positive noise, while `go mod tidy -diff` fails on unused
  dependencies in `go.mod`.
- **`unsafe` is forbidden in application packages** (`depguard` denies `"unsafe"`
  across `cmd/` and `internal/`). Standard-library and vetted driver internals
  may use `unsafe`; our business code never needs it without an addendum and a
  fuzz suite.

### 8.3 Measure the claim; do not assert it

Every statement of the form *"this scales"*, *"this is fast enough"*, or *"this
worker will not starve HTTP traffic"* is an unverified claim until measured:

- **Commit the load script or Go benchmark** (`scripts/load/*.js` for `k6`, or
  `*_bench_test.go` for `benchstat`) so anyone can re-run it when query plans or
  payloads change. Blend new endpoints *into* the realistic read/write traffic
  mix rather than benchmarking an isolated route on an idle pool.
- **Report the tail, never only the median.** Pool exhaustion, GC pacing, and
  lock contention leave `p50` flat while spiking `p99`: record `p50`, `p95`,
  `p99`, and `max`.
- **Measure cold** whenever caches, prepared statements, or OS page caches
  participate, and state in the script header what invalidates the benchmark.
- **Rewrite speed claims require a same-machine, same-session comparison**
  against the old implementation on identical hardware and data — never an
  isolated throughput figure compared against memory of the old system.

### 8.4 Close the class, not the instance

Fixing a bug at the one call site where it surfaced leaves its siblings live. In
the same change, search the entire repository (`git grep`, AST query, or
`sqlc` scan) for every occurrence of the same defect shape, fix them together,
promote the check into `.golangci.yml` or `check-standards` (§2.7) where
mechanizable, and **list the audited sites in the addendum** so reviewers know
the class was closed. Conversely, before deleting code flagged as "unreferenced"
by an audit, search `docs/decisions/` for an accepted ruling keeping it —
*mechanically unreferenced* and *unwanted* are different findings.

---

## 9. Reproducible local dev and the environment story

*Decision: `DR-10` (dev orchestration).*

- **One command from clone to green.** `just bootstrap` checks the Go & Node
  versions, copies `.env.example` to `.env` when absent, starts `docker compose
  up -d db`, applies the schema (`goose` migrations under `DR-11 = A`, or the
  embedded snapshot under `DR-11 = B`) + `db/seed.sql`, and prints the next
  three commands. `just verify` runs the full §8.1 ladder. `just up` runs the
  dev server; `just e2e` runs Playwright with video enabled.
- **`just` is a task list, not a build system.** Keep `justfile` to ~10
  self-documenting recipes (`just --list`). `go run ./cmd/devtask` is the
  typed-Go alternative when automation has non-trivial logic; `make` when the
  organisation mandates Makefiles (`DR-10`). Pick one — never maintain half the
  commands in `Makefile` and half in `scripts/`.
- **One typed `Config` struct, parsed once at startup.** Load defaults +
  environment variables + CLI flags in `internal/platform/config` (`caarlos0/env/v11`)
  and validate every field (`netip.Prefix`, `url.URL`, port bounds, pool sizes)
  via `Validate() error` (`errors.Join`) before opening sockets — failing fast
  at boot with every broken variable named at once.
- **Secrets are an unprintable generic value type.** Wrap passwords, session
  keys, DSNs, and API tokens in `Secret[string]` implementing `fmt.Stringer`,
  `fmt.GoStringer`, `slog.LogValuer`, and `jsonv2.Marshaler` to emit
  `"[REDACTED]"` unconditionally, exposing raw bytes only via `.Expose()`.
- **The env files are a three-file contract, committed as templates only:**
  - `.env.example` — every variable with safe local defaults/placeholders and a
    one-line comment;
  - `.env` — developer's local values, git-ignored;
  - `.env.test` — points strictly at the separate test Postgres instance/DB,
    used by `just verify` and CI.
  Never point dev and test at the same database.
- **Hermetic offline builds work out of the box.** Because `sqlc` (`DR-02 = A`)
  and `templ` (`DR-05 = B`) commit pure generated `.go` files verified against
  `db/schema.sql`, `go build` in Docker and CI **never needs a live database
  connection** (no `.sqlx/` cache files to manage). `sqlc diff` in CI guarantees
  the committed `.sql.go` files match `queries.sql` + `db/schema.sql`.
- **Single-source version declarations.** Go version (`go.mod`), Postgres major
  version (`compose.yaml`), Node version (`.nvmrc` when `DR-05 = A`), and base
  image digests (`Dockerfile`) each have one authoritative home.
- **Egress-restricted agent sandboxes (`go.dev` and `proxy.golang.org`
  blocked).** Inside cloud containers whose outbound SNI allowlist permits only
  `github.com`, `pypi.org`, and `registry.npmjs.org`, install Go 1.27 from the
  `go-bin` PyPI wheel and configure `GOPROXY=direct GOSUMDB=off` per §21.

---

## 10. Deployment and CI/CD from day one: sandbox containers + SHIP-HATS (kept inert)

Decide how the project ships before the first feature, and commit the deployment
files with the first code. Retrofitting a container contract and a government
pipeline onto a finished app surfaces every hidden assumption at once: a server
bound to `127.0.0.1`, proxy headers trusted by hop count, missing CA roots in a
scratch image, `CGO` `libc` mismatches, or a script requiring Bash 5 on macOS.

### 10.1 The container contract (active from day one)

*Decision: `DR-09` (runtime image).*

- **Listen on `0.0.0.0:3000`, with explicit `http.Server` timeouts.** Read `HOST`
  (default `0.0.0.0`) and `PORT` (default `3000`) from the environment, and
  **never** call `http.ListenAndServe` (zero timeouts = Slowloris DoS, flagged
  by `gosec` `G112`):

```go
addr := net.JoinHostPort(cfg.Host, strconv.Itoa(cfg.Port))
srv := &http.Server{
	Addr:              addr,
	Handler:           app,
	ReadHeaderTimeout: 5 * time.Second,
	ReadTimeout:       15 * time.Second,
	WriteTimeout:      30 * time.Second,
	IdleTimeout:       60 * time.Second,
	MaxHeaderBytes:    1 << 20, // 1 MiB
}
```

- **Pure-Go static build (`CGO_ENABLED=0`) with BuildKit module/compiler caches.**
  Unlike C/Rust OpenSSL builds, Go's standard-library TLS (`crypto/tls`, with
  post-quantum `X25519MLKEM768` & `ML-DSA` in Go 1.27) and `pgx/v5` are 100%
  pure Go — requiring **zero shared C libraries** at runtime!
- **Runtime stage on `gcr.io/distroless/static-debian12:nonroot` (~2 MiB),
  numeric `USER 65532:65532`, pinned by digest.** `distroless/static` ships root
  CA certificates, `/usr/share/zoneinfo`, and nonroot passwd entries, with no
  `libc`, no shell, and no package manager. Implement `/app/server healthcheck`
  as a 15-line CLI subcommand so `HEALTHCHECK` needs no `curl`:

```dockerfile
# syntax=docker/dockerfile:1.7
# Pin digests in the real repository; tags shown here for readability.
FROM --platform=$BUILDPLATFORM golang:1.27.3-bookworm AS builder
WORKDIR /src

ARG TARGETOS=linux
ARG TARGETARCH
ARG VERSION=dev

COPY go.mod go.sum ./
RUN --mount=type=cache,target=/go/pkg/mod \
    go mod download && go mod verify

COPY . .
RUN --mount=type=cache,target=/go/pkg/mod \
    --mount=type=cache,target=/root/.cache/go-build \
    CGO_ENABLED=0 GOOS=${TARGETOS} GOARCH=${TARGETARCH} \
    go build -trimpath -buildvcs=false \
      -ldflags="-s -w -X main.version=${VERSION}" \
      -o /out/server ./cmd/server

FROM gcr.io/distroless/static-debian12:nonroot
COPY --from=builder /out/server /app/server
ENV HOST=0.0.0.0 PORT=3000
EXPOSE 3000
USER 65532:65532
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD ["/app/server", "healthcheck", "--url", "http://127.0.0.1:3000/healthz"]
ENTRYPOINT ["/app/server"]
```

- `//go:embed *.sql` (`§5.1`) embeds `goose` migrations inside `/app/server`, so
  no SQL directory copy is required in the runtime image.
- **`.dockerignore`** excludes `.git/`, `.env*`, `bin/`, `coverage.out`,
  `frontend/node_modules/`, and `testdata/`. It must **not** exclude
  `viper-agent/` or any platform-supplied directory.
- **`Dockerfile.dev`** preserves the cloud sandbox VIPER contract (`COPY
  viper-agent/`, `/viper-agent/entrypoint.sh`, UID `1001`, `PORT=3000` external
  proxy → `VIPER_APP_PORT=3001` app → `VIPER_AGENT_PORT=9111` agent), installs
  the pinned `go1.27.3` toolchain + `air` (`github.com/air-verse/air`) alongside
  Node/Playwright, binds `HOST=0.0.0.0`, and mounts `GOMODCACHE` + `GOCACHE`
  volumes so incremental Go rebuilds finish in `< 400 ms`.
- **`Dockerfile.cloudflared`** pins the `cloudflared` release digest, runs with
  `--no-autoupdate`, accepts `TUNNEL_TOKEN` at runtime only, and forwards to
  port `3000`.

#### Trust the proxy by address, never by hop count

Believe `X-Forwarded-For` / `X-Forwarded-Proto` **only** when `r.RemoteAddr`
belongs to `TRUSTED_PROXY_CIDRS` (`[]netip.Prefix`), then walk backwards and
select the **rightmost hop that is not itself a trusted proxy** (preventing both
client IP spoofing on the left and proxy-chain length fragility):

```go
package httpx

import (
	"net/http"
	"net/netip"
	"strings"
)

func ClientIP(h http.Header, peer netip.Addr, trusted []netip.Prefix) netip.Addr {
	if !inPrefixes(peer, trusted) {
		return peer // Untrusted direct peer: ignore X-Forwarded-For completely
	}
	vals := h.Values("X-Forwarded-For")
	for i := len(vals) - 1; i >= 0; i-- {
		parts := strings.Split(vals[i], ",")
		for j := len(parts) - 1; j >= 0; j-- {
			hop, err := netip.ParseAddr(strings.TrimSpace(parts[j]))
			if err != nil {
				continue
			}
			if !inPrefixes(hop, trusted) {
				return hop
			}
		}
	}
	return peer
}

func inPrefixes(ip netip.Addr, prefixes []netip.Prefix) bool {
	for _, p := range prefixes {
		if p.Contains(ip) {
			return true
		}
	}
	return false
}
```

Unit-test `ClientIP` with a table: untrusted public peer + spoofed header,
trusted ingress + spoofed leftmost hop, all-trusted internal hops, IPv6 mapped
addresses, and malformed tokens. Lint Dockerfiles with `hadolint` and smoke-test
the built container in CI on `:3000/healthz`.

### 10.2 SHIP-HATS: what the platform requires (research, October 2026)

SHIP-HATS is GovTech's CI/CD platform in the Singapore Government Tech Stack.
Findings below come from public SHIP-HATS documentation; internal GitLab
templates require TechPass + SEED.

- **Platform.** GitLab Dedicated at `sgts.gitlab-dedicated.com` (Ultimate),
  paired with SonarQube, Nexus Repository Pro, Nexus IQ (SCA), Fortify on Demand
  (SAST/DAST), Jira, and Confluence (up to CONFIDENTIAL CLOUD-ELIGIBLE /
  SENSITIVE-NORMAL).
- **Templates.** `include:` `innersource/sgts/ship-hats/ship-hats-templates`
  pinned to a literal release tag (`v1.1.12` as of September 2026, mandatory
  after Rekor's decommissioning on 30 September 2026). Consume hidden jobs via
  `extends`: `.build-and-push-docker-image` (Kaniko),
  `.copy-docker-image-from-one-remote-registry-to-another`,
  `.generate-gitlab-attestation`, `.sign-container`, `.verify-container`,
  `.trivy-scan`, `.nexus-iq-scan`, `.sonarqube-scan`,
  `.invoke-awscli-commands-with-assumerole` (OIDC).
- **Immutable stage & job names:** `.pre`, `build`, `test`, `static-test`,
  `sign`, `runtime-test`, deploy stages; never rename `build-job` or
  `deploy-prod-manual-job` / `deploy-final-job`.
- **WOG Pipeline Execution Policy** (mandatory since March 2026; legacy
  compliance pipelines ended 30 June 2026): policy jobs never read repo YAML
  variables, so set `CF_LEVEL` (1–4, default 4), `SONAR_PROJECTKEY`,
  `SONAR_TOKEN`, `NEXUS_IQ_APP_ID`, `NEXUS_IQ_USERNAME`/`PASSWORD`,
  `COSIGN_PASSWORD`, and `FOD_PAT` in GitLab project/group CI/CD settings.
- **Runners & 2-hour job cap:** CStack Kubernetes default (`UID 65533`, 4 vCPU /
  8 GB, no image builds), `ship_docker` (`_med`/`_large`/`_arm`, root
  non-privileged → **Kaniko**, never Docker-in-Docker), and pilot GitLab-hosted
  VMs. Go's fast compilation + cached `GOMODCACHE`/`GOCACHE` stays comfortably
  under the 2-hour runner cap.
- **Supply chain & October/November 2026 enforcement dates:**
  - Pull container bases and packages via Nexus (`nexus-docker.ship.gov.sg`, …).
  - Since **3 June 2026**, Nexus IQ **fails components younger than 7 days** and
    integrity-rating violations.
  - From **1 November 2026**, SHIP-HATS Docker runners **block EOL and
    blocklisted images**.
  - Pin scanner images (Trivy `>= 0.69.3`); Nexus purges unused artefacts at 180
    days; since **16 October 2026**, Git over HTTPS requires PAT (`<= 180` day
    expiry) or SSH key.

**Go specifics on SHIP-HATS:**
- **Nexus Go Module Proxy (`GOPROXY`) vs `go mod vendor`:** Sonatype Nexus
  Repository Pro supports Go module proxy repositories (`go-proxy`). Set CI
  environment variables using `@@SHIPHATS_*@@` placeholders until activation,
  and ensure internal government module prefixes **never** query Google's public
  `proxy.golang.org` or `sum.golang.org`:

```yaml
# .gitlab/ci/go.gitlab-ci.yml.shiphats excerpt
variables:
  GOPROXY: "https://@@SHIPHATS_NEXUS_GO_PROXY@@,off"
  GOPRIVATE: "@@SHIPHATS_GOPRIVATE_GLOB@@"      # e.g. sg.gov.*,*.ship.gov.sg
  GONOSUMDB: "@@SHIPHATS_GOPRIVATE_GLOB@@"
  GOFLAGS: "-mod=readonly"
```

  If a specific agency tenancy has not enabled a Nexus `go-proxy` endpoint and
  blocks egress to `proxy.golang.org`, run `go mod vendor`, commit `vendor/`,
  and switch `GOFLAGS="-mod=vendor"` (recorded as an addendum).
- **Enforcing the 7-day publish-age gate locally & in CI:** Unlike `pnpm`
  (`minimumReleaseAge`) or Cargo `1.100` (`global-min-publish-age`), Go `1.27`
  has no `go.mod` minimum-age directive. Enforce it deterministically in
  `scripts/check-module-age.sh` by inspecting `.Time` from `go list -m -json all`
  (which reads module `.info` timestamps from the proxy) and failing any direct
  or indirect module version published `< 7 days` ago unless allowlisted for an
  active `govulncheck` security advisory!
- **AWS Fargate / CStack runtime sizing:** Go `1.25+` automatically detects
  Linux cgroup CPU limits and sets `GOMAXPROCS` dynamically (do **not** import
  `go.uber.org/automaxprocs`). Always set `GOMEMLIMIT` to `~85%` of container
  memory (e.g. `GOMEMLIMIT=1740MiB` on a 2 GiB task) so Go's Green Tea GC paces
  heap growth before Linux OOM-kills the container.

### 10.3 The discipline: SHIP-HATS files from day one, kept inert

- Carry all five SHIP-HATS artefacts from commit one with a `.shiphats` suffix:
  - `.gitlab-ci.yml.shiphats`
  - `.gitlab/ci/*.gitlab-ci.yml.shiphats`
  - `sonar-project.properties.shiphats`
  - `.gitlab/CODEOWNERS.shiphats`
  - `.gitlab/merge_request_templates/Default.md.shiphats`
- Use `@@SHIPHATS_<NAME>@@` placeholders (never secrets) and provide the Bash
  3.2 `activate-shiphats.sh` activator (`--non-interactive`, `--force`,
  `--keep-inert`).
- **Go SHIP-HATS pipeline stage mapping** (mirroring `just verify` identically):
  - `static-test`: `golangci-lint fmt --diff`, `golangci-lint run ./...`,
    `nilaway ./...`, `govulncheck ./...`, `go-licenses check`, `go mod tidy -diff`,
    `scripts/check-module-age.sh`, `scripts/check-decisions.sh`;
  - `test`: `CGO_ENABLED=1 go test -race -shuffle=on -coverprofile=coverage.out
    -json ./... > test-report.json` against a Postgres service container +
    `scripts/check-schema-parity.sh` + `sqlc diff`, feeding SonarQube via
    `sonar.go.coverage.reportPaths=coverage.out` and
    `sonar.go.tests.reportPaths=test-report.json` (with `sonar.exclusions`
    skipping `**/*_test.go`, `**/*.sql.go`, `**/*_templ.go`, `**/*.gen.go`);
  - `build`: Kaniko multi-stage `CGO_ENABLED=0` image build + `:3000/healthz`
    container smoke check;
  - `runtime-test`: Playwright e2e with video against the built image.
- Cache `GOMODCACHE` (`.cache/go-mod`) and `GOCACHE` (`.cache/go-build`) keyed
  on `go.sum`, test `activate-shiphats.sh` into a `t.TempDir()` scratch folder,
  and validate rendered YAML with `check-jsonschema --builtin-schema
  vendor.gitlab-ci`.

### 10.4 Root scripts run everywhere

Root shell scripts (`dev.sh`, `activate-shiphats.sh`, `scripts/*.sh`) must run
on macOS's `/bin/bash` **Bash 3.2**:

- no `declare -A` associative arrays, `mapfile`/`readarray`, or `${var,,}`;
- expand possibly-empty arrays under `set -euo pipefail` as
  `${arr[@]+"${arr[@]}"}`;
- lint every script in CI with `shellcheck`.

---

## 11. What to decide before writing the first feature (checklist)

1. **Run the decision interview** (`DR-01`…`DR-03` before `cmd/` or `internal/`;
   `DR-04`…`DR-11` before the area they govern, with `DR-11` before the first
   table), recording each as `docs/decisions/NNNN-*.md`.
2. Living spec path, sequential addenda numbering, and `scripts/check-decisions.sh`
   wired into CI.
3. Toolchain pinned in `go.mod` (`go 1.27`, `toolchain go1.27.3`, `tool`
   directives), `.golangci.yml` `version: "2"`, `gofumpt` + `goimports` active.
4. Per-test real-Postgres isolation via `pgtestdb` (`CREATE DATABASE … TEMPLATE`)
   and explicit "never mock the data layer" rule.
5. One IDOR negative test per route asserting exact recorded status (`404`
   default, or `401`/`403` by recorded decision) **and** unchanged DB row +
   router meta-test + `docs/security-matrix.md`.
6. Single data-access layer (`sqlc` + `pgx/v5`), zero `internal/mappers`,
   `active_*` filtering on every read and authorization query.
7. Soft delete (`expires_at`) + partial unique indexes + `assert_*_is_active()`
   PL/pgSQL `23503` triggers + Go 1.27 `uuid.NewV7()` ID structs + real system
   actor rows.
8. Schema (`DR-11`): either twin `db/schema.sql` + `migrations/NNNNN_*.sql` per
   change, `pg_dump` parity script in CI, advisory-locked `goose` boot migration
   + `server migrate` CLI; or a single embedded `db/schema.sql` with a
   `schema_state(version, sha256)` boot gate refusing mismatches, a boot-twice
   test, a check banning `migrations/`, and a written trigger for moving B → A.
9. Generated wire contract (`openapi.json` + `schema.ts`) committed and diffed,
   route-registration parity test, single RFC 9457 error writer, `Idempotency-Key`
   on retryable `POST`s.
10. `data-testid` authoring convention, hook/component split, pure JSX/`.templ`
    interiors.
11. Test layout by type, Playwright video on by default (`E2E_VIDEO=off` switch,
    `retries: 0`, `trace: "retain-on-failure"`), named SQL fixtures, injected
    `Clock`, seeded `math/rand/v2` `PCG`.
12. §8.1 9-rung validation ladder named honestly in every report, `Validation:`
    commit trailer on constrained runs, no unreasoned `t.Skip`.
13. One-command `just bootstrap` / `just verify`, three-file `.env` contract,
    `Secret[T]` redaction, offline `go build`.
14. Container contract (`0.0.0.0:3000`, `http.Server` timeouts, `CGO_ENABLED=0`
    `distroless/static:nonroot`, `USER 65532:65532`, `/app/server healthcheck`),
    `netip.Prefix` CIDR proxy trust, `hadolint`, CI container smoke test.
15. Inert `*.shiphats` files + Bash 3.2 `activate-shiphats.sh` + scratch-dir
    activation test + `check-jsonschema`.
16. Supply chain: `govulncheck`, `go-licenses`, `go mod tidy -diff`, and 7-day
    module publish-age check (`scripts/check-module-age.sh`).
17. §13 strictness profile committed (`go.mod`, `.golangci.yml` v2, `nilaway`)
    with a test asserting `.golangci.yml` validates cleanly.
18. §14 Go signature & type rules agreed (value vs pointer, no `Get` prefix, no
    stutter, unexported fields + `IsZero()`, `PatchField[T]` for `PATCH`,
    `slog.LogValuer`).
19. §15 pattern bounds agreed: unexported-field structs for Parse-Don't-Validate
    everywhere, typestate reserved strictly for linear sequences, `Outcome[T]`
    for post-commit write-then-publish obligations.
20. §16 concurrency & telemetry invariants: `errgroup` / `WaitGroup.Go`
    ownership, outbound `*http.Client` timeouts, `semaphore.Weighted` on
    `argon2id`, OTel `v1.47` flushed before `pool.Close()`, `r.Pattern` RED
    metrics.
21. §17 baselines: `-trimpath -ldflags="-s -w"` build flags, `GOMEMLIMIT` set,
    one `b.Loop()` benchmark with `benchstat` noise budget, and nightly
    fuzz/`synctest`/`gremlins` jobs scheduled.
22. §2.5–§2.8 test discipline: assertions read persisted DB state, consequential
    addenda record manual bite-check sabotages, `check-standards` is proven to
    fail on fixtures, and `coverage.out` floors act as a ratchet.
23. §18 package dependency DAG checked by `internal/arch_test.go` (proven to
    fail on a cycle/layer fixture), with shared vocabulary isolated in a
    stdlib-only `internal/kernel/` leaf package from day one.
24. Porting an existing system only: §20 — live legacy oracle, 3-bucket
    mechanical test classification, exported golden fixtures, Go determinism
    hazard table, divergence log, and a twin-DB shadow harness proven to fail on
    mutated responses.
25. §1.1 two-cut plans and specs: multi-task design sections carry `Verify / do`
    boxes (`id`, action, path/command, measurable `done when`), survey counts
    carry re-check commands, and `check-plan-docs` is proven to fail on a
    fixture.

Answer these twenty-five up front and a greenfield Go project avoids the silent
drift, nil panics, leaked goroutines, and mid-project rewrites this template
exists to prevent. (Items 1–21 preserve the original numbering; 22–25 were
appended.)

---

## 12. Decision cards

Copy the card verbatim when asking the user (§0.3–§0.4). Every card has all five
parts per option and ends with a single recommendation. `DR-02` is in §0.4; the
remaining ten are below, in interview order.

### `DR-01` · HTTP router — batch 1

```text
DR-01 · HTTP router — question 1 of batch 1

Which HTTP router should serve the API and attach middleware?

A. go-chi/chi/v5 (v5.3.2) — 100% net/http compatible with scoped middleware groups
   Real example:
       r := chi.NewRouter()
       r.Use(httpx.RequestID, httpx.OTelMiddleware, httpx.Recoverer)
       r.Route("/api/requests", func(r chi.Router) {
           r.Use(authn.RequireSession(sessions))
           r.Get("/{id}", reqHandlers.Get)
           r.Post("/", reqHandlers.Create)
       })
   Pros:  every handler is plain `http.HandlerFunc` and every middleware is
          `func(http.Handler) http.Handler`; `r.Route` / `r.Group` scopes auth
          and rate-limit middleware cleanly without sub-mux prefix stripping;
          `chi.Walk` inspects the full route tree for §2.2's IDOR coverage test;
          zero external transitive dependencies.
   Costs: one small third-party dependency over stdlib (`~1,500` LOC).
   Choose if: you want standard `net/http` handlers with ergonomic route groups
          and route-tree introspection.

B. Standard library net/http.ServeMux (Go 1.22+ method + wildcard routing)
   Real example:
       mux := http.NewServeMux()
       authed := authn.RequireSession(sessions)
       mux.Handle("GET /api/requests/{id}", authed(http.HandlerFunc(reqHandlers.Get)))
       mux.Handle("POST /api/requests", authed(http.HandlerFunc(reqHandlers.Create)))
   Pros:  zero dependencies; `r.PathValue("id")` and `r.Pattern` are built into
          `net/http.Request`; guaranteed compatibility for the life of Go 1.
   Costs: no built-in route grouping (`r.Group`) or middleware stacking helper,
          and no built-in `Walk` API to enumerate registered routes for §2.2
          without wrapping `Handle` in a custom registry struct.
   Choose if: the service has < 15 routes and you want a pure-stdlib HTTP edge.

C. labstack/echo/v4 — custom echo.Context framework
   Real example:
       e := echo.New()
       g := e.Group("/api/requests", authn.RequireEchoSession(sessions))
       g.GET("/:id", func(c echo.Context) error {
           return reqHandlers.GetEcho(c)
       })
   Pros:  handlers return `error` directly into a central `HTTPErrorHandler`;
          batteries-included binding and middleware helpers.
   Costs: `func(echo.Context) error` is incompatible with standard `http.Handler`
          middleware (`scs/v2`, Go 1.25 `http.CrossOriginProtection`, `otelhttp`)
          without `echo.WrapMiddleware` adapters (§0.8).
   Choose if: your team already standardises on Echo across existing services.

Recommendation: A — `chi/v5` keeps 100% standard `net/http` types while giving
route-group middleware scoping and `chi.Walk` for §2.2's security test.
Reply A/B/C, or "all recommendations".
```

### `DR-02` · Data access layer — batch 1

Use the full card in §0.4 (`sqlc` + `pgx/v5` · `bob` + `pgx/v5` · `ent` / `bun`;
recommends `sqlc` + `pgx/v5`).

### `DR-03` · Module and package layout — batch 1

```text
DR-03 · Module and package layout — question 3 of batch 1

How should the Go repository be structured?

A. Single go.mod with domain-vertical internal/ packages
   Real example:
       go.mod
       cmd/server/main.go
       internal/
         requests/       # model.go, handlers.go, policy.go, queries.sql, queries.sql.go
         actors/         # model.go, queries.sql, queries.sql.go
         authn/          # session.go, middleware.go
         platform/       # config/, httpx/, telemetry/, clock/
   Pros:  one `go.mod`/`go.sum` to pin and audit; Go compiles each package in
          parallel and caches untouched packages in `GOCACHE`; `internal/` is
          compiler-enforced visibility; adding a feature touches one folder.
   Costs: cross-domain boundaries rely on Go's acyclic import rule plus a short
          `internal/arch_test.go` test (§18.5) so peer domains don't tangle.
   Choose if: you are building one deployable service (plus CLI/worker entrypoints
          under `cmd/`) — the right shape for > 90% of Go services.

B. Single go.mod with technical-layer packages
   Real example:
       internal/
         handlers/       # requests_handler.go, actors_handler.go
         services/       # requests_service.go, actors_service.go
         repositories/   # requests_repo.go, actors_repo.go
         models/         # request.go, actor.go
   Pros:  familiar to engineers arriving from Spring Boot or NestJS.
   Costs: every feature edits four directories; `models/` quickly becomes a
          shared grab-bag; invites unnecessary interface + mapper ceremony that
          fights §4.1 and §7.3.
   Choose if: organisational convention mandates horizontal MVC folders.

C. Multi-module go.work workspace (`services/api/go.mod`, `libs/*/go.mod`)
   Real example:
       go.work           # go 1.27; use ( ./services/api ./services/worker ./libs/telemetry )
       services/api/go.mod
       services/worker/go.mod
       libs/telemetry/go.mod
   Pros:  hard `go.mod` dependency firewalls between independently versioned
          binaries or publishable internal SDKs.
   Costs: `go.work` must be synced or excluded carefully in CI/Docker; tagging
          interdependent modules requires coordinated pseudo-versions; overkill
          when all binaries deploy from one repo.
   Choose if: two binaries in this repo have genuinely disjoint heavy dependency
          trees and independent release cadences.

Recommendation: A — Go already compiles per-package in milliseconds; one
`go.mod` with domain-vertical `internal/<domain>/` packages gives maximum speed
and cohesion with zero workspace friction.
Reply A/B/C, or "all recommendations".
```

### `DR-04` · Wire contract — batch 2

```text
DR-04 · Wire contract and client generation — question 1 of batch 2

How should the Go backend and TypeScript client stay in sync?

A. danielgtaylor/huma/v2 (v2.39.1) → OpenAPI 3.1 → openapi-typescript + openapi-fetch
   Real example:
       type CreateRequestInput struct {
           Body struct {
               Title string `json:"title" minLength:"1" maxLength:"200"`
           }
       }
       huma.Register(api, huma.Operation{
           OperationID: "create-request",
           Method:      http.MethodPost,
           Path:        "/api/requests",
       }, h.Create)
       // TS caller: const { data, error } = await api.POST("/api/requests", { body });
   Pros:  Go structs are the single source of truth; emits OpenAPI 3.1 + native
          RFC 9457 `application/problem+json` errors automatically; mounts right
          onto `chi/v5` (`humachi`) or `ServeMux` (`humago`); zero drift when
          `openapi.json` and `schema.ts` are diff-checked in CI (§6.1).
   Costs: handler signatures follow Huma's `func(context.Context, *In) (*Out, error)`
          convention; struct tags drive schema constraints.
   Choose if: Go owns the API and you want zero-ceremony OpenAPI 3.1 + RFC 9457.

B. Spec-first OpenAPI 3.0/3.1 → oapi-codegen/v2 (v2.8.0 `strict-server`) + openapi-typescript
   Real example:
       # api/openapi.yaml edited by hand; generates StrictServerInterface:
       func (h *Handler) CreateRequest(
           ctx context.Context, req gen.CreateRequestRequestObject,
       ) (gen.CreateRequestResponseObject, error) { … }
   Pros:  contract is reviewed in YAML before Go or TS code is written; ideal
          when external teams or API gateways co-own the OpenAPI spec.
   Costs: YAML authoring verbosity; OpenAPI 3.1 edge cases in `oapi-codegen` lag
          OpenAPI 3.0.3 slightly; every endpoint requires editing YAML, running
          codegen, then implementing the generated interface.
   Choose if: an external API governance group signs off on `openapi.yaml` first.

C. Protobuf + Buf + connectrpc.com/connect (v1.21 / v2) (`@connectrpc/connect-web`)
   Real example:
       // proto/requests/v1/requests.proto -> buf generate
       mux.Handle(requestsv1connect.NewRequestServiceHandler(svc))
       // Speaks Connect JSON/proto over HTTP/1.1 & HTTP/2 AND standard gRPC!
   Pros:  strongest cross-language schema evolution rules (`buf breaking` in CI);
          one handler serves browser `fetch` JSON and service-to-service gRPC.
   Costs: Protobuf toolchain (`buf`), proto-to-domain conversion structs, and
          Connect's own error envelope instead of RFC 9457 (§0.8).
   Choose if: the same API serves both a browser SPA and internal gRPC clients.

Recommendation: A — `huma/v2` + `openapi-typescript` keeps Go structs as the one
source of truth and emits OpenAPI 3.1 + RFC 9457 out of the box.
Reply A/B/C, or "all recommendations".
```

### `DR-05` · Frontend — batch 2

```text
DR-05 · Frontend architecture — question 2 of batch 2

What renders the UI?

A. React 19 + Vite + TypeScript (embedded into the Go binary via `//go:embed`)
   Real example:
       // internal/ui/assets.go
       //go:embed all:dist
       var DistFS embed.FS

       const { data, isPending } = useQuery({
         queryKey: ["requests", id],
         queryFn: () => api.GET("/api/requests/{id}", { params: { path: { id } } }),
       });
   Pros:  richest component ecosystem for complex interactive tables, optimistic
          updates, and client state; compiles into static assets served from one
          Go binary in production.
   Costs: two toolchains (`go` + `node`), two lint/test runners, and §6.1's
          OpenAPI codegen pipeline.
   Choose if: the UI has rich client-side state (drag-and-drop, complex wizards,
          dense interactive data grids).

B. Server-rendered Go with `a-h/templ` (v0.3.1070) + HTMX 2
   Real example:
       templ RequestRow(r requests.Summary) {
           <tr id={ "req-" + r.ID.String() } data-testid="request-table__row">
               <td>{ r.Title }</td>
               <td>
                   <button hx-delete={ "/ui/requests/" + r.ID.String() }
                           hx-target="closest tr" hx-swap="outerHTML"
                           data-testid="request-row__archive">Archive</button>
               </td>
           </tr>
       }
   Pros:  one language (`go`), compile-time type-checked HTML templates with
          automatic XSS contextual escaping, no client state cache to drift from
          Postgres, no Node runtime required to build the UI (`templ generate`).
   Costs: committed `*_templ.go` files; rich offline/canvas interactions still
          need focused JS islands; progressive enhancement discipline required.
   Choose if: the app is CRUD, workflows, queues, and forms, and the team wants
          an all-Go stack.

C. Standard library `html/template` + HTMX 2 (zero template codegen)
   Real example:
       //go:embed templates/*.html
       var tplFS embed.FS
       // Executed into a bytes.Buffer first so template errors never half-write 200 OK
   Pros:  zero external dependencies or codegen; stdlib contextual auto-escaping.
   Costs: template field typos (`{{ .Titl }}`) fail at test/runtime rather than
          compile time unless every template has a rendering unit test.
   Choose if: the UI is minimal (a few admin/login pages) and zero codegen wins.

Recommendation: A when interactive client state dominates; B (`templ` + HTMX)
when server-driven workflows and forms dominate — pick explicitly against your UI.
Reply A/B/C, or "all recommendations".
```

### `DR-06` · Authentication — batch 2

```text
DR-06 · Authentication — question 3 of batch 2

How are callers authenticated?

A. Opaque server-side sessions in Postgres (`alexedwards/scs/v2` + `pgxstore`) + stdlib CSRF
   Real example:
       sm := scs.New()
       sm.Store = pgxstore.New(pool)
       sm.Lifetime = 8 * time.Hour
       sm.Cookie.HttpOnly = true
       sm.Cookie.Secure = true
       sm.Cookie.SameSite = http.SameSiteLaxMode
       cop := http.NewCrossOriginProtection() // Go 1.25 stdlib Sec-Fetch-Site + Origin CSRF!
       handler := cop.Handler(sm.LoadAndSave(router))
   Pros:  instant server-side session revocation (`sm.RenewToken(ctx)` on login
          prevents fixation); no token in `localStorage`; Go 1.25's built-in
          `http.CrossOriginProtection` blocks cross-origin state-changing requests
          with zero double-submit CSRF token ceremony; fits §4.5 live-membership joins.
   Costs: one indexed `sessions` lookup per request (< 0.4 ms on local network);
          cookies require credentialed requests on same-site origins.
   Choose if: first-party browser app (SPA or HTMX) talking to this Go backend.

B. Short-lived asymmetric JWT (`EdDSA`, `<= 5 min`) + rotating Postgres refresh token
   Real example:
       tok, err := jwt.ParseWithClaims(bearer, &Claims{}, keyFunc,
           jwt.WithValidMethods([]string{"EdDSA"}), // prevents alg:none / HMAC confusion
           jwt.WithIssuer(cfg.JWTIssuer),
           jwt.WithAudience(cfg.JWTAudience),
           jwt.WithExpirationRequired(),
       )
   Pros:  non-browser CLI/service callers authenticate with `Authorization: Bearer`
          without cookies; resource servers verify signatures locally.
   Costs: revocation lags until access-token expiry unless paired with a deny-list;
          refresh-token rotation + reuse detection adds tables anyway; **never**
          trust role claims inside the JWT for §4.5 resource authorization.
   Choose if: mobile apps, CLIs, or multiple resource services consume one token.

C. OpenID Connect Authorization Code + PKCE (`coreos/go-oidc/v3` + `x/oauth2`), establishing A
   Real example:
       verifier := oauth2.GenerateVerifier() // RFC 7636 S256 PKCE built into x/oauth2
       authURL := oauthCfg.AuthCodeURL(state, oauth2.S256ChallengeOption(verifier))
       // Callback verifies ID token nonce + signature via oidc.IDTokenVerifier,
       // upserts actor row, calls sm.RenewToken(ctx), and sets session from A.
   Pros:  delegates passwords, MFA, and Singpass / TechPass / CorpPass federation
          to the IdP while keeping instant local session revocation via A.
   Costs: local dev needs a mock OIDC issuer (e.g. `oauth2-proxy/mockoidc` in
          tests); callback `state`, `nonce`, and PKCE verifier cookies must be tested.
   Choose if: enterprise/government SSO is in scope now or before launch.

Recommendation: A for first-party web apps, paired with C the moment corporate
or government SSO (TechPass / Singpass) is on the roadmap.
Reply A/B/C, or "all recommendations".
```

### `DR-07` · Error wire shape — batch 2

```text
DR-07 · Error wire shape — question 4 of batch 2

What JSON shape does every non-2xx API response return?

A. RFC 9457 Problem Details (`Content-Type: application/problem+json`)
   Real example:
       {
         "type": "https://errors.example.gov.sg/request-conflict",
         "title": "Request already submitted",
         "status": 409,
         "detail": "This request was submitted at 2026-10-27T03:14:00Z.",
         "requestId": "0192f3c4-1111-7000-8000-000000000099",
         "errors": [{ "location": "body.title", "message": "must not be blank" }]
       }
   Pros:  IETF standard (RFC 9457); built natively into `huma/v2` (`DR-04 = A`);
          extensible (`requestId`, `traceId`, field `errors[]`) without inventing
          a custom envelope; understood by API gateways and OpenAPI tooling.
   Costs: slightly more fields than `{ "error": "…" }`; `type` slugs need stable
          kebab-case discipline.
   Choose if: greenfield API with no legacy client forcing an older envelope.

B. Project-specific `{ "error": { "code", "message", "requestId", "fields" } }` envelope
   Real example:
       {
         "error": {
           "code": "REQUEST_CONFLICT",
           "message": "This request was already submitted.",
           "requestId": "0192f3c4-1111-7000-8000-000000000099"
         }
       }
   Pros:  terse `SCREAMING_SNAKE_CASE` switch keys; zero RFC terminology.
   Costs: bespoke schema that OpenAPI generators and gateways do not recognise as
          standard problem details; you write and document every extension rule.
   Choose if: matching an existing sibling service's exact client error parser.

C. Bare HTTP status code + plain text (`404 Not Found`)
   Real example:
       HTTP/1.1 409 Conflict
       Content-Type: text/plain; charset=utf-8

       conflict
   Pros:  trivial on tiny webhook receivers.
   Costs: cannot distinguish two `409` domain reasons or report per-field `422`
          validation errors cleanly to a UI form.
   Choose if: machine-to-machine probe or webhook sink with zero UI consumers.

Recommendation: A — RFC 9457 is an IETF standard and ships built into `huma/v2`.
Reply A/B/C, or "all recommendations".
```

### `DR-08` · Background work — batch 3

```text
DR-08 · Background jobs and async side-effects — question 1 of batch 3

How should work that must not block an HTTP response (emails, webhooks, exports) run?

A. SQL transactional outbox table + in-process `FOR UPDATE SKIP LOCKED` worker
   Real example:
       -- Claim batch atomically in Postgres:
       UPDATE outbox_jobs
          SET status = 'running', attempts = attempts + 1, locked_at = now()
        WHERE id IN (
            SELECT id FROM outbox_jobs
             WHERE status = 'pending' AND run_at <= now()
             ORDER BY run_at, id LIMIT 10
               FOR UPDATE SKIP LOCKED
        )
       RETURNING id, kind, payload, attempts;
   Pros:  zero new infrastructure (no Redis/SQS); enqueuing inside the handler's
          `pgx.Tx` guarantees atomic commit with the domain write; ~120 lines of
          auditable Go + `sqlc` with exponential backoff and dead-letter status.
   Costs: you own those 120 lines (poll ticker, `LISTEN/NOTIFY` wake-up, stuck-job
          reaper); tops out around a few thousand jobs/second per Postgres primary.
   Choose if: modest async volume (emails, audit webhooks, PDF exports) where
          transactional atomicity with Postgres matters more than throughput.

B. `riverqueue/river` (v0.49.0) — native Go + `pgx/v5` transactional Postgres queue
   Real example:
       _, err := riverClient.InsertTx(ctx, tx, SendReceiptArgs{
           RequestID: reqID.UUID(),
       }, &river.InsertOpts{MaxAttempts: 5})
   Pros:  built specifically for Go generics + `pgx/v5` (`InsertTx` shares the
          exact `pgx.Tx` of your `sqlc` write!); periodic cron, uniqueness windows,
          snoozing, rescue of stuck jobs, and optional `riverui` dashboard built in.
   Costs: River manages its own schema migrations (`rivermigrate`) alongside
          `goose`, which must be invoked in `RunMigrations` and `testdb` setup.
   Choose if: you have > 3 distinct job types, scheduled jobs, uniqueness windows,
          or retry workflows and still want Postgres-only infrastructure.

C. None yet — synchronous in-request only
   Real example:
       // No worker loop started in cmd/server; external side effects wait for an
       // explicit addendum superseding DR-08.
   Pros:  zero moving parts until the first real async requirement exists.
   Costs: **never** spawn detached `go sendEmail(...)` goroutines to dodge picking
          A or B — a pod restart drops the email silently and violates §16.2.
   Choose if: launch scope has zero emails, webhooks, or slow background exports.

Recommendation: A when you have 1–2 simple transactional side-effects; B (`river`)
as soon as you need cron, uniqueness, or multiple queues — never fire-and-forget
goroutines.
Reply A/B/C, or "all recommendations".
```

### `DR-09` · Runtime container base — batch 3

```text
DR-09 · Runtime container base image — question 2 of batch 3

What base image runs the compiled Go binary in production?

A. `gcr.io/distroless/static-debian12:nonroot` (built with `CGO_ENABLED=0`)
   Real example:
       FROM gcr.io/distroless/static-debian12:nonroot
       COPY --from=builder /out/server /app/server
       USER 65532:65532
       ENTRYPOINT ["/app/server"]
   Pros:  ~2 MiB attack surface; contains CA roots, `/usr/share/zoneinfo`, and
          `nonroot` user, with zero shell, zero `libc`, and near-zero Trivy CVEs;
          Go's pure-Go TLS + `pgx/v5` needs zero C shared libraries.
   Costs: `docker exec -it … sh` is impossible by design (debug with ephemeral
          containers or §17.1 `FlightRecorder` / `pprof`).
   Choose if: security scan cleanliness, minimal image size, and SHIP-HATS Trivy
          gates matter (default).

B. `debian:bookworm-slim` (mirrored via Nexus)
   Real example:
       FROM debian:bookworm-slim
       RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates tzdata \
        && rm -rf /var/lib/apt/lists/* && useradd -u 65532 -r -s /usr/sbin/nologin app
       USER 65532:65532
   Pros:  has `glibc` if a mandatory CGO library ever enters scope, plus a shell
          when ops policies require break-glass container `exec`.
   Costs: ~80 MiB image and recurring Debian `apt` CVE churn in Trivy scans.
   Choose if: platform operations require a shell inside the container or CGO.

C. `alpine:3.22` (with `CGO_ENABLED=0`)
   Real example:
       FROM alpine:3.22
       RUN apk add --no-cache ca-certificates tzdata && adduser -D -u 65532 app
       USER 65532:65532
   Pros:  ~8 MiB image with `sh` and `apk` available.
   Costs: `musl` DNS resolver quirks if `CGO_ENABLED=1` is ever turned on by
          mistake; still ships a shell and package manager for attackers.
   Choose if: your agency Nexus mirror standardises on hardened Alpine bases.

Recommendation: A — `CGO_ENABLED=0` on `distroless/static-debian12:nonroot` is
Go's superpower: a ~15 MiB total image with CA certs, tzdata, and almost zero
OS CVEs ever.
Reply A/B/C, or "all recommendations".
```

### `DR-10` · Dev orchestration — batch 3

```text
DR-10 · Developer task runner — question 3 of batch 3

What command runs `bootstrap`, `verify`, `up`, and `e2e`?

A. `just` (`justfile` at repository root)
   Real example:
       set dotenv-load := true

       # Run the full §8.1 validation ladder
       verify:
           golangci-lint fmt --diff
           golangci-lint run ./...
           nilaway -include-pkgs="{{module}}" ./...
           CGO_ENABLED=1 go test -race -shuffle=on ./...
           govulncheck ./...
   Pros:  purpose-built command runner (no `.PHONY`, no tab-vs-space traps);
          `just --list` self-documents recipes; loads `.env` cleanly.
   Costs: one small static binary (`just`) on developer laptops and CI images.
   Choose if: you want clean, readable recipes without Make quirks.

B. Pure Go task binary (`go run ./cmd/devtask <subcommand>`)
   Real example:
       // Invoked via `go run ./cmd/devtask verify` — zero external binary needed
       func main() { … }
   Pros:  requires literally nothing beyond `go` itself; cross-platform Go code
          instead of shell pipelines when orchestration grows conditional logic.
   Costs: more verbose than a 25-line `justfile` for simple command sequences.
   Choose if: developer workstations are locked down and cannot install `just`.

C. POSIX / GNU `make` (`Makefile`)
   Real example:
       SHELL := /bin/bash
       .SHELLFLAGS := -eu -o pipefail -c
       .PHONY: verify
       verify:
       	golangci-lint fmt --diff
       	CGO_ENABLED=1 go test -race -shuffle=on ./...
   Pros:  preinstalled on virtually every Linux/macOS box and CI runner.
   Costs: `.PHONY` boilerplate, `$` escaping traps, and macOS GNU Make 3.81
          quirks.
   Choose if: team muscle memory and org templates all expect `make verify`.

Recommendation: A (`just`), falling back to C (`make`) if workstation policy
forbids installing `just`.
Reply A/B/C, or "all recommendations".
```

### `DR-11` · Schema evolution — batch 3

```text
DR-11 · Schema evolution — question 4 of batch 3

Is there already a database holding data that must be migrated in place, or can
every database still be wiped and rebuilt cleanly?

A. Twin files: wholesale snapshot + numbered goose/v3 migrations (§5.1–§5.2)
   Real example:
       db/schema.sql                            # current snapshot parsed by sqlc
       migrations/00007_add_request_priority.sql # forward-only goose migration
       scripts/check-schema-parity.sh           # CI proves pg_dump parity
   Pros:  existing staging/production databases upgrade in place; migration
          history is replayable; rolling expand/contract deploys (§5.2) work.
   Costs: every schema edit touches two SQL files plus `check-schema-parity.sh`;
          embeds and locks `goose/v3` from day one even before launch.
   Choose if: any environment already holds data you will not recreate (staging
          with external testers, a persistent demo, or production).

B. Single embedded snapshot + `schema_state(version, sha256)` boot gate (§5.3)
   Real example:
       // db/embed.go: //go:embed schema.sql
       const SchemaVersion = 12
       // Boot applies schema.sql on empty DB, verifies match on (12, sha256),
       // and exits non-zero naming `just db-reset` on any older version/hash.
   Pros:  one SQL file (`db/schema.sql`) serves simultaneously as boot schema,
          `pgtestdb` test template, and `sqlc`'s offline compiler source; zero
          early-prototype migration churn to review or squash later.
   Costs: existing local/CI databases cannot upgrade in place — any version or
          hash mismatch refuses to boot until `just db-reset` runs. Requires a
          boot-twice test, a refuse-older test, a `check-standards` rule banning
          stray `migrations/`, and a written trigger ending Option B.
   Choose if: nothing is deployed yet and every database can be thrown away.

Recommendation: B until the first environment holds data worth keeping, then
supersede `DR-11` to A by copying `db/schema.sql` as `migrations/00001_initial.sql`
(moving B → A is trivial; starting at A prematurely invents history nobody needed).
Reply A/B, or "all recommendations".
```

---

## 13. The strictness profile (Go's answer to `tsconfig` `strictest`)

Go's compiler alone rejects unused variables, unused imports, implicit numeric
conversions, and package import cycles — and silently permits **ignored error
returns (`f()`), unchecked `nil` interface/pointer dereferences, forgotten
`rows.Close()`, non-exhaustive enum `switch`es, unguarded `http.DefaultClient`
calls, and shadowed `err` variables**. Pairing `go vet` with **`golangci-lint`
v2 (`v2.14.0`)** and Uber's inter-procedural **`nilaway`** closes every one of
those holes:

| TypeScript `strictest` flag | Go `1.27` + `golangci-lint` v2 + `nilaway` equivalent |
| --- | --- |
| `strictNullChecks` | `nilaway` (inter-procedural nil-flow prover) + `govet` `nilness` + `nilerr` + `nilnil` |
| `noImplicitAny` / `noUncheckedIndexedAccess` | Static typing + `errcheck` (`check-type-assertions: true`, `check-blank: true`) + banned `any` map soup |
| `switch` exhaustiveness (`never`) | `exhaustive` (`default-signifies-exhaustive: false`) on typed enum constants |
| `noUnusedLocals` / `noUnusedParameters` | Go compiler + `unused` + `unparam` + `ineffassign` |
| `noFallthroughCasesInSwitch` | Go language default (no implicit fallthrough in `switch`) |
| `useUnknownInCatchVariables` | Explicit `error` values + `errorlint` (`%w` wrapping, `errors.Is` / `errors.AsType`) |
| `exactOptionalPropertyTypes` | Go `1.27` `json:"...,omitzero"` + `PatchField[T]` (§14.3) |

### 13.1 The three artifacts (commit verbatim, adjust module path only)

1. **`go.mod` toolchain and tool pins:**

```gomod
module example.gov.sg/project

go 1.27
toolchain go1.27.3

tool (
	github.com/a-h/templ/cmd/templ
	github.com/pressly/goose/v3/cmd/goose
	github.com/sqlc-dev/sqlc/cmd/sqlc
	go.uber.org/nilaway/cmd/nilaway
	golang.org/x/vuln/cmd/govulncheck
)
```

2. **`.golangci.yml` (`version: "2"` — note that v1's `run.skip-dirs` and
   mixed formatter/linter config were removed in `golangci-lint` v2):**

```yaml
version: "2"

run:
  timeout: 5m
  tests: true
  modules-download-mode: readonly

formatters:
  enable:
    - gofumpt
    - goimports
  settings:
    gofumpt:
      extra-rules: true
    goimports:
      local-prefixes:
        - example.gov.sg/project

linters:
  default: none
  enable:
    # Correctness, nil & error discipline
    - govet
    - staticcheck
    - errcheck
    - errorlint
    - nilerr
    - nilnil
    - ineffassign
    - unused
    - unparam
    - exhaustive
    - durationcheck
    # Resource, HTTP & context safety
    - bodyclose
    - sqlclosecheck
    - rowserrcheck
    - contextcheck
    - fatcontext
    - containedctx
    - noctx
    # Complexity, style & Go 1.27 modernization
    - modernize
    - gocritic
    - revive
    - funlen
    - gocognit
    - nestif
    - gochecknoinits
    # Architecture, security & suppression hygiene
    - depguard
    - forbidigo
    - gosec
    - nolintlint

  settings:
    govet:
      enable-all: true
      disable:
        - fieldalignment # premature struct-padding churn outside hot-path types (§17)
    errcheck:
      check-type-assertions: true
      check-blank: true
    errorlint:
      errorf: true
      errorf-multi: true
      asserts: true
      comparison: true
    exhaustive:
      default-signifies-exhaustive: false
    funlen:
      lines: 50
      statements: 35
      ignore-comments: true
    gocognit:
      min-complexity: 15
    nestif:
      min-complexity: 4
    revive:
      rules:
        - name: argument-limit
          arguments: [4] # ctx + up to 3 domain params (§7.1)
        - name: flag-parameter
        - name: early-return
        - name: superfluous-else
        - name: indent-error-flow
        - name: var-naming
        - name: receiver-naming
        - name: error-naming
        - name: exported
        - name: package-comments
    forbidigo:
      forbid:
        - pattern: ^panic$
          msg: "never panic in application code; return a typed error (§7.2)"
        - pattern: ^fmt\.Print.*$
          msg: "use structured log/slog instead of fmt.Print* (§16.7)"
        - pattern: ^http\.(DefaultClient|DefaultServeMux|Get|Post|PostForm|Head)$
          msg: "use an explicit *http.Client with timeouts and *chi.Mux / *http.ServeMux (§10.1, §16.4)"
        - pattern: ^time\.(Now|Local)$
          msg: "inject Clock for testable UTC time and never use time.Local (§2.4, §4.5)"
    depguard:
      rules:
        no-unsafe-or-legacy:
          files:
            - "$all"
          deny:
            - pkg: "unsafe"
              desc: "unsafe requires a numbered addendum and fuzz suite (§8.2)"
            - pkg: "math/rand$"
              desc: "use math/rand/v2 (seeded PCG in tests) or crypto/rand (§3)"
            - pkg: "io/ioutil"
              desc: "use io and os stdlib functions"
            - pkg: "github.com/pkg/errors"
              desc: "use stdlib errors, fmt.Errorf %w, and errors.AsType"
            - pkg: "github.com/google/uuid"
              desc: "use Go 1.27 stdlib uuid package (§4.5)"
        domain-purity:
          files:
            - "**/internal/*/*.go"
            - "!**/internal/platform/**"
            - "!**/internal/*/*_test.go"
          deny:
            - pkg: "os"
              desc: "read env and files in cmd/ or internal/platform/config, not domain packages"
    nolintlint:
      require-explanation: true
      require-specific: true
      allow-unused: false

  exclusions:
    generated: lax
    rules:
      - path: _test\.go
        linters:
          - funlen
          - gocognit
          - forbidigo # tests may construct fixed times or assert panics
      - path: cmd/server/main\.go
        linters:
          - forbidigo # main wires real time.Now Clock

issues:
  max-issues-per-linter: 0
  max-same-issues: 0
```

3. **Inter-procedural nil-safety (`nilaway`):** run `go tool nilaway
   -include-pkgs="example.gov.sg/project" ./...` right beside `golangci-lint` in
   `just verify`. `golangci-lint` checks single-function AST rules; `nilaway`
   traces `nil` slices, maps, pointers, and interfaces **across function and
   package boundaries** before a single request runs.

Add a CI check `golangci-lint config verify` so a typo in `.golangci.yml` fails
loudly instead of silently ignoring a rule block.

### 13.2 Severity: warnings don't exist in CI

Every enabled linter fails `golangci-lint run` with a non-zero exit code. For
rapid inner-loop iteration on a laptop, developers may run `golangci-lint run
--fast-only ./...`, while `just verify` and CI always run the full type-aware
suite (`golangci-lint run ./...` + `nilaway` + `go test -race`).

### 13.3 Four Go linter traps to configure intentionally

1. **`errcheck` with `check-blank: true` and `defer rows.Close()`.** Read-only
   `Close()` calls (`defer resp.Body.Close()`) return an error nobody can recover
   from, yet `_ = resp.Body.Close()` triggers `check-blank`! Provide a tiny
   `httpx.CloseQuietly(io.Closer)` helper for read streams — and **never** use
   it on a writable file or `tx.Commit()`, where `Close()`/`Commit()` flushes
   buffered bytes and its error is the write result.
2. **Enable `exhaustive` on enums, NOT `exhaustruct` globally.** `exhaustruct`
   forces callers to spell out all 22 zero-valued fields of `&http.Server{}` or
   `tls.Config{}`, ruining idiomatic Go zero-value defaults. Leave `exhaustruct`
   off (or scoped strictly to one package) while keeping `exhaustive` **on**
   (`default-signifies-exhaustive: false`) so adding a new domain `Status` constant
   immediately flags every `switch` in the repo!
3. **`contextcheck` when spawning bounded post-response cleanup or audit flushes.**
   Passing `r.Context()` to work that must finish completing a committed DB step
   cancels mid-flight if the browser tab closes; derive
   `ctx, cancel := context.WithTimeout(context.WithoutCancel(r.Context()), 3*time.Second)`
   (`defer cancel()`) so trace/span values carry over without inheriting client
   cancellation.
4. **`gosec` `G115` integer overflow conversions (`int` → `int32`/`uint32`).**
   Postgres `integer` (`int32`) vs Go `int` (`int64` on 64-bit) triggers `G115`
   on bare `int32(n)`. Do not silence `G115`; validate range bounds at input
   parsing (`min:"1" max:"1000"`) or check `if n < 0 || n > math.MaxInt32` in a
   domain constructor once.

### 13.4 What the profile cannot prove

Static analysis cannot prove SQL column semantics (`sqlc` + real-DB tests do),
goroutine absence of deadlocks under contention (`-race` + `goleak` + `synctest`
do), integer arithmetic overflow (`math/bits` or explicit bounds checks do), or
missing authorization predicates (§2.2's negative IDOR tests do).

---

## 14. API and idiom rules (the parts reviewers actually cite)

Grounded in the [Google Go Style Guide](https://google.github.io/styleguide/go/),
[Uber Go Style Guide](https://github.com/uber-go/guide/blob/master/style.md),
and *Effective Go*.

### 14.1 Value vs pointer receivers, parameters, and slice ownership

| Type shape | Receiver & parameter convention | Why |
| --- | --- | --- |
| Small immutable value (`RequestID`, `ActorID`, `Email`, `Money`, `time.Time`) | **By value** (`func (id RequestID) String() string`) | Stack-allocated, nil-impossible, thread-safe to copy freely |
| Struct that mutates state, contains `sync.Mutex`/`atomic.*`, or is large (`> ~64 B`) | **By pointer** (`func (s *Store) Invalidate(...)`) | Prevents copying locks (`govet` `copylocks`) and avoids copying wide structs |
| Consistency rule on one type | **Never mix** value and pointer receivers on the same struct | Mixing breaks interface satisfaction on value variables and confuses mutation semantics |
| Slices (`[]T`) and maps (`map[K]V`) crossing a boundary | Clone defensively (`slices.Clone(in)`, `maps.Clone(in)`) when stored on a struct or returned from internal state | A Go slice header is a 24-byte view over a shared backing array — caller mutation corrupts struct invariants silently! |

Never use `*string`, `*int`, or `*[]T` inside domain models just to mean
"unset" — use a domain value with `IsZero()`, a dedicated union/variant, or
`PatchField[T]` at the HTTP `PATCH` edge (§14.3).

### 14.2 Naming rules (`Get` prefixes, package stutter, and cost honesty)

- **Never prefix getters with `Get`.** Write `req.Owner()`, not `req.GetOwner()`;
  reserve `Fetch*` / `Load*` / `Compute*` for methods that perform I/O or non-O(1)
  work so cost is visible at the call site.
- **Never stutter the package name.** Inside `package requests`, export `Summary`,
  `ParseID`, `NewStore`, and `Invalidate` — callers write `requests.Summary` and
  `requests.Invalidate(ctx, id)`, never `requests.RequestSummary`.
- **Single-method interfaces take `-er` nouns where natural** (`Clock`, `Mailer`,
  `TokenVerifier`) — **never** `IMailer` or `MailerInterface`.
- **Acronyms keep uniform case:** `RequestID`, `HTTPClient`, `OIDCConfig`,
  `urlStr` / `rawURL` — never `RequestId` or `HttpClient` (`revive` `var-naming`).

### 14.3 Type shape: unexported fields, zero-value safety, and `PatchField[T]`

- **Exported structs with invariants keep their fields unexported.** In Go, any
  package can instantiate `Email{}` or `Request{}` as a zero literal! Keep fields
  unexported (`type Email struct { v string }`), provide a validating constructor
  (`ParseEmail(raw string) (Email, error)`), and expose an `IsZero() bool` check
  that write paths reject if handed an uninitialised zero value.
- **Seal sum-type interfaces to the defining package** by including an unexported
  marker method (`isDecisionOutcome()`) on the interface (§15.4).
- **Distinguish omitted vs `null` vs value on `PATCH` (`PatchField[T]`).** A
  `*string` field cannot tell `"description" omitted` (leave column alone) apart
  from `"description": null` (clear nullable column to `NULL`). Use a tiny
  generic `PatchField[T]` everywhere `PATCH` semantics exist, pairing cleanly
  with Go 1.27's `omitzero` on outbound serialization:

```go
package wire

import (
	"bytes"
	jsonv2 "encoding/json/v2"
)

type PatchField[T any] struct {
	Set   bool
	Null  bool
	Value T
}

func (f PatchField[T]) IsZero() bool { return !f.Set }

func (f *PatchField[T]) UnmarshalJSON(data []byte) error {
	f.Set = true
	if bytes.Equal(data, []byte("null")) {
		f.Null = true
		var zero T
		f.Value = zero
		return nil
	}
	f.Null = false
	return jsonv2.Unmarshal(data, &f.Value, jsonv2.RejectUnknownMembers(true))
}
```

### 14.4 Modern Go 1.26 / 1.27 conversions and error unwrapping

- **Always use Go 1.26's generic `errors.AsType[E](err)` instead of `errors.As`:**

```go
// Good (Go 1.26+): compile-time type-safe, single line, zero reflection panics
if pgErr, ok := errors.AsType[*pgconn.PgError](err); ok && pgErr.Code == pgerrcode.UniqueViolation {
	return Conflict("request title already exists")
}
```

- **Use Go 1.26's `new(expr)`** when constructing optional pointer fields for
  generated external structs (`TimeoutSeconds: new(30)` instead of a throwaway
  local variable `v := 30; &v`).
- **Wrap errors with `%w` only when callers are permitted to match the inner
  error programmatically** (`errors.Is` / `errors.AsType`); use `%v` across
  trust boundaries when hiding internal driver details from public API contracts!
  (Go 1.27's `go vet` also catches subtle `func (e *MyErr) Error()` pointer-vs-value
  `%w` bugs automatically.)

### 14.5 Standard interface set on domain value types

Every domain identifier / scalar (`RequestID`, `ActorID`, `Email`, `Secret[T]`)
implements the standard library contracts once so logging, JSON, query params,
and tests work uniformly:

- `String() string` (`fmt.Stringer` — redacted on `Secret[T]`)
- `LogValue() slog.Value` (`slog.LogValuer` — structured attributes & PII safety)
- `MarshalText() ([]byte, error)` and `UnmarshalText([]byte) error` (handled
  automatically by `encoding/json`, `encoding/json/v2`, Huma, and `sqlc` text
  codecs)
- `IsZero() bool` (used natively by Go 1.27's `json:"...,omitzero"`)

### 14.6 `godoc` comments and testable `Example*` functions

- Every exported package has a `// Package <name> …` doc comment; every exported
  type and function starts its doc comment with its exact identifier name and
  states error conditions (`// Invalidate marks the request expired. It returns
  ErrNotFound if id does not exist or is not owned by actor.`).
- Write `func ExampleParseEmail()` in `email_test.go` with `// Output:` comments
  for core domain types — `go test` compiles and verifies them on Rung 5 (§8.1).

### 14.7 API review checklist

- [ ] No `Get*` prefix on cheap accessors; no `requests.Request*` package stutter.
- [ ] Domain value types have unexported fields, `Parse*` constructor, and `IsZero()`.
- [ ] Slices/maps stored or returned across boundaries are cloned (`slices.Clone`).
- [ ] Value vs pointer receivers are consistent across all methods of each struct.
- [ ] `PATCH` inputs use `PatchField[T]`, never ambiguous `*T` for nullable columns.
- [ ] Error unwrapping uses `errors.Is` and Go 1.26 `errors.AsType[T](err)`.
- [ ] `Secret[T]` and PII types implement `slog.LogValuer` redaction.
- [ ] Exported functions document which domain errors callers should match.

---

## 15. Design patterns that earn their keep

Go's simplicity makes ceremony stand out immediately. Every pattern below earns
its place by turning a class of runtime bug into a compile error — and names the
exact condition where using it is over-engineering.

### 15.1 Parse, don't validate — with unexported-field structs (never `type Email string`!)

**Go trap to avoid:** In Rust (`struct Email(String)`) or branded TypeScript, a
newtype prevents raw strings from sneaking in. In Go, `type Email string` **fails
to enforce invariants** because Go's untyped string constants convert implicitly:
`SendWelcome("not-an-email")` compiles without calling `ParseEmail`!

Always wrap validated scalars in a **struct with an unexported field**:

```go
package actors

import (
	"errors"
	"log/slog"
	"net/mail"
	"strings"
)

type Email struct {
	v string // unexported: external packages cannot construct non-empty Email literals
}

var ErrInvalidEmail = errors.New("invalid email address")

func ParseEmail(raw string) (Email, error) {
	trimmed := strings.TrimSpace(raw)
	addr, err := mail.ParseAddress(trimmed)
	if err != nil || addr.Address != trimmed {
		return Email{}, ErrInvalidEmail
	}
	return Email{v: strings.ToLower(addr.Address)}, nil
}

func (e Email) String() string       { return e.v }
func (e Email) IsZero() bool         { return e.v == "" }
func (e Email) MarshalText() ([]byte, error) { return []byte(e.v), nil }

func (e *Email) UnmarshalText(b []byte) error {
	parsed, err := ParseEmail(string(b))
	if err != nil {
		return err
	}
	*e = parsed
	return nil
}

func (e Email) LogValue() slog.Value {
	if e.IsZero() {
		return slog.StringValue("")
	}
	return slog.StringValue("[REDACTED_EMAIL]")
}
```

Parse once at the HTTP/CLI boundary; deeper domain functions accept `Email` and
never re-run regexes or `strings.Contains(s, "@")`.

### 15.2 Distinct ID structs (`RequestID`, `ActorID`)

Wrap Go 1.27's `uuid.UUID` per entity (`type RequestID struct { v uuid.UUID }`,
`type ActorID struct { v uuid.UUID }`). Mint IDs exclusively in domain
constructors (`NewRequestID()` calling `uuid.NewV7()`) and verify RFC 9562 v7 in
`ParseRequestID` (`(u[6] >> 4) == 7 && (u[8] & 0xc0) == 0x80`). Swapping
`(actorID, requestID)` at a call site fails at `go build`.

### 15.3 Typestate (`Request[S State]`) — strictly for linear sequences

Go generics encode compile-time state transitions cleanly when a workflow is a
fixed, linear pipeline (`Draft` → `Submitted` → `Approved`):

```go
type Draft struct{}
type Submitted struct{ SubmittedAt time.Time }
type requestState interface{ Draft | Submitted }

type Request[S requestState] struct {
	id    RequestID
	title string
	state S
}

func Submit(r Request[Draft], now time.Time) Request[Submitted] {
	return Request[Submitted]{
		id:    r.id,
		title: r.title,
		state: Submitted{SubmittedAt: now.UTC()},
	}
}
```

**When typestate is wrong (do not use it here):** when rows are loaded from
Postgres in arbitrary runtime states, when transitions branch/loop dynamically,
or when admins configure workflows. There, use a single `Request` struct with a
typed `Status` enum and an `exhaustive`-checked `switch` in `CanTransition`.

### 15.4 Sealed union interfaces over `kind` + nullable pointer soup

Go lacks native Rust `enum` sum types, so developers often write buggy structs
with `Kind string` plus four nullable pointers where three are secretly `nil`.
Replace pointer soup with a **package-sealed interface**:

```go
type Decision interface {
	isDecision() // unexported: only types in this package can implement Decision
}

type Approved struct {
	Approver ActorID
	At       time.Time
}
func (Approved) isDecision() {}

type Rejected struct {
	Reviewer ActorID
	Reason   string
}
func (Rejected) isDecision() {}
```

### 15.5 Parameter structs first; Functional Options only for optional platform tuning

- **Inside `internal/<domain>/`:** take a plain `SubmitParams` struct (and a
  `Validate() error` check if external). Every required field is visible at the
  call site.
- **On shared `internal/platform/` constructors with ≥ 4 genuinely optional
  knobs and safe defaults:** use `type Option func(*options)` (`WithMaxRetries(3)`),
  validating options inside `NewClient(...) (*Client, error)` (never panicking
  inside an `Option` closure).
- **Never** write Java-style `.WithTitle(t).WithOwner(o).Build()` builders that
  turn missing required arguments into runtime errors.

### 15.6 Small, consumer-defined interfaces

Define interfaces **in the package that calls them**, `1–3` methods wide, and
only when ≥ 2 real non-mock implementations exist (e.g. `SESMailer` in prod and
`CaptureMailer` in local/e2e dev):

```go
// internal/requests/notify.go — consumer defines only what it needs
type ReceiptSender interface {
	SendReceipt(ctx context.Context, to actors.Email, id RequestID) error
}

// Compile-time satisfaction proof in adapter package:
var _ requests.ReceiptSender = (*ses.Client)(nil)
```

### 15.7 `defer` transaction & resource guards

Pair every acquired transaction, lock, or stream with `defer` on the very next
line. With `pgx/v5`, `tx.Rollback(ctx)` after a successful `tx.Commit(ctx)` is a
safe no-op returning `pgx.ErrTxClosed`:

```go
tx, err := pool.Begin(ctx)
if err != nil {
	return fmt.Errorf("begin tx: %w", err)
}
defer func() {
	rbCtx, cancel := context.WithTimeout(context.WithoutCancel(ctx), 3*time.Second)
	defer cancel()
	_ = tx.Rollback(rbCtx)
}()
```

### 15.8 Functional core, imperative shell

Keep transition rules, pricing, quota math, and eligibility policies in **pure
functions** (`policy.go`) taking plain domain structs + `now time.Time` and
returning `(Decision, error)` with zero `context.Context` and zero `pgx`
imports. The imperative handler/command loads rows via `sqlc` inside a
transaction, calls the pure function, persists the decision, and commits. Pure
policy suites run 500 cases in `< 5 ms`.

### 15.9 Dispatch hierarchy (cheapest sufficient tool wins)

| Need | Go mechanism |
| --- | --- |
| Single implementation (95% of domain & `sqlc` code) | Concrete struct / package function |
| Closed set of variants known to one package | Typed `Status` `switch` (`exhaustive`) or sealed interface (§15.4) |
| Type-parametric data structure / helper (`PatchField[T]`, `Secret[T]`) | Go generics (`[T any]` / constrained type set) |
| Open runtime plug-in / ≥ 2 real external adapters (`Mailer`, `Clock`) | 1–3 method consumer-defined interface (§15.6) |

### 15.10 Patterns we decline

| Anti-pattern | Why it hurts in Go | Do this instead |
| --- | --- | --- |
| `type FooRepository interface` per table (1 real impl) | Doubles boilerplate and encourages banned DB mocks (§2.1) | Concrete `*Queries` / domain functions against real `pgtestdb` |
| Reflection DI containers (`uber-go/dig`, `samber/do`) | Turns missing wiring from a `go build` error into a boot/request panic | Explicit `Deps` struct constructed in `cmd/server/main.go` |
| Fluent `.SetX().SetY().Build()` builders | Hides required parameters at runtime | Plain parameter struct + validating constructor |
| Struct embedding used as OOP inheritance | Leaks embedded methods onto public API and JSON serialization | Explicit named struct fields and delegation |
| Package-level `var db *pgxpool.Pool` + `func init()` | Breaks `t.Parallel()` test isolation and hides startup order | Explicit constructor injection; `gochecknoinits` |
| `type Email string` primitive alias for validated types | Untyped string literals bypass `ParseEmail` silently (§15.1) | `type Email struct { v string }` with unexported field |
| `map[string]any` payloads inside `internal/` | Defeats static typing, `nilaway`, and `openapi` generation | Typed structs + `jsonv2.RejectUnknownMembers(true)` |
| Fire-and-forget `go sendEmail(ctx, ...)` in handlers | Inherits cancelled `r.Context()` and vanishes on pod deploy | Transactional SQL outbox or `river.InsertTx` (`DR-08`) |
| `context.WithValue` used as a dependency bag | Untyped `any` lookups and invisible function signatures | Explicit parameters; `context` holds trace/auth metadata only |
| GORM auto-migrate & struct `Updates(model)` | Silently skips zero values (`0`, `false`, `""`) and drifts from SQL | `sqlc` + `pgx/v5` + explicit `goose` SQL migrations |

### 15.11 Effects as a returned value (post-commit write-then-publish)

When correctness requires every mutation to trigger an **in-process post-commit
notification** (pushing an SSE/WebSocket frame, invalidating an in-memory cache
tag, waking a scheduler), "remember to call `hub.Publish` after `tx.Commit`"
fails quietly on the third write endpoint added six months later. (Note the
boundary with `DR-08`: **durable external** side-effects like emails and
webhooks belong inside the Postgres `pgx.Tx` via the outbox table or
`river.InsertTx`; returned `Effects` govern **post-commit in-memory** fan-out
that must fire *only after* `tx.Commit` succeeds.)

Go has **no `#[must_use]` attribute**, so returning a 3-tuple `(Scan, Effects,
error)` lets `scan, _, err := RecordScan(...)` silently discard the effects!
Encode the obligation as an **unexported-field capability wrapper
(`effects.Outcome[T]`)** whose value `T` cannot even be read without either
publishing or stating a discard reason:

```go
package effects

import (
	"context"
	"example.gov.sg/project/internal/kernel"
)

type Publisher interface {
	Publish(ctx context.Context, events []kernel.Event) error
}

// Outcome wraps a committed write result T together with post-commit effects.
// Both fields are unexported: callers can extract T ONLY via Publish or Discard.
type Outcome[T any] struct {
	val    T
	events []kernel.Event
}

func New[T any](val T, events ...kernel.Event) Outcome[T] {
	return Outcome[T]{val: val, events: events}
}

func (o Outcome[T]) Publish(ctx context.Context, p Publisher) (T, error) {
	if len(o.events) > 0 {
		if err := p.Publish(ctx, o.events); err != nil {
			var zero T
			return zero, err
		}
	}
	return o.val, nil
}

func (o Outcome[T]) Discard(_reason string) T { return o.val }
```

- Domain writes return `(effects.Outcome[Scan], error)` without importing the
  SSE hub or cache adapter, keeping the package graph acyclic (§18).
- `kernel.Event` and `kernel.CacheTag` live in the dependency-free
  `internal/kernel/` leaf package as closed enums/unions (`exhaustive`-checked),
  so adding a new event kind flags every subscriber `switch` at lint time.
- For void writes (`Outcome[struct{}]`), add a 30-line `go/types` rule in
  `check-standards` (§2.7, proven on a violating fixture) flagging any
  unconsumed `effects.Outcome` value.
- **When `Outcome[T]` is wrong:** best-effort telemetry, debug logs, or OTel
  counters — wrapping those trains engineers to write `.Discard("n/a")`
  reflexively, destroying the signal.

---

## 16. Concurrency correctness and observability

### 16.1 Runtime rules

- **Let Go `1.25+` manage cgroup `GOMAXPROCS` natively.** Go 1.25 made the
  runtime cgroup-CPU aware out of the box and updates `GOMAXPROCS` dynamically
  when container CPU quotas change — do **not** add `go.uber.org/automaxprocs`.
- **Every goroutine has an owner, a stop signal, and a join point.** If you
  cannot answer "which function waits for this goroutine to exit before `main`
  returns?", you have written a goroutine leak and a shutdown race.

### 16.2 Structured concurrency (`errgroup` and `WaitGroup.Go`)

- **Fallible parallel work uses `golang.org/x/sync/errgroup.WithContext(ctx)`
  with `g.SetLimit(n)`** — never unbounded goroutine fan-out over caller-supplied
  slices:

```go
g, gctx := errgroup.WithContext(ctx)
g.SetLimit(8)
for _, id := range ids {
	g.Go(func() error {
		return enrichItem(gctx, pool, id) // Go 1.22+ per-iteration loop variable is safe!
	})
}
if err := g.Wait(); err != nil {
	return err
}
```

- **Infallible worker fan-out uses Go 1.25's `wg.Go(func() { … })`** instead of
  manual `wg.Add(1)` / `defer wg.Done()` pairs.
- **Catch panics inside background worker goroutines.** An unrecovered panic in
  *any* spawned goroutine crashes the entire Go binary immediately, bypassing the
  HTTP `Recoverer` middleware! Wrap worker entrypoints in a tiny `safego` recover
  guard that logs stack + trace and converts panics into errors.

### 16.3 Cancellation safety in `select` & client-disconnect mid-write hazards

- **Every channel send/receive in long-lived or bounded pipelines selects on
  `<-ctx.Done()`:**

```go
select {
case out <- event:
	return nil
case <-ctx.Done():
	return ctx.Err()
}
```

- **Never call `time.After(d)` inside a `for`/`select` loop** (prefer a reused
  `time.NewTimer` / `time.NewTicker` with `defer ticker.Stop()`).
- **Client tab close cancels `r.Context()` immediately.** If an HTTP handler
  executes two separate `pool.Exec(r.Context(), …)` writes without a transaction
  and the browser disconnects after statement 1, statement 1 stays committed and
  statement 2 aborts! Wrap multi-statement mutations in a single `pgx.Tx`
  (`§15.7`) so client cancellation rolls back the entire unit atomically.

### 16.4 Backpressure: bounded queues, timeouts, and CPU semaphores

- **No unbounded channels or queues** (`make(chan Job, 100000)` hiding memory
  growth until OOM). Bound capacity and reject (`429` / `503` `Retry-After`) or
  persist to Postgres (`DR-08`).
- **Every outbound dependency has an explicit deadline:**
  - HTTP: dedicated `&http.Client{Timeout: 10 * time.Second}` (default
    `http.DefaultClient` has **infinite** timeout and is banned in §13);
  - Postgres: `pgxpool.Config` sets `MaxConns`, `MaxConnLifetime`,
    `MaxConnIdleTime`, and statement/context timeouts;
  - CPU/memory-heavy hashing (`argon2id`, PDF): gate behind
    `semaphore.Weighted` (`Acquire(ctx, 1)`) so credential-stuffing traffic
    queues/429s instead of OOM-killing the pod.

### 16.5 Locks (`sync.Mutex`)

- Prefer `sync.Mutex` over `sync.RWMutex` unless benchmarks prove read
  contention.
- **Never hold a `sync.Mutex` across network, disk, or Postgres I/O.** Copy or
  reserve state under the lock in nanoseconds, unlock, then perform I/O.
- Place `mu sync.Mutex` directly above the unexported fields it guards, and
  never pass a struct containing a lock by value (`govet` `copylocks`).

### 16.6 Ordered graceful shutdown

Handle `SIGINT`/`SIGTERM` via `signal.NotifyContext` and tear down in **strict
reverse dependency order** so in-flight requests never encounter a closed
Postgres pool or dropped OTel spans:

```go
ctx, stop := signal.NotifyContext(context.Background(), syscall.SIGINT, syscall.SIGTERM)
defer stop()

// ... start HTTP server and background workers ...
<-ctx.Done()
readiness.SetDraining() // /readyz immediately returns 503 Service Unavailable

drainCtx, cancel := context.WithTimeout(context.Background(), 20*time.Second)
defer cancel()

_ = httpServer.Shutdown(drainCtx) // 1. Stop accepting & drain in-flight HTTP handlers
_ = workerGroup.Wait()            // 2. Drain background outbox / River workers
_ = otelShutdown(drainCtx)        // 3. Flush OTel traces, metrics, and logs
pool.Close()                      // 4. Close pgxpool LAST
```

### 16.7 Structured `log/slog` (`NewMultiHandler`)

- Use standard-library `log/slog` exclusively (`fmt.Print*` and legacy `log.*`
  are banned in §13).
- Combine JSON stdout logging and OpenTelemetry log export using Go 1.26's
  built-in **`slog.NewMultiHandler`**:

```go
jsonHandler := slog.NewJSONHandler(os.Stdout, &slog.HandlerOptions{Level: cfg.LogLevel})
otelHandler := otelslog.NewHandler("server", otelslog.WithLoggerProvider(loggerProvider))
logger := slog.New(slog.NewMultiHandler(jsonHandler, otelHandler))
```

- Always log with context (`logger.InfoContext(ctx, "request invalidated",
  slog.Any("request_id", id))`) so trace/span correlation attaches
  automatically, using typed `slog.Attr`s (`LogAttrs`) on hot paths.

### 16.8 OpenTelemetry Go (`v1.47.0` — all three signals stable `1.x` GA)

- Pin `go.opentelemetry.io/otel` `v1.47.0+` (`>= v1.45.0` is mandatory for
  `CVE-2026-81870`). As of OTel Go `v1.42+`, Traces (`sdk/trace`), Metrics
  (`sdk/metric`), **and** Logs (`otel/log` + `sdk/log`) are all stable `1.x` GA.
  Note that `go.opentelemetry.io/otel/log/global` is deprecated — pass explicit
  `*sdklog.LoggerProvider` instances via `Deps`, never hidden globals!
- Instrument inbound HTTP with `otelhttp.NewHandler` (`v0.72.0`), outbound HTTP
  clients with `otelhttp.NewTransport`, and `pgxpool` with
  `github.com/exaring/otelpgx` (`cfg.ConnConfig.Tracer = otelpgx.NewTracer()`).
- Propagate W3C `traceparent` + `baggage` (`propagation.NewCompositeTextMapPropagator`).

### 16.9 RED metrics without cardinality explosions

Emit **Rate, Errors, and Duration** (`http.server.request.duration`) keyed ONLY
by bounded attributes: `http.request.method`, `http.response.status_code`, and
**route template** (`http.route`, read from `r.Pattern` or
`chi.RouteContext(r.Context()).RoutePattern()`, e.g. `"/api/requests/{id}"`).
**Never** put raw `r.URL.Path`, `actor_id`, `email`, or `request_id` into metric
labels — high-cardinality labels blow up Prometheus / OTel Collector memory in
minutes; put high-cardinality IDs on **spans and structured logs** instead.

### 16.10 PII and `Secret[T]` redaction

- `Secret[T]` and `Email` implement `slog.LogValuer` so accidental
  `slog.Any("cfg", cfg)` or `slog.Any("actor", actor)` calls emit `[REDACTED]`.
- Configure `otelhttp` / HTTP logging middleware with an explicit header
  allowlist (`Content-Type`, `User-Agent`, `X-Request-Id`), never logging
  `Authorization`, `Cookie`, or `Set-Cookie`.

### 16.11 Health probes: `/healthz` vs `/readyz`

- **`GET /healthz` (liveness):** returns `200 OK` immediately in memory. **Never
  ping Postgres in `/healthz`** — a 3-second database failover would cause
  Kubernetes/ECS to restart every healthy Go pod simultaneously!
- **`GET /readyz` (readiness):** returns `503` immediately once
  `readiness.SetDraining()` fires, and otherwise runs a 1-second bounded
  `pool.Ping(ctx)` so load balancers stop routing to pods that cannot reach
  Postgres.

### 16.12 Concurrency & observability review checklist

- [ ] Zero bare `go func()` without an owning `errgroup` or `WaitGroup.Go`.
- [ ] Background goroutines recover panics and report them to `slog` + metrics.
- [ ] Multi-step writes inside handlers run in one `pgx.Tx` (§16.3).
- [ ] Channel loops `select` on `<-ctx.Done()` and never call `time.After` per iteration.
- [ ] Zero `http.DefaultClient`; every outbound client and pool has explicit timeouts.
- [ ] `argon2id` and heavy CPU/memory endpoints are bounded by `semaphore.Weighted`.
- [ ] No `sync.Mutex` is held across Postgres or network I/O.
- [ ] Shutdown drains HTTP → workers → OTel providers → `pool.Close()` in order.
- [ ] Metric labels use route patterns (`"/api/requests/{id}"`), never raw paths/UUIDs.
- [ ] `/healthz` is dependency-free; `/readyz` checks draining state + `pool.Ping`.

---

## 17. Performance and adversarial testing

### 17.1 Measure before tuning

- **CPU, heap, mutex, and goroutine-leak profiles (`runtime/pprof`).** Expose
  `net/http/pprof` (including Go 1.27's GA **`/debug/pprof/goroutineleak`**
  profile!) **only** on a loopback/internal admin port (`127.0.0.1:9091`), never
  on the public `:3000` router.
- **Always-on production flight recording (`runtime/trace.FlightRecorder`, Go
  1.25+).** Keep a tiny (~5 MiB, 5-second) in-memory execution-trace ring buffer
  running at `< 1%` overhead and snapshot it to object storage / disk only when
  a request exceeds its latency SLO or panics — capturing the exact root cause
  of tail-latency spikes inside `distroless` without needing a shell!
- **Benchmarks use Go 1.24+'s `for b.Loop()` + `b.ReportAllocs()`, compared via
  `benchstat`.** `b.Loop()` prevents compiler dead-code elimination and excludes
  setup/cleanup time automatically:

```go
func BenchmarkParseEmail(b *testing.B) {
	b.ReportAllocs()
	for b.Loop() {
		_, _ = actors.ParseEmail("alice.tan@example.gov.sg")
	}
}
```

  Run `go test -run='^$' -bench=. -benchmem -count=10 ./... > new.txt` and compare
  against `old.txt` with `benchstat old.txt new.txt` before claiming any
  micro-optimisation helped.

### 17.2 Production build flags and Profile-Guided Optimization (PGO)

- Build release binaries with `CGO_ENABLED=0 go build -trimpath -buildvcs=false
  -ldflags="-s -w"` (reproducible paths, stripped DWARF/symbol tables for smaller
  images while retaining full Go panic stack traces!).
- Once real production CPU pprof samples exist, commit a merged profile at
  `cmd/server/default.pgo`: `go build` detects `default.pgo` automatically and
  applies devirtualization and hot-path inlining for a **2–14% throughput gain**
  with zero source-code complexity.

### 17.3 Green Tea GC, allocations, and `GOMEMLIMIT`

- **Go 1.26+ enables the Green Tea garbage collector by default**, cutting GC CPU
  overhead by **10–40%** on allocation-heavy web services via locality-aware span
  scanning.
- **Always configure `GOMEMLIMIT` to ~85% of container memory** (leave `GOGC=100`
  default) so the runtime paces GC before the container hits `cgroup` OOM, while
  avoiding GC thrashing if a transient spike approaches 100%.
- **Pre-size slices when length is known** (`make([]Summary, 0, len(rows))`);
  reach for `sync.Pool` only after `b.ReportAllocs()` and heap profiles prove a
  specific allocation dominates GC pressure.

### 17.4 The Postgres query plan matters ten times more than Go micro-tuning

- Run `EXPLAIN (ANALYZE, BUFFERS)` on every list, search, and authorization join
  before tuning Go code.
- **Paginate by keyset cursor `(created_at, id) < ($1, $2)`**, never large
  `OFFSET` scans.
- Batch bulk inserts with `pgx.CopyFrom` or `pgx.Batch` instead of `for` loops
  issuing N round-trips.

### 17.5 Adversarial testing beyond example-based tests

Example tests prove the cases you thought of. The seven tools below hunt the
ones you didn't:

1. **Property-based testing (`pgregory.net/rapid` `v1.2.0`):** assert algebraic
   invariants (round-trip codecs, pagination cursor monotonicity, `Invalidate`
   idempotency); commit `testdata/rapid/` failure files.
2. **Native coverage-guided fuzzing (`go test -fuzz`):** write `func
   FuzzClientIP(f *testing.F)` / `FuzzParseCursor` / `FuzzWebhookSignature` for
   every untrusted byte/string parser. Seed corpus entries run as fast unit
   tests on **every** `go test ./...` PR run; continuous `-fuzztime=60s` runs
   nightly.
3. **Race detector (`CGO_ENABLED=1 go test -race`):** non-negotiable on every PR
   unit and integration test run.
4. **Deterministic concurrency & timer testing (`testing/synctest` + Go 1.27
   `httptest.NewTestServer`):** test retry backoffs, session expiry, outbox
   leases, and HTTP timeouts in **0 ms of real wall-clock sleep** with zero
   flakiness:

```go
func TestOutboxRetryBackoff(t *testing.T) {
	synctest.Test(t, func(t *testing.T) {
		srv := httptest.NewTestServer(flakyWebhookHandler()) // Go 1.27 synctest-aware server!
		defer srv.Close()

		done := startWorkerWithBackoff(t.Context(), srv.Client(), srv.URL)
		synctest.Sleep(30 * time.Second) // Go 1.27 helper: advances virtual clock + synctest.Wait()
		assertDeliveredAfterRetries(t, done)
	})
}
```

5. **Goroutine leak detection (`go.uber.org/goleak` + Go 1.27 `goroutineleak`):**
   wire `func TestMain(m *testing.M) { goleak.VerifyTestMain(m) }` in domain and
   worker packages so any test leaking a background goroutine fails immediately.
6. **Mutation testing (`go-gremlins/gremlins`):** mutate operators and branches
   in `policy.go` / `authn` / billing math; require `>= 80%` mutation kill score
   on security-critical packages so weak assertions ("status != 500") get caught.
7. **Breaking contract diffs (`oasdiff` + `apidiff`):** run `oasdiff breaking
   main:openapi.json openapi.json` when external/mobile clients consume the API
   (and `apidiff` if publishing a Go SDK module).

Remember: **coverage is a ratchet, not a target** (§2.7). A line executed by a
test that asserts nothing is worse than an uncovered line because it looks
tested; §2.6's bite check and `gremlins`, not the percentage, prove the
assertions actually bite.

### 17.6 Where each check runs

| Gate | Every PR (`just verify`) | Nightly scheduled CI | Pre-release |
| --- | --- | --- | --- |
| `golangci-lint` + `nilaway` + `govulncheck` | Yes | Yes | Yes |
| Unit + `rapid` (100 cases) + fuzz seeds (`-race`) | Yes | Yes (`-rapid.checks=2000`) | Yes |
| `synctest` + `goleak` + real-DB integration (`-race`) | Yes | Yes | Yes |
| Playwright E2E (video on) + `:3000/healthz` container | Yes | Yes | Yes |
| `go test -fuzz=Fuzz… -fuzztime=60s` per fuzz target | Seed corpus only | **Yes** | Yes |
| `gremlins unleash` mutation testing (`policy`, `authn`) | Changed critical pkg | **Yes** | Yes |
| `benchstat` regression suite (`count=10`) | On hot-path PRs | **Yes** | Yes |

---

## 18. Architecture in Go

Five architecture rules hold in any language:

1. **Boundary before distribution** — establish the module seam inside one
   binary first; extract a network service only on measured ~10× resource
   divergence, team release blocking, compliance isolation, runtime mismatch, or
   established end-to-end ownership, moving tables into an owned schema before
   moving code.
2. **Executable dependency rules** — a dependency arrow that exists only on a
   whiteboard is already broken.
3. **One write owner per table** — one domain package owns mutations to a table;
   other domains read through that package's exported functions or a deliberate
   read model.
4. **A pattern per package, not per codebase** — differentiating core slices earn
   pure `policy.go` + explicit ports; boring admin/lookup slices stay a handler
   + `sqlc` query + integration test, avoiding *sinkhole* pass-through layers.
5. **An abstraction needs a second real implementation** — an interface with one
   implementation (plus a banned mock) is an unfulfilled prediction.

Go gives you half of Rule 2 for free: **the compiler refuses to compile any
circular import between packages**.

**Check the package graph by test, and establish `internal/kernel/` on day one.**
Even in Go, a layout sketched in prose often smuggles a hidden cycle ("just a
callback function") that `go build` only catches halfway through implementation,
tempting someone to dump domain structs into `internal/common`. Before writing
domain packages, put **only** true cross-domain shared vocabulary — typed entity
`ID`s (`RequestID`, `ActorID`), the `Clock` interface, `Secret[T]`, and closed
`Event` / `CacheTag` enums — into a stdlib-only leaf package `internal/kernel/`
(zero SQL, zero HTTP, zero business logic), encode the allowed package DAG in
`internal/arch_test.go`, and verify `arch_test.go` fails on a violating fixture
(§2.7).

### 18.1 The Go compiler is the architecture boundary

Go gives you two rock-solid compile-time primitives out of the box:

1. **`internal/` visibility:** no external module can import anything under
   `internal/`. Never create a top-level `pkg/` directory in an application
   repository — `pkg/` is an obsolete pre-modules habit that surrenders compiler
   encapsulation for imaginary reuse.
2. **Acyclic package graph:** `go build` refuses to compile any circular import
   between two packages. Used well, this keeps domain dependencies clean forever;
   used poorly (micro-packages), it causes "import cycle hell".

### 18.2 When splitting packages pays (and the micro-package trap)

Unlike Rust crates (where Cargo compiles a whole crate per dependency unit), **Go
already compiles and caches at the individual directory/package level in
milliseconds**. Splitting one domain (`requests`) into four sub-packages
(`internal/requests/domain`, `internal/requests/repo`, `internal/requests/service`,
`internal/requests/http`) buys zero compile speed, immediately triggers circular
imports, and tempts developers to dump shared structs into a toxic
`internal/common/types` grab-bag!

Keep **one package per bounded domain** (`internal/requests/`), split cleanly
across focused files (`model.go`, `policy.go`, `handlers.go`, `queries.sql.go`)
until a domain genuinely exceeds ~2,500 lines or sprouts an independent sub-domain.

### 18.3 The port: concrete struct, closed switch, or 1–2 method consumer interface

Do not port Hexagonal Architecture's Java ceremony literally (`ports/inbound/`,
`ports/outbound/`, `RequestServiceImpl`). In Go:

- Inbound "ports" are simply the exported functions and HTTP handlers of
  `package requests`.
- Postgres persistence is `queries.sql` → `Queries` inside `internal/requests/`
  tested against real `pgtestdb` (§2.1).
- External side-effects (email, S3, Singpass OIDC, Stripe) are `1–3` method
  interfaces **defined inside the domain package that calls them** (§15.6) and
  implemented by adapter packages under `internal/platform/<adapter>/`.

### 18.4 Concrete `Deps` state vs globals and `context.Value` bags

Wire all shared infrastructure in `cmd/server/main.go` into an explicit struct
passed into domain route registration — zero globals, zero reflection containers.
`context.Context` carries **only** request-scoped cross-cutting metadata
(cancellation/deadlines, OTel span, request ID, authenticated `Actor` via an
unexported key `type actorCtxKey struct{}`), **never** `*pgxpool.Pool`, `Config`,
or domain stores.

### 18.5 Canonical layout and executable `arch_test.go`

```text
cmd/
  server/main.go            # CLI dispatch (serve | migrate | healthcheck | dump-openapi)
internal/
  arch_test.go              # Enforces package dependency DAG in `go test`!
  kernel/                   # Stdlib-only shared vocabulary leaf (IDs, Clock, Secret, Event)
  actors/                   # Foundational domain (imports kernel & platform, no sibling domains)
    doc.go
    model.go
    queries.sql
    queries.sql.go
  authn/                    # Session / OIDC / CSRF middleware; depends on actors & kernel
  requests/                 # Feature domain; may import actors, kernel & platform, never cmd/
    doc.go
    model.go
    policy.go               # Pure functional core (zero pgx / http imports)
    handlers.go
    queries.sql
    queries.sql.go
    requests_test.go
  wire/external/            # Third-party webhook DTOs (sole custom-casing island)
  platform/                 # Domain-agnostic infrastructure (may import kernel, zero domain imports!)
    config/
    clock/
    effects/
    httpx/
    problem/
    telemetry/
    testdb/
db/
  schema.sql                # Wholesale current snapshot (§5)
  seed.sql
migrations/
  embed.go
  00001_initial.sql
```

Enforce the arrow of dependencies with a 45-line `internal/arch_test.go` using
`golang.org/x/tools/go/packages` (plus a unit test asserting `checkGraph` flags
a synthetic forbidden edge, §2.7) — zero external DSL required:

```go
package internal_test

import (
	"strings"
	"testing"

	"golang.org/x/tools/go/packages"
)

func TestArchitectureBoundaries(t *testing.T) {
	t.Parallel()
	cfg := &packages.Config{Mode: packages.NeedName | packages.NeedImports}
	pkgs, err := packages.Load(cfg, "./...")
	if err != nil {
		t.Fatalf("load packages: %v", err)
	}
	for _, pkg := range pkgs {
		isKernel := strings.HasSuffix(pkg.PkgPath, "/internal/kernel")
		isPlatform := strings.Contains(pkg.PkgPath, "/internal/platform/")
		for imp := range pkg.Imports {
			if strings.Contains(imp, "/cmd/") {
				t.Errorf("%s must never import entrypoint %s", pkg.PkgPath, imp)
			}
			if isKernel && strings.Contains(imp, "/internal/") {
				t.Errorf("kernel leaf %s must not import internal package %s", pkg.PkgPath, imp)
			}
			if isPlatform && (strings.Contains(imp, "/internal/requests") || strings.Contains(imp, "/internal/actors")) {
				t.Errorf("platform package %s must stay domain-agnostic, imported %s", pkg.PkgPath, imp)
			}
		}
	}
}
```

### 18.6 Ten Go-specific architecture anti-patterns

1. **`pkg/` directory in an app repo** — leaks internal types; use `internal/`.
2. **`internal/models` / `internal/types` shared grab-bag** — couples every
   domain together to dodge import cycles instead of keeping `internal/kernel/`
   restricted to zero-logic shared IDs/events.
3. **`internal/utils` / `common` / `helpers`** — attracts unrelated functions;
   name packages for what they provide (`httpx`, `clock`, `problem`).
4. **Horizontal MVC folders (`controllers/`, `services/`, `repositories/`)** —
   scatters one feature across four directories and forces mapper ceremony.
5. **1-to-1 `Repository` interfaces for `sqlc` queries** — mocks the unmockable
   (§2.1) and hides SQL errors behind fake abstractions.
6. **`context.WithValue` dependency injection** — hides dependencies from
   function signatures and panics when a middleware order changes.
7. **Package-level `var` singletons + `func init()`** — invisible boot side
   effects and flaky parallel tests.
8. **Leaking `pgconn.PgError` or `sql.ErrNoRows` above domain boundaries** —
   translate driver errors into domain errors inside `internal/<domain>/`.
9. **Domain `policy.go` importing `net/http` or `pgx/v5`** — ruins the pure
   functional core (§15.8).
10. **Premature `go.work` multi-module split** — pays multi-module versioning
    taxes when a single `go.mod` + `arch_test.go` compiles in `< 2 s`.

### 18.7 Architecture review checklist

- [ ] Zero `pkg/`, `internal/utils`, `internal/common`, or `internal/mappers` directories.
- [ ] `internal/kernel` imports only Go standard-library packages.
- [ ] `internal/platform/*` imports zero domain packages (verified by `arch_test.go`).
- [ ] Domain packages form an explicit DAG (`kernel` ← `actors` ← `authn` ← `requests`).
- [ ] Pure business rules in `policy.go` have zero database or HTTP imports.
- [ ] Interfaces live in consumer packages and have ≥ 2 real implementations.
- [ ] `sql.ErrNoRows` / `pgx.ErrNoRows` and `pgconn.PgError` are translated inside the owning domain.
- [ ] `cmd/server/main.go` owns the entire wiring graph and shutdown sequence.

---

## 19. Keeping this template honest

This file is itself a living document, and a `CLAUDE.md` that nobody prunes rots
faster than the code it governs: agents follow dead rules religiously or learn
to ignore all of them. Maintain it the way it asks you to maintain a project:

- **Every rule here has an automated backstop** — `go build`, `.golangci.yml` v2,
  `nilaway`, `sqlc compile`, `govulncheck`, `arch_test.go`, `check-standards`,
  `check-decisions.sh`, `check-schema-parity.sh`, `check-module-age.sh`, or the
  route IDOR meta-test. Never add a prose rule without wiring the check that
  fails CI when it breaks.
- **Re-verify versions and platform facts on Go's six-month cadence (February &
  August), and quarterly against SHIP-HATS.** The `DR-02` and `DR-04` ecosystems
  move fast, and SHIP-HATS rules in §10.2 shifted four times in 2026 alone
  (Rekor decommissioning, Nexus IQ's seven-day module-age gate, EOL image
  blocking, PAT-only Git over HTTPS). Note security point releases (`go1.27.3`)
  explicitly and retire third-party shims once stdlib absorbs them (`uuid`,
  `encoding/json/v2`, `slog.NewMultiHandler`, `errors.AsType`,
  `http.CrossOriginProtection`, `testing/synctest`, `WaitGroup.Go`,
  `goroutineleak`).
- **Never renumber a `DR-` or an addendum.** Teams cite them in doc comments,
  PRs, and audit responses. Add a new card or a superseding addendum rather than
  editing an identifier's meaning.
- **When a default flips, update the sections that assume it in the same commit.**
  §2, §4, §5, §6, §9, and §10 each assume §0.7's defaults. Changing §0.7 while
  leaving §4 on the old tool causes agents to follow whichever section they read
  first.
- **Add a card only when the choice is genuinely open.** Every new question taxes
  kickoff attention. If the answer does not vary by project, make it an
  invariant in a section, not a `DR-` card.
- **Keep every code snippet compiling.** Maintain a tiny scratch module in CI or
  during quarterly reviews that compiles every Go excerpt in this file against
  the pinned `go.mod` versions so upstream signature changes are caught here
  before a user hits them.
- **Re-verify §13 against the pinned `golangci-lint` v2 release.** Run
  `golangci-lint config verify` and diff `golangci-lint linters` on every minor
  bump (`v2.x`) so deprecated or renamed linters never break a bootstrap build.
- **Re-verify OpenTelemetry signal stability in §16.8** (`otel/log` + `sdk/log`
  reached `1.x` GA while `otel/log/global` was deprecated; `otelslog` and
  `otelhttp` `0.x` bridge versions still step in lockstep with `otel` `v1.x`).
- **State what each revision of this template actually verified.** The October
  2026 initial authoring and `DR-11` / `§2.5–§2.8` / `§15.11` / `§20` revision of
  this file were made in a sandbox without a `go` toolchain installed (`go` not
  present on `PATH`). All Go `1.27` stdlib and third-party API signatures
  (`uuid`, `encoding/json/v2`, `goose.WithSlog`, `httptest.NewTestServer`,
  `synctest.Sleep`, `fergusstrange/embedded-postgres` `v1.34.0`) were verified
  against `go.dev/doc/go1.27` and `pkg.go.dev`, and internal `§` and `DR-01`…
  `DR-11` cross-references were checked by script, **but the Go code excerpts
  were not compiled locally**; compile-check every excerpt in the scratch module
  above on the first pass with `go1.27.3` available.
- **Do not let §15 grow into a pattern catalogue.** A pattern earns its place
  only by naming both the bug class it eliminates and the condition under which
  using it is wrong; turning every post-mortem into a lint rule or `synctest`
  gate beats adding paragraphs.

If a rule here conflicts with the language you actually chose, you are in the
wrong variant. [`GREENFIELD.md`](GREENFIELD.md) is the language-neutral
template; to write a variant for another language, keep its section order,
replace each mechanism with the target language's idiomatic equivalent, and
preserve every language-independent invariant (real-database tests, soft
deletion, bite checks, honest validation, single-source decisions).

---

## 20. Porting an existing system to Go

Everything in §0–§19 assumes a blank slate. Porting a live Python, Node.js,
Ruby, PHP, or Java system to Go is harder in one specific way: the legacy code
is simultaneously **the specification and the system being retired**, and the
costliest bugs are quiet semantic shifts — a `nil` slice serialised as `null`
instead of `[]`, a `-0.5` rounded to `-1` instead of `0`, or a randomised Go
`map` changing response order. Apply the rules below **on top of** §0–§19.

### 20.1 Scope, then the oracle

- **Fix the port boundary before writing code.** State explicitly which layers
  move to Go (HTTP API, worker, domain rules) and which stay unchanged (often
  the browser UI). Any boundary that stays must remain byte- and status-compatible
  (including existing `401`/`403` vs `404` codes until an addendum changes them,
  §2.2) and have its client types generated from the new Go contract (§6.1).
- **Keep the legacy system runnable as the executable oracle.** Answer *"what
  does the old service return on X?"* by executing the old service against the
  input, never by eye-reading dynamic Python/JS code and guessing.
- **Classify legacy test files mechanically before porting a single test.** Run
  a script counting HTTP requests, internal module imports, and raw DB touches
  per test file to bucket every file into:
  1. *Pure black-box HTTP/E2E* — port directly or point at the Go backend;
  2. *Black-box HTTP + internal helpers* — keep the HTTP assertions, replace
     setup with SQL fixtures (§3);
  3. *White-box unit tests over legacy internals* — re-derive from the spec and
     golden fixtures rather than translating legacy class mocks into Go.
  Track every file in a committed ledger so "port the tests" never stalls silently.
- **Make the existing Playwright / black-box E2E suite switchable via one env
  var** (`TARGET_BACKEND=legacy|go`) so the exact same browser suite runs
  unchanged against both servers.

### 20.2 Golden fixtures exported from the legacy implementation

- **Export, never hand-type.** Run the legacy implementation across an input
  corpus for every pure calculation, validator, slugifier, and parser, writing
  committed `{input, expectedOutput}` JSON/NDJSON fixtures plus a manifest of
  fixture counts checked against the legacy test runner.
- **Validator fixtures assert both normalised output and error message keys**,
  catching subtle trim/Unicode-normalisation or precedence shifts, not just
  boolean pass/fail.
- **Generate fixtures via a repeatable script and never hand-edit them** to make
  a failing Go test pass.

### 20.3 Determinism hazards when porting to Go

Audit every calculation, sort, hash, and serializer against these nine Go traps
before porting domain logic:

| Hazard | Typical legacy behaviour (JS / Python / Java) | Go `1.27` rule |
| --- | --- | --- |
| **Map iteration order** | Insertion-ordered (`JS Map`/`Object`, Python `dict`) | Go **intentionally randomises `map` iteration per run**; `encoding/json` sorts `map[string]V` alphabetically! Use a slice of structs or explicit key sort wherever order is observable |
| **Empty / `nil` slice on the wire** | Empty list is always `[]` | `encoding/json` v1 marshals `var s []T` (`nil`) as **`null`**! Either use `encoding/json/v2` (which marshals `nil` slices as `[]` by default) or initialise `make([]T, 0)` / custom marshaler consistently |
| **Sort stability** | `Array.prototype.sort` (ES2019+) and Python `timsort` are **stable** | `slices.SortFunc` / `sort.Slice` are **unstable** (`pdqsort`)! Use **`slices.SortStableFunc`** with a total tie-breaker comparator |
| **Rounding `.5` ties (especially negatives)** | JS `Math.round(-0.5)` is `-0` ($+\infty$); Python `round(-0.5)` is `0` (half-to-even) | Go `math.Round(-0.5)` is **`-1`** (half away from zero); `math.RoundToEven(-0.5)` is **`0`**! Write one golden-tested rounding helper matching the legacy contract and Postgres `numeric` |
| **Floating-point & money** | JS `number` is IEEE-754 `float64` everywhere | Use `int64` minor units or `shopspring/decimal` for money; where IEEE-754 parity is required, test `NaN`/`±Inf` explicitly (`json` rejects both!) |
| **Integer width & bitwise math** | JS `\| 0` and `Math.imul` wrap signed **32-bit**; Python `int` is arbitrary-precision | Go `int` is **64-bit** on 64-bit hosts and wraps silently on overflow; use explicit `int32`/`uint32` for legacy hash math and checked bounds on inputs |
| **String length & slicing** | JS `.length` = UTF-16 code units; Python `len(s)` = Unicode code points | Go `len(s)` = **UTF-8 bytes**; `utf8.RuneCountInString(s)` = code points; `rivo/uniseg` = grapheme clusters. Pick the exact unit per validation rule and test with CJK + emoji |
| **Missing vs `null` vs zero** | `undefined` vs `null` vs `""`/`0`/`false` | Go zero values (`""`, `0`, `false`) conflate with omitted unless `PatchField[T]` (§14.3) or pointer/presence tracking is used at the wire edge |
| **Ambient clock & RNG** | `Date.now()` / `datetime.now()` / `Math.random()` called inline | Count every ambient clock/random site in the legacy repo first; inject `Clock` and seeded `math/rand/v2` (§2.4, §3) in Go |

### 20.4 The shadow run: diffing legacy and Go live

- **Run both servers against twin Postgres databases seeded identically**,
  comparing HTTP status, headers, body, **and persisted table rows** side by
  side.
- **Put all non-determinism rules inside one unit-tested normaliser:**
  timestamps within a tight request window map to `<NOW>` (timestamps outside
  the window are **flagged**, never masked!), minted UUIDv7s alias by first-seen
  order (`<ID_1>`, `<ID_2>`), random tokens validate length + alphabet before
  aliasing, unordered sets sort *only* where the API contract declares order
  insignificant, and numeric fields compare exact.
- **Compare status class before body**, and compare SSE/WebSocket streams frame
  by frame (event type, payload, and retry/timing fields within bounded ranges).
- **Maintain a decision-backed divergence allow-list** — any difference without
  an accepted addendum ID fails the shadow run.
- **Prove the shadow harness fails** (§2.7): run legacy-vs-legacy (must report
  `0` false positives) and legacy-vs-sabotaged-legacy (mutated status, mutated
  field, dropped SSE frame, reordered list — every single one must fail!).
- **Compile a test-only deterministic mode** (`//go:build deterministic`: fixed
  `Clock`, seeded UUIDv7 entropy) for byte-identical replay tests, and verify in
  CI (`go list` / build flags check) that release binaries never include the
  `deterministic` build tag.

### 20.5 Sharing domain rules with the browser (and why Go WASM is rarely step one)

Unlike Rust (`wasm32-unknown-unknown` in `~100–250 KB`), standard Go
`GOOS=js GOARCH=wasm` embeds the Go scheduler and garbage collector into a
**`~2–5 MB` raw (`~600 KB–1.2 MB` brotli)** binary, while TinyGo subsets
reflection and `encoding/json/v2`. Choose the lightest tier that fits:

1. **Default — server evaluation + generated data catalogues (§6.1):** move
   shared bounds, state tables, regexes, and asset-cache rules into Go data
   structures, generate `frontend/src/lib/generated/rules.ts`, and delete
   duplicated client copies.
2. **Offline pure client engine already in TypeScript:** keep the client engine
   pure and validate both the Go package and the TS package against the exact
   same committed golden fixture corpus (§20.2).
3. **`GOOS=js GOARCH=wasm` (only for heavy offline editors/simulations):**
   isolate the engine in a pure Go package (zero `net/http`, zero `pgx`, zero
   goroutine leaks), expose a **versioned JSON-in / JSON-out facade** (`schemaVersion`
   checked on load) with `defer recover()` panic containment at the WASM boundary,
   lazy-load it as an immutable hashed asset only on screens that need it, and
   ratchet its brotli byte size in CI.

### 20.6 Surfacing quiet legacy assumptions before designing

Audit the legacy codebase up front and record each finding as an addendum:

- **Implicit single-process state:** in-memory caches, rate-limit maps, SSE hubs,
  one-time challenge maps, and `setInterval` cron loops assume `replicas = 1`.
  Either move state to Postgres or, if staying single-instance initially, acquire
  a **Postgres session advisory lock at startup** so an accidental second pod
  refuses to boot loudly instead of splitting live memory.
- **Write-then-publish conventions:** replace fragile legacy event hooks with
  `effects.Outcome[T]` (§15.11).
- **Bugs you are tempted to "clean up along the way":** missing CSRF, quirky
  status codes, multiple auth headers, non-transactional writes. Track every one
  in a **divergence log** (*kept for parity* · *changed by addendum NNNN* · *to
  decide*). Fixing quirks silently during a port makes shadow diffs unreadable.
- **Single-writer test-DB workarounds:** if the legacy suite serialised tests or
  throttled uploads to appease SQLite or WASM `PGlite`, document why each
  workaround existed before deleting it on real `pgtestdb` Postgres.
- **Legacy runtime boot scripts:** fold Python/Node/Bash seed or provisioning
  scripts into `/app/server` subcommands so `distroless/static` ships clean.

### 20.7 The package dependency graph is deliverable one

Sketch the `internal/` package DAG (`internal/kernel` → foundational domains →
feature domains → `cmd/server`), encode it in `internal/arch_test.go` (§18.5)
with a failing-cycle fixture, and keep `/healthz`, `/readyz`, and publisher
wiring in the `cmd/server` composition root so domain packages never import each
other circularly.

### 20.8 Cutover and retirement

- **Cut over per domain on objective gates, never a calendar date:** all golden
  and characterisation suites green, consecutive full-scenario shadow runs with
  zero unexplained divergences, and §8.3 same-machine tail-latency parity.
- **Exercise rollback before cutover:** freeze schema changes during the shadow
  window and boot the legacy image against the shared database in staging to
  prove rollback actually works.
- **Retire in one deliberate commit** once the rollback window closes: delete
  the shadow harness, legacy code, and temporary parity shims together rather
  than leaving dead scaffolding forever.

---

## 21. Egress-restricted sandboxes and pure-Go client/server bootstrap

Cloud coding sandboxes (such as Arena / E2B Debian 12 `bookworm` `x86_64`
containers) often omit `go` and `chromium` from the base image and block TLS
handshakes to Google-hosted Go infrastructure. Standard `curl https://go.dev/dl/...`
and default `go get` invocations fail immediately unless you bootstrap from an
allowed registry and route module resolution directly through `github.com`.

### 21.1 Sandbox baseline and outbound firewall reality

| Layer | Present / Allowed | Missing / TLS-Blocked (`SSL_ERROR_SYSCALL` / `EOF`) |
| --- | --- | --- |
| **System tools** | `gcc`/`cc` (CGO & `-race` work natively), `ld`, `ar`, `node` (v22.22+), `npm`, `python3`, `pip`, `unzip`, `curl`, `tar`, `git`, `gh` | `go`, `gofmt`, `golangci-lint`, `chromium` |
| **Outbound HTTPS** | `github.com`, `api.github.com`, `codeload.github.com`, `pypi.org`, `files.pythonhosted.org`, `registry.npmjs.org` | `go.dev`, `dl.google.com`, `proxy.golang.org`, `sum.golang.org`, `golang.org`, `gopkg.in`, `deb.debian.org`, `objects.githubusercontent.com` |
| **Snapshot exclusions** | `/tmp/*` plus workspace dirs named `.arena`, `.cache`, `.local`, `build`, `dist`, `node_modules`, `target` | Non-excluded directories under `/home/user` count toward the ~128 MB / 10,000-file turn-end snapshot cap |

Keep `GOROOT`, `GOMODCACHE`, `GOCACHE`, and unpacked browser binaries under
`/tmp/*` (or an excluded `.arena/` / `.cache/` folder) — never under default
`~/go/pkg/mod`, which lives inside `/home/user` and is *not* excluded from
workspace snapshots.

### 21.2 Zero-guesswork Go 1.27.3 install from PyPI (~4 s)

Full `linux/amd64` Go 1.27.3 (`go`, `gofmt`, stdlib, `lib/wasm`, and C/race
tooling) ships as a prebuilt `manylinux` wheel on PyPI (`go-bin==1.27.3`):

```bash
set -euo pipefail
GO_STAGE="/tmp/go-stage"
export GOROOT="/tmp/go-1.27"
rm -rf "$GO_STAGE" "$GOROOT" && mkdir -p "$GO_STAGE"

pip download --no-deps --only-binary=:all: --dest "$GO_STAGE" "go-bin==1.27.3" >/dev/null
unzip -q "$GO_STAGE"/go_bin-*.whl -d "$GO_STAGE/unpacked"
mv "$GO_STAGE/unpacked/go" "$GOROOT"

# MANDATORY: wheel zip archives strip +x bits on go, gofmt, compile, link, asm, cgo, and vet.
chmod -R +x "$GOROOT/bin" "$GOROOT/pkg/tool"
rm -rf "$GO_STAGE"

export PATH="$GOROOT/bin:$PATH"
export GOPROXY="direct"
export GOSUMDB="off"
export GOMODCACHE="/tmp/go-mod-cache"
export GOCACHE="/tmp/go-build-cache"

go version
```

### 21.3 Module resolution when `proxy.golang.org` and `sum.golang.org` are blocked

1. **Always set *both* `GOPROXY=direct` and `GOSUMDB=off`.** Setting
   `GOPROXY=direct` alone clones `github.com/*` modules via `git` and then fails
   verification with `Get "https://sum.golang.org/lookup/...": EOF`.
2. **Rewrite vanity import domains (`golang.org/x/*`, `gopkg.in/*`) to their
   `github.com` mirrors in `go.mod`.** Under `GOPROXY=direct`, Go resolves
   non-GitHub module paths via `https://<vanity>?go-get=1`, which the SNI
   firewall drops (`unrecognized import path "golang.org/x/sync": EOF`). One
   `replace` directive per `golang.org/x/*` family routes Git directly to
   `github.com/golang/*`:

   ```bash
   go mod edit \
     -replace=golang.org/x/sync=github.com/golang/sync@v0.12.0 \
     -replace=golang.org/x/sys=github.com/golang/sys@v0.31.0 \
     -replace=golang.org/x/net=github.com/golang/net@v0.37.0 \
     -replace=golang.org/x/text=github.com/golang/text@v0.23.0 \
     -replace=golang.org/x/crypto=github.com/golang/crypto@v0.36.0
   go mod tidy
   ```

3. **Zero-external-module stdlib remains fastest for self-contained apps.** Go
   1.22–1.27 `net/http.ServeMux` (`"GET /{$}"`, `"POST /api/verify"`), `embed`,
   `encoding/json`, `log/slog`, `sync/atomic`, and `net/http/httptest` cover full
   REST + static/Wasm servers with zero network dependency fetches and native
   `go test -race ./...` support via Debian's preinstalled `gcc`.

### 21.4 Pure-Go backend + pure-Go `GOOS=js GOARCH=wasm` frontend (no Next.js)

When building a pure-Go backend paired with a compiled Go WebAssembly browser
client from scratch, four Go 1.24–1.27 details save immediate debugging:

1. **`wasm_exec.js` moved in Go 1.24+.** Legacy `$(go env GOROOT)/misc/wasm/wasm_exec.js`
   no longer exists in Go 1.27 (`misc/wasm/` holds only `wasm_exec.html`). Copy
   from `lib/wasm/` instead:

   ```bash
   cp "$(go env GOROOT)/lib/wasm/wasm_exec.js" internal/server/static/wasm_exec.js
   ```

   Go 1.27 also ships `$(go env GOROOT)/lib/wasm/wasm_exec_node.js`, allowing
   `GOOS=js GOARCH=wasm` packages to run unit tests directly under preinstalled
   Node 22 in `< 0.1 s` without launching a browser:

   ```bash
   GOOS=js GOARCH=wasm go test -exec="node $(go env GOROOT)/lib/wasm/wasm_exec_node.js" ./internal/ui
   ```

2. **Three `syscall/js` runtime invariants (`//go:build js && wasm`):**
   - **End `main()` with `select {}`.** Returning from `main()` terminates the
     Go Wasm instance, causing subsequent `js.FuncOf` DOM event listeners to
     throw `Error: Go program has already exited`.
   - **Never perform blocking HTTP/channel waits synchronously on a `js.FuncOf`
     callback stack.** Spawn `go func() { ... }()` inside `click`/`submit`
     handlers; blocking the callback stack deadlocks the browser's single-threaded
     JS event loop before `fetch()` can resolve.
   - **Keep pure view/filter/JSON logic in a platform-neutral `internal/ui`
     package** (no `syscall/js` import) so `go test -race ./...` exercises 100%
     of rendering, escaping, and state filtering natively on `linux/amd64`.
3. **Measured `.wasm` payload trade-off (`net/http` vs `syscall/js` `fetch`):**
   - Importing `net/http` inside `cmd/wasm` gives zero-JS-glue `http.Get("/api/...")`
     and `http.Post("/api/...", ...)` (backed by stdlib `roundtrip_js.go`), at a
     measured binary size of **`~11.9 MB` raw / `~3.0 MB` gzipped**.
   - Calling `js.Global().Call("fetch", ...)` via a thin `syscall/js` Promise
     helper (dropping `net/http` from the Wasm import graph) cuts the artifact
     **2.8×** to **`~4.2 MB` raw / `~1.17 MB` gzipped**. Serve `/app.wasm` with
     `Content-Type: application/wasm` (and `compress/gzip` when `Accept-Encoding`
     permits).
4. **Single-binary build & test pipeline (`//go:generate` + `//go:embed`):**

   ```go
   // In internal/server/server.go:
   //go:generate sh -c "cp \"$(go env GOROOT)/lib/wasm/wasm_exec.js\" static/wasm_exec.js && GOOS=js GOARCH=wasm go build -ldflags=\"-s -w\" -o static/app.wasm ../../cmd/wasm"
   //go:embed static/index.html static/wasm_exec.js static/app.wasm
   var embeddedAssets embed.FS
   ```

   ```bash
   go generate ./... \
     && go build -ldflags="-s -w" -o bin/go-service ./cmd/server \
     && go test -race -v ./...
   ```

### 21.5 Live-preview networking and offline Chromium E2E verification

- **Exact root route + `0.0.0.0` binding:** register the HTML shell on
  `mux.HandleFunc("GET /{$}", ...)` (Go 1.22+ exact-root syntax; `"GET /"` acts
  as a catch-all subtree prefix), add `mux.HandleFunc("GET /favicon.ico", ...)`
  returning `204 No Content` so Chromium emits zero console 404s, bind
  `http.Server` to `0.0.0.0:${PORT:-3002}` with `ReadHeaderTimeout: 5 * time.Second`,
  accept proxy `Host` headers (`https://{port}-{sandboxId}.e2b.app`), and call
  strictly relative `/api/*` paths from browser/Wasm code.
- **Headless Chromium 150 E2E without `apt-get`:** install `playwright-core` and
  `@toolchain-bin/aimeeting-sandbox-chromium` from `registry.npmjs.org` with
  `export AIMEETING_BROWSER_HOME="/tmp/aimeeting-browser"` (keeps the `394 MiB`
  unpacked browser + Debian 12 `lib/*.so` closure out of `/home/user` snapshots)
  and pass `LD_LIBRARY_PATH: browserPkg.libraryPath()` +
  `args: ["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"]` to
  `chromium.launch(...)`.




