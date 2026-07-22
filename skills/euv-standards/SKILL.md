---
name: euv-standards
description: EUV 框架开发指南。涵盖 html! / class! / vars! / var! / #[component] / watch! / computed! 宏的完整使用规范 + euv-core App / Signal<T> / HookContext / VirtualNode 全部公开 API + class! extends 拼接语义 + auto-get 单段标识符自动 .get() 语法糖 + 22 个 ui 组件 + 6 个模块布局（core/engine/ui/macros/cli/example）。触发关键词：euv、Signal、html!、class!、computed!、watch!、vars!、var!、![component]、VirtualNode、use_signal、App::mount、wasm-pack、euv-cli、auto_value、euv_component_registry_cache。
license: MIT
---

# EUV 框架开发指南

`euv-standards` skill 覆盖 **euv** WebAssembly UI 框架的全部编码规范。本文档对应源版本为 `/d/code/euv/Cargo.toml` (`euv = "0.12.23"`, edition 2024)；monorepo 6 个子 crate：`core` / `engine` / `macros` / `ui` / `cli` / `example`（根 `euv` crate 只是个 2 行 `pub use` 壳）。

事实依据由源码直接验证（详见"Source-of-truth files"段）。
完整类目见 `euv-ui-standards` skill（304 个 class! + design tokens）。

---

## 1. 快速开始

### 1.1 项目初始化

`example/` 子项目是直接拿来用的 demo：

```shell
cd /d/code/euv/example
cargo build --release
wasm-pack build --target web --dev
# 输出在 example/pkg/，搭一个静态 server 跑 example/www/
```

CLI 工具：`cargo install --path euv/cli`（**或** 跑预编译的 `euv build` / `euv fmt` / `euv server` / `euv mode`，详见第 17 节）。

### 1.2 入口文件 `src/lib.rs`

`euv` 本身只是个 `pub use {euv_core::*, euv_macros::*}` + `pub use {console_error_panic_hook, js_sys, wasm_bindgen, wasm_bindgen_futures, web_sys}` 的薄壳。euv **无 main.rs**，需要你写：

```rust
use euv::*;
use euv_ui::inject_app_global_css;

#[wasm_bindgen]
pub fn main() {
    console_error_panic_hook::set_once();
    inject_app_global_css();
    App::mount("#app", app);
}

fn app() -> VirtualNode {
    // 返回虚拟 DOM（详见第 3 节 html! 宏）
    html! { div { "Hello" } }
}
```

`console_error_panic_hook::set_once()` 必须设置，否则浏览器中的 Rust panic 静默无输出。`inject_app_global_css()` 必须在 `App::mount` 之前调用，把 `ui/src/style/css/fn.rs` 里的全局 CSS 注入到 `<head>`。

### 1.3 HTML 入口 `www/index.html`

```html
<!DOCTYPE html>
<html>
  <head>
    <meta charset="utf-8" />
    <title>euv app</title>
  </head>
  <body>
    <div id="app"></div>
    <script type="module" src="../pkg/euv_example.js"></script>
  </body>
</html>
```

`<div id="app">` 是 `App::mount("#app", ...)` 选择器匹配目标，**ID 必须存在**。

### 1.4 构建与运行

```shell
wasm-pack build --target web --dev    # 产 pkg/*.wasm + pkg/*.js

# 用 euv dev server（自带热重载）：
euv server                            # 包含 wasm-pack --dev + file watcher

# release:
wasm-pack build --target web --release
```

Cargo 端关键依赖：`hyperlane = "21.3.4"`（CLI 用作 server），`wasm-bindgen = "0.2"`，`web-sys = { version = "0.3", features = ["..."] }`（feature 列表非常长，详见根 `euv/Cargo.toml`）。

---

## 2. 项目目录结构

