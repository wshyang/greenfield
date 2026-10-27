# Go `1.27.3` Decision Register (`DR-01`…`DR-11`) & Kickoff Checklist

Ask unresolved cards in 2–3 compact batches; write `docs/decisions/NNNN-*.md` for each.

| ID | Decision | Options (*Default in bold*) |
| --- | --- | --- |
| `DR-01` | HTTP router & handler style | **A: `net/http` (`1.22+` mux) or `chi/v5` + `huma/v2`** · B: OpenAPI-first `oapi-codegen/v2` · C: ConnectRPC (`connectrpc.com/connect`) |
| `DR-02` | Database access | **A: `sqlc` (`v1.31+`) + `jackc/pgx/v5`** · B: `pgx/v5` + typed query builder (`sq`/`jet`) — never GORM |
| `DR-03` | Wire contract & JSON | **A: Code-first `huma/v2` → OpenAPI 3.1 → `@hey-api/openapi-ts` (`encoding/json/v2`)** · B: Schema-first `openapi.yaml` · C: Protobuf / `buf` |
| `DR-04` | Strictness & static gates | **A: `.golangci.yml` v2 strict + `uber-go/nilaway` + `govulncheck` + `arch_test.go`** · B: Standard linter set without `nilaway` |
| `DR-05` | Frontend architecture | **A: React + Vite SPA (`frontend/`)** · B: `a-h/templ` + HTMX SSR · C: Headless API only |
| `DR-06` | Authentication & sessions | **A: Postgres-backed `alexedwards/scs/v2` cookie + `coreos/go-oidc/v3` + Go `1.25+` `http.CrossOriginProtection`** · B: Stateless JWT bearer (API-only) |
| `DR-07` | Configuration | **A: Typed env struct (`caarlos0/env/v11`) validated at startup + `.env.example`/`.env.test`** · B: Flag + env CLI (`kong`) |
| `DR-08` | Background jobs & durable effects | **A: Transactional Postgres queue (`riverqueue/river` `InsertTx`)** · B: Custom SQL `outbox_events` polling worker · C: None yet (in-process `effects.Outcome[T]` only) |
| `DR-09` | Observability | **A: `log/slog` JSON (`slog.NewMultiHandler`) + OpenTelemetry (`otelhttp`, `otelslog`, OTLP)** · B: `log/slog` + Prometheus `/metrics` |
| `DR-10` | Runtime container image | **A: `gcr.io/distroless/static-debian12:nonroot@sha256:...` (`CGO_ENABLED=0`, `/app/server healthcheck` subcommand)** · B: Pinned `debian:12-slim` (only if CGo required) |
| `DR-11` | Schema evolution mode | **B (pre-launch default): Single embedded `db/schema.sql` + `schema_state(version, sha256)` advisory-locked boot gate** · A (once any DB holds persistent data): Twin `db/schema.sql` + `pressly/goose/v3` migrations |

## Go 25-Item Day-One Checklist

Verify before first feature PR: (1) `docs/spec.md` + `docs/decisions/`; (2) `pgtestdb` real-DB test harness (or `fergusstrange/embedded-postgres` `v1.34+` `PG >= 18.3` when Docker absent); (3) `DR-01..DR-11` settled; (4) `sqlc` single-mapper config; (5) soft-delete + liveness FK triggers + `uuid.NewV7()` + seeded system actors; (6) `DR-11` Option A parity or Option B `schema_state` gate + boot-twice/refuse-older tests; (7) OpenAPI + TS codegen diff + `gen-shared-rules`; (8) RFC 9457 Problem Details + `PatchField[T]`; (9) `data-testid` + Playwright `retries: 0` + `trace: "retain-on-failure"`; (10) realistic fixture pools + `synctest` clock; (11) `justfile` / `dev.sh` + `.env.example`/`.env.test`; (12) `.golangci.yml` v2 + `nilaway` + `goleak` + `goroutineleak`; (13) `0.0.0.0:3000` distroless `Dockerfile*` + CIDR proxy trust; (14) inert `*.shiphats` + Nexus 7-day age check; (15) Bash 3.2 root scripts; (16) route IDOR completeness test; (17) security matrix; (18) `Secret[T]` redaction; (19) `check-standards` proven on violating fixtures + `coverage.out` ratchet; (20) `effects.Outcome[T]` post-commit wrapper; (21) `internal/kernel` stdlib-only leaf + `internal/arch_test.go` failing-fixture proof; (22) two-cut `check-plan-docs` gate; (23) mixed-load tail-latency benchmark harness (`bench/`); (24) bug-class sweep rule; (25) *(ports only)* legacy oracle, 3-bucket test ledger, golden fixtures, and twin-DB shadow harness.
