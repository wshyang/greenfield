---
paths:
  - "db/**"
  - "migrations/**"
  - "**/*.sql"
  - "**/schema.ts"
  - "**/sqlc.yaml"
---

# Database & Schema Evolution Rules

Apply these invariants whenever touching SQL, ORM schemas, or migrations:

- **Soft deletion only — never hard `DELETE` domain rows.** Every removable table carries nullable `expires_at` / `deleted_at TIMESTAMPTZ`, a partial unique index (`WHERE expires_at IS NULL`), `invalidate` (not `delete`) repository methods, and active-row filtering on **every** read and authorization query.
- **Liveness-aware foreign keys.** Plain Postgres FKs allow pointing at soft-deleted rows; attach a `BEFORE INSERT OR UPDATE` trigger rejecting references whose target row has `expires_at IS NOT NULL` (`SQLSTATE '23503'`).
- **Timestamp-ordered UUIDv7 IDs minted in one place** (`uuid.NewV7()` in Go `1.27`, `Uuid::now_v7()` in Rust, `uuidv7` in Node), wrapped in typed/branded entity IDs (`RequestID`, `ActorID`).
- **System/background actors are real seeded rows**, never `'system'` or `'unknown'` sentinel strings, so every `actor_id` is a real FK.
- **One write owner per table.** Cross-module reads go through the owning module's exported query functions or an explicit read model.
- **One translation layer only:**
  - *Go:* `sqlc` + `pgx/v5` (`emit_pointers_for_null_types: true`); zero hand-written CRUD mappers.
  - *Node:* Drizzle `src/db/schema.ts` maps `camelCase` ↔ `snake_case`; zero second mapper layer.
  - *Rust:* `sqlx` compile-checked queries (`query_as!`) or `diesel` — never two ORMs.
- **Respect the active `DR-11` schema mode:**
  - **Option A (persistent DBs exist):** update `db/schema.sql` **and** add a forward-only numbered migration in the same commit; never edit a committed migration; use 4-step expand/contract for renames/drops.
  - **Option B (pre-launch, zero persistent data):** single `db/schema.sql` (exported from `schema.ts` in Drizzle repos) + `schema_state(version, sha256)` advisory-locked boot gate that refuses mismatches naming the reset command. Beware Postgres `CREATE TYPE` (no `IF NOT EXISTS`) and `CREATE TABLE IF NOT EXISTS` (silently skips new columns on old DBs) — always check `schema_state` **before** running DDL, and forbid `migrations/`.
