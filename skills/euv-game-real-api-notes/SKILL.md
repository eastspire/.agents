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

## Router overlay stack — single-pop 铁律 (verified 0.18.17)

OVERLAY_STACK / MODAL_STACK 是 euv 的全局 overlay 栈,支持 modal / drawer / panel 嵌套,**系统 back 键与 UI dismiss 共享 popstate handler 这一个 pop 入口**。任何 dismiss 路径都只能 pop 一次 — UI 预先 pop + popstate handler 再 pop = 错关父级 overlay(经典症状:嵌套 modal 关第 3 层,结果第 2 层也跟着关)。

**症状**(实测 PR #69, euv example `page_modal` 的 Nested Modals 卡):

- 打开 Layer 1 → Open Layer 2 → Open Layer 3
- 点 Layer 3 的关闭按钮(`modal_dismiss_handler`)
- 预期:Layer 3 关闭
- 实际:Layer 3 和 Layer 2 同时关闭

**根因**:`Router::overlay_stack_close` (UI dismiss 入口) 之前在内部先 pop 一次 `OVERLAY_STACK`,再调 `Router::overlay_back(None)`,后者设 `BACK_PENDING=true` + 调 `history.back()`;popstate handler 看到 `BACK_PENDING=true`,**又 pop 一次** + invoke closer — 第二次 pop 错关到下一层 modal。

**修复**(`ui/src/component/router/hook/impl.rs`):

```rust
pub fn overlay_stack_close() {
    Self::overlay_back(None);   // 不要在这里手动 pop,完全交给 popstate handler
}
```

正确的 dismiss 协议:

| 触发方式 | 调用链 | pop 入口 |
|---------|--------|---------|
| UI 关闭按钮 | `dismiss_modal` → `modal_close_via_ui` (manual remove from MODAL_STACK by signal identity) → `overlay_stack_close` → `overlay_back` (set BACK_PENDING) → `history.back` | popstate handler, `BACK_PENDING=true` 路径 |
| 系统 back 键 | (无前置调用) popstate 直接触发 | popstate handler, BACK_PENDING=false 路径 |
| Drawer nav item | `close_drawer_and_navigate` → `overlay_back(target)` | popstate handler, `BACK_PENDING=true` 路径,后续 navigate |

关键 API:

- `Router::modal_push(visible, closer)`: push 到 MODAL_STACK + OVERLAY_STACK + `history.push_state()`
- `Router::modal_close_via_ui(visible)`: 按 signal identity 从 MODAL_STACK 移除 + 调 `overlay_stack_close`(identity-based removal 保证嵌套 modal 顺序正确)
- `Router::overlay_back(target)`: 设 `BACK_PENDING` + 可选 `NAVIGATE_AFTER_BACK` + `history.back()`
- `Router::overlay_stack_pop()`: 副作用按 `Rc::ptr_eq` 也清 MODAL_STACK(幂等,UI dismiss 已 manual remove 后 no-op)

**验证**:`use_overlay_history` 的 popstate handler 必须在以下三类输入下都表现正确:

1. UI dismiss n3 → BACK_PENDING=true → pop c3 → invoke closer3 → n3 false, n1/n2 保留
2. 系统 back 键 → BACK_PENDING=false → pop top → invoke 其 closer
3. 混用:UI 关一个 + back → 关下一个,**不重复关同一个**

任何新增 overlay dismiss helper 都必须遵守这条 single-pop 铁律 — **不能让 UI dismiss 路径 pop 一次后再让 popstate handler 再 pop 一次**。

## SPA server worktree trap (recurring — captured 2026-09-02)

`/tmp/spa_server.py` has `WWW_DIR` hardcoded to the live worktree at the time
of creation. When you switch worktrees (e.g. `git worktree add .../fullscreen-fix`
for a separate fix branch), the **old server keeps serving the OLD www
directory** while the new wasm lives at the new path. Result: headless tests
appear to "regress" because they're being served the pre-fix wasm.

Trap signals:
- `curl http://localhost:8080/pkg/euv_example_bg.wasm | wc -c` returns the
  WRONG size (e.g. pre-fix wasm is 1,365,272 bytes, post-fix is 1,929,257
  bytes — 564 KB diff is the giveaway)
- All test assertions fail even though `cargo build` succeeded locally
- The same SPA server pid you killed last session is somehow still running
  (different port? `ss -lntp` doesn't show Python but `ps -ef | grep spa`
  does)

Fix pattern: for each worktree you start, **copy `/tmp/spa_server.py` to a
fresh `/tmp/spa_server_<fix>.py` and edit `WWW_DIR` to the worktree path**.
Use a different port (`PORT = 8081` etc.) so you can run multiple concurrently
for comparison. Verify with `curl http://localhost:<port>/pkg/euv_example_bg.wasm | wc -c`
matching the on-disk `ls -l example/www/pkg/euv_example_bg.wasm` size
BEFORE running any browser test.

This trap caught PR #104 fix-verification (stale www served from earlier
session) and PR #106 fix-verification (same pattern). Burn it into muscle
memory: **before claiming a browser-verified fix, prove the served wasm is
the wasm you just built**.