```
euv/                            # workspace root
├── Cargo.toml                  # 6 members: cli, core, engine, example, macros, ui
├── src/lib.rs                  # 2 行 pub use 薄壳
├── cli/                        # CLI 工具（euv build / fmt / server / mode）
├── core/                       # 运行时：App / Signal<T> / HookContext / VirtualNode / Css
│   └── src/{app,event,reactive,renderer,vdom}/
├── engine/                     # 2D/3D 游戏引擎（Canvas + WebGPU）
│   └── src/{asset,audio,collider,config,engine,entity,input,math,physics,renderer,scene,scheduler,spatial,sprite}/
├── macros/                     # 6 个 proc-macro 函数式 + 1 个 attribute
│   └── src/{class,computed,html,ident,var,watch}/
├── ui/                         # 22 个组件 + 全局 class! 注册表 + CSS vars + global CSS
│   └── src/{component,style}/ + 22 个 ui 组件子目录
└── example/                    # 完整 demo（example/src/page/<name>/ 共 ~20 个 page）
```

`euv-macros` 是 `proc-macro = true`，通过 `euv/Cargo.toml` 的 `[lib] crate-type = ["rlib"]` 暴露给 `euv::*`。

---

## 3. html! 宏

> **底层**：`#[proc_macro] pub fn html(input) -> TokenStream` (macros/src/lib.rs:59)。
> 所有 html! 调用是**编译期宏展开**，生成构造 `VirtualNode` 的 Rust 代码。

### 3.1 元素与属性

```rust
html! { div { class: c_container() h1 { "Hello" } } }

// 字符串属性
html! { input { r#type: "text" placeholder: "Enter name" } }
// Rust 关键字使用 r# 前缀：r#type、r#loop、r#match

// 信号属性
let count: Signal<i32> = App::use_signal(|| 0);
html! { span { count } }                          // 信号属性：自动追踪依赖

// 事件属性（闭包签名 FnMut(Event)）
html! { button { onclick: move |event: Event| { /* handle */ } "Click" } }

// CSS 类属性（多 class 自动合并；`class:` 可重复）
html! { div { class: c_flex_row() class: c_padding() class: c_card() } }

// style 属性（snake_case → kebab-case；多 style 自动合并）
html! { div { style: {display: "flex"; padding: "10px"; font_size: "14px";} } }

// 布尔属性（必须 Signal<bool>）
let agree: Signal<bool> = App::use_signal(|| true);
html! { input { r#type: "checkbox" checked: agree } }

// 自定义属性（data_* → data-*，aria_* → aria-*）
html! { div { data_role: "container" aria_label: "Demo" "Content" } }
```

### 3.2 条件渲染

**响应式 `if`**（用于单分支条件，block-level `else` 不支持）：

```rust
let show: Signal<bool> = App::use_signal(|| true);
html! {
    if { show } { div { "Visible" } }
    // 响应式 if 不允许直接接 `else {}`；用 match 或两个 stacked if
}
```

**响应式 `match`**（必须包含 `_` 通配分支）：

```rust
html! {
    match { route } {
        "/" => { page_home() }
        _ => { page_not_found() }
    }
}
```

**属性值条件**：

```rust
html! { div { class: if { is_active } { c_active() } else { c_inactive() } } }
```

**块级 `if {} { ... } else { ... }` 不支持**——这条是已知 euv macro 限制，必须改成两个 `if {}` 叠加 / `if {} {} else if {} {} else {} {}`（else 用同 if 分隔）/ `match`。详见 `euv-html-macro-traps` skill。

### 3.3 列表渲染

```rust
// for 不是响应式结构，是普通 Rust for 循环
// 迭代表达式两种写法：
for item in { items } { li { item } }    // 带花括号：表达式边界
for item in items { li { item } }         // 不带花括号：循环体 { 作边界
for index in 0..100 { li { format!("Item {}", index + 1) } }

// 带索引
for (index, item) in items.iter().enumerate() { li { span { index } span { item } } }

// 带 key 的列表渲染（启用 keyed diffing）
html! { ul { for item in { items } { li { key: item.id item.name } } } }
```

### 3.4 嵌入表达式

