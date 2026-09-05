---
name: euv-standards
description: '**euv 框架完整 API + 坑表 — 与 euv 框架打交道时必加载**。version '*', edition 2024。涵盖:7 个 crate 布局、`html!`/`class!`/`vars!`/`var!`/`#[component]`/`#[watch]`/`#[computed]` 过程宏真实签名、28 个 euv-ui 组件（带 view/）+ 358 个 design class + 2 个 theme var 集合、Signal/VirtualNode 响应式系统、`App::mount()` 入口。'
---

# euv 框架完整规范 (verified 2026-08)

> ⚠️ **本文所有数字/签名都实地验证自 `/root/github/euv-dev/euv/` 源码。**不要凭训练数据推断。验证方法见末尾。

## 1. Workspace 布局 (7 个 crate)

```
euv/
├── Cargo.toml          # workspace root, members = [...]
├── core/               # euv-core: VirtualNode / Signal / App 核心
├── macros/             # euv-macros: 7 个 proc_macro
├── src/                # euv: re-export = euv_core::* + euv_macros::*
├── ui/                 # euv-ui: 28 组件 + 358 class + 2 theme vars
├── engine/             # euv-engine: 渲染引擎
├── cli/                # euv-cli: CLI 工具
└── example/            # euv-example: 25 个 page 演示
```

依赖关系:`euv` = `euv-core` + `euv-macros`(纯 re-export,无源码)。
任何 euv 项目在 `Cargo.toml` 写 `euv = "0.13"` + `euv-ui = "0.13"` 即可拿到全部能力。

## 2. 7 个过程宏(实地验证自 `macros/src/lib.rs`)

| 宏               | 形态                 | 用途                                                                 |
| ---------------- | -------------------- | -------------------------------------------------------------------- |
| `html! { ... }`  | proc_macro           | JSX 风格虚拟 DOM,产出 `VirtualNode`                                  |
| `class! { ... }` | proc_macro           | CSS class 工具函数集合(编译时展开)                                   |
| `vars! { ... }`  | proc_macro           | 主题 var 集合块,产生 `pub fn c_xxx()` 多个                           |
| `var! { ... }`   | proc_macro           | 单个主题 var(单数)                                                   |
| `watch`          | proc_macro           | 副作用绑定(底层,在 `html!` 内部使用)                                 |
| `computed`       | proc_macro           | 派生 signal(底层)                                                    |
| `#[component]`   | proc_macro_attribute | 标记 `pub fn euv_xxx(node: VirtualNode<EuvXxxProps>) -> VirtualNode` |

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

## 5. `class!` 宏 — 358 个 design class

文件:`ui/src/style/class/fn.rs`(3789 行,单宏调用)。

**形态**:

```rust
class! {
    pub c_euv_button_primary_md { /* CSS */ }
    pub c_euv_button_outline_md { /* CSS */ }
    pub c_card { /* ... */ }
    // ... 共 358 个
}
```

**调用**:在 `html!` 内 `class: c_euv_button_primary_md()`(注意是**函数调用**不是字符串,带空括号)。

**数字验证命令**:

```bash
grep -cE "^[[:space:]]+pub c_" /tmp/euv/ui/src/style/class/fn.rs
# → 358
```

> ❌ 旧版 skill 写"304"/"306",实测 358(0.18.x,含 §3.F 站点组件 + c_euv_* 系列)。**永远以源码为准**。

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

## 7. 28 个 euv-ui 组件(实地列表,`ls -d ui/src/component/*/view`)

```
alert / badge / button / card / checkbox / debug / doc_layout / drawer /
dropdown / field / header / hero / info / input / loading / logo / markdown /
modal / navbar / nav / pagination / result / router / sidebar / tag / toc /
vconsole / virtual_list
```

> 纯 hook 工具组件(无 `view/`,不进 euv_* 渲染树):`browser / camera / layout / theme / touch`。

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