## Splitting inline vs fullscreen rendering trees (verified 2026-09-02, PR #106)

If the same `<canvas>` element needs different parent wrappers in inline
mode vs fullscreen mode, **don't share the canvas between two parent
chains** — make `if/else` branches at the canvas level:

```rust
// WRONG: canvas always inside fullscreen wrapper + letterbox (PR #104)
// inline: c_game_canvas_wrapper > c_game_fullscreen_canvas_wrapper > letterbox > canvas
//   (inline gets squeezed by the letterbox + flex chain)
// fullscreen: c_game_container_fullscreen > c_game_fullscreen_canvas_wrapper > letterbox > canvas
//   (16:9 letterbox bars inside a viewport that isn't 16:9)

// RIGHT: split trees (PR #106)
div {
    class: if { canvas_2d_fullscreen.get() } {
        c_game_container_fullscreen()  // fixed 100vw×100vh
    } else {
        c_game_canvas_wrapper(&format!("{W} / {H}"))  // aspect-ratio: W/H
    }
    if { canvas_2d_fullscreen.get() } {
        div { class: c_game_fullscreen_canvas_wrapper()
            canvas { ... onclick: handler.clone() }
        }
    } else {
        canvas { ... onclick: handler.clone() }  // direct child
    }
    if { canvas_2d_fullscreen.get() } {
        div { class: c_game_fullscreen_toolbar() euv_button { ... } }
    }
}
```

**`onclick: handler.clone()`** is required in BOTH branches because each
branch moves the closure into a separate `VirtualNode`. The closure type is
`Option<Rc<dyn Fn(Event)>>` — `Rc::clone()` (cheap refcount bump, not full
closure clone). The PR #104 version didn't need `.clone()` because there was
only one canvas, but splitting forces both branches to take ownership.

**Loading overlay anchoring**: if you have a `c_game_loading_overlay` (WebGPU /
WebGL tabs) with `position: absolute; top: 0; left: 0; width: 100%; height: 100%`,
its containing block is the nearest positioned ancestor. In the inline path
the `c_game_canvas_wrapper` is `position: relative` → overlay anchored to
wrapper bounds. In the fullscreen path the `c_game_fullscreen_canvas_wrapper`
is flex:1 but NOT positioned → overlay would anchor to the nearest
positioned ancestor above (`c_game_container_fullscreen` = viewport),
covering the toolbar too. **Fix**: add `position: "relative"` to the fullscreen
canvas wrapper so overlay stays scoped to the canvas area.

**After-exit layout settling**: when exiting fullscreen, the canvas moves from
`c_game_fullscreen_canvas_wrapper` (flex:1 fills container) back to
`c_game_canvas_wrapper` (aspect-ratio lock). Layout doesn't fully re-flow until
the next resize tick. Tests that measure right after `await page.click('Exit')`
will see the canvas height stale (e.g. 820×410 instead of 820×547). **Fix in
tests**:

