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

## 6.6 同 root 的 `use` 必须聚合成一个 brace 语句(2026-09-27 user 钦定)

**user 原话**: "同一作用域内,相同 crate/模块 root 的 use 必须聚合成一个 brace 形式语句,禁止拆成多行独立 use"

### 规则

同一文件、同一作用域内,**2 个及以上独立的顶层 `use` 语句**且 **root segment 相同** → 必须合并成一个 brace 语句。root segment = 路径中第一个 `::` 之前的部分(`std` / `serde` / `super` / `crate` / 任何本地模块名)。

```rust
// ❌ 违规:同一 root `std` 被拆成 3 条独立语句
use std::ffi::c_void;
use std::path::Path;
use std::collections::HashMap;

// ✅ 正确:聚合成一个 brace 语句
use std::{collections::HashMap, ffi::c_void, path::Path};

// ✅ 正确:不同 root 各自独立是正常的,不算违规
use std::path::Path;
use serde::Serialize;
use tokio::sync::Mutex;

// ✅ 正确:已经聚合的 + 不同 root
use std::{fmt::{self, Debug}, path::Path};
pub use serde::Serialize;
```

### 分组粒度:按 (root, visibility) 分组 —— 这是实测结论,不是拍脑袋

**实测(2026-09-27,rustfmt 1.9.0-stable + nightly 1.101.0):**

| rustfmt 配置 | `use std::a; use std::b;` | `pub use std::a; use std::b;`(跨 visibility) |
| --- | --- | --- |
| stable 默认(`Preserve`) | **不合并**,仅按字母重排 | **不合并**,仅重排 |
| nightly `imports_granularity = "Module"` | **不合并** | **不合并** |
| nightly `imports_granularity = "Crate"` | **合并** → `use std::{a, b};` | **不合并**,`pub use` 仍独立 |

结论:

1. `imports_granularity` 是 **nightly-only** 选项(配了但用 stable 只会 warning 忽略),三个仓都没有 `rustfmt.toml`,所以 rustfmt 默认**永远不会**帮你合并 —— 这正是需要 verifier 的原因。
2. 即使 nightly `Crate` 粒度,`pub use` 与私有 `use` 也**始终保持分离**。这是**有意的语义**(re-export vs 私有导入),不是代码漂移。

因此:**跨 visibility 的同 root 组合予以豁免**,verifier 按 `(root, visibility)` 二元组分组,`pub use std::X;` + `use std::Y;` 不报。

### 豁免清单(每一条都有 fixture 覆盖)

| # | 场景 | 为什么豁免 |
| --- | --- | --- |
| 1 | 不同 root(`use std::...` + `use serde::...`) | 正常的多 crate 导入,聚合反而降低可读性 |
| 2 | 同 root 但 visibility 不同(`pub use std::X;` + `use std::Y;`) | 见上表实测:rustfmt 刻意保持分离,re-export 与私有导入语义不同 |
| 3 | glob 与非 glob 并存(`use super::*;` + `use super::Foo;`) | 合并会改变解析语义 —— 显式项可以 shadow glob 项 |
| 4 | fn 体内部的 `use` | §6.4 已禁止 fn 内 use,不重复报 |
| 5 | `#[cfg(test)] mod tests` 内的 use | 测试局部导入,属 §14 范畴 |
| 6 | 被属性 gate 的 import(`#[cfg(windows)] use std::ffi::c_void;`) | **合并会把属性提升到整个 brace 组**,导致非 Windows 平台也带上条件 —— 合并等于改语义;ctares `server-manager/src/lib.rs:31` 就是这个形态 |
| 7 | 无 root 的 brace re-export(`use { r#struct::*, r#type::* };`) | 本来就已是聚合形式,归 §6.1 三段式管辖 |
| 8 | 两条同 root 语句被**另一个 §6.1 stage** 隔开 | 见下方优先级 |

### 优先级:§6.1 三段式顺序 > §6.6 聚合

`lib.rs` / `mod.rs` 的 §6.1 三段式严格顺序(mod → `pub use` → `pub(crate) use` → `pub(super) use` → private use)是**硬性**规则(见 check 27)。**当聚合要求与三段式顺序冲突时,以三段式顺序为准。**

- 两条同 root、同 visibility 的语句如果处在**同一个 stage 内的连续段**(中间只有注释/空行)→ 报,应该合并。
- 如果它们被**另一个 stage** 隔开(例如 private `use` 和 `pub use` 中间插了 `mod` 声明)→ **不报**。合并会要求把一条 import 移过 stage 边界,直接破坏 check 27。

verifier 用"连续段"(run)切分实现这一点:两个 `use` 之间若存在超过 2 行的间隔,视为跨 stage,不聚合、不报告。**注释行不算 stage 边界** —— 注释夹在两条同 root `use` 之间仍然会被报出并要求合并。

### 验证

- 脚本:`scripts/verify_use_aggregation.py <repo>`(use 块状态机 + 花括号深度跟踪,**只扫顶层**)。
- audit:`audit_rust_standards.py` check 41(列表第 40 条)。
- hook:`staged_file_gate.py` 已注册 `verify_use_aggregation`,只拦**新引入**的违规,不拦历史债。
- fixture:`~/.hermes/cache/scratch/verifier-fixtures/use-agg-{compliant,violating}`:compliant 0 hits / exit 0(8 个豁免文件),violating 4 hits / exit 1(4 个违规文件)。audit 端到端双向通过(check 41 在 violating 侧 FAIL 4 hits,在 compliant 侧 PASS)。
- 三仓实测(2026-09-27):**euv 1 违规文件 / 1 hit**(`macros/tests/mod.rs:12`)/ **ctares 0** / **hyperlane 0**。
  - **注意**:`grep` 粗扫出的"多条 `use std::`"绝大多数**本来就已经是 brace 形式**(如 euv `core/src/lib.rs:15` + `:28` 分别是 `pub use std::{` / `use std::{`),不是违规;粗扫数字远高于 verifier 数字属正常。verifier 会解析出每条语句的**真实 root**再分组,无 root 的 `use { ... }` re-export 块不参与分组。
