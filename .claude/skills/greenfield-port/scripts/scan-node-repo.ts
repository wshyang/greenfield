// Zero-dependency mechanical scanner for porting a Node.js / TypeScript repository
// to Go 1.27 (or Rust 1.99). Uses only erasable TypeScript syntax + Node built-ins
// so Node 22+ executes it directly with zero npm install and zero LLM script-token cost.

import fs from "node:fs";
import path from "node:path";

interface CliOpts {
  repoRoot: string;
  target: "go" | "rust";
  format: "markdown" | "json";
  outPath: string | null;
}

interface RouteHit {
  file: string;
  line: number;
  kind: "http" | "nextjs-route" | "ws" | "sse";
  signature: string;
}

interface TestBucketEntry {
  file: string;
  bucket: 1 | 2 | 3;
  bucketLabel: "Bucket 1 (black-box HTTP/E2E)" | "Bucket 2 (HTTP + DB/helper setup)" | "Bucket 3 (white-box / mocked unit)";
  signals: string[];
}

interface SiteHit {
  file: string;
  line: number;
  snippet: string;
}

interface HazardSummary {
  id: string;
  name: string;
  targetNote: string;
  count: number;
  recheckCmd: string;
  samples: SiteHit[];
}

const IGNORED_DIRS = new Set([
  ".git",
  "node_modules",
  "dist",
  "build",
  "out",
  ".next",
  ".nuxt",
  ".svelte-kit",
  ".turbo",
  "coverage",
  ".cache",
  "vendor",
  ".claude",
]);

const CODE_EXTS = new Set([".ts", ".tsx", ".mts", ".cts", ".js", ".jsx", ".mjs", ".cjs"]);

function parseArgs(argv: string[]): CliOpts {
  let repoRoot = process.cwd();
  let target: "go" | "rust" = "go";
  let format: "markdown" | "json" = "markdown";
  let outPath: string | null = null;

  for (let i = 0; i < argv.length; i++) {
    const arg = argv[i];
    if (arg === "--target" && argv[i + 1]) {
      const val = argv[++i].toLowerCase();
      if (val === "go" || val === "rust") target = val;
    } else if (arg === "--format" && argv[i + 1]) {
      const val = argv[++i].toLowerCase();
      if (val === "markdown" || val === "json") format = val;
    } else if (arg === "--out" && argv[i + 1]) {
      outPath = argv[++i];
    } else if (!arg.startsWith("-")) {
      repoRoot = path.resolve(arg);
    }
  }
  return { repoRoot, target, format, outPath };
}

/**
 * Strips // line comments and /* block comments * / while preserving every '\n'
 * so line numbers remain 100% identical to the source file, and respecting string
 * literals ('...', "...", `...`) so URLs like "http://..." are never mangled.
 */
export function stripCommentsPreserveLines(src: string): string {
  const out: string[] = [];
  let i = 0;
  const n = src.length;
  let state: "code" | "squote" | "dquote" | "tmpl" | "line_cmt" | "block_cmt" = "code";

  while (i < n) {
    const ch = src[i];
    const next = i + 1 < n ? src[i + 1] : "";

    if (state === "code") {
      if (ch === "/" && next === "/") {
        state = "line_cmt";
        out.push("  ");
        i += 2;
        continue;
      }
      if (ch === "/" && next === "*") {
        state = "block_cmt";
        out.push("  ");
        i += 2;
        continue;
      }
      if (ch === "'") state = "squote";
      else if (ch === '"') state = "dquote";
      else if (ch === "`") state = "tmpl";
      out.push(ch);
      i++;
    } else if (state === "line_cmt") {
      if (ch === "\n") {
        state = "code";
        out.push("\n");
      } else {
        out.push(" ");
      }
      i++;
    } else if (state === "block_cmt") {
      if (ch === "*" && next === "/") {
        state = "code";
        out.push("  ");
        i += 2;
      } else {
        out.push(ch === "\n" ? "\n" : " ");
        i++;
      }
    } else {
      // Inside a string or template literal
      if (ch === "\\" && i + 1 < n) {
        out.push(ch, src[i + 1]);
        i += 2;
        continue;
      }
      if (
        (state === "squote" && ch === "'") ||
        (state === "dquote" && ch === '"') ||
        (state === "tmpl" && ch === "`")
      ) {
        state = "code";
      }
      out.push(ch);
      i++;
    }
  }
  return out.join("");
}