```python
await page.click('button:has-text("Exit")')
await page.wait_for_timeout(3000)              # close animation
await page.evaluate("window.dispatchEvent(new Event('resize'))")  # force reflow
await page.wait_for_timeout(1500)
```

## Tab select handler must reset tab-scoped signals (verified 2026-09-02, PR #104)

The pitfall table in euv-standards §12 already documents this for fullscreen
state, but the pattern generalizes: any signal registered in page-level
`HookContext` (via `App::use_signal` in a `use_*_state()` hook) that drives
per-tab UI state must be reset when the user switches tabs. Otherwise the
state survives the `match` arm DOM destruction and re-appears when the user
returns to the original tab.

```rust
fn game_2d_on_tab_select(
    tab: Signal<Game2DTab>,
    target: Game2DTab,
    fullscreen: UseGame2DFullscreen,
) -> impl Fn(Event) + 'static {
    move |_| {
        // Always reset per-tab transient state first
        fullscreen.get_canvas_2d().set(false);
        fullscreen.get_web_gl().set(false);
        fullscreen.get_web_gpu().set(false);
        // (any other per-tab signals: modal-open, form-state, pending-uploads)
        tab.set(target);
    }
}
```

Apply to every tab onclick handler, e.g.:

```rust
div {
    class: if { tab.get() == Game2DTab::Canvas2D } { c_tab_item_active() } else { c_tab_item_inactive() }
    onclick: game_2d_on_tab_select(tab, Game2DTab::Canvas2D, fullscreen)
    "2D"
}
```

(Not `App::use_effect` watching the tab signal — the effect fires once per
render and races with the user. Direct handler is deterministic.)

## Fixed-aspect canvas + viewport-fill container — browser auto-scaling is fine

For fullscreen on portrait phones (375×667) and other aspect-mismatched
viewports: **the browser's automatic non-uniform scaling of the canvas
backing bitmap is acceptable UX**,** if** the game's coordinate system stays
in fixed logical space (e.g. `GAME_2D_CANVAS_WIDTH × GAME_2D_CANVAS_HEIGHT =
600 × 400`). The CSS box becomes viewport-fill; the bitmap gets stretched to
match; balls/cubes draw in 600×400 logical coords. Verified PR #106:
- portrait 375×667 viewport → canvas 343×617 (fills viewport minus padding)
- ratio 0.5559 ≈ viewport ratio 0.5622 (NOT 16:9)

For deeper responsive scaling (recompute ball positions in viewport
coordinates, keep balls circular regardless of orientation), would need to
resize the backing store dynamically. PR #106 stopped at "fill viewport with
browser auto-scale" — if the user later wants balls to stay circular during
rotation, the next step is a `sync_to_current_canvas()` that reads
`canvas.getBoundingClientRect()` instead of the fixed game constants.

## Fullscreen canvas rotation — geometric width-utilization constraint (verified 2026-09-03, PRs #114, #118, #120, #122)

When a `<canvas>` element (with intrinsic `width="600" height="400"` =
3:2 backing buffer) is rotated via CSS `transform: rotate(90deg)` inside
a fullscreen flex container, the **visible visual bounding box width is
capped at the wrapper's height**, regardless of how wide the wrapper is.

