---
name: euv
description: '**入口 skill — 使用 euv 框架必须加载**。euv 是 declarative cross-platform UI 框架,edition 2024,Rust → WASM 编译,monorepo 7 个 crate(core / engine / macros / ui / cli / example / docs)。关键 API:App::mount + Signal<T> + #[component] + html!/class!/vars!/var!/watch!/computed!。**Progressive loading 模式**:本 skill 是入口 + 跳转表;具体 API 在 references/api-*.md 子文档按需加载,避免一次读全量。**任何涉及 euv 框架的任务先 load 本 skill,然后根据要写的代码类型加载对应的 api-*.md**。**当且仅当任务完全不使用 euv**才不加载。'
license: MIT
---
# euv 入口 skill — Progressive Loading Index

> **本 skill 只做跳转 + 5-行最小调用**。euv 框架的完整 API / 坑表按需求分到 references/api-*.md 子文档中,需要哪个加载哪个,不要一次读全。

## 0. 必须先了解

- **Workspace 布局**:workspace 根 `euv` (re-export 包) + 7 个子 crate(`core` + `engine` + `macros` + `ui` + `cli` + `example` + `docs`),见 `euv-standards/SKILL.md` §1
- **Rust edition**:2024;**Framework 是 WASM target**(非 native)
- **依赖管理**:用 `crate-cli`(`~/.cargo/bin/crate`),**不要用 `euv-cli`** 做 fmt/bump/publish
- **skill 不维护版本号**:查根 `Cargo.toml` `[workspace.package] version`

## 1. 按需加载 — references/api-*.md

### `references/api-core.md`(euv-core 完整 pub API,~232 项,~23 KB)

**何时加载**:写 `Signal<T>` / `VirtualNode` / `App` / `Hook` / `Event` / `NodeRef` / `AttributeValue` / `Render` / `LruCache` 时。

| 你要写... | 看哪一段 |
|---|---|
| `Signal<T>` 创建/读写/订阅(`Signal::create` / `.get` / `.set` / `.subscribe` / `.unsubscribe`) | `app::impl` + `reactive::signal::impl` + `reactive::signal::struct` |
| `use_signal / use_cleanup / use_interval / use_window_event / use_node_ref / batch / mount / schedule_update` | `app::impl` |
| `VirtualNode::Tag / VirtualNode` enum + `render / try_get_tag_name / get_children / try_get_props / extend_attributes` | `vdom::node::impl` + `vdom::node::enum` + `vdom::node::struct` |
| `AttributeValue` + `Css` + `MediaRule` + `EventAdapter` + `into_attribute / into_callback` | `vdom::attribute::*` + `vdom::cast::impl` |
| `NodeRef<T>`(`new / get / set / get_cloned / clear / is_set`) | `noderef::impl` + `noderef::struct` |
| `NativeEventHandler::create` + `EventCallback / SharedEventCallback` | `event::handler::*` |
| `LruCache<K, V>`(`get / put / peek / remove / contains / len` 等) | `reactive::cache::impl` + `reactive::cache::struct` |
| `HookContext::current / with / signal / cleanup / noderef` + `IntervalHandle` | `reactive::hook::impl` + `reactive::hook::struct` |

### `references/api-macros.md`(euv-macros,8 个 proc_macro)

**何时加载**:写 `html!{}` / `class!{}` / `vars!{}` / `var!(name)` / `watch!{}` / `computed!{}` / `#[component]` 时。

| 宏 | 用途 |
|---|---|
| `html!(...)` | 声明式 UI 节点(JSX-like,compile-time 展开 `VirtualNode`) |
| `class!(...)` | 嵌套 CSS class 定义(@media / @keyframes / `var!(...)` 嵌套)|
| `vars!(...)` | 全局 CSS custom properties(theme tokens)|
| `var!(name)` | class 内引用 `--name` 的糖 |
| `watch! { signal => expr }` | 响应式副作用 |
| `computed! { signal => expr }` | 派生 Signal |
| `#[component]` | 函数转 component,自动 Props 注入 |
| `unsafe_no_inline!`(internal)| framework 内部用 |

### `references/api-ui.md`(euv-ui 完整 pub API,~386 项,~40 KB)

**何时加载**:写任何 `euv_button {}` / `euv_card {}` / `use_async` / `use_i18n` / theme / router / markdown / virtual_list 等 component 或 hook 时。

**结构**:
- `component/<name>/view/{fn, struct, enum}` — 每个 `euv_<name>` 组件的签名/Props/事件
- `component/<name>/hook/{fn, struct, impl}` — 组件专属 hook(`browser` / `camera` / `input` / `layout` / `router` / `theme` / `touch` / `vconsole` / `virtual_list`)
- `hook/<utility>/{fn, struct, impl, enum, type, trait}` — 通用 hook 工具集(`counter` / `debounced_value` / `error_boundary` / `form` / `i18n` / `lazy` / `previous` / `profiler` / `suspense` / `throttled_value` / `toggle` / `transition` / `use_async`)
- `style/{class, var, css}` — design tokens(详细 class 见 `euv-ui-standards`)

