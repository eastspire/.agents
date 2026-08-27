# 13. 依赖管理

## 13.1 复用优先

- 优先复用项目中已引入的第三方库
- 避免引入新依赖,除非必要且经过权衡
- 若引入新依赖,需说明理由并符合安全审查标准
- **不引入新第三方依赖**优先于 `Cargo.toml` 整洁度;需要时先评估是否能用现有依赖 + 内部宏实现

## 13.2 Cargo.toml 强制约定

| 配置项 | 强制值 |
|--------|--------|
| `edition` | `"2024"` |
| `package.exclude` | 包含 `"target"`, `"sh"`, `".github"` |
| lib 项目的 `package.exclude` | **额外** 包含 `"Cargo.lock"` |
| proc-macro crate 的 `[lib]` | `proc-macro = true;` |

## 13.3 Profile 配置(dev 与 release 必须完全相同)

```toml
[profile.dev]
incremental = false
opt-level = 3
lto = true
panic = "unwind"
debug = false
codegen-units = 1
strip = "debuginfo"

[profile.release]
incremental = false
opt-level = 3
lto = true
panic = "unwind"
debug = false
codegen-units = 1
strip = "debuginfo"
```

> 完整 Cargo.toml 模板见 `templates/cargo-toml.md`

## 13.4 `[dev-dependencies]` 与 workspace `cargo publish` 鸡生蛋(2026-08-27 verified euv PR #26)

**坑**:workspace 里两个 crate 形成**同 version 周期内的发布互锁**:

- crate A 常规依赖 crate B (`[dependencies] B = { workspace = true }`)
- crate B 的 `[dev-dependencies]` 又引用 crate A (`A = { workspace = true }`)

`cargo publish -p B` 的预检查会**对所有 dev-dep 做 crates.io registry 校验**(即使 dev-dep 不会被打包进 `.crate`)。B 想要 publish 必须先有 `A = "version"` 在 crates.io,A 想要 publish 又要先有 `B = "version"`(regular dep)。**两边都 publish 不,**

具体报错:

```
error: failed to prepare local package for uploading
  failed to select a version for the requirement `A = "^X.Y.Z"`
  candidate versions found which didn't match: <older>, ...
  required by package `B vX.Y.Z`
```

**为什么不响**:CI 的 publish step 用 retry+continue 循环,per-package 失败不 `exit 1`,run 报告 `success`。**只有去 crates.io 查 `max_stable_version` 才能发现**。

**修复 — path-only dev-dep**(cargo 允许的最简形式,**无注释**):

```toml
[dev-dependencies]
A = { path = "../" }
```

- 去掉 version spec → cargo 跳过 registry lookup
- tests 编译仍能找到 dev-dep crate (cargo 通过本地 workspace path 解析)
- `cargo publish` 不再要求该 dev-dep 在 crates.io 上存在
- **不加注释**(理由写在 commit message body / PR description,代码内不放解释性文字 —— 与 §3 硬性规则一致)

**根 `Cargo.toml` 无法修这个坑**:dev-dep 写在子 crate 自己的 `Cargo.toml`;`[workspace.dependencies]` 里 path-only alias 不行(cargo 要求 alias 必须对应真实 workspace member name);子 crate 内 `[dev-dependencies]` 是唯一改动点。

**`../` 路径耦合警告**:`macros/Cargo.toml` 现在 `path = "../"` 指向 `euv/` 仓库根。如果以后重构把 `macros/` 挪到别处,需要相应调整。可考虑 CI 加 `cargo metadata | jq -r '.workspace_root'` 一致性检查,但属于过度工程。

**根因诊断步骤**(命中上述症状时):

1. `cargo package -p <crate> --no-verify --allow-dirty` → 应成功(无 error)
2. `cargo publish -p <crate> --dry-run --allow-dirty --no-verify --registry crates-io` → 应 reach "Uploading <crate> <version>"
3. **不要**信 `cargo publish` exit code = 0 —— workflow retry loop 会吞掉失败
4. **查 crates.io**:`curl https://crates.io/api/v1/crates/<crate>` 的 `max_stable_version` 必须匹配 git tag

**euv 仓库实例**(2026-08-27):

- `euv` 根 crate `[dependencies] euv-macros = { workspace = true }`(regular)
- `euv-macros/macros/Cargo.toml` `[dev-dependencies] euv = { workspace = true }`(dev)
- 0.14.0 凑巧 publish 成功(首次 `euv` 上 crates.io,resolver 无历史可比)
- **0.14.1 / 0.14.2 都失败**,只有 `euv-core` / `euv-cli`(无 workspace dep on `euv`)真的到了 crates.io
- PR #26 fix:把 `euv = { workspace = true }` 改成 `euv = { path = "../" }`,1 file / +1 / -1