The reasoning:
- Canvas's intrinsic `width`/`height` attributes set `aspect-ratio: auto
  600/400` (3:2), which **competes with** explicit CSS
  `width: 100%; height: 100%`. Browser resolves by honoring both: canvas
  CSS box = wrapper width × wrapper height = `1248 × 750` (landscape).
- `transform: rotate(90deg)` rotates the layout box visually. Visible
  bbox swaps W/H: `1248 × 750` → visual `750 × 1248` (portrait).
- The wrapper is typically `flex: 1` filling a `flex-direction: column`
  fullscreen container, so wrapper height ≈ 750 px (viewport minus
  toolbar / padding) regardless of viewport width.
- **Therefore visible width = 750 px regardless of whether viewport is
  1280, 1920, or 3840 px wide.** Width util = `750/1280 = 58.6%` on
  1280×800 viewport — capped by the wrapper height, NOT by viewport
  width.

This is a hard geometric constraint of CSS-only rotation. To break it:

| Approach | Width util | Side effects |
| --- | --- | --- |
| CSS `rotate(90deg)` (PR #114 → #118) | 58.6% (capped by wrapper H) | Visual overflow above/below viewport (clipped) |
| Drop rotation, `aspect-ratio: 3/2`, `height:100%; width:auto` (PR #120) | 87.9% on 1280×800 | No rotation; visible is landscape, matches inline |
| `aspect-ratio: 2/3` portrait CSS box + rotate | Same as PR #118 (58.6%) | Portrait CSS box, rotates to landscape visual |
| Canvas backing buffer rendered rotated (JS-side, e.g. `ctx.rotate(π/2)` then clear+redraw) | Fills viewport | Requires game-loop change; euv `euv-engine` doesn't expose `ctx.rotate`, would need raw `web_sys` `CanvasRenderingContext2d.rotate` |

User feedback drove three fullscreen iterations in one day:
- PR #114 (rotate 45°): user happy, requested more
- PR #118 (rotate 90°): user asked "等比宽度高度比例" (same aspect as
  inline) — interpreted as "drop rotation, use full width"
- PR #120 (drop rotation, aspect-ratio: 3/2): width util 87.9%
- User follow-up: "全屏需要保持画布比例，顺时针旋转90度" — interpreted
  as "rotation is required, restore it" (the two clauses were
  geometrically contradictory, the user's literal request won)
- PR #122: rotation restored

**Lesson:** when iterating on fullscreen canvas, **state the geometric
trade-off explicitly to the user before changing approach**. The
"preserve ratio + maximize width + rotate 90°" triplet is
mathematically impossible with CSS-only rotation.

Implementation pattern that survives the rotation toggle (so PR #120
and PR #122 share most code):

```rust
// view fn: per-tab fullscreen signal, conditional class on canvas
canvas {
    class: if { canvas_2d_fullscreen.get() } {
        c_game_2d_canvas_fullscreen()
    } else {
        c_game_2d_canvas()
    }
    onclick: on_canvas_click.clone()  // both branches need .clone()
    ontouchstart: on_canvas_touch.clone()
}
```

```css
/* c_game_2d_canvas_fullscreen */
width: 100%;
height: 100%;
cursor: pointer;
display: block;
background: var!(accent);
touch-action: none;
object-fit: contain;       /* /* preserves backing buffer 3:2 inside CSS box */
transform: rotate(90deg); /* PR #122 restored */
transform-origin: center;
```

**`object-fit: contain` on `<canvas is critical** — without it, the
backing bitmap (600×400) stretches to whatever shape the wrapper has,
turning balls into ovoids and cubes into rectangles. With `contain`,
the bitmap uniformly scales within the CSS box and the canvas's `var!(accent)`
black background shows through any letterbox bars inside the bitmap.

Visual verification (headless Chromium 1280×800 viewport) shows:
- transform = `matrix(0, 1, -1, 0, 0, 0)` = cos(90°)·identity = 90° CW
- bbox positioned at `(265, -249)` = canvas CSS box (1248×750) center
  (665, 375) minus rotated half-extents (375, 624)
- bbox extends `y: -249 to 999` → top 249px and bottom 199px clipped by
  viewport (800px)

## Fullscreen iteration cycle pattern (verified 2026-09-03, 4 PRs in one session)

User iterates tersely on UI tweaks ("顺时针旋转45度" → "再顺时针旋转45度"
→ "等比宽度高度比例" → "保持比例，顺时针旋转90度"). Each cycle:

1. **Patch CSS classes** in `example/src/style/class/fn.rs` (and
   sometimes `ui/src/style/class/fn.rs` for shared `c_game_*` classes).
