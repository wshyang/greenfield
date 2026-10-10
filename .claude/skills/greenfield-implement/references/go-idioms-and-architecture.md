# Go `1.27.3` Implementation & Architecture Reference

## 1. Go `1.24–1.27` Standard-Library Defaults (Retire Legacy Shims)

- **UUIDv7:** stdlib `"uuid"` (`uuid.NewV7()`) — mint in one helper inside `internal/kernel`.
- **JSON:** stdlib `"encoding/json/v2"` (`jsonv2.UnmarshalRead` with `jsonv2.RejectUnknownMembers(true)` on inbound bodies; `omitzero` instead of `omitempty`; note `nil` slices marshal as `[]` in v2 vs `null` in v1!).
- **Errors & Pointers:** `errors.AsType[TargetErr](err)` (Go `1.26+` generic error inspection), `new(expr)` pointer helper, `fmt.Errorf("context: %w", err)` once at boundaries (log OR return, never both).
- **Concurrency & Leak Detection:** `errgroup.WithContext(ctx)` with `.SetLimit(n)`, `sync.WaitGroup.Go(fn)` (Go `1.25+`), `t.Context()`, `testing/synctest` for deterministic time/retry tests, `uber-go/goleak` in `TestMain` + Go `1.27` `/debug/pprof/goroutineleak`.
- **Security:** `http.CrossOriginProtection` (`1.25+` Fetch-Metadata CSRF), `os.Root` (`1.24+` traversal-proof FS), explicit `ReadHeaderTimeout` / `MaxBytesReader`, CIDR-validated `X-Forwarded-For` parser, never `http.DefaultClient` or `http.DefaultServeMux`.

## 2. Domain Types, `PatchField[T]`, `Secret[T]` & `effects.Outcome[T]`

- **Parse, don't validate (zero-value safe):** wrap validated strings/scalars in structs with **unexported fields** (`type Email struct { v string }`, `ParseEmail(raw) (Email, error)`), never bare `type Email string` (which lets `Email("")` bypass validation).
- **3-state `PATCH` (`PatchField[T]`):** distinguish omitted (`Set == false`), explicit JSON `null` (`Set && Null`), and value (`Set && !Null && Value`) in custom `UnmarshalJSONFrom` (`json/v2`).
- **`Secret[T]`:** implement `fmt.Stringer`, `slog.LogValuer`, and `MarshalJSONTo` returning `"[REDACTED]"`; expose raw value only via `.Expose()`.
- **Post-commit effects (`internal/platform/effects`):**
  ```go
  type Outcome[T any] struct {
      val    T
      events []kernel.Event // unexported: caller CANNOT read val directly!
  }
  func (o Outcome[T]) Publish(ctx context.Context, pub Publisher) (T, error)
  func (o Outcome[T]) Discard(reason string) T
  ```
  Back with a `go/types` rule in `./cmd/check-standards` banning `Outcome[struct{}]`. Use `river.InsertTx(ctx, tx, ...)` (`DR-08`) inside `pgx.Tx` when external delivery must survive a crash between `Commit` and `Publish`.

## 3. Canonical Package Layout & `internal/arch_test.go`

- `cmd/server/main.go`: sole composition root (`serve | migrate | healthcheck | dump-openapi | gen-shared-rules`) + graceful signal shutdown.
- `internal/kernel`: **stdlib-only** leaf (`RequestID`, `ActorID`, `Clock`, `Secret[T]`, `Event`).
- `internal/platform/*`: domain-agnostic infra (`config`, `httpx`, `problem`, `effects`, `telemetry`, `testdb`) — imports `kernel`, **zero domain imports**.
- `internal/<domain>/`: vertical feature package (`model.go`, pure zero-I/O `policy.go`, `queries.sql` + `queries.sql.go`, `handlers.go`, `<domain>_test.go`).
- Ban `pkg/`, `internal/utils`, `internal/common`, horizontal `controllers/services/repositories`, `func init()` side effects, and `context.WithValue` DI.
- Enforce the DAG in `internal/arch_test.go` (`golang.org/x/tools/go/packages`) and prove it catches a synthetic forbidden edge.
