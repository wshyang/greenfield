# Rust `1.99` (2024 Edition) Implementation & Architecture Reference

## 1. Crate Boundaries & Type-Driven Domain Core

- **Cargo workspace DAG (`crates/`):**
  - `crates/kernel`: zero-I/O leaf holding typed `Uuid` v7 newtypes (`RequestId`, `ActorId`), `Clock` trait, `SecretString` wrappers, and closed `Event` / `CacheTag` enums — zero `sqlx`, `axum`, or domain business logic.
  - Domain crates (`crates/actors`, `crates/requests`, …): keep internals module-private (`pub(crate)`); expose narrow domain functions and types; pure policy functions take values and return `Result<(DomainValue, Effects), DomainError>` with zero async DB handles.
  - Binary composition root (`bins/server`): wires `AppState`, `axum::Router`, `tower` middleware, healthchecks, and graceful shutdown.
  - Verify the Cargo dependency graph in a test over `cargo metadata --no-deps` (proven against a violating fixture).

## 2. Idioms That Prevent Whole Bug Classes

- **Parse, don't validate:** `nutype` / tuple-struct newtypes with private inner fields (`struct Email(String);` + `TryFrom<&str>`); invalid states unrepresentable via exhaustive enums (avoid catch-all `_ =>` arms on internal enums so adding a variant triggers compiler errors at every match site!).
- **Wire & DB discipline:** `sqlx::query_as!` compile-checked SQL (`.sqlx/` offline cache diffed in CI); `#[serde(deny_unknown_fields, rename_all = "camelCase")]` on inbound DTOs; `Option<Option<T>>` with `#[serde(default, deserialize_with = ...)]` for 3-state `PATCH`; `utoipa` OpenAPI generation diffed against committed TypeScript client types + `gen-shared-rules` for Service Worker constants.
- **`#[must_use]` post-commit `Effects`:**
  ```rust
  #[must_use = "post-commit effects must be published via publisher.publish(effects).await or explicitly dropped via effects.ignore(reason)"]
  pub struct Effects(Vec<kernel::Event>);
  ```
  Pair with `#![deny(unused_must_use)]` at workspace level; use a transactional Postgres outbox (`DR-08`) inside `sqlx::Transaction` when delivery must survive crashes.
- **Strictness & Concurrency:** deny `clippy::unwrap_used`, `clippy::expect_used` (outside tests), `clippy::dbg_macro`, `clippy::todo`; never hold a `std::sync::MutexGuard` across `.await`; bound channels (`tokio::sync::mpsc::channel(cap)`) and spawn tasks through `JoinSet` / `CancellationToken` rather than detached `tokio::spawn` fire-and-forget.
