---
name: euv-standards
description: EUV 框架开发指南。涵盖 html! 宏、class! 宏、computed! 宏、watch! 宏、vars!/var! 宏、component 属性宏的完整使用规范，以及响应式信号系统、虚拟 DOM、事件处理、条件/列表渲染、表单、异步、动画、Keep-Alive、组件绑定、CLI 工具、项目结构等全部 API 的使用方法。触发关键词：euv、Signal、html!、class!、computed!、watch!、vars!、![component]、VirtualNode、use_signal、App::mount、wasm-pack、euv-cli
---

# EUV 框架开发指南

你是一名精通 Rust WebAssembly 前端开发的资深工程师，熟悉 euv 框架的所有 API 和使用规范。你使用中文回复用户，提供的代码示例必须使用正确的 euv API。

## 1. 快速开始

### 1.1 项目初始化

```sh
cargo new my-euv-app
cd my-euv-app
```

`Cargo.toml`：

```toml
[package]
edition = "2024"

[dependencies]
euv = "*"
lombok-macros = "*"

[lib]
crate-type = ["cdylib", "rlib"]
```

### 1.2 入口文件 `src/lib.rs`

```rust
use euv::*;
use wasm_bindgen::prelude::*;

#[wasm_bindgen]
pub fn main() {
    console_error_panic_hook::set_once();
    mount("#app", app);
}

fn app() -> VirtualNode {
    let count: Signal<i32> = use_signal(|| 0);
    html! {
        div {
            h1 { "Hello, euv!" }
            p { "Count: " count }
            button {
                onclick: move |_event: Event| {
                    let current: i32 = count.get();
                    count.set(current + 1);
                }
                "Increment"
            }
        }
    }
}
```

> `use euv::*` 即可访问所有 API，无需单独引入 `web-sys`、`js-sys`、`wasm-bindgen`、`wasm-bindgen-futures`、`console_error_panic_hook`。

### 1.3 HTML 入口 `www/index.html`

```html
<!DOCTYPE html>
<html>
  <head>
    <meta charset="utf-8" />
    <title>My euv App</title>
  </head>
  <body>
    <div id="app"></div>
    <script type="module">
      import init, { main } from './pkg/my_euv_app.js';
      await init();
      main();
    </script>
  </body>
</html>
```

### 1.4 构建与运行

```sh
# 使用 wasm-pack
wasm-pack build --target web --out-dir www/pkg

# 使用 euv 开发服务器（热重载）
cargo install euv-cli
euv run --crate-path . --www-dir ./www --port 80 -- --target web
```

## 2. 项目目录结构

```
├── cli/         # 命令行开发服务器
├── core/        # 核心逻辑（app、event、reactive、renderer、router、vdom）
├── macros/      # 过程宏（class、computed、html、ident、var、watch）
├── example/     # 示例 SPA（路由、布局、导航、各功能页面）
├── ui/          # UI 组件库
├── www/         # Web 发布目录
```

## 3. html! 宏

### 3.1 元素与属性

```rust
html! { div { class: c_container() h1 { "Hello" } } }

// 字符串属性
html! { input { r#type: "text" placeholder: "Enter name" } }
// Rust 关键字使用 r# 前缀：r#type、r#loop、r#match

// 信号属性
let count: Signal<i32> = App::use_signal(|| 0);
html! { span { count } }

// 事件属性（闭包签名 FnMut(Event)）
html! { button { onclick: move |event: Event| { /* handle */ } "Click" } }

// CSS 类属性
html! { div { class: c_container() "Content" } }
// 多 class 自动合并
html! { div { class: c_flex_row() class: c_padding() class: c_card() } }

// style 属性（snake_case → kebab-case）
html! { div { style: {display: "flex"; padding: "10px"; font_size: "14px";} } }

// 多 style 自动合并
html! { div { style: {display: "flex"; gap: "10px";} style: {padding: "20px";} } }

// 布尔属性（必须 Signal<bool>）
let agree: Signal<bool> = App::use_signal(|| true);
html! { input { r#type: "checkbox" checked: agree } }

// 自定义属性（data_* → data-*，aria_* → aria-*）
html! { div { data_role: "container" aria_label: "Demo" "Content" } }
```

### 3.2 条件渲染

```rust
// 响应式 if——条件用 {} 包裹，信号变化时自动重新求值
let show: Signal<bool> = App::use_signal(|| true);
html! {
    if { show.get() } { div { "Visible" } } else { "" }
}
// 响应式 if 的 else 分支不能省略

// 内联 if——条件直接写，在父级渲染时一次性求值，适合 for 循环内
html! {
    ul { for item in items.get() {
        if item.len() > 5 { li { "Long" } } else { li { "Short" } }
    } }
}

// 响应式 match
html! {
    match { route.get().as_str() } {
        "/" => { page_home() }
        _ => { page_not_found() }
    }
}
// match 必须包含 _ 通配分支

// 属性值条件渲染
html! { div { class: if { is_active.get() } { c_active() } else { c_inactive() } } }
```