```rust
// 动态表达式 {expr}——自动包装为动态节点
html! { div { {format!("Count: {}", count)} } }
```

### 3.5 自动 .get()（Signal 解包）

**核心 euv 特性**：`html!` 内部的 `{}` 表达式如果是**单段标识符**（bare identifier），**自动调用 `.get()`**：

```rust
let count: Signal<i32> = App::use_signal(|| 0);
html! {
    div {
        span { class: c_counter_value() count }     // 自动 .get() 解包为 i32
    }
}
```

- `{ count }` → `count.auto_value()` → 等价 `count.get()`
- `{ state.value }` → **不会** auto-unwrap（多段路径）→ 显示 `state.value` 字符串而不是值
- `{ signal.iter() }` → 不会 auto-unwrap
- `{ signal == 5 }` → 不会 auto-unwrap

实现位于 `macros/src/html/fn.rs::should_auto_get` —— 检测是否为单个 unqualified identifier，是则注入 `.auto_value()` 调用；其他形式保持原样。

实现细节：`Signal<T>` 提供固有方法 `auto_value(self) -> T`（等价 `self.get()`），`{}` 内的单段标识符会被宏自动加 `.auto_value()`。**不要在 `{}` 里手写 `.get()` + 单段标识符**，会双重 `get()` —— `auto_value()` 已在 macro 层注入。

如果要对多段路径值做 reactive 解包，要么走 `{ state.value.get() }`，要么把单段信号先 `let s = state.value;` 再 `{ s }`（但 `s` 是裸信号的话会 auto-unwrap）。

### 3.6 字符串字面量标签

```rust
html! { "custom-tag" { "Content" } }     // 自定义元素（Custom(&'static str) Tag）
```

`Tag::Custom` 接收任意 `&'static str`，会原样输出到 DOM。浏览器自定义元素（web components）走这条路径。

### 3.7 动态标签

```rust
let tag_kind: Signal<String> = App::use_signal(|| "div".to_owned());
html! { {tag_kind} { "Content" } }
// 等价 <DynamicTag>{ "Content" }</DynamicTag>
```

动态标签走 `DynamicNode`，在 `core/src/vdom/node/struct.rs`。

---

## 4. class! 宏

> **底层**：`#[proc_macro] pub fn class(input) -> TokenStream` (macros/src/lib.rs:84)。
> 一次展开生成：函数 `pub fn c_xxx() -> Css`、`pub fn c_xxx(...) -> Css`、`pub fn c_xxx(...)` 的伪类/媒体查询辅助函数等。

### 4.1 定义 CSS 类

```rust
class! {
    pub struct c_my_button {       // 注意是 struct 关键字（macros/src/class/struct.rs）
        display: flex,
        padding: 12px 16px,
        background: #28a745,
        color: #fff,
        border-radius: 4px,
    }
}
```

展开后：

```rust
pub fn c_my_button() -> Css { Css { /* ... */ } }     // 返回 Css（含 inline style + class name）
```

### 4.2 参数化 CSS 类

```rust
class! {
    pub c_button_bg(color: &str) {
        background: format!("{} {} {}", var!(background), var!(text-primary), color),
    }
}
let style: Css = c_button_bg("#fff");
```

### 4.3 继承（extends）

```rust
class! {
    pub c_my_button {
        background: #28a745,
        color: #fff,
    }
    pub extends c_my_button, c_my_disabled {
        opacity: 0.5,
        cursor: not-allowed,
    }
}
```

`extends` 语义 = **字符串拼接**（参见 `macros/src/class/impl.rs`）：`parent.get_style().to_string() + STR_SPACE + self.props`。同一个属性名靠 **CSS cascade** 后定义胜出来 override；不要用 `extends` 来"重置"父属性。

### 4.4 伪类/伪元素

```rust
class! {
    pub c_input {
        ::placeholder { color: var!(muted-foreground); }
        :hover { border-color: var!(accent); }
        :focus { outline: none; }
    }
}
```

### 4.5 媒体查询

