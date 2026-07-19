---
name: euv
description: "A declarative, cross-platform UI framework for Rust with virtual DOM, reactive signals, and HTML macros for WebAssembly. Use when building browser-based UIs in pure Rust, writing web frontends that compile to WebAssembly, or working with the `html!` / `class!` / `#[component]` / `Signal<T>` APIs. Triggers: euv, html! macro, Signal<T>, App::mount, euv-ui, euv_engine, euv_component, virtual DOM, reactive signal, WebAssembly UI."
license: MIT
---

# euv

- GitHub: <https://github.com/euv-dev/euv.git>
- crates.io: <https://crates.io/crates/euv>
- docs.rs: <https://docs.rs/euv>

## Overview

euv is a workspace of six crates under one umbrella:

| Crate | Path | Purpose |
|---|---|---|
| `euv` | `.` | Public facade. Re-exports `euv-core` + `euv-macros` and the wasm-bindgen/js-sys/web-sys bindings. |
| `euv-core` | `core/` | `App` / `Signal<T>` / `HookContext` / `VirtualNode` / `AttributeValue` / `Css` runtime. |
| `euv-macros` | `macros/` | Proc-macros: `html!` / `class!` / `#[component]` / `watch!` / `computed!` / `vars!` / `var!`. |
| `euv-ui` | `ui/` | Pre-built UI components (`euv_button`, `euv_card`, `euv_header`, `euv_nav_item`, `euv_modal`, …) + global stylesheet + helpers (`use_browser_state`, `use_camera_state`, `local_storage_*`, `use_resize`, `use_theme_state`, …). |
| `euv-engine` | `engine/` | 2D/3D game engine (Canvas + WebGPU renderers, ECS, scene graph, physics, input, sprites, audio, asset cache, scheduler). Zero-size `Engine` façade. |
| `euv-cli` | `cli/` | CLI tool that wraps `wasm-pack`. |
| `euv-example` | `example/` | Live demo of every feature as `example/src/page/<name>/`. |

Top-level entry point at `src/lib.rs`:

```rust
pub use {euv_core::*, euv_macros::*};
pub use {console_error_panic_hook, js_sys, wasm_bindgen, wasm_bindgen_futures, web_sys};
```

## 项目元信息

- crate 名: `euv` (workspace root)
- Rust edition: `2024`
- License: `MIT`
- 类型: `[workspace]` with 6 members: `cli`, `core`, `engine`, `example`, `macros`, `ui`
- 关键字: `cross-platform` (root); members add: `http`, `request`, `response`, `tcp`, `cross-platform`, `web-programming`, `network-programming`

## Installation

```shell
cargo add euv
cargo add euv-ui euv-engine
```

In `Cargo.toml` the workspace declaration is:

```toml
[dependencies]
euv = { path = "euv" }
euv-ui = { path = "euv/ui" }
euv-engine = { path = "euv/engine" }
```

`euv` is a `cdylib`/`rlib` only (`crate-type = ["rlib"]`) — there is no `main.rs`; you `#[wasm_bindgen] pub fn main()` yourself.

## Quick start

Minimal counter (matches `example/src/page/counter/view/fn.rs`):

```rust
use euv::*;
use euv_ui::*;

#[wasm_bindgen]
pub fn main() {
    console_error_panic_hook::set_once();
    inject_app_global_css();
    App::mount("#app", app);
}

fn app() -> VirtualNode {
    let count: Signal<i32> = App::use_signal(|| 0);
    html! {
        div {
            class: c_page_container()
            euv_header { icon: "🔢" title: "Counter" }
            euv_card {
                title: "Counter"
                p {
                    "The current count is "
                    span { class: c_counter_value()  count }
                    "."
                }
                div {
                    class: c_button_controls()
                    euv_button { variant: EuvButtonVariant::Primary label: "Add"    onclick: on_add(count) }
                    euv_button { variant: EuvButtonVariant::Primary label: "Reset"  onclick: on_reset(count) }
                }
            }
        }
    }
}

fn on_add(count: Signal<i32>) -> Option<Rc<dyn Fn(Event)>> {
    Some(Rc::new(move |_| count.set(count.get() + 1)))
}
fn on_reset(count: Signal<i32>) -> Option<Rc<dyn Fn(Event)>> {
    Some(Rc::new(move |_| count.set(0)))
}
```

