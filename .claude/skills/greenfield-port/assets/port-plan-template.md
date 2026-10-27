# Porting Review & Two-Cut Plan: `<Legacy System>` → `<Go 1.27 | Rust 1.99>`

> Generated from mechanical scan (`scan-node-for-port.sh`) + live legacy inspection. Every checkbox in Cut 2 carries a unique ID, one imperative verb, a concrete path/command/count, and a measurable leaf `done when`.

---

## 1. Port Boundary & Executable Oracle (`§20.1`)

**Cut 1 — Shape:**
- **Moving to `<Go 1.27>`:** `<HTTP API, background jobs, DB queries, ops CLI subcommands>`
- **Staying unchanged:** `<Browser SPA / Service Worker / mobile client>` — wire JSON shapes and existing `401`/`403` vs `404` status codes remain identical until a post-cutover addendum changes them.
- **Shared client/server rules (`<N>` files from scan §3):** `<Tier 1: ./cmd/server gen-shared-rules -> frontend/src/lib/generated/rules.ts | Tier 2: pure TS + shared golden corpus>`.

### Verify / do
- [ ] PORT-1.1 Boot the legacy Node service against an isolated seed DB as the executable oracle — `curl -sf http://127.0.0.1:<legacy-port>/healthz` — done when the legacy oracle responds `200` reproducibly from one command
- [ ] PORT-1.2 Wire `TARGET_BACKEND=legacy|go` into Playwright / black-box HTTP config (`<path>`) — `TARGET_BACKEND=legacy npx playwright test` — done when `<Bucket-1-count>` black-box suites run unchanged via env switch

---

## 2. Mechanical 3-Bucket Test Ledger & Golden Fixtures (`§20.1–§20.2`)

**Cut 1 — Shape:**
All `<Total-Tests>` legacy test files (`scan-node-for-port.sh` §2) are accounted for: `<B1>` Bucket 1 black-box suites repoint via `TARGET_BACKEND`; `<B2>` Bucket 2 HTTP+DB suites keep HTTP assertions and move setup to SQL fixtures; `<B3>` Bucket 3 white-box suites become exported `{input, expectedOutput}` golden fixtures (`fixtures/golden/`) + real-DB Go integration tests.

### Verify / do
- [ ] PORT-2.1 Commit the `<Total-Tests>`-row test classification ledger in `docs/plans/test-port-ledger.md` — `wc -l docs/plans/test-port-ledger.md` — done when all `<Total-Tests>` legacy test files have an owner bucket and target Go package
- [ ] PORT-2.2 Export golden JSON fixtures + count manifest from legacy pure modules (`<list from scan §3>`) into `fixtures/golden/` — `node scripts/export-golden-fixtures.ts --verify-manifest` — done when manifest counts match and `fixtures/golden/` is read-only under `lock-golden-fixtures.sh`

---

## 3. Determinism Hazards & Quiet Legacy Assumptions (`§20.3`, `§20.6`)

**Cut 1 — Shape:**
Address all scanned JS→Go hazard sites (`HZ-01`…`HZ-08` from scan §4: `<clock-count>` clock sites, `<rng-count>` RNG sites, `<sort-count>` bare `.sort()` sites, `<round-count>` rounding sites, `<patch-count>` tri-state `undefined`/`null` sites) and `<single-instance-count>` implicit `replicas = 1` sites before porting domain handlers.

### Verify / do
- [ ] PORT-3.1 Create the divergence register at `docs/decisions/divergence-log.md` classifying every discovered legacy quirk (`kept-for-parity` | `changed-by-NNNN` | `to-decide`) — `test -f docs/decisions/divergence-log.md` — done when zero known status/wire quirks lack a status entry
- [ ] PORT-3.2 Implement golden-tested Go helpers for rounding, UTF-8/UTF-16 length parity, `slices.SortStableFunc`, `PatchField[T]`, and `json/v2` empty-slice `[]` marshalling in `internal/platform/` — `go test ./internal/platform/...` — done when 100% of exported golden edge cases pass
- [ ] PORT-3.3 Fence or migrate all `<single-instance-count>` in-memory `Map`/`Set`/`setInterval` sites (move to Postgres or acquire a startup Postgres session advisory lock) — `go test ./internal/... -run TestSingleInstanceLock` — done when a second instance either shares state via Postgres or refuses to boot deterministically

---

## 4. Target Go Package Graph & Vertical Slice Port (`§18`, `§20.7`)

**Cut 1 — Shape:**
Establish `internal/kernel` (stdlib-only IDs, `Clock`, `Secret[T]`, `Event`) ← `internal/platform/*` (`effects.Outcome[T]`, `problem`, `httpx`, `testdb`) ← foundational domains (`actors`, `authn`) ← feature domains ← `cmd/server/main.go` (`serve | migrate | healthcheck | dump-openapi | gen-shared-rules`).

### Verify / do
- [ ] PORT-4.1 Encode the `internal/` package DAG in `internal/arch_test.go` with a synthetic forbidden-import fixture — `go test ./internal -run TestArchitectureBoundaries` — done when the violating fixture fails and production packages pass
- [ ] PORT-4.2 Tighten `db/schema.sql` (`NOT NULL`, `CHECK`, liveness FK triggers) verified against a sanitised live-data dump — `psql "$TEST_DATABASE_URL" -v ON_ERROR_STOP=1 -f db/schema.sql` — done when live-shaped seed data loads with zero constraint violations

---

## 5. Twin-DB Shadow Harness, Cutover & Retirement (`§20.4`, `§20.8`)

**Cut 1 — Shape:**
Replay scenarios against Legacy Node and Go `1.27` backed by identically-seeded twin Postgres databases, comparing status, headers, JSON bodies, SSE/WS frames, and persisted rows through one unit-tested normaliser.

### Verify / do
- [ ] PORT-5.1 Prove the twin-DB shadow harness catches planted mutations before trusting `0` diffs — `go test ./cmd/shadow-diff/...` — done when legacy-vs-legacy reports `0` diffs and legacy-vs-mutated-legacy fails on flipped status, mutated field, reordered slice, and dropped SSE frame
- [ ] PORT-5.2 Run mixed-workload shadow + tail-latency benchmark (`bench/`) on the same host and dataset — `just bench-compare` — done when `0` unexplained divergences remain and `p50`/`p95`/`p99`/`max` + cold-start meet parity
- [ ] PORT-5.3 Rehearse staging rollback to the legacy Node container on frozen schema, then delete legacy code + shadow harness in one post-window commit — `git grep -c "TARGET_BACKEND" || true` — done when staging rollback succeeds pre-cutover and parity shims are removed cleanly post-window
