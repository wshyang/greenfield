# Real-DB Testing, Bite Checks, Standards Ratchets & Tail Benchmarks

## 1. Real Postgres in Docker-Present vs Docker-Free Environments

- **Default:** `docker compose up -d db` locally + Postgres service container in CI (never spin a new `testcontainers` container per test file).
- **Docker-free real-binary fallback (record in addendum):**
  - *Go:* `github.com/fergusstrange/embedded-postgres` (`v1.34.0+`, `Config.CachePath` from `.env.test`, dynamic port in `TestMain`) + `peterldowns/pgtestdb` template-DB cloning (`< 20 ms`/test). Use Postgres **`>= 18.3.0`** on Apple Silicon macOS (native arm64 binaries without Rosetta 2); note Zonky archives ship vanilla Postgres without `postgis`/`pgvector`.
  - *Node:* `embedded-postgres` real-binary wrapper (cached archive, per-worker port/data dir). **Forbid `@electric-sql/pglite` for server integration tests** — WASM single-user mode runs one session behind a mutex, hiding pool contention, deadlocks, session advisory locks, and `FOR UPDATE SKIP LOCKED` races.
  - *Rust:* `sqlx::test` against `postgresql_embedded` cached binary per `nextest` run when Docker is absent.

## 2. Scoped Mutation Testing & Deterministic Cost Pins

Scope mutation runs strictly to incident-grade packages (authz, money/billing, state machines) on nightly CI:
- **Go:** `go-gremlins/gremlins` (`gremlins unleash ./internal/<domain>`). Pin hot-path allocations/queries via `testing.AllocsPerRun` and a `pgx.QueryTracer` SQL counter — never wall-clock `time.Since` assertions.
- **Node/TS:** `@stryker-mutator/core` (`v10.x`) + `@stryker-mutator/vitest-runner` + **mandatory `@stryker-mutator/typescript-checker` (`checkers: ["typescript"]`)** so Vitest's type-stripping never executes non-compiling mutants as JS! Pin N+1 promises with a Drizzle query-logger counter.
- **Rust:** `cargo-mutants` (`cargo mutants --package <crate>`).

## 3. Self-Enforcing `check-standards` & Coverage Ratchet

- Every `check-standards` rule (`STD-001`, …) ships with a **violating fixture** (covering single quotes, double quotes, and raw/template literals) proven to fail in tests, **plus** a non-empty file-count assertion so renamed directories never pass vacuously.
- Walk the live router registry (`chi.Walk` / Fastify `onRoute` / `axum` route inventory) so adding an endpoint without an IDOR negative test fails CI.
- Commit measured repeatable coverage floors (`coverage.out` / `vitest.config.ts` `coverage.thresholds` / `cargo-llvm-cov`) as a **ratchet**: raise when earned; require a numbered addendum to lower.

## 4. Tail-Latency Measurement (`§8`)

Any numeric latency/throughput claim requires a committed script (`k6`, `oha`, or `autocannon` in `bench/`) driving a realistic mixed workload, reporting **`p50`, `p95`, `p99`, `max`, and cold-cache first-request latency**, measured on the same machine and dataset when comparing against a baseline.
