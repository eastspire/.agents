# 14. 测试策略一致性

## 14.1 测试目录结构

- **单元测试放在项目根目录的 `tests/` 里**,子目录按职责命名(如 `tests/server/`, `tests/route/`),里面文件命名遵守 1.3 节的命名规则(关键字文件 + raw identifier)。
- **`tests/mod.rs` 直接列子模块**(`mod config; mod context; ...`,子模块名不带 `r#`),开头 `use crate_name::*;` 引入被测 crate 的全部公共 API。
- **`tests/<sub>/mod.rs` 极简三段式**(与 src 同样遵守 `mod r#xxx;` + `use super::*;`),但**测试模块内部符号全部私有**,不需要 `pub use`、不需要 `pub(crate) use`(tests/ 是独立 crate)。
- **`tests/<sub>/fn.rs`** 写法:`use super::*;` 开头,然后直接 `#[test] fn test_case() { let value: T = ...; ... assert_eq!(...); }`,每个 `#[test]` 函数独立、互不依赖。
- **测试不需要镜像 src**:tests/ 里只放真正需要测试行为的文件(通常是 `fn.rs`),不必为 src/ 里每个关键字文件都建立对应测试文件。

## 14.2 覆盖率

- 测试覆盖率尽可能高,覆盖边界条件和错误路径。

## 14.3 派生宏生成样板

`#[derive]` 样板字段统一通过项目内的派生宏(参见 references/16-lombok-derives.md)生成 getter/setter / Debug / Display,不要手写 `impl Server { pub fn get_field(&self) -> &Field { &self.field } }`。

## 14.4 单测必须在 `tests/` 目录里;不允许为测试改 API 可见性

**硬性规则**:**所有单测文件必须放在 `<crate>/tests/` 目录下**(子目录按职责命名,如 `tests/renderer/`, `tests/vdom/`),**禁止**以下写法:

```rust
// ❌ 禁止:inline #[cfg(test)] mod tests 在 production file 里
pub(crate) fn compute_plan() -> Vec<Plan> {
    // ... 30 行 production 逻辑 ...
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test] fn plan_handles_disjoint() { ... }
    #[test] fn plan_handles_reorder() { ... }
    // ... 25 个测试
}
```

**禁止理由**:
- `tests/` 目录是独立的 test crate,**编译单元独立**,**运行速度更快**(只 rebuild tests crate 时不必 rebuild lib crate 的 test artifacts)。
- `tests/<sub>/` 是项目惯例,**新加入的 contributor 知道去哪里找测试**。
- `#[cfg(test)] mod tests { ... }` 把测试和 production 混在同一个 file 里,大型 fn file 会膨胀到 1000+ 行,**review diff 难以读**。
- 项目目录的"production/test"边界靠 file path 体现,**不能依赖 `#[cfg(test)]` 编译器 attribute** 作为 boundary marker。

**API 可见性铁律**:**不允许为测试改 API 可见性**。具体含义:

```rust
// ❌ 禁止:为了 integration test 能调到,把 pub(crate) 改成 pub
pub fn compute_plan() -> Vec<Plan> { ... }  // 原本是 pub(crate)

// ❌ 禁止:为了测试,把 private fn 升级成 pub(crate)
pub(crate) fn internal_helper() { ... }  // 原本是 fn
```

**理由**:
- 项目公共 API 是**对外契约**,**测试是内部 consumer**。改可见性让生产 API 表面积变大,**外部用户可能调用到不该调的内部 helper**,破坏封装。
- `pub(crate)` 已经包含整个 crate 的可见性,如果连 crate 内 integration test 都看不到 → 那说明**应该把这个 fn 也搬到 lib.rs 的 `pub use {r#xxx::*}`** 暴露链上,而不是把 visibility 改成 `pub`。
- 私有 helper(默认 `fn`)如果需要被测试访问,正确做法是**让它通过正常的 public API 间接触达**,或者在 production code 增加一个**真正的 public wrapper** 而不是简单改 visibility。

**唯一例外**(master 现有 pattern,记录在 `engine/src/physics/impl.rs:971-975` 注释里):

> "These tests live inline (rather than under `engine/tests/`) because the `physics` module does not yet `pub use r#impl`, so external tests cannot reach methods like `step()` or `apply_torque()`. Once the module is reorganised to expose impls publicly, these can move to an integration test target alongside `input/fn.rs` and `webgpu/fn.rs`."

如果 `tests/<sub>/fn.rs` 内的测试**当前无法访问**任何 `pub(crate)` items(因为所在 module 未 `pub use r#xxx`),**可以临时**用 `#[cfg(test)] mod tests { ... }` inline 在 production file 顶部,但**必须**加这个 master 风格的注释解释"为何暂未搬" + 给出 future refactor 计划。

**新加的 PR 不允许 inline `#[cfg(test)] mod tests`**:必须先通过 `lib.rs` 的 `pub use {r#xxx::*}` 暴露 module,然后写 `tests/<sub>/fn.rs`。

**检测**(每个 PR 改动的 sub-file):
```bash
# 任何 + 行包含 #[cfg(test)] mod tests { 是 violation
git diff -U0 origin/master HEAD -- '*.rs' | grep -E "^\+.*#\[cfg\(test\)\]"
# 期望: 零行(注释 / 文档里的引用不算)

# master 例外 pattern (inline tests with explanatory comment):
git grep -B 3 "fn .*() {" -- '*.rs' | grep "tests live inline"
# 期望: 0..N 行(master 已有 4 处,新 PR 不应再加)
```

**Master 当前 inline `mod tests` 列表**(2026-09-12 检查):
- `engine/src/physics/impl.rs:971` — 解释"physics module 未 pub use r#impl"
- `engine/src/lighting/impl.rs` — 同样模式
- `engine/src/raytracing/impl.rs` — 同样模式
- `core/src/renderer/render/fn.rs` (PR #202 新加) — **没有解释注释**(违规)

**新 PR 要么**:
1. 把测试搬到 `<crate>/tests/<sub>/fn.rs` + 在 lib.rs 加 `pub use r#xxx::*;` 让 module 暴露(推荐路径)。
2. 如果 (1) 不可行(其他约束),用 inline `#[cfg(test)] mod tests` 但**必须**加 master 风格注释解释 + 写明 future refactor 路径。
