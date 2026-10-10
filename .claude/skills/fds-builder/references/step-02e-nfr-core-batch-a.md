# Step 02E — NFR Archetypes Batch A: Mandatory Core (`SEC`, `PERF`, `LOG`) & Quantitative `SCALE`

Load **only** during **Step `2.10`** (`Section 13.1–13.4`).

---

## 1. Mandatory User-Choice Protocol (`§5.5`, `§7.5`)

1. **Never choose an NFR tier silently.** Present `4` structured `AskUserQuestion` questions in Step `2.10` (`1` each for `SEC`, `PERF`, `LOG`, and `SCALE`; **STOP & WAIT**). Append `(Recommended Default)` to the context-matched tier label while offering adjacent tiers + `allowCustomResponse: true` (note in stem that all `SEC-1..7` / `PERF-1..5` / `LOG-1..5` / `SCALE-1..5` IDs are selectable via Custom).
2. **`SEC`, `PERF`, and `LOG` are ALWAYS active** (cannot be skipped). **`SCALE` is conditional** — include an explicit `"Skip Scalability NFR (Not applicable)"` option in Question 4 so the user decides (`§7.5`).
3. Tag any preset parameter not yet individually customized as `[DRAFT — archetype default]` (`fds-state.sh set-nfr --family <FAM> --status draft-default --archetype <ID>`).

---

## 2. Security (`SEC-1..7`) & Performance (`PERF-1..5`) — *Always Active*

| Tier | `AskUserQuestion` Label | Baseline Parameters | Trade-Off & `because {reason}` |
|---|---|---|---|
| `SEC-1` | Public Zero-Auth Utility | TLS 1.3+, IP rate limit (`60 req/min`), strict input validation, CSP headers, zero accounts | Zero login friction; unsuitable for user-owned data because anonymous callers cannot be isolated. |
| `SEC-2` | Single-Tenant / Consumer Auth | OIDC/Argon2id, `HttpOnly+Secure+SameSite=Lax` session, CSRF guard, lockout (`5` fails/`15m`) | Simple per-user auth; lacks org role boundaries because permissions are flat per account. |
| `SEC-3` | Multi-Tenant RBAC + MFA *(SaaS Default)* | Tenant-scoped row isolation, predefined RBAC, admin MFA, `15m` token / `8h` idle session | Prevents cross-tenant IDOR and admin takeover; adds membership join + MFA because SaaS shares infra. |
| `SEC-4` | Enterprise ABAC/ReBAC + SSO/SCIM | SAML/OIDC SSO, SCIM offboarding (`<= 5m`), resource-level `R2` grants, `90d` API key rotation | Unlocks enterprise IT offboarding; increases `R2` graph complexity because grants vary per resource. |
| `SEC-5` | Regulated FinTech / Health | Column envelope encryption, maker-checker dual approval, `15m` idle TTL, tamper-evident audit | Meets segregation-of-duties audits; slows admin mutations because high-risk writes require 2 actors. |
| `SEC-6` | Gov / Zero-Trust High-Assurance | Service `mTLS`, phishing-resistant WebAuthn MFA, egress allowlist, `0s` per-request authz check | Stops token replay & lateral movement; adds cert ops + per-call authz cost because network trust is zero. |
| `SEC-7` | Classified / Air-Gapped Custody | HSM keys, dual-custody break-glass lease, import/export sanitizer, zero external egress | Protects disconnected sovereign workloads; forbids SaaS webhooks because external egress is blocked. |
| `PERF-1` | Async / Batch Back-Office | Read `p95 <= 1500 ms`, Write `p95 <= 2500 ms`, Batch `<= 10 min`, Export `<= 60 s` | Zero cache complexity; unsuitable for rapid interactive work because multi-second waits stall staff. |
| `PERF-2` | Internal Line-of-Business *(Internal Default)* | Read `p50 <= 120 / p95 <= 400 / p99 <= 1000 ms`, Write `p95 <= 600 ms`, TTI `<= 2.0 s` | Met by indexed SQL alone; avoids cache-invalidation bugs because staff concurrency is bounded. |
| `PERF-3` | Customer-Facing Web/API *(External Default)* | Read `p50 <= 60 / p95 <= 200 / p99 <= 500 ms`, Write `p95 <= 350 ms`, LCP `<= 1.8 s`, page `<= 100` | Snappy external UX; requires strict query budgets and bounded pagination because latency drives churn. |
| `PERF-4` | Realtime Collaborative | Read `p50 <= 25 / p95 <= 80 / p99 <= 200 ms`, fan-out `p95 <= 150 ms` | Supports live multi-user presence; requires hot projections because cold SQL joins exceed `80 ms`. |
| `PERF-5` | Sub-25ms Edge Decisioning | Read `p50 <= 8 / p95 <= 25 / p99 <= 50 ms`, zero sync upstream I/O on hot path | Fits inline gateways; forces precomputed state because synchronous remote calls blow `25 ms`. |

