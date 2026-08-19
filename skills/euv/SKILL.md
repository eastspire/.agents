---
name: euv
description: '**入口 skill — 使用 euv 框架必须加载**。任何涉及 euv 框架的任务(写 Rust web UI / WASM 项目、用 html! / class! / vars! / var! / watch! / computed! 宏、定义 #[component]、用 Signal<T> / App::mount / euv-ui / euv-engine、编译 web 前端到 WASM、写 game 用 euv-engine)→ **先 `skill_view("euv-standards")` 看完整 API/坑表 + `skill_view("euv-ui-standards")` 看 304 个 class!/design tokens**(若涉及 UI/页面/组件设计,后者强制加载)。euv 是 declarative cross-platform UI 框架,版本 0.13.3,edition 2024,monorepo 6 个工作区(crate `core` + `engine` + `macros` + `ui` + `cli` + `example`),根 crate 只是个 2 行 `pub use` 壳。关键 API:App::mount + Signal<T>::get/.set + HookContext + VirtualNode + #[component] + use_signal + auto-get 单段标识符自动 .get() 语法糖 + class! extends 拼接。关键触发词:euv, html! macro, class! macro, vars!, var!, watch!, computed!, #[component], Signal<T>, App::mount, euv-ui, euv-engine, euv_component_registry_cache, virtual DOM, reactive signal, WebAssembly UI, WebGPU game engine, wasm-pack, euv-cli, auto_value, euv-macros, use_signal, HookContext, VirtualNode, mount_to_body, request_animation_frame。**当且仅当任务完全不使用 euv**才不加载 euv-standards。'
license: MIT
---
# euv

- GitHub: <https://github.com/euv-dev/euv.git>
- crates.io: <https://crates.io/crates/euv>
- docs.rs: <https://docs.rs/euv>

## Documentation sources (docs-pages)

