# GREENFIELD.md — pick your language, then take the matching template

This repository is a **set of standing-instruction templates** for starting a new
project so that the expensive lessons are paid for once, up front, instead of
being rediscovered mid-project. This file is the **router**. It does not contain
the rules; it asks one question, records the answer, and hands you the file that
does.

```text
GREENFIELD.md            ← you are here: the language question and the shared contract
├── GREENFIELD-NODE.md   ← Node.js + TypeScript variant (standalone)
├── GREENFIELD-RUST.md   ← Rust variant (standalone)
├── FDS_BUILDER.md       ← companion: builds the functional/design spec (any language)
└── initial-templates/   ← container starters to contextualise, not to copy blind
```

**The router's only job is to stop the agent from picking a language for you.**
Every rule in the variants assumes a language; a rule written for the wrong one
is worse than no rule, because it is confidently wrong. So the first action on a
greenfield repo is not scaffolding — it is the question in §1.

---

## 0. How to use this repository

1. **Ask §1 before writing any code.** The answer is `DR-00`, the first entry in
   the project's decision register, and it is recorded as addendum `0001` before
   the first commit that contains `src/`.
2. **Copy exactly one variant** to the new repository as `CLAUDE.md`. The
   variants are standalone: each restates the whole contract in its own
   language, so a future reader never needs this router. Do not concatenate two
   variants, and do not "merge the good bits" — a merged file is a third,
   unmaintained variant.