function walkRepo(root: string): string[] {
  const results: string[] = [];
  function visit(dir: string): void {
    let entries: fs.Dirent[];
    try {
      entries = fs.readdirSync(dir, { withFileTypes: true });
    } catch {
      return;
    }
    entries.sort((a, b) => a.name.localeCompare(b.name));
    for (const ent of entries) {
      if (IGNORED_DIRS.has(ent.name)) continue;
      const full = path.join(dir, ent.name);
      if (ent.isDirectory()) {
        visit(full);
      } else if (ent.isFile()) {
        results.push(full);
      }
    }
  }
  visit(root);
  return results;
}

function toPosixRel(root: string, full: string): string {
  return path.relative(root, full).split(path.sep).join("/");
}

function isTestFile(rel: string): boolean {
  return (
    /\.(test|spec)\.[cm]?[jt]sx?$/.test(rel) ||
    /(^|\/)(__tests__|e2e|playwright|cypress)\//.test(rel)
  );
}

function isFrontendFile(rel: string): boolean {
  return (
    rel.endsWith(".tsx") ||
    rel.endsWith(".jsx") ||
    /(^|\/)(frontend|client|web|ui|public)\//.test(rel) ||
    /(^|\/)(sw|service-worker)\.[cm]?[jt]s$/.test(rel)
  );
}

function resolveRelativeImport(importerRel: string, spec: string, knownSet: Set<string>): string | null {
  if (!spec.startsWith(".")) return null;
  const baseDir = path.posix.dirname(importerRel);
  const raw = path.posix.normalize(path.posix.join(baseDir, spec));
  const candidates = [
    raw,
    raw.replace(/\.[cm]?js$/, ".ts"),
    raw.replace(/\.[cm]?jsx$/, ".tsx"),
    `${raw}.ts`,
    `${raw}.tsx`,
    `${raw}.js`,
    `${raw}/index.ts`,
    `${raw}/index.js`,
  ];
  for (const c of candidates) {
    if (knownSet.has(c)) return c;
  }
  return null;
}