```rust
class! {
    pub c_grid {
        display: grid;
        grid-template-columns: repeat(2, 1fr);
        @media (max-width: 767px) { grid-template-columns: 1fr; }
    }
}
```

### 4.6 动态属性名

属性名可以用 `{expr}` 形式（宏将其 splice 成 key），但**值必须是字符串字面量**——这是 class! CSS DSL 的约束（不是 Rust 表达式）。例如插值颜色值需要走参数化 class（4.2 节）。

### 4.7 样式属性名

snake_case 自动转 kebab-case：`font_size` → `font-size`, `background_color` → `background-color`。

### 4.8 配合 var! 使用

```rust
class! {
    pub c_card {
        background: var!(background);       // var! 宏展开 → "var(--background)"
        color: var!(foreground);
    }
}
```

颜色用 `var!(xxx)` token，**禁止硬编码**（详见 `euv-ui-standards` 第 1 节）。

---

## 5. vars!/var! 宏

> **底层**：`#[proc_macro] pub fn vars(input)` (macros/src/lib.rs:158) + `#[proc_macro] pub fn var(input)` (macros/src/lib.rs:181)。
> 共同职责：在编译期把 tokens 拼成 `"var(--xxx)"`。

```rust
vars! {
    pub c_theme_light {       // 生成 pub fn c_theme_light() 注入器
        bg-primary: "#f8f9fb",
        text-primary: "#1a1a2e",
    }
    pub c_theme_dark {
        bg-primary: "#0f0f1e",
        text-primary: "#e8e8f5",
    }
}

class! {
    pub c_container {
        background: var!(bg-primary);      // 等价 "var(--bg-primary)"
        color: var!(text-primary);
    }
}
```

- `vars! { pub <name> { key: value; ... } }` 展开后是一个 `c_<name>()` 函数，**调用时注入 `<style>` 节点到 `<head>`**。
- `var!(name)` / `var!("name")`（裸 kebab-case 或字符串字面量）展开为字符串 `"var(--name)"`，**用在 class! 或 html! style 表达式里**。
- 命名空间实际由 `vars!` 函数 `pub c_theme_light` 来注入所有 key，因此不同 vars! 块之间的 key 必须互不冲突。

实际项目里 vars! 的名字习惯：`c_theme_light`、`c_theme_dark` 两块 + 同名 key 镜像，运行时根据主题切换调用哪个注入函数。具体见 `ui/src/style/var/fn.rs`。

---

## 6. computed! 宏

> **底层**：`#[proc_macro] pub fn computed(input) -> TokenStream` (macros/src/lib.rs:136)。

`computed!` 把若干信号 + 闭包生成一个**派生 `Signal<T>`** —— 任意依赖变化时自动重算并通知订阅者。**返回类型必须显式标注**（编译期无法推断）。

```rust
computed!(
    celsius: Signal<f64>,
    |celsius_value: f64| -> Signal<f64> {
        let new_fahrenheit: f64 = celsius_value * 9.0 / 5.0 + 32.0;
        // 返回值内部会 wrap 成 Signal<T>
    }
).expect("computed")
```

实际参数形式可能在不同版本间略有差异（也支持 `(celsius, |celsius_value: f64| { ... })` 形式，老版本）。失败用 `.expect("computed celsius->fahrenheit")` / `?` 处理。

---

## 7. watch! 宏

> **底层**：`#[proc_macro] pub fn watch(input) -> TokenStream` (macros/src/lib.rs:109)。

`watch!` 监听一个或多个信号，注册副作用回调。**注意：watch! 不是派生新信号，是 side-effect 触发**。

```rust
let celsius: Signal<f64> = App::use_signal(|| 0.0);
let fahrenheit: Signal<f64> = App::use_signal(|| 32.0);

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

---

## 8. component 属性宏

> **底层**：`#[proc_macro_attribute] pub fn component(_attr, item) -> TokenStream { item }` (macros/src/lib.rs:204)
> **关键事实**：`#[component]` 是 **pass-through marker**，**不生成 wrapper code**！

