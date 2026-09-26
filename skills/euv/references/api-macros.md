# euv-macros 完整 proc_macro 签名

Source: `macros/src/lib.rs` — 8 个 proc_macro。

## 完整签名

| proc_macro | 类型 | 签名 |
|---|---|---|
| `html` | `#[proc_macro]` | `pub fn html(input: TokenStream)` |
| `class` | `#[proc_macro]` | `pub fn class(input: TokenStream)` |
| `watch` | `#[proc_macro]` | `pub fn watch(input: TokenStream)` |
| `computed` | `#[proc_macro]` | `pub fn computed(input: TokenStream)` |
| `vars` | `#[proc_macro]` | `pub fn vars(input: TokenStream)` |
| `var` | `#[proc_macro]` | `pub fn var(input: TokenStream)` |
| `unsafe_no_inline` | `#[proc_macro]` | `pub fn unsafe_no_inline(input: TokenStream)` |
| `component` | `#[proc_macro_attribute]` | `pub fn component(_attr: TokenStream, item: TokenStream)` |

## 用法对照

- `html!` — 声明式 UI 节点构造(JSX-like),compile-time 宏展开为 `VirtualNode` 树
- `class!` — 嵌套 CSS class 定义,支持 `@media` / `@keyframes` / `var!(...)` 嵌套
- `vars!` — 全局 CSS custom properties(theme tokens)
- `var!` — class 内引用 `--name` 的语法糖
- `watch!` — 响应式副作用,Signal 变化时执行
- `computed!` — 派生 Signal(其他 Signal 的函数)
- `component` — `#[component]` 属性宏,把函数转为 component + 自动 Props 注入
- `unsafe_no_inline` — 内部宏,避免 `#[inline]` 误用(framework 内部用)
