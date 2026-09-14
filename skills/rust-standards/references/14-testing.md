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

## 14.4 单测必须在 `tests/` 目录里;**绝对禁止**为测试改 API 可见性

### 默认形态:integration test under `tests/`

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

**默认理由**:
- `tests/` 目录是独立的 test crate,**编译单元独立**,**运行速度更快**(只 rebuild tests crate 时不必 rebuild lib crate 的 test artifacts)。
- `tests/<sub>/` 是项目惯例,**新加入的 contributor 知道去哪里找测试**。
- `#[cfg(test)] mod tests { ... }` 把测试和 production 混在同一个 file 里,大型 fn file 会膨胀到 1000+ 行,**review diff 难以读**。
- 项目目录的"production/test"边界靠 file path 体现,**不能依赖 `#[cfg(test)]` 编译器 attribute** 作为 boundary marker。

### API 可见性铁律(2026-09-12 user 明确):**绝对禁止为测试改 visibility**

具体含义:

```rust
// ❌ 禁止:为了 integration test 能调到,把 pub(crate) 改成 pub
pub fn compute_plan() -> Vec<Plan> { ... }  // 原本是 pub(crate)

// ❌ 禁止:为了 tests/ 能 import,在 lib.rs 加 pub use re-export
pub use renderer::render::compute_plan;     // 原本没有这条

// ❌ 禁止:为了测试,把 private fn 升级成 pub(crate) 或 pub
pub(crate) fn internal_helper() { ... }  // 原本是 fn
```

**user 原话(2026-09-12)**:
> "你不应该修改模块可见性, 你应该使用已有可见的api去在tests里做单测, 通过已有的api覆盖, **没有暴露的api的单测**。"

**推理**:
- 项目公共 API 是**对外契约**,**测试是内部 consumer**。改 visibility 让生产 API 表面积变大,**外部用户可能调用到不该调的内部 helper**,破坏封装。
- `pub(crate)` 已经包含整个 crate 的可见性,如果连 crate 内 integration test 都看不到 → 那说明**这个 fn 本来就不该被测试**(它是 implementation detail,不是 stable contract),**正确做法是删掉这个测试,而不是改 visibility**。
- 没有暴露的 API = 没有针对它的单测(测试 = 通过已暴露 API 验证行为,不是 direct white-box inspection)。

### `pub(crate)` item 的测试怎么办 — **DELETE,不保留 inline**(2026-09-12 user 终极规则)

user 原话(2026-09-12 第二轮明确):

> "src里所有单测删除,有tests目录是单测的,如果单测的功能不是pub那就忽略,如果是pub就加到tests 里严格遵守规范"

具体含义:

```rust
// ❌ 禁止:为 pub(crate) item 保留 inline #[cfg(test)] mod tests
pub(crate) fn compute_plan() -> Vec<Plan> { ... }

#[cfg(test)]
mod tests {
    // 即便加了 master 风格注释解释"为何不能搬到 tests/",
    // 这块 inline 测试也必须删除,不能保留
}
```

**最终规则**:
- `pub(crate)` fn / enum / struct 的测试 → **删掉整个 `#[cfg(test)] mod tests { ... }` 块**,不留任何 inline 测试。
- `pub` fn / enum / struct 的测试 → 移到 `<crate>/tests/<feature>/fn.rs` + `<crate>/tests/<feature>/mod.rs`(`use euv_engine::*;` / `use euv_core::*;`),不能改 visibility 让 inline test 看得见。
- 即便某个 `pub(crate)` 算法非常关键、值得 unit test → **也不能加 inline 测试**,**算法正确性必须通过 `pub` API 的 end-to-end 测试间接验证**。

**euv PR #203 实测(2026-09-12)**:
- `core/src/renderer/render/fn.rs` 整块 922 行 inline 测试(测 `compute_child_ops_plan` + `lis_indices`,都是 `pub(crate)`)→ **整块删除**。
- `engine/src/physics/impl.rs` 5 个 inline tests → 4 个 pub-only 测试移到 `engine/tests/physics/fn.rs`,1 个调用 `pub(crate)` getter `get_inverse_inertia` 的测试 → **删除**(没改 visibility)。
- `engine/src/lighting/impl.rs` 6 个 inline tests → 5 个全部移到 `engine/tests/lighting/fn.rs`(全 pub),1 个调用 `pub(crate)` const 的测试 → **删除**。
- `engine/src/raytracing/impl.rs` 5 个 inline tests → 4 个移到 `engine/tests/raytracing/fn.rs`,1 个调用 `pub(crate)` const `RAYTRACE_DEFAULT_MAX_BOUNCES` 的测试 → **删除**。