3. **Split it as it grows** (each variant's §0 explains the split), keeping the
   decision/addenda and test sections in the first file an agent reads.
4. **Pair it with `FDS_BUILDER.md`.** The design-spec prompt and the engineering
   template answer different questions — what the system must do, and how the
   code must be built. Both are needed; neither substitutes for the other.
5. **Contextualise `initial-templates/`.** The Dockerfile there auto-detects an
   app type, which is wrong for anything with its own server (§10.1 of either
   variant explains what to replace).
6. **Delete what does not apply, in the same commit that makes it not apply.**
   A stale rule that nobody follows teaches future agents that the file is
   advisory.

---

## 1. The language question (DR-00)

Ask it once, as its own message, using the card shape both variants already
prescribe: a real code excerpt per option in the project's own vocabulary, pros,
costs, a "choose this if" line, and a recommendation. Never bundle it with the
framework or database question — those are downstream of this answer and will be
asked later, inside the chosen variant.

**Do not re-ask an answered question.** If the request already names the
language ("a Rust service that…", "a Next.js app that…"), treat `DR-00` as
answered: confirm it in one line, record it, and go straight to that variant's
register. Asking again is the same failure as never asking, wearing a different
hat — it tells the user nobody is listening.

```text
DR-00 · Backend language — the first decision

Which language and runtime should the server be written in? This decides which
template you get; everything else (framework, ORM, auth, runtime image) is asked
afterwards, inside that template.

A. Node.js 22 + TypeScript — one language across the stack
   Real example (Fastify + Drizzle, the variant's default shape):
       app.get("/api/requests/:id", async (req, reply) => {
         const [row] = await db.select().from(requests)
           .where(and(eq(requests.id, req.params.id), isNull(requests.expiresAt)))
           .limit(1);
         if (!row) return reply.code(404).send(problem(404, "not-found"));
         return row;
       });
   Pros:  fastest path from clone to a running route; the same language as the
          React frontend, so one toolchain and one hiring profile; the deepest
          library ecosystem for the things government apps actually need
          (PDF/Excel, email, SSO sample code, OCR, spreadsheets); a large pool
          of reviewers.
   Costs: no compile-time SQL or wire checking unless you add Drizzle/Kysely and
          generate types; ~60–150 MB RSS per service and GC pauses in the tail;
          CPU-bound work needs worker_threads or a second service; the type
          system stops at the boundary you remembered to type.
   Choose if: the workload is CRUD and API orchestration, the deadline is real,
          or the team already writes TypeScript.

B. Rust 1.99 (2024 edition) — the type system as the design tool
   Real example (axum + sqlx, the variant's default shape):
       async fn get_request(
           State(state): State<AppState>,
           Path(id): Path<Uuid>,
       ) -> Result<Json<RequestSummary>, ApiError> {
           Ok(Json(state.requests.summary(RequestId::from(id)).await?))
       }
   Pros:  a typo in a column name or a renamed wire field fails the build, not a
          page; ~10–30 MB RSS, no GC, flat p99 under load; one static binary in
          a distroless image with no runtime to patch; exhaustive errors and
          `Option` make the "forgot the null case" bug class much harder.
   Costs: slower iteration on CRUD (borrow checker, rebuilds, more ceremony for
          email/PDF/auth); a smaller hiring pool and fewer drop-in libraries;
          compile times that make CI caching a design concern; a rewrite if the
          team later decides it wanted Node.
   Choose if: there is a hard latency/memory constraint, the service is
          long-lived and ops cost dominates, the domain is correctness-critical,
          or the team already writes and reviews Rust.

C. A language with no variant yet (Python, Go, Java/Kotlin, C#…)
   Real answer: there is no template, so the honest options are (1) choose A or B
   for now, or (2) write the variant first (§7) and accept that it is a
   half-day of work with no code output.

Recommendation: A, unless §2's answers point at Rust. Node gets a service to
first-endpoint fastest, and a hot path can be carved out into Rust later; the
reverse migration is a rewrite.
Reply A/B/C, or "you choose" (which means A, recorded as decided_by: agent).
```

### 1.1 Recording the answer

The answer becomes addendum `0001` in the new repository, before scaffolding:

```markdown
---
id: 0001
decision: DR-00
status: accepted
decided_by: user          # or agent, if the user delegated
date: 2026-10-23
supersedes: null
---

# 0001 — Backend language: Rust

## Decision
Rust, per GREENFIELD-RUST.md, copied to CLAUDE.md.
## Why
<the user's reason, in their words>
## Rejected
- Node + TypeScript: <the actual reason>
## Impact
- §13–§17 of the template apply as written; `DR-01`…`DR-10` come next.
```

If the user delegates ("you choose"), say which conditions you checked, record
`decided_by: agent`, and put the same sentence in the PR description. A silent
default is the failure this router exists to prevent.

---

## 2. When the answer is not obvious

Answer all six; none is decisive alone. **Rust has to earn it: four or more
answers — including Q1 or Q2 — must point at Rust, otherwise choose Node.** Rust
is the better answer for a narrow set of problems and a worse answer for a broad
set of teams; pretending otherwise is how a six-week tool becomes a four-month
project.

| # | Question | Points to Node | Points to Rust |
| --- | --- | --- | --- |
| 1 | Is there a hard numeric constraint — p99 latency, RAM per replica, cold start, single static binary, no GC in the tail? | no such constraint | constraint is measured and binding |
| 2 | Who maintains this in 18 months, and do they write Rust **today**? | the team is JS/TS, or unknown | at least one reviewer writes Rust |
| 3 | Is the work CRUD, API orchestration, and third-party calls, or CPU-bound (parsing, crypto, media, simulation, streaming)? | I/O-bound | CPU-bound |
| 4 | Does the domain depend on JS-only libraries (SSO SDK with only JS samples, some PDF/OCR/Excel packages, vendor SDKs)? | yes | no, or a Rust crate exists |
| 5 | Is the UI React? | yes → one language across the stack | UI is Leptos/HTMX, or a thin API is fine |
| 6 | What is the real deadline versus a Rust ramp-up? | weeks | months, and the ramp is planned |

Two rules of thumb that survive contact with reality:

- **Latency is usually Postgres, not the language.** A Rust service making five
  sequential 2 ms queries is slower than a Node service making one 3 ms query.
  Measure the query plan before rewriting a service for speed (Rust variant
  §17.4 says the same thing from inside the language).
- **The cost of Rust is paid by every future change, not just the first one.**
  If the team cannot review it, the type system's benefits are consumed by the
  review bottleneck.

---

## 3. What every variant shares (the invariant core)

These are language-independent. They are the reason the templates exist, and a
new variant must carry all of them, translated into whatever the language makes
idiomatic. The variant states them concretely; this list is the contract.

| Invariant | Why it is language-independent |
| --- | --- |
| **A living spec plus a numbered addenda register**, written in the same change as the decision | Drift is a process failure, not a syntax problem |
| **A decision interview**: ask before coding, record the answer, supersede rather than edit | Prevents an agent from silently choosing on the user's behalf |
| **Tests against a real database**, through the real app entrypoint, never a mocked data layer | A mock cannot fail the way SQL fails |
| **An IDOR negative test per route**, asserting the exact status *and* that no row changed | Authentication is not authorization, in any language |
| **Soft deletion, not `DELETE`**, with active-row filtering on every read and every authorization check | Data retention and accidental resurrection are schema-level |
| **Timestamp-ordered IDs (UUIDv7), minted in one place, wrapped in a type** | Index locality and argument-swap bugs are runtime facts |
| **Real rows for system actors**, never sentinel strings | Every `actor_id` must be a genuine foreign key |
| **Schema snapshot and numbered migration, both updated in the same commit**, with a parity check | Two sources of truth drift silently |
| **Typed wire contract generated from the server**, committed, and diffed in CI | A rename must be a compile error, not a blank page |
| **`data-testid` at authoring time** with a documented convention | The e2e suite is a contract, not a scavenger hunt |
| **Function shape rules** (≤ 50 lines, ≤ 3 parameters, guard clauses, no flag arguments, domain-based modules) | Fowler's refactorings do not care what compiles them |
| **Honest validation**: name the rung you reached; never claim "tests pass" from a typecheck | The failure mode is a green message over a broken build |
| **One-command local dev**, three-file env contract, separate test DB | Reproducibility is not language-specific |
| **Container contract**: listen on `0.0.0.0:3000`, numeric `USER`, healthcheck, pinned digests, proxy trusted by CIDR | The platform's ingress does not read your source language |
| **SHIP-HATS carried inert** as `*.shiphats` with `activate-shiphats.sh`, kept in step | Compliance is a pipeline property, not a framework feature |
| **Root scripts run on Bash 3.2** | The new joiner's macOS does not care what the server is written in |

**Conflict rule.** If this table and a variant disagree, the variant wins for a
project that copied it — it is the file the agent actually reads — and the other
must be corrected in the same commit. A router that quietly contradicts its
variants is worse than no router.

---

## 4. What varies, and what a new variant must decide

Each variant answers the same layers with different tools. This is the map a new
variant has to fill in; it is also why the router must not try to hold the rules
itself.

| Layer | Node + TypeScript | Rust | What a third variant must settle |
| --- | --- | --- | --- |
| HTTP / routing | Fastify or Next.js route handlers | `axum 0.8` + `tower` | framework, extractor model, how tests drive the app without a socket |
| Data access | Drizzle (schema-as-source), one casing, no hand-written mappers | `sqlx 0.9` (compile-checked SQL) or diesel, never two | the ORM/query layer, and whether SQL is checked at compile time |
| Wire contract | shared types / OpenAPI → client | `utoipa` → OpenAPI → TS | how server types become client types, and the CI diff that proves it |
| Migrations | numbered SQL + wholesale snapshot | same twin, `sqlx::migrate!` | the migration runner and the parity check |
| Tests | Vitest + Playwright, real DB | `cargo nextest` + `sqlx::test` + Playwright | test runner, DB isolation mechanism, video evidence |
| Auth | session cookie + CSRF | `tower-sessions` + `argon2` + OIDC | session store, revocation, CSRF story |
| Strictness | `tsconfig` `strictest` + lint | Clippy profile + `clippy.toml` | what "strict" means when the compiler is not already strict |
| Lint / supply chain | ESLint, `npm audit`, lockfile policy | `clippy -D warnings`, `cargo-deny`, 7-day age gate | the equivalent gates, and which ones are CI-only |
| Runtime image | `node:22-alpine`, multi-stage, `USER` | distroless + `cargo-chef` + healthcheck subcommand | base image, build caching, healthcheck without a shell |
| Frontend | React + Vite (default) | React + Vite (default), Leptos/HTMX optional | whether the UI is a separate axis or part of the language choice |

**The frontend is a separate axis.** Both variants default to React + Vite and
treat the API as the boundary; Rust additionally offers Leptos or Askama/HTMX for
a Rust-only stack. Choosing Rust for the backend does **not** commit you to a
Rust frontend, and choosing Node does not commit you to one either. Record the
frontend as its own decision (`DR-05` in the Rust variant), not as a consequence
of `DR-00`.

---

## 5. After the answer

1. Copy the chosen variant to the new repository as `CLAUDE.md`.
2. Write addendum `0001` (§1.1) in the same commit.
3. Work the variant's own decision register — `DR-01`…`DR-10` in Rust, the
   equivalent questions in Node — **before** the code that depends on them.
4. Pair with `FDS_BUILDER.md`; the spec is written in the product's language,
   not the implementation's.
5. Bootstrap: one command to a running stack, a real test DB, and the container
   contract green before the first feature.

Nothing in this router needs to be copied forward. If a project's `CLAUDE.md`
still contains a link back here, the variant was not standalone enough — fix the
variant.

---

## 6. Mixed-language projects

Allowed, and sometimes right — but it must be a decision, not an accident.

| Shape | Good when | Cost |
| --- | --- | --- |
| Node API + a Rust worker for one hot or CPU-bound job | a single measured bottleneck (parsing, image/PDF work, crypto) | a second toolchain, a second image, a job contract to version |
| Rust API + a small Node tool for a JS-only SDK | one library has no usable equivalent | a sidecar or a build-time step, and two dependency policies |
| Rust core crate with a Node/TS frontend | the domain deserves the type system, the UI needs the ecosystem | FFI/WASM boundary, or a clean HTTP split |

Rules: **one language owns the data layer.** Two services writing the same tables
through two ORMs is the two-source-of-truth trap with a network hop. Pick a
single owner per table, and let the other call it. Also count the CI cost honestly
— two toolchains means two caches, two lint policies, and two upgrade calendars,
which is exactly the friction the single-language templates exist to remove.

---

## 7. Adding a new language variant

Only do this if someone will maintain it. A variant that rots is worse than a
variant that does not exist, because it carries the authority of the set.

1. **Copy the nearest skeleton.** `GREENFIELD-RUST.md` is the fuller shape
   (§0–§18, with the decision cards and the code-level sections); the Node
   variant is the leaner one (§0–§11).
2. **Keep the two load-bearing sections intact in intent**: the decision
   interview and the addendum discipline. They are the reason the set exists.
3. **Translate the invariant core of §3**, one row at a time, into the language's
   idiomatic mechanism. If a row has no equivalent, say so and say what replaces
   it — an honest gap beats a borrowed rule.
4. **Resolve every fork with real code.** Each option needs a compiling excerpt
   in the project's vocabulary, its costs, and a "choose this if". A menu of
   adjectives is not a decision aid.
5. **Date it and record versions** at the top ("verified October 2026"), the way
   both existing variants do. An undated template is a rumour.
6. **Name it `GREENFIELD-<LANG>.md`**, add it to the register in §8, and add the
   pointer in the same commit.
7. **Prove standalone-ness**: hand the file alone to someone who has never seen
   this repo and check they can bootstrap a project. If they need the router or
   the other variant, the file is not done.
8. **Do not invent a third language choice in the card** until its variant
   exists. §1-C exists precisely so the router never pretends.

---

## 8. Register

| Variant | Status | Verified | Maintainer |
| --- | --- | --- | --- |
| `GREENFIELD-NODE.md` | active | October 2026 | <team> |
| `GREENFIELD-RUST.md` | active | October 2026 | <team> |
| Python, Go, Java/Kotlin, C# | not written | — | — |

A row is only "active" if the version facts at its top are within a quarter and
its CI claims still run. Demote before you let it mislead.

---

## 9. Keeping the router honest

- **The router stays small.** Every rule added here is a rule that will drift
  from the variant that owns it. Additions belong in the shared-invariant table
  (§3) only when they are genuinely language-independent.
- **Re-ask the question when the constraints change**, not on a calendar — a new
  latency SLO, a mandated SSO, a team change. Record the new answer as a
  superseding addendum; never edit `0001`.
- **Keep the recommendation current.** If Rust becomes the default for this
  organisation's context (or Node does), change §1's recommendation and §2's
  rule of thumb in the same commit, and say why in the commit message.
- **Re-verify the register quarterly.** A variant's "verified" date must mean the
  versions and platform facts inside it were checked, not that the file exists.
- **Never let the router name a stack the variants do not implement.** The
  failure mode is an agent citing §4's table as if it were a rule, and inventing
  a project that matches neither template.
