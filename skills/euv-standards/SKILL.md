---
name: euv-standards
description: '**euv 框架完整 API + 坑表 — 与 euv 框架打交道时必加载**。version '*', edition 2024。涵盖:7 个 crate 布局、`html!`/`class!`/`vars!`/`var!`/`#[component]`/`#[watch]`/`#[computed]` 过程宏真实签名、22 个 euv-ui 组件 + 306 个 design class + 2 个 theme var 集合、Signal/VirtualNode 响应式系统、`App::mount()` 入口。'
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
| 在 `class!` 块里写嵌套选择器 | 仅支持伪类/伪元素(`hover`/`before`,拼成 `.c_x:hover`);**后代选择器不支持**,见本条下方专项 |
| 路由刷新丢 state | 路由 state 必须在 `App::mount` 之前 `use_signal` 一次 |
| `match` 在 `html!` 里大小写写错 | 关键字 `match`(小写),分支用 `=>` 不是 `->` |
| 给组件加额外字段想放 children | **错**。children 永远走 `node.get_child_node()`,**不是 props** |
| 在 `class!` 里写后代选择器(`.parent h1`) | **不支持**。element selector block(`h1 { ... }`)序列化时与父类名**直接拼接无空格**(`.c_fooh1`,无效选择器)。需要后代/排版样式时用 `Css::inject_css(raw_css)` 注入原始 CSS(verified 0.14.2,`macros/src/class/fn.rs` flatten_selector_blocks 拼接 + `core` inject_style 无空格) |
| `html!` 子位置写 `{ foo(x) }` 带参函数调用 | 宏解析报 `expected `,``。在 html! 外预计算 `let node = foo(x);`,然后裸标识符嵌入 `node` |
| `html!` 里裸文本以 `": "` 结尾(如 `"Page not found: "`)后接 `{ expr }` | proc macro panic `"..." is not a valid identifier`。合并成单个 `{ format!("Page not found: {x}") }` |
| `html!` 里 `match prev { ... }`(scrutinee 不带花括号) | 报 `expected `,` following match arm`。必须写 `match { expr } { ... }` |
| `match { prev }` / `if { active }` 里 prev/active 是 Option/bool 等**非 Signal** 局部变量 | 单段标识符在 `{}` 内被自动重写为 `.get()` → `Option`/`bool` 无 `get` 方法编译失败。解法:(a) 条件类名改用函数指针 `let cls: fn() -> &'static Css = if active { c_a } else { c_b };` + `class: cls()`;(b) 或写成多段表达式如 `if { heading.level == 3u8 }`(多 token 不触发 auto-get) |
| 给 task list / 条件属性写 `checked: if { c } { "checked" } else { "" }` | HTML 里 `checked=""` 也算 checked。拆两个分支分别渲染带/不带该属性的元素 |
| `class!` 里写 `media("(max-width: 767px)") { ... }` 调用形式 | **静默丢弃**(编译过但生成的 CSS 没有 @media 规则,媒体查询全部失效)。必须用块形式 `@media ((max-width: 767px)) { ... }`(euv-ui 全部 306 个 class 的写法;生成的 CSS 条件就是双层括号,浏览器接受)。排查法:运行时 `document.styleSheets` 里找类名对应的 `@media` 规则是否存在(verified 0.14.3,euv-docs) |
| 根 `app()` 的 html! 是纯静态树(没有任何 reactive `if`/`match`/`for`) | **整个应用的 signal 订阅全部失效**:`Mount::setup` 直接 `render_fn()` 一次,只有 reactive `if`/`match`/`for` 才创建 DynamicNode;signal.get() 读在没有 DynamicNode 的静态子树里不订阅任何节点,路由/主题切换零 DOM 更新。必须镜像官方 example 的根模式:`html! { if { cond_reading_signal } { shell_a {...} } else { shell_b {...} } }`(verified 0.14.3:静态根下 hashchange 事件触发但 docs 组件不重渲染) |
| reactive `if { cond }` 的 cond 是不读 signal 的裸 prop/局部 bool | 条件闭包**捕获首次渲染的值**,之后 prop 变了也不更新(如侧边栏在首页隐藏后永远不回来)。cond 里必须直接读 signal:`if { !route_is_home(&route_signal.get()) }`(verified 0.14.3) |
| 组件标签上写 `key:`(如 `my_comp { key: x }`) | `key` 被当成 props 字段 → `E0560 struct has no field named key`。要按 key 强制重挂载组件,外面包一层 `div { key: x style: "display: contents" my_comp {...} }` |
| 经历无关的重渲染(如切主题)后,再切路由,页面部分内容变陈旧 | diff 路径下嵌套 Dynamic 子树可能不刷新。用上面的 keyed `display:contents` 包装强制 remount(verified 0.14.3,euv-docs:切主题 2 次后 en→zh 路由,侧边栏变中文但正文停在英文) |
| 文档/长内容布局出现水平溢出(pre/长 inline code 撑破) | flex 链 `min-width: auto` 让内容 min-content 穿透。给 flex 容器逐级补 `min-width: "0px"`(body > main > main_inner > content 整条链) |

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

