# CLAUDE.md — <Project Name>

## 1. Stack & Settled Decisions (`docs/decisions/`)

- **Backend (`0001` / `DR-00`):** `<Go 1.27.3 | Node.js 22 LTS + TypeScript 5 | Rust 1.99>`
- **HTTP & Wire (`DR-01`, `DR-03`):** `<e.g. chi v5 + huma v2 OpenAPI -> generated TS client>`
- **Database (`DR-02`, `DR-11`):** PostgreSQL `<18>` via `<sqlc + pgx/v5 | Drizzle ORM | sqlx 0.9>` · Schema evolution mode: `<Option B: single db/schema.sql + schema_state gate | Option A: db/schema.sql + forward-only migrations/>`
- **Jobs & Effects (`DR-08`):** `<River / SQL outbox>` for durable external side-effects; `<effects.Outcome[T] | MustPublish<T> | #[must_use] Effects>` for post-commit SSE/cache notifications
- **Auth (`DR-06`):** `<Server-side Postgres sessions + OIDC + CSRF>`
- **Frontend (`DR-05`):** `<React + Vite + TypeScript>`

## 2. Canonical Commands

```bash
<bootstrap-cmd>        # Stand up local dev + separate test Postgres from zero
<typecheck-lint-cmd>   # Full compiler + linter + dependency-graph + check-standards
<test-integration-cmd> # Real-DB integration tests (zero repo mocks, retries = 0)
<test-e2e-cmd>         # Playwright E2E (video on, retries: 0, trace: retain-on-failure)
<codegen-diff-cmd>     # Regenerate wire/SQL/shared-rules & assert git diff --exit-code
```

## 3. Module Dependency DAG

`<kernel>` (zero-I/O shared IDs, `Clock`, `Event`) ← `<platform>` (domain-agnostic infra) ← `<foundational domains: actors, authn>` ← `<feature domains>` ← `<composition root: cmd/server | src/app.ts | bins/server>`. Enforced in CI by `<internal/arch_test.go | dependency-cruiser | cargo-deny>`.

## 4. Ten Non-Negotiable Invariants

1. **Decisions in the same change:** Every choice not dictated by `docs/spec.md` gets a numbered `docs/decisions/NNNN-*.md` addendum (YAML frontmatter + `- [ ] ID ... — done when ...` checkboxes) in the same commit. Multi-task plans use two cuts (`/greenfield-spec-and-plan`).
2. **Real-DB tests, zero repo mocks:** Drive the real router/entrypoint against an isolated real Postgres test DB (never WASM `PGlite` for server suites).
3. **Positive + IDOR negative test per route:** Every endpoint asserts happy-path persisted DB state **and** wrong-party session rejection (`<404 | 401/403>`) with **unchanged DB rows**.
4. **Watch every new test fail (the bite check):** Sabotage the guarded clause, watch the test go red, revert cleanly, and record watched sabotages in consequential addenda (`/greenfield-verify`).
5. **Soft deletion + UUIDv7 + real actor rows:** Nullable `expires_at`, partial unique indexes (`WHERE expires_at IS NULL`), liveness FK triggers, active-row filters on every read/authz query, single-site UUIDv7 minting, and seeded rows for system actors.
6. **Single translation layer:** One DB mapping layer (`sqlc` / Drizzle / `sqlx`), typed wire contracts (`satisfies` in TS tests, `json/v2` in Go), and one source for shared server/worker rules.
7. **Function & UI discipline:** Functions `<= 50` lines (`<= 20` target), `<= 3` params, guard clauses (`<= 3` nesting), zero flag booleans; React components render (presentation-only JSX, `data-testid` at authoring time) and hooks decide.
8. **Zero flaky-test masking:** `retries: 0` across unit, integration, and Playwright suites; timeouts derived from single-iteration measurements.
9. **Container & SHIP-HATS contract:** Listen on `0.0.0.0:3000`, numeric `USER`, CIDR proxy trust, inert `*.shiphats` (`@@SHIPHATS_<NAME>@@`, Nexus 7-day age gate), and Bash 3.2-compatible root `.sh` scripts.
10. **Honest validation reporting:** State the exact verification rung executed (`static syntax` / `typecheck+lint` / `unit` / `real-DB integration` / `Playwright E2E`); never say *"tests pass"* unless the test runner ran against a real DB.

## 5. Using `.claude/` Skills, Path Rules & Verification Scripts

Keep **one** root instruction file (`CLAUDE.md`; if other agents require `AGENTS.md`, make `CLAUDE.md` a single `@AGENTS.md` import or symlink — never maintain two diverging copies).

| When doing this task… | In Claude Code | In other `AGENTS.md` harnesses (no Skill/Hook loader) |
| --- | --- | --- |
| Writing an addendum (`docs/decisions/`), 2-cut plan (`docs/plans/`), or FDS (`docs/spec.md`) | Invoke `greenfield-spec-and-plan` | Read `.claude/skills/greenfield-spec-and-plan/SKILL.md`, then run `.claude/skills/greenfield-spec-and-plan/scripts/check-plan-and-fds.sh <file>` |
| Adding/changing routes, domain logic, queries, workers, or post-commit effects | Invoke `greenfield-implement` | Read `.claude/skills/greenfield-implement/SKILL.md` + `.claude/skills/greenfield-implement/references/<go\|node\|rust>-idioms-and-architecture.md` |
| Touching SQL/migrations, `.tsx`/Playwright, `Dockerfile*`/`*.shiphats`, or `.sh` scripts | Auto-loaded from `.claude/rules/*.md` | Read the matching file in `.claude/rules/` before editing |
| Writing tests, running bite checks, benchmarking, or finishing a task | Invoke `greenfield-verify` | Read `.claude/skills/greenfield-verify/SKILL.md` and run `.claude/skills/greenfield-verify/scripts/audit-repo-gates.sh` |
| Porting a legacy system *(if applicable)* | User runs `/greenfield-port [go\|node\|rust]` | Run `.claude/skills/greenfield-port/scripts/scan-node-for-port.sh`, then read `.claude/skills/greenfield-port/SKILL.md` + `<lang>-porting-hazards.md` |