`#[component]` 唯一作用是标记一个函数让 `html!` 宏编译期扫描源码识别。具体流程：

1. `html!` 在展开时读取 `target/euv_component_registry_cache`（即 `macros/src/html/const.rs::REGISTRY_CACHE_FILE_NAME`）
2. 第一次构建扫描整个 source tree，记录所有 `#[component]` 标注的函数名
3. 后续构建优先读缓存，过期才重新扫描
4. `html!` 在解析 tag name 时查 registry：registry 里有 → 生成组件调用代码；没有 → 当成 `Tag::Custom("xxx")` HTML 元素

```rust
#[derive(Clone, Default, Eq, PartialEq, Hash)]
struct MyCardProps { title: String }

#[component]
pub fn my_card(node: VirtualNode<MyCardProps>) -> VirtualNode {
    let MyCardProps { title, .. } = node.try_get_props().unwrap_or_default();
    let children: VirtualNode = node.get_child_node();
    html! { div { h3 { title } children } }
}

// 使用
html! { my_card { title: "Hello" p { "Content" } } }
```

`#[component]` 标签必需，否则 `html!` 把 `<my_card>` 当成 `<my_card>` HTML 元素（浏览器不识别就吞掉）。

---

## 9. 响应式信号系统

### 9.1 use_signal

```rust
let count: Signal<i32>   = App::use_signal(|| 0);
let visible: Signal<bool> = App::use_signal(|| true);
let text: Signal<String>  = App::use_signal(|| String::new());
```

`App::use_signal<T, F>` where bound：`T: Clone + PartialEq + 'static`, `F: FnOnce() -> T`。**必须在 render fn 体内调用**——它通过当前 `HookContext` 维护 signal identity 跨 re-render；render 外调用没有 hook context 会 panic。

### 9.2 Signal 方法

| 方法                                              | 说明                                                                                            |
| ------------------------------------------------- | ----------------------------------------------------------------------------------------------- |
| `Signal::create(value)`                           | 直接创建（不依赖 HookContext）；`T: Clone + PartialEq + 'static` 必要                           |
| `Signal::default()`                               | 通过 `T::default()` 创建；`T: Default` 额外必要                                                 |
| `Signal<T>::none()`                               | const fn，返回 placeholder（用于 `static SignalCell<T> = SignalCell::none()` 模式）             |
| `Signal::get(&self) -> T`                         | 获取值；动态节点渲染时自动 `add_dependent(dynamic_id)`                                          |
| `Signal::set(&self, value: T)`                    | 设值；值相等（PartialEq）时不触发更新；通过 `Scheduler::update` 标记 dirty 并 schedule dispatch |
| `Signal::subscribe<F>(&self, callback: F)`        | 追加监听器（追加，可多次注册）                                                                  |
| `Signal::replace_listener<F>(&self, callback: F)` | 清空再注册单一回调（pub(crate)）                                                                |
| `Signal::deactivate(&self)`                       | 标记 alive=false，不释放内存（让 stale 闭包仍能安全 get）                                       |

### 9.3 use_cleanup

```rust
App::use_cleanup(move || { /* cleanup side effects */ });
// 清理副作用。FnOnce + 'static 必要；只有首次 render 注册，后续 render 同 hook index 是 no-op。
```

### 9.4 use_window_event

```rust
App::use_window_event("hashchange", move || { /* handle */ });
```

底层通过全局 window 事件代理 registry，多个组件监听同名事件只 1 次 `addEventListener`，清理时只移除 registry entry 不移除共享 listener。事件名 `AsRef<str>`，callback `FnMut() + 'static`。

### 9.5 use_interval

```rust
let handle: IntervalHandle = App::use_interval(1000, move || { /* every second */ });
handle.clear(); // 提前取消
```

`FnMut() + 'static` 必要。返回 `IntervalHandle`，在 hook context teardown 时自动清理（解决手写 `setInterval + Closure::forget()` 的内存泄漏）。

### 9.6 Signal::create（全局信号）

