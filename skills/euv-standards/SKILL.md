---
name: euv-standards
description: '**euv 框架完整 API + 坑表 — 与 euv 框架打交道时必加载**。版本 0.13.3, edition 2024。涵盖:7 个 crate 布局、`html!`/`class!`/`vars!`/`var!`/`#[component]`/`#[watch]`/`#[computed]` 过程宏真实签名、22 个 euv-ui 组件 + 306 个 design class + 2 个 theme var 集合、Signal/VirtualNode 响应式系统、`App::mount()` 入口。'
---

# euv 框架完整规范 (v0.13.3, verified 2026-08)

> ⚠️ **本文所有数字/签名都实地验证自 `/tmp/euv` 源码。**不要凭训练数据推断。验证方法见末尾。

## 1. Workspace 布局 (7 个 crate)

```
euv/
├── Cargo.toml          # workspace root, members = [...]
├── core/               # euv-core: VirtualNode / Signal / App 核心
├── macros/             # euv-macros: 7 个 proc_macro
├── src/                # euv: re-export = euv_core::* + euv_macros::*
├── ui/                 # euv-ui: 22 组件 + 306 class + 2 theme vars
├── engine/             # euv-engine: 渲染引擎
├── cli/                # euv-cli: CLI 工具
└── example/            # euv-example: 25 个 page 演示
```

依赖关系:`euv` = `euv-core` + `euv-macros`(纯 re-export,无源码)。
任何 euv 项目在 `Cargo.toml` 写 `euv = "0.13"` + `euv-ui = "0.13"` 即可拿到全部能力。

## 2. 7 个过程宏(实地验证自 `macros/src/lib.rs`)

| 宏 | 形态 | 用途 |
|---|---|---|
| `html! { ... }` | proc_macro | JSX 风格虚拟 DOM,产出 `VirtualNode` |
| `class! { ... }` | proc_macro | CSS class 工具函数集合(编译时展开) |
| `vars! { ... }` | proc_macro | 主题 var 集合块,产生 `pub fn c_xxx()` 多个 |
| `var! { ... }` | proc_macro | 单个主题 var(单数) |
| `watch` | proc_macro | 副作用绑定(底层,在 `html!` 内部使用) |
| `computed` | proc_macro | 派生 signal(底层) |
| `#[component]` | proc_macro_attribute | 标记 `pub fn euv_xxx(node: VirtualNode<EuvXxxProps>) -> VirtualNode` |

`html!` 内部实际用到了 `watch` / `computed`(它们由 html! 触发,不直接手写)。

## 3. `#[component]` 组件契约(必须遵守)

每个组件函数都是同一个签名(从 button 实际看到):

```rust
#[component]
pub fn euv_button(node: VirtualNode<EuvButtonProps>) -> VirtualNode {
    let EuvButtonProps { variant, label, onclick, disabled }
        : EuvButtonProps = node.try_get_props().unwrap_or_default();
    let children: VirtualNode = node.get_child_node();
    // ... 用 html! 构造
}
```

**硬性规则**:
1. 函数名必须 `pub fn euv_<lowercase>(node: VirtualNode<Props>) -> VirtualNode`
2. Props 结构体字段名对应 `html!` 里的属性 key
3. **子节点** 通过 `node.get_child_node()` 拿到,不是 Props 字段
4. 解构时一定要 `unwrap_or_default()`,提供 fallback
5. `html!` 内 prop 语法:**冒号 + 空格 + 值**,如 `class: c_xxx()`、`onclick: handler`

## 4. `html!` 宏语法(真实可用的子集)

**元素**:
```rust
html! {
    div { class: c_card() children }
    button { class: c_btn_primary() disabled: true onclick: h }
    img { src: "x.png" alt: "x" }
    input { value: sig.get() placeholder: "..." }
}
```

**控制流(都已验证可用)**:
```rust
html! {
    div {
        if cond { span { "yes" } } else { span { "no" } }
        for x in items.iter() {
            li { {x} }
        }
        match route_signal.get().as_str() {
            "/about" => { page_about {} }
            _ => { page_not_found {} }
        }
    }
}
```

**插值 `{}`**: 任何要嵌入表达式的位置用 `{expr}`,包括 prop 值(`class: {dynamic_class()}`)。

**调用组件**:
```rust
euv_button { variant: EuvButtonVariant::Primary label: "OK" onclick: h }
euv_modal { open: sig children }
```

