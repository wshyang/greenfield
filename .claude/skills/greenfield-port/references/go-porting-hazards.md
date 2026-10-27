# Porting to Go `1.27` — Determinism Hazards, Browser Rules & Shadow Harness

## 1. Nine Go Determinism Hazards to Audit First

| Hazard | Typical Legacy Behaviour | Go `1.27` Rule |
| --- | --- | --- |
| **Map iteration order** | Insertion-ordered (`JS`/`Python`) | Go **randomises `map` iteration per run**; `encoding/json` sorts `map[string]V` alphabetically. Use slices of structs or explicit key sorting whenever order is observable |
| **Empty vs `nil` slice** | Always `[]` | `encoding/json` v1 marshals `nil` slice as **`null`**! Use `encoding/json/v2` (`nil` → `[]` by default) or `make([]T, 0)` consistently |
| **Sort stability** | Stable (`timsort` / ES2019+) | `slices.SortFunc` / `sort.Slice` are **unstable** (`pdqsort`)! Use **`slices.SortStableFunc`** with a total tie-breaker |
| **`.5` tie rounding** | JS `Math.round(-0.5)` = `-0`; Python `round(-0.5)` = `0` | `math.Round(-0.5)` = **`-1`**; `math.RoundToEven(-0.5)` = **`0`**. Centralise one golden-tested rounding helper |
| **Money & floats** | IEEE-754 `float64` everywhere | Use `int64` minor units or `shopspring/decimal`; JSON rejects `NaN`/`±Inf` |
| **Integer width** | JS bitwise `\| 0` wraps **32-bit**; Python arbitrary-precision | Go `int` is **64-bit** and overflows silently; use explicit `int32`/`uint32` for legacy hash math |
| **String length** | JS UTF-16 units; Python code points | `len(s)` = **UTF-8 bytes**; `utf8.RuneCountInString` = code points; `rivo/uniseg` = graphemes. Test CJK + emoji |
| **Omitted vs `null` vs zero** | `undefined` vs `null` vs `""`/`0` | Use `PatchField[T]` at wire edges so Go zero values never masquerade as omitted |
| **Ambient clock / RNG** | Inline `Date.now()` / `random()` | Count legacy sites; inject `Clock` and seeded `math/rand/v2` (`//go:build deterministic` gated out of release builds) |

## 2. Sharing Rules with the Browser (Why Go WASM Comes Third)

Standard `GOOS=js GOARCH=wasm` embeds the Go scheduler + GC (**`~2–5 MB` raw / `~600 KB–1.2 MB` brotli**), and TinyGo restricts reflection/`json/v2`:
1. **Default:** server evaluation + `./cmd/server gen-shared-rules` → `frontend/src/lib/generated/rules.ts` (CI diff-checked).
2. **Existing offline TS engine:** keep pure TS validated against the shared golden fixture corpus.
3. **`GOOS=js GOARCH=wasm` (last resort for heavy offline tools):** pure Go package, versioned `schemaVersion` JSON facade with `defer recover()`, lazy-loaded per route, and CI brotli size ratchet.
