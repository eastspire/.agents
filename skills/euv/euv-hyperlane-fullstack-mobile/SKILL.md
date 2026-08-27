---
name: euv-hyperlane-fullstack-mobile
description: euv+hyperlane mobile wasm scaffold, GitHub Pages deploy
---

# euv + hyperlane fullstack mobile workflow

> Class-level playbook for building mobile-first WASM apps with [euv](https://github.com/euv-dev/euv) frontend and [hyperlane](https://github.com/eastspire/hyperlane) backend. Captures lessons learned building the visa-tracker end-to-end: 388 compile errors → 0 errors, working GitHub Pages deploy.

## When to use this skill

- Scaffolding a new euv WASM frontend (mobile UI + Signal state + class! CSS)
- Wiring hyperlane HTTP backend with SQLite (or any db) and serving static wasm assets
- Deploying the resulting `client/www/` to GitHub Pages via Actions workflow
- Hitting macro cascade errors and need a clean, working minimal pattern to copy from

## When NOT to use this skill

- Pure Rust CLI / server project (no wasm) → use `rust-standards`
- Just researching a single crate's API → use `rust-crate-use`
- Game-only euv usage → see `euv-game-real-api-notes` (user-owned, more specific)
- Tauri packaging an existing euv web app → use `euv-app`

## Workflow (5 phases)

### Phase 1: Scaffold workspace

`Cargo.toml` (workspace root):

```toml
[workspace]
members = ["server", "client"]
resolver = "2"

[workspace.dependencies]
euv = { path = "../../euv-dev/euv", version = "0.13.6" }
euv-core = { path = "../../euv-dev/euv/core", version = "0.13.6" }
euv-ui = { path = "../../euv-dev/euv/ui", version = "0.13.6" }
euv-engine = { path = "../../euv-dev/euv/engine", version = "0.13.6" }
hyperlane = "21.3.6"
hyperlane-macros = "0.1"
wasm-bindgen = "0.2"
wasm-bindgen-futures = "0.2"
serde = { version = "1", features = ["derive"] }
serde_json = "1"
js-sys = "0.3"
console_error_panic_hook = "0.1"
chrono = { version = "0.4", features = ["serde"] }
```

`client/Cargo.toml`:

```toml
[lib]
crate-type = ["cdylib", "rlib"]   # both so wasm-bindgen can produce cdylib AND cargo check works as rlib

[dependencies]
euv = { workspace = true }
euv-core = { workspace = true }
euv-ui = { workspace = true }
euv-engine = { workspace = true }
wasm-bindgen = { workspace = true }
wasm-bindgen-futures = { workspace = true }
serde = { workspace = true }
serde_json = { workspace = true }
console_error_panic_hook = { workspace = true }
web-sys = { version = "0.3", features = ["Window","Document","Element","HtmlElement","HtmlInputElement","HtmlSelectElement","HtmlTextAreaElement","Event","EventTarget","Request","RequestInit","Headers","Response","console"] }
js-sys = { workspace = true }
```

**Critical**: `crate-type = ["cdylib", "rlib"]` — without both, `cargo check` and `wasm-bindgen` cannot both succeed.

### Phase 2: Author the wasm frontend (the order that works)

Always write in this order to avoid macro cascade traps. Each step MUST compile before moving to the next:

1. **`models.rs`** — serde types deriving `PartialEq` (required for Signal<T>::set/get — see pitfall 1).
2. **`api.rs`** — thin `fetch` wrapper, no state, no closures inside euv macros.
3. **`state.rs`** — pure Signal-based state struct with `#[derive(Clone, Default)]`. No `Rc<RefCell<...>>`.
4. **`style.rs`** — `class! { pub c_xxx { prop: "value"; ... } }` using the **flat prop:value syntax** (NOT the wrapped `style { ... }` form — that errors with "this function takes 2 arguments").
5. **`lib.rs`** — `#[wasm_bindgen] pub fn main()` calling `App::mount("#app", move || app_root(state.clone()))`. Inside, write `fn app_root(state: AppState) -> VirtualNode` and `fn render_xxx(state: AppState) -> VirtualNode` as plain fns — **do NOT use `#[component]`** (the macro can't propagate `Rc<RefCell<T>>` props; we don't need props because we have Signal state). Reference modules with `crate::xxx::yyy`.
6. `cargo check --target wasm32-unknown-unknown` — MUST be 0 errors.

### Phase 3: Author the hyperlane backend

- One `Server::default()`, register routes one by one (`server.route::<MyRoute>(path).await`), tasks/panics/errors/middlewares similarly.
- Each handler implements `ServerHook::new(...)` + `handle -> Status`. Use `Context::get_request()` and `Context::get_mut_response()` for I/O.
- Static serving: a `serve_static` handler that reads `client/www/{path}` from disk and returns it as `application/wasm`, `application/json`, `text/html`, or `text/css` based on extension. Mount it at `/pkg/{file}` and `/` (catch-all for index.html).
- Run on `0.0.0.0:8080`, log to stdout with `tracing`/`RUST_LOG=info`.

### Phase 4: Build the wasm bundle

**Skip `wasm-pack build`** — its bundled `wasm-bindgen` is often too old and the install step can hang indefinitely.

```bash
# 1. Build the cdylib
cd client
cargo build --release --target wasm32-unknown-unknown
# produces target/wasm32-unknown-unknown/release/<crate_name>.wasm

# 2. Install matching wasm-bindgen-cli ONCE
cargo install -f wasm-bindgen-cli --version 0.2.127 --quiet

# 3. Generate JS bindings
wasm-bindgen ../target/wasm32-unknown-unknown/release/<crate_name>.wasm \
    --target web \
    --out-dir www/pkg \
    --out-name <crate_name_with_underscores> \
    --no-typescript
```

Output: `www/pkg/<crate>.js` + `www/pkg/<crate>_bg.wasm`.

### Phase 5: Deploy to GitHub Pages

`.github/workflows/deploy.yml`:

```yaml
name: Deploy to GitHub Pages
on:
  push: { branches: [master] }
  workflow_dispatch:
permissions: { contents: read, pages: write, id-token: write }
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: dtolnay/rust-toolchain@stable
        with: { targets: wasm32-unknown-unknown }
      - uses: Swatinem/rust-cache@v2
      - run: cd client && cargo build --release --target wasm32-unknown-unknown
      - run: cargo install wasm-bindgen-cli --version 0.2.127 --quiet
      - run: |
          wasm-bindgen ../target/wasm32-unknown-unknown/release/<crate>.wasm \
            --target web --out-dir www/pkg --out-name <crate> --no-typescript
      - uses: actions/configure-pages@v5
      - uses: actions/upload-pages-artifact@v3
        with: { path: client/www }
  deploy:
    needs: build
    runs-on: ubuntu-latest
    environment: { name: github-pages, url: ${{ steps.deployment.outputs.page_url } } }
    steps:
      - id: deployment
        uses: actions/deploy-pages@v4
```

User must enable: `Settings → Pages → Source: GitHub Actions`.

## Pitfalls (from real sessions)

### 1. `Signal<T>` requires `T: PartialEq + 'static`

`Signal::set` errors with `the method set exists for struct euv::Signal<Vec<X>>, but its trait bounds were not satisfied: can't compare X with X` if X doesn't derive PartialEq. **Always** `#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]` on every Signal-payload struct.

### 2. `class!` macro syntax — flat prop:value ONLY

```rust
// ✅ Works
class! { pub c_btn { padding: "10px"; color: "#fff"; } }

// ❌ Fails with "this function takes 2 arguments but 1 argument was supplied"
class! { pub c_btn { style { padding: "10px"; color: "#fff"; } } }
```

### 3. `Signal::create` not `Signal::new`

```rust
// ✅ Works
let s: Signal<bool> = Signal::create(false);

// ❌ Fails with "this function takes 2 arguments but 1 argument was supplied"
let s: Signal<bool> = Signal::new(false);
```

### 4. `html!` block has no `let` statements

```rust
// ✅ Works
let issue_str = v.issue_date.clone().unwrap_or_else(|| "—".to_string());
html! { div { { issue_str } } }

// ❌ Fails with "unexpected token" / "no rules expected this token"
html! {
    div {
        let issue_str = v.issue_date.clone().unwrap_or_else(|| "—".to_string());
        { issue_str }
    }
}
```

### 5. `html!` `for` body is a single identifier

```rust
// ✅ Works
let items: Vec<VirtualNode> = vec.into_iter().map(|x| view(x)).collect();
html! { for item in items { item } }

// ❌ Fails E0507 "cannot move out of value, a captured variable in an FnMut closure"
html! { for item in items { { item } } }
```

### 6. `html!` `if` accepts only Signal<T> not plain bool

```rust
// ✅ Works
html! { if { cond.get() } { ... } else { ... } }

// ❌ Fails "no method get found for type bool" — macro auto-calls .get()
html! { if { cond } { ... } else { ... } }

// Workaround for plain bool
html! { if { Signal::create(cond).get() } { ... } }
```

### 7. `html!` no `&&` in conditions

```rust
// ❌ Fails — both sides must be Signal
html! { if cond_a && cond_b { ... } }

// ✅ Workaround: nest
html! { if cond_a { if cond_b { ... } else {} } else {} }
```

### 8. `#[component]` props don't accept `Rc<RefCell<T>>`

The generated prop-extraction macro errors with `Rc<RefCell<AppStateInner>>: Into<euv::VirtualNode>` cascade. **Don't use `#[component]` for user views** — define plain `fn render_xxx(state: AppState) -> VirtualNode` and call them directly. Reserve `#[component]` for euv-ui library components.

### 9. Closures need cloned state per-handler

```rust
// ✅ Works — each handler clones state into its own Rc
let st_add = state.clone();
let on_add = move |_e: Event| { st_add.borrow_mut().field = ...; };
let st_del = state.clone();
let on_del = move |_e: Event| { st_del.borrow_mut().field = ...; };
html! { div {
    button { onclick: on_add "Add" }
    button { onclick: on_del "Del" }
}}

// ❌ Fails E0507 — same state captured by multiple FnMut closures
let on_add = move |_| state.borrow_mut().field = ...;
let on_del = move |_| state.borrow_mut().field = ...;
```

### 10. `euv fmt` is destructive — do NOT use mid-debugging

`euv fmt` will rewrite your html! and class! macros aggressively:

- Renames unknown `c_foo()` calls to the closest matching `class!` registry entry (often wrong — turning `c_btn_danger()` into `c_btn_danger_btn()`).
- Inserts extra `}` to close nested for loops — often MISMATCHED, requiring manual cleanup.
- Re-merges `let st = state.clone()` style closures, undoing snapshot patterns.
- Re-formats `for item in items { item }` back to `for item in items { { item } }`, reintroducing E0507.
- Strips hand-added `class!` entries.

**Workflow**:

1. Run `euv fmt` ONCE at the start of a session.
2. Run `cargo check` immediately after to verify no regression.
3. Hand-edit files from that point. Don't run fmt again until committing — and always re-check after.
4. If fmt breaks things mid-session, revert with `git checkout HEAD -- <file>` and re-apply via `patch` tool.

### 11. `wasm-pack build` can hang at "Installing wasm-bindgen"

Observed on this VM (GFW environment). Workaround: skip `wasm-pack` entirely, run `cargo build --target wasm32-unknown-unknown --release` + `wasm-bindgen` directly.

### 12. wasm-bindgen version must match

For euv 0.13.6: install `wasm-bindgen-cli --version 0.2.127`. Mismatch triggers a warning but still produces bindings.

### 13. GFW environment: SSH push to github.com is slow (20+ min)

Default timeouts kill long git index-pack. Workaround: `GIT_SSH_COMMAND="ssh -o StrictHostKeyChecking=no -o ServerAliveInterval=30"` and let the process run in the background with `notify_on_complete=true`. Or use GitHub API (Contents API + tree) to bypass git entirely (see `github-tree-api-multi-file-commit` skill).

### 14. `gh repo create` defaults to HTTPS, which is GFW-blocked

Add the SSH remote manually after `gh repo create`:
```bash
gh repo create <owner>/<repo> --public --source=. --remote=origin --push
# if HTTPS push fails (mirror.ghproxy.com dead), re-add SSH:
git remote remove origin
git remote add origin git@github.com:<owner>/<repo>.git
GIT_SSH_COMMAND="ssh -o StrictHostKeyChecking=no" git push -u origin master
```

### 15. wasm module loading needs `<script type="module">`

```html
<script type="module">
    import init from "./pkg/<crate>.js";
    init().catch(err => document.getElementById("app").innerHTML = `error: ${err}`);
</script>
```

Without `type="module"`, the script runs in classic mode and fails on `import`.

### 16. GitHub Pages base path matters for subdirs

If repo is `eastspire/visa-tracker`, GitHub Pages serves at `https://eastspire.github.io/visa-tracker/`. Relative paths like `./pkg/<crate>.js` work fine. Absolute paths like `/pkg/<crate>.js` will break.

### 17. wasm-bindgen 0.2.127 flag `--no-pack` doesn't exist

The flag was removed in newer wasm-bindgen. Just omit it.

## End-to-end validation

After build + serve locally:

```bash
cargo run --release &
sleep 2
for ep in health index "pkg/visa_tracker_client.js" "pkg/visa_tracker_client_bg.wasm" "api/countries" "api/visas" "api/stats"; do
    code=$(curl -s -o /dev/null -w "%{http_code}" "http://127.0.0.1:8080/$ep")
    echo "$ep: $code"
done
```

All should be 200. Then in a browser, load the page and check console for `[visa-tracker] wasm initialized` log.

## Reference materials

- `references/euv-macro-cheatsheet.md` — compact list of html! and class! patterns
- `references/hyperlane-handler-pattern.md` — minimal hyperlane server with one GET + one POST handler + static serving
- `templates/deploy.yml` — copy-paste GitHub Actions workflow for wasm + Pages deploy

## Key Decisions / Architectural notes

- **Use Signal<T> directly in app state, NOT Rc<RefCell<T>>** — Signal-based state is what euv's reactivity model is designed for, and it cleanly separates "the value" from "the owner of the value". Rc<RefCell<T>> adds manual borrow management on top.
- **Skip `#[component]` for user views** — reserve it for euv-ui library components. User views should be plain `fn render_xxx(state) -> VirtualNode` and called directly. This avoids the prop-extraction cascade entirely.
- **Skip `wasm-pack build`** — run `cargo build --target wasm32-unknown-unknown --release` + `wasm-bindgen` directly. wasm-pack's auto-install step is unreliable on this VM.
- **Run `euv fmt` once, then never again mid-debug** — fmt's rewrites are too aggressive to recover from iteratively.