```rust
static GLOBAL_COUNT: SignalCell<i32> = SignalCell::none();

fn init_global_count() {
    let count: Signal<i32> = App::use_signal(|| 0);
    GLOBAL_COUNT.set(count);
}
fn get_global_count() -> Signal<i32> { GLOBAL_COUNT.get() }
```

`SignalCell` 是一个**单参 placeholder**（非 `Signal<T>`），可以 `static` 储存 + `OnceLock`/`set`/`get`。**不要在 render 外用 `Signal::new(value)`**—— `Signal::new` 是 `SignalCell` 的 `new` 而不是 `Signal<T>::create`。

### 9.7 App::batch

```rust
App::batch(|| {
    count.set(1);
    name.set("updated".to_owned());
});
// 批量处理信号更新；闭包内 set 不立即触发 DOM 更新
```

实现：把 `SUPPRESS_SCHEDULE` 设为 true，所有 set 调用只标记 dirty 但不 schedule；最外层 batch 退出时一次性 dispatch。配合 `App::schedule_update(&[deps])`（精确 dirty 标记）使用。

---

## 10. 虚拟 DOM

### VirtualNode 变体

| 变体                                                                           | 说明                                       |
| ------------------------------------------------------------------------------ | ------------------------------------------ |
| `Element { tag: Tag, attrs: Vec<AttributeEntry>, children: Vec<VirtualNode> }` | HTML 元素节点                              |
| `Text(String)`                                                                 | 文本节点                                   |
| `Fragment(Vec<VirtualNode>)`                                                   | 片段节点（无包装元素）                     |
| `Empty`                                                                        | 空占位节点                                 |
| `Component { name: String, props: T, children: Vec<VirtualNode> }`             | 组件节点（`#[component]` 触发）            |
| `Dynamic(DynamicNode)`                                                         | 动态节点（依赖信号变化时整体 re-evaluate） |

`Tag` 枚举（`core/src/vdom/node/enum.rs`）：`Div, Span, P, A, Button, Input, ..., Custom(&'static str)`。`Custom` 走字符串字面量标签（如 web components）。

### mount

```rust
App::mount("#app", app);
// 唯一挂载入口。No `mount_node` / `mount_into` 存在。
// selector 支持 "#id" / ".class" / "tag" 三种 CSS selector 形式
```

`App::mount<S, F>(selector: S, render_fn: F) where S: AsRef<str>, F: FnOnce() -> VirtualNode` —— selector 是 `&str`/`String`/任何 `AsRef<str>`，render_fn 是闭包返回 root VirtualNode。

调用后 `Mount::setup` 把 render fn 用 `box_leak` 永久化 + 设置全局 root dynamic id，开始响应式循环。

---

## 11. 事件系统

```rust
// 内联闭包
html! { button { onclick: move |event: Event| { /* handle */ } "Click" } }

// NativeEventHandler
pub fn counter_on_increment(counter: Signal<i32>) -> NativeEventHandler {
    NativeEventHandler::create("click", move |_event: Event| {
        counter.set(counter.get() + 1);
    })
}

// 事件数据下转型
move |event: Event| {
    if let Some(mouse) = event.dyn_ref::<MouseEvent>() { let x = mouse.client_x(); }
    if let Some(key) = event.dyn_ref::<KeyboardEvent>() { let code = key.code(); }
    if let Some(target) = event.target()
        && let Ok(input) = target.clone().dyn_into::<HtmlInputElement>() {
            input.value()
        }
}
```

`EventAdapter<T>` / `EventNamedAdapter<T>` / `AttrValueAdapter<T>` / `CallbackNamedAdapter<T>` 都是 `core/src/vdom/attribute/struct.rs` 的新类型，让 `FnMut(Event)` / `FnMut()` 等统一持有。

---

## 12. 组件系统

### Props Down / Callback Up

