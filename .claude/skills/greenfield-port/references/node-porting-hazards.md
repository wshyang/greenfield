# Porting to Node.js `22` + TypeScript — Determinism Hazards & Shared Engine

## 1. Eight JavaScript / V8 Determinism Hazards to Audit First

| Hazard | Legacy Behaviour (Python / Java / SQL / Go) | Node.js `22` + TypeScript Rule |
| --- | --- | --- |
| **64-bit integers (`> 2^53 - 1`)** | Exact `int64` / `BIGINT` / `Decimal` | `number` is float64 (`9007199254740992 === 9007199254740993` is `true`!). Map `bigint`/`numeric` to `bigint` or `decimal.js`, serialised as JSON strings |
| **`Array.prototype.sort()`** | Numeric sort (`[2, 10]`) | **`[10, 2].sort()` returns `[10, 2]`** (UTF-16 string sort)! Always pass an explicit total comparator `(a, b) => a - b` |
| **Object `{}` key order** | Pure insertion order or sorted | Plain `{}` iterates **array-index keys (`"0"`, `"2"`, `"10"`) in ascending numeric order first**, then string keys by insertion! Use `Map` or tuple arrays when order matters |
| **`JSON.stringify` traps** | Explicit errors or `null` | Silently **drops `undefined` object keys**, turns `NaN`/`±Infinity` into **`null`**, and **throws `TypeError` on `BigInt`**! Validate outbound DTOs with `satisfies` + Zod/TypeBox |
| **Rounding `.5` ties** | Half-away (`-1`) or half-to-even (`0`) | **`Math.round(-0.5)` returns `-0`** ($+\infty$)! Use one golden-tested `decimal.js` helper with explicit rounding mode |
| **String `.length` & slicing** | Code points or UTF-8 bytes | `.length` counts **UTF-16 code units** (`"🙂".length === 2`). Use `[...s].length` for code points or `Intl.Segmenter` (`granularity: "grapheme"`) |
| **`Date` parsing** | Explicit naive vs aware | `new Date("2026-10-27")` = UTC midnight, but `new Date("2026-10-27T00:00:00")` (no `Z`) = **host local time**! Require explicit `Z`/offset or UTC epoch ms |
| **Ambient `Date.now()` / `Math.random()`** | Inline calls | Audit every call site; inject `Clock` and non-prod-gated seeded PRNG |

## 2. Browser-Shared Domain Engine (Pure TypeScript, Zero WASM)

Do **not** compile WASM in an all-TypeScript stack: isolate shared domain calculations/validators in a **zero-I/O workspace package (`packages/domain-engine`)** enforced by `dependency-cruiser` (forbidding `node:*`, Fastify, Drizzle, and `process.env`), run the legacy golden fixtures against it in Vitest, ratchet Vite client chunk bytes in CI, and stamp `schemaVersion` on `IndexedDB`/`localStorage` payloads.