**原"master 例外 pattern"已被 user 推翻**:14.4 之前文档说"可以保留 inline + master 风格注释",**user 现在不允许这个例外**。任何 inline `#[cfg(test)] mod tests` 块 = review reject,不管有没有注释。

**检测脚本**(`scripts/audit_rust_standards.py` rule 8 + 新加的 rule 15):

### 检测(每个 PR 改动的 sub-file)

```bash
# 任何 + 行包含 #[cfg(test)] mod tests { 是 violation
git diff -U0 origin/master HEAD -- '*.rs' | grep -E "^\+.*#\[cfg\(test\)\]"
# 期望: 零行(注释 / 文档里的引用不算)

# visibility 收紧变更检测(2026-09-12 加)
# 反向:PR 是否把 fn/enum/struct 的 visibility 从 private 升级到 pub(crate)/pub
# 或在 lib.rs / mod.rs 加了 pub use re-export 用于 tests/ 集成测试?
git diff -U0 origin/master HEAD -- '*.rs' | grep -E "^\+.*pub fn |^\+.*pub\(crate\) fn |^\+.*pub enum |^\+.*pub\(crate\) enum |^\+.*pub use " | grep -v "^\+.*pub use std::" | grep -v "^\+.*pub use crate::"
# 然后人工 review:每条都必须是 production API surface 调整,**禁止**为测试调整

# master 例外 pattern (inline tests with explanatory comment):
git grep -B 3 "fn .*() {" -- '*.rs' | grep "tests live inline"
# 期望: 0..N 行(master 已有 N 处,新 PR 加 inline 必须 append 一条)
```

### Master 当前 inline `mod tests` 列表(2026-09-12 PR #203 后)

所有 inline `#[cfg(test)] mod tests` 都已删除或迁移到 `tests/`:

- `engine/src/physics/impl.rs:971` — inline tests 已迁到 `engine/tests/physics/fn.rs`(2026-09-12 PR #203)
- `engine/src/lighting/impl.rs` — inline tests 已迁到 `engine/tests/lighting/fn.rs`(2026-09-12 PR #203)
- `engine/src/raytracing/impl.rs` — inline tests 已迁到 `engine/tests/raytracing/fn.rs`(2026-09-12 PR #203)
- `core/src/renderer/render/fn.rs` (PR #202 + PR #203 inline) — inline tests 已删除(测 pub(crate),按 §14.4 不保留,2026-09-12 PR #203)

## 14.5 单测不需要注释(2026-09-12 user 明确)

### 铁律:测试 fn 内禁止任何 `///` / `//!` / `//` 注释

测试文件的代码全部裸写,不需要任何文档或内联解释。**Test fn name 就是文档**,assertion 表达意图。任何注释都是冗余:

```rust
// ❌ 禁止:文件头 //! 注释
//! Integration tests for the 3D physics step pipeline.
//!
//! Moved from `engine/src/physics/impl.rs` per rust-standards §14.4.
//! These tests exercise only `pub` items reachable via `use euv_engine::*;`.

// ❌ 禁止:per-fn /// 注释
/// Regression test for the bug where `RigidBody3D::apply_torque`
/// accumulated torque into `torque_accumulator` but
/// `PhysicsWorld3D::step()` only zeroed it without ever converting it
/// into angular velocity.
#[test]
fn step_applies_torque_to_3d_angular_velocity() { ... }

// ❌ 禁止:fn 体内 inline `//` 注释
#[test]
fn step_applies_torque_to_3d_angular_velocity() {
    let mut body = ...;
    // Default inertia = mass (1.0) so inverse_inertia == 1.0;
    // applying torque (0, 0, 2) for a 1 s step should give omega == (0, 0, 2).
    body.apply_torque(...);
}
```

### ✅ 正确:裸测试

```rust
use euv_engine::*;

const EPSILON: f64 = 1e-9;

#[test]
fn step_applies_torque_to_3d_angular_velocity() {
    let mut world: PhysicsWorld3D = PhysicsWorld3D::default();
    let mut body: RigidBody3D = RigidBody3D::new_dynamic(1, Vector3D::new(0.0, 0.0, 0.0));
    body.apply_torque(Vector3D::new(0.0, 0.0, 2.0));
    world.add_body(body);
    world.step(1.0);
    let omega: Vector3D = world.get_body(1).unwrap().get_angular_velocity();
    assert!(omega.get_x().abs() < EPSILON);
    assert!(omega.get_y().abs() < EPSILON);
    assert!((omega.get_z() - 2.0).abs() < EPSILON);
    world.step(1.0);
    let omega_after: Vector3D = world.get_body(1).unwrap().get_angular_velocity();
    assert!((omega_after.get_z() - 2.0).abs() < EPSILON);
}
```

### 适用范围

- **文件头 `//!` 模块注释**:禁止(包括解释 §14.4 迁移来源的注释)
- **每个测试 fn 的 `///` doc comment**:禁止(包括解释 regression 原因的注释)
- **fn 体内 inline `//` 注释**:禁止(包括解释测试逻辑或计算来源的注释)
- **空白行做 section 分隔**:允许(`#[test]` 之间用空行分组)

### 检测

pre-commit 跑下面的 grep,任何命中都不通过:

```bash
# 检查所有 tests/*.rs 文件 + tests/**/*.rs 内是否有注释
git diff origin/master HEAD -- "*.rs" | grep -E "^\+.*tests/" | grep -E "^\+.*//" | grep -v "^\+.*//.*//.*//"
# 更直接的方式:
for f in $(git diff --name-only origin/master HEAD -- "*.rs" | grep -E "/tests/.*\\.rs$"); do
  # 检查文件内是否有注释行(以 // 开头的行,排除 use 行)
  if grep -nE "^\s*//[^/]" "$f" 2>/dev/null | grep -v "^\s*//!" | grep -v "^\s*/// " | grep -v "^\s*use "; then
    echo "FAIL: test file has inline // comments: $f"
  fi
done
```

更简单的等价规则:**测试文件中任何 `//` 开头的行都不允许**(除了上面 sample 中 fn 体内展示的禁止用例——也就是全部禁止)。`///` `//!` 文件级 doc 全部禁止,fn 体内 inline 全部禁止。


## 14.6 Practical recipe: adding tests for a NEW pub fn (avoid the inline-mistake)

The pitfall that keeps recurring: when adding tests for a newly-created `pub fn`, the path of least resistance is `#[cfg(test)] mod tests { ... }` at the bottom of the source file. **That path is closed by §14.4.** The correct recipe:

### Step-by-step

1. **Source file:** only the `pub fn` body + `pub use` re-export wiring (if needed). **Zero `#[cfg(test)]` blocks.**
2. **Test fixture dir:** create `<crate>/tests/<feature>/` with three files:
   - `mod.rs` — single line `mod r#fn;` (raw identifier is required because `fn` is a keyword; see §1.4)
   - `fn.rs` — starts with `use std::path::Path;` etc. as needed, then `#[tokio::test]` / `#[test]` functions calling `euv_crate::the_pub_fn(...)` via fully-qualified path
   - If the test needs a multi-line raw string literal input, **put it in a separate `<crate>/tests/<feature>/<fixture>.txt` and use `include_str!("fixture.txt")`** — keeps `fn.rs` lint-clean and avoids `r#"..."#` ambiguity in code-review tooling
3. **Register:** add `mod <feature>;` to `<crate>/tests/mod.rs` (between existing entries, no r# prefix on the test module name itself per §14.1)
4. **Dev-deps:** if `tempfile` / `tokio` macros etc. are needed in tests but not lib, add to `<crate>/Cargo.toml` `[dev-dependencies]` (integration tests use `[dev-dependencies]`, not `[dependencies]`)
5. **Verify:** `cargo test --tests -p <crate>` (not `--lib`, which would skip integration tests; not bare `cargo test` which would also run any leftover inline tests and silently mask the §14.4 violation)

### Why `euv_crate::xxx` not `super::*`

Even when `<crate>/lib.rs` has `pub use {build::*, ...};` (which re-exports the pub fn at crate root), the safest pattern inside `tests/<feature>/fn.rs` is `euv_crate::pub_fn_name(...)` directly. `use super::*;` from inside `fn.rs` brings nothing useful (test crate has no `super` parent beyond `tests/mod.rs`'s `use euv_crate::*;`, which is global anyway). Belt-and-suspenders: write the full path.

### Anti-pattern I hit in 2026-09-14 (PR #233 first pass)

Wrote `#[cfg(test)] mod minify_inline_js_tests { use std::path::Path; ... }` at the bottom of `cli/src/build/fn.rs` because the helper was new and the natural instinct is to put tests where the function lives. §14.4 forbids it. **Always start from the assumption: this new test goes in `tests/<feature>/`, period.** Only after explicitly verifying there's no `tests/`-compatible path (e.g. testing a `pub(crate)` item, which then means *delete the test*) should you even consider alternatives — and there are none per §14.4.

### Pre-commit self-check

```bash
# PR diff should add ZERO + lines matching this pattern
git diff origin/master HEAD -- '*.rs' | grep -E '^\+.*#\[cfg\(test\)\]'
# Expected: empty

# New tests/ files should exist for every new pub fn tested
git diff origin/master HEAD --stat -- 'tests/**/*.rs'
# Expected: non-empty if tests were added
```

If `#[cfg(test)]` shows up in the diff but no `tests/<feature>/` file was created, the PR is incomplete — fix before push.