### 3.3 列表渲染

```rust
// for 本身不是响应式结构，是一个普通 Rust for 循环，在父级渲染时运行
// 迭代表达式支持两种写法（功能完全等价）：
// 带花括号 {expr}：花括号作为表达式边界
for item in { items.get() } { li { item } }
// 不带花括号 expr：宏直接解析，以循环体 { 为边界
for item in items.get() { li { item } }
for index in 0..100 { li { format!("Item {}", index + 1) } }

// 带索引
for (index, item) in items.get().iter().enumerate() { li { span { index } span { item } } }

// 带 key 的列表渲染（启用 Keyed Diffing）
html! { ul { for item in { items.get() } { li { key: item.id item.name } } } }
```

### 3.4 嵌入表达式

```rust
// 动态表达式 {expr}——自动包装为动态节点，响应式
html! { div { {format!("Count: {}", count.get())} } }

// 静态表达式（裸标识符）——一次性转换，非响应式
html! { div { count } }
```

### 3.5 字符串字面量标签

```rust
// 用于 Web Components，始终为 Tag::Element
html! { "my-custom-element" { class: c_container() "Content" } }
```

### 3.6 动态标签

```rust
let tag_name: Signal<String> = App::use_signal(|| "div".to_string());
html! { { tag_name.get() } { "Dynamic tag content" } }
```

## 4. class! 宏

### 4.1 定义 CSS 类

```rust
class! {
    pub container { max_width: "800px"; margin: "0 auto"; }
    pub(crate) header { font_size: "28px"; }
    hidden { display: "none"; }
}
```

### 4.2 参数化 CSS 类

```rust
class! {
    pub dynamic_color(color: &str) {
        color: {color};
        padding: "8px 16px";
    }
}
```

### 4.3 继承（extends）

```rust
class! {
    pub c_base { padding: "8px 16px"; border_radius: "4px"; }
    pub c_primary_button {
        c_base();        // 继承样式属性、伪类规则和媒体查询规则
        cursor: "pointer";
        hover { background: "#4338ca"; } // 可覆盖继承的伪类
    }
}
```

### 4.4 伪类/伪元素

```rust
class! {
    pub c_button {
        padding: "10px 20px"; background: "#4f46e5";
        hover { background: "#4338ca"; }
        focus { outline: "2px solid #818cf8"; }
        before { content: "\"→\""; }
        nth_child(2n+1) { background: "rgba(0,0,0,0.05)"; }
    }
}
```

### 4.5 媒体查询

```rust
class! {
    pub c_responsive {
        padding: "20px";
        media("(max-width: 768px)") { padding: "12px"; font_size: "14px"; }
    }
}
```

### 4.6 动态属性名

```rust
class! {
    pub c_dynamic(key: &str, value: &str) {
        {key}: {value};
        padding: "8px 16px";
    }
}
```

### 4.7 样式属性名

使用 snake_case，自动转换为 kebab-case：`font_size` → `font-size`，`align_items` → `align-items`。

### 4.8 配合 var! 使用

```rust
class! { pub c_container {
    background: var!(bg-primary);
    border: format!("1px solid {}", var!(border-color));
} }
```

## 5. vars!/var! 宏

```rust
// 定义 CSS 变量
vars! {
    pub c_theme_light { bg-primary: "#f8f9fb"; text-primary: "#1a1a2e"; }
}

// 引用 CSS 变量
var!(bg-primary)   // → "var(--bg-primary)"
var!("bg-primary") // → "var(--bg-primary)"

// 在 class! 中使用
class! { pub c_container { background: var!(bg-primary); } }

// 在 format! 中使用
class! { pub c_nav { border-right: format!("1px solid {}", var!(glass-border)); } }
```

## 6. computed! 宏

监听一个或多个信号，派生新的响应式值。返回 `Signal<T>`，返回类型必须显式标注。

```rust
let full_name: Signal<String> = computed!(first_name, last_name, |first: String, last: String| -> String {
    format!("{} {}", first, last)
});

// 匿名参数
computed!(counter, timer, |count: i32, _: f64| -> String { format!("Count: {}", count) });
```

## 7. watch! 宏

监听信号变化执行副作用，创建时立即执行一次。适用于日志、网络请求、手动同步。

```rust
let count: Signal<i32> = App::use_signal(|| 0);
watch!(count, |count_val: i32| {
    web_sys::console::log_1(&format!("Count: {}", count_val).into());
});

// 匿名参数
watch!(timer, count, |_, count_val: i32| { /* handle */ });
watch!(timer, |_: f64| { /* ignore value */ });
```

## 8. component 属性宏