---

## 3. Audit/Logging (`LOG-1..5`, *Always Active*) & Scalability (`SCALE-1..5`, *Conditional + 5 Numeric Metrics*)

> **`§7.3` Hard Rule:** Never write `"must scale"`. Every active `SCALE-*` block MUST state all **5 numeric metrics**: `(1)` Current→Projected RPS/TPS, `(2)` Horizon, `(3)` Burst Multiplier, `(4)` Concurrent Users, `(5)` Resource/Cost Scaling Ratio.

| Tier | `AskUserQuestion` Label | Baseline Parameters (`[DRAFT — archetype default]` until confirmed) | Trade-Off & `because {reason}` |
|---|---|---|---|
| `LOG-1` | Operational Access & Error Logs | Structured JSON stdout, `request_id`, status/latency, `30d` retention, zero secret logging | Minimal storage; cannot reconstruct domain edits because before/after values are not stored. |
| `LOG-2` | Domain Mutation Audit *(Internal Default)* | `LOG-1` + `#obj-audit-event` on every write/transition (`actor_id`, `action`, `target`, `90d` hot/`1y` cold) | Answers who changed X and when; adds 1 atomic audit insert per write. |
| `LOG-3` | Tenant-Visible Admin Trail *(SaaS Default)* | `LOG-2` + PII-masked field diff, auth/role events, tenant query `#surf-*` (`1y` hot/`3y` cold) | Enables customer compliance self-service; requires query surface + redaction rules. |
| `LOG-4` | Regulated Immutable WORM Trail | Append-only hash-chained store (`UPDATE`/`DELETE` revoked), sensitive-read logging, `7y` retention | Passes statutory financial/clinical audits; forbids rewriting historical rows. |
| `LOG-5` | Forensic Non-Repudiation Ledger | `LOG-4` + external batch signature anchor, dual-authorized watermarked export, `7–10y` retention | Tamper-evident even against root DB admins; adds cryptographic key-ops overhead. |
| `SCALE-1` | Departmental / Single-Team | `5 -> 25` RPS (`12m`), `3x` burst (`75` RPS), `50` conc. users, single-node vertical, `<= 1.2x` cost ratio | Zero distributed-state overhead; bounded ceiling because single-node trades elasticity for simplicity. |
| `SCALE-2` | Mid-Market Org *(B2B Default)* | `25 -> 150` RPS (`18m`), `5x` burst (`750` RPS), `500` conc. users, `2..6` stateless replicas, `<= 1.1x` ratio | Absorbs workday spikes on primary+replica DB; forbids in-memory process locks across replicas. |
| `SCALE-3` | Multi-Tenant Production SaaS | `150 -> 1,000` RPS (`24m`), `5x` burst (`5,000` RPS), `5,000` conc. users, pooling + async queues, `<= 1.0x` ratio | Isolates noisy-neighbor bursts; adds queue backpressure & idempotency rules. |
| `SCALE-4` | High-Traffic Civic / Consumer | `1,000 -> 10,000` RPS (`24m`), `10x` burst (`100k` RPS), `50,000` conc. users, CDN + partitioned tables, `<= 0.85x` | Survives national surges; requires Day-1 table partition keys to avoid hot-index locks. |
| `SCALE-5` | Hyper-Scale / Flash-Event | `10k -> 100k` RPS (`36m`), `20x` burst, `500k` conc. users, multi-region cells + load shedding, `<= 0.75x` | Preserves availability under flash crowds; trades global serializability for cell isolation. |

---

## 4. Section 13 Per-Category Block Schema (`§7.1`)

```markdown
### 13.X <Category Name> {#nfr-<slug>}
- **Selected Archetype:** `<TIER-ID>` — <Name> (`[DC-NNN]`)
| Parameter | Target Value | Provenance | Rationale (`because ...`) |
|---|---|---|---|
| <Metric> | `<Value>` | Confirmed (`DC-NNN`) or [DRAFT — archetype default] | <Concrete trade-off `because ...`> |
- **Testable Requirements:** numbered deterministic rules.
- **BDD Acceptance Checks:** **Given** ... **When** ... **Then** ...
- **Stress & Degradation Behavior:** exact behavior under overload, timeout, or clock skew.
```
