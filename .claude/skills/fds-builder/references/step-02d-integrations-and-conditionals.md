# Step 02D — Retention, Conditional `R6`/`R7` Rules, External Integrations & Data Migration

Load **only** during **Step `2.09`** (`Sections 7 & 12`). Execute **only** the sub-domains included in Step `1.3` (verify explicit `D9` `because DC-NNN` skip notices for excluded ones; never ask `> 4` questions in a single `AskUserQuestion` call — split into sequential calls if `> 4` questions are needed across active sub-domains).

---

## 1. Domain 10 — Data Retention, Archival & Purge Policy (`Section 7` / `Section 13`)

Confirm via `AskUserQuestion` (**STOP & WAIT**) whenever domain records carry operational, financial, or statutory lifespans:
- Active hot-storage retention window per `#obj-*` class.
- Archive vs automated purge trigger (`status == archived` + age threshold).
- Interaction with `R3` deletion integrity (e.g., anonymizing `#obj-user` PII while retaining `#obj-invoice` ledger rows for `7` years).

---

## 2. `R6` — Path, Route & Identifier Collision Specification (`§6.9`, Section 7)

Required whenever `r6-collision` is `included` (dynamic slugs, vanity paths, shortcodes, or `/me` vs `/{id}` share a namespace):
1. **Specificity-Ordered Route/Key Table (`#cstr-route-specificity`):** Order every shared pattern deterministically (`1. Exact Literal` > `2. Prefix-Typed Segment` > `3. Dynamic Slug/Wildcard`).
2. **Shadowing Analysis:** Explicitly identify colliding patterns (e.g., `/{org_slug}` vs `/settings`, `/projects/{slug}` vs `/projects/new`).
3. **Closed Reserved Literal List:** Enumerate exact forbidden slug tokens (`admin`, `api`, `assets`, `auth`, `billing`, `docs`, `healthz`, `help`, `internal`, `login`, `logout`, `me`, `metrics`, `new`, `null`, `readyz`, `root`, `settings`, `static`, `status`, `support`, `system`, `undefined`, `webhooks`) and cross-link this list into the `Validation Rule` + `Error Message` of the slug attribute in `Section 5` (`D3`).

---

## 3. `R7` — Session Continuity Specification (`§6.7`, Section 7)

Required whenever `r7-session` is `included` (ban vague prose like *"user stays logged in"*). Elicit policy choices via `AskUserQuestion` (**STOP & WAIT**) and specify all **7 items** under `#cstr-session-continuity`:
1. **Storage Medium & Cookie/Token Contract:** Exact cookie/key name, `HttpOnly`, `Secure`, `SameSite` (`Lax`/`Strict`), path/domain scope, and CSRF protection rule.
2. **Absolute TTL & Idle Timeout:** Exact durations (e.g., `12h` absolute, `30m` idle) and sliding-window renewal threshold.
3. **Browser Reload While Valid:** Exact preserved state (route, query filters, unsaved form draft behavior).
4. **Reload / Mutation After Expiry:** Return-to URL preservation, unsaved input handling, and verbatim session-expired banner message.
5. **Mid-Session Account Deactivation / Role Revocation:** Exact cutoff behavior cross-linked to `R8` (`Section 5`).
6. **Client Rehydration Order:** Deterministic boot order (`1. Session probe` → `2. Tenant/role context` → `3. Route data`).
7. **Pre-Rehydration UI State:** Neutral skeleton/gate guaranteeing **zero flash of unauthorized UI or stale tenant data**.

---

## 4. Domain 8 — External Integrations (`§9.3`, Section 12.1 `#int-*`)

Required whenever `integrations` is `included`. Confirm failure/fallback behavior via `AskUserQuestion` (**STOP & WAIT**) and document for every `### 12.X <Provider/Capability> {#int-<slug>}`:
- **Purpose & Direction:** Outbound sync API, outbound async job, or inbound signed webhook.
- **Auth, Secret Storage & Rotation:** Auth scheme (OAuth2 client credentials, HMAC webhook secret, mTLS), env/vault injection (zero hardcoded keys), and dual-key rotation window.
- **Contract & Language-Agnostic Pseudo-Schema (`D16`):** Request/event fields in Markdown tables or ```` ```pseudocode ```` (never `json`/`ts`/`python` code blocks if locked to implementation libraries; keep schemas vendor/language-neutral).
- **6-Row Failure Matrix:** `Timeout` | `4xx Auth/Validation` | `429 Rate Limit` | `5xx Outage` | `Malformed Payload` | `Duplicate Event / Idempotency Key`.
- **Retry / Circuit-Breaker / Fallback Strategy** + **Field Mapping Table** (`External Field -> #obj-*.attribute`).

---

## 5. Domain 11 — Legacy Data Migration (`§6.8`, Section 12.2 `#int-data-migration`)

Required whenever `data-migration` is `included`. Confirm quarantine & cutover strategy via `AskUserQuestion` (**STOP & WAIT**) and specify all **7 parts**:
1. `Source System & Schema Inventory` • 2. `Field-by-Field Mapping Table` (`Source -> #obj-*.attr`) • 3. `Normalization & Cleaning Rules` • 4. `Dirty-Record Quarantine Policy` (never silently drop rows) • 5. `Dependency-Ordered Load Sequence` (honoring `R3`) • 6. `Row-Count & Checksum Reconciliation Gates` • 7. `Rollback & Cutover Window Strategy`.
