# Porting to Rust `1.99` — Determinism Hazards, `wasm32` Engine & Shadow Harness

## 1. Key Rust Determinism Hazards to Audit First

| Hazard | Typical Legacy Behaviour | Rust `1.99` Rule |
| --- | --- | --- |
| **`HashMap` iteration order** | Insertion-ordered (`JS`/`Python`) | `std::collections::HashMap` randomises `SipHash` seeds per process! Use `BTreeMap` or `indexmap::IndexMap` whenever key order reaches JSON/UI |
| **Rounding & floats** | JS `Math.round(-0.5)` = `-0`; Python half-to-even `0` | `f64::round(-0.5)` = **`-1.0`** (`round_ties_even` = **`0.0`**). Use `rust_decimal` (`MidpointNearestEven` vs `MidpointAwayFromZero`) for money/quotas and test negative `.5` ties against golden fixtures |
| **Integer overflow** | Python unbounded `int`; JS float64 / 32-bit bitwise | Rust panics in debug and **wraps silently in `--release`** unless `checked_*` / `saturating_*` or workspace overflow checks are configured! |
| **Sort stability & `f64` `PartialOrd`** | Total comparator / stable | Use `.sort_by(...)` (stable) rather than `.sort_unstable_by(...)`, with `f64::total_cmp` and deterministic tie-breaker keys |
| **String indexing & length** | UTF-16 units (JS) or code points (Python) | `s.len()` = **UTF-8 bytes**; `s.chars().count()` = code points; `unicode_segmentation::UnicodeSegmentation::graphemes(s, true)` = graphemes |
| **`Option` wire serialisation** | `undefined` omitted vs `null` present | Explicit `#[serde(skip_serializing_if = "Option::is_none")]` vs `null` per legacy endpoint contract, verified by shadow diffing |

## 2. Sharing Domain Rules via `wasm32-unknown-unknown` (`~100–250 KB`)

When the legacy client runs an offline calculation/validation engine:
- Keep the engine crate **100% pure** (`crates/domain-engine`, zero `tokio`/`sqlx`/`axum`, injected time/entropy).
- Expose a **versioned JSON-in / JSON-out boundary** (`schema_version` checked on load, `std::panic::catch_unwind` converted into structured error results rather than killing the browser WASM instance).
- Lazy-load the `.wasm` asset only on routes that use it, and ratchet compressed `.wasm` size in CI.