**裸组件**(`euv_card {}`)和带子节点(`euv_modal { open: sig }  children  `)都可。

## 5. `class!` 宏 — 306 个 design class

文件:`ui/src/style/class/fn.rs`(3338 行,单宏调用)。

**形态**:
```rust
class! {
    pub c_euv_button_primary_md { /* CSS */ }
    pub c_euv_button_outline_md { /* CSS */ }
    pub c_card { /* ... */ }
    // ... 共 306 个
}
```

**调用**:在 `html!` 内 `class: c_euv_button_primary_md()`(注意是**函数调用**不是字符串,带空括号)。

**数字验证命令**:
```bash
grep -cE "^[[:space:]]+pub c_" /tmp/euv/ui/src/style/class/fn.rs
# → 306
```

> ❌ 旧版 skill 写"304",实测 306,差 2。**永远以源码为准**。

## 6. `vars!` / `var!` — 2 个 theme 集合

文件:`ui/src/style/var/fn.rs`,只有 2 个 `pub c_*` 顶层:
- `c_theme_light`(白底黑字)
- `c_theme_dark`(黑底白字)

但每个集合内部有几十个 token,像 `background`、`foreground`、`border`、`accent`、`muted-foreground` 等。

```rust
vars! {
    pub c_theme_light {
        background: "#ffffff";
        foreground: "#000000";
        border: "#000000";
        // ...
    }
    pub c_theme_dark {
        background: "#000000";
        foreground: "#ffffff";
        // ...
    }
}
```

## 7. 22 个 euv-ui 组件(实地列表)

```
alert / badge / browser / button / camera / card / checkbox / field / header /
info / input / layout / loading / logo / modal / nav / router / tag / theme /
touch / vconsole / virtual_list
```

每个组件文件结构(以 button 为例):
```
component/button/
├── mod.rs            # pub use view::*;
└── view/
    ├── mod.rs        # pub use {enum::*, fn::*, struct::*}
    ├── enum.rs       # pub enum EuvButtonVariant { Primary, Outline }
    ├── fn.rs         # #[component] pub fn euv_button(...)
    └── struct.rs     # pub struct EuvButtonProps { ... }
```

带 hook 的组件(9 个)多一层 `hook/`:
- `browser / camera / input / layout / router / theme / touch / vconsole / virtual_list`

**注意区分**:
- `euv_button` ← **库组件**(在 `euv-ui` 里,所有页面共用)
- 自定义组件(如 example 里的 `nav_item`)`pub(crate) fn` + 用 `euv_nav_item { ... }` 包装库组件

## 8. 响应式:Signal + watch + computed

**Signal 创建**(在 App 启动时):
```rust
let count: Signal<i32> = App::use_signal(0);
let (count, set_count) = App::use_signal(0);  // 二元组形式
```

**读**:`count.get()`(返回 `i32`)
**写**:`set_count.set(5)` 或 `count.set(5)`

**派生**:
```rust
let doubled: Signal<i32> = computed! { count.get() * 2 };
```

**副作用**:
```rust
watch! { [count]; /* 当 count 变化时执行 */ };
```

> ⚠️ `watch!` 经常在闭包/条件内需要传 `&[count]` 这种形式,**实际项目里推荐用 `html!` 内的 `for`/`if`/`match` 直接响应**,手动 watch 容易触发死循环。

## 9. App 入口

```rust
use euv::*;

#[wasm_bindgen]
pub fn main() {
    console_error_panic_hook::set_once();
    inject_app_global_css();  // 注入 euv-ui 的全局 CSS
    App::mount("#app", app);
}
```

`App::mount(selector, render_fn)` 签名(实地:`core/src/app/impl.rs`):
```rust
pub fn mount<S, F>(selector: S, render_fn: F)
where S: Into<String>, F: Fn() -> VirtualNode + 'static
```

**`app` 渲染函数约定**:
```rust
pub(crate) fn app() -> VirtualNode {
    html! { /* 根节点 */ }
}
```

## 10. 路由(基于 signal 的极简路由)

`example/src/component/router/view/fn.rs` 实地模式:
```rust
#[component]
pub(crate) fn page_router(node: VirtualNode<PageRouterProps>) -> VirtualNode {
    let PageRouterProps { route_signal } = node.try_get_props().unwrap_or_default();
    html! {
        div { class: c_page_router()
            match { route_signal.get().as_str() } {
                "/" | "/about" => { page_about {} }
                "/animation" => { page_animation {} }
                _ => { page_not_found {} }
            }
        }
    }
}
```

