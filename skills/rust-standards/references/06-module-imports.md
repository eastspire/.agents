# 6. 模块导入规则

## 6.1 lib.rs

**只导入整个 crate 全局共用的依赖项**,规范:

- 空行分隔不同类型的导入
- 同类需要聚合(当前 crate / 本地其他 crate / 标准库 / 第三方)
- 按顺序书写导入:
  1. `mod` 声明(普通子模块名)**—— 这一组内禁止空行**(所有 `mod xxx;` 紧贴,不分段)
  2. `pub use`(子模块 glob)
  3. `pub use`(外部 crate glob)
  4. `pub(crate) use`
  5. `pub(super) use`
  6. `use` 私有导入
- 每组按 当前 crate / 标准库 / 外部库 顺序排列
  - **第 6 组(private use)内部还要细分**:
    - 私有 `use std::{...}`(或 `use current_crate::*;` 如果当前 crate 是 workspace 成员)在前
    - 私有 `use {external_crate_1::*, external_crate_2::Symbol, ...}` 在后
    - **单条 `use external_crate::Symbol;` 也要并入 `use {...}` 块**,不要写成独立的 `use ...;` 行后跟 `use {...}` 块。例如 `use log::SetLoggerError;` 应合并进 `use {clap::Parser, log::SetLoggerError, serde::Serialize, ...}`,而不是独占一行放在 `use std::{...}` 之后 / `use {...}` 块之前。

### §6.1 常见违规(2026-09-14 euv PR #235 实测)

1. **private use 写在 pub use 之前**(step 6 必须在 step 2-5 之后)。
2. **`pub use {sub-modules::*}` 放在 `pub use std` / `pub use external` 之后**(子模块 glob 是 step 2,必须最前)。
3. **mod 列表中间插入空行**(§6.1 step 1:所有 `mod xxx;` 紧贴)。
4. **`use current_crate::*;` 夹在 private std 和 private externals 之间**(在 private use 组内部,当前 crate 必须在 std 之前、externals 之后 —— 顺序:当前crate → std → 外部库)。
5. **单条 `use external_crate::Symbol;` 单独成行,没合并进 `use {...}` 块**。
6. **`pub use {sub-modules::*}` 但 sub-modules 内的 items 是 `pub(crate)`**(`E0644: glob import doesn't reexport anything with visibility 'pub'`)。**Fix**:改成 `pub(crate) use {sub-modules::*};`,visibility 必须 ≤ glob 内所有 item 的最大 visibility。验证:`grep -h 'pub(\|^pub ' <crate>/src/<sub>/fn.rs <crate>/src/<sub>/struct.rs ...` 看最大可见性。

### §6.1 pitfall-a:`pub use {sub_modules::*}` 的 visibility 匹配(2026-09-14 euv PR #236)

`pub use {a::*, b::*, c::*};` glob re-export 要求**所有 glob 进来的 item 至少有 `pub` visibility**。如果某 sub-module 的 fn / struct / const 是 `pub(crate)`,`pub use` 会编译期 warn:

```
warning: glob import doesn't reexport anything with visibility `pub` because no imported item is public enough
  --> src/lib.rs:10
   |
10 | pub use {component::*, page::*, style::*};
   |          ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
   = note: the most public imported item is `pub(crate)`
```

**正确做法**:**visibility 必须 ≤ glob 内所有 item 的最大 visibility**。三种解法:

| sub-modules 内部 visibility | 推荐 lib.rs 写法 |
|------------------------------|------------------|
| 全 `pub` | `pub use {a::*, b::*, c::*};` |
| 全 `pub(crate)` | `pub(crate) use {a::*, b::*, c::*};` |
| 混合 | 拆 glob:`pub use {a::*}; pub(crate) use {b::*, c::*};` |

**Step-up 检查**:`pub(crate)` → `pub` 让 sub-modules 公共暴露 = **review reject**(违反最小暴露原则,且对独立测试 crate 必要)。正确方向永远是**降低 lib.rs 端的 visibility**,不要提升 sub-module 端。euv `example/src/lib.rs` 实测:3 个 sub-modules 全部 `pub(crate)` items → 改 lib.rs 为 `pub(crate) use {...};`,0 warning。

### Audit 覆盖范围

