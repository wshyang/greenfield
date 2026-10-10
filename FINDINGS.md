# FINDINGS.md — Go Greenfield Best Practices & Design Patterns Research (October 2026)

> **Purpose:** Iterates top-to-bottom through every section (`Preamble`, `§0–§19`) and every directive (`D-00.1`..`D-19.1`) tabulated in `TEMP-PLANNING.md`, documenting October-2026-verified Go (`Go 1.27` / `go1.27.3`) language mechanics, standard-library additions, ecosystem trade-offs, design patterns, and exact translation decisions for `GREENFIELD-GO.md`.

---

## Baseline — Verified Go Toolchain & Ecosystem Versions (October 2026)

### Go Release Progression (`Go 1.24` → `Go 1.27.3`)

| Release | Date | Verified Features Shaping Idiomatic Go in October 2026 |
| --- | --- | --- |
| **Go 1.24** | Feb 2025 | `tool` directives in `go.mod` (`go get -tool`, `go tool <binary>`) replacing `tools.go`; `testing.T.Context()` & `testing.B.Loop()`; `os.Root` traversal-resistant filesystem handles; `omitzero` JSON struct tag; Swiss Table `map` runtime; native FIPS 140-3 module. |
| **Go 1.25** | Aug 2025 (`1.25.14`) | **Container-aware `GOMAXPROCS`** on Linux cgroups v1/v2 with dynamic runtime updates (obsoletes `go.uber.org/automaxprocs`); **`net/http.CrossOriginProtection`** tokenless W3C Fetch-Metadata (`Sec-Fetch-Site`) + `Origin`/`Host` CSRF defense; **GA `testing/synctest`** (`synctest.Test`, `synctest.Wait`) deterministic virtual-clock concurrency testing; **`sync.WaitGroup.Go(fn)`**; **`runtime/trace.FlightRecorder`** ring-buffer flight recorder; `go vet` `waitgroup` & `hostport` analyzers. |
| **Go 1.26** | Feb 2026 (`1.26.10` Oct 2026) | **`errors.AsType[E error](err) (E, bool)`** generic, reflection-free, compile-checked error unwrapping; **`new(expr)`** expression operand (`new("active")`, `new(int32(50))`); **Green Tea GC** enabled by default (`10–40%` lower GC CPU overhead); **`log/slog.NewMultiHandler`** fan-out handler; `net/http.ServeMux` status-preserving `307` trailing-slash redirects. |
| **Go 1.27** | **19 Aug 2026** (latest patch **`go1.27.3`**, 21–24 Oct 2026, fixing `GO-2026-6809`) | **Stdlib `uuid` package** (`uuid.UUID`, `uuid.NewV7()`, `uuid.NewV4()`, `uuid.Parse()`, `uuid.Nil()`, `MarshalText`/`UnmarshalText`/`AppendText` per RFC 9562); **Stdlib `encoding/json/v2` & `encoding/json/jsontext`** (rejects invalid UTF-8 and duplicate JSON keys by default, `jsonv2.RejectUnknownMembers(true)`, streaming `MarshalWrite`/`UnmarshalRead`); **GA `goroutineleak` profile** in `runtime/pprof` and `/debug/pprof/goroutineleak` (GC-reachability detection of permanently blocked goroutines); **generic methods** on types; **`net/http/httptest.NewTestServer`** in-memory fake network server wired for `testing/synctest`; **`crypto/mldsa`** (FIPS 204); `bytes.CutLast` / `strings.CutLast`; `go test` runs `stdversion` vet analyzer by default; `go vet` `printf` flags `%w` on `*E` when `E` implements `error` by value; `30%` faster `<80B` allocations. |

### Verified Ecosystem Modules (October 2026, >7 Days Aged for Nexus IQ)

| Area | Module | Verified Version | Status & Key Finding |
| --- | --- | --- | --- |
| **HTTP Router (`DR-01`)** | `github.com/go-chi/chi/v5` / `net/http.ServeMux` | `v5.3.2` / stdlib `1.27` | Both are 100% `net/http.Handler` + `context.Context` native (`r.Pattern` populated for low-cardinality RED metrics). Avoid `fiber`/`fasthttp` (breaks `net/http`, `otelhttp`, `scs`, `CrossOriginProtection`). |
| **Data Access (`DR-02`)** | `github.com/sqlc-dev/sqlc` + `github.com/jackc/pgx/v5` | `v1.31.1` + `v5.11.0` | Compile-checked SQL -> zero-reflection Go code on native `pgx/v5` binary wire protocol; alternatives: `stephenafamo/bob` (typed SQL DSL + schema codegen) or `entgo.io/ent` / `uptrace/bun`. |
| **Migrations (`§5`)** | `github.com/pressly/goose/v3` | `v3.29.0` | `goose.NewProvider` + `//go:embed` + `lock.NewPostgresSessionLocker` (or `NewPostgresTableLocker` behind PgBouncer) + `-- +goose NO TRANSACTION`. |
| **Test DB Isolation (`§2.1`)** | `github.com/peterldowns/pgtestdb` | `v0.1.1` | Migrates hashed template DB once under advisory lock; clones per-`t.Parallel()` test DB via `CREATE DATABASE ... TEMPLATE` in `~10–30ms` with non-superuser role. |
| **Wire Contract (`DR-04`)** | `github.com/danielgtaylor/huma/v2` / `oapi-codegen/v2` / `connectrpc.com/connect` | `v2.39.1` / `v2.8.0` / `v1.21.1` (`v2.0.2`) | `huma/v2` emits OpenAPI 3.1 + RFC 9457 `problem+json` from Go structs (`humachi`/`humago`); `oapi-codegen/v2` (`strict-server`) handles spec-first OAS; `connectrpc` serves Protobuf/JSON RPC over `net/http`. |
| **Server-Side UI (`DR-05`)** | `github.com/a-h/templ` | `v0.3.1070` | Compiles `.templ` HTML into type-checked, context-escaped Go functions (`v0.3.1100` cut 26 Oct 2026 — hold 7 days under SHIP-HATS Nexus IQ). |
| **Auth & Sessions (`DR-06`)** | `alexedwards/scs/v2` + `coreos/go-oidc/v3` + `golang.org/x/oauth2` + `alexedwards/argon2id` | `v2.9.0` / `v3.21.0` / `v0.37.0` / `v1.0.0` | `scs/pgxstore` reuses `pgxpool`; `http.NewCrossOriginProtection()` (Go 1.25 stdlib) supplies stateless browser CSRF defense; `go-oidc/v3` handles Singpass/CorpPass/TechPass/Entra OIDC + PKCE. |
| **Background Jobs (`DR-08`)** | SQL outbox (`SKIP LOCKED`) / `github.com/riverqueue/river` | stdlib+`pgx` / `v0.49.0` | Either a ~150-LOC SQL `FOR UPDATE SKIP LOCKED` lease outbox or `river` + `riverpgxv5` (`InsertTx` inside `pgx.Tx`) avoids dual-write bugs with zero Redis dependency. |
| **Observability (`§16`)** | `go.opentelemetry.io/otel` + `otelslog` + `otelhttp` + `exaring/otelpgx` | `v1.47.0` / `v0.21.0` / `v0.72.0` / `v0.12.0` | **All three OTel Go core signals (`otel/trace`, `otel/metric`, AND `otel/log` + `otel/sdk/log`) are stable `1.x` as of `v1.47.0`** (`otel/log/global` deprecated in `1.47.0`; `otel/sdk >= v1.45.0` patches `CVE-2026-81870`). |
| **Lint & Vuln (`§8`, `§13`)** | `golangci/golangci-lint/v2` + `uber-go/nilaway` + `golang.org/x/vuln/cmd/govulncheck` | `v2.14.0` / pseudo-pin / `v1.9.0` | `.golangci.yml` requires `version: "2"` (`formatters:` top-level key); `nilaway` catches inter-procedural nil panics; `govulncheck` verifies call-graph CVE reachability across deps + Go stdlib. |
| **Adversarial Tests (`§17`)** | `pgregory.net/rapid` + `go.uber.org/goleak` + `go-gremlins/gremlins` + `oasdiff` / `apidiff` | `v1.2.0` / `v1.3.0` / `v0.5.x` | Property shrinking (`rapid`), teardown goroutine-leak verification (`goleak`), mutation testing (`gremlins`), and OpenAPI/Go semver compatibility checks. |

---

## Top-to-Bottom Subject-Area Findings (Mapped to `TEMP-PLANNING.md`)

### Group A — Preamble & `§0`: Template Bootstrap, Invariants vs. Forks & Decision Interview (`D-00.1`–`D-00.9`)

- **`D-00.1` & `D-00.2` (Standalone Contract & Dated Versions):**
  - Mirror `GREENFIELD-RUST.md`'s 3-job framing (fix day-one invariants, stop silent stack guessing via `DR-01..DR-10`, settle reviewer-cited Go idioms in `§13–§18`) with an explicit **"Versions verified October 2026 (`Go 1.27` / `go1.27.3`; Go 1.28 lands February 2027)"** banner.
