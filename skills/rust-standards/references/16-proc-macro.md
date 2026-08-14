# 16. 过程宏 crate 专属约定(仅 proc-macro crate 适用)

过程宏 crate(`proc-macro = true`)有别于普通 lib crate,需遵守以下额外约束。

## 16.1 lib.rs 是所有宏的注册入口

- 文件开头使用 `//! Crate name //! Description` 顶层 doc comment
- 紧接着 `mod helper;` 列出所有 helper 子模块(**子模块名是普通 snake_case**,不带 `r#`)
- 然后 `use { closed::*, ... };`(`{}` 内**不带 `r#`** 因为子模块不是关键字)一次性把 helper glob 进 `lib.rs`
- 之后才是 `use proc_macro::TokenStream;` 等外部依赖
- 所有 `#[proc_macro_attribute] pub fn attr_macro(...) -> TokenStream { ... }` **必须** 在 `lib.rs` 中实现,**不允许拆到子模块**

## 16.2 helper 子模块的 mod.rs

同样遵守普通 lib crate 的 `mod r#xxx;` + `pub use`/`pub(crate) use` + `use super::*;` 三段式(参见 references/06-module-imports.md)。

## 16.3 依赖方向(避免循环)

- 过程宏 crate 可以依赖对应的 lib crate(`proc-macro = ...` 依赖 `lib-crate = "..."`)
- 反过来 lib crate **不能** 依赖 proc-macro

## 16.4 测试

过程宏 crate 通常不写 `tests/`(因为宏测试通常放在使用宏的 lib crate 的 `tests/` 里做集成测试,或作为宏的 README 示例代码)。