Build to a wasm bundle:

```shell
euv build              # wraps wasm-pack build --target web --dev
# or directly:
wasm-pack build --target web --dev
```

## Core API (`euv-core`)

### `App`

Zero-size façade struct (`core/src/app/struct.rs`). All App entry points live in `core/src/app/impl.rs`:

```rust
impl App {
    pub fn mount<S, F>(selector: S, render_fn: F)
    pub fn use_signal<T, F: FnOnce() -> T>(init: F) -> Signal<T>
    pub fn use_cleanup<F: FnOnce()>(cleanup: F)
    pub fn use_interval<F>(millis: i32, callback: F) -> IntervalHandle
    pub fn use_window_event<E, F>(event_name: E, callback: F)
    pub fn batch<F, R>(callback: F) -> R
    pub fn schedule_update(dependents: &[usize])
}
```

`App::mount("#app", app)` calls `app()` to render the root, then re-runs it whenever any `Signal<T>` read during that render fires `.set()`.

### `Signal<T>` — reactive primitive

`core/src/reactive/signal/struct.rs` + `impl.rs`:

```rust
impl<T> Signal<T> {
    pub fn create(value: T) -> Self
    pub const fn none() -> Self
    pub fn get(&self) -> T
    pub fn set(&self, value: T)
    pub fn subscribe<F>(&self, callback: F)
}
impl<T> Signal<Signal<T>> {
    pub fn get(&self) -> Signal<T>
    pub fn set(&self, signal: Signal<T>)
}
```

Rules:
- Read a signal inside an `html!` template body to subscribe that DOM node.
- `signal.get()` returns `T` by value — for non-`Copy` types, clone before capture.
- `signal.set(new_value)` schedules a re-render of every subscriber.
- Inside `html!` braces `{ expr }`, a **single-segment identifier path** is auto-rewritten as `expr.get()`. `state.field`, `signal.iter()`, `signal == X` are NOT auto-unwrapped — call `.get()` explicitly. Source: `macros/src/html/fn.rs::should_auto_get`.

### Virtual DOM (`VirtualNode`)

`core/src/vdom/node/enum.rs`:

```rust
pub enum VirtualNode<T = ()> {
    Element { tag: Tag, attrs: Vec<AttributeEntry>, children: Vec<VirtualNode> },
    Text(String),
    Fragment(Vec<VirtualNode>),
    Empty,
    Component { name: String, props: T, children: Vec<VirtualNode> },
    Dynamic(DynamicNode),
}
pub enum Tag { Div, Span, P, A, Button, Input, Custom(&'static str), … }
```

### CSS class helpers

`ui/src/style/class/fn.rs` exposes class helpers like `c_page_container()`, `c_counter_value()`, `c_button_controls()` etc. Call them inside `class: c_xxx()` attributes. To register your own styles use `core::inject_css(text)` (`core/src/vdom/attribute/impl.rs`) or `ui::inject_app_global_css()`.

## `html!` macro

From `macros/src/lib.rs`. Supported syntax:

```rust
html! {
    div {
        class: c_xxx()
        id: "literal"
        key: index.to_string()
        attr: value
        on<event>: handler

        "raw text"
        { expr }                      // dynamic text — single ident auto-.get()s
        if { cond } { ... }           // reactive if (brace form)
        if cond { ... }               // inline if (non-reactive)
        if { a } else if { b } { ... }
        match { value } {             // reactive match
            Variant => html!{ ... }
        }
        for x in { list.get().iter() } { ... }
        for (i, x) in { list.get().iter().enumerate() } { ... }
        EuvComponent { prop: value }  // built-in or user #[component]
    }
}
```

Critical restrictions (encoded in `html/fn.rs` and `euv-html-macro-traps` skill):
- `if {} else {}` (block-level `else` after `if {}`) is NOT supported. Use `if {} {} else if {} {} else {} {}` or two stacked `if {}` blocks.
- Closures captured inside `for` bodies cannot outlive the closure, so complex per-row event handlers (edit/delete/pagination) need a refactor pattern (see `euv-html-macro-traps`).
- Non-`Copy` values captured by the render closure need `.clone()` because the html! body is a `FnMut`.
- `key:` attribute on each `for`-iteration child is recommended for stable diffing.

## `class!` macro

`macros/src/lib.rs::class`:

```rust
class! {
    pub struct c_my_button {
        display: flex,
        padding: 12px 16px,
        background: #28a745,
        color: #fff,
        border-radius: 4px,
    }
    pub extends c_my_button, c_my_disabled {
        opacity: 0.5,
        cursor: not-allowed,
    }
}
```

Generated: a `c_my_button()` function returning a `Css` value (`core/src/vdom/attribute/struct.rs`). The `extends` semantics is string concatenation (`parent.get_style().to_string() + STR_SPACE + self.props` in `macros/src/class/impl.rs:284`) — same property names resolve via CSS cascade (later wins).

## Other macros (`euv-macros`)

All proc-macros from `macros/src/lib.rs`:

| Macro | Syntax | Behavior |
|---|---|---|
| `#[component]` | on `fn name(node: VirtualNode<Props>) -> VirtualNode` | Generates props struct + render dispatch |
| `html! { ... }` | inline template | VirtualNode DSL |
| `class! { ... }` | inline CSS block | Generates `c_*()` helpers |
| `#[vars!]` / `#[var!]` | on `use X;` or let-binding | Thread-local variable binding for the render scope |
| `#[watch!]` | statement form: `watch!(s1, s2, |s1v, s2v| { ... })` | Reactive side-effect when any signal changes |
| `#[computed!]` | on `fn name(...) -> T` | Cached derived signal |

`watch!` real example from `example/src/page/binding/hook/fn.rs`:

```rust
watch!(celsius, |celsius_value: f64| {
    let new_fahrenheit: f64 = celsius_value * 9.0 / 5.0 + 32.0;
    fahrenheit.set((new_fahrenheit * 100.0).round() / 100.0);
});
watch!(
    red, green, blue,
    |red_value: i32, green_value: i32, blue_value: i32| {
        hex_color.set(format!("#{:02x}{:02x}{:02x}", red_value, green_value, blue_value));
    }
);
```

## `euv-ui` components (`ui/src/component/<name>/view/fn.rs`)

Each component takes `VirtualNode<EuvXxxProps>` and returns `VirtualNode`. Common props:

| Component | Props struct | Required fields | Notable enum |
|---|---|---|---|
| `euv_button` | `EuvButtonProps` | `label`, `variant` | `EuvButtonVariant::{Primary,Secondary,Success,Danger,Warning,Info}` |
| `euv_card` | `EuvCardProps` | `title` | — |
| `euv_header` | `EuvHeaderProps` | `icon`, `title`, `subtitle?` | — |
| `euv_input` | `EuvInputProps` | `value: Signal<String>` | — |
| `euv_checkbox` | `EuvCheckboxProps` | `checked: Signal<bool>` | — |
| `euv_field` | `EuvFieldProps` | `label`, `value: Signal<String>` | — |
| `euv_modal` | `EuvModalProps` | `visible: Signal<bool>`, `closer` | — |
| `euv_nav_item` / `euv_mobile_nav_item` | `EuvNavItemProps` | `label`, `route`, `on_click` | — |
| `euv_nav_items` | `EuvNavItemsProps` | `items: Vec<EuvNavItemConfig>` | — |
| `euv_tag` | `EuvTagProps` | `label` | `EuvTagVariant`, `EuvTagColor` |
| `euv_badge` | `EuvBadgeProps` | `label` | — |
| `euv_alert` | `EuvAlertProps` | `message` | `AlertVariant` |
| `euv_loading` | `EuvLoadingProps` | — | — |
| `euv_logo` | `EuvLogoProps` | — | `LogoButtonVariant` |
| `euv_info` | `EuvInfoProps` | — | — |
| `euv_virtual_list` | `EuvVirtualListProps` | `config: EuvVirtualListConfig` | — |
| `euv_routes` / `euv_page_router` | `EuvRoutesProps` | `routes: Vec<EuvRouteConfig>` | — |
| `euv_vconsole_panel/fab/drawer` | `EuvVconsole*Props` | — | `LogLevel`, `LogFilter` |

Router API (`ui/src/component/router/view/impl.rs`):

```rust
pub fn new<F>(path: &'static str, component: F) -> Self   // EuvRouteConfig
pub fn current_route() -> String
pub fn navigate<R: AsRef<str>>(route: R)
pub fn link_handler<R: AsRef<str>>(route: R) -> NativeEventHandler
pub fn is_mobile() -> bool
```