function extractImports(cleanCode: string): string[] {
  const specs: string[] = [];
  const reStatic = /\b(?:import|export)\s+(?:[^'"]*?\s+from\s+)?['"]([^'"]+)['"]/g;
  const reDynamic = /\b(?:import|require)\s*\(\s*['"]([^'"]+)['"]\s*\)/g;
  for (const m of cleanCode.matchAll(reStatic)) specs.push(m[1]);
  for (const m of cleanCode.matchAll(reDynamic)) specs.push(m[1]);
  return specs;
}

function scanRepository(opts: CliOpts) {
  const allFiles = walkRepo(opts.repoRoot);
  const relFiles = allFiles.map((f) => toPosixRel(opts.repoRoot, f));
  const codeRelFiles = relFiles.filter((r) => CODE_EXTS.has(path.posix.extname(r)) && !r.endsWith(".d.ts"));
  const knownCodeSet = new Set(codeRelFiles);

  // 1. Package manifests & dependency stack
  const pkgFiles = relFiles.filter((r) => r === "package.json" || r.endsWith("/package.json"));
  const allDeps = new Map<string, string>();
  const npmScripts: Record<string, string> = {};
  let moduleType = "commonjs (default)";
  let workspaces: string[] = [];

  for (const pf of pkgFiles) {
    try {
      const pkg = JSON.parse(fs.readFileSync(path.join(opts.repoRoot, pf), "utf8"));
      if (pf === "package.json") {
        if (pkg.type === "module") moduleType = "esm (type: module)";
        if (Array.isArray(pkg.workspaces)) workspaces = pkg.workspaces;
        else if (pkg.workspaces && Array.isArray(pkg.workspaces.packages)) workspaces = pkg.workspaces.packages;
        if (pkg.scripts && typeof pkg.scripts === "object") {
          for (const [k, v] of Object.entries(pkg.scripts)) npmScripts[k] = String(v);
        }
      }
      for (const sec of ["dependencies", "devDependencies"]) {
        const map = pkg[sec];
        if (map && typeof map === "object") {
          for (const [dep, ver] of Object.entries(map)) {
            if (!allDeps.has(dep)) allDeps.set(dep, String(ver));
          }
        }
      }
    } catch {
      // Ignore malformed package.json
    }
  }

  const detectMatches = (candidates: string[]) => candidates.filter((c) => allDeps.has(c));
  const stackSummary = {
    moduleType,
    workspaces,
    packageJsonCount: pkgFiles.length,
    frameworks: detectMatches(["fastify", "express", "next", "hono", "koa", "@nestjs/core", "@trpc/server"]),
    ormAndDb: detectMatches(["drizzle-orm", "prisma", "@prisma/client", "kysely", "knex", "typeorm", "sequelize", "pg", "postgres", "better-sqlite3", "@electric-sql/pglite"]),
    auth: detectMatches(["passport", "@fastify/cookie", "@fastify/session", "express-session", "jose", "jsonwebtoken", "openid-client", "lucia", "better-auth", "next-auth"]),
    validation: detectMatches(["zod", "@sinclair/typebox", "valibot", "joi", "ajv", "yup"]),
    jobsAndRealtime: detectMatches(["bullmq", "pg-boss", "agenda", "ws", "@fastify/websocket", "socket.io", "ioredis", "redis"]),
    testing: detectMatches(["vitest", "jest", "@playwright/test", "playwright", "cypress", "supertest"]),
  };

  // 2. Scan code files
  const routes: RouteHit[] = [];
  const statusCodeCounts: Record<string, number> = { "401": 0, "403": 0, "404": 0, "409": 0, "422": 0 };
  const testLedger: TestBucketEntry[] = [];
  const singleInstanceHits: SiteHit[] = [];
  const testWorkaroundHits: SiteHit[] = [];
  const pureGoldenCandidates: string[] = [];

  const frontendImports = new Set<string>();
  const backendImports = new Set<string>();

  const hazardBuckets: Record<string, SiteHit[]> = {
    clock: [],
    rng: [],
    bareSort: [],
    roundingAndFloat: [],
    bitwise32: [],
    utf16LenSlice: [],
    jsonAndObjectOrder: [],
    patchUndefinedNull: [],
  };

  for (const rel of codeRelFiles) {
    const full = path.join(opts.repoRoot, rel);
    const raw = fs.readFileSync(full, "utf8");
    const clean = stripCommentsPreserveLines(raw);
    const lines = clean.split("\n");
    const rawLines = raw.split("\n");
    const imports = extractImports(clean);

    // Classify tests mechanically into 3 buckets
    if (isTestFile(rel)) {
      const signals: string[] = [];
      const hasE2eOrHttp =
        imports.some((s) => /playwright|cypress|supertest|undici/.test(s)) ||
        /\b(app\.inject|request\(app\)|page\.goto|fetch\()\b/.test(clean);
      const hasDbOrInternal =
        imports.some((s) => /drizzle|prisma|kysely|knex|typeorm|\bpg\b|db|queries|schema|pglite|sqlite/.test(s)) ||
        /\b(db\.(select|insert|update|delete|execute|query)|prisma\.)\b/.test(clean);
      const hasWhiteboxMocks = /\b(vi|jest)\.(mock|spyOn|fn)\b|\bsinon\./.test(clean);

      if (hasE2eOrHttp) signals.push("HTTP/E2E");
      if (hasDbOrInternal) signals.push("DB/ORM");
      if (hasWhiteboxMocks) signals.push("mocks/spies");

      let bucket: 1 | 2 | 3;
      let bucketLabel: TestBucketEntry["bucketLabel"];
      if (hasE2eOrHttp && !hasDbOrInternal && !hasWhiteboxMocks) {
        bucket = 1;
        bucketLabel = "Bucket 1 (black-box HTTP/E2E)";
      } else if (hasE2eOrHttp && !hasWhiteboxMocks) {
        bucket = 2;
        bucketLabel = "Bucket 2 (HTTP + DB/helper setup)";
      } else {
        bucket = 3;
        bucketLabel = "Bucket 3 (white-box / mocked unit)";
      }
      testLedger.push({ file: rel, bucket, bucketLabel, signals: signals.length ? signals : ["unit/direct-import"] });

      // Detect single-writer test DB workarounds in test/config files
      lines.forEach((ln, idx) => {
        if (/\b(PGlite|pglite|better-sqlite3|:memory:|fileParallelism\s*:\s*false|maxConcurrency\s*:\s*1|workers\s*:\s*1|runInBand)\b/.test(ln)) {
          testWorkaroundHits.push({ file: rel, line: idx + 1, snippet: rawLines[idx].trim().slice(0, 110) });
        }
      });
      continue;
    }

    // Track test runner configs for single-writer workarounds too
    if (/(vitest|jest|playwright)\.config\.[cm]?[jt]s$/.test(rel)) {
      lines.forEach((ln, idx) => {
        if (/\b(fileParallelism\s*:\s*false|maxConcurrency\s*:\s*1|workers\s*:\s*1|retries\s*:\s*[1-9])\b/.test(ln)) {
          testWorkaroundHits.push({ file: rel, line: idx + 1, snippet: rawLines[idx].trim().slice(0, 110) });
        }
      });
      continue;
    }

    // Track cross-boundary shared imports (Frontend/Worker <-> Backend)
    const isFront = isFrontendFile(rel);
    for (const spec of imports) {
      const resolved = resolveRelativeImport(rel, spec, knownCodeSet);
      if (resolved) {
        if (isFront) frontendImports.add(resolved);
        else backendImports.add(resolved);
      } else if (spec.startsWith("@") && !spec.startsWith("@types/")) {
        // Workspace package import candidate
        if (isFront) frontendImports.add(spec);
        else backendImports.add(spec);
      }
    }

    if (isFront) continue; // Backend-focused scans below

    // Next.js App Router route file check
    if (/(^|\/)app\/api\/.*\/route\.[cm]?[jt]s$/.test(rel)) {
      routes.push({ file: rel, line: 1, kind: "nextjs-route", signature: "Next.js App Router handler" });
    }

    // Pure golden-fixture candidate check (backend non-UI file with zero IO/framework/DB imports, exporting functions)
    const hasIoImport = imports.some((s) =>
      /^(node:|fs|path|http|https|net|crypto|child_process|stream|fastify|express|hono|koa|next|@nestjs|drizzle|prisma|kysely|knex|pg|postgres|ioredis|redis|bullmq|ws|socket\.io)/.test(s),
    );
    if (!hasIoImport && /\bexport\s+(function|const)\s+[A-Za-z0-9_]+/.test(clean) && !/\bprocess\.env\b/.test(clean)) {
      pureGoldenCandidates.push(rel);
    }

    // Line-by-line backend inspections
    let braceDepth = 0;
    for (let idx = 0; idx < lines.length; idx++) {
      const ln = lines[idx];
      const rawTrim = rawLines[idx].trim().slice(0, 110);
      const lineNo = idx + 1;

      // Routes (HTTP / WS / SSE)
      const routeMatch = ln.match(/\b(app|router|fastify|server|api)\.(get|post|put|patch|delete|all|route|ws)\s*\(\s*(['"`][^'"`]+['"`])/);
      if (routeMatch) {
        routes.push({
          file: rel,
          line: lineNo,
          kind: routeMatch[2] === "ws" ? "ws" : "http",
          signature: `${routeMatch[2].toUpperCase()} ${routeMatch[3]}`,
        });
      }
      if (/text\/event-stream/.test(ln)) {
        routes.push({ file: rel, line: lineNo, kind: "sse", signature: "SSE text/event-stream" });
      }
      if (/\bnew\s+WebSocketServer\b|\bsocket\.io\b/.test(ln)) {
        routes.push({ file: rel, line: lineNo, kind: "ws", signature: "WebSocketServer / socket.io" });
      }

      // Explicit HTTP status codes (authz 401/403 vs 404 parity!)
      for (const m of ln.matchAll(/\b(?:status|code|sendStatus)\s*\(\s*(401|403|404|409|422)\s*\)/g)) {
        statusCodeCounts[m[1]] = (statusCodeCounts[m[1]] || 0) + 1;
      }

      // Module-level (braceDepth === 0) mutable state & replicas=1 assumptions
      if (braceDepth === 0 && /\bnew\s+(Map|Set|WeakMap|LRUCache|NodeCache)\b/.test(ln)) {
        singleInstanceHits.push({ file: rel, line: lineNo, snippet: rawTrim });
      }
      if (/\b(setInterval|cron\.schedule|new\s+CronJob)\s*\(/.test(ln)) {
        singleInstanceHits.push({ file: rel, line: lineNo, snippet: rawTrim });
      }
      if (/\b(writeFileSync|writeFile|createWriteStream|appendFile|tmpdir)\s*\(/.test(ln)) {
        singleInstanceHits.push({ file: rel, line: lineNo, snippet: rawTrim });
      }

      // Determinism hazards
      if (/\bDate\.now\s*\(|\bnew\s+Date\s*\(\s*\)|\bperformance\.now\s*\(/.test(ln)) {
        hazardBuckets.clock.push({ file: rel, line: lineNo, snippet: rawTrim });
      }
      if (/\bMath\.random\s*\(|\brandomUUID\s*\(/.test(ln)) {
        hazardBuckets.rng.push({ file: rel, line: lineNo, snippet: rawTrim });
      }
      if (/\.sort\s*\(\s*\)/.test(ln)) {
        hazardBuckets.bareSort.push({ file: rel, line: lineNo, snippet: rawTrim });
      }
      if (/\bMath\.round\s*\(|\.toFixed\s*\(/.test(ln)) {
        hazardBuckets.roundingAndFloat.push({ file: rel, line: lineNo, snippet: rawTrim });
      }
      if (/(\|\s*0\b|>>>\s*0\b|\bMath\.imul\s*\()/.test(ln)) {
        hazardBuckets.bitwise32.push({ file: rel, line: lineNo, snippet: rawTrim });
      }
      if (/\.(charCodeAt|codePointAt|substring)\s*\(/.test(ln) || (/\.length\b/.test(ln) && /\b(max|min|limit|trunc|valid|len|char)/i.test(ln))) {
        hazardBuckets.utf16LenSlice.push({ file: rel, line: lineNo, snippet: rawTrim });
      }
      if (/\bJSON\.stringify\s*\(|\bObject\.(keys|entries|values)\s*\(|\bfor\s*\(\s*(?:const|let|var)\s+\w+\s+in\b/.test(ln)) {
        hazardBuckets.jsonAndObjectOrder.push({ file: rel, line: lineNo, snippet: rawTrim });
      }
      if (/\bundefined\b.*!==|\bnull\b.*!==|\.optional\s*\(\s*\)\.nullable\s*\(\s*\)|\.nullish\s*\(\s*\)/.test(ln)) {
        hazardBuckets.patchUndefinedNull.push({ file: rel, line: lineNo, snippet: rawTrim });
      }

      for (const ch of ln) {
        if (ch === "{") braceDepth++;
        else if (ch === "}") braceDepth = Math.max(0, braceDepth - 1);
      }
    }
  }

  // Shared client/server imports intersection
  const sharedClientServerModules = [...frontendImports].filter(
    (x) => backendImports.has(x) || (knownCodeSet.has(x) && !isFrontendFile(x)),
  ).sort();

  // Auxiliary scripts inventory
  const auxScriptFiles = relFiles.filter(
    (r) => /\.(sh|py)$/.test(r) || /^(scripts|bin|tools)\//.test(r),
  );

  const isGo = opts.target === "go";
  const hazards: HazardSummary[] = [
    {
      id: "HZ-01",
      name: "Ambient clock (`Date.now()`, `new Date()`, `performance.now()`)",
      targetNote: isGo ? "Inject `Clock` interface; test with `testing/synctest` (§20.3)" : "Inject `Clock` trait; gate deterministic replay clock out of release (§20.3)",
      count: hazardBuckets.clock.length,
      recheckCmd: `git grep -nE "Date\\.now\\(|new Date\\(\\s*\\)|performance\\.now\\(" -- '*.ts' '*.js' ':!*.test.*' ':!*.spec.*'`,
      samples: hazardBuckets.clock.slice(0, 5),
    },
    {
      id: "HZ-02",
      name: "Ambient RNG & UUIDv4 (`Math.random()`, `randomUUID()`)",
      targetNote: isGo ? "Use `uuid.NewV7()` in `internal/kernel` + seeded `math/rand/v2` or `crypto/rand`" : "Use `Uuid::now_v7()` + seeded RNG in test-only deterministic feature",
      count: hazardBuckets.rng.length,
      recheckCmd: `git grep -nE "Math\\.random\\(|randomUUID\\(" -- '*.ts' '*.js' ':!*.test.*' ':!*.spec.*'`,
      samples: hazardBuckets.rng.slice(0, 5),
    },
    {
      id: "HZ-03",
      name: "Comparator-free `.sort()` (JS UTF-16 lexicographic sort)",
      targetNote: isGo ? "Use `slices.SortStableFunc` with explicit total tie-breaker comparator" : "Use stable `.sort_by(...)` with total tie-breaker comparator",
      count: hazardBuckets.bareSort.length,
      recheckCmd: `git grep -nE "\\.sort\\(\\s*\\)" -- '*.ts' '*.js' ':!*.test.*' ':!*.spec.*'`,
      samples: hazardBuckets.bareSort.slice(0, 5),
    },
    {
      id: "HZ-04",
      name: "Tie rounding & float formatting (`Math.round`, `.toFixed`)",
      targetNote: isGo ? "`Math.round(-0.5)` is `-0`, Go `math.Round(-0.5)` is `-1` (`RoundToEven` is `0`); use golden-tested helper / `int64` minor units" : "`f64::round(-0.5)` is `-1.0`; use `rust_decimal` with explicit midpoint strategy",
      count: hazardBuckets.roundingAndFloat.length,
      recheckCmd: `git grep -nE "Math\\.round\\(|\\.toFixed\\(" -- '*.ts' '*.js' ':!*.test.*' ':!*.spec.*'`,
      samples: hazardBuckets.roundingAndFloat.slice(0, 5),
    },
    {
      id: "HZ-05",
      name: "32-bit JS bitwise truncation (`| 0`, `>>> 0`, `Math.imul`)",
      targetNote: isGo ? "Go `int` is 64-bit; use explicit `int32`/`uint32` for legacy hash/checksum parity" : "Use explicit `i32`/`u32` wrapping ops (`wrapping_mul`, etc.)",
      count: hazardBuckets.bitwise32.length,
      recheckCmd: `git grep -nE "\\|\\s*0\\b|>>>\\s*0\\b|Math\\.imul\\(" -- '*.ts' '*.js' ':!*.test.*' ':!*.spec.*'`,
      samples: hazardBuckets.bitwise32.slice(0, 5),
    },
    {
      id: "HZ-06",
      name: "UTF-16 string `.length` / `.substring` / `.charCodeAt` bounds",
      targetNote: isGo ? "Go `len(s)` = UTF-8 bytes, `utf8.RuneCountInString` = code points, `uniseg` = graphemes; test CJK + emoji" : "Rust `s.len()` = UTF-8 bytes, `.chars().count()` = code points, `unicode-segmentation` = graphemes",
      count: hazardBuckets.utf16LenSlice.length,
      recheckCmd: `git grep -nE "\\.(charCodeAt|codePointAt|substring)\\(|\\.length\\b" -- '*.ts' '*.js' ':!*.test.*' ':!*.spec.*'`,
      samples: hazardBuckets.utf16LenSlice.slice(0, 5),
    },
    {
      id: "HZ-07",
      name: "`JSON.stringify` (`undefined` drop) & object key-order iteration",
      targetNote: isGo ? "Go randomises `map` iteration (`encoding/json` sorts map keys; `json/v2` marshals `nil` slice to `[]` vs v1 `null`)" : "Rust `HashMap` randomises iteration; use `IndexMap`/`BTreeMap` and explicit `skip_serializing_if`",
      count: hazardBuckets.jsonAndObjectOrder.length,
      recheckCmd: `git grep -nE "JSON\\.stringify\\(|Object\\.(keys|entries|values)\\(" -- '*.ts' '*.js' ':!*.test.*' ':!*.spec.*'`,
      samples: hazardBuckets.jsonAndObjectOrder.slice(0, 5),
    },
    {
      id: "HZ-08",
      name: "Tri-state `undefined` vs `null` vs value (`PATCH` / `.nullish()`)",
      targetNote: isGo ? "Use `PatchField[T]` (`Set`, `Null`, `Value`) at wire boundaries so Go zero values never conflate with omitted" : "Use `Option<Option<T>>` with custom serde deserializer",
      count: hazardBuckets.patchUndefinedNull.length,
      recheckCmd: `git grep -nE "\\.nullish\\(|\\.nullable\\(" -- '*.ts' '*.js' ':!*.test.*' ':!*.spec.*'`,
      samples: hazardBuckets.patchUndefinedNull.slice(0, 5),
    },
  ];

  const b1 = testLedger.filter((t) => t.bucket === 1).length;
  const b2 = testLedger.filter((t) => t.bucket === 2).length;
  const b3 = testLedger.filter((t) => t.bucket === 3).length;

  return {
    scannedAt: new Date().toISOString().slice(0, 10),
    repoRoot: opts.repoRoot,
    targetLanguage: opts.target,
    totals: {
      allFiles: relFiles.length,
      codeFiles: codeRelFiles.length,
      backendRoutes: routes.length,
      testFiles: testLedger.length,
      bucket1Blackbox: b1,
      bucket2HttpDb: b2,
      bucket3Whitebox: b3,
      sharedClientServerModules: sharedClientServerModules.length,
      singleInstanceSites: singleInstanceHits.length,
      pureGoldenCandidates: pureGoldenCandidates.length,
    },
    stackSummary,
    statusCodeCounts,
    sharedClientServerModules,
    routes,
    testLedger,
    singleInstanceHits,
    testWorkaroundHits,
    pureGoldenCandidates,
    hazards,
    npmScripts,
    auxScriptFiles,
  };
}

function renderMarkdown(r: ReturnType<typeof scanRepository>): string {
  const tgt = r.targetLanguage === "go" ? "Go 1.27" : "Rust 1.99";
  const lines: string[] = [];
  lines.push(`# Mechanical Porting Readiness Audit (Node/TS → ${tgt})`);
  lines.push("");
  lines.push(`- **Scanned repository:** \`${r.repoRoot}\` (${r.totals.codeFiles} JS/TS files across ${r.stackSummary.packageJsonCount} \`package.json\` manifest(s))`);
  lines.push(`- **Module system:** \`${r.stackSummary.moduleType}\`${r.stackSummary.workspaces.length ? ` · Workspaces: \`${r.stackSummary.workspaces.join(", ")}\`` : ""}`);
  lines.push(`- **Detected stack:** frameworks=[${r.stackSummary.frameworks.join(", ") || "none"}] · db=[${r.stackSummary.ormAndDb.join(", ") || "none"}] · auth=[${r.stackSummary.auth.join(", ") || "none"}] · validation=[${r.stackSummary.validation.join(", ") || "none"}] · jobs/realtime=[${r.stackSummary.jobsAndRealtime.join(", ") || "none"}] · tests=[${r.stackSummary.testing.join(", ") || "none"}]`);
  lines.push("");

  lines.push(`## 1. HTTP / Realtime Surface & Legacy Status-Code Footprint (§20.1)`);
  lines.push("");
  lines.push(`- **Detected route/realtime registrations:** \`${r.totals.backendRoutes}\` (verify against live router table)`);
  lines.push(`- **Explicit error-status call sites:** \`401\`=${r.statusCodeCounts["401"]} · \`403\`=${r.statusCodeCounts["403"]} · \`404\`=${r.statusCodeCounts["404"]} · \`409\`=${r.statusCodeCounts["409"]} · \`422\`=${r.statusCodeCounts["422"]} *(preserve legacy \`401\`/\`403\` vs \`404\` on unchanged client boundaries until a post-cutover addendum changes them)*`);
  if (r.routes.length > 0) {
    lines.push("");
    lines.push("| Kind | Signature | Location |");
    lines.push("| --- | --- | --- |");
    for (const rt of r.routes.slice(0, 40)) {
      lines.push(`| \`${rt.kind}\` | \`${rt.signature}\` | \`${rt.file}:${rt.line}\` |`);
    }
    if (r.routes.length > 40) lines.push(`| … | *(${r.routes.length - 40} additional routes omitted)* | — |`);
  }
  lines.push("");

  lines.push(`## 2. Mechanical 3-Bucket Legacy Test Ledger (\`${r.totals.testFiles}\` files, 0 unaccounted)`);
  lines.push("");
  lines.push(`- **Bucket 1 — Pure black-box HTTP/E2E (\`${r.totals.bucket1Blackbox}\`):** repoint unchanged via \`TARGET_BACKEND=legacy|${r.targetLanguage}\`.`);
  lines.push(`- **Bucket 2 — HTTP + internal DB/helper setup (\`${r.totals.bucket2HttpDb}\`):** port HTTP assertions; replace setup with SQL fixtures.`);
  lines.push(`- **Bucket 3 — White-box / mocked unit tests (\`${r.totals.bucket3Whitebox}\`):** export pure logic as golden fixtures (§20.2) and replace repo mocks with real-DB integration tests.`);
  if (r.testLedger.length > 0) {
    lines.push("");
    lines.push("| Test File | Assigned Bucket | Detected Signals |");
    lines.push("| --- | --- | --- |");
    for (const t of r.testLedger) {
      lines.push(`| \`${t.file}\` | ${t.bucketLabel} | ${t.signals.join(", ")} |`);
    }
  }
  lines.push("");

  lines.push(`## 3. Shared Browser/Worker ↔ Server Modules (\`${r.sharedClientServerModules.length}\`) & Golden Candidates (\`${r.pureGoldenCandidates.length}\`)`);
  lines.push("");
  if (r.sharedClientServerModules.length > 0) {
    lines.push("**Modules imported by BOTH frontend/worker and backend** (decide per file: `./cmd/server gen-shared-rules` catalogue vs shared golden corpus" + (r.targetLanguage === "go" ? "; avoid ~2–5 MB Go WASM unless heavy offline engine" : " or `wasm32-unknown-unknown`") + "):");
    for (const m of r.sharedClientServerModules) lines.push(`- \`${m}\``);
  } else {
    lines.push("- Zero direct cross-boundary TS imports detected between frontend and backend.");
  }
  lines.push("");
  if (r.pureGoldenCandidates.length > 0) {
    lines.push("**Pure backend modules (zero I/O imports — prime §20.2 golden-fixture export targets):**");
    for (const p of r.pureGoldenCandidates.slice(0, 25)) lines.push(`- \`${p}\``);
    if (r.pureGoldenCandidates.length > 25) lines.push(`- *(+${r.pureGoldenCandidates.length - 25} more)*`);
  }
  lines.push("");

  lines.push(`## 4. JS → ${tgt} Determinism Hazard Counts (§20.3)`);
  lines.push("");
  lines.push("| ID | Hazard | Sites | Target Porting Rule | Re-check Command |");
  lines.push("| --- | --- | ---: | --- | --- |");
  for (const h of r.hazards) {
    lines.push(`| \`${h.id}\` | ${h.name} | **${h.count}** | ${h.targetNote} | \`${h.recheckCmd}\` |`);
  }
  lines.push("");

  lines.push(`## 5. Quiet Legacy Assumptions (§20.6)`);
  lines.push("");
  lines.push(`- **Implicit \`replicas = 1\` state / timers / local FS sites (\`${r.singleInstanceHits.length}\`):** move to Postgres or guard single-replica boot with a Postgres session advisory lock.`);
  for (const s of r.singleInstanceHits.slice(0, 15)) {
    lines.push(`  - \`${s.file}:${s.line}\` — \`${s.snippet}\``);
  }
  lines.push(`- **Single-writer test-DB / serialisation workarounds (\`${r.testWorkaroundHits.length}\`):** document before removing on real multi-session Postgres.`);
  for (const w of r.testWorkaroundHits.slice(0, 10)) {
    lines.push(`  - \`${w.file}:${w.line}\` — \`${w.snippet}\``);
  }
  lines.push(`- **npm scripts (\`${Object.keys(r.npmScripts).length}\`) & auxiliary ops scripts (\`${r.auxScriptFiles.length}\`):** fold seed/migrate/healthcheck scripts into compiled server subcommands.`);
  for (const a of r.auxScriptFiles.slice(0, 15)) {
    lines.push(`  - \`${a}\``);
  }
  lines.push("");
  return lines.join("\n");
}

if (import.meta.url === `file://${process.argv[1]}`) {
  const opts = parseArgs(process.argv.slice(2));
  if (!fs.existsSync(opts.repoRoot)) {
    process.stderr.write(`Error: repository path does not exist: ${opts.repoRoot}\n`);
    process.exit(1);
  }
  const report = scanRepository(opts);
  const output = opts.format === "json" ? JSON.stringify(report, null, 2) + "\n" : renderMarkdown(report);
  if (opts.outPath) {
    fs.mkdirSync(path.dirname(path.resolve(opts.outPath)), { recursive: true });
    fs.writeFileSync(opts.outPath, output, "utf8");
    process.stdout.write(`Wrote ${opts.format} port scan report to ${opts.outPath} (${report.totals.codeFiles} code files, ${report.totals.testFiles} test files classified).\n`);
  } else {
    process.stdout.write(output);
  }
}
