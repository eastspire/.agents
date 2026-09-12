# 1. 目录结构与文件组织

## 1.1 目录命名

- 所有目录以功能命名(如 `api/`, `auth/`, `model/`, `service/`, `request/`, `response/`)。
- 对于 Monorepo 项目,需要尽可能拆分子 `crate`,每个子 crate 职责单一。

## 1.2 Cargo.lock 处理

- `lib` 项目不需要上传 `lock` 文件到 `git` 仓库(`.gitignore` 必须包含 `Cargo.lock`,`Cargo.toml` 的 `package.exclude` 也必须包含 `"Cargo.lock"`)。
- `bin` 项目需要上传 `lock` 文件到 `git` 仓库。

## 1.3 关键字文件(9 种)

每个目录下仅允许创建以 **Rust 关键字命名的 `.rs` 文件**,共 **九种**:

| 文件名 | 只允许包含 | 不允许包含 |
|--------|-----------|-----------|
| `const.rs` | `const` 声明 | 其他任何声明 |
| `static.rs` | `static` 声明 | 其他任何声明 |
| `fn.rs` | 自由函数 `fn` | 类型、trait、impl |
| `enum.rs` | `enum` 定义 | `struct` / `impl` / `fn` |
| `struct.rs` | `struct` 定义(含 tuple struct 与 unit struct) | `enum` / `impl` / `fn` |
| `trait.rs` | `trait` 定义 | `impl` / `struct` / `enum` / `fn` |
| `impl.rs` | `impl` 块(为已存在类型实现方法或 trait) | 类型定义 |
| `type.rs` | `type` 别名(`pub type X = ...`) | `fn` / `struct` / `enum` / `impl` |
| `mod.rs` | 模块入口,组织当前模块的导出与导入 | 类型 / 函数实现 |

- `lib.rs` 或 `main.rs`:项目根入口。
- **关键字文件之间不得混用**。如需新增类型,把类型搬到对应关键字文件。
- 子目录可按职责细分(如 `request/`、`response/`、`server/`、`client/`),每个子目录独立遵循上述关键字文件约束。

### 1.3a 关键字文件纯净性 enforcement

§1.3 表格是**硬性约束**——每个 sub-file 的 basename 决定了它能包含什么:

| basename | 唯一允许的 top-level declaration | 唯一禁止 |
|----------|----------------------------------|----------|
| `const.rs` | `pub const X: T = ...` | `fn` / `struct` / `enum` / `impl` / `trait` / `type` / `static` |
| `static.rs` | `pub static X: T = ...` | `fn` / `struct` / `enum` / `impl` / `trait` / `type` / `const` |
| `fn.rs` | `pub fn xxx(...) ...` (free fns) | `struct` / `enum` / `trait` / `impl` / `type` / `const` / `static` |
| `enum.rs` | `pub enum Foo { ... }` | `struct` / `fn` / `trait` / `impl` / `type` |
| `struct.rs` | `pub struct Foo { ... }` | `enum` / `fn` / `trait` / `impl` / `type` |
| `trait.rs` | `pub trait Foo { ... }` | `struct` / `enum` / `fn` / `impl` / `type` |
| `impl.rs` | `impl X { ... }` / `impl Trait for X { ... }` | `struct` / `enum` / `fn` 声明(只能有 impl 块) |
| `type.rs` | `pub type Alias = ...` | `fn` / `struct` / `enum` / `impl` / `const` / `static` |
| `mod.rs` | `mod r#xxx;` + `pub use` + `use super::*;` | `struct` / `enum` / `fn` / `impl` / `trait` / `const` / `static` |

**常见误区**:`fn.rs` 内顺手定义 `pub(crate) enum ChildOpPlan`(因为 fn 调用它)——这违反 §1.3。**正确做法**:新建 `enum.rs`,在 `mod.rs` 加 `mod r#enum;` + `pub(crate) use {r#enum::*};`,然后 `fn.rs::use super::*;` 就能直接用 `ChildOpPlan`。

**`fn.rs` / `struct.rs` 是最常被当作"grab-bag"误用的两个文件**(因为它们承接业务逻辑)。抗拒诱惑:新增 enum / type / impl 必须搬到对应关键字文件。

**例外**:`#[cfg(test)] mod tests { ... }` 块内可以定义测试专用 helper(闭包、type alias、临时 struct)— 这部分不进 production 编译,不算污染。