## 13.5 `Cargo.toml` 不加任何注释(2026-08-27 verified)

与 `mod.rs` / `lib.rs` 一致,`Cargo.toml` 也是纯结构文件 —— 不写 `# xxx` 解释 dep 改动原因 / `[dev-dependencies]` 用意 / `[profile.xxx]` 调参理由。理由放进 commit message body 或 PR description。原因:

- TOML 注释会被 cargo 在打包时**保留进 `Cargo.toml.orig`**(用户拉到的 source tarball 里看得到),给下游读者带来 "这条改动是因为什么背景" 的困惑
- cargo publish 在 resolver 失败时,错误回引依赖树;注释不解决问题,只会让 git blame / PR review 的人多看几行
- 一致性:`mod.rs` 不写注释(lib  §3 + §6.2),`Cargo.toml` 也不写

例外(可写注释):仅当某行 cargo 语法本身不直观,例如 `[profile.<name>] debug-assertions = true`(普通 cargo 写法之外需要解释的优化),才允许 `# 短注释一行` 点明。**禁止** 长段解释 —— 那种一律挪到 commit body。

## 13.6 dev-dep 该写哪个 crate:不要依赖 facade (2026-08-27 verified euv PR #26 复盘)

`§13.4` 的 `path = "../"` 是**最小可工作修复**。但用户反馈 "macros 依赖的是 euv-core 吧不是 euv 吧" 戳中了更对的方向:**优先看 dev-dep 真正需要的是什么,而不是看测试代码 `use X::*` 引入了什么**。

**架构模式**(euv / hyperlane 等 monorepo 通用):

```
crate A (root) ─┬─> re-exports ─┐
                │              ├─> consumer sees A::*
                │              │
                └─ regular ─>  │   (facade)
                                 │
crate B (core / runtime)        │
  pub struct HookContext { ... } ┘   <- HookContext 实际定义在这里
```

euv 实例:

- `euv` (root) `lib.rs`:`pub use {euv_core::*, euv_macros::*};` —— 2 行 facade
- `HookContext` / `Signal` / `RawHtml` 实际定义在 `euv-core`
- `euv-macros` 的 `#[proc_macro] class!` / `var!` 等 proc-macro 定义在 `euv-macros`

测试代码 `use euv::*;` 看似只用一个 crate,实际同时拿到了:

1. `euv-core` 的运行时类型(`HookContext`、`Signal`、`RawHtml`)
2. `euv-macros` 自身的 proc-macros(`class!`、`var!`、`vars!`、`watch!`、`#[component]`、`computed!`、`unsafe_no_inline!`)

依赖 `euv` 是 "伞式导入",**只用类型不需要伞**,但因为 proc-macro 也走伞,改用 `use euv_core::*` 会断掉所有 proc-macro 调用。

**正确做法**:判断 dev-dep 的真实需要:

- 只需要运行时类型 → 直接 dev-dep 底层 crate(`euv-core` / 真正的定义处),`use use::*` 拿类型,proc-macro 调用改成 `crate::macro_name!`(proc-macro 在自家 crate `tests/` 里通过 `#[proc_macro]` 自动可见,**不需要 dev-dep 自身**)
- 需要 proc-macro → 仍 dev-dep 伞(`euv`),因为 proc-macro 不是 `pub` 的,得通过伞才能从测试 crate 拉到
- 同时需要两者 → dev-dep 伞是当前最不痛的方案,scope 超出一行 fix 时再拆分 `use`

**euv PR #26 实际选了伞方案**(`euv = { path = "../" }`),因为拆 `use euv_core::*` + 改所有 proc-macro 调用是 ~30 个测试文件的大改,**scope 不在 "fix cargo publish" 的最小 PR 内**。判断标准:

- 一行 Cargo.toml 改动 + 测试不动 → **伞方案**(当前 PR #26)
- dev-dep 简化到 `euv-core` 需要测试配合改 → **单独 PR**(拆分 `use` + 改 proc-macro 调用 + 验证)

**怎么定位真实定义处**(`grep` 链路,不靠训练数据记忆):

```bash
# 找到类型/宏的真实归属 crate
for typ in HookContext Signal RawHtml; do
  grep -rln "pub struct $typ\b" src/ */src/ 2>/dev/null | head -1
done
# proc-macro:
grep -rln '#\[proc_macro\]' */src/ 2>/dev/null | head
# 查 root crate 是不是 facade:
cat root/Cargo.toml/src/lib.rs | head -10   # 看 pub use {*, *}
```

返回 `core/src/reactive/hook/struct.rs` → 真实定义在 `core` (`euv-core`)。返回 root 的 `lib.rs` 看到 2 行 `pub use` → 确认是 facade,**没有新内容**,所有东西从子 crate 透出。

**配套能力**(防止自己再重蹈覆辙):

- 用户偏好:"只改根 Cargo.toml 的 version" / "依赖版本也不改" → §13.6 之前已经写过的"只动根 + 子 crate 由 CI sync"模式
- dev-dep 这一改(`path = "../"`)是同一个铁律的延伸:**改 Cargo.toml 任何行之前,先看这个改动是不是必须在那个 crate 自己里**——根 `[workspace.dependencies]` 改不到子 crate 的 `[dev-dependencies]`,`[profile.xxx]` 不影响 dev-dep,只有子 crate 自己说了算。

## 13.7 `[dependencies]` 块内顺序:本地 crate 在前,三方在后(2026-08-27 verified euv PR #28)

`[dependencies]` / `[dev-dependencies]` / `[build-dependencies]` 块内的 entry 顺序按以下规则确定:

- **primary**(决定先后两组):workspace 内本地 crate vs 三方 crate。**本地在前,三方在后**。
- **secondary**(组内排序):key 名称长度,**短的在前**。
- **tertiary**(同级 tiebreak):字典序 ASCII,**靠前的字母在前**。

"本地 crate" = workspace member,典型名字以 `euv-` 起头或等于 `euv`,对应 `[workspace.dependencies]` 里的 path-only 那一组。在 `[dependencies]` 里写成 `xxx = { workspace = true }` 就是本地引用。

例(`example/Cargo.toml`,10 个 dep):

```toml
[dependencies]
euv = { workspace = true }              # 本地,长度 3
euv-ui = { workspace = true }           # 本地,长度 6
euv-engine = { workspace = true }       # 本地,长度 10
serde = { workspace = true }            # 三方,长度 5
qrcode = { workspace = true, ... }      # 三方,长度 6
serde_json = { workspace = true }       # 三方,长度 10
lombok-macros = { workspace = true }    # 三方,长度 13
compare_version = { workspace = true }  # 三方,长度 15
serde-wasm-bindgen = { workspace = true }# 三方,长度 18
console_error_panic_hook = { workspace = true }# 三方,长度 24
```

分组:本地组(`euv` / `euv-ui` / `euv-engine`)→ 三方组(其余 7 个)。
组内按长度排序;`qrcode` 在三方组里长度 6 是最小,但因为**前面有本地组**,它不会出现在文件最前面。

**为什么本地在前**(与 `use` 语句保持一致):Rust 项目 `lib.rs` / `mod.rs` 里 `pub use` / `use` 顺序约定俗成是**本地模块在上、三方 crate 在下**(例 `euv/src/lib.rs`:`pub use {euv_core::*, euv_macros::*};` 在 `pub use {console_error_panic_hook, js_sys, ...};` 之前;`core/src/lib.rs`:本地 `mod`/`pub use` 在 `pub use std::{...}` 之前)。Cargo.toml dep 块是对外的"imports 等价物",理应遵循同一规则 —— 本地优先,三方排后。

**为什么不是纯 alphabetic**:alphabetic-only 会把 `alloc-no-stdlib`(长度 15)排到 `euv-core`(长度 8)前面 —— 视觉上本地 crate 被埋在三方 crate 海洋里。读者要确认 "这个 workspace 里有多少本地 dep" 时需要扫完整段。长度优先 + 本地在前 让这种常见检查"一眼可读"。

**为什么 `[workspace.dependencies]` 不适用本规则**:`[workspace.dependencies]` 块的语义是"声明 workspace 共享的 dep 版本 source",entry 顺序对 cargo 行为无影响,但**约定俗成地按 alphabetic 排**(不是按长度、不是按本地/三方分组),因为这块的内容是项目管理层级的"依赖目录",读者按字母查找具体的 dep 名。两套约定并存,不要混。

**手工维护**:

- PR 提交前跑一次 `cargo sort`-类工具确认(本仓库 euv 项目 `euv fmt` 不处理 Cargo.toml,**需要单独 sort**)
- 新增 dep 时,先判断本地还是三方 → 插入对应组 → 组内按长度找位置。**不要**随意 append 到末尾
- PR review 时,如果新增 dep 破坏了顺序,要求 author 重新排序

**配套工具**(尚未自动化):如果未来要工具化,`taplo fmt` + 一段自定义 order_by fn 是最直接的;优先级低于 §13.4 / §13.5 / §13.6,先把这三条吃透再考虑自动化。