```rust
#[derive(Clone, Default)]
struct MyCardProps { title: &'static str }

#[component]  // 必须标记，html! 宏才能识别
pub fn my_card(node: VirtualNode<MyCardProps>) -> VirtualNode {
    let MyCardProps { title, .. } = node.try_get_props().unwrap_or_default();
    let children: VirtualNode = node.get_child_node();
    html! { div { h3 { title } children } }
}

// 使用
html! { my_card { title: "Hello" p { "Content" } } }
```

## 9. 响应式信号系统

### 9.1 use_signal

```rust
let count: Signal<i32> = App::use_signal(|| 0);
let visible: Signal<bool> = App::use_signal(|| true);
```

### 9.2 Signal 方法

| 方法                         | 说明                                     |
| ---------------------------- | ---------------------------------------- |
| `Signal::create(value)`      | 直接创建，不依赖 HookContext             |
| `Signal::default()`          | 使用 T::default() 创建                   |
| `get(&self) -> T`            | 获取值（在动态节点内调用时自动追踪依赖） |
| `set(&self, value)`          | 设置值，值相同不触发更新                 |
| `subscribe(&self, callback)` | 追加监听器                               |

### 9.3 use_cleanup

```rust
App::use_cleanup(move || { /* 清理副作用 */ });
```

### 9.4 use_window_event

```rust
App::use_window_event("hashchange", move || { /* handle */ });
```

### 9.5 use_interval

```rust
let handle: IntervalHandle = App::use_interval(1000, move || { /* every second */ });
handle.clear(); // 提前取消
```

### 9.6 Signal::create（全局信号）

```rust
static GLOBAL_COUNT: SignalCell<i32> = SignalCell::none();
fn init_global_count() {
    let count: Signal<i32> = App::use_signal(|| 0);
    GLOBAL_COUNT.set(count);
}
fn get_global_count() -> Signal<i32> { GLOBAL_COUNT.get() }
```

### 9.7 App::batch

批量处理信号更新，闭包内的 set 不会触发即时 DOM 更新。

```rust
App::batch(|| {
    count.set(1);
    name.set("updated".to_string());
});
```

## 10. 虚拟 DOM

### VirtualNode 变体

| 变体       | 说明                             |
| ---------- | -------------------------------- |
| `Element`  | HTML 元素节点                    |
| `Text`     | 文本节点                         |
| `Fragment` | 片段节点，无包装元素             |
| `Dynamic`  | 动态节点，信号变化时自动重新渲染 |
| `Empty`    | 空占位节点                       |

### mount

```rust
App::mount("#app", app); // 挂载到选择器匹配的元素
App::mount_node("app", app); // 直接挂载到 DOM 元素 ID

// 嵌入到已存在节点中（不替换已有内容）
App::mount_into("#app", footer);
```

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

## 12. 组件系统

### Props Down / Callback Up

```rust
#[derive(Clone, Default)]
struct Props { message: &'static str, onclick: Option<Rc<dyn Fn(Event)>> }

#[component]
pub fn child(node: VirtualNode<Props>) -> VirtualNode {
    let Props { message, onclick, .. } = node.try_get_props().unwrap_or_default();
    html! { button { onclick: onclick message } }
}
```

### 双向绑定（Shared Signal）

```rust
let shared: Signal<String> = App::use_signal(|| "".to_string());
html! { child_input(shared) }
pub fn child_input(text: Signal<String>) -> VirtualNode {
    html! { input { value: text.get() oninput: move |e: Event| { /* set */ } } }
}
```

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
    onchange: move |event: Event| { /* handle */ }
    option { value: "apple" "Apple" }
} }

// Textarea
html! { textarea { value: content
    oninput: move |event: Event| { /* handle */ }
} }
```

## 14. 异步操作

```rust
use euv::{js_sys::*, wasm_bindgen_futures::*, web_sys::*, *};

let data: Signal<String> = App::use_signal(|| "".to_string());
App::spawn(async {
    let resp = reqwest::get("https://api.example.com/data").await;
    // ...
});
```

## 15. 动画

通过响应式信号切换 CSS 属性值 + `transition` 实现平滑过渡。

```rust
let is_active: Signal<bool> = App::use_signal(|| false);
html! { div {
    style: {opacity: if { is_active.get() } { "1" } else { "0" }; transition: "opacity 0.3s";}
} }
```

## 16. Keep-Alive

同时渲染所有 Tab 内容（不条件渲染），通过 CSS `display: none/block` 控制可见性，保持 Hook 状态存活。

```rust
html! {
    div {
        div { class: if { tab == "info" } { c_active() } else { c_inactive() } "Info Content" }
        div { class: if { tab == "settings" } { c_active() } else { c_inactive() } "Settings Content" }
    }
}
```

## 17. CLI 工具

```sh
cargo install euv-cli  # 安装，包名 euv-cli，可执行文件 euv

euv new <project>                              # 创建新项目
euv run --crate-path . --www-dir ./www         # 启动开发服务器（热重载）
euv build --crate-path . --www-dir ./www       # 构建
euv fmt --crate-path .                         # 格式化
euv publish                                   # 发布
```