```rust
#[derive(Clone, Default, Eq, Hash, PartialEq)]
struct Props { message: &'static str, onclick: Option<Rc<dyn Fn(Event)>> }

#[component]
pub fn child(node: VirtualNode<Props>) -> VirtualNode {
    let Props { message, onclick, .. } = node.try_get_props().unwrap_or_default();
    html! { button { onclick: onclick message } }
}
```

### 双向绑定（Shared Signal）

```rust
let shared: Signal<String> = App::use_signal(|| "".to_owned());
html! { child_input(shared) }

#[component]
pub fn child_input(text: Signal<String>) -> VirtualNode {
    html! {
        input { value: text.get()
            oninput: move |e: Event| {
                if let Some(t) = e.target()
                    && let Ok(input) = t.clone().dyn_into::<HtmlInputElement>() {
                        text.set(input.value());
                    }
            }
        }
    }
}
```

**重要**：Signal 必须满足 `Clone + PartialEq + 'static` 才能从子组件 prop 传来传去。

---

## 13. 表单处理

```rust
// 文本输入
html! { input { r#type: "text" value: username
    oninput: move |event: Event| {
        if let Some(target) = event.target() && let Ok(input) = target.clone().dyn_into::<HtmlInputElement>() {
            username.set(input.value());
        }
    }
} }

// Checkbox
html! { input { r#type: "checkbox" checked: agree
    onchange: move |event: Event| {
        if let Some(target) = event.target() && let Ok(input) = target.clone().dyn_into::<HtmlInputElement>() {
            agree.set(input.checked());
        }
    }
} }

// Select
html! { select { value: selected
    onchange: move |event: Event| { /* */ }
    option { value: "apple" "Apple" }
} }

// Textarea
html! { textarea { value: content
    oninput: move |event: Event| { /* */ }
} }
```

---

## 14. 异步操作

```rust
use euv::{js_sys::*, wasm_bindgen_futures::*, web_sys::*, *};

let data: Signal<String> = App::use_signal(|| String::new());
App::spawn(async {
    let resp: Response = reqwest::get("https://api.example.com/data").await.unwrap();
    // ...
    data.set("loaded".to_owned());
});
```

`App::spawn` 把 `Future + 'static` 转到 wasm_bindgen_futures 的 `spawn_local`（在 wasm target 上）。

---

## 15. 动画

通过响应式信号切换 CSS 属性值 + `transition` 实现平滑过渡：

```rust
let is_active: Signal<bool> = App::use_signal(|| false);
html! { div {
    style: {opacity: if { is_active.get() } { "1" } else { "0" }; transition: "opacity 0.3s";}
} }
```

euv-ui-standards 提供 `c_anim_fade_in`、`c_anim_spin`、`c_anim_pulse`、`c_anim_scale_box` 等 class（详见 ui-standards 第 3.20 节）。

---

## 16. Keep-Alive

同时渲染所有 Tab 内容（不条件渲染），通过 CSS `display: none/block` 控制可见性，保持 hook 状态存活：

```rust
html! {
    div {
        div { class: if { tab == "info" } { c_active() } else { c_inactive() } "Info Content" }
        div { class: if { tab == "settings" } { c_active() } else { c_inactive() } "Settings Content" }
    }
}
```

注意：`keep_alive` 的实现是"不卸载"，**所有内部 `Signal::create` 只创建一次**，节省重复开销；euv 的 `use_*` hooks 仅在 `[if { ... }]` 分支切换时 teardown。

---

## 17. CLI 工具

`cli/` 子 crate 是一个 `euv` 命名的 CLI，封装 `wasm-pack + hot reload + 端口转发`。命令（来自 `cli/src/lib.rs::pub use {build::*, error::*, fmt::*, logger::*, mode::*, server::*, ...}`）：

| 子命令       | 用途                                         |
| ------------ | -------------------------------------------- |
| `euv build`  | `wasm-pack build --target web --dev/release` |
| `euv fmt`    | `cargo fmt` + Rustfmt 格式化                 |
| `euv server` | 静态文件 server + file watcher 热重载        |
| `euv mode`   | 切换 dev/release 模式                        |