- **`D-00.3` & `D-00.4` (Copy, Prune, Unpack & Optional Section Splitting):**
  - Preserve `DR-01..DR-10` IDs permanently so addenda (`docs/decisions/NNNN-*.md`), doc comments, and `scripts/check-decisions.sh` remain cross-referenced. Optional split files follow `CLAUDE-go-<area>.md`, keeping `§0`, `§1`, and `§2` in the root `CLAUDE.md`.
- **`D-00.5` (`initial-templates/` Contextualisation):**
  - Inspection of `initial-templates/{Dockerfile,Dockerfile.dev}` confirms `Dockerfile` is a Node/static-HTML auto-detector (`node:22-alpine`) and `Dockerfile.dev` wraps `/viper-agent/entrypoint.sh` (`UID 1001`, `PORT=3000`, `VIPER_APP_PORT=3001`, `VIPER_AGENT_PORT=9111`). `GREENFIELD-GO.md` `§10.1` must replace `Dockerfile` with a multi-stage `golang:1.27.3-bookworm` -> `distroless/static-debian12:nonroot` build and show how `Dockerfile.dev` adds Go `1.27.3` + `air` + `/go/pkg/mod` & `go-build` cache mounts while keeping `/viper-agent/` intact.
- **`D-00.6`–`D-00.9` (Invariants vs. Forks, 10-Rule Interview, YAML Addenda & Go's 10 `DR` Forks):**
  - **Go Invariants:** Real-Postgres per-test isolation (`pgtestdb`), zero mocked repositories, per-route IDOR negative tests asserting unchanged DB rows, soft deletion (`expires_at`) + active-row views + FK liveness triggers, UUIDv7 (`uuid.NewV7()`) in unexported-field structs, twin schema files (`db/schema.sql` + `migrations/`), `0.0.0.0:3000` non-root container contract, zero request-path panics, `-race` + `.golangci.yml` v2 + `nilaway` + `govulncheck`.
  - **Go's 10 Genuine Ecosystem Forks (`DR-01..DR-10` in 3 Batches):**
    - *Batch 1 (Foundation — mandatory before `cmd/` or `internal/`):*
      - `DR-01` HTTP router: **A. `go-chi/chi/v5`** (recommended) · **B. stdlib `net/http.ServeMux`** · **C. `danielgtaylor/huma/v2` unified router+OpenAPI** (cross-linked with `DR-04`). *(To keep `DR-01` and `DR-04` orthogonal like Rust's `axum`/`utoipa`: `DR-01` = HTTP router (`chi/v5` vs stdlib `net/http.ServeMux` vs `labstack/echo` v4/v5), recommending `chi/v5`; `DR-04` = Wire contract (`huma/v2` on `chi`/`ServeMux` -> OpenAPI 3.1 -> `openapi-typescript` vs spec-first `oapi-codegen/v2` vs `connectrpc.com/connect` + Buf).)*
      - `DR-02` Data access: **A. `sqlc` `v1.31` + `jackc/pgx/v5` `v5.11`** (recommended) · **B. `stephenafamo/bob` + `pgx/v5` (typed SQL query builder + schema codegen)** · **C. `uptrace/bun` or `entgo.io/ent`**. (Explicitly ban `gorm.io/gorm` or warn why reflection zero-value traps violate `§4`.)
      - `DR-03` Module & package layout: **A. Single `go.mod` module with domain-vertical `internal/<domain>` packages** (recommended) · **B. Single `go.mod` with layered `internal/{domain,app,adapters}` packages** · **C. Multi-module `go.work` workspace** (only when publishing a standalone Go SDK).
    - *Batch 2 (Product Surface):*
      - `DR-04` Wire contract: **A. `huma/v2` -> OpenAPI 3.1 -> `openapi-typescript` + `openapi-fetch`** (recommended) · **B. Spec-first `oapi-codegen/v2` (`strict-server`)** · **C. `connectrpc.com/connect` + `buf`**.
      - `DR-05` Frontend: **A. React + Vite + TypeScript** (recommended for rich long-lived product UIs) · **B. `a-h/templ` + HTMX** (type-checked Go SSR) · **C. `html/template` + HTMX** (zero-codegen stdlib SSR for tiny tools).
      - `DR-06` Authentication: **A. Server-side Postgres sessions (`alexedwards/scs/v2` + `pgxstore`) + Go 1.25 `http.CrossOriginProtection`** (recommended) · **B. Stateless JWT (`lestrrat-go/jwx/v3`)** · **C. Delegated OIDC (`coreos/go-oidc/v3` + `x/oauth2` PKCE, composed with A)**.
      - `DR-07` Error wire shape: **A. RFC 9457 `application/problem+json`** (recommended) · **B. Simple envelope `{ "error": { "code", "message" } }`** · **C. Bare HTTP status codes**.
    - *Batch 3 (Operations):*
      - `DR-08` Background work: **A. Transactional SQL outbox (`FOR UPDATE SKIP LOCKED` lease) + in-process `errgroup` worker** (recommended default for zero external dependencies, ~150 LOC) · **B. `riverqueue/river` (`riverpgxv5` `InsertTx`)** (full retries/periodic cron/UI on Postgres) · **C. No background work yet**.
      - `DR-09` Runtime image: **A. `gcr.io/distroless/static-debian12:nonroot` (`CGO_ENABLED=0`)** (recommended — note Go's huge advantage over Rust here: pure-Go `CGO_ENABLED=0` uses `distroless/static` at `~2 MiB` with zero `libc` at all!) · **B. `debian:bookworm-slim`** · **C. `alpine:3.22`**.
      - `DR-10` Dev orchestration: **A. `just`** (recommended, matching sibling templates) · **B. `go run ./cmd/devtask` (pure-Go xtask equivalent)** · **C. `make`**.
  - **Cross-Decision Consistency (`§0.8`):** Document interactions (`DR-05 = templ+HTMX` downgrades `DR-04` TS client codegen while keeping OpenAPI/route parity tests; `DR-01 = stdlib ServeMux` uses `humago` instead of `humachi`; `DR-09 = distroless/static` requires `CGO_ENABLED=0` in build while CI runs `-race` with `CGO_ENABLED=1`!).

---

### Group B — `§1`: Living Spec, Addendum Discipline & Executable Go Documentation (`D-01.1`–`D-01.3`)

- **`D-01.1` & `D-01.2` (Addenda & `scripts/check-decisions.sh`):**
  - Identical `docs/decisions/NNNN-*.md` YAML frontmatter (`id`, `decision`, `status`, `decided_by`, `date`, `supersedes`) + `scripts/check-decisions.sh` scanning `cmd/` and `internal/` for unresolved `TODO(DR-xx)` markers and broken `supersedes` chains.
- **`D-01.3` (Go Doc Comments as Executable Spec):**
  - Go's `godoc` / `pkgsite` convention requires every package to have a `// Package <name> ...` comment (placed in `doc.go` or the primary file) citing its governing addendum (`// Governing decision: 0007 (DR-02).`) and every exported symbol in domain packages to carry a complete sentence starting with the symbol's name.
  - Enforce mechanically via `revive` rules `package-comments` and `exported` inside `.golangci.yml` (`§13`), plus **Testable Go Examples (`func ExampleParseEmail() { ... // Output: ... }`)** in `*_test.go`, which `go test ./...` compiles and executes automatically (Go's direct equivalent of `cargo test --doc`!).

---

### Group C — `§2` & `§3`: Real-Postgres Testing, IDOR Verification & Test Infrastructure (`D-02.1`–`D-03.1`)

- **`D-02.1` (Real-Postgres Per-Test Isolation & Socket-Free HTTP Driving):**
  - **Why not transaction-rollback test wrappers?** Wrapping a test in `BEGIN` / `ROLLBACK` breaks the moment the handler under test calls `pool.Begin(ctx)` (unless savepoints are faked via non-production interfaces) and hides transaction-commit triggers/constraints!
  - **Chosen Go Mechanism — `peterldowns/pgtestdb`:** Hashes `migrations/*.sql` + `fixtures/*.sql`, migrates a template database once under a Postgres advisory lock, and clones an isolated database per test via `CREATE DATABASE pgtestdb_<hash> TEMPLATE ...` in **`~10–30ms`**! Every `t.Parallel()` test gets its own real `*pgxpool.Pool` against a real migrated schema.
  - **Socket-free router execution:** Every Go router (`chi.Router`, `http.ServeMux`, `huma`) implements `net/http.Handler`. Tests construct `req := httptest.NewRequestWithContext(t.Context(), http.MethodGet, "/api/requests/...", nil)`, `rec := httptest.NewRecorder()`, and invoke `app.ServeHTTP(rec, req)` directly in memory with zero TCP port binding!
- **`D-02.2` (IDOR Negative Test + Unchanged-Row Assertion + Route Coverage Meta-Test):**
  - Every route test suite pairs `TestOwnerCanInvalidateOwnRequest` with `TestMalloryCannotInvalidateAlicesRequest`, asserting `http.StatusNotFound` (`404`, avoiding existence disclosure) **and** querying `SELECT expires_at IS NULL FROM requests WHERE id = $1` on `pool` to prove the rejected mutation left the row untouched.
  - **Structural enforcement:** `chi.Walk(router, ...)` inspects every registered `(method, route)` at test time and asserts a matching `*_forbidden_for_other_actor` test case exists in the route security table/test files!
- **`D-02.4` & `D-03.1` (Go Test Runner, Table Tests, Property Tests, Clock/RNG, Panic Intolerance):**
  - **Table tests:** Idiomatic `for _, tc := range cases { t.Run(tc.name, func(t *testing.T) { t.Parallel(); ... }) }` — unlike a bare `for` loop with `t.Fatal`, `t.Run` subtests execute **every** case independently and report all failures in one run (matching Rust's `rstest`!).
  - **Property tests:** `pgregory.net/rapid` (`rapid.Check(t, ...)`), committing failure seeds under `testdata/rapid/` so regressions replay deterministically.
  - **Frozen Clock & Seeded RNG:** Pass `Clock` (`type Clock func() time.Time` with `Clock.Now()`) and `math/rand/v2` `rand.New(rand.NewPCG(seed1, seed2))` (banning unseeded RNGs via `depguard`).
  - **Request-path panics fail tests:** Recovery middleware is enabled in production `Server` wiring to keep the pod alive on unexpected bugs, OR configured in test mode (`PanicMode: FailTest`) to re-panic / mark `t.Errorf` so a handler nil-dereference can **never** pass a negative test that merely expected `>= 400`!

---

### Group D — `§4` & `§5`: Database Discipline, Soft Deletion, FK Triggers, UUIDv7 & Twin Schema Evolution (`D-04.1`–`D-05.2`)

- **`D-04.1` (One Casing, One Wire Translation, Zero `mappers/`):**
  - Postgres uses `snake_case`; Go structs use exported `PascalCase` fields (required by Go visibility rules for JSON/SQL reflection or `sqlc` codegen); the wire boundary translates once via `json:"camelCase"` struct tags generated or declared on wire types.
  - **Ban `internal/mappers`, `toDTO()`, and `fromModel()` chains** via CI check + `forbidigo`. Read endpoints project directly into read shapes via `sqlc`; write endpoints decode into dedicated input structs via Go 1.27 `jsonv2.UnmarshalRead(r.Body, &input, jsonv2.RejectUnknownMembers(true))` (Go's exact equivalent of `#[serde(deny_unknown_fields)]`, blocking mass assignment of `owner_id` or `expires_at`!).
- **`D-04.2` & `D-04.3` (Single Data Layer, Soft Deletion & `active_*` Views with `sqlc`):**
  - All SQL for `requests` lives in `internal/requests/queries.sql` compiled by `sqlc` (`v1.31.1`) against `db/schema.sql` (`schema: "db/schema.sql"` in `sqlc.yaml`!).
  - **Critical `sqlc` + Postgres `VIEW` Finding:** Just like `sqlx` in Rust, PostgreSQL's catalog does not track `NOT NULL` constraints on columns projected through `CREATE VIEW active_requests AS SELECT ... FROM requests WHERE expires_at IS NULL`, causing `sqlc` to infer pointer/nullable types unless told otherwise — OR `sqlc` `column` overrides (`overrides: [{ column: "active_requests.title", not_null: true }]`) / SQL `COALESCE` / `sqlc` analyzer config resolves nullability cleanly! Document this exact `sqlc` view-nullability behaviour in `§4.3` and `DR-02` so developers aren't surprised. Writes and `RETURNING` always target the base `requests` table, never `active_requests`.
- **`D-04.4` (PL/pgSQL FK Liveness Trigger & `pgconn.PgError` `23503`):**
  - Carry the exact `assert_actor_is_active()` `BEFORE INSERT OR UPDATE` PL/pgSQL trigger raising `ERRCODE = 'foreign_key_violation'` (`23503`). In Go `pgx/v5`, unwrap with Go 1.26's `if pgErr, ok := errors.AsType[*pgconn.PgError](err); ok && pgErr.Code == pgerrcode.ForeignKeyViolation` and integration-test that inserting a request for a soft-deleted actor fails with `23503` / `422`/`409` domain error.
- **`D-04.5` (UUIDv7 in Go 1.27 Stdlib `uuid`, `timestamptz` UTC, Real System Actors, Live Authz):**
  - Go 1.27 added RFC 9562 **`uuid`** (`"uuid"`) to the standard library (`uuid.NewV7()`, `uuid.Parse()`, `uuid.Nil()`). Wrap in `type RequestID struct { v uuid.UUID }` (unexported `v`, version-checked `(u[6] >> 4) == 7` on `ParseRequestID` when strict v7 is desired, `MarshalText`/`UnmarshalText`, and `pgx` `TextValuer`/`TextScanner` or `sqlc` `overrides`).
  - Enforce `time.Time` normalized to `.UTC()` (`timestamptz` in Postgres; ban `time.Local` via `forbidigo`), migration-seeded system actor rows (zero `'system'` strings or `NULL` actor FKs), and live membership joins on every authorization query.
- **`D-05.1` & `D-05.2` (Twin `db/schema.sql` + `migrations/NNNN_*.sql`, `goose`, `pg_dump` Parity & Expand/Contract):**
  - Maintain `db/schema.sql` (+ `db/seed.sql`) AND `migrations/NNNN_*.sql` in the **same commit**. Point `sqlc.yaml` `schema:` at `db/schema.sql` for instant compilation, and run `scripts/check-schema-parity.sh` in CI applying `db/schema.sql` to `$SNAPSHOT_URL` and `goose up` (`migrations/`) to `$MIGRATED_URL`, diffing normalized `pg_dump --schema-only --no-owner`!
  - Use `goose/v3` (`v3.29.0`) with `//go:embed`, `lock.NewPostgresSessionLocker` on boot, `-- +goose NO TRANSACTION` for `CREATE INDEX CONCURRENTLY`, a standalone `/app/server migrate` subcommand, and 4-release expand → backfill → switch → contract for destructive DDL.

---

### Group E — `§6` & `§7`: Wire Contracts, `data-testid`, Function Shape, Error Centre/Edge & Go Smell Table (`D-06.1`–`D-07.5`)

- **`D-06.1`–`D-06.3` (Generated Wire Contracts, RFC 9457, `data-testid`, Copy Hygiene):**
  - With `DR-04 = A` (`huma/v2`), `/app/server dump-openapi > openapi.json` + `git diff --exit-code openapi.json` + `npx openapi-typescript openapi.json -o frontend/src/lib/api/schema.ts` + `git diff --exit-code frontend/src/lib/api/schema.ts` guarantees any Go struct rename breaks CI until TypeScript updates in lockstep. Add a Go test comparing `openapi.json` paths against `chi.Walk` routes.
  - Single RFC 9457 `application/problem+json` writer (`ApiError`) that logs raw `pgx`/internal causes via `slog.ErrorContext` and emits only safe `type`, `title`, `status`, `detail`, `instance` (never `pgconn.PgError` text or `DR-` IDs).
  - Preserve `internal/wire/external/` for third-party webhook casing, `Idempotency-Key` storage on retryable `POST`s, and `{component-kebab}__{element-role}` `data-testid` rules.
- **`D-07.1` (Function Size, Guard Clauses, Parameter Caps, Naming & CQS in Go):**
  - Enforce in `.golangci.yml` v2: `funlen` (`lines: 50`, `statements: 35`, target `<= 20`), `gocognit` (`min-complexity: 15`) + `nestif` (`max-complexity: 3`), `revive` `argument-limit` (`max: 4` in Go because `ctx context.Context` is idiomatically arg #1 + `<= 3` domain params; `> 3` domain params take an `*Input` / `Params` struct!), and `revive` `flag-parameter` banning boolean mode flags.
  - Ban weasel nouns (`*Manager`, `*Service` grab-bags, `*Factory`, `*Helper`, `util`/`common` packages — enforced by `revive` `var-naming` checks!).
- **`D-07.2` (Typed Domain Errors at Centre, Erased Only at `main`/CLI, Zero Request-Path Panics):**
  - Domain functions return typed error structs (`*NotFoundError`, `*ConflictError`, or closed `*DomainError` with `Kind` enum) unwrapped via Go 1.26's `errors.AsType[T](err)` / `errors.Is`. Ad-hoc `fmt.Errorf("...: %w", err)` chains without domain classification belong at `main`/CLI boundaries, never replacing domain error variants in handlers.
  - Ban `panic(...)`, `must*` helpers in request paths, unchecked type assertions (`errcheck.check-type-assertions: true`), and unguarded slice indexing `s[i]` without bounds check.
- **`D-07.3` (Container-Free DI, Concrete-First Hierarchy, CPU Isolation):**
  - Construct a concrete `App` / `Deps` struct (`DB *pgxpool.Pool`, `Clock Clock`, `Config Config`) in `cmd/server/main.go` (`run(ctx)`). **Forbid `type RequestRepository interface` when Postgres is the sole real implementation** (`§2.1` bans DB mocks!). Interfaces earn existence only with `>= 2` live implementations (e.g., `Mailer`: SES vs SMTP/dev sink) and are defined at the **consumer** (`1–3` methods).
  - **Go vs Tokio CPU note:** Unlike Tokio's fixed cooperative async worker threads, Go's preemptive M:N scheduler (`GOMAXPROCS`) preempts tight loops at async safe points (~10ms) and hands blocking syscalls off `P`s automatically — **however**, unbounded concurrent `argon2id` hashes (`64 MiB` RAM each!) will OOM the container and saturate all CPU cores! Bound `argon2id` / PDF / crypto work behind `golang.org/x/sync/semaphore.Weighted` (e.g., `max = GOMAXPROCS / 2`).
- **`D-07.4` & `D-07.5` (Domain-Vertical Go Packages, Frontend Hook/JSX Split & Smell Table):**
  - **Go's Multi-File Package Superpower:** In Go, every `.go` file in `internal/requests/` (`model.go`, `handlers.go`, `queries.sql.go`, `policy.go`) already shares one package namespace (`package requests`)! Splitting a `> 800`-line file into two focused `.go` files inside `internal/requests/` requires **zero barrel files and zero re-exports**, and Go's compiler rejects circular package imports natively at build time!

---

### Group F — `§8`, `§9`, `§10` & `§11`: Validation Ladder, Local Dev, Containers, SHIP-HATS & Checklist (`D-08.1`–`D-11.1`)

- **`D-08.1` & `D-08.2` (Go's 9-Rung Validation Ladder & Gate Config):**
  1. Format (`golangci-lint fmt --diff` running `gofumpt` + `goimports`)
  2. Types (`go build ./...` + `go test -run=^$ ./...` compiling all tests without running them!)
  3. Lints (`golangci-lint run ./...` + `nilaway ./...`)
  4. Unit (`CGO_ENABLED=1 go test -race -short -shuffle=on ./...`)
  5. Examples/Docs (`CGO_ENABLED=1 go test -race -run '^Example' ./...`)
  6. Integration (`CGO_ENABLED=1 go test -race -shuffle=on ./...` with `DATABASE_URL`)
  7. E2E (`npx playwright test` with video on)
  8. Supply chain (`govulncheck ./...` + `go-licenses check` + `go mod verify` + `go mod tidy -diff`)
  9. Container (`docker build`, run, `/app/server healthcheck` against `:3000/healthz`).
  - Carry the mandatory `Validation:` git commit trailer on constrained runs, `t.Skip("blocked on 0012; see TICKET-431")` governance, `.golangci.yml` v2 single source of lint truth, `nolintlint` requiring specific linter + explanation, and banning `unsafe` via `depguard`/`gosec`.
- **`D-09.1` (One-Command Dev, Typed Config, Redacted `Secret`, 3-File `.env`, Offline Builds):**
  - `just bootstrap` / `just verify` / `just up` / `just e2e` (`DR-10`), typed `Config` (`caarlos0/env/v11` or `koanf`), `Secret` struct redacting `String()`, `GoString()`, `LogValue()`, and `MarshalJSON()`, `.env.example` / `.env` / `.env.test` (distinct test DB!), and **zero-DB offline builds** (`sqlc` generates pure Go committed to git, so `go build` in Docker/CI never needs a live database or `.sqlx/` cache!).
- **`D-10.1`–`D-10.4` (Containers, CIDR Proxy Trust, SHIP-HATS Oct 2026 Go Proxy & Bash 3.2):**
  - **Container (`§10.1`):** `CGO_ENABLED=0` static build with `--mount=type=cache,target=/go/pkg/mod` and `--mount=type=cache,target=/root/.cache/go-build` into `gcr.io/distroless/static-debian12:nonroot`, `USER 65532:65532`, `HOST=0.0.0.0 PORT=3000`, `/app/server healthcheck`, embedded `goose` migrations, `.dockerignore` preserving `viper-agent/`, `Dockerfile.dev` VIPER compatibility, and a rightmost-untrusted-IP `net/netip.Prefix` function (`clientIP(r.Header, peerAddr, trustedPrefixes)`) with table unit tests.
  - **SHIP-HATS Go Specifics (`§10.2`–`§10.3`):**
    - Retain all verified Oct 2026 SHIP-HATS platform rules (`sgts.gitlab-dedicated.com`, `ship-hats-templates` `v1.1.12` post-Rekor 30 Sep 2026, immutable stage/job names, WOG PEP `CF_LEVEL` 1–4, CStack/Kaniko 2h runners, Nexus IQ 7-day component age gate since 3 Jun 2026, 1 Nov 2026 EOL image block, Trivy `>= 0.69.3`, 16 Oct 2026 PAT/SSH rule).
    - **Go Module Proxy & 7-Day Age Gate:** Configure `GOPROXY=https://@@SHIPHATS_NEXUS_GO_URL@@,off`, `GOPRIVATE=@@SHIPHATS_GOPRIVATE@@`, `GONOSUMDB=@@SHIPHATS_GOPRIVATE@@` (or commit `vendor/` via `go mod vendor` + `-mod=vendor` documented by addendum if a tenancy lacks a Nexus Go proxy). Because the `go` CLI has no `global-min-publish-age` flag in `go.mod` as of Go `1.27`, provide `scripts/check-module-age.sh` (or `go list -m -json all` checking `.Time` is `>= 7 days` old!) so CI catches <7-day modules locally before Nexus IQ blocks the pipeline!
    - **SonarQube Go properties:** `sonar.go.coverage.reportPaths=coverage.out`, `sonar.go.tests.reportPaths=test-report.json`.
  - **Bash 3.2 (`§10.4`) & 21-Item Checklist (`§11`):** Carry `${a[@]+"${a[@]}"}` + ShellCheck + 21-item Go checklist.

---

### Group G — `§12` through `§19`: Decision Cards, Strictness, Idioms, Patterns, Concurrency, Performance, Architecture & Anti-Rot (`D-12.1`–`D-19.1`)

- **`D-12.1` (`§12` Ten Decision Cards):** Full pasteable cards `DR-01..DR-10` with compiling Go `1.27` snippets, Pros, Costs, Choose-if, and Recommendations.
- **`D-13.1` (`§13` Go's Strictness Profile):**
  - Map every `tsconfig strictest` flag to Go `1.27` + `.golangci.yml` `version: "2"` + `nilaway`. Highlight Go's real gaps cleanly:
    1. **`strictNullChecks` gap in Go:** Go pointers, interfaces, slices, maps, channels, and funcs all admit `nil`, AND every struct has a zero value! Close via value types where non-optional, `govet nilness` + Uber `nilaway` for inter-procedural nil-deref detection, and `errcheck` (`check-blank: true`, `check-type-assertions: true`).
    2. **`noUncheckedIndexedAccess` gap in Go:** Map lookup `v, ok := m[k]` supports comma-ok, while slice indexing `s[i]` panics on OOB; guard bounds explicitly.
    3. **`exactOptionalPropertyTypes` gap in Go:** `*T` conflates `"field omitted"` and `"field explicitly null"` on `PATCH`! Solve with a tiny generic `PatchField[T]` (`Set bool`, `Null bool`, `Value T`) implementing Go 1.27 `jsonv2.UnmarshalerFrom` (`§14.3`).
    4. **Four Go Linter Traps (`§13.3`):** (a) Enabling `linters.default: all` (enables mutually contradictory/deprecated linters like `exhaustruct` and `ireturn` that break idiomatic Go); (b) `exhaustruct` globally forcing noise on 30-field `http.Server` / `tls.Config` structs; (c) `govet fieldalignment` scrambling domain struct readability for 0.00% latency gain on I/O paths; (d) `nilaway` false positives on test helpers / `sync.Once` unless scoped via `-include-pkgs`.
- **`D-14.1` (`§14` Go API & Idiom Rules):**
  - Value vs pointer boundary table; Go getter convention (`Owner()`, **never** `GetOwner()`, per Effective Go & Google Go Style Guide); cost-honest method names; unexported fields + `IsZero()` + `omitzero`; `PatchField[T]` for `PATCH`; standard interfaces matrix (`Stringer`, `slog.LogValuer`, `TextMarshaler`/`TextUnmarshaler`, `error`); `godoc` + `Example*` tests; 8-item review checklist.
- **`D-15.1` (`§15` Design Patterns Allow-List & 10-Item Deny-List):**
  - **Crucial Go Language Trap Documented in `§15.1`:** In Go, `type Email string` (a defined primitive type) **does NOT enforce Parse-Don't-Validate** because Go's assignability rules permit **untyped string constants** (`const x = "not-an-email"; var e Email = "not-an-email"`) to convert implicitly with zero constructor call! Only a **struct wrapping an unexported field** (`type Email struct { v string }`) is unforgeable outside its package (while still keeping zero heap overhead!).
  - Cover Parse-don't-validate, Distinct ID structs (`RequestID`/`ActorID`), Typestate (`Request[Draft]` -> `Request[Submitted]`, sequences only!), Sealed union interfaces (replacing `kind` + nullable pointer soup), Validated Parameter Struct / Functional Options (and when Functional Options is wrong!), Consumer-defined 1–2 method interfaces, `defer` synchronous guards (never hiding fallible `Close()` errors on writable resources!), Functional Core / Imperative Shell, Go dispatch hierarchy, and the 10-row Declined Patterns table.
- **`D-16.1` (`§16` Concurrency Correctness & Observability):**
  - Go runtime rules (cgroup `GOMAXPROCS`, `GOMEMLIMIT`, `semaphore.Weighted` for CPU-bound `argon2id`, outbound `*http.Client` timeouts, idempotent jittered retries), structured concurrency (`errgroup.WithContext` + `SetLimit` & Go 1.25 `WaitGroup.Go`), `select` cancellation & HTTP client-disconnect mid-write atomicity (`pgx.Tx` + `context.WithoutCancel` rollback), bounded channels & semaphores, `sync.Mutex` rules (never copy, never hold across I/O), ordered `SIGTERM` graceful drain, `log/slog` (`NewMultiHandler`) + `context.Context` OTel span propagation + W3C trace links on background jobs, OpenTelemetry Go `v1.47.0` (all 3 signals stable `1.x`!), RED metrics via `r.Pattern` (Go 1.22+ route template), PII/`Secret` `LogValuer` scrubbing, `/healthz` vs `/readyz`, and 10-item review checklist.
- **`D-17.1` (`§17` Performance & Adversarial Testing):**
  - Profile first (`pprof` on loopback admin mux, Go 1.25 `FlightRecorder`, Go 1.27 `/debug/pprof/goroutineleak`, Go 1.24+ `b.Loop()` + `benchstat`), production build profile (`CGO_ENABLED=0`, `-trimpath`, `-ldflags="-s -w"`, PGO `default.pgo`, noting Go preserves `gopclntab` under `-s -w` so stack traces & `recover` keep working!), Green Tea GC + `GOMEMLIMIT`, Postgres query plan priority (`EXPLAIN (ANALYZE, BUFFERS)`), adversarial tool matrix (`rapid`, `go test -fuzz`, `go test -race`, `testing/synctest` + Go 1.27 `httptest.NewTestServer`, `uber-go/goleak`, `gremlins` mutation testing, `oasdiff`/`apidiff`, `govulncheck`), and PR/Nightly/Release CI cadence.
- **`D-18.1` (`§18` Architecture in Go):**
  - Compiler-enforced acyclic package graph + `internal/` directory wall; when splitting Go packages pays vs micro-package vanity (`domain`/`ports`/`dto` import-cycle traps); Go port mechanics (concrete struct -> closed switch -> 1–2 method consumer interface -> leaf generics, avoiding struct generic infection); concrete `App`/`Deps` state (banning global `var DB` and `context.Value` service locators); `internal/` layout + `arch_test.go` (`go/packages`) & `depguard` fitness function; 10 Go architectural anti-patterns; 8-item review checklist.
- **`D-19.1` (`§19` Keeping This Template Honest):**
  - Bi-annual Feb/Aug Go toolchain & quarterly SHIP-HATS re-verification, `DR-` immutability, atomic default updates, scratch-module compile verification for all Go snippets, `.golangci.yml` v2 diffing on upgrades, OTel `1.x` vs contrib `0.x` tracking, `§15` anti-bloat rule, and closing sibling pointers.

---

## Primary Sources Verified (October 2026)

- Go `1.27` (`go1.27.3`), `1.26`, `1.25` Release Notes & Stdlib Specs (`uuid`, `encoding/json/v2`, `errors.AsType`, `net/http.CrossOriginProtection`, `testing/synctest`, `runtime/pprof` `goroutineleak`, `runtime/trace.FlightRecorder`, `log/slog.NewMultiHandler`): `https://go.dev/doc/devel/release`, `https://go.dev/doc/go1.27`, `https://pkg.go.dev/uuid`, `https://pkg.go.dev/encoding/json/v2`, `https://pkg.go.dev/errors`, `https://go.dev/doc/go1.26`, `https://go.dev/doc/go1.25`
- `sqlc` `v1.31.1`, `jackc/pgx/v5` `v5.11.0`, `pressly/goose/v3` `v3.29.0`, `peterldowns/pgtestdb`: `https://docs.sqlc.dev/en/latest/reference/datatypes.html`, `https://pkg.go.dev/github.com/jackc/pgx/v5`, `https://pkg.go.dev/github.com/pressly/goose/v3`, `https://pkg.go.dev/github.com/peterldowns/pgtestdb`
- `danielgtaylor/huma/v2` `v2.39.1`, `go-chi/chi/v5` `v5.3.2`, `oapi-codegen/v2` `v2.8.0`, `connectrpc.com/connect` `v1.21.1`/`v2.0.2`, `a-h/templ` `v0.3.1070`: `https://pkg.go.dev/github.com/danielgtaylor/huma/v2`, `https://pkg.go.dev/github.com/oapi-codegen/oapi-codegen/v2`, `https://github.com/a-h/templ`
- `alexedwards/scs/v2` `v2.9.0`, `coreos/go-oidc/v3` `v3.21.0`, `riverqueue/river` `v0.49.0`: `https://pkg.go.dev/github.com/alexedwards/scs/v2`, `https://pkg.go.dev/github.com/riverqueue/river`
- OpenTelemetry Go `v1.47.0` (`otel/log` 1.x GA, `otelslog` `v0.21.0`, `otelhttp` `v0.72.0`, `exaring/otelpgx` `v0.12.0`): `https://pkg.go.dev/go.opentelemetry.io/otel`, `https://pkg.go.dev/go.opentelemetry.io/contrib/bridges/otelslog`, `https://pkg.go.dev/github.com/exaring/otelpgx`
- `golangci-lint` `v2.14.0`, `govulncheck` `v1.9.0`, Uber `nilaway`, Google/Uber Go Style Guides, SonarQube Go & Nexus Go Proxy: `https://golangci-lint.run/docs/configuration/file/`, `https://pkg.go.dev/golang.org/x/vuln/cmd/govulncheck`, `https://github.com/uber-go/guide`, `https://go.dev/wiki/CodeReviewComments`, `https://docs.sonarsource.com/sonarqube-server/analyzing-source-code/test-coverage/go-test-coverage`, `https://help.sonatype.com/en/go-repositories.html`
- Post-`e8e96f2` Go & Node Delta Verification (`fergusstrange/embedded-postgres` `v1.34.0`, `@stryker-mutator/core` `10.1.1` + `@stryker-mutator/typescript-checker`, `@electric-sql/pglite` `0.5.11` single-session WASM architecture): `https://pkg.go.dev/github.com/fergusstrange/embedded-postgres`, `https://www.npmjs.com/package/@stryker-mutator/core`, `https://github.com/electric-sql/pglite`

---

## Part III — Independent Assessment of `e8e96f2` (`GREENFIELD-RUST.md` Refinements) for Go and Node

Commit `e8e96f2` (`+635 / -51` lines in `GREENFIELD-RUST.md`) introduces 16 distinct refinements distilled from real porting and verification experience (`§1.1`, `§2.5–§2.8`, `DR-11` / `§5.3`, `§6.1` worker parity, `§8.3–§8.4`, `§11` `#22–25`, `§15.11` `Effects`, `§18` graph check + leaf crate, `§19` uncompiled-revision honesty, and `§20` porting). Below is the independent engineering assessment of how each applies — and where blind copy-paste must be **adapted, challenged, or replaced** — in `GREENFIELD-GO.md` (`3,107` lines, `§0–§19` full skeleton) and `GREENFIELD-NODE.md` (`697` lines, `§0–§12` lean skeleton).

### Structural Prerequisite on `GREENFIELD-NODE.md`
Before applying `e8e96f2` to `GREENFIELD-NODE.md`, note the structural asymmetry: `GREENFIELD-NODE.md` is currently the **lean** `§0–§12` variant (`697` lines, no `DR-01..DR-10` cards and no `§13–§19` code-idiom/pattern/concurrency/adversarial sections), whereas `GREENFIELD-RUST.md` (`3,662` lines) and `GREENFIELD-GO.md` (`3,107` lines) use the **full** `§0–§20` skeleton. Two viable strategies exist for Node:
- **Option N1 (Surgical Backport into Lean Node Skeleton, `~1,050` lines):** Fold the high-leverage invariants into existing `§0–§12` plus a concise new `§13. Porting an existing system to Node.js + TypeScript` without adding 11 decision cards.
- **Option N2 (Full `§0–§20` Parity Upgrade, `~2,700` lines):** Promote `GREENFIELD-NODE.md` to the full `DR-01..DR-11` + `§0–§20` architecture first so all three variants (`NODE`, `RUST`, `GO`) share identical section numbers.

### Directive-by-Directive Independent Assessment (`D-00.9` .. `D-20.1`)

1. **`D-00.9` — Standalone, Sibling-Neutral De-coupling (`Preamble`, `§0.1`, `§0.4`, `§18`, `§19`):**
   - **Go (`Adopt Directly`):** Strip references to `GREENFIELD-NODE.md` / `GREENFIELD-RUST.md` in Preamble and `§19`, remove `"Drizzle / Diesel"` name-dropping in `DR-02` Option B (`bob`), and inline the 5 universal architecture rules at the top of `§18` instead of citing `GREENFIELD.md §5`.
   - **Node (`Adopt — Fixes Existing Defect`):** `GREENFIELD-NODE.md` `§12` (`line 487`) currently says *"The router's §5 fixes the cross-language decisions; this section is only the Node and TypeScript mechanism for them"* without stating what those 5 rules are! Inlining the 5 rules makes `GREENFIELD-NODE.md` genuinely standalone when `GREENFIELD.md` is pruned.

2. **`D-01.2` — Checkbox `## Impact` (`§0.5`), Two-Cut Plans & Measurable `done when` (`§1.1`, `§1.1.1`), Native Doc Checker:**
   - **Go (`Adopt + Scope Guard`):** Implement `check-plan-docs --check` in pure Go stdlib (`cmd/devtask` or `internal/plancheck_test.go`, compiling in `< 200 ms` with zero bootstrap dependency). **Independent pushback:** scope the full two-cut `Verify / do` prose-section gate to **multi-task plans, specs, and porting docs**, keeping 15-line `DR-xx` decision addenda concise (`2–4` verifiable `## Impact` checkboxes).
   - **Node (`Adopt + Native Node 22 TS Execution`):** `GREENFIELD-NODE.md` `§1` currently lacks even an addendum front-matter template. Add the YAML + checkbox `## Impact` template and `§1.1` two-cut rule, running `node scripts/check-plan-docs.ts --check` natively on Node `22.6+` type-stripping (zero bash/python scripts).

3. **`D-05.3` — `DR-11` Schema Evolution: Twin Migrations vs Single Snapshot + Version Gate (`§5.3`):**
   - **Go (`Adopt — Stronger Synergy with `sqlc`, Plus One Postgres Caveat`):** Under `DR-11 = B`, `db/schema.sql` serves three roles simultaneously with zero drift: `//go:embed` boot schema, `pgtestdb` test template, and `sqlc`'s offline compiler input (eliminating Rust `sqlx`'s live-DB `.sqlx/` cache friction!). **Go/Postgres caveat to add:** Postgres lacks `CREATE TYPE IF NOT EXISTS` for `ENUM`/`DOMAIN`s and `IF NOT EXISTS` silently skips column/constraint alterations. Rather than re-running `db/schema.sql` blindly on every boot, store both `version int` and `sha256 text` in `schema_state`: apply on empty DB, **no-op + verify catalog tables** when `(version, sha256)` matches, and **exit non-zero naming the reset command** on any version or hash mismatch!
   - **Node (`Adapt — Avoid Creating a Drizzle Two-Source-of-Truth Trap`):** In `GREENFIELD-NODE.md`, `src/db/schema.ts` (Drizzle) is the schema source. Copying Rust's hand-edited `db/schema.sql` under `DR-11 = B` would re-introduce two sources of truth! In Node, `DR-11 = B` must generate `db/schema.sql` from `schema.ts` (`drizzle-kit export --sql > db/schema.sql`, diff-checked in CI) and stamp `schema_state(version, sha256)` at boot — **never** running interactive `drizzle-kit push` silently against an older DB.

4. **`D-02.5` — Negative Authz Status (`404` Default vs Recorded `401`/`403` Decision, `§2.2`):**
   - **Go & Node (`Adopt Directly in Both`):** Prevents breaking legacy clients or public-existence resources during ports while preserving the non-negotiable invariant (exact expected status **and** unchanged DB row).

5. **`D-02.6` — Assertion Quality (`§2.5` — *What the assertion must look at*):**
   - **Go (`Adopt Directly`):** Re-query Postgres or fetch via a second endpoint; marshal test fixtures from typed wire structs (`jsonv2.Marshal(wire.RequestSummary{...})`) rather than raw JSON strings.
   - **Node (`Adopt with `satisfies` Rule`):** Even higher leverage in TypeScript, where `as RequestSummary` type assertions silence missing/renamed fields! Mandate `const expected = { ... } satisfies RequestSummary` (banning `as` casts on test fixtures).

6. **`D-02.7` — The Bite Check & Scoped Mutation Sweeps (`§2.6`):**
   - **Go (`Adopt + Stdlib Cost Pins`):** Pair manual addendum bite-check logs and scoped `go-gremlins/gremlins` runs (`authn`, `policy.go`, money) with Go's deterministic stdlib **`testing.AllocsPerRun`** and a `pgx.QueryTracer` query-counter for cost/N+1 promises (Trap #3).
   - **Node (`Adopt + Critical Vitest/Stryker Type-Checker Requirement`):** Use `@stryker-mutator/core` (`v10.x`) + `@stryker-mutator/vitest-runner` scoped to authz/billing/domain rules, **and mandate `@stryker-mutator/typescript-checker` (`"checkers": ["typescript"]`)**! Without it, Vitest's esbuild/SWC strip-only pipeline executes type-invalid mutants as valid JS, directly triggering `§2.6` Trap #1 (counting non-compiling mutants as survivors/timeouts).

7. **`D-02.8` — Self-Enforcing Standards Checker & Coverage as a Ratchet (`§2.7`, `§17.5`):**
   - **Go (`Adopt + AST Advantage over Regex`):** Update `§2.4` and `§17.5` from "coverage is a diagnostic" to **coverage as a measured ratchet** (`coverage.out` floor per package). Implement `check-standards` using Go's stdlib `go/ast` + `go/types` for Go code rules (eliminating raw-string vs double-quote regex blindness!) while still requiring `testdata/standards/` violating fixtures and non-empty input assertions for every rule.
   - **Node (`Adopt`):** Enforce Vitest `coverage.thresholds` (`autoUpdate: false`) as a committed ratchet, plus `scripts/check-standards.ts` tested against violating fixtures and router/enum completeness enumeration.

8. **`D-02.9` — Stubs, Flakes, and Measured Timeouts (`§2.8`):**
   - **Go (`Adopt Directly`):** Note `go test -timeout` vs `t.Context()` deadline hierarchy so outer test timeouts never truncate inner wait diagnostics.
   - **Node (`Adopt + Fix Playwright `trace` Conflict!`):** Crucial in Node/Playwright where templates default to `retries: process.env.CI ? 2 : 0`. **Important cross-section catch:** banning retries (`retries: 0`) breaks `§3`'s `trace: "on-first-retry"` (which records nothing when retries are 0!). Both Go and Node (and Rust!) should pair `retries: 0` with **`trace: "retain-on-failure"`**.

9. **`D-03.2` — Embedded Real Postgres Binary for Docker-Free Environments (`§3`):**
   - **Go (`Adopt with `fergusstrange/embedded-postgres` `v1.34.0` Caveats`):** Start one `embeddedpostgres` server per package `TestMain` (`CachePath` from `.env.test`, dynamic port) and clone per-test DBs inside it via `pgtestdb`. Document two Go-specific caveats: (a) use Postgres `>= 18.3.0` on Apple Silicon (`v1.34.0` universal Darwin binaries; older builds needed Rosetta 2); (b) Zonky binaries bundle **vanilla Postgres only** (no `postgis`/`pgvector`).
   - **Node (`Adopt Binary Option + Explicitly Fence Out `@electric-sql/pglite``):** Node teams told "no Docker" instinctively install `@electric-sql/pglite` (`v0.5.x`). **Independent ruling:** PGlite runs Postgres in WASM **single-user mode** (one backend session; even `pglite-socket` multiplexes onto one session with a transaction mutex), making concurrent transactions, `FOR UPDATE SKIP LOCKED` races, deadlocks, and session advisory locks **impossible to test**! Allow the `embedded-postgres` real-binary npm wrapper when Docker is absent; forbid PGlite as a stand-in for server integration tests.

10. **`D-06.4` — Single-Source Server + Browser Worker Rules (`§6.1`):**
    - **Go (`Adopt Directly`):** Generate `frontend/src/lib/generated/rules.ts` from Go via `cmd/server` + diff-check in CI + run a sampled cross-runtime parity test.
    - **Node (`Adapt — Direct Pure Workspace Package, Not Codegen`):** In an all-TypeScript repo, code-generating TS from TS is needless indirection. Put shared asset-path/bound/format rules in a pure zero-I/O `packages/shared-rules` module imported directly by Fastify and the Service Worker, guarded by `dependency-cruiser`.

11. **`D-08.3` — Measure Performance Claims (`§8.3`) & Close Defect Classes (`§8.4`):**
    - **Go & Node (`Adopt Directly in Both`):** Committed load scripts (`k6`/`oha`/`autocannon`) weighted into realistic traffic mixes reporting `p50`/`p95`/`p99`/`max` and cold-cache runs; whole-repo sibling defect sweeps recorded in addenda; checking `docs/decisions/` before deleting "unreferenced" code.

12. **`D-11.2` — Appended Day-One Checklist Items `22–25` (`§11`):**
    - **Go (`Adopt 1-for-1`):** Appends items `22–25` cleanly onto `GREENFIELD-GO.md`'s existing `1–21` checklist.
    - **Node (`Adapt Numbering`):** Appends onto `GREENFIELD-NODE.md`'s `1–17` checklist (`18–21`) under Option N1, or `22–25` under Option N2.

13. **`D-15.2` — Effects as a Returned Value (`§15.11` — Solving the Missing `#[must_use]` in Go & TS!):**
    - **Why blind translation fails:** Neither Go nor TypeScript has `#[must_use]`. In Go, `scan, _, err := store.RecordScan(...)` compiles cleanly; in TypeScript, `const { scan } = await recordScan()` or `const [scan] = await recordScan()` silently drops `effects` even under `strictest`!
    - **Go idiomatic solution (`effects.Outcome[T]` + Post-Commit Boundary):**
      - Return `(effects.Outcome[Scan], error)` where `type Outcome[T any] struct { val T; events []kernel.Event }` keeps both fields **unexported** and only yields `T` via `func (o Outcome[T]) Publish(ctx context.Context, pub Publisher) (T, error)` or `func (o Outcome[T]) Discard(reason string) T`! The Go compiler itself prevents reading `Scan` without handling the effects (backed by a 30-line `go/types` check in `check-standards` for `Outcome[struct{}]`).
      - Clarify the boundary with `DR-08`: durable external side-effects (email, webhooks) belong in the transactional SQL outbox / `river.InsertTx` *inside* `pgx.Tx`; `Outcome[T]` governs **post-commit in-process notifications** (SSE/WebSocket push, cache invalidation, wake-up signals) that must fire *only after* `tx.Commit` succeeds!
    - **Node idiomatic solution (`MustPublish<T>` with ECMAScript `#private` fields):**
      - Wrap `(value, effects)` in `class MustPublish<T> { readonly #value: T; readonly #effects: readonly AppEvent[]; ... }` whose only exits are `await res.publish(bus): Promise<T>` and `res.discard(reason: string): T`. Hard `#` private fields cannot be destructured, spread, or JSON-serialized accidentally!

14. **`D-18.2` — Scripted Dependency Graph Check + Shared-Vocabulary Leaf (`§18`):**
    - **Go (`Adopt`):** Introduce `internal/kernel/` (stdlib-only leaf holding typed `ID`s, `Clock`, `Secret[T]`, closed `Event`/`CacheTag` types — zero SQL, zero HTTP, zero business logic) and test `internal/arch_test.go` (`go/packages`) against an intentional cycle/violation fixture.
    - **Node (`Adopt`):** Add `packages/kernel` (or `src/kernel/`) + a violating-fixture test for `dependency-cruiser` in `GREENFIELD-NODE.md` `§12.3`.

15. **`D-19.2` — Honest Uncompiled Revision Disclosure (`§19`):**
    - **Go (`Adopt Immediately`):** `GREENFIELD-GO.md` was drafted in a container without a `go` binary (`go not installed`); recording that exact verification boundary in `§19` directly practices `§8.1` honesty.
    - **Node (`Adopt`):** Record verification level (`tsc --noEmit` vs prose-only) whenever `GREENFIELD-NODE.md` is revised.

16. **`D-20.1` — `§20` Porting an Existing System (`§20.1–§20.8`):**
    - **Shared core (`§20.1`, `20.2`, `20.4`, `20.6`, `20.7`, `20.8` — `Adopt in Both`):** Live legacy oracle, 3-bucket mechanical test classification, exported golden `{input, output}` + validator message-key fixtures, twin-DB shadow harness with unit-tested normaliser + old-vs-mutated-old failure proof + test-only deterministic build mode, quiet legacy assumptions (single-instance Postgres session advisory lock, `Effects`, divergence log, removing single-writer DB gates, folding boot scripts into subcommands), graph-first, and per-domain cutover with exercised rollback on frozen schema all hold across Go and Node.
    - **Go-specific redesign of `§20.3` (Determinism Hazards) & `§20.5` (Browser Engine):**
      - **`§20.3` Go hazards:** (1) Go runtime **deliberately randomizes `map` iteration per run** (and `encoding/json` sorts map keys alphabetically, differing from JS insertion order!); (2) `nil` slice marshals to **`null`** in `encoding/json` v1 vs **`[]`** in `encoding/json/v2`; (3) `sort.Slice` is unstable (`slices.SortStableFunc` required); (4) `math.Round(-0.5) == -1` vs JS `Math.round(-0.5) === -0` vs Python/banker's `math.RoundToEven(-0.5) == 0`; (5) `len(s)` = UTF-8 bytes vs `utf8.RuneCountInString` = code points vs JS `.length` = UTF-16 code units vs `uniseg` graphemes; (6) 64-bit `int` vs JS 32-bit `| 0` / `Math.imul`.
      - **`§20.5` Go WASM pushback:** Unlike Rust's `~100–250 KB` `wasm32` modules, standard Go `GOOS=js GOARCH=wasm` ships the Go runtime + GC (`~2–5 MB` raw, `~600 KB–1.2 MB` brotli), and TinyGo restricts reflection/`jsonv2`. Default to server evaluation + generated rule catalogues (`§6.1`) or a golden-tested TS engine; reserve `GOOS=js GOARCH=wasm` strictly for heavy offline tools that pass an explicit compressed bundle budget.
    - **Node-specific redesign of `§20.3` (Determinism Hazards) & `§20.5` (Browser Engine):**
      - **`§20.3` Node hazards (porting from Python/Java/Go/.NET/PHP):** (1) JS `number` is IEEE-754 `float64` only — integers `> 2^53 - 1` silently corrupt Postgres `bigint` / Java `long` unless mapped to `bigint` or `decimal.js`; (2) `Array.prototype.sort()` with **no comparator sorts numbers as ASCII strings** (`[10, 2].sort()` → `[10, 2]`); (3) plain `{}` objects iterate array-index keys (`"0"`, `"2"`, `"10"`) in **numeric order** ahead of insertion-ordered keys (use `Map` when exact insertion order matters); (4) `JSON.stringify` drops `undefined` keys, turns `NaN`/`±Infinity` into `null`, and **throws `TypeError` on `BigInt`**; (5) `Math.round(-0.5)` produces `-0`.
      - **`§20.5` Node shared engine (Drop WASM completely!):** Server and browser share TypeScript natively. Replace `wasm32` with a **zero-I/O workspace package (`packages/domain-engine`)** gated by `dependency-cruiser` (forbidding `node:*`, `drizzle-orm`, `process.env`, `Date.now()`) + Vite bundle-size ratchet + `schemaVersion` validation only at persisted storage (`IndexedDB`/`localStorage`) or worker boundaries.

---

## Part IV: Converting `GREENFIELD-<lang>` into Claude Code Skills, Path-Scoped Rules & Hooks (October 2026 Research & Assessment)

### 1. Problem Statement & Quantitative Token Audit

Copying a standalone `GREENFIELD-<LANG>.md` file directly as a repository's root `CLAUDE.md` creates severe context-window pressure and instruction dilution:

| Template File | Lines | Bytes | Approx. Tokens (Every Turn) | Share of 200k Window Before Turn 1 |
| --- | ---: | ---: | ---: | ---: |
| `GREENFIELD-GO.md` | `3,700` | `~181 KB` | `~45,000` | `~22.5%` |
| `GREENFIELD-RUST.md` | `3,662` | `~176 KB` | `~44,000` | `~22.0%` |
| `GREENFIELD-NODE.md` | `1,200` | `~62 KB` | `~15,500` | `~7.8%` |

Anthropic's official Claude Code documentation (`code.claude.com/docs/en/best-practices`, `code.claude.com/docs/en/context-window`, verified July–October 2026) identifies **"The over-specified `CLAUDE.md`"** (`> 200` lines) as a primary failure pattern: when thousands of lines of bootstrap menus, inactive option cards (`DR-01..DR-11`), container templates, and porting guides sit in every prompt, model adherence to critical per-turn rules (real-DB tests, IDOR negative tests, bite checks, soft-delete filters) degrades sharply (*lost-in-the-middle*), and long sessions hit compaction much earlier.

### 2. Why Naive 1-to-1 Conversion (`GREENFIELD-<LANG>.md` → One Giant `SKILL.md`) Also Fails

Researching Claude Code's skill lifecycle and compaction internals (`code.claude.com/docs/en/skills` & `context-window`) surfaces a critical architectural constraint:

1. **Three-tier progressive disclosure:**
   - **Tier 1 — Frontmatter (`name` + `description` + `when_to_use`):** Loaded at session startup (`~60–100` tokens per skill; `description` + `when_to_use` combined is truncated at **`1,536` characters** in Claude Code's skill catalog, and `description` is capped at **`1,024` characters** in the portable Agent Skills standard `agentskills.io`). Rebuilt from disk after compaction (`v2.1.304+`).
   - **Tier 2 — `SKILL.md` Markdown body:** Loaded into conversation history when invoked (`/<skill-name>` or auto-matched by Claude) and **retained across subsequent turns**. Official authoring best practice caps `SKILL.md` at **`< 500` lines (`< 5,000` tokens)**.
   - **Tier 3 — Bundled `references/`, `scripts/`, `assets/`:** **`0` tokens** until Claude explicitly calls `Read` on a reference file or executes `${CLAUDE_SKILL_DIR}/scripts/...` via `Bash` (where **only script stdout/stderr enters context**, never the script source!).
2. **The 5,000-token compaction cliff:**
   - Upon context compaction, Claude Code re-injects invoked skill bodies up to a hard cap of **`5,000` tokens per skill** and **`25,000` tokens total across all invoked skills** (dropping oldest skills first and **truncating oversized `SKILL.md` files from the bottom**).
   - Dumping a `45,000`-token `GREENFIELD-GO.md` into a single `SKILL.md` would still lose **~89% of its instructions** on the first compaction!

### 3. Verified `SKILL.md` Frontmatter & Substitution Reference (October 2026)

- **Portable core (`agentskills.io` + Claude API + Claude Code):**
  - `name`: lowercase `[a-z0-9-]`, max `64` chars, matches folder name, cannot contain reserved words `claude` or `anthropic`.
  - `description`: non-empty, third-person *what + when to trigger* (`<= 1,024` chars for cross-surface portability).
- **Claude Code operational frontmatter:**
  - `when_to_use`: extra trigger phrases/examples (shares the `1,536`-char catalog budget with `description`).
  - `argument-hint` & `arguments`: autocomplete signature and named `$arg` positional bindings (`$ARGUMENTS`, `$0`, `$1`).
  - `disable-model-invocation: true`: removes the skill from Claude's auto-invocation catalog (**`0` startup tokens!**) so only explicit `/skill-name` runs it — ideal for one-time `/greenfield-bootstrap` and episodic `/greenfield-port`.
  - `user-invocable: false`: hides from `/` menu; background knowledge loaded only by Claude.
  - `paths`: glob list restricting auto-activation to sessions touching matching files.
  - `allowed-tools` / `disallowed-tools`: per-turn tool grants or restrictions.
  - `context: fork` + `agent`: runs the skill in an isolated subagent window so heavy audits return a concise summary without polluting main-thread context.
  - `hooks`: skill-scoped lifecycle hooks (`PreToolUse`, `PostToolUse`, `Stop`) supporting `once: true` (honored **only** in skill frontmatter!).
- **Path variables:** `${CLAUDE_SKILL_DIR}` (always points to the skill folder regardless of `cwd` or install scope) and `${CLAUDE_PROJECT_DIR}` (repository root).

### 4. Can Claude Hooks Help? — Project Hooks vs Skill-Scoped `hooks:`

Hooks (`code.claude.com/docs/en/hooks`) are **the highest-leverage upgrade** in converting `GREENFIELD-<lang>`, because they move "never-do-X" rules **out of the LLM's attention budget completely** (`0` idle tokens, deterministic execution even under `bypassPermissions`):

| Hook Scope | Lifespan | Best Fit for `GREENFIELD` Rules | Key Caveats (Verified Oct 2026) |
| --- | --- | --- | --- |
| **Project Hooks (`.claude/settings.json`)** | Every turn from session start | 1. **`SessionStart`** (incl. post-`compact`): detect stack (`go.mod` / `package.json` / `Cargo.toml`), schema mode (`Option A` vs `Option B`), and open `## Impact` checkboxes → inject a 12-line `additionalContext` state summary.<br>2. **`PreToolUse` (`Edit\|Write`)**: block direct edits to generated files (`*.sql.go`, `*_templ.go`, `generated/*`), block `migrations/` creation in `DR-11` Option B or edits to committed migrations in Option A, and block non-placeholder secrets in `*.shiphats`.<br>3. **`PostToolUse` (`Edit\|Write`)**: `< 50 ms` per-file static checks — Bash 3.2 syntax on root `*.sh`, addendum frontmatter/`done when` checks, Go (`encoding/json` v1, `uuid.New()` v4, `fmt.Print`), Node (`as` fixture casts, `PGlite` in server tests, `.filter`/`.reduce` inside JSX), Rust (`.unwrap()`, `dbg!`, `Uuid::new_v4()`), and broken `§` links in `GREENFIELD*.md`.<br>4. **`Stop`**: warn via `additionalContext` when routes/schema changed without tests/addenda, reminding Claude to state the exact §8 validation rung reached. | `PreToolUse` uses `hookSpecificOutput: { hookEventName: "PreToolUse", permissionDecision: "deny", permissionDecisionReason: "..." }` (or exit `2` + stderr); top-level `decision: "block"` is deprecated on `PreToolUse` (still current on `PostToolUse` and `Stop`). Never set `if:` on non-tool events (`Stop`, `SessionStart`) or the hook never fires. |
| **Skill Frontmatter `hooks:` (`SKILL.md`)** | Registered **only once the skill is invoked**, then active for the rest of the session (or subagent lifetime under `context: fork`; `once: true` clears after first exit-`0` run) | 1. **`greenfield-bootstrap` (`PreToolUse`, `once: true`)**: physically block creating `src/` / `internal/` / `crates/` / `cmd/` until `docs/decisions/0001-*.md` (`DR-00` language choice) exists.<br>2. **`greenfield-spec-and-plan` (`PostToolUse`)**: enforce two-cut `Verify / do` checkbox syntax, ban vague lead verbs (*ensure/consider/review/improve/handle*), and enforce `FDS_BUILDER` `D15` (zero diagrams) during spec sessions.<br>3. **`greenfield-port` (`PreToolUse`)**: deny manual `Edit\|Write` on `fixtures/golden/**` so legacy golden fixtures can only be regenerated from the live oracle. | **Inactive until the skill is invoked** (`/hooks` hides uninvoked skill hooks). Therefore, universal safety invariants must live in `.claude/settings.json`, while mode-specific workflow guards belong in `SKILL.md` `hooks:`. |

### 5. Recommended Four-Layer Decomposition (`sidequest/.claude/`)

Splitting `GREENFIELD-<lang>` by **instruction lifecycle** cuts steady-state context consumption by **`~96%`** (`~45,000` tokens → `~1,500` tokens in a seeded project, or `~270` tokens inside `sidequest/` itself) while surviving compaction intact:

1. **Layer 1 — Lean Unpacked `CLAUDE.md` (`<= 130` lines, `~1,200` tokens; template in `skills/greenfield-bootstrap/assets/CLAUDE.lean-template.md`):** Holds only settled project facts (language + `DR-01..DR-11` one-line answers, exact build/test commands, package DAG, and 10 one-line invariants). Re-injected 100% from disk after every compaction.
2. **Layer 2 — Path-Scoped `.claude/rules/*.md` (`0` startup tokens; auto-loaded by `paths:` glob):**
   - `database-and-schema.md` (`db/**`, `migrations/**`, `**/*.sql`, `**/schema.ts`, `**/sqlc.yaml`)
   - `frontend-components-hooks.md` (`**/*.tsx`, `**/hooks/**/*.ts`, `e2e/**`, `playwright.config.*`)
   - `containers-and-shiphats.md` (`Dockerfile*`, `.dockerignore`, `**/*.shiphats`, `.gitlab/**`)
   - `bash32-root-scripts.md` (`*.sh`, `scripts/**/*.sh`)
3. **Layer 3 — Five Progressive-Disclosure Skills (`.claude/skills/*/SKILL.md`, each `< 230` lines + Tier 3 `references/` & `scripts/`):**
   - `greenfield-bootstrap` (`disable-model-invocation: true` → `0` idle tokens): `DR-00` router + Go/Node/Rust `DR-01..DR-11` interview, template pruning, lean `CLAUDE.md` generation, and `require-dr00-before-code.sh` hook.
   - `greenfield-spec-and-plan` (auto + `/greenfield-spec-and-plan`): `NNNN` addenda, two-cut plans (`Verify / do` + leaf `done when`), `FDS_BUILDER` mode, and `check-plan-and-fds.sh` validator/hook.
   - `greenfield-implement` (auto + `/greenfield-implement`): routes Claude to **only** the active language's Tier 3 reference (`go-idioms-and-architecture.md`, `node-idioms-and-architecture.md`, or `rust-idioms-and-architecture.md` — never loading two languages at once).
   - `greenfield-verify` (auto + `/greenfield-verify`): real-DB positive + IDOR negative tests, bite-check workflow, scoped mutation testing (`gremlins` / Stryker `typescript-checker` / `cargo-mutants`), tail-latency measurement, and `audit-repo-gates.sh`.
   - `greenfield-port` (`disable-model-invocation: true` → `0` idle tokens): legacy oracle, 3-bucket test ledger, Go/Node/Rust determinism hazard tables, twin-DB shadow diffing, and `lock-golden-fixtures.sh` hook.
4. **Layer 4 — Deterministic Hooks (`sidequest/.claude/settings.json` + `sidequest/.claude/hooks/*.sh`):** `session-context.sh`, `pre-write-guard.sh`, `post-edit-check.sh`, and `stop-honesty-gate.sh`.