`euv-ui` hooks (`ui/src/component/<name>/hook/impl.rs`):

```rust
use_browser_state() -> UseEuvBrowser
use_camera_state() -> UseEuvCamera
use_resize() -> Signal<bool>
use_drawer_toggle(drawer_open: Signal<bool>) -> Option<Rc<dyn Fn(Event)>>
use_safe_area_fix()
apply_cached_insets()
use_theme_state(mobile_signal: Signal<bool>) -> ThemeState
use_system_theme_change(theme_signal: Signal<String>)
detect_system_theme() -> String
toggle(theme_signal: Signal<String>) -> Option<Rc<dyn Fn(Event)>>
local_storage_get<K: AsRef<str>>(key: K) -> Option<String>
local_storage_set<K, V>(key: K, value: V)
use_scroll_state() -> UseVirtualList
use_scroll_to_top(route_signal: Signal<String>)
use_hash_change(route_signal: Signal<String>)
register_popstate_guard(guard: Rc<dyn Fn() -> bool>) -> usize
overlay_push_state()
overlay_back(navigate_target: Option<String>)
modal_push(visible: Signal<bool>, closer: Rc<dyn Fn()>)
modal_close_via_ui(visible: Signal<bool>)
open_system_browser<U: AsRef<str>>(url: U)
external_link_handler<U: AsRef<str>>(url: U) -> NativeEventHandler
use_toggle(signal: Signal<bool>) -> Option<Rc<dyn Fn(Event)>>
on_input_value(signal: Signal<String>) -> Option<Rc<dyn Fn(Event)>>
on_change_value(signal: Signal<String>) -> Option<Rc<dyn Fn(Event)>>
on_change_checked(signal: Signal<bool>) -> Option<Rc<dyn Fn(Event)>>
on_focus_scroll_into_view() -> Option<Rc<dyn Fn(Event)>>
on_blur_restore_height() -> Option<Rc<dyn Fn(Event)>>
```

## `euv-engine` (optional)

Zero-size `Engine` façade (`engine/src/engine/struct.rs`) + `EngineHandle`:

```rust
impl Engine {
    pub fn default_config() -> EngineConfig
    pub async fn run(config: EngineConfig, handler: TickHandlerRc) -> EngineHandle
    pub fn new_handle(config: EngineConfig) -> EngineHandle
}
pub fn canvas_renderer(config: &RenderConfig) -> Option<CanvasRenderer>
pub async fn webgpu_renderer(config: &RenderConfig) -> Result<WebGpuRenderer, WebGpuInitError>
```

Config builders (`engine/src/config/impl.rs`):

```rust
EngineConfig::create(render_config)
    .with_scheduler(scheduler_config);

RenderConfig::canvas2d("#canvas", 1280.0, 720.0);
RenderConfig::webgpu("#canvas", 1280.0, 720.0);
```

Namespaces (`engine/src/<area>/<file>.rs`):
- `math` — `Vector2D/3D`, `Quaternion`, `Matrix4x4`, `Rect`, `Circle`, `Color`, `AABB3D`, `Sphere`, `Plane`, `Ray3D`, `Transform2D/3D`, constants (`PI`, `TWO_PI`, `DEG_TO_RAD`, `EPSILON`), free fns (`clamp`, `lerp`, `distance`, `smoothstep`, `approach`, `sign`, `wrap`, `lerp_angle`, `from_angle`)
- `entity` — `Entity`, `EventBus`, `Component` trait, types `ComponentRc` / `EntityRc` / `EventHandler`
- `scene` — `SceneManager`, `Scene` trait, `SceneRc`, transitions (`request_transition`, `process_pending_transition`)
- `input` — `Input`, `InputState`, `MouseButton`, `InputAction`, touch/key state
- `physics` — `RigidBody2D/3D`, `PhysicsWorld2D/3D`, `BodyType`, `BodyCollider` / `BodyCollider3D`
- `collider` — `Collider` trait, `Collider3D` trait, `AabbCollider`, `CircleCollider`, `AabbCollider3D`, `SphereCollider3D`
- `renderer` — `CanvasRenderer`, `WebGpuRenderer`, `Camera2D/3D`, `SsaaCanvas`, `LinearGradient`, `RadialGradient`, `ShadowConfig`, `RenderLayer`, `BlendMode`, `RenderQuality`, `WebGpuInitError`
- `sprite` — `SpriteSheet`, `SpriteFrame`, `SpriteAnimation`, `Animator`, `AnimationMode`, `AnimationState`
- `asset` — `AssetCache`, `AssetLoader`, `AssetType`, `AssetState`, `AssetEntry`
- `audio` — `GameAudioContext`, `AudioClip`, `AudioPlayState`
- `scheduler` — `Scheduler`, `SchedulerConfig`, `SchedulerHandle`, `TickHandler` trait, `TickHandlerRc`
- `spatial` — `SpatialHashGrid2D/3D`

