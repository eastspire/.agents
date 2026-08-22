---
name: euv-game-real-api-notes
description: Real euv + euv-engine API surface verified by reading source at /root/github/euv-dev/euv/{,engine,macros}. Load before scaffolding any euv WASM project — the documented examples drift from the actual API.
---

# euv / euv-engine Real API (verified / current)

> Source paths: `/root/github/euv-dev/euv/{engine,macros,core,ui}/src/`.
> Example at `/root/github/euv-dev/euv/example/src/`.

## Cargo.toml minimum (works without an org-relative path)

```toml
[lib]
crate-type = ["cdylib", "rlib"]

[dependencies]
euv = "*"
euv-engine = "0.1.0"
```

Add `wasm-pack` once for `euv build`:
```bash
cargo install wasm-pack
```

## Re-exports

`euv` re-exports `wasm_bindgen::*`, `web_sys`, `js_sys`, the html macro, etc.
`euv_engine` re-exports from `math::r#struct::*` (Color, Vector2D), `scene::r#struct::*` (DrawList), `renderer::r#struct::*` (CanvasRenderer), `config::r#struct::*` (RenderConfig), `engine::r#struct::*` (Engine). Impl blocks (private modules) provide methods on the re-exported types.

So:
```rust
use euv::*;
use euv_engine::*; // gives you Color, Vector2D, DrawList, CanvasRenderer, RenderConfig, Engine
```

## Engine bootstrap (verified from `euv-cli * euv build`)

`euv build` calls `wasm-pack build --dev --out-dir www/pkg --target web`. The crate is mounted via:

```rust
#[wasm_bindgen]
pub fn main() {
    console_error_panic_hook::set_once();
    App::mount("#app", app_root);
}
```

`App::mount(selector, fn() -> VirtualNode)` is the entry. `app_root` is a plain `fn -> VirtualNode`, not a hook.

## Engine API (real, not documented in `euv-engine/README`)

```rust
// Configs:
RenderConfig::canvas2d(selector: &str, w: f64, h: f64) -> RenderConfig
RenderConfig::webgpu (selector: &str, w: f64, h: f64) -> RenderConfig

// Renderer creation (Engine impl):
euv_engine::Engine::canvas_renderer(&RenderConfig) -> Option<CanvasRenderer>
euv_engine::Engine::webgl_renderer  (&RenderConfig) -> Option<CanvasRenderer>
// No Engine::webgpu_renderer yet — fall back to canvas_renderer for now and just register the webgpu config.

// Per-frame:
let renderer: CanvasRenderer = ...;
let list: DrawList = DrawList::create();
list.fill_rect(pos: Vector2D, w: f64, h: f64, color: Color);
list.fill_circle(pos: Vector2D, r: f64, color: Color);
list.stroke_circle(pos: Vector2D, r: f64, color: Color, line_w: f64);
list.fill_text(text: String, pos: Vector2D, color: Color, font: &str);
renderer.replay(&list);
```

## Math types (real names from `Getters` + `New` derives)

```rust
Color::new(r, g, b, a) -> Color            // r,g,b,a in 0.0..=1.0
Vector2D::new(x, y) -> Vector2D
Vector2D::zero() -> Vector2D              // // inferred from engine usage
v.get_x() -> f64
v.get_y() -> f64
v.get_x_mut(&mut self) -> &mut f64       // only if you took &mut
```

## html! macro rules (verified)

- The body is a fragment of nested elements; no `return` needed.
- `class: c_foo()` works ONLY if `class!` was called somewhere. The `c_foo()` function returns a `Css` type and the macro chains `.get_style()` on it.
- Reactive `if { cond } { ... } else { ... }` accepts a `Signal` directly — the macro auto-inserts `.get()`. Passing a bool or already-`.get()`'d value errors with "no method `get` found for type `bool`".
- For `eq`/`neq` on signals, do `if cond { ... }` or `if !cond { ... }` — `Signal::neq` is **not** a method (it errors with `no method named neq`).

## `App::use_window_event` gotcha

`App::use_window_event(name, Fn())` and `App::use_signal(init)` and
`App::use_cleanup(closure)` are **hooks** — they must be called from
within a function that is rendered as a `#[component]` page during the
virtual DOM render pass, OR synchronously from the top of the root
function passed to `App::mount`. Calling them inside a `spawn_local`
future, an event-listener `Closure`, or after an `await` silently
PANICS (the framework's thread-local "current hook context" is gone).
This produces a **completely white page** with no error visible —
`App::mount` never returns, so nothing else runs.

**Workaround for canvas games:** skip euv hooks entirely. Mount a
static `html!` tree once, then drive everything from raw `web_sys`:

- D-pad, buttons: `add_event_listener_with_callback` directly on the
  `Element` (`pointerdown` / `pointerup` / `touchstart`).
- Overlays (boot, game-over): toggle by `set_attribute("style",
  "display: none/flex")` on a `get_element_by_id`-queried element.
- Keyboard: single `document.add_event_listener_with_callback("keydown", ...)`.
- Game loop: `Closure::new(...).forget()` for the RAF callback, save
  it as `js_sys::Function` via `as_ref().unchecked_ref::<js_sys::Function>().clone()`
  to defeat the borrow of the `Closure` itself.

This is sufficient for any game whose UI is a single canvas with HTML
overlays — the VDOM doesn't need to re-render at all.

## RefCell reborrow pitfall

Inside a `FnMut` closure passed to RAF / event handler, `let w = rc.borrow(); foo(w); bar(w);` is fine because `borrow()` returns a fresh `Ref`. But `let mut w = rc.borrow_mut(); w.x; w.y = ...;` and then trying to do `rc.borrow()` again while `w` is live is the classic overlap panic. Snapshot flags into locals first, then take a fresh short-lived `borrow_mut()` per logical unit.

## Deploy to GitHub Pages from a `gh-pages` branch

`wasm-pack` writes `www/pkg/.gitignore = "*"`. To ship the bundle on `gh-pages`, you must:

```bash
cd /tmp/pq-pages && git init -b gh-pages
cp -r <repo>/www/* .
rm pkg/.gitignore
git add -f pkg/
git commit -m "deploy: ..."
git push -f <remote> gh-pages
```

Enabling Pages on the repo with `has_pages: true` at creation time works. After pushing `gh-pages`, hit `https://<owner>.github.io/<repo>/` (may need 10–20 s to provision).

## cargo check invocation

```bash
cargo check --target wasm32-unknown-unknown
```

This is the canonical validation step before `euv build`. The lint heuristic may report false-positive "`async move` only allowed in 2018 or later" on stable, but the real compiler is fine.