The full Chinese reference for euv lives in the [docs-pages](https://github.com/docs-pages/docs) repo (private). **This skill is the API/pitfall cheatsheet; docs-pages is the source of truth for tutorials, full macro specs, and feature guides.**

Selected pages from docs-pages are vendored flat under `references/` (no symlinks — plain copies of the specific files this skill needs). To find a topic:

- **Macros** — `references/html.md`, `class.md`, `component.md`, `watch.md`, `computed.md`, `var.md`, `css-vars.md` (full syntax, props, all examples)
- **Feature guides** — `references/reactive.md`, `vdom.md`, `event.md`, `engine.md` (2D/3D engine API), `lifecycle.md`, `component.md`, `mount.md`, `binding.md`, `list.md`, `conditional.md`, `async.md`, `form.md`, `keep-alive.md`, `canvas.md`, `websocket.md`, `sse.md`, `observer.md`, `platform.md`, `animation.md`, `timer.md`, `select.md`, `file.md`, `renderer.md`

To refresh `references/` after docs-pages updates, run the sync script from the repo root:

```shell
bash scripts/sync-references.sh                       # full sync (clones docs-pages)
bash scripts/sync-references.sh --source-dir <path>   # reuse an existing clone
bash scripts/verify-references.sh                     # show what changed vs HEAD
```

The mapping of `references/<file>.md` → `docs-pages/src/...` lives in `scripts/sync-references.mapping`. To add a new file, append a line; to pin a customized version, add `# manual override:` to its line and the script will leave that dest alone. See `scripts/README.md` for the full workflow.

---

## Index

| I want to... | Jump to |
| --- | --- |
| Find docs-pages source for tutorials and full macro specs | [Documentation sources (docs-pages)](#documentation-sources-docs-pages) |
| Get a 1-paragraph summary of the 6-crate monorepo | [Overview](#overview) |
| See crate name / edition / license | [Project Metadata](#project-metadata) |
| Add `euv` to `Cargo.toml` | [Installation](#installation) |
| Build / run the dev server with `euv-cli` | [`euv-cli`](#euv-cli) |
| See the 5-line minimum call to mount an app | [Quick start](#quick-start) |
| Browse the full core API (`App`, `Signal<T>`, `HookContext`, `VirtualNode`, `AttributeValue`, `Css`) | [Core API (`euv-core`)](#core-api-euv-core) |
| Write JSX-like HTML in Rust | [`html!` macro](#html-macro) |
| Build dynamic class strings | [`class!` macro](#class-macro) |
| Use `#[component]`, `watch!`, `computed!`, `vars!`, `var!` | [Other macros (`euv-macros`)](#other-macros-euv-macros) |
| Construct typed event handlers | [Event factory](#event-factory) |
| Use a pre-built component (`euv_button`, `euv_card`, …) | [`euv-ui` components](#euv-ui-components-uisrccomponentnameviewfnrs) |
| Render 2D / 3D games with `euv-engine` | [`euv-engine` (optional)](#euv-engine-optional) |
| Avoid the common gotchas | [Common pitfalls](#common-pitfalls) |
| Self-verify before committing | [Verification checklist](#verification-checklist) |
| Find the canonical source file for a symbol | [Source-of-truth files](#source-of-truth-files) |
| Find related skills | [Related skills](#related-skills) |

---

## Overview

euv is a workspace of six member crates under one umbrella. The root package is version `0.13.3`, edition 2024, and is `rlib`-only; `euv-macros` is the separate proc-macro crate.

| Crate         | Path       | Purpose                                                                                                                                                                                                                          |
| ------------- | ---------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `euv`         | `.`        | Public facade. Re-exports `euv-core` + `euv-macros` and the wasm-bindgen/js-sys/web-sys bindings.                                                                                                                                |
| `euv-core`    | `core/`    | `App` / `Signal<T>` / `HookContext` / `VirtualNode` / `AttributeValue` / `Css` runtime.                                                                                                                                          |
| `euv-macros`  | `macros/`  | Proc-macros: `html!` / `class!` / `#[component]` / `watch!` / `computed!` / `vars!` / `var!`.                                                                                                                                    |
| `euv-ui`      | `ui/`      | Pre-built UI components (`euv_button`, `euv_card`, `euv_header`, `euv_nav_item`, `euv_modal`, …) + global stylesheet and browser/layout/router/theme/touch/vconsole/virtual-list helpers. |
| `euv-engine`  | `engine/`  | 2D/3D game engine (Canvas + WebGPU renderers, ECS, scene graph, physics, input, sprites, audio, asset cache, scheduler). Zero-size `Engine` façade.                                                                              |
| `euv-cli`     | `cli/`     | CLI tool that wraps `wasm-pack`.                                                                                                                                                                                                 |
| `euv-example` | `example/` | Live demo of every feature as `example/src/page/<name>/`.                                                                                                                                                                        |

Top-level entry point at `src/lib.rs`:

```rust
pub use {euv_core::*, euv_macros::*};
pub use {console_error_panic_hook, js_sys, wasm_bindgen, wasm_bindgen_futures, web_sys};
```

## Project Metadata

- crate 名: `euv` (workspace root)
- Rust edition: `2024`
- License: `MIT`
- 类型: `[workspace]` with 6 members: `cli`, `core`, `engine`, `example`, `macros`, `ui`(注:`core` 不在 `cargo add` 列表,其能力已合入 `euv` facade)
- 关键字: docs-pages 未给出权威 Cargo keywords 列表;以 `Cargo.toml` 为准。

## Installation

```shell
cargo add euv
cargo add euv-ui euv-engine
```

Dev server / build tool — install the `euv-cli` subcommand (`cargo install euv-cli` installs a binary named `euv`):

```shell
cargo install euv-cli
euv run --crate-path . --www-dir ./www --port 80 -- --target web
```

In `Cargo.toml` the workspace declaration is:

```toml
[dependencies]
euv = { path = "euv" }
euv-ui = { path = "euv/ui" }
euv-engine = { path = "euv/engine" }
```

`euv` 库本身 **rlib-only** (`crate-type = ["rlib"]`),而用户项目 `lib.rs` 必须 `crate-type = ["cdylib", "rlib"]`(`cdylib` 让 `wasm-pack` 输出 `*.wasm`;与 `quick-start/README.md:49` 一致)。`euv-macros` 是 `proc-macro = true`;`euv-core`、`euv-ui`、`euv-engine` 是 rlib crates。没有框架自带的 `main.rs`:`example` 暴露 `#[wasm_bindgen] pub fn main()`,内部 `console_error_panic_hook::set_once()` → `euv_ui::inject_app_global_css()` → `App::mount("#app", app)`。

## `euv-cli`

`euv-cli` 是独立的 CLI 工具,二进制名 `euv`,提供 3 个 mode:**`run`**(构建 + dev server + 热重载)、**`build`**(仅构建,等同 `wasm-pack build`)、**`fmt`**(格式化 euv macro)。`--` 之后的 `wasm-pack build` 参数会原样透传(`cli/README.md:27-31`)。安装 + dev 启动一行搞定:

```shell
cargo install euv-cli

euv run --dev --crate-path ./example --port 80 --www-dir www --index-html ./template.html -- \
  --target web --out-dir www/pkg --out-name euv --no-typescript --no-pack --no-gitignore
# 或仅构建:euv build
# 或发布构建:euv run --release ...
```

### `euv fmt` —— **euv 项目唯一推荐的 Rust 格式化器**

```shell
euv fmt
```

**为什么不是 `cargo fmt`**:euv 项目重度依赖 `html!` / `class!` / `vars!` / `var!` / `computed!` / `watch!` / `#[component]` 这类 macro。`cargo fmt` 不展开 macro,只能动 macro 外的 Rust 语法 —— macro **内部**的 child 缩进、嵌套大括号、`key: value;` 折行都不会被处理,导致 PR 里有大量 macro 内手动对齐 / 漂移缩进 看着糟心。

`euv fmt` 则会展开 euv macro 后再格式化,所以:

- `html! { div { class: x() "..." } }` —— child 自动 indent
- `class! { c_x: "..."; c_y: "..."; }` —— `;` 一致、嵌套大括号对齐
- `vars! { pub c_theme_light { space-2xs: "2px"; } }` —— 嵌套层级清晰
- `#[component]` 后的 `fn fn_name(...) { ... }` —— body 一致

> **改完 `.rs` 后 commit 之前必跑 `euv fmt`**;CI 上一般 `euv fmt --check`。其它通用格式化工具链看 `code-formatting-tools` skill 的 §0/§5。

## Quick start

Minimal counter (matches `example/src/page/counter/view/fn.rs` — full version with `euv-ui` wrappers; `quick-start/README.md:62-96` shows the bare `div`/`h1`/`button` form without `euv-ui`):

```rust
use euv::*;
use euv_ui::*;

#[wasm_bindgen]
pub fn main() {
    console_error_panic_hook::set_once();
    euv_ui::inject_app_global_css();
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

Zero-size façade struct (`core/src/app/struct.rs`). All App entry points live in `core/src/app/impl.rs`. Every `use_*` hook and `mount` carries an explicit bound:

```rust
impl App {
    pub fn mount<S, F>(selector: S, render_fn: F)            // CSS-selector mount
        where S: AsRef<str>, F: FnOnce() -> VirtualNode;
    pub fn use_signal<T, F>(init: F) -> Signal<T>           // use inside render fn; outside, use Signal::create
        where T: Clone + PartialEq + 'static, F: FnOnce() -> T;
    pub fn use_cleanup<F>(cleanup: F)                        // called on context teardown
        where F: FnOnce() + 'static;
    pub fn use_interval<F>(millis: i32, callback: F) -> IntervalHandle
        where F: FnMut() + 'static;
    pub fn use_window_event<E, F>(event_name: E, callback: F)
        where E: AsRef<str>, F: FnMut() + 'static;
    pub fn batch<F, R>(callback: F) -> R                      // precise-dirty batching
        where F: FnOnce() -> R;
    pub fn schedule_update(dependents: &[usize])             // precise-dirty mark + dispatch
}
```

`App::mount("#app", app)` calls `app()` to render the root, then re-runs it whenever any `Signal<T>` read during that render fires `.set()`.

### `Signal<T>` — reactive primitive

`core/src/reactive/signal/{struct,impl}.rs`. Both `App::use_signal` and every `Signal<T>` impl are gated on the same `T` bound. `Signal<T>` is `Copy`/`Clone` and owns a `usize` handle to heap state; `SignalCell<T>` is the separate single-threaded initialization wrapper:

```rust
impl<T> Signal<T>
where
    T: Clone + PartialEq + 'static,
{
    pub fn create(value: T) -> Self                          // direct, no HookContext
    pub fn get(&self) -> T                                   // auto-tracks current DynamicNode id
    pub fn set(&self, value: T)                              // no-op when value == current
    pub fn subscribe<F>(&self, callback: F)                  // appends a listener
        where F: FnMut() + 'static;
    pub(crate) fn replace_listener<F>(&self, callback: F)    // clear-and-set
    pub(crate) fn deactivate(&self)                          // mark alive=false (for stale closures)
}

impl<T> SignalCell<T>
where
    T: Clone + PartialEq + 'static,
{
    pub const fn none() -> Self
    pub fn set(&self, signal: Signal<T>)                     // panics if already initialized
    pub fn get(&self) -> Signal<T>                           // panics if uninitialized
}

impl FireHandle {
    pub fn new<F>(fire: F) -> Self where F: FnMut() + 'static
    pub unsafe fn fire(self)
    pub unsafe fn fire_at(addr: usize)
}

impl<T> Default for Signal<T>
where
    T: Clone + PartialEq + 'static + Default,
{
    fn default() -> Self { Self::create(T::default()) }
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
pub enum Tag { Element(String), Component(String) }   // Tag::Component marks custom #[component] functions
pub enum VirtualNode<Props = ()> {
    Element {
        tag: Tag,
        attributes: Vec<AttributeEntry>,
        children: Vec<VirtualNode>,
        key: Option<String>,
        props: Option<Box<Props>>,
    },
    Text(TextNode),
    Fragment(Vec<VirtualNode>),
    Dynamic(DynamicNode),
    Empty,
}

impl VirtualNode<Props> {
    // children 折叠为单个 VirtualNode
    //   - 无 children → Empty
    //   - 1 个 child  → 直接返回该 child
    //   - ≥2 个       → Fragment(Vec<VirtualNode>)
    // 错误形式(无 child)内部走 try_get_child_node().unwrap_or_default()。
    pub fn get_child_node(&self) -> VirtualNode;
    // 取 Element 变体的 props 克隆。`Text` / `Fragment` / `Dynamic` / `Empty` 全部返回 None。
    // 要求 Props: Clone(签名 where bound 强制)。
    pub fn try_get_props(&self) -> Option<Props> where Props: Clone;
    // 返回 Option<VirtualNode>(无 child 时 None,1 个 child 时 Some(child),多个时 Some(Fragment))
    pub fn try_get_child_node(&self) -> Option<VirtualNode>;
    // Vec<VirtualNode> 形式:Element 的 children 字段;非 Element 返回 None
    pub fn try_get_children(&self) -> Option<&Vec<VirtualNode>>;
    pub fn has_children(&self) -> bool;
}
```

```rust
use euv::VirtualNode;

fn first_child(node: &VirtualNode) -> VirtualNode {
    node.get_child_node()      // 自动 Empty / single / Fragment 三态
}

fn dump_props<P: Clone + std::fmt::Debug>(node: &VirtualNode<P>) {
    if let Some(p) = node.try_get_props() {        // 非 Element 变体返回 None
        println!("props = {p:?}");
    }
}
```

### CSS class helpers

`ui/src/style/class/fn.rs` exposes class helpers like `c_page_container()`, `c_counter_value()`, `c_button_controls()` etc. Call them inside `class: c_xxx()` attributes. To register your own styles use `Css::inject_css(text)` (公开 API 形式;`core/src/vdom/attribute/impl.rs` 是源码内部路径) 或 `euv_ui::inject_app_global_css()`。

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

- `if / if-else / if-else if / if-else if-else` 块级链 **全部支持**。`macros/src/html/impl.rs:165-170` 是块级 `else` 的解析路径(`else` 后非 `if` 直接 push `(None, body, false)` 终止循环)。reactive / inline 形态和混合链(`if a {} else if {b} {}`)也均 OK。`form.md:151-165` 级联下拉框示例演示了 `if { } { } else if { } { } else { "" }` 链。
- `if { cond } { body }` 的 body **必须**用 `{ ... }` 花括号块包裹(不接裸表达式或裸子元素列表)。`macros/src/html/impl.rs:144-146` 强制 `braced!` 解析 body。同样的限制也适用于 `else` / `else if` 的 body,以及 `for ... in ... { body }` / `match ... { ... }` 的所有 arm body。
- 在 attribute 位置使用 `if ...`(例如 `class: if { cond } { c_a() } else { c_b() }`)时,body 必须是单值或 `{ ... }` 块,**不能**是裸 children 块(`macros/src/html/impl.rs` 的 attribute-value 解析路径约 L312-318)。
- Closures captured inside `for` bodies cannot outlive the closure, so complex per-row event handlers (edit/delete/pagination) need a refactor pattern (see `euv-html-macro-traps`).
- Non-`Copy` values captured by the render closure need `.clone()` because the html! body is a `FnMut`.
- `key:` attribute on each `for`-iteration child is recommended for stable diffing.

## `class!` macro

`macros/src/lib.rs::class`:

```rust
class! {
    pub c_base_button {
        display: "flex";
        padding: "12px 16px";
    }
    pub c_primary_button(color: &str) {
        c_base_button();
        background: color;
        :hover {
            opacity: "0.9";
        }
        @media (max-width: 767px) {
            padding: "8px 12px";
        }
    }
}
```

`class!` supports plain declarations, parameterized classes, inheritance via call-like entries such as `c_base_button()` or `c_base_button(arg)`, dynamic property keys (`{key}: value`), CSS pseudo selectors (`:hover`, `::before`, nested selectors), and CSS at-rules including `@media`, `@keyframes`, `@supports`, `@layer`, `@container`, `@property`, `@scope`, `@font-face`, and other parsed at-rule forms. It generates a function returning `Css`; `vars!` 也生成函数,非参数化返回 `&'static Css`,参数化返回 owned `Css`(`css-vars.md:99`);`vars!` 支持参数化:

```rust
vars! {
    pub c_theme_dynamic(bg: &str, text: &str) {
        bg-primary: {bg};
        text-primary: {text};
    }
}
```

`var!(name)` expands to the string `var(--name)`.

## Other macros (`euv-macros`)

All proc-macros from `macros/src/lib.rs`:

| Macro                  | Syntax                                                | Behavior                                           |
| ---------------------- | ----------------------------------------------------- | -------------------------------------------------- |
| `#[component]`         | on `fn name(node: VirtualNode<Props>) -> VirtualNode` | Marker attribute; `html!` discovers annotated component functions by scanning source and uses the generated props metadata |
| `html! { ... }`        | inline template                                       | VirtualNode DSL; supports dynamic expressions, reactive `if`/`match`/`for`, event attributes, keys, and multiple roots |
| `class! { ... }`       | inline CSS block                                      | Generates `Css` helpers, including selectors, nested selectors, dynamic keys, parameters, inheritance, and at-rules |
| `vars! { ... }`        | CSS custom-property block                             | Generates a `Css` helper whose declarations are emitted as `--name: value` |
| `var!(name)`            | inside CSS expressions                                 | Expands to the CSS string `var(--name)` |
| `watch!(signals..., closure)` | signals + closure | Runs once immediately and again when any input signal changes; init + on-change runs in `App::batch`, so cascading `set` calls within the same frame are merged into a single DOM update (`binding.md:213-214, 232-233`) |
| `computed!(signals..., closure) -> T` | signals + typed closure return | Creates a derived `Signal<T>` and updates it when an input changes |

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

## Event factory

`NativeEventHandler` 是 euv 公开 API 的事件工厂(非 macro,但与 `html!` 事件属性同级别;`event.md:39-79`):

```rust
impl NativeEventHandler {
    pub fn create(event_name: &'static str, callback: impl FnMut(Event) + 'static) -> Self;
    pub fn handle(self, event: &Event);   // manual dispatch
}
```

使用:在组件 Props 间传递或复用。`handler.handle(event)` 手动调用。`NativeEventHandler: Clone`,克隆共享同一闭包。

## `euv-ui` components (`ui/src/component/<name>/view/fn.rs`)

Each component takes `VirtualNode<EuvXxxProps>` and returns `VirtualNode`. Common props:

| Component                              | Props struct                                               | Required fields                   | Notable enum                                                        |
| -------------------------------------- | ---------------------------------------------------------- | --------------------------------- | ------------------------------------------------------------------- |
| `euv_button`                           | `EuvButtonProps`                                           | `label`, `variant`                | `EuvButtonVariant::{Primary,Secondary,Success,Danger,Warning,Info}` |
| `euv_card`                             | `EuvCardProps`                                             | `title`                           | —                                                                   |
| `euv_header`                           | `EuvHeaderProps`                                           | `icon`, `title`, `subtitle?`      | —                                                                   |
| `euv_input`                            | `EuvInputProps`                                            | `value: Signal<String>`           | —                                                                   |
| `euv_checkbox`                         | `EuvCheckboxProps`                                         | `checked: Signal<bool>`           | —                                                                   |
| `euv_field`                            | `EuvFieldProps`                                            | `label`, `value: Signal<String>`  | —                                                                   |
| `euv_modal`                            | `EuvModalProps`                                            | `visible: Signal<bool>`, `closer` | —                                                                   |
| `euv_nav_item` / `euv_mobile_nav_item` | `EuvNavItemProps`                                          | `label`, `route`, `on_click`      | —                                                                   |
| `euv_nav_items`                        | `EuvNavItemsProps`                                         | `items: Vec<EuvNavItemConfig>`    | —                                                                   |
| `euv_tag`                              | `EuvTagProps`                                              | `label`                           | `EuvTagVariant`, `EuvTagColor`                                      |
| `euv_badge`                            | `EuvBadgeProps`                                            | `label`                           | —                                                                   |
| `euv_alert`                            | `EuvAlertProps`                                            | `message`                         | `AlertVariant`                                                      |
| `euv_loading`                          | `EuvLoadingProps`                                          | —                                 | —                                                                   |
| `euv_logo`                             | `EuvLogoProps`                                             | —                                 | `LogoButtonVariant`                                                 |
| `euv_info`                             | `EuvInfoProps`                                             | —                                 | —                                                                   |
| `euv_browser`                          | (browser-view wrapper around `<iframe>` + sandbox helpers) | —                                 | —                                                                   |
| `euv_camera`                           | (camera/microphone permission + preview hooks)             | —                                 | —                                                                   |
| `euv_layout`                           | (`euv_layout_*` grid shell components)                     | —                                 | —                                                                   |
| `euv_theme`                            | (theme toggle + system-theme tracking)                     | —                                 | —                                                                   |
| `euv_touch`                            | (touch / swipe gesture helpers)                            | —                                 | —                                                                   |
| `euv_virtual_list`                     | `EuvVirtualListProps`                                      | `config: EuvVirtualListConfig`    | —                                                                   |
| `euv_routes` / `euv_page_router`       | `EuvRoutesProps`                                           | `routes: Vec<EuvRouteConfig>`     | —                                                                   |
| `euv_vconsole_panel/fab/drawer`        | `EuvVconsole*Props`                                        | —                                 | `LogLevel`, `LogFilter`                                             |

Component files live under `ui/src/component/<name>/` (`view/fn.rs` for the `#[component]` fn, `struct.rs` for the Props struct, `enum.rs` for any *Variant / *Color enums, plus `impl.rs`, `type.rs`, `const.rs` etc. as needed). `ui/src/component/mod.rs` lists the 22 directories: `alert`, `badge`, `browser`, `button`, `camera`, `card`, `checkbox`, `field`, `header`, `info`, `input`, `layout`, `loading`, `logo`, `modal`, `nav`, `router`, `tag`, `theme`, `touch`, `vconsole`, `virtual_list`.

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

> **注意(docs-pages `event.md:194-245`)**: `use_toggle` / `on_input_value` / `on_change_value` / `on_change_checked` / `on_focus_scroll_into_view` / `on_blur_restore_height` 在 `euv-ui` 中是 `UseEuvInput` 零大小结构体的**关联函数**,而非自由函数;正确调用形式是 `UseEuvInput::on_input_value(text)` 等。`on_input_value` / `on_change_value` 同时支持 `HtmlInputElement` / `HtmlTextAreaElement` / `HtmlSelectElement` 三种表单元素(`event.md:245`);原生 `select` 元素可用 `onchange: UseEuvInput::on_change_value(signal)` 直接绑定(见 `form.md:103-167`)。

## `euv-engine` (optional)

`engine/src/lib.rs` 暴露 18 个子模块(全部 `pub use *`):`asset` / `audio` / `cell` / `collider` / `config` / `easing` / `engine` / `entity` / `input` / `math` / `particle` / `physics` / `renderer` / `scene` / `scheduler` / `spatial` / `sprite` / `timer` / `tween`(L8-26)。架构与 `euv::App` 同型:`Engine` 是**零大小**命名空间(所有方法都是 `impl Engine` 上的关联函数,不持有状态),真正干活的是 `EngineHandle`(stateful,持 `EngineConfig` + `CanvasRenderer` / `WebGpuRenderer` / `WebGlRenderer` + `SchedulerHandle`)。`NativeEventHandler`(`euv-core` 公开)与 engine 内部 namespace 的 `EventHandler`(实际是 `Rc<dyn Fn(&EntityEvent)>` 给 `Entity::subscribe` 用)是完全不同的概念,不要混用。

### 完整 Engine 启动示例(Canvas 2D + TickHandler)

```rust
use euv::*;
use euv_engine::*;

// 1. RenderConfig:canvas2d / webgpu / webgl 都是 (selector, width, height) 3 参(selector 是 S: AsRef<str>)
let render: RenderConfig = RenderConfig::canvas2d("#game", 1280.0, 720.0);
// let render = RenderConfig::webgpu("#game", 1280.0, 720.0);   // 3D 用,需要浏览器支持 WebGPU
// let render = RenderConfig::webgl("#game", 1280.0, 720.0);     // WebGL 2 后备方案

// 2. EngineConfig:create 接受 RenderConfig,默认 SchedulerConfig(60Hz fixed timestep)
//    builder 链:目前只有 with_scheduler(没有 with_input / with_scene / with_ecs)
let config: EngineConfig = EngineConfig::create(render);

// 3. TickHandler 必须实现两方法(签名见 engine/src/scheduler/trait.rs)
struct Game { x: f64 }
impl TickHandler for Game {
    fn on_update(&mut self, delta_time: f64) {          // 固定步长,所有游戏逻辑在这
        self.x += 100.0 * delta_time;
    }
    fn on_render(&mut self, interpolation: f64) {      // 每动画帧一次,interpolation ∈ [0,1)
        // 用 interpolation 在两个 on_update 之间插值,得到平滑渲染
        let _ = (self.x, interpolation);
    }
}

#[wasm_bindgen]
pub async fn start_game() {
    // 主路径:new_handle + init_canvas + start
    let mut handle: EngineHandle = Engine::new_handle(config);
    if handle.init_canvas() {            // bool — 成功 true,失败 false
        handle.start(Rc::new(Game { x: 0.0 }) as TickHandlerRc);
    }

    // 快速路径:Engine::run 一次完成 new_handle + init + start(返回句柄,可用 handle.stop() 停止)
    let handle: EngineHandle = Engine::run(EngineConfig::create(render), Rc::new(Game { x: 0.0 })).await;
    // let _ = handle;   // 用 handle.stop() 关闭
}
```

### Scheduler 独立使用(不用 `Engine`)

`SchedulerHandle::start(config, handler)` 是 `requestAnimationFrame` 驱动的 fixed-timestep loop,`SchedulerConfig` **没有** `default()` 之外的 public 构造;用 `SchedulerConfig::new(fixed_timestep, max_frame_time)`(或 `..Default::default()` 拿到 60Hz 默认值)。`engine.md:153` 和 `engine/src/scheduler/impl.rs:4-8` 都确认 `Default` 是 `new(DEFAULT_FIXED_TIMESTEP, DEFAULT_MAX_FRAME_TIME)`。

```rust
use euv_engine::*;
use std::rc::Rc;

let cfg: SchedulerConfig = SchedulerConfig::new(1.0 / 60.0, 0.25);   // 60Hz, frame_time 上限 0.25s
let handler: TickHandlerRc = Rc::new(MyGame::default());
let sched: SchedulerHandle = SchedulerHandle::start(cfg, handler);
// ... 之后用 sched.stop() / sched.is_running() / sched.update_count() / sched.frame_count()
```

### Canvas 2D vs WebGPU vs WebGL

- `init_canvas(&mut self) -> bool` — 同步,无错误细节,失败仅返回 `false`(用于 fast-path `Engine::run` 也只能靠此判断)。
- `init_webgpu(&mut self) -> Result<WebGpuRenderer, WebGpuInitError>` — `async`,返回 typed error(`WebGpuInitError`);要在 UI 上报告 WebGPU 失败原因时**直接调** `init_webgpu`,不要走 `Engine::run`。
- `init_webgl(&mut self) -> Result<WebGlRenderer, WebGpuInitError>`(同形态,`engine.md:53-54`)。
- 三者**互斥**:init 任意一个会清空另外两个的 renderer 字段(`engine/src/engine/impl.rs:155-168`)。`Engine::run` 内部按 `RenderConfig.get_backend()` 自动选 init 函数。
- `WebGpuInitError` 是 `renderer` 子模块导出,要在 match arm 里用就 `use euv_engine::WebGpuInitError;`。

### Input / Scene / Entity / Physics 模块速查

- `input` — `Input`(零大小 namespace)、`InputState`、`MouseButton`、`InputAction`(枚举)。底层容器是 `HashSet<Input>` / `HashSet<InputAction>`,**不是** `Set`(`engine/src/lib.rs:38` 已 `use std::collections::{HashMap, HashSet}`)。
- `scene` — `SceneManager`,`Scene` trait,`SceneRc`;转场 `request_transition` / `process_pending_transition`。
- `entity` — `Entity`、`EventBus`、`Component` trait;类型别名 `ComponentRc` / `EntityRc` / `EventHandler = Rc<dyn Fn(&EntityEvent)>` / `EventHandlers = HashMap<String, Vec<EventHandler>>`(`engine/src/entity/type.rs:18-21`)。`Entity::subscribe(name, handler)` 绑事件。
- `physics` — `RigidBody2D::new(id, position, velocity, force_accumulator, rotation, angular_velocity, mass, inverse_mass, restitution, friction, body_type, collider)` 12 参;`RigidBody2D::new_dynamic(id, position)` 简写;`RigidBody3D` 同形;`PhysicsWorld2D/3D`,`BodyType`,`BodyCollider` / `BodyCollider3D`。
- `collider` — `Collider` / `Collider3D` trait,`AabbCollider`,`CircleCollider`,`AabbCollider3D`,`SphereCollider3D`。
- `renderer` — `CanvasRenderer`,`WebGpuRenderer`,`Camera2D/3D`,`SsaaCanvas`,`LinearGradient`,`RadialGradient`,`ShadowConfig`,`RenderLayer`,`BlendMode`,`RenderQuality`,`WebGpuInitError`。
- `sprite` — `SpriteSheet`,`SpriteFrame`,`SpriteAnimation`,`Animator`,`AnimationMode`,`AnimationState`。
- `asset` — `AssetCache`,`AssetLoader`,`AssetType`,`AssetState`,`AssetEntry`。
- `audio` — `GameAudioContext`,`AudioClip`,`AudioPlayState`(Web Audio 封装)。
- `cell` / `tween` / `easing` / `timer` / `particle` / `math` — 内部 cell 容器、tween 系统、缓动函数、计时器、粒子系统、数学(`Vector2D/3D`,`Quaternion`,`Matrix4x4`,`Rect`,`Circle`,`Color`,`AABB3D`,`Sphere`,`Plane`,`Ray3D`,`Transform2D/3D`,常量 `PI` / `TWO_PI` / `DEG_TO_RAD` / `EPSILON`,free fns `clamp` / `lerp` / `distance` / `smoothstep` / `approach` / `sign` / `wrap` / `lerp_angle` / `from_angle`)。
- `spatial` — `SpatialHashGrid2D::with_default_size()`,`SpatialHashGrid2D::query(&self, center: Vector2D, half_extent: Vector2D) -> Vec<usize>`(`engine.md:101`);3D 同形。

### TickHandler 注意事项

- `TickHandler` trait 在 `engine/src/scheduler/trait.rs:3-22`;**必须**实现 `on_update(&mut self, delta_time: f64)` 和 `on_render(&mut self, interpolation: f64)` 两方法,缺一编译失败。
- 传给 `EngineHandle::start` / `SchedulerHandle::start` 的形参是 `TickHandlerRc`(=`Rc<dyn TickHandler>`),所以要么 `Rc::new(MyGame::default()) as TickHandlerRc`,要么直接传 `Rc<MyGame>` 靠 coercion。
- `interpolation` ∈ [0, 1):当前帧在两个固定步长 `on_update` 之间的相对位置;用 `(prev_state * (1 - interp) + curr_state * interp)` 做插值,渲染才不掉帧。
- `delta_time` 来自 `SchedulerConfig::fixed_timestep`,**永远等于** `fixed_timestep`;不是真实 wall-clock 间隔。
- `frame_time` 走 `min(real_frame_time, max_frame_time)`,防止 tab 切回后巨量补帧。

## Common pitfalls

1. **`signal.get()` in `html!` body inside `{}`** — single-segment ident auto-unwraps, multi-segment does not. `state.value` inside `{}` stays a `Signal<T>`; use `state.value.get()` explicitly.
2. **`if { cond } { body }` body 必须是 `{ ... }` 块** — 不能写裸表达式或裸子元素列表(`macros/src/html/impl.rs:144-146` 强制 `braced!` 解析)。纯 `if { } { } else { }`(不带 `else if` 中间分支)的块级 `else` **完全支持**(解析路径 `macros/src/html/impl.rs:165-170`);reactive / inline 形态、混合链(`if a {} else if {b} {}`)也都 OK。
3. **Closures over for-loop items** — complex CRUD with per-row click handlers inside `for` loops runs into `FnMut`-double-borrow issues. Restructure into a parent `Signal<Vec<T>>` and a single child component.
4. **`Signal<T>` vs `SignalCell<T>`** — `Signal::create(value)` is the direct public constructor; `SignalCell::none()`/`set()`/`get()` is a separate single-threaded storage wrapper. There is no `Signal::none()` or `Signal::new(value)` public constructor. (基于 `core/src/reactive/signal/struct.rs` 源码,docs-pages 未演示。)
5. **Non-Copy values in `html!`** — render body is `FnMut`. `let count = App::use_signal(|| 0)` works because `i32` is `Copy`. For `String` etc., use signals only and clone on capture.
6. **`#[component]` body must destructure props via `node.try_get_props().unwrap_or_default()`** — the macro generates the wrapper but the inner fn receives `VirtualNode<Props>` not `Props`.
7. **`inject_app_global_css()` must be called before `App::mount`** — otherwise `euv_button` etc. render unstyled.
8. **`console_error_panic_hook::set_once()` is required** in `main()` or Rust panics in the browser are silent.
9. **`class!` "继承"通过调用父函数(不是 `extends` 关键字)** — 例如 `c_base_button();` 嵌入父类块;同名属性按 CSS cascade 后定义者获胜。不要通过重新声明同名属性来"移除"父类样式(`class!` 没有 `extends` 关键字,这个名字可能是误用)。
10. **`c_euv_button_*` classes force `flex: 1 1 120px`** — any `display:flex` parent will stretch them to ≥120px. Wrap in a non-flex container or add `flex: none` override. (基于 `ui/src/style/class/fn.rs` 源码,docs-pages 未覆盖。)
11. **`<form onsubmit=...>` 必须 `event.prevent_default()`** — 否则页面会刷新 (`form.md:99-101`)。
12. **`ondragover` 必须 `event.prevent_default()`** — 否则 `ondrop` 不会触发 (`form.md:241-243, 261`)。

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