**检测**(每个 PR 改动的 sub-file):
```bash
# 在 fn.rs / const.rs / static.rs 内不该出现的声明
grep -nE '^(pub |pub\(crate\) )?(struct|enum|trait|impl|type)' \
  $(git diff --name-only upstream/master HEAD -- '*.rs' | grep -E '/(fn|const|static|mod)\.rs$')

# 期望: 零行(或仅注释/doc string 中的引用)
```

### 1.3b raw-string-aware 检测 — WGSL shader 内 decl 是 false positive (2026-09-12 教训)

**陷阱**:`const.rs` 经常包含 WGSL shader raw string literal:

```rust
pub(crate) const GAME_2D_WEBGPU_SHADER: &str = r#"
struct BallData { pos_radius: vec4<f32>, color: vec4<f32>, };
struct BallsUniforms { ... };
fn vs_main(@builtin(vertex_index) vi: u32) -> VertexOutput { ... }
fn fs_main(in: VertexOutput) -> @location(0) vec4<f32> { ... }
"#;
```

naive grep `grep -nE '^(pub )?(struct|enum|trait|impl|type)' const.rs` 会报 **38 false positives** — 那些 `struct BallData { ... }` 是 WGSL shader code 不是 Rust 声明。

**正确检测必须 raw-string aware**:
- 跟踪 `r#"..."#` / `r##"..."##` open / close markers
- 当 parser 在 raw string 内,**完全跳过** 关键字检测
- parser 退出 raw string 后再恢复检测

**实现模式**(Python + awk 模板,参考 `audit_rust_standards.py` 第 15 rule):
```python
in_raw = False
delim = ""
for i, line in enumerate(lines, 1):
    if in_raw:
        close_marker = '"' + delim
        if close_marker in line:
            pos = line.find(close_marker)
            after = line[pos + len(close_marker):]
            in_raw = False
            delim = ""
            # process remainder (after raw-string close)
            if re.match(forbidden_pattern, after):
                print(f"{f}:{i}: {after[:80]}")
        continue
    m = re.search(r'r(#+)"', line)
    if m:
        delim = m.group(1)
        rest = line[m.end():]
        close_marker = '"' + delim
        cpos = rest.find(close_marker)
        if cpos == -1:
            in_raw = True  # multi-line raw string
        # process pre-raw-portion for forbidden decls (in case decls are before raw string)
        pre = line[:m.start()]
        if re.match(forbidden_pattern, pre):
            print(f"{f}:{i}: {pre[:80]}")
        continue
    if re.match(forbidden_pattern, line):
        print(f"{f}:{i}: {line[:80]}")
```

**适用项目**:euv / hyperlane / 其他把 WGSL / GLSL / HLSL shader 嵌入 `pub(crate) const *_SHADER: &str = r#"..."#;` 的 Rust 项目。**所有 raw-string literal 内的非 Rust 代码都需要 raw-string-aware 检测**,否则 naive grep 会爆 false positive。

**踩坑**:audit script rule 15 (R1.3a raw-string-aware) 实测 38 false positives → 0 false positives 后 PASS。验证方法:临时插一个 `pub(crate) struct INVALID_TEST { ... }` 到非 `struct.rs` 文件,看 audit 是否 FAIL。

## 1.4 raw identifier 命名(关键!)

由于 `enum` / `impl` / `const` / `static` / `struct` / `trait` / `type` / `fn` 是 Rust 关键字,直接写 `mod enum;` 会编译失败。所有关键字文件必须在 `mod.rs` 中以 **raw identifier**(`r#xxx`)形式声明:

```rust
mod r#const;
mod r#enum;
mod r#fn;
mod r#impl;
mod r#static;
mod r#struct;
mod r#trait;
mod r#type;
```

对应的 `pub use` / `pub(crate) use` 也必须用 raw identifier:

```rust
pub use {r#const::*, r#enum::*, r#fn::*, r#impl::*, r#static::*, r#struct::*, r#trait::*, r#type::*};
```

**文件本体**(磁盘上的 `struct.rs` / `enum.rs` 等)按 Rust 关键字原名命名,**不要写成 `r#struct.rs`**。

## 1.5 示例结构

```bash
src/
├── lib.rs
├── api/
│   ├── const.rs
│   ├── enum.rs
│   ├── fn.rs
│   ├── impl.rs
│   ├── mod.rs
│   ├── static.rs
│   ├── struct.rs
│   ├── trait.rs
│   ├── type.rs
├── tests/
│   ├── api
│     ├── fn.rs
│     ├── mod.rs
│   ├── mod.rs
```