`scripts/audit_rust_standards.py` 当前 **不检查** §6.1 的顺序违规(只检查 mod.rs 三段式 + sub-file `use super::*;`)。**lib.rs use/pub use 组顺序是 user-review-only 项** —— review reject 之前 agent 不会自动发现。PR #235 是 user 主动指出后才修。

> 完整模板见 `templates/lib-rs.md`

## 6.2 子模块 mod.rs(严格三段式,**无任何注释、无空行分隔**)

1. `mod r#xxx;` 列表(关键字文件用 raw identifier,普通文件用原名)
2. `pub use {r#xxx::*, ...};` 或 `pub use {子模块::*};` 把需要对外暴露的符号 glob 出去;只在本 crate 内可见的符号用 `pub(crate) use {...};`;测试用的 `mod.rs` 通常不需要 `pub use`
3. 末尾独占一行 `use super::*;`(不带分号以外的任何修饰)

> 完整模板(标准/简化/私有/测试 四种)见 `templates/mod-rs.md`

## 6.3 子文件(fn.rs / struct.rs / impl.rs 等)

- **第一行** **可以省略 `use super::*;`**(2026-09-26 第六轮 user 放宽)。即:
  - ✅ 文件**无** `use` —— OK(例如 `pub fn foo() {}` 直接开头)
  - ✅ 文件**首行** `use super::*;` —— OK
  - ✅ 文件**体内任何位置** `use super::*;` —— OK
  - ❌ 文件**有** use 但**不是** `use super::*;` —— 违规
- 后续自由声明,**不允许**出现 `use crate::xxx;`、`use std::xxx;`、`use super::具体路径;`、`use external_crate::xxx;`、`use crate::*;` 这类长路径或具体路径导入(任何非 `use super::*;` 形式的 use 都违规)
- 必须通过 `use super::*;`(或干脆**不**写 use,完全在文件内本地声明所有东西)来访问父模块符号

> **历史**(2026-09-26 之前): 旧 §6.3 强制要求子文件首行必须是 `use super::*;`,
> 不能省略。第六轮 user 原话: "不是所有文件都必须要需要使用 use super::*,
> 可以不要 use, 对于 lib.rs, mod.rs 之外的 rs 文件, 是不允许出现 use::super::*
> 和没有 use 之外的其他写法的", 明确放宽 "可以不要 use"。本节已同步更新。
>
> 验证脚本 `scripts/verify_keyword_file_purity.py`:
> - `_check_first_line_super` —— 检测首行是否是 `use` 但**不是** `use super::*;`(放宽到 "有 use 时必须是 use super::*;")
> - `_check_use_centralized` —— 扫描整文件捕所有 `use\s+(crate::|super::(?![*])|std::|[a-zA-Z_]\w*::)` 形式
>
> 被 `audit_rust_standards.py` check 23 调用。

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


**Pitfall-b(子文件函数体内全路径调用外部 crate 符号,audit rule 9 不覆盖)**:

§6.4 字面禁止 `use std::xxx::yyy;` 这种 fn 内 import,但**没有显式禁止 fn 体内 `external_crate::Symbol` 全路径调用**。例如 `minify_js::Session::new()` 在 `cli/src/build/fn.rs` 的 fn 体里 — audit rule 9 只 grep `use crate::xxx;` 模式,**不 grep 函数体内的 `external_crate::xxx` 调用**,所以 PASS,但 user review 仍会判 §6.3/§6.4 spirit 违规。

**正确写法**:
1. 在 lib.rs `pub use external_crate::{SpecificSym1, SpecificSym2, ...};` 集中 re-export 用到的具体符号
2. 子文件 fn 体内用裸名:`Session::new()` / `minify(...)` / `TopLevelMode::Module`

**易错**:`pub use external_crate;` 只 re-export 整个 crate 的名字(如 `minify_js`),**不能让** `use super::*;` 拿到 crate 内的符号 — 必须 `pub use external_crate::{Symbol1, Symbol2};` 显式列。

```rust
// ❌ 编译过,但 audit rule 9 抓不到,user review 仍 reject
let session: minify_js::Session = minify_js::Session::new();

// ✅ lib.rs 集中 re-export
// pub use minify_js::{Session, TopLevelMode, minify};
// 子文件 fn 体:
let session: Session = Session::new();
```

**detection**(audit script 之外的补充检查,`scripts/check_subfile_external_paths.sh`):

