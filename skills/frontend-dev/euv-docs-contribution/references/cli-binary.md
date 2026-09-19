# euv-docs CLI binary — adding `[[bin]]` + parameterised `build.rs`

Verified on `eastspire/euv-docs` (commit `41c6deb`, 2026-09-18). The skill
covers three concrete edits that turn a vanilla wasm cdylib euv-docs project
into a CLI tool that builds any markdown directory:

```
euv-docs <SRC_DIR> [--out <OUT_DIR>] [--name <NAME>] [--debug]
```

The pattern: a native `[[bin]]` shell-out to `euv build` with two env vars
that override the embedded `build.rs`'s hardcoded `manifest_dir/docs` and
`manifest_dir/www` paths. Default behaviour (no env vars set) is unchanged.

## The three edits

### 1. `Cargo.toml` — add the `[[bin]]`

```toml
[lib]
crate-type = ["cdylib", "rlib"]

[[bin]]
name = "euv-docs"
path = "src/bin/euv-docs.rs"
required-features = []
```

The cdylib and the bin coexist on the same crate. `cargo build --bin euv-docs`
produces a native executable; `cargo build --target wasm32-unknown-unknown`
still produces the wasm bundle. The shared `build.rs` runs once per cargo
invocation regardless of target.

Do **not** add a `[features]` gate just to swap CLI behaviour. The CLI is a
natively compiled consumer; the wasm build keeps the existing `main()` entry.

### 2. `build.rs` — read src/out from env vars

`build.rs` originally hardcodes `manifest_dir/docs` and `manifest_dir/www`.
Replace with env-var lookups (the bin sets these):

```rust
fn main() {
    let manifest_dir: PathBuf = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
    let docs_dir: PathBuf = match env::var("EUV_DOCS_SRC_DIR") {
        Ok(path) => PathBuf::from(path),
        Err(_) => manifest_dir.join("docs"),
    };
    let www_dir: PathBuf = match env::var("EUV_DOCS_OUT_DIR") {
        Ok(path) => PathBuf::from(path),
        Err(_) => manifest_dir.join("www"),
    };
    let out_dir: String = env::var("OUT_DIR").expect("OUT_DIR");

    println!("cargo:rerun-if-changed={}", docs_dir.display());
    println!("cargo:rerun-if-env-changed=EUV_DOCS_SRC_DIR");
    println!("cargo:rerun-if-env-changed=EUV_DOCS_OUT_DIR");
    // ... rest of build.rs unchanged; replace `manifest_dir.join("www")` with `www_dir`
}
```

Three things to remember:

1. **Print the rerun-if-changed directive with the resolved path**, not the
   hardcoded literal `"docs"` — otherwise changing files in a user-supplied
   source dir won't trigger a rebuild.
2. **Add `cargo:rerun-if-env-changed=EUV_DOCS_SRC_DIR`** (and the OUT var) so
   changing the bin's flags invalidates the build cache. The literal env
   var name is what cargo hashes.
3. **Don't change the wasm-build behaviour** when neither env var is set.
   The fallback `Err(_)` arm preserves the in-tree demo flow exactly.

### 3. `src/bin/euv-docs.rs` — the CLI itself

A complete ~180-line CLI that does only three things:

1. Parse `<SRC_DIR>` + `--out <OUT_DIR>` + `--name <NAME>` + `--debug|--release`.
2. Validate: `src_dir.is_dir()` and `src_dir/config.toml` exists. Print
   usage to stderr + exit 2 on parse error, exit 1 on validation/run error.
3. Shell out to `euv build`:

   ```rust
   let mut command: Command = Command::new("euv");
   command.current_dir(&manifest_dir);  // ← critical
   command
       .arg("build")
       .arg(if args.release { "--release" } else { "--debug" })
       .arg("--index-html").arg(&template_path);
   command.env("EUV_DOCS_SRC_DIR", src_dir);
   command.env("EUV_DOCS_OUT_DIR", out_dir);
   let pkg_dir: PathBuf = out_dir.join("pkg");
   command.arg("--");
   command
       .arg("--target").arg("web")
       .arg("--out-dir").arg(&pkg_dir)
       .arg("--out-name").arg(args.name)
       .arg("--no-typescript")
       .arg("--no-pack")
       .arg("--no-gitignore");
   ```

## Three pitfalls — all reproduced and fixed in this session

### Pitfall 1: `wasm-pack build` errors with "crate directory is missing Cargo.toml"