## 16. euv-engine WebGPU renderer 真实 API(2026-08 实地补完)

euv-engine 的 `WebGpuRenderer`(在 `engine/src/renderer/impl.rs` 中)是 WebGPU 的 1:1 Rust 包装层,**所有 WebGPU const 名都集中在 `const.rs`,所有方法签名都在 `impl.rs`**。

### 16.1 真实 const 总数与命名约定

`engine/src/renderer/const.rs` 实地有 **300+ `pub(crate) const WEBGPU_*`**,命名规则:

| 前缀 | 含义 | 例 |
|---|---|---|
| `WEBGPU_METHOD_*` | JS 方法名 | `WEBGPU_METHOD_MAP_ASYNC = "mapAsync"` |
| `WEBGPU_PROPERTY_*` | 描述符字典 key | `WEBGPU_PROPERTY_BYTES_PER_ROW = "bytesPerRow"` |
| `WEBGPU_MAP_MODE_READ` | u32 数值常量 | `WEBGPU_MAP_MODE_READ: u32 = 1` |

**黄金纪律**:**先 `grep` 再加 const** — 99% 你想加的都已经存在,加重复会触发 `E0428 defined multiple times` 雪崩。

```bash
grep -oE "WEBGPU_(PROPERTY|METHOD|MAP_MODE)_[A-Z_]+" \
  /root/projects/euv/engine/src/renderer/const.rs | sort -u
```

### 16.2 WebGpuRenderer 真实方法表(impl.rs)

