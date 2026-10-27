# Egress-Restricted Sandbox Bootstrap (Rust 1.99, Go 1.27.3, Node 22.22, Chromium 150)

Use this playbook when running inside a cloud coding container (such as Arena / E2B Debian 12 `bookworm` `x86_64`) where `rustc`, `cargo`, `go`, and `chromium` are missing and TLS SNI allows only `github.com` / `api.github.com` / `codeload.github.com`, `registry.npmjs.org`, and `pypi.org` / `files.pythonhosted.org` (blocking `sh.rustup.rs`, `index.crates.io`, `go.dev`, `proxy.golang.org`, `sum.golang.org`, `deb.debian.org`, and `objects.githubusercontent.com` GitHub Release redirects).

Keep unpacked toolchains, caches, and browsers under `/tmp/*` (or an excluded `.arena/` / `.cache/` folder) so `/home/user` turn-end snapshots stay well below the ~128 MB / 10,000-file cap.

---

## 1. Rust 1.99.0 + `wasm32-unknown-unknown` (~18 s via `registry.npmjs.org`)

```bash
set -euo pipefail
PREFIX="/tmp/rust-1.99"
STAGE="/tmp/rust-stage"
rm -rf "$PREFIX" "$STAGE" && mkdir -p "$PREFIX" "$STAGE/extract"
cd "$STAGE"

npm pack \
  @toolchain-bin/rustc-1.99.0-x86_64-unknown-linux-gnu \
  @toolchain-bin/cargo-1.99.0-x86_64-unknown-linux-gnu \
  @toolchain-bin/rust-std-1.99.0-x86_64-unknown-linux-gnu \
  @toolchain-bin/rust-std-1.99.0-wasm32-unknown-unknown \
  @toolchain-bin/clippy-1.99.0-x86_64-unknown-linux-gnu \
  @toolchain-bin/rustfmt-1.99.0-x86_64-unknown-linux-gnu

for tgz in toolchain-bin-*.tgz; do
  rm -rf "$STAGE/extract/package"
  tar -xzf "$tgz" -C "$STAGE/extract"
  bash "$STAGE/extract/package/install.sh" --prefix="$PREFIX" --disable-ldconfig >/dev/null
done

# MANDATORY: npm tarballs strip +x on nested rust-lld, ld.lld, and wasm-ld linkers.
chmod +x \
  "$PREFIX"/bin/* \
  "$PREFIX"/libexec/* \
  "$PREFIX"/lib/rustlib/x86_64-unknown-linux-gnu/bin/* \
  "$PREFIX"/lib/rustlib/x86_64-unknown-linux-gnu/bin/gcc-ld/*

rm -rf "$STAGE"
export PATH="$PREFIX/bin:$PATH"
```

- **Dependencies when `index.crates.io` is blocked:** prefer zero-external-crate `std` first. When crates are needed, unpack `https://codeload.github.com/<org>/<repo>/tar.gz/<tag>` into `vendor/<crate>/`, write `{"files":{}}` to `vendor/<crate>/.cargo-checksum.json`, and configure `[source.crates-io] replace-with = "vendored-sources"` at the **workspace root** `.cargo/config.toml` (Cargo reads `.cargo/config.toml` from `$PWD`, not `--manifest-path`; `[patch.crates-io]` alone still fails fetching `index.crates.io/config.json`).
- **Pure-Rust Wasm (`wasm32-unknown-unknown`):** set `crate-type = ["cdylib", "rlib"]` for native `cargo test`, `[profile.release]` (`opt-level = "z"`, `lto = true`, `codegen-units = 1`, `panic = "abort"`, `strip = true` -> `~68 KB`), Rust 2024 `#[unsafe(no_mangle)]` + `thread_local! { RefCell<...> }`, and pass `--target-dir "$OUT_DIR/wasm-target"` when compiling Wasm from `build.rs`.

---

## 2. Go 1.27.3 + `GOOS=js GOARCH=wasm` (~4 s via `pypi.org`)

```bash
set -euo pipefail
GO_STAGE="/tmp/go-stage"
export GOROOT="/tmp/go-1.27"
rm -rf "$GO_STAGE" "$GOROOT" && mkdir -p "$GO_STAGE"

pip download --no-deps --only-binary=:all: --dest "$GO_STAGE" "go-bin==1.27.3" >/dev/null
unzip -q "$GO_STAGE"/go_bin-*.whl -d "$GO_STAGE/unpacked"
mv "$GO_STAGE/unpacked/go" "$GOROOT"
chmod -R +x "$GOROOT/bin" "$GOROOT/pkg/tool"
rm -rf "$GO_STAGE"

export PATH="$GOROOT/bin:$PATH"
export GOPROXY="direct" GOSUMDB="off" GOMODCACHE="/tmp/go-mod-cache" GOCACHE="/tmp/go-build-cache"
```

- **Vanity module paths (`golang.org/x/*`):** add `go mod edit -replace=golang.org/x/sync=github.com/golang/sync@v0.12.0` (and sibling `golang.org/x/*` repos) so Git clones directly from `github.com` without hitting blocked `https://golang.org/...?go-get=1`.
- **Go 1.24+ Wasm paths & rules:** copy `$(go env GOROOT)/lib/wasm/wasm_exec.js` (`misc/wasm/wasm_exec.js` no longer exists); end `cmd/wasm/main.go` with `select {}`; spawn `go func() { ... }()` inside `js.FuncOf` handlers before blocking I/O; use `syscall/js` `fetch` (~1.17 MB gzipped) over `net/http` in Wasm (~3.0 MB gzipped) when bundle size matters.

---

## 3. Node.js 22.22 + Native TypeScript (Zero Bundler / Zero Native Addons)

- Use flagless native `.ts` execution (`node src/server/main.ts`, `node --test test/*.test.ts`), `node:module.stripTypeScriptTypes(src, { mode: "strip" })` for browser ES2024 modules (`Content-Type: text/javascript; charset=utf-8`), and `node:sqlite` (`DatabaseSync`, compiled with `SQLITE_DQS=0` — single-quote string literals `'ok'` or use `?` parameters; pass `--disable-warning=ExperimentalWarning`).
- Avoid packages whose `postinstall` downloads binaries from blocked CDNs or GitHub Releases (`playwright`, `puppeteer`, `cypress`, `prebuild-install` addons). If using Vite, set `server: { host: "0.0.0.0", allowedHosts: [".e2b.app"], proxy: { "/api": "http://127.0.0.1:3001" } }`.

---

## 4. Live Preview & Offline Headless Chromium 150

1. Bind servers to `0.0.0.0`, serve `GET /favicon.ico -> 204` and `/app.wasm` as `application/wasm`, accept proxy `Host` headers (`*.e2b.app`), and call strictly relative `/api/*` URLs from browser/Wasm code.
2. Install `playwright-core` + `@toolchain-bin/aimeeting-sandbox-chromium` in `/tmp/browser-driver` and **always** export `AIMEETING_BROWSER_HOME="/tmp/aimeeting-browser"` (avoids unpacking `394 MiB` into `~/.aimeeting-browser` inside `/home/user`), launching with `executablePath: browserPkg.executablePath()`, `LD_LIBRARY_PATH: browserPkg.libraryPath()`, and `args: ["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"]`.
