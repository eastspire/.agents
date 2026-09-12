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

## 6.4 子文件禁止重复 import 已 re-export 的符号

子文件通过 `use super::*;` 已经拿到父模块 `pub use std::{...}` / `pub use other_crate::xxx;` re-export 的所有符号。**子文件体内(包括函数体)禁止再写 `use std::xxx::yyy;` 重新导入这些符号**——rustc 会报歧义 glob 或 clippy 报 `unused_imports`。

**正确写法**:
```rust
// fn.rs 第一行已经是 use super::*;
// HashMap / HashSet 已经通过 lib.rs 的 pub use std::collections::{...} + super::* 可见
pub(crate) fn compute_plan() {
    let mut map: HashMap<&str, usize> = HashMap::with_capacity(8);
    // ...直接用 HashMap,不需要 use std::collections::HashMap;
}
```

**错误写法**(review reject):
```rust
pub(crate) fn compute_plan() {
    use std::collections::HashMap;  // ❌ 已经在 lib.rs pub use 了
    let mut map: HashMap<&str, usize> = HashMap::with_capacity(8);
}
```

**为何禁止**:
- 重复 import 让读者困惑:HashMap 从哪来?为什么这里需要单独 use?
- 如果 lib.rs 重构删除某个 `pub use std::...`,sub-file 内部的 use 会变成"hard-to-track"依赖,造成隐式耦合。
- clippy `unused_imports` 警告会指出冗余但 reviewer 要先判断"lib.rs 是否真的 re-export 了"——直接禁止更干净。

**判断流程**(写新 sub-file fn 之前):
1. `grep -E '^pub use std' <crate>/src/lib.rs` 看 lib.rs 已 re-export 什么 std 符号。
2. `grep -E '^pub use other_crate' <crate>/src/lib.rs` 看 lib.rs 已 re-export 什么外部 crate 符号。
3. 你需要的符号在以上列表里 → 直接写名字,不需要额外 use。
4. 不在 → **可能应该加到 lib.rs**(如果 sub-file 也需要),或者换一个已经在 re-export 列表里的等价类型。

**例外**:
- `#[cfg(test)] mod tests { use std::time::Instant; }` 如果 `Instant` 没在 lib.rs pub use,且仅测试使用 → OK。
- 子文件**首次**使用某个 std 符号,而该符号尚未被 lib.rs re-export → **应先加到 lib.rs** (`pub use std::time::Instant;`),然后再在 sub-file 用。**不要**在 sub-file 内 `use std::time::Instant;` 直接绕开。
