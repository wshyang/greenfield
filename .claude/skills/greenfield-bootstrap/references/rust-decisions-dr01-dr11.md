# Rust `1.99` (2024 Edition) Decision Register (`DR-01`…`DR-11`) & Kickoff Checklist

Ask unresolved cards in 2–3 compact batches; write `docs/decisions/NNNN-*.md` for each.

| ID | Decision | Options (*Default in bold*) |
| --- | --- | --- |
| `DR-01` | HTTP framework | **A: `axum 0.8` + `tower` + `tower-http`** · B: `actix-web 4` |
| `DR-02` | Database access | **A: `sqlx 0.9` compile-checked SQL (`query_as!` + `.sqlx/` offline cache)** · B: `diesel 2` (`diesel-async`) — never mix two |
| `DR-03` | Wire contract | **A: `utoipa 5` → OpenAPI 3.1 → generated TS client (CI diff-checked)** · B: Schema-first OpenAPI · C: `tonic` / Protobuf |
| `DR-04` | Strictness & lints | **A: Workspace `[lints.clippy]` pedantic/unwrap_used/dbg_macro deny + `cargo-deny` + `cargo-udeps`** · B: Standard `clippy -D warnings` |
| `DR-05` | Frontend architecture | **A: React + Vite SPA (`frontend/`)** · B: `askama` + HTMX SSR · C: `leptos` CSR/SSR |
| `DR-06` | Authentication & sessions | **A: `tower-sessions` (Postgres store) + `argon2` / `openidconnect` + CSRF** · B: Stateless JWT (API-only) |
| `DR-07` | Configuration | **A: Typed `figment` / `envy` struct validated at startup + `secrecy::SecretString`** · B: `clap` env + CLI |
| `DR-08` | Background jobs & durable effects | **A: Transactional Postgres outbox / `apalis` SQL queue** · B: In-process `tokio` worker + SQL advisory lock · C: None yet (`#[must_use] Effects` only) |
| `DR-09` | Observability | **A: `tracing` JSON + `tracing-opentelemetry` OTLP + `tower_http::trace`** · B: `tracing` JSON + Prometheus `/metrics` |
| `DR-10` | Runtime container image | **A: `gcr.io/distroless/cc-debian12:nonroot@sha256:...` + `cargo-chef` + `server healthcheck` subcommand** · B: Static `musl` scratch/distroless |
| `DR-11` | Schema evolution mode | **B (pre-launch default): `include_str!("../../db/schema.sql")` + `schema_state(version, sha256)` advisory-locked boot gate** · A (once persistent DBs exist): Twin `db/schema.sql` + `sqlx::migrate!` |

## Rust 25-Item Day-One Checklist

Verify before first feature PR: (1) `docs/spec.md` + `docs/decisions/`; (2) `sqlx::test` / real-DB `cargo nextest` harness (`postgresql_embedded` fallback when Docker absent); (3) `DR-01..DR-11` settled; (4) single `serde` + `sqlx` mapping discipline; (5) soft-delete + liveness FK triggers + `Uuid::now_v7()` newtypes + seeded system actors; (6) `DR-11` Option B `schema_state` gate or Option A twin migrations; (7) `utoipa` OpenAPI + shared worker rules codegen diff; (8) RFC 9457 `ApiError` + double-`Option<Option<T>>` PATCH; (9) `data-testid` + Playwright `retries: 0` + `trace: "retain-on-failure"`; (10) realistic fixture pools + injected `Clock`; (11) `justfile` + `.env.example`/`.env.test`; (12) workspace Clippy lints + `cargo-deny` (7-day age gate); (13) `0.0.0.0:3000` `cargo-chef` distroless `Dockerfile*` + CIDR proxy trust; (14) inert `*.shiphats` + `activate-shiphats.sh`; (15) Bash 3.2 root scripts; (16) route IDOR completeness test; (17) security matrix; (18) `SecretString` redaction; (19) `xtask check-standards` proven on violating fixtures + `cargo-llvm-cov` ratchet; (20) `#[must_use] struct Effects` post-commit wrapper; (21) zero-I/O `crates/kernel` leaf + scripted `cargo metadata` DAG test proven on a cycle fixture; (22) two-cut `cargo xtask check-plan-docs`; (23) mixed-load tail-latency benchmark harness; (24) bug-class sweep rule; (25) *(ports only)* legacy oracle, 3-bucket test ledger, golden fixtures, and twin-DB shadow harness.