CLI 复用 `hyperlane-cli = "0.1.22"` 作为底层 HTTP server。

详细参数跑 `euv --help`。

---

## Source-of-truth files

**euv 项目源码**：

- `euv/Cargo.toml` — workspace 6 members、`[workspace.dependencies]`、web-sys feature list
- `euv/src/lib.rs` — facade（2 行 `pub use`）
- `euv/core/src/{app,event,reactive,renderer,vdom}/` — 运行时
- `euv/core/src/app/{struct,impl}.rs` — `App` 零尺寸 + 7 个 static fn（mount/use_signal/use_cleanup/use_interval/use_window_event/batch/schedule_update）
- `euv/core/src/reactive/signal/{struct,impl}.rs` — `Signal<T>` + `SignalCell<T>` + `FireHandle`
- `euv/core/src/vdom/node/{enum,struct}.rs` — `VirtualNode`, `Tag`, `TextNode`, `DynamicNode`
- `euv/core/src/vdom/attribute/{struct,enum,impl}.rs` — `Css`, `AttributeValue`, `AttributeEntry`, `EventAdapter`, `inject_css`, `parse_pseudo_rules`, `parse_media_rules`
- `euv/macros/src/lib.rs` — 6 个 `#[proc_macro]` (`html/class/watch/computed/vars/var`) + 1 个 `#[proc_macro_attribute]` (`component`)
- `euv/macros/src/html/{fn,const,enum,impl}.rs` — `html!` parser, auto-get, dynamic tag handling, registry caching（`REGISTRY_CACHE_FILE_NAME = "euv_component_registry_cache"`）
- `euv/macros/src/class/impl.rs` — `class!` implementation，`extends` 字符串拼接语义
- `euv/macros/src/{vars,var,computed,watch}/*.rs` — 对应 4 个 proc-macro 实现
- `euv/ui/src/component/{mod.rs,alert,badge,browser,button,camera,card,checkbox,field,header,info,input,layout,loading,logo,modal,nav,router,tag,theme,touch,vconsole,virtual_list}` — 22 个组件
- `euv/ui/src/style/{class,var,css}/fn.rs` — 304 个 class（`ui/src/style/class/fn.rs`）、vars! 注入器、全局 CSS
- `euv/cli/src/{lib,main}.rs` + `cli/src/{build,fmt,server,mode,logger,error}` — CLI 子命令
- `euv/engine/src/{asset,audio,collider,config,engine,entity,input,math,physics,renderer,scene,scheduler,spatial,sprite}` — 2D/3D 引擎
- `euv/example/src/page/<name>/{view,hook,struct,const,mod}.rs` — 20+ pages

**euv/SKILL.md / euv-standards / euv-ui-standards 共享源点**（与本文档一致）：

- `core/src/lib.rs:6-9` 模块声明：`mod app; mod event; mod reactive; mod renderer; mod vdom;` —— 5 个顶级模块
- `core/src/reactive/{cast,hook,mod,schedule,signal}` —— 5 个 reactive 子模块
- `core/src/vdom/{attribute,cast,mod,node}` —— 4 个 vdom 子模块
- `macros/src/{class,computed,html,ident,lib,var,watch}` —— 7 个 macro 模块
- `ui/src/lib.rs:9 pub use {component::*, style::*}` + `ui/src/component/mod.rs` 22 子模块

## Related skills

- `euv` — 框架总览 + App/Signal/VirtualNode/high-level Quick start
- `euv-ui-standards` — 304 个 class 名表 + 22 个组件 HTML 结构 + 完整 design tokens + 写新 page 标准模板
- `euv-html-macro-traps` — 9 个 macro pitfall（auto-get 单段 vs 多段、if {} else {} 块级 else、for-loop closure 双所有权、c_euv_button force flex 1 1 120px 等）
- `euv-engine-design` — `Engine` 零尺寸 façade contract
- `euv-hook-context-collision` — `HookContext::current()` 全局 thread_local 陷阱
- `euv-app` — example app + Tauri Android 打包
