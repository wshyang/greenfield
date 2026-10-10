# Node.js `22 LTS` + TypeScript `5` Implementation & Architecture Reference

## 1. Module Boundaries (`packages/` + `dependency-cruiser` + Fastify Encapsulation)

TypeScript erases visibility at build time and `export` is not a module wall. Combine three mechanisms:

1. **Workspace packages with strict `package.json` `"exports"`** (`".": "./src/index.ts"`), starting with a zero-I/O leaf `packages/kernel` (branded IDs, `Clock`, `MustPublish<T>`, `DomainEvent`) and `packages/shared-rules` (rules shared between Fastify and browser/Service Workers — zero TS-to-TS codegen!).
2. **Four `dependency-cruiser.config.cjs` rules** (tested against a violating fixture in CI):
   - `kernel-is-pure-leaf`: `packages/kernel` / `src/kernel` imports zero `node:*`, ORM, HTTP, or domain paths.
   - `no-cross-module-internals`: `src/<modA>` never imports `src/<modB>/internal`.
   - `domain-does-not-import-infra`: `domain/` never imports `db/`, `http/`, or `adapters/`.
   - `no-circular`: zero import cycles.
3. **Fastify child-context encapsulation:** scope module decorators/hooks inside `app.register(...)` plugins; use `fastify-plugin` **only** for true global infrastructure (DB pool, authn, logger), never `Symbol.for("skip-override")` or string-keyed DI containers. Wire the entire graph explicitly in `src/app.ts`.

## 2. Drizzle Single-Casing, Edge Validation & `MustPublish<T>`

- **One mapper only:** Drizzle `src/db/schema.ts` maps `camelCase` TypeScript properties ↔ `snake_case` Postgres columns; delete any second hand-written mapper layer. Do not wrap DB queries in 1-impl repository `interface`s.
- **No `any` or `as` casts at boundaries or in tests:** parse external inputs with Zod/TypeBox at the edge, and type-check test expectations with **`satisfies WireDto`** (never `as WireDto`).
- **Never mutate in place** (`{ ...prev, status: "closed" }`); never use `forEach(async ...)` (use `for...of await` or `Promise.all`).
- **Post-commit effects via ECMAScript `#private` fields (`MustPublish<T>`):**
  ```ts
  export class MustPublish<T> {
    readonly #value: T;
    readonly #effects: readonly DomainEvent[];
    private constructor(value: T, effects: readonly DomainEvent[]) {
      this.#value = value;
      this.#effects = effects;
    }
    static of<T>(value: T, effects: readonly DomainEvent[]): MustPublish<T> {
      return new MustPublish(value, effects);
    }
    async publish(bus: EffectPublisher): Promise<T> {
      await bus.publishAll(this.#effects);
      return this.#value;
    }
    discard(_reason: string): T { return this.#value; }
  }
  ```
  `#value` and `#effects` cannot be destructured (`Object.keys(res)` is `[]`), forcing callers to invoke `await res.publish(bus)` or `res.discard(reason)`. Use a Drizzle transactional `outbox_events` insert when delivery must survive process crashes.

## 3. Native Node `22+` Tooling

Keep repository automation (`scripts/check-standards.ts`, `scripts/check-plan-docs.ts`) in erasable TypeScript run directly via `node scripts/<name>.ts` — never scatter ad-hoc Python/AWK helper scripts across a Node repo.
