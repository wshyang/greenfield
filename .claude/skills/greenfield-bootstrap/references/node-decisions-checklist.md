# Node.js `22 LTS` + TypeScript `5` Decisions & 18-Item Kickoff Checklist

Confirm and record each architectural fork in `docs/decisions/NNNN-*.md`:

1. **Package manager & workspace layout:** `pnpm` or `npm` workspaces (`packages/kernel`, `packages/shared-rules`, domain packages or `src/<domain>/` + `dependency-cruiser`).
2. **HTTP framework:** **Fastify `5.12+`** (encapsulated plugins + `app.inject()` socket-free real-DB testing + CIDR `trustProxy`) or Next.js App Router.
3. **ORM & single-casing rule:** **Drizzle ORM** (`src/db/schema.ts` maps `camelCase` ↔ `snake_case`, zero hand-written mappers).
4. **Schema evolution mode (`§5`):**
   - **Option B (pre-launch default):** `src/db/schema.ts` → CI-diffed `drizzle-kit export --sql` (`db/schema.sql`) + `schema_state(version, sha256)` advisory-locked boot gate that refuses mismatches naming `npm run db:reset` (never silent `drizzle-kit push`; `migrations/` forbidden).
   - **Option A (once any DB holds persistent data):** Twin `db/schema.sql` + numbered forward-only `migrations/` in the same commit.
5. **Wire contract & shared worker rules:** Shared Zod/TypeBox or OpenAPI types + zero-I/O `packages/shared-rules` imported directly by Fastify and Service Workers.
6. **Test Postgres runner:** Docker / CI service container, or `embedded-postgres` real binary when Docker is absent — **never WASM `@electric-sql/pglite` for server integration tests**.
7. **Post-commit effects vs durable outbox:** `MustPublish<T>` (`#private` fields) for in-process SSE/cache notifications; Drizzle transactional `outbox_events` table for crash-durable external side-effects.

## Node 18-Item Day-One Checklist

(1) `docs/spec.md` + `docs/decisions/` with checkbox `## Impact`; (2) real-DB Vitest integration harness + recorded negative-authz code (`404` vs `401`/`403`) checking unchanged rows; (3) Drizzle single-casing policy; (4) soft-delete + liveness FK trigger + UUIDv7 + real system actor rows; (5) Schema Option B `schema_state` gate or Option A twin migrations; (6) `data-testid` + typed wire contracts + `packages/shared-rules`; (7) test layout + Playwright video on, `retries: 0`, `trace: "retain-on-failure"`; (8) realistic fixture pools + injected `Clock`; (9) honest validation caveat + `bench/` tail-latency scripts; (10) one-command local dev + `.env`/`.env.test`; (11) `<= 50`-line functions, `<= 3` params, guard clauses, component-renders / hook-decides, presentation-only JSX, `<= 800` LOC files; (12) `0.0.0.0:3000` `node:22-alpine` `Dockerfile*` + CIDR proxy trust; (13) inert `*.shiphats` + `activate-shiphats.sh` (Bash 3.2); (14) `satisfies` test fixtures, bite checks, scoped Stryker with `@stryker-mutator/typescript-checker`, `check-standards.ts` fixture proof, Vitest coverage ratchet; (15) `MustPublish<T>` `#private` wrapper; (16) `packages/kernel` pure leaf + 4-rule `dependency-cruiser.config.cjs` tested on a violating fixture; (17) two-cut `node scripts/check-plan-docs.ts --check`; (18) *(ports only)* live legacy oracle, 3-bucket test ledger, golden fixtures, JS determinism audit, twin-DB shadow harness.
