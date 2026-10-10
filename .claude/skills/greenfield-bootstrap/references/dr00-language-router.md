# `DR-00` · Backend Language Router

Present this card once as its own message only when the user has not already named the backend language.

```text
DR-00 · Backend language — the first decision

A. Node.js 22 LTS + TypeScript — one language across the stack
   Shape: Fastify 5 + Drizzle ORM + Vitest + Playwright
   Pros:  fastest clone-to-first-endpoint; shares pure TS packages directly with
          React/Service Workers (zero WASM/codegen); deepest SSO/PDF/Excel SDK support.
   Costs: types erase at runtime unless validated at every edge; ~60–150 MB RSS
          and V8 GC tail pauses; module walls require workspace exports + depcruise.
   Choose if: CRUD/API orchestration dominates, deadline is tight, or team is JS/TS.

B. Go 1.27 — fast compilation, single static binary, native concurrency
   Shape: chi/huma + sqlc + pgx/v5 + Go 1.27 stdlib (uuid v7, json/v2, synctest)
   Pros:  <2 s incremental builds; ~15–40 MB RSS in distroless/static; compiler-enforced
          package privacy (internal/) + sqlc compile-checked SQL; effortless goroutines.
   Costs: verbose error/validation ceremony; nil-slice/zero-value wire subtleties;
          browser code sharing uses generated rule catalogues rather than shared TS.
   Choose if: you want a tiny static container, predictable tail latency, high I/O
          fan-out, and fast onboarding without borrow-checker ramp-up.

C. Rust 1.99 (2024 edition) — affine type system as the design tool
   Shape: axum 0.8 + sqlx 0.9 + cargo-nextest + distroless
   Pros:  compile-checked SQL + exhaustive enums + #[must_use] Effects; ~10–30 MB RSS,
          zero GC, flattest p99; ~100–250 KB wasm32-unknown-unknown browser engines.
   Costs: slowest CRUD iteration and compile times; steepest hiring/review bottleneck.
   Choose if: hard numeric p99/memory constraints, correctness-critical domain engine,
          compact browser WASM requirement, and reviewers who write Rust today.

Recommendation: A for rapid full-stack CRUD; B when static-binary ops, concurrency,
or Go team familiarity apply; C only when >= 4 rubric signals (including Q1 or Q2)
point to Rust. Reply A / B / C, or "you choose".
```

## Six-Question Scoring Rubric (When Undecided)

1. Hard numeric `p99` / memory / zero-GC / static-binary SLO? (`No` → Node · `Static binary + low RSS` → Go · `Zero-GC hard p99` → Rust)
2. Who reviews PRs in 18 months? (Match the language reviewers read fluently today.)
3. Workload shape? (`CRUD + SDKs` → Node · `High-fanout I/O, workers, proxies` → Go · `CPU/crypto/parsers/WASM` → Rust)
4. Mandatory JS-only vendor/SSO SDKs? (`Yes` → Node)
5. Shared complex offline browser domain engine? (`Yes, already TS` → Node · `Yes, binary WASM <250 KB` → Rust · `Catalogue/server-eval` → Go)
6. Delivery horizon vs ramp-up budget? (`Weeks` → Node/Go · `Months + Rust reviewers` → Rust)
