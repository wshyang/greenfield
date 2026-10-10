# Step 02F — NFR Archetypes Batch B: Conditional (`A11Y`, `OBS`, `I18N`, `PRIV`) & Mandatory `§7.4` Sub-Tables

Load **only** during **Step `2.11`** (`Section 13.5–13.8`).

---

## 1. Conditional NFR Elicitation Rule (`§7.5`)

Present `4` structured `AskUserQuestion` cards in Step `2.11` (`1` each for `A11Y`, `OBS`, `I18N`, and `PRIV`; **STOP & WAIT**). Every card MUST include both context-matched archetype tiers (`(Recommended Default)` labeled where appropriate) **and** an explicit `"Skip <Family> (Not applicable)"` option — **never skip a conditional NFR without explicit user confirmation**. Record every choice via `fds-state.sh set-nfr`.

---

## 2. Accessibility (`A11Y-1..5`) & Observability (`OBS-1..4`)

| Tier | `AskUserQuestion` Label | Baseline Parameters | Sub-Table? | Trade-Off & `because {reason}` |
|---|---|---|---|---|
| `A11Y-1` | Headless API / CLI Only | Stable error codes, `--json` & `NO_COLOR`, deterministic exit codes, zero GUI | No | Fits pure API/CLI tools; inapplicable to browser apps because GUI elements do not exist. |
| `A11Y-2` | Internal Keyboard & Contrast | Logical `Tab` order, `Escape`/`Enter` modals, `>= 4.5:1` contrast, visible focus ring | No | Fast internal ops baseline; omits full screen-reader ARIA live coverage. |
| `A11Y-3` | WCAG 2.1 AA *(Web Default)* | Semantic landmarks, labeled inputs, ARIA live errors, `4.5:1`/`3:1` contrast, `200%` zoom, zero traps | No | Standard commercial web accessibility; requires modal focus-return & toast live-region specs. |
| `A11Y-4` | WCAG 2.2 AA Civic Mandate | `A11Y-3` + `24x24px` pointer targets, focus-not-obscured, paste-friendly auth, `prefers-reduced-motion` | No | Meets public-sector inclusion rules; constrains ultra-dense compact icon toolbars. |
| `A11Y-5` | WCAG 2.2 AAA High-Inclusion | `7:1` contrast, forced-colors parity, `<= Grade 8` error copy, voice/switch nav, session-timeout warning | No | Maximizes low-vision/motor/cognitive inclusion; restricts low-contrast palettes and jargon. |
| `OBS-1` | Basic Health Probe & Crash Logs | `GET /healthz`, structured JSON error logs, process crash alert | No | Zero telemetry infra; blind to latency regressions before full outage. |
| `OBS-2` | RED Metrics & Readiness *(Default)* | `/healthz` + DB `/readyz`, per-route Rate/Errors/Duration (`p50/p95/p99`), queue depth, threshold alerts | **YES (`§7.4`)** | Catches latency/5xx spikes early; requires an owned component-alert matrix. |
| `OBS-3` | OTel Tracing + SLO Burn Alerts | `OBS-2` + W3C `traceparent` spans across HTTP/DB/jobs/integrations, `99.9%` SLO burn-rate alerts | **YES (`§7.4`)** | Pinpoints cross-service bottlenecks in 1 trace; adds async span-propagation rules. |
| `OBS-4` | Business KPIs + Synthetic Canaries | `OBS-3` + domain funnel counters, `5m` synthetic end-to-end probes, runbook link per alert | **YES (`§7.4`)** | Detects silent business-flow breakage when HTTP `200` holds; requires canary data hygiene. |

---

## 3. Internationalization (`I18N-1..4`) & Privacy (`PRIV-1..4`)