2. `cargo build --target wasm32-unknown-unknown --release -p euv-example`
   + `wasm-bindgen target/wasm32-unknown-unknown/release/euv_example.wasm
   --out-dir example/www/pkg --target web --no-typescript`.
3. Visual verify via headless Chromium SPA (port 8080, `WWW_DIR` =
   live worktree — **see SPA worktree trap below**).
4. Create worktree at `upstream/master`, branch
   `fix/fullscreen-<short-desc>`. Copy changes. `euv fmt` (recurring
   whitespace reflow on `ui/src/style/class/fn.rs` dropdown menu CSS
   comment block, +4 spaces per run — cosmetic, expected). `cargo fmt
   --all`. `cargo check -p euv -p euv-core -p euv-engine -p euv-ui -p
   euv-example --target wasm32-unknown-unknown`. `cargo clippy ... -- -D
   warnings`.
5. Commit + push to fork + `gh pr create --repo euv-dev/euv --base master
   --head eastspire:fix/...`. Wait ~3-4 min for 5/5 critical CI. Merge.
6. New worktree at new `upstream/master`, branch `chore/bump-X.Y.Z`.
   Bump root `[package].version` only (CI `sync_workspace_version`
   propagates to sub-crates + path-deps — **禁止全仓 sed**, see
   euv-standards §17). `euv fmt` + `cargo fmt --all` + check + clippy.
   Commit + push + PR.
7. Wait ~3-4 min for 9/9 master CI. Verify crates.io + GitHub Release
   published.
8. `git stash && git reset --hard upstream/master && git stash drop` in
   main worktree. `git worktree remove ...` for both. `pkill -f
   'spa_server'`.

Total wall-clock: ~10-15 min per feature PR + bump, ~25-30 min total
per iteration cycle. Sustained this for 4 cycles in one session
(PRs #114/#115 → #116/#117 → #118/#119 → #120/#121 → #122/#123).

**User preference (verified 2026-09-03):** when the user gives terse
UI iteration instructions followed by "euv fmt之后升级小版本合并" or
"继续", they want autonomous execute-and-merge end-to-end with NO
mid-iteration confirmation requests. The only legit pause points are
- irreversible destructive actions on user-owned content (rm -rf, force
  push unmerged PR, etc.)
- genuinely ambiguous interpretation that materially changes the
  outcome (e.g. "should I keep rotation or drop it?" — that does NOT
  apply here because the literal request wins over meta-rationalizing
  about trade-offs).

For ambiguous geometric trade-offs: **pick the literal interpretation,
state it in the PR body, ship it**. The user will correct course if
wrong. Do NOT preemptively ask "should I optimize for X or Y?" — that
fragments the iteration cycle and burns time on a question they will
answer by their next turn anyway.

## euv workspace path-dep gotcha (verified 2026-09-02, recurring)

euv 根 `Cargo.toml` 用 `[patch.crates-io]` 把所有 euv-* 子 crate 用相对 path 引用(euv 是 monorepo,workspace member 之间 path-dep)。这是为了让 workspace 内部 cross-crate 改动立即生效,**但与 crates.io 上的同名 crate 共存时**有微妙:

- path-dep 永远走本地源码,不拉 crates.io。
- 但 path-dep 也要写 `version = "0.18.16"`(`[workspace.dependencies]` 内 inline),**这个 version 必须和根 `[package] version` 一致**,否则 `cargo check` 报 `failed to select a version for the requirement euv = "^0.18.15"`。
- minor bump(0.18.x → 0.19.x)会破坏 path-dep 区间;patch bump(0.18.15 → 0.18.16)不破。
- **CI 的 `sync_workspace_version` job** 在根 version 改后自动 sed 所有 workspace.dependencies 与子 crate 的 package.version,**本地复现 CI 的 sed 并随 PR 提交**就能保证 `cargo check` 在合并前就绿。

具体 sed 配方见 `euv-standards/references/consolidated-pr-workflow.md` / rust-wasm-gh-pages-deploy-pitfalls §sync_workspace_version。
