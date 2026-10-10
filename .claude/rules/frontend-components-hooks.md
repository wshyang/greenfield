---
paths:
  - "**/*.tsx"
  - "**/hooks/**/*.ts"
  - "e2e/**"
  - "frontend/**"
  - "playwright.config.*"
---

# Frontend Components, Hooks & E2E Rules

- **A component renders; a hook decides.** Split along the server boundary:
  - Components own JSX layout, view-only state, event wiring, and DOM-only effects — **zero `lib/api` imports** (`grep -c "lib/api" <Component>.tsx` must be `0`).
  - Hooks (`lib/hooks/use<Feature>.ts` + colocated `.test.ts`) own API calls, server-data derivations, validation, and fetch effects — zero JSX and zero imports from `components/`.
  - During separation refactors, **move bodies verbatim** before changing behaviour.
- **Keep JSX interiors presentation-only (`return (...)`):**
  - No `.filter()`, `.reduce()`, `.sort()`, `.find()`, `.some()`, or `.every()` inside `return (...)` (only bare `.map()` rendering pre-computed lists).
  - Compute each derivation once above `return`; no inline `new Date()`, `.toFixed()`, or `JSON.parse`; inline `onClick`/`onChange` handlers do wiring only.
- **`data-testid` on every interactive element at authoring time** using `{component-kebab}__{element-role}`. Repeated rows share one testid; scope by visible anchor text first.
- **Never leak internal decision IDs (`DR-04`, addendum numbers, internal slugs) into user-facing copy.**
- **Shared server + Service Worker rules:** keep immutable-asset regexes, upload bounds, and format lists in one source (`packages/shared-rules` in Node; generated `frontend/src/lib/generated/rules.ts` + CI diff check in Go/Rust).
- **Playwright defaults:** record video by default (`E2E_VIDEO=off` escape hatch), set **`retries: 0`** paired with **`trace: "retain-on-failure"`** (never `"on-first-retry"`, which records nothing under zero retries), drive the real backend with zero API mocks, and assert computed styles in the real browser when layout/visibility is the requirement.