| 方法 | 签名 | 用途 |
|---|---|---|
| `get_device()` | `&JsValue` | 拿 `GpuDevice` |
| `get_queue()` | `&JsValue` | 拿 `GpuQueue` |
| `get_context()` | `&JsValue` | 拿 `<canvas>` 上下文 |
| `create_command_encoder(&self)` | `&self -> JsValue` | 命令编码器 |
| `create_buffer(&self, size, usage)` | `(u64, u32) -> JsValue` | GPU buffer |
| `create_sampler(&self, mag_filter, ...)` | `(u32, ...) -> JsValue` | 采样器 |
| `create_view(&self, texture, Option<&TextureViewDescriptor>)` | `&JsValue -> JsValue` | 纹理视图(本轮补完 descriptor 完整字段) |
| `create_bind_group(&self, layout, &BindGroupDescriptor)` | `&JsValue` | 绑定组 |
| `create_shader_module<S: AsRef<str>>(&self, code: S)` | `JsValue` (预存在,本轮**未**重定义) |
| `create_shader_module_with_label(&self, wgsl, label)` | `&str, &str -> JsValue` (本轮新增,带 devtools label) |
| `create_render_pipeline(&self, wgsl, vs_entry, fs_entry, config)` | `&str, &str, &str, &RenderConfig -> JsValue` |
| `create_render_pipeline_full(&self, descriptor)` | `&RenderPipelineFullDescriptor -> JsValue` (本轮补完) |
| `create_compute_pipeline(&self, wgsl, entry)` | `&str, &str -> JsValue` |
| `begin_render_pass_full(&self, descriptor)` | `&RenderPassDescriptor -> JsValue` (本轮补完) |
| `begin_render_pass_to_texture(&self, texture, color, depth)` | `&JsValue, &Color, Option<&DepthAttachment> -> JsValue` |
| `begin_compute_pass(&self, descriptor)` | `Option<&ComputePassDescriptor> -> JsValue` |
| `set_pipeline(&self, pass, pipeline)` | `&JsValue, &JsValue` |
| `set_bind_group(&self, pass, index, group)` | `&JsValue, u32, &JsValue` (3 参,预存在) |
| `set_bind_group_with_dynamic_offsets(&self, pass, index, group, &[u32])` | (本轮新增,4 参,渲染通道) |
| `set_bind_group_compute_with_dynamic_offsets(&self, pass, index, group, &[u32])` | (本轮新增,4 参,计算通道) |
| `set_vertex_buffer(&self, pass, slot, buffer)` | `&JsValue, u32, &JsValue` |
| `set_index_buffer(&self, pass, buffer, format)` | `&JsValue, &JsValue, &str` |
| `set_viewport(&self, pass, x, y, w, h, min_z, max_z)` | (本轮新增) |
| `set_scissor_rect(&self, pass, x, y, w, h)` | (本轮新增) |
| `set_stencil_reference(&self, pass, reference: u32)` | (本轮新增) |
| `set_blend_constant(&self, pass, r, g, b, a)` | (本轮新增) |
| `draw(&self, pass, vertex_count, instance_count, first_vertex, first_instance)` | (本轮补完参数) |
| `draw_indexed(&self, pass, index_count, instance_count, first_index, base_vertex, first_instance)` | (本轮补完参数) |
| `draw_indirect(&self, pass, buffer, offset)` | (本轮补完参数) |
| `draw_indexed_indirect(&self, pass, buffer, offset)` | (本轮补完参数) |
| `dispatch(&self, pass, x, y, z)` | 计算 pass 调度 |
| `end_render_pass(&self, pass)` | `&JsValue` |
| `finish_command_encoder(&self, encoder)` | `&JsValue -> JsValue` |
| `submit(&self, &[JsValue])` | 命令缓冲提交 |
| `copy_texture_to_buffer(&self, src, dst, &Extent3D)` | 纹理→buffer 拷 |
| `write_texture(&self, &JsValue queue, &TextureWriteDescriptor, &[u8])` | (本轮新增) |
| `read_buffer(&self, buffer, offset, size) -> Option<Vec<u8>>` (async) | **async fn**(本轮新增,不是 sync — 同步会卡死 wasm executor) |
| `generate_mipmaps(&self, texture)` | (本轮新增) |
| `push_error_scope(&self, filter: &str) -> JsValue` | (本轮新增,错误诊断) |
| `pop_error_scope(&self) -> JsValue` | (本轮新增,返回 Promise<JsValue>) |
| `apply_camera(&self, ...)` | 2D 相机 |
| `create_texture_view` / `create_depth_texture` / `create_offline_render_target` | 2D 离屏 RT |
| `create_uniform_buffer` / `create_uniform_bind_group` | 2D 路径快速方法 |

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

| 坑 | 解决 |
|---|---|
| 加 const 触发 `E0428 duplicate` | **先 grep `engine/src/renderer/const.rs`,99% 已存在** |
| 加方法触发 `E0592 duplicate` | **Rust 不支持 method overloading**。改用不同名字(如 `create_shader_module_with_label` 而非 `create_shader_module` 重复) |
| `await` 在 `fn` 里报 `E0728` | 改 `async fn`,由调用方 `await` |
| `Reflect::set(&dict, &key, value)` 第三个参数要 `&JsValue` | `Reflect::set` 是 `(&JsValue, &JsValue, &JsValue) -> Result` |
| `if let Some(x) = d.get_origin()` 让 `x: &JsValue` | 直接 `&x` 用,不要 `&&JsValue` |
| sync `read_buffer` 卡死 wasm executor | 必须 `pub async fn read_buffer`,由 `wasm_bindgen_futures::JsFuture` 驱动 |
| `baseMipLevel=0` 触发浏览器报错 | 0 = default,跳过 set 让浏览器兜底 |

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