```bash
# 对 PR diff 内修改的所有 src/ 子文件(fn.rs / impl.rs / struct.rs / enum.rs / trait.rs / type.rs / const.rs),
# grep 是否有 `external_crate::xxx` 全路径调用(extern = 在 Cargo.toml 显式列出的第三方 dep)
for f in $(git diff --name-only origin/master HEAD -- '*.rs' | grep -E '^[^/]+/src/[^/]+/[^/]+\.rs$' | grep -vE '/(mod|lib)\.rs$'); do
  for ext in $(grep -E '^[a-zA-Z0-9_-]+\s*=' Cargo.toml | cut -d'=' -f1 | tr -d ' '); do
    # 排除 std / core / alloc(允许出现)和 euv-* 本仓 crate
    case "$ext" in std|core|alloc) continue;; esac
    if grep -nE "\b${ext}::[A-Za-z]" "$f" >/dev/null 2>&1; then
      echo "POSSIBLE-VIOLATION: $f uses ${ext}::... in sub-file body"
    fi
  done
done
```

预 commit 必跑这一检查。euv PR #233 实测:3 处 `minify_js::Session/minify/TopLevelMode` 调用全被这一脚本抓到,audit 原 rule 9 漏掉。

**例外**:
- `#[cfg(test)] mod tests { use std::time::Instant; }` 如果 `Instant` 没在 lib.rs pub use,且仅测试使用 → OK。
- 子文件**首次**使用某个 std 符号,而该符号尚未被 lib.rs re-export → **应先加到 lib.rs** (`pub use std::time::Instant;`),然后再在 sub-file 用。**不要**在 sub-file 内 `use std::time::Instant;` 直接绕开。

## 6.5 禁止 `use ... as ...` as 重命名(2026-09-26 user 钦定)

**user 原话**: "类型导入禁止使用 as 重命名,如果类型冲突才在使用的地方使用最短可区分的命名空间"

### 规则

任何 `use` 语句(任意可见性:`use` / `pub use` / `pub(crate) use` / `pub(super) use`;含分组多行 import 块内的 `as`)**禁止** `as <ident>` 重命名:

```rust
// ❌ 全部违规
use std::task::Context as TaskContext;
use std::{fmt::{self, Write as FmtWrite}};
pub use std::io::Result as IoResult;
```

### 类型冲突的正确解法:使用处最短可区分命名空间

冲突时**不改 import**,在**使用处**写最短可区分的命名空间路径:

```rust
// lib.rs:
use std::{fmt::{self, Debug, Display, Formatter}, io};

// 子文件(冲突:本地 Result vs std::fmt::Result):
fn fmt(&self, f: &mut Formatter<'_>) -> fmt::Result { ... }   // ✅
fn connect(addr: &str) -> io::Result<Stream> { ... }          // ✅
let item: toml_edit::Value = parse(raw);                      // ✅ extern crate 名天然在作用域内
```

- `fmt::Result` / `io::Error` / `toml_edit::Value` 都是"最短可区分"形式。
- extern crate 名(edition 2018+)在所有位置天然在作用域内,`toml_edit::Value` 不需要任何 import。
- 本地模块与 std 同名时(如 crate 内有 `mod fmt;`),`fmt::Result` 会解析到本地模块 → 最短可区分形式升级为全路径 `std::fmt::Result`。
- 无冲突时直接 import 原名(`use std::fmt::Write;`),不要防御性改名。

### 别名替换的正确流程(防炸)

替换存量别名前**必须**确认别名指向的不是本地定义:

```bash
grep -rn "struct <Alias>\|type <Alias>\|enum <Alias>" <crate>/src
```

euv cli 实测:`FmtResult` 是本地 `pub(crate) struct FmtResult`(`cli/src/fmt/struct.rs`),不是 std 别名。盲目全局替换 `FmtResult → fmt::Result` 把 struct 定义与构造函数全部改炸(E0425/E0433 5 处)。本地定义的别名不动,只替换 import 别名 + 其使用处。

### 验证

- 脚本:`scripts/verify_no_import_rename.py <repo>`(use 块状态机,覆盖单行 / 分组多行 / 各可见性)。
- audit:`audit_rust_standards.py` check 37。
- fixture:`~/.hermes/cache/scratch/verifier-fixtures/rename-{compliant,violating}`,双向通过(0 / 3 hits,exit 0/1)。
- 三仓收敛(2026-09-26):hyperlane 2 / euv 6 / ctares 1 → 全部 0。
