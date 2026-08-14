# 6. 模块导入规则

## 6.1 lib.rs

**只导入整个 crate 全局共用的依赖项**,规范:

- 空行分隔不同类型的导入
- 同类需要聚合(当前 crate / 本地其他 crate / 标准库 / 第三方)
- 按顺序书写导入:
  1. `mod` 声明(普通子模块名)
  2. `pub use`(子模块 glob)
  3. `pub use`(外部 crate glob)
  4. `pub(crate) use`
  5. `pub(super) use`
  6. `use` 私有导入
- 每组按 当前 crate / 标准库 / 外部库 顺序排列

> 完整模板见 `templates/lib-rs.md`

## 6.2 子模块 mod.rs(严格三段式,**无任何注释、无空行分隔**)

1. `mod r#xxx;` 列表(关键字文件用 raw identifier,普通文件用原名)
2. `pub use {r#xxx::*, ...};` 或 `pub use {子模块::*};` 把需要对外暴露的符号 glob 出去;只在本 crate 内可见的符号用 `pub(crate) use {...};`;测试用的 `mod.rs` 通常不需要 `pub use`
3. 末尾独占一行 `use super::*;`(不带分号以外的任何修饰)

> 完整模板(标准/简化/私有/测试 四种)见 `templates/mod-rs.md`

## 6.3 子文件(fn.rs / struct.rs / impl.rs 等)

- **第一行** 必须是 `use super::*;`
  - 例外:`const.rs` 因为只放顶层常量且不需要父模块符号,可省略 `use super::*;`,但项目惯例是也保留
- 后续自由声明,**不允许**出现 `use crate::xxx;`、`use super::具体路径;` 这类长路径导入
- 必须通过 `use super::*;` 间接访问父模块 re-export 的符号(与 `mod.rs` 中的 re-export 配合使用)

> 模板见 `templates/sub-file.md`