### `references/api-engine.md`(euv-engine 完整 pub API,~704 项,~63 KB,最大)

**何时加载**:写 2D/3D game / 渲染 / physics / sprite / particle / asset / scheduler 时。

**模块**:21 个,grep `grep -cE "^mod [a-z_]+;" engine/src/lib.rs` 即得。包括:`asset` / `audio` / `cell` / `collider` / `config` / `easing` / `engine` / `entity` / `input` / `lighting` / `math` / `particle` / `physics` / `raytracing` / `renderer` / `scene` / `scheduler` / `spatial` / `sprite` / `timer` / `tween`(全部 `pub use *` re-export 到 crate 根)。

### `references/api-cli.md`(euv-cli 完整 pub API,~39 项)

**何时加载**:写 CLI tool 集成 / `euv-cli` subcommand 时。**注意**:euv-cli 不提供 fmt/bump/publish — 这些在外部 `crate-cli`。

### `references/api-docs.md`(euv-docs,~34 项)

**何时加载**:用 euv-docs 写文档站(`home_page` / `bin/docs`)。

### `references/pitfalls.md`(consolidated index,链接到详细 reference)

**何时加载**:写完代码准备提交 / debug 一个奇怪行为时。包含 20+ 个反复踩坑的 mixin / hook / DOM / version / build 问题。

## 2. 互锁 skill(必须同时加载)

| 你要做... | 加载 |
|---|---|
| 写任何 Rust 代码 | `rust-standards` |
| 写 design class / 用 `var!()` 引用 CSS token | `euv-ui-standards`(class 索引 + design tokens) |
| 编译到 WASM | `rust-crate-use` 提供 `wasm-pack` / `wasm-bindgen` 文档 |
| 跑 example / 验证 demo | `euv-wasm-gh-pages-deploy-pitfalls`(WASM 部署)|
| PR / bump 流程 | `rust-pr-validation-checklist` + `euv-standards/SKILL.md` §17 |

## 3. 5-行最小调用

```rust
use euv::{App, Signal, component, html};

#[component]
fn Counter() -> VirtualNode {
    let count = use_signal(|| 0);
    html! { <button onClick={move |_| count.set(count.get() + 1)}>{count}</button> }
}

fn main() {
    App::mount("#app", || html! { <Counter /> });
}
```

完整 `html!{}` 语法 / reactive `if / match / for` / `class!{}` 嵌套 / event handler 注册:加载 `references/api-macros.md`。

## 4. docs-pages 文档站(教程 / 完整示例)

`docs-pages` 仓库(docs-pages/docs)提供完整中文教程 — 全 25+ 个 page 同步到本 skill 的 `references/` 下(按 topic 切分):
- **宏**: `references/html.md`, `class.md`, `component.md`, `watch.md`, `computed.md`, `var.md`, `css-vars.md`
- **特性**: `references/reactive.md`, `vdom.md`, `event.md`, `engine.md`, `lifecycle.md`, `mount.md`, `binding.md`, `list.md`, `conditional.md`, `async.md`, `form.md`, `keep_alive.md`, `canvas.md`, `websocket.md`, `sse.md`, `observer.md`, `platform.md`, `animation.md`, `timer.md`, `select.md`, `file.md`, `renderer.md`

这些是**教程**(有完整示例代码),与 `references/api-*.md` 的**API 速查**互补。两者按需加载。

## 5. 何时不加载本 skill

- 任务只涉及 hyperlane / rust-standards / cargo / git — 与 euv 完全无关
- 任务只读 euv 源码做静态分析 / extract API(已经用本 skill 的 references/api-*.md 即可)

## 6. 相关 skill

- **`euv-standards`**:workspace 布局 + crate 关系 + 跨 crate 规则(`[workspace.package]` / sync_workspace_version / 7 个 crate 互依赖 / version bump 铁律)
- **`euv-ui-standards`**:design class catalogue + var token 索引(查具体 class 含义)
- **`euv/euv-ui-class-verification`**:改 `class!{}` 后验证 class 注册表一致
- **`euv/euv-engine-webgpu-completion-workflow`**:WebGPU renderer API 补完流程
- **`euv/euv-hyperlane-fullstack-mobile`**:euv + hyperlane + 移动端 wasm 整合
- **`euv/euv-game-real-api-notes`**:euv-engine 真实 API notes
- **`euv/euv-app`**:euv-app (Tauri 2.x Android packaging)
- **`rust-standards`**:Rust 通用规范