| Tier | `AskUserQuestion` Label | Baseline Parameters | Sub-Table? | Trade-Off & `because {reason}` |
|---|---|---|---|---|
| `I18N-1` | Single-Locale UTF-8 + UTC *(Default)* | Unicode NFC UTF-8, `UTC` ISO-8601 storage, single UI locale (`en-SG`/`en-US`), IANA display TZ | No | Avoids translation overhead now while keeping DB UTC/UTF-8 clean; requires copy extraction if localized later. |
| `I18N-2` | Externalized ICU Copy + Multi-TZ/CCY | Keyed ICU message catalog (zero string concat), per-user IANA TZ, ISO-4217 minor-unit currency integers | No | Makes future locales drop-in; requires message keys on every `D3` validation message. |
| `I18N-3` | Multi-Lingual LTR Pack + Fallback | `I18N-2` + `2+` launch LTR locales, negotiation (`user > header > tenant`), `35%` text-expansion budget | No | Serves multilingual regions natively; multiplies error/empty-state copy QA across locales. |
| `I18N-4` | Full BiDi (`LTR + RTL`) + Schemas | `I18N-3` + CSS logical properties, mirrored RTL nav, locale collation, flexible name/address schemas | No | Unlocks Arabic/Hebrew and global legal formats; forbids physical `left/right` layout rules. |
| `PRIV-1` | Zero-PII Operational Data | Stores zero names, emails, phones, or national IDs; opaque actor IDs only | No | Eliminates PII breach/DSAR scope; unusable when displaying human profiles or emailing users. |
| `PRIV-2` | Standard Contact PII *(Default)* | Contact PII (`name`, `email`, `ip`), log/URL redaction, encryption at rest, `30d` deletion/anonymization | **YES (`§7.4`)** | Covers standard login profiles; requires cataloging every PII field + log redaction rule. |
| `PRIV-3` | PDPA / GDPR Regulated Lifecycle | `PRIV-2` + purpose/consent record, DSAR export (`<= 30d`) & ledger-safe anonymization, scheduled purge job | **YES (`§7.4`)** | Satisfies statutory PDPA/GDPR audits; requires `R3` anonymization design on historical records. |
| `PRIV-4` | Special-Category + Residency | `PRIV-3` + app-layer per-tenant column encryption, residency pinning, crypto-shredding, audited UI unmask | **YES (`§7.4`)** | Protects national ID / health / financial secrets; precludes raw `LIKE` queries without blind indexes. |

---

## 4. Mandatory `§7.4` Sub-Tables (Author Immediately When `OBS-2+` or `PRIV-2+` Is Selected)

### 4.1 `OBS-2..4` Observability Component Matrix (`{#nfr-observability-components}` under `13.6`)
```markdown
#### Observability Component Matrix {#nfr-observability-components}
| Component / Flow Anchor | Golden Signals & Metrics | Trace Span & Correlation | Structured Log Events | Target SLO / Threshold | Alert Severity & Operator Action |
|---|---|---|---|---|---|
| `#flow-example` / HTTP API | `http_requests_total`, `http_request_duration_ms` (`p50/p95/p99`) | Span `POST /items` (`trace_id`, `tenant_id`) | `item.created`, `item.validation_failed` | `p95 <= 200 ms`, `5xx < 0.5%` (`5m`) | `P1` page if `5xx >= 1%` for `5m`; check DB/upstream readiness |
```

### 4.2 `PRIV-2..4` PII Inventory (`{#nfr-pii-inventory}` under `13.8`)
```markdown
#### PII Inventory {#nfr-pii-inventory}
| Attribute Anchor (`#obj-*.field`) | PII Classification | Purpose / Lawful Basis | Encryption & Storage | UI Masking & Log Redaction | Retention & Purge Trigger | DSAR Export / Erasure Rule |
|---|---|---|---|---|---|---|
| `#obj-user.email` | Direct Contact PII | Auth & transactional alerts | Lowercased UTF-8; encrypted at rest | Full to owner/admin; `[REDACTED_EMAIL]` in logs | Active + `30d` post-deactivation | Exported in JSON; rewritten to `deleted-<uuid>@redacted.invalid` on erasure |
```