| 坑                                                                                                                                   | 解决                                                                                                                                                                                                                                                                                                                                                                                                 |
| ------------------------------------------------------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `class:` 后忘记 `()`(写成 `c_xxx`)                                                                                                   | **`class!` 宏展开的全是 fn,必须调用**:`c_xxx()`                                                                                                                                                                                                                                                                                                                                                      |
| `onclick: h` 而 `h` 是 `Fn()` 不是 `Fn(Event)`                                                                                       | 事件 handler 一律 `Fn(Event) -> ()`                                                                                                                                                                                                                                                                                                                                                                  |
| `node.get_child_node()` 返回 `Empty`                                                                                                 | 用 `match children { Empty => Text("..."), other => other }` 兜底                                                                                                                                                                                                                                                                                                                                    |
| 写 `<div className="x">` (React 习惯)                                                                                                | euv 是 `class: c_xxx()`,无 className                                                                                                                                                                                                                                                                                                                                                                 |
| 写 `class: "static-string"`                                                                                                          | 编译会过但绕过了 design system,**不推荐**                                                                                                                                                                                                                                                                                                                                                            |
| `Signal` 写 `let s: Signal<i32> = ...;` 然后传值                                                                                     | Signal 必须 clone 或传引用,不能 move                                                                                                                                                                                                                                                                                                                                                                 |
| 在 `class!` 块里写嵌套选择器                                                                                                         | 仅支持伪类/伪元素(`hover`/`before`,拼成 `.c_x:hover`);**后代选择器不支持**,见本条下方专项                                                                                                                                                                                                                                                                                                            |
| 路由刷新丢 state                                                                                                                     | 路由 state 必须在 `App::mount` 之前 `use_signal` 一次                                                                                                                                                                                                                                                                                                                                                |
| `match` 在 `html!` 里大小写写错                                                                                                      | 关键字 `match`(小写),分支用 `=>` 不是 `->`                                                                                                                                                                                                                                                                                                                                                           |
| 给组件加额外字段想放 children                                                                                                        | **错**。children 永远走 `node.get_child_node()`,**不是 props**                                                                                                                                                                                                                                                                                                                                       |
| 在 `class!` 里写后代选择器(`.parent h1`)                                                                                             | **不支持**。element selector block(`h1 { ... }`)序列化时与父类名**直接拼接无空格**(`.c_fooh1`,无效选择器)。需要后代/排版样式时用 `Css::inject_css(raw_css)` 注入原始 CSS(verified 0.14.2,`macros/src/class/fn.rs` flatten_selector_blocks 拼接 + `core` inject_style 无空格)                                                                                                                         |
| `html!` 子位置写 `{ foo(x) }` 带参函数调用                                                                                           | 宏解析报 `expected `,``。在 html! 外预计算 `let node = foo(x);`,然后裸标识符嵌入 `node`                                                                                                                                                                                                                                                                                                              |
| `html!` 里裸文本以 `": "` 结尾(如 `"Page not found: "`)后接 `{ expr }`                                                               | proc macro panic `"..." is not a valid identifier`。合并成单个 `{ format!("Page not found: {x}") }`                                                                                                                                                                                                                                                                                                  |
| `html!` 里 `match prev { ... }`(scrutinee 不带花括号)                                                                                | 报 `expected `,` following match arm`。必须写 `match { expr } { ... }`                                                                                                                                                                                                                                                                                                                               |
| `match { prev }` / `if { active }` 里 prev/active 是 Option/bool 等**非 Signal** 局部变量                                            | 单段标识符在 `{}` 内被自动重写为 `.get()` → `Option`/`bool` 无 `get` 方法编译失败。解法:(a) 条件类名改用函数指针 `let cls: fn() -> &'static Css = if active { c_a } else { c_b };` + `class: cls()`;(b) 或写成多段表达式如 `if { heading.level == 3u8 }`(多 token 不触发 auto-get)                                                                                                                   |
| 给 task list / 条件属性写 `checked: if { c } { "checked" } else { "" }`                                                              | HTML 里 `checked=""` 也算 checked。拆两个分支分别渲染带/不带该属性的元素                                                                                                                                                                                                                                                                                                                             |
| `class!` 里写 `media("(max-width: 767px)") { ... }` 调用形式                                                                         | **静默丢弃**(编译过但生成的 CSS 没有 @media 规则,媒体查询全部失效)。必须用块形式 `@media ((max-width: 767px)) { ... }`(euv-ui 全部 348 个 class 的写法;生成的 CSS 条件就是双层括号,浏览器接受)。排查法:运行时 `document.styleSheets` 里找类名对应的 `@media` 规则是否存在(verified 0.14.3,euv-docs)                                                                                                  |
| 根 `app()` 的 html! 是纯静态树(没有任何 reactive `if`/`match`/`for`)                                                                 | **整个应用的 signal 订阅全部失效**:`Mount::setup` 直接 `render_fn()` 一次,只有 reactive `if`/`match`/`for` 才创建 DynamicNode;signal.get() 读在没有 DynamicNode 的静态子树里不订阅任何节点,路由/主题切换零 DOM 更新。必须镜像官方 example 的根模式:`html! { if { cond_reading_signal } { shell_a {...} } else { shell_b {...} } }`(verified 0.14.3:静态根下 hashchange 事件触发但 docs 组件不重渲染) |
| reactive `if { cond }` 的 cond 是不读 signal 的裸 prop/局部 bool                                                                     | 条件闭包**捕获首次渲染的值**,之后 prop 变了也不更新(如侧边栏在首页隐藏后永远不回来)。cond 里必须直接读 signal:`if { !route_is_home(&route_signal.get()) }`(verified 0.14.3)                                                                                                                                                                                                                          |
| 组件标签上写 `key:`(如 `my_comp { key: x }`)                                                                                         | `key` 被当成 props 字段 → `E0560 struct has no field named key`。要按 key 强制重挂载组件,外面包一层 `div { key: x style: "display: contents" my_comp {...} }`                                                                                                                                                                                                                                        |
| 经历无关的重渲染(如切主题)后,再切路由,页面部分内容变陈旧                                                                             | diff 路径下嵌套 Dynamic 子树可能不刷新。用上面的 keyed `display:contents` 包装强制 remount(verified 0.14.3,euv-docs:切主题 2 次后 en→zh 路由,侧边栏变中文但正文停在英文)                                                                                                                                                                                                                             |
| 文档/长内容布局出现水平溢出(pre/长 inline code 撑破)                                                                                 | flex 链 `min-width: auto` 让内容 min-content 穿透。给 flex 容器逐级补 `min-width: "0px"`(body > main > main_inner > content 整条链)                                                                                                                                                                                                                                                                  |
| 组件 prop 传 `Vec<T>` 后在 reactive `if` 的 html! 块里 `items.iter()`                                                                | **借用逃逸编不过**(FnMut 闭包引用不能逃逸)。`items.into_iter().map(...).collect::<Vec<VirtualNode>>()` 在 html! **外面**构建好,再整体插值;可见性切换用 `class: if { signal } { c_x_open() } else { c_x_closed() }` 常挂载方案(verified 0.15.1,euv_dropdown)                                                                                                                                          |
| reactive `if { open } { ...children... }` 包住 `node.get_child_node()` 的 children                                                   | `E0507`:VirtualNode 非 Copy,不能 move 进 FnMut。同样改常挂载 + 响应式 class(verified 0.15.1,euv_drawer)                                                                                                                                                                                                                                                                                              |
| 非 workspace 项目(crates.io 依赖)里 `euv_button {}` 等组件标签报 `AttrValueAdapter` trait 错                                         | euv < 0.15.2 的 `html!` 组件注册表只扫本 crate + path 依赖;**升 euv ≥ 0.15.2**,注册表会扫 `$CARGO_HOME/registry/src/*/<name>-<version>/src`(无 build.rs 的 crate 缓存落在 `$TMP/euv_registry_<hash>/`)                                                                                                                                                                                               |
| euv 仓** minor 版本升级**(如 0.15.x→0.16.0）后本地 `cargo check` 报 `failed to select a version for the requirement euv = "^0.15.3"` | workspace 内 path-dep 钉了 `^0.15.3`,minor bump 超出区间；patch bump 不受影响。**本地复现 CI `sync_workspace_version` 的 sed 并随 PR 提交**（根 `workspace.dependencies` 各 euv* version + 各 member `package.version`),CI sync 变 no-op；之后 `cargo generate-lockfile` 再验证                                                                                                                      |
| 文档站/长页面切换主题后**一屏以下区域配色不对**（暗色模式下页面底部一大片白）                                                        | `c_app_root` 是 `height: 100%` 的视口锁定 app 壳（example 内部容器滚动）；文档站若是 document 滚动，根元素只有 1 视口高，主题 `background` 到 1 视口高度就断了。两种修法：(a) 根 class 覆盖 `height: "auto"`（保留 `min-height: "100%"`)；(b) **对齐 example：根保持 100%，内容放进 `c_app_main`/`c_mobile_main` 内部滚动容器**（euv-docs PR #9 采用，同时根治）。亮色模式白底看不出，暗色才暴露（verified 0.16.0/0.16.1, euv-docs PR #8/#9)                                                                                                       |
| 文档站壳上的 locale 绑定文本（侧栏树/section label/品牌标题）切换语言后**不更新**，停留在旧语言                                        | 壳组件 mount 时从 route 算 locale，信号变化不会重建组件体（key 加在静态根 div 上也不订阅信号）；`Router::navigate` 异步生效，紧跟 `location.reload()` 会把导航冲掉。正确姿势：`location.set_hash(route)`（同步生效）**再 `location.reload()`**，整页重启按新 locale 重建（i18n 文档站标准行为，verified euv-docs PR #9)                                                                                                       |
| 移动端 header/drawer 顶部间距直接写 `env(safe-area-inset-top)`（无条件信任 env）| **letterbox 浏览器会谎报 env**（VivoBrowser 类报 41px 造成"顶部大片空白"；PWA/沉浸式 WebView env 又是真值必须消费）——静态规则无法区分两种宿主。最终架构（PR #63,0.18.12）：`c_mobile_header`/`c_mobile_nav_drawer` 消费 `var(--euv-mobile-safe-top, 0px)`（**默认 0**，浏览器永远贴顶）；沉浸式宿主显式声明（`window.__EUV_IMMERSIVE__=true` 或 `<meta name="euv-immersive" content="true">`），框架 `UseEuvLayout::use_safe_area_fix` 实测 env 后把变量写到 `<html>`。页面永不直接信任 env()，由知道自己沉浸式的宿主声明（euv-app 注入点 = `src-tauri/src/cache/fn.rs` `on_page_load` → `webview.eval`，euv-app PR #4)                                                                                                                                                                                                                                               |
| **`euv fmt` workspace clean 但 CI `cargo fmt --check` 报 diff** | 两个工具不一致：`euv fmt` 只重排 `class!`/`html!` 宏内部（macro-aware），impl 代码完全交给 `cargo fmt`。**Rust match arm 简单到能放一行时 `cargo fmt` 会压成 `Pattern => expr,` 单行**（PR #101 实际踩坑：原写多行 `Fragment(children) => { ... }` CI 不接受，必须合并成单行）。`euv fmt` 不会主动碰 impl 代码。**实战**：本地写完先用 `euv fmt` 跑一次，再跑 `cargo fmt`（如果装了）或参考最近 PR CI 风格确认 match arm 单行/多行一致性。 |
| **patch tool 自带 rustfmt 报"let chains are only allowed in Rust 2024 or later"假错** | patch tool 自带的 rustfmt 是旧版（< 1.85），不支持 Rust 2024 `let chains` 语法。文件实际是合法的（CI 用 rustc 1.98 全过）。patch tool 输出 `lint.status: error` 不代表代码有问题——只要修改是局部的（patch 工具显示"Pre-existing lint errors — this edit didn't introduce new ones"）就放心提交。 |
| **`match { signal }` arm 切换后，旧 tab 的 page-level `Signal<bool>` 状态幸存 → 切回 tab 时 overlay / 状态错位再现** | `match` arm 切换时 `core/src/renderer/render/impl.rs:914` 走 `render_full_replace`（整 arm DOM 子树销毁重建），但**注册在 page-level `HookContext` 里的 `Signal` 不会随之清除**——`hook_context.switch_arm`（`core/src/reactive/hook/impl.rs:24`）只清 per-arm hooks/cleanups。表现：fullscreen tab A 进入全屏 → `canvas_2d_fullscreen.set(true)`（page-level signal）→ 切到 tab B（A arm DOM 被销毁）→ 切回 A（A arm 重建）→ `c_game_container_fullscreen` overlay 重现，因为 `canvas_2d_fullscreen` signal 仍然是 `true`。**修复模式**：tab 切换处理器里**先复位所有 per-tab state signal 再 `tab.set(value)`**。例：`game_2d_on_tab_select(tab, value, fullscreen)` 在闭包最前面 `fullscreen.get_canvas_2d().set(false); fullscreen.get_web_gl().set(false); fullscreen.get_web_gpu().set(false);` 再 `tab.set(value)`。其他跨 arm 持有的 boolean / enum signal（modal-open、form-state、pending-uploads）同理。诊断：复现切 tab 后残留 UI → 在 `register_popstate_guard`/tab handler 加日志确认 signal 没复位。verified PR #104 (0.18.38)。 |
| **fixed-aspect canvas（800×450 = 16:9）放进全屏容器后，绘制的球/精灵被拉伸成椭圆** | canvas backing buffer 是固定逻辑分辨率（`GAME_2D_CANVAS_WIDTH × GAME_2D_CANVAS_HEIGHT = 800 × 450`）。如果外层 `c_game_container_fullscreen`（`width: 100%; height: 100%; position: fixed`）直接铺满 viewport，再把 `<canvas>` 用 `width: 100%; height: 100%` 嵌进去，浏览器按 viewport 比例（如 1280×800 = 1.6:1）拉伸 16:9 的 bitmap → 球变横向椭圆。**修复：插一层 16:9 letterbox wrapper**——class 必备三件套 `aspect-ratio: "16 / 9"; width: "100%"; max-width: "100%"; max-height: "100%"; height: "auto"; display: "flex"; align-items: "center"; justify-content: "center";`，**外加 `position: "relative"`**（让 `c_game_loading_overlay` 这种 `position: absolute` 的子元素以此为定位锚点，否则会逃逸到 `c_game_container_fullscreen`）。view 里 `<div class: c_letterbox()><canvas class: c_canvas() .../></div>`，原 backing 不变（仍 800×450），浏览器均匀缩放到 letterbox。generic 模式：任何"fixed-aspect bitmap/sprite 嵌入 fluid 容器"都套这个 letterbox 包装。verified PR #104 (0.18.38, euv example game_2d/game_3d 全屏模式)。 |

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
# 组件数(带 view/ 的)
ls -d /tmp/euv/ui/src/component/*/view | wc -l      # → 28(另有 browser/camera/layout/theme/touch 5 个纯 hook 组件无 view/)

# class 数
grep -cE "^[[:space:]]+pub c_" /tmp/euv/ui/src/style/class/fn.rs   # → 358

# vars 数
grep -cE "^[[:space:]]+pub c_" /tmp/euv/ui/src/style/var/fn.rs     # → 2

# 7 个 proc_macro
grep -E "proc_macro" /tmp/euv/macros/src/lib.rs

# 组件带 hook 的列表
find /tmp/euv/ui/src/component -name "hook" -type d

# 32 个 example page
ls /tmp/euv/example/src/page/ | grep -v mod.rs | wc -l
```

每次大版本升级,跑一遍这些命令,数字有变就更新本文档。

## 15. 与其他 skill 关系

- **rust-standards**:同时必加载(任何 Rust 任务)。Rust 代码风格/错误处理/lombok 以它为准。
- **rust-crate-use**:euv 用的第三方 crate(`lombok-macros` / `wasm_bindgen` / `web-sys` / `js-sys`)由它管。
- **euv-ui-standards**:UI 设计规范 + 358 个 class 的具体样式含义(以 §5 实测为准)。
- **euv-pixel-game-scaffold**:用 euv 搭游戏的脚手架(euv 实际能力不止 web,也能做 2D/3D 游戏 —— example 里有 `game_2d` / `game_3d` page)。

## 16. euv-engine WebGPU renderer 真实 API(2026-08 实地补完)

euv-engine 的 `WebGpuRenderer`(在 `engine/src/renderer/impl.rs` 中)是 WebGPU 的 1:1 Rust 包装层,**所有 WebGPU const 名都集中在 `const.rs`,所有方法签名都在 `impl.rs`**。

### 16.1 真实 const 总数与命名约定

`engine/src/renderer/const.rs` 实地有 **300+ `pub(crate) const WEBGPU_*`**,命名规则:

| 前缀                   | 含义           | 例                                              |
| ---------------------- | -------------- | ----------------------------------------------- |
| `WEBGPU_METHOD_*`      | JS 方法名      | `WEBGPU_METHOD_MAP_ASYNC = "mapAsync"`          |
| `WEBGPU_PROPERTY_*`    | 描述符字典 key | `WEBGPU_PROPERTY_BYTES_PER_ROW = "bytesPerRow"` |
| `WEBGPU_MAP_MODE_READ` | u32 数值常量   | `WEBGPU_MAP_MODE_READ: u32 = 1`                 |

**黄金纪律**:**先 `grep` 再加 const** — 99% 你想加的都已经存在,加重复会触发 `E0428 defined multiple times` 雪崩。

```bash
grep -oE "WEBGPU_(PROPERTY|METHOD|MAP_MODE)_[A-Z_]+" \
  /root/projects/euv/engine/src/renderer/const.rs | sort -u
```

### 16.2 WebGpuRenderer 真实方法表(impl.rs)

| 方法                                                                                               | 签名                                                        | 用途                                   |
| -------------------------------------------------------------------------------------------------- | ----------------------------------------------------------- | -------------------------------------- |
| `get_device()`                                                                                     | `&JsValue`                                                  | 拿 `GpuDevice`                         |
| `get_queue()`                                                                                      | `&JsValue`                                                  | 拿 `GpuQueue`                          |
| `get_context()`                                                                                    | `&JsValue`                                                  | 拿 `<canvas>` 上下文                   |
| `create_command_encoder(&self)`                                                                    | `&self -> JsValue`                                          | 命令编码器                             |
| `create_buffer(&self, size, usage)`                                                                | `(u64, u32) -> JsValue`                                     | GPU buffer                             |
| `create_sampler(&self, mag_filter, ...)`                                                           | `(u32, ...) -> JsValue`                                     | 采样器                                 |
| `create_view(&self, texture, Option<&TextureViewDescriptor>)`                                      | `&JsValue -> JsValue`                                       | 纹理视图(本轮补完 descriptor 完整字段) |
| `create_bind_group(&self, layout, &BindGroupDescriptor)`                                           | `&JsValue`                                                  | 绑定组                                 |
| `create_shader_module<S: AsRef<str>>(&self, code: S)`                                              | `JsValue` (预存在,本轮**未**重定义)                         |
| `create_shader_module_with_label(&self, wgsl, label)`                                              | `&str, &str -> JsValue` (本轮新增,带 devtools label)        |
| `create_render_pipeline(&self, wgsl, vs_entry, fs_entry, config)`                                  | `&str, &str, &str, &RenderConfig -> JsValue`                |
| `create_render_pipeline_full(&self, descriptor)`                                                   | `&RenderPipelineFullDescriptor -> JsValue` (本轮补完)       |
| `create_compute_pipeline(&self, wgsl, entry)`                                                      | `&str, &str -> JsValue`                                     |
| `begin_render_pass_full(&self, descriptor)`                                                        | `&RenderPassDescriptor -> JsValue` (本轮补完)               |
| `begin_render_pass_to_texture(&self, texture, color, depth)`                                       | `&JsValue, &Color, Option<&DepthAttachment> -> JsValue`     |
| `begin_compute_pass(&self, descriptor)`                                                            | `Option<&ComputePassDescriptor> -> JsValue`                 |
| `set_pipeline(&self, pass, pipeline)`                                                              | `&JsValue, &JsValue`                                        |
| `set_bind_group(&self, pass, index, group)`                                                        | `&JsValue, u32, &JsValue` (3 参,预存在)                     |
| `set_bind_group_with_dynamic_offsets(&self, pass, index, group, &[u32])`                           | (本轮新增,4 参,渲染通道)                                    |
| `set_bind_group_compute_with_dynamic_offsets(&self, pass, index, group, &[u32])`                   | (本轮新增,4 参,计算通道)                                    |
| `set_vertex_buffer(&self, pass, slot, buffer)`                                                     | `&JsValue, u32, &JsValue`                                   |
| `set_index_buffer(&self, pass, buffer, format)`                                                    | `&JsValue, &JsValue, &str`                                  |
| `set_viewport(&self, pass, x, y, w, h, min_z, max_z)`                                              | (本轮新增)                                                  |
| `set_scissor_rect(&self, pass, x, y, w, h)`                                                        | (本轮新增)                                                  |
| `set_stencil_reference(&self, pass, reference: u32)`                                               | (本轮新增)                                                  |
| `set_blend_constant(&self, pass, r, g, b, a)`                                                      | (本轮新增)                                                  |
| `draw(&self, pass, vertex_count, instance_count, first_vertex, first_instance)`                    | (本轮补完参数)                                              |
| `draw_indexed(&self, pass, index_count, instance_count, first_index, base_vertex, first_instance)` | (本轮补完参数)                                              |
| `draw_indirect(&self, pass, buffer, offset)`                                                       | (本轮补完参数)                                              |
| `draw_indexed_indirect(&self, pass, buffer, offset)`                                               | (本轮补完参数)                                              |
| `dispatch(&self, pass, x, y, z)`                                                                   | 计算 pass 调度                                              |
| `end_render_pass(&self, pass)`                                                                     | `&JsValue`                                                  |
| `finish_command_encoder(&self, encoder)`                                                           | `&JsValue -> JsValue`                                       |
| `submit(&self, &[JsValue])`                                                                        | 命令缓冲提交                                                |
| `copy_texture_to_buffer(&self, src, dst, &Extent3D)`                                               | 纹理→buffer 拷                                              |
| `write_texture(&self, &JsValue queue, &TextureWriteDescriptor, &[u8])`                             | (本轮新增)                                                  |
| `read_buffer(&self, buffer, offset, size) -> Option<Vec<u8>>` (async)                              | **async fn**(本轮新增,不是 sync — 同步会卡死 wasm executor) |
| `generate_mipmaps(&self, texture)`                                                                 | (本轮新增)                                                  |
| `push_error_scope(&self, filter: &str) -> JsValue`                                                 | (本轮新增,错误诊断)                                         |
| `pop_error_scope(&self) -> JsValue`                                                                | (本轮新增,返回 Promise<JsValue>)                            |
| `apply_camera(&self, ...)`                                                                         | 2D 相机                                                     |
| `create_texture_view` / `create_depth_texture` / `create_offline_render_target`                    | 2D 离屏 RT                                                  |
| `create_uniform_buffer` / `create_uniform_bind_group`                                              | 2D 路径快速方法                                             |

### 16.3 描述符结构(struct.rs)

```rust
pub struct TextureViewDescriptor {
    pub format: Option<&'static str>,        // "rgba8unorm" / "depth24plus" / ...
    pub dimension: Option<&'static str>,     // "1d"/"2d"/"2d-array"/"cube"/"cube-array"
    pub aspect: Option<&'static str>,        // "all"/"depth-only"/"stencil-only"
    pub base_mip_level: u32,                 // 0 = default
    pub mip_level_count: u32,                // 0 = default (全 mip)
    pub base_array_layer: u32,
    pub array_layer_count: u32,
}
pub struct TextureWriteDescriptor {
    pub texture: JsValue,                    // **不是 Option** — 必传
    pub mip_level: u32,
    pub origin: Option<JsValue>,             // {x,y,z} 字典
    pub data_layout: JsValue,                // {offset,bytesPerRow,rowsPerImage} 字典
    pub size: JsValue,                       // {width,height,depthOrArrayLayers} 字典
}
```

> ⚠️ Lombok `Getter` 对 `u32` 字段生成 `fn get_x(&self) -> u32`(value,**非** `&u32`),对 `Option<T>` 生成 `fn get_x(&self) -> Option<T>`(value)。**`u32` 字段不要 `*` 解引用**。

### 16.4 坑表(WebGPU 路径)

| 坑                                                         | 解决                                                                                                                    |
| ---------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------- |
| 加 const 触发 `E0428 duplicate`                            | **先 grep `engine/src/renderer/const.rs`,99% 已存在**                                                                   |
| 加方法触发 `E0592 duplicate`                               | **Rust 不支持 method overloading**。改用不同名字(如 `create_shader_module_with_label` 而非 `create_shader_module` 重复) |
| `await` 在 `fn` 里报 `E0728`                               | 改 `async fn`,由调用方 `await`                                                                                          |
| `Reflect::set(&dict, &key, value)` 第三个参数要 `&JsValue` | `Reflect::set` 是 `(&JsValue, &JsValue, &JsValue) -> Result`                                                            |
| `if let Some(x) = d.get_origin()` 让 `x: &JsValue`         | 直接 `&x` 用,不要 `&&JsValue`                                                                                           |
| sync `read_buffer` 卡死 wasm executor                      | 必须 `pub async fn read_buffer`,由 `wasm_bindgen_futures::JsFuture` 驱动                                                |
| `baseMipLevel=0` 触发浏览器报错                            | 0 = default,跳过 set 让浏览器兜底                                                                                       |

### 16.5 验证脚本

```bash
# 真实 const 清单
grep -oE "WEBGPU_(PROPERTY|METHOD|MAP_MODE)_[A-Z_]+" \
  /root/projects/euv/engine/src/renderer/const.rs | sort -u | wc -l

# 真实方法清单
grep -oE "pub fn [a-z_]+" /root/projects/euv/engine/src/renderer/impl.rs | sort -u

# cargo check 0 错
cd /root/projects/euv/engine && cargo check --target wasm32-unknown-unknown
# cargo test 0 fail
cd /root/projects/euv/engine && cargo test
# euv fmt 0 file changed
cd /root/projects/euv && euv fmt
```

## 17. 版本升级规则(用户说「升级版本」时)

euv 仓的 release bump **只改 1 个文件**(verified PR #101 + 2026-09-05 PR #148→#149/#150/#151 re-verified by user):
**根 `Cargo.toml` 第 3 行 `[package] version = "X.Y.Z"`**。**只改一行**。

CI `.github/workflows/rust.yml` 里 `sync_workspace_version` job(`if: github.event_name == 'push' && github.ref_name == 'master'`)在 master merge commit 上**自动 propagate**:
- 6 个子 crate 各自的 `[package] version`(cli/core/engine/example/macros/ui)
- 根 `[workspace.dependencies]` 里 6 个 path-dep 的 `version = "X.Y.Z"`

PR 内 squash 后是 **1 file / +1/-1 diff**,典型。

⚠️ **不要相信 §17 旧版的反向错误叙事**("必须本地手改全部 7 处")。**那个版本错的** — 2026-09-05 user 当场纠正原话："只应该升级根目录的最开头的version,其他的不应该升级,子包也不需要升级版本,流水线会升级"。当时 PR #148 主 agent 改 7 个文件后 user 立刻 reject。正确做法见下。

**推荐脚本**(已验证 PR #101 + PR #151):

```bash
cd /root/github/euv-dev/euv
NEW_VER="0.18.61"
OLD_VER="0.18.60"
# 只改根 Cargo.toml 的 [package] version
sed -i "s/^version = \"$OLD_VER\"$/version = \"$NEW_VER\"/" Cargo.toml
# 验证 git diff --stat 应该只有 1 file +1/-1
git diff --stat
# 期望:Cargo.toml | 2 +-
```

**不要**对 6 个子 crate `Cargo.toml` 或 `[workspace.dependencies]` path-dep 做任何 `sed`。CI 会处理。

**验证清单**(PR commit 之前):
- `git diff --stat` 输出**只有** `Cargo.toml` (根) + 1 line
- 多任何文件 = 停下来,不要 commit,先 `git checkout HEAD -- <extra-file>`

**PR 合并后验证**(CI sync_workspace_version 跑了之后):
- `gh api repos/euv-dev/euv/contents/Cargo.toml --jq .content | base64 -d | grep '^version'`
- 7 个 crate 都是 `X.Y.Z` (根 + 6 子)
- master 出现 `chore: sync all package versions to X.Y.Z` 自动 commit

**若 release PR 误改了 7 个文件**(历史教训,2026-09-05 PR #148):
1. revert PR: `git revert -m 1 <merge_sha>` 在新分支 → PR → merge
2. 重新提交**不含** Cargo.toml 改动的引擎代码 PR(用 `git cherry-pick --no-commit` + `git checkout HEAD -- */Cargo.toml`)
3. 单独提交"只改根"的新 bump PR
4. CI sync 会自动 propagate 0.X 版本给子 crate

**千万不要全局 sed `version = "X.Y.Z"` 在所有子目录**(会误伤第三方依赖版本号,且违反铁律)。

**PR 前必跑**:
- `cargo check -p euv -p euv-core -p euv-engine -p euv-ui -p euv-example --target wasm32-unknown-unknown`(17s)
- `euv fmt`(workspace clean;会顺手改无关注释缩进,带上)
- `wasm-pack build example` + headless chromium 浏览器验证版本号实际渲染到页面

详细版规见 `project-memory` skill 的 Version policy 节。