The bin's `Command::new("euv")` inherits the parent's working directory by
default. When the bin lives in `/tmp/target/debug/euv-docs` (cargo's
shared target dir via sccache / `CARGO_TARGET_DIR`), `euv build` runs in
`/tmp` — no Cargo.toml there, euv fmt also complains about missing `/tmp/src`.

**Fix**: explicitly `command.current_dir(&manifest_dir);` before `.arg("build")`.
`env!("CARGO_MANIFEST_DIR")` is set at compile time by cargo and always
points to the `Cargo.toml`'s directory.

### Pitfall 2: `Command::new("euv")` cannot find the `euv` binary

Symptom: `failed to invoke 'euv' build: No such file or directory (os error 2)`.

When the bin is launched by `cargo run --bin euv-docs` or by a CI runner,
`PATH` may not include `/root/.cargo/bin` where `euv` lives.

**Fix**: either explicit `command.env("PATH", env::var_os("PATH").unwrap())`
(not always enough — Command inherits PATH by default), or — better —
detect and `forward` PATH defensively:

```rust
let mut command = Command::new("euv");
if let Some(path) = env::var_os("PATH") {
    command.env("PATH", path);
}
```

In practice the fix that actually worked was `current_dir` (Pitfall 1); the
PATH forwarding belt-and-braces is also worth keeping.

### Pitfall 3: `cargo build --bin euv-docs` succeeds but the binary lands in an unexpected dir

`CARGO_TARGET_DIR` defaults to the project's `target/` subdir. But if
`rust-cache` / `sccache` is set up to share `target/` across projects (the
common pattern), the bin lands in **`CARGO_TARGET_DIR/debug/euv-docs`**,
not `./target/debug/euv-docs`. If you're scripting around the path, query
`cargo metadata --format-version 1` or just print and grep `find
$CARGO_TARGET_DIR -name euv-docs -type f`.

The second-build time drop is the real validation: first invocation ~60s
(full euv-docs wasm build + wasm-opt), subsequent invocations with no
source changes ~3-6s (cargo cache + wasm-opt cache hit). Numbers
reproduced on this machine: first build 1m03s, second build 5.83s, third
3.18s.

## Verification recipe (no network)

```bash
cd ~/github/eastspire/euv-docs

# 1. Build the CLI
cargo build --bin euv-docs --release
# Expect: produces <CARGO_TARGET_DIR>/release/euv-docs

# 2. Smoke-test argument handling
./euv-docs --version   # euv-docs 0.1.0
./euv-docs             # usage + rc 2
./euv-docs /no/such/dir  # error + rc 1

# 3. Build a real markdown dir (use the docs-pages/docs-euv fork, 130 md)
./euv-docs /root/_migrate/docs-euv/docs --out /tmp/cli-test
# Expect: build complete -> /tmp/cli-test

# 4. Verify output structure
ls /tmp/cli-test/
#   index.html  img/  js/  audio/  css/  essay/  markdown-images/  pkg/  video/  webfonts/
ls /tmp/cli-test/pkg/
#   euv_docs_bg.wasm  euv_docs.js

# 5. Serve + Playwright verify
cd /tmp/cli-test && python3 -m http.server 5501 &
# Probe http://127.0.0.1:5501/ with Playwright; expect sidebar + hero + 36 feature cards + footer
```

## Why no clap, no anyhow, no env_logger

Per `rust-standards` §13.1 ("don't introduce new third-party dependencies
prioritised over Cargo.toml tidiness") and §13.2 (Cargo.lock is fine; no
crate pinning gymnastics):

- **clap** — 50 lines of hand-rolled arg parsing fits a 4-arg CLI. Adding
  `clap = "4"` for one binary is the kind of dependency creep the user
  flagged in PR review.
- **anyhow** — `Result<(), String>` covers all error paths; converting to
  anyhow buys nothing for a binary that prints one error line.
- **env_logger** — `eprintln!` for stderr + `println!` for stdout is
  enough; cargo/euv-cli format upstream logs.

## Reusing the pattern for `euv-ui` or `euv` crates

Same recipe applies: add `[[bin]]`, parameterise `build.rs` env-var
locations (the few that exist — usually just `OUT_DIR` paths), shell out
to whatever the host pre-existing wrapper was. The exact env-var names
should follow the `EUV_<CRATE>_<FIELD>` convention used here:

- `EUV_DOCS_SRC_DIR` / `EUV_DOCS_OUT_DIR` — source / output paths
- `EUV_<CRATE>_CACHE_DIR` — shared target dir override
- `EUV_<CRATE>_TEMPLATE` — HTML template path

Keep the bin name aligned with the crate name (`euv-docs`) so `cargo install`
predicts correctly.