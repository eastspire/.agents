# 9. 遵守项目现有规范

## 9.1 严格遵循项目的约定

- 文件夹命名
- 模块划分方式
- 包导入风格(参考 references/06-module-imports.md)
- 代码排序逻辑
- 编码约定
- **禁止函数体内出现空行**

## 9.2 泛型约束写法

泛型参数统一使用 `where` 关键字进行约束:

```rust
// ✅ 正确
fn parse<T>(input: T) -> Result<T, Error>
where
    T: FromStr,
{
    // ...
}

// ❌ 错误
fn parse<T: FromStr>(input: T) -> Result<T, Error> {
    // ...
}
```

**不允许在 `fn` 签名直接写 `<T: Bound>`,必须挪到 `where T: Bound { ... }`**。

## 9.3 impl 块排列顺序(同一文件内多个 impl 时)

1. **trait 的 blanket impl**(如 `impl<F, R> SomeTrait<R> for F where ... {}`)
2. `impl Default for Xxx`
3. `impl Xxx`(本体方法,按调用关系或字母顺序排列)
4. `impl PartialEq` / `impl Eq` / `impl Hash` / `impl PartialOrd` / `impl Ord`

## 9.4 关联函数 / factory 独立 impl 块

- 关联函数(factory / utility)放独立 `impl Hook { ... }` 块,**不混入** 数据类型自身的 `impl` 块
- 工厂方法、构造器、单字段 getter 统一返回显式类型(不依赖类型推导)
- 若返回非 `()`,加 `#[must_use]`

## 9.5 函数体内禁止空行(§9.1 item 10 展开)

§9.1 第 6 项明确"**禁止函数体内出现空行**"。这一条比一般代码风格更严格:fn 体内的 statement / let / expression 之间不允许插入空行作为视觉分隔。Section break 必须用注释表达(`// Phase 1: ...`,`// Pass 3: emit Remove for ...`,`// OPT 11: ...`)。

**正确写法**(fn 体无空行):
```rust
pub(crate) fn patch_children_keyed(
    &mut self,
    parent: &Element,
    old_children: &[VirtualNode],
    new_children: &[VirtualNode],
) {
    // OPT 11: the move plan is computed by compute_child_ops_plan.
    let mut old_keys_indexed: Vec<Option<&str>> = Vec::with_capacity(old_children.len());
    for child in old_children.iter() {
        old_keys_indexed.push(child.key());
    }
    // Build the new-key index in parallel: position -> key.
    let mut new_keys_indexed: Vec<Option<&str>> = Vec::with_capacity(new_children.len());
    for child in new_children.iter() {
        new_keys_indexed.push(child.key());
    }
    let plan: Vec<ChildOpPlan> = compute_child_ops_plan(&old_keys_indexed, &new_keys_indexed);
    // ...
}
```

**错误写法**(fn 体内有空行,review reject):
```rust
pub(crate) fn patch_children_keyed(...) {
    // OPT 11: ...

    let mut old_keys_indexed: Vec<Option<&str>> = Vec::with_capacity(...);  // ← 空行后第一行

    for child in old_children.iter() {  // ← 又一个空行后
        old_keys_indexed.push(child.key());
    }
}
```

**`euv fmt` / `cargo fmt` 不会自动删除 fn 内空行**——这两个 formatter 只重排 token 间空白,不主动移除 inter-statement 空行。**review 时必须手动检查**。

**检测方法**(每个 PR 改动的 fn):
```bash
awk '
  /pub fn |pub\(crate\) fn |^fn / && !in_fn { in_fn=1; start=NR; blanks=0; next }
  in_fn && /^}$/ { if (blanks > 0) print FILENAME ":" start "-" NR ": " blanks " blank line(s)"; in_fn=0; next }
  in_fn && /^$/ { blanks++ }
  in_fn && /^[[:space:]]*\/\// { next }  # 注释行不算 break
' <crate>/src/<modified_file>.rs
```

**例外**(允许空行的位置):
- `#[test] fn a() { ... }` 与 `#[test] fn b() { ... }` 之间 — test 分隔符,idiomatic Rust。
- 顶层 free function `fn a() { ... }` 闭合 `}` 之后、`fn b(...)` 的 doc comment 之前 — 顶层 item 分隔,**不算 fn 内空行**。
- struct / enum literal 内字段之间 — 字面量内部布局,不构成 statement 间空行。