> ⚠️ **没有 React Router 那种 `<Routes>` 声明**。路由就是 `match`,URL 变化由你自己驱动 `route_signal.set(...)`。

## 11. Props 结构体实际样例

```rust
#[derive(Clone, CustomDebug, Default)]
pub struct EuvButtonProps {
    pub variant: EuvButtonVariant,
    pub label: &'static str,
    #[debug(skip)]
    pub onclick: Option<Rc<dyn Fn(Event)>>,
    pub disabled: Signal<bool>,
}
```

要点:
- 必须 `#[derive(Default)]`(因为 `try_get_props().unwrap_or_default()` 兜底)
- 事件 handler 类型:`Option<Rc<dyn Fn(Event)>>`
- 响应式 prop 用 `Signal<T>`,不是裸 `T`
- `#[debug(skip)]` 跳过 `Rc<dyn Fn(...)>`,避免 `Debug` 报错

## 12. 常见坑表(实战踩过)

| 坑 | 解决 |
|---|---|
| `class:` 后忘记 `()`(写成 `c_xxx`) | **`class!` 宏展开的全是 fn,必须调用**:`c_xxx()` |
| `onclick: h` 而 `h` 是 `Fn()` 不是 `Fn(Event)` | 事件 handler 一律 `Fn(Event) -> ()` |
| `node.get_child_node()` 返回 `Empty` | 用 `match children { Empty => Text("..."), other => other }` 兜底 |
| 写 `<div className="x">` (React 习惯) | euv 是 `class: c_xxx()`,无 className |
| 写 `class: "static-string"` | 编译会过但绕过了 design system,**不推荐** |
| `Signal` 写 `let s: Signal<i32> = ...;` 然后传值 | Signal 必须 clone 或传引用,不能 move |
| 在 `class!` 块里写嵌套选择器 | 宏不解析嵌套,**单层** |
| 路由刷新丢 state | 路由 state 必须在 `App::mount` 之前 `use_signal` 一次 |
| `match` 在 `html!` 里大小写写错 | 关键字 `match`(小写),分支用 `=>` 不是 `->` |
| 给组件加额外字段想放 children | **错**。children 永远走 `node.get_child_node()`,**不是 props** |

## 13. 最小可运行模板

```rust
// lib.rs
use euv::*;

#[wasm_bindgen]
pub fn main() {
    console_error_panic_hook::set_once();
    inject_app_global_css();
    App::mount("#app", app);
}

pub fn app() -> VirtualNode {
    let (count, set_count) = App::use_signal(0);
    html! {
        div { class: c_euv_button_primary_md()
            button { onclick: move |_| set_count.set(count.get() + 1)
                { "Count: " } { count.get() }
            }
        }
    }
}
```

## 14. 数字/事实验证脚本(用这个对账)

```bash
# 组件数
ls -d /tmp/euv/ui/src/component/*/ | wc -l          # → 22

# class 数
grep -cE "^[[:space:]]+pub c_" /tmp/euv/ui/src/style/class/fn.rs   # → 306

# vars 数
grep -cE "^[[:space:]]+pub c_" /tmp/euv/ui/src/style/var/fn.rs     # → 2

# 7 个 proc_macro
grep -E "proc_macro" /tmp/euv/macros/src/lib.rs

# 组件带 hook 的列表
find /tmp/euv/ui/src/component -name "hook" -type d

# 25 个 example page
ls /tmp/euv/example/src/page/ | grep -v mod.rs | wc -l
```

每次大版本升级,跑一遍这些命令,数字有变就更新本文档。

## 15. 与其他 skill 关系

- **rust-standards**:同时必加载(任何 Rust 任务)。Rust 代码风格/错误处理/lombok 以它为准。
- **rust-crate-use**:euv 用的第三方 crate(`lombok-macros` / `wasm_bindgen` / `web-sys` / `js-sys`)由它管。
- **euv-ui-standards**:UI 设计规范 + 304 个 class 的具体样式含义(虽然数字 304→306,以本文 306 为准)。
- **euv-pixel-game-scaffold**:用 euv 搭游戏的脚手架(euv 实际能力不止 web,也能做 2D/3D 游戏 —— example 里有 `game_2d` / `game_3d` page)。