## Common pitfalls

1. **`signal.get()` in `html!` body inside `{}`** — single-segment ident auto-unwraps, multi-segment does not. `state.value` inside `{}` stays a `Signal<T>`; use `state.value.get()` explicitly.
2. **`if { cond } { ... } else { ... }`** — block-level `else` is rejected. Stack two `if {}` blocks or use `match`.
3. **Closures over for-loop items** — complex CRUD with per-row click handlers inside `for` loops runs into `FnMut`-double-borrow issues. Restructure into a parent `Signal<Vec<T>>` and a single child component.
4. **`App::use_signal`** — must be called inside the render fn body, NOT stored as `let x = Signal::new(v)` outside a render. `Signal::new` is a `SignalCell` (single-arg internal), not the public `Signal<T>`.
5. **Non-Copy values in `html!`** — render body is `FnMut`. `let count = App::use_signal(|| 0)` works because `i32` is `Copy`. For `String` etc., use signals only and clone on capture.
6. **`#[component]` body must destructure props via `node.try_get_props().unwrap_or_default()`** — the macro generates the wrapper but the inner fn receives `VirtualNode<Props>` not `Props`.
7. **`inject_app_global_css()` must be called before `App::mount`** — otherwise `euv_button` etc. render unstyled.
8. **`console_error_panic_hook::set_once()` is required** in `main()` or Rust panics in the browser are silent.
9. **`extends` in `class!` is concat, not override** — same-named property uses CSS cascade (later wins). Don't try to "remove" parent styles by re-declaring them.
10. **`c_euv_button_*` classes force `flex: 1 1 120px`** — any `display:flex` parent will stretch them to ≥120px. Wrap in a non-flex container or add `flex: none` override.

## Verification checklist

- [ ] `cargo check -p euv-ui -p euv-example` exits 0
- [ ] `cargo clippy --all-targets -p euv-core -p euv-macros -p euv-ui` 0 warnings
- [ ] `wasm-pack build --target web --dev` produces `pkg/euv_example_bg.wasm`
- [ ] Browser console shows zero errors after `App::mount` (look for "App::mount called twice" or render-loop warnings)
- [ ] Clicking a button updates only its signal-bound text node (DOM diff sanity)

## Source-of-truth files

- `src/lib.rs` — re-export facade
- `core/src/lib.rs` — module graph
- `core/src/app/{struct,impl}.rs` — `App`
- `core/src/reactive/signal/{struct,impl}.rs` — `Signal<T>`
- `core/src/vdom/node/enum.rs` — `VirtualNode`, `Tag`
- `core/src/vdom/attribute/{struct,impl}.rs` — `Css`, `AttributeValue`, `merge_class`, `inject_css`
- `macros/src/lib.rs` — proc-macro entry points
- `macros/src/html/fn.rs` — `html!` parser
- `macros/src/class/impl.rs` — `class!` implementation (`extends` concat semantics at line 284)
- `example/src/lib.rs` — full demo `main()` (40 lines)
- `example/src/page/counter/view/fn.rs` — minimal html!/Signal/Component example
- `example/src/page/binding/hook/fn.rs` — `watch!` examples
- `ui/src/component/<name>/view/fn.rs` — every pre-built component's signature
- `ui/src/style/class/fn.rs` — global class helpers (`c_page_container`, `c_button_controls`, …)

## Related skills

- `euv-standards` — html! macro syntax + closures + `#[component]` rules
- `euv-ui-standards` — full class catalogue + `euv-ui` design system
- `euv-html-macro-traps` — 9 specific pitfalls (auto-get, else block, FnMut, button width, …)
- `euv-engine-design` — `Engine` zero-sized façade contract
- `euv-hook-context-collision` — `HookContext::current()` global thread_local pitfalls
- `euv-app` — example app entry