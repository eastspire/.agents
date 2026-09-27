# 13. 依赖管理

## 13.1 复用优先

- 优先复用项目中已引入的第三方库
- 避免引入新依赖,除非必要且经过权衡
- 若引入新依赖,需说明理由并符合安全审查标准
- **不引入新第三方依赖**优先于 `Cargo.toml` 整洁度;需要时先评估是否能用现有依赖 + 内部宏实现

> **13.1 实操判断**:依赖是否真的"新",看 Cargo.lock 而不在 Cargo.toml —— 已经 transitive 进入 lock file 的 crate(如 `lombok-macros` 经常作为 `euv` / `euv-ui` 的 transitive 出现),显式声明到 `[dependencies]` 不算"新第三方依赖",只是把 transitive 提升为直接依赖。验证:`grep -A1 'name = "lombok' <crate>/Cargo.lock | head -3` 看 lock 里有没有。**已在 lock 里 → 允许显式 declare**;**不在 → 必须先评估是否能用现有 dep + 内部宏替代**。2026-09-18 eastspire/euv-docs PR #31 lombok-macros 走这条路。

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

### 13.3.1 monorepo 子包 Cargo.toml 禁止重复定义 profile(2026-09-14 hyperlane PR #34 实测)

**坑**:workspace 里 `hyperlane-core/Cargo.toml` 也写了 `[profile.dev]` / `[profile.release]` 段(从原单仓代码搬运过来),`cargo check` 时 cargo **会警告**但不报错:

```
warning: profiles for the non root package will be ignored, specify profiles at the workspace root:
package:   /path/to/<crate>/Cargo.toml
workspace: /path/to/monorepo/Cargo.toml
```

Cargo 的 profile 配置**只能在 workspace 根 `Cargo.toml`**生效一次,子包 profile 全部被 cargo 忽略。

**修复 — 从所有子包 Cargo.toml 删除 profile 段**:

```bash
# 从子包 Cargo.toml 删除 [profile.dev] 和 [profile.release] 整段
sed -i '/^\[profile\./,/^\[/d' core/Cargo.toml macros/Cargo.toml type/Cargo.toml cli/Cargo.toml
# 注意 sed 多行匹配不会保留 file 末尾空行,可能残留孤儿 `strip = "debuginfo"` 等 config 行,要单独清理:
sed -i '/^strip = "debuginfo"$/d' core/Cargo.toml macros/Cargo.toml type/Cargo.toml cli/Cargo.toml
```

**euv 模式**:`euv-dev/euv` monorepo 里 cli/Cargo.toml / core/Cargo.toml 等子包 Cargo.toml **完全不含** `[profile.*]` 段,profile 全部集中在根 `Cargo.toml`。

**检测**:monorepo PR review 时跑 `cargo check --workspace` 看是否有 `profiles for the non root package will be ignored` warning;0 warnings 通过。

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

## 13.7 `[dependencies]` / `[dev-dependencies]` / `[build-dependencies]` / `[workspace.dependencies]` 块内顺序(round-4,2026-09-27)

四个 dep 块(`[dependencies]` / `[dev-dependencies]` / `[build-dependencies]` / `[workspace.dependencies]`)统一遵循"**本地在前,三方在后 + 组内 entry 长度升序**"规则,块内**唯一允许的空行**出现在"本地组与三方组的交界处"。**组内排序 primary = entry 完整长度**(整条 entry 跨所有行的 whitespace-agnostic 字符总数),**secondary = dep key ASCII 字典序**。

### 13.7.1 三类块的分组定义

| 块 | 本地组(在前) | 三方组(在后) |
|---|---|---|
| `[dependencies]` / `[dev-dependencies]` / `[build-dependencies]` | `euv* = { workspace = true }`(workspace 内 path-dep crate 名,无论是否标 `path = "..."`) | 其他所有 crate 名(`serde`、`tokio`、`minify-js` 等) |
| `[workspace.dependencies]` | `euv* = { path = "xxx", version = "..." }` 形式 | 其他所有 crate 名 |

**判断"本地"**:dep 的 `value` 部分包含 `workspace = true` 引用 workspace dep、或 dep 名字是 workspace member name(在 `[workspace] members` 列表里)。判定时可一行看 dep 名,二行看 value。

### 13.7.2 跨段空行(2026-09-27 user 钦定)

**任意两个连续 `[]` 段头之间,最后一个 entry 之后必须正好 1 个空行分隔**。

```toml
[dependencies]
serde = "1.0"

[dev-dependencies]      # ✓ OK: 正好 1 个空行分隔
tokio = "1.0"

[build-dependencies]    # ✗ FAIL: 0 个空行 (跟 [dev-dependencies] 直接相连)
cc = "1.0"


[features]              # ✗ FAIL: 2 个空行
default = []
```

**关键定义**:"跨段空行" = **段最后一个 entry 之后** 到 **下个段头之前** 的空行数。**段内** entry 之间的空行(例如本地/三方边界 §13.7.3 那个空行)**不算**跨段违规 —— verifier 通过"最后一个 entry"作为锚点区分两种空行。

**适用所有 `[]` 段头**,不限于 dep 4 块:`[package]` / `[lib]` / `[features]` / `[profile.*]` / `[patch.*]` / `[[bin]]` / `[[example]]` / `[[bench]]` 等。

**示例**:
- `[package]` 与 `[dependencies]` 之间 0 空行 → FAIL
- `[dependencies]` 与 `[dev-dependencies]` 之间 2 空行 → FAIL
- `[dependencies]` 与 `[dev-dependencies]` 之间 1 空行 → OK(即使 `[dependencies]` 段内有 local/third-party 边界空行,不算违规)
- `[lib]` 与 `[[bin]]` 之间 1 空行 → OK

**为什么不靠直觉手动保持**:`cargo new` 生成的模板在 `[package]` 与 `[dependencies]` 之间留 1 空行,但 `[dependencies]` 与 `[dev-dependencies]` 之间常留 2 空行(因 `[dev-dependencies]` 由 `cargo add --dev` 后追加,前面的 entry 已经有 trailing blank)。这种"模板默认布局"违反规则,需要 verifier 强约束。

**验证脚本**:`scripts/verify_dep_order.py::check_cross_section_blanks` 自动跑(已挂在 `audit_rust_standards.py` check 21 末段 + `rust_pre_commit.py` Phase 2 + pre-commit git hook)。

**Fixture**:`~/.hermes/cache/scratch/verifier-fixtures/cross-section-blank-{compliant,violating}`:compliant 0/exit 0,violating 2/exit 1(0 空行 + 2 空行各 1 hit)。

### 13.7.3 块内顺序(round-4)

- **本地组在前,三方组在后**;本地与三方之间**唯一允许的空行**(1 行 `\n`)。
- **组内排序 primary = entry 完整长度**(整条 entry 跨所有行的 whitespace-agnostic 字符总数,含 `key = {...}` 与 features/fields),**secondary = dep key ASCII 字典序**。`euv < euv-ui < euv-cli < euv-core < euv-engine < euv-macros < euv-example` 正是按 entry 长度升序排(`euv = { path = ".", version = "..." }` 最短,`euv-example = { path = "example", version = "..." }` 最长)。三方同理:`log < toml < quote < chrono < ignore < if-addrs < js-sys < serde-wasm-bindgen < wasm-bindgen < alloc-no-stdlib < serde_json < hyperlane < ...`。
- **同长度时按 dep key 字典序**(`euv-engine` 与 `euv-macros` 都是 52 字符,字典序在前即可)。

### 13.7.4 为什么 round-4 用 entry 完整长度而不是 key 长度或 alphabetic

- **key 长度太小太均**:大多数 dep key 在 4-12 字符之间,`log`/`toml`/`quote`/`chrono`/`ignore` 都 5-6 字符,key 长度 primary 几乎退化为 alphabetic。user 原话是"整体长度从小到大排序",**整体 = entry 整体**,不是 key 整体。
- **alphabetic 看不出"短在前"的视觉引导**:alphabetic 是任意选择,扫读 dep 块时不提示"这里有一段短的简单声明"。entry 长度 ascending 是物理视觉规律(短条目在最上,长条目在下),与 §13.7.9 const.rs 内部排序精神一致(const 短在前)。
- **单规则胜过拼接**:alphabetic + 空行分组的双规则依赖"哪里该有/不该有空行"的判断;length-primary + key-secondary 是单一可计算函数,verifier/fixer 共用同一个 sort key(`scripts/verify_dep_order.entry_sort_key`),无法漂移。

### 13.7.5 为什么保留本地/三方分组 + 边界空行

分组让"工作区内部依赖"与"外部依赖"在视觉上立即可分(本地短缩写在多行 entry 上总是较短,长度排序同样把本地排在上)。**唯一空行** = 边界,符合 §13.7.4 的"空行只有视觉分隔意义时才出现"原则——三方组内不再有"无意义空行"。

### 13.7.6 例(`example/Cargo.toml` `[dependencies]`)

```toml
[dependencies]
euv = { workspace = true }
euv-ui = { workspace = true }
euv-core = { workspace = true }
euv-engine = { workspace = true }
euv-macros = { workspace = true }

serde = { workspace = true }
tokio = { workspace = true }
chrono = { workspace = true }
hyperlane = { workspace = true }
serde_json = { workspace = true }
color-output = { workspace = true }
compare_version = { workspace = true }
console_error_panic_hook = { workspace = true }
```

本地组 5 条按 entry 长度升序(`euv`(26) < `euv-ui`(29) < `euv-core`(31) < `euv-engine`/`euv-macros`(33 并列,字典序在前))。中间 1 空行。三方组按 entry 长度升序(`serde`/`tokio`(28) < `chrono`(29) < `hyperlane`(32) < `serde_json`(33) < `color-output`(35) < `compare_version`(38) < `console_error_panic_hook`(47))。

### 13.7.7 例(根 `Cargo.toml` `[workspace.dependencies]`)

```toml
[workspace.dependencies]
euv = { path = ".", version = "0.24.6" }
euv-ui = { path = "ui", version = "0.24.6" }
euv-cli = { path = "cli", version = "0.24.6" }
euv-core = { path = "core", version = "0.24.6" }
euv-engine = { path = "engine", version = "0.24.6" }
euv-macros = { path = "macros", version = "0.24.6" }
euv-example = { path = "example", version = "0.24.6" }

log = "0.4.33"
toml = "0.9.12"
quote = "1.0.47"
chrono = "0.4.45"
ignore = "0.4.31"
if-addrs = "0.15.0"
js-sys = "0.3.103"
qrcode = { version = "0.14.1", default-features = false }
clap = { version = "4.6.4", features = ["derive"] }
serde = { version = "1.0.229", features = ["derive"] }
minify-js = "0.6.0"
proc-macro2 = "1.0.107"
syn = { version = "2.0.119", features = ["full", "extra-traits"] }
alloc-no-stdlib = "=2.0.4"
color-output = "10.0.10"
compare_version = "2.0.14"
hyperlane = "21.3.6"
hyperlane-cli = "0.1.25"
lombok-macros = "2.1.0"
serde_json = "1.0.151"
serde-wasm-bindgen = "0.6.5"
console_error_panic_hook = "0.1.7"
wasm-bindgen = "0.2.126"
wasm-bindgen-futures = "0.4.76"
wasm-bindgen-test = "0.3.76"
web-sys = { version = "0.3.103", features = [...] }
notify = { version = "8.2.0", default-features = false, features = [
    "macos_fsevent",
] }
tokio = { version = "1.53.1", features = [...] }
```

本地组 7 条按 entry 长度升序(`euv`(40) < `euv-ui`(44) < `euv-cli`(46) < `euv-core`(48) < `euv-engine`/`euv-macros`(52 并列) < `euv-example`(54))。中间 1 空行。三方组按 entry 长度升序(`log`(11) < `toml`(11) < `quote`(13) < `chrono`(13) < `ignore`(13) < `if-addrs`(14) < `js-sys`(14) < `qrcode`/`clap`/`serde`/`minify-js`/`proc-macro2`/`syn`(20-40 段) < 较短的多行 entry)。

> **注意**:`serde` 与 `serde_json` 紧邻且长度不同(`serde` 短,`serde_json` 长),不会因为 key 前缀重叠而被合并——sort 是基于 entry 整体字符数,不是 prefix tree。

### 13.7.8 PR 提交前自检(Python 一行 sort 验证, round-4)

```bash
python3 -c "
import re, sys, tomllib
path = sys.argv[1]
section = sys.argv[2]
text = open(path).read()
m = re.search(r'^\[' + section + r'\]\n(.*?)(?=^\[|\Z)', text, re.S | re.M)
if not m: sys.exit(0)
block = m.group(1)
# 多行 entry 边界识别:以行首 'key =' 开始,持续到下一个行首 'key =' 或块结束
entries = []
current = []
for line in block.splitlines():
    if re.match(r'^[a-zA-Z0-9_-]+\s*=', line):
        if current:
            entries.append(current)
        current = [line]
    elif current:
        current.append(line)
if current:
    entries.append(current)

def entry_key(lines):
    return (sum(len(l.strip()) for l in lines), lines[0].split('=', 1)[0].strip())

local_set = set()
# 本地 = workspace member name 简化:用 path-only dev-dep 模式 + workspace = true 推断
# 这里只读 Cargo.toml 不知道 workspace members,用 key 前缀启发式
def is_local(key):
    return key.startswith('euv') or key == path.split('/')[-1].removesuffix('.toml')

local = [e for e in entries if is_local(e[0].split('=', 1)[0].strip())]
third = [e for e in entries if not is_local(e[0].split('=', 1)[0].strip())]
expected = sorted(local, key=entry_key) + sorted(third, key=entry_key)
if [e[0] for e in entries] != [e[0] for e in expected]:
    print('MISMATCH:')
    for i, (a, b) in enumerate(zip(entries, expected)):
        if a[0] != b[0]: print(f'  line {i+1}: {a[0]!r} -> should be {b[0]!r}')
    sys.exit(1)
print('OK')
" Cargo.toml dependencies
```

`section` 可换成 `dev-dependencies` / `build-dependencies` / `workspace.dependencies` 同样适用。

**该脚本近似于 verifier 的判定**(都基于 entry 完整长度 + dep key 字典序),但**不要用作 PR-time 唯一校验**——verifier 是 source of truth。验证自己改完后跑 `scripts/verify_dep_order.py <repo-root>` 报 0 violations 才算完工。

### 13.7.9 spirit 延伸(const.rs / 关键字文件内部顺序,2026-09-14 PR #233 实测)

本规则字面只覆盖 Cargo.toml 的 4 个 dep 块,但同样的"短在前 + 字典序 tiebreak"精神适用于同文件内同类声明的顺序。新增 `pub const FOO: T = ...;` 到 `const.rs` 时,按 (key 长度, ASCII 字典序) 找到正确位置插入,而不是 append 到末尾或紧跟在"语义相关的另一个 const"后面。

示例:`const.rs` 新增 `SNIPPETS_DIR_NAME`(长度 17)和 `SNIPPET_FILE_PREFIX`(长度 19) 时,正确位置是 `SRC_DIR_NAME`(12) 之后、`CARGO_TOML_FILE_NAME`(20) 之前——具体来说 `SNIPPETS_DIR_NAME`(17) 在 `GITIGNORE_FILE_NAME`(18) 之前,`SNIPPET_FILE_PREFIX`(19) 在 `GITIGNORE_FILE_NAME` 之后。**按字符长度,不要按"它们在 src 里属于同一 feature 就相邻"**。

`fn.rs` 内部的 `pub fn` 排序在多数项目里保留"调用顺序"(高层 wrapper 在前、底层 helper 在后),不强行套用本规则——但当一个文件里出现多个独立的 `pub fn` 且无明确调用链时(如 `pub fn` 是相互独立的 utility),同样按 `(name length, lex)` 排序更易扫读。

### 13.7.10 修订历史

| 日期 | 版本 | 规则 |
|---|---|---|
| 2026-09-14 第一轮 | user 原话"toml导入遵守整体长度从小到大排序,一样长度按照字典序从小到大排序" | 块内 (key 长度, 字典序) |
| 2026-09-14 第二轮 | §13.7 主体讲 `[dependencies]` / `[dev-dependencies]` / `[build-dependencies]` (len, lex),workspace.dependencies 单独 alphabetic,不分本地/三方 | (len, lex) + workspace.dependencies alphabetic,**无分组空行** |
| 2026-09-14 第三轮 | user 指出"三方依赖之间还有空行,只有本地依赖和三方依赖之间需要空行"——视觉上分组必须有明确语义,不能"无意义空行" | 本地 vs 三方分组,组内 alphabetic,**唯一空行在组边界** |
| **2026-09-27 round-4(当前)** | user 复盘"目前都不符合要求"——alphabetic 与第三轮差太远,实际应是 round-1 第一轮的"整体长度"规则,但**整体 = entry 整体**,不是 key 整体;verifier 与 fixer 都按 (entry 完整长度, dep key 字典序) 排序,共用 `verify_dep_order.entry_sort_key` | 块内 (entry 完整长度, dep key 字典序),本地 vs 三方分组,**唯一空行在组边界** |

round-4 是当前实现。第三轮的"组内 alphabetic"是中间迭代,user 在 2026-09-27 复盘时发现仓库距离 round-1 的"整体长度"规则差太远,明确撤回第三轮。前三轮是迭代实验——round-4 是最终版。



## 13.7.1 实战 pitfall:apply §13.7 时最容易漏 workspace.dependencies(2026-09-14 验证)

**踩坑实录**:第一次 PR review "toml 顺序"时,只盯 `[dependencies]` / `[dev-dependencies]` / `[build-dependencies]` 三个 block 重排,**完全漏掉根 `Cargo.toml` 的 `[workspace.dependencies]` 块** —— 那块有 35 个 entry 是按插入序排的。user 第二次指出后才补上,造成 2 轮返工。

**为什么会漏**:skill §13.7 主体讲 `[dependencies]` 排序规则,`[workspace.dependencies]` 单独一段说"按 alphabetic 排",视觉上像"小例外"。实际 workspace.dependencies 是 **35+ 行的最显眼 dep 块**,违反影响范围最大,反而最容易被误以为是"已经排过"的(因为 alphabetic 看起来"已经有序"了)。

**自检 Checklist — PR 提交前必跑**(覆盖 4 类 block × N 文件):

- [ ] `[dependencies]` 按 (entry 完整长度, dep key 字典序) 排
- [ ] `[dev-dependencies]` 按 (entry 完整长度, dep key 字典序) 排
- [ ] `[build-dependencies]` 按 (entry 完整长度, dep key 字典序) 排
- [ ] `[workspace.dependencies]` 按 (entry 完整长度, dep key 字典序) 排
- [ ] workspace 内所有 `Cargo.toml` 都跑过一遍,不止当前修改的那个

**自检脚本**:`scripts/verify_dep_order.py`,扫所有 workspace Cargo.toml 文件,检查 4 类 block 顺序,违规时打印精确行号 + 当前顺序 vs 期望顺序对比,exit 1。**PR 提交前必跑**(类似 `cargo fmt --check`)。

**多行 entry 的边界识别坑**(重排 workspace.dependencies 时实测踩过 2 次):

| 错误做法 | 失败模式 |
|---|---|
| 按 `key =` 字符串切片,忽略 array 多行延续 | `tokio` 的 `features = [ ... ]` 块被中途切走,生成 `tokio = { version = "1.53.1", features = [
    "rt-multi-thread",` 然后丢失续行 |
| 用 regex 找下一个 `key =` 行,但忽略 array `[` `]` bracket 深度 | array 内部的 `"Gpu",` 行被错误识别为"下一个 key 行",array 被截断;或 `]` 后下一行真正新 key 被跳过 |
| **正确做法**:`^[a-zA-Z0-9_-]+\s*=` 只匹配**行首**(无缩进),array 续行以 4 空格开头不匹配新 key;逐 entry 收集直到遇到下一个行首 `key =` 或块结束 |

**多行 entry 完整性校验**:重排完成后**用 `tomllib.loads()` parse 一遍**重排后的 Cargo.toml,如果 key 列表与重排前 tomllib parse 的 key 列表一致 → entry 切片没断。如果不一致 → 重新做,别发布。

**不要手 patch workspace.deps**:之前我尝试手 patch 的两次,都因为 array 多行识别错误破坏了文件,最后只能 `git checkout HEAD -- Cargo.toml` 回退,从头来。多行 entry 顺序调整 = 必须程序化处理,人工不靠谱。

**修订历史**:本规则在 2026-09-14 替代 §13.7 旧版"primary 本地在前 + 三方在后,secondary 长度,tertiary 字典序"。**2026-09-27 round-4 进一步修订**:之前第三轮的"组内 alphabetic"撤回,统一为"组内 (entry 完整长度, dep key 字典序)"。verifier 与 fixer 共用 `scripts/verify_dep_order.entry_sort_key` —— 单一可计算函数,不再依赖"哪里该有空行"的视觉判断。

## 13.8 `[section]` header 之间必须有空行(2026-09-27 user 钦定)

user 原话:**"Cargo.toml 不同配置字段之间需要保证有一个空行"**。任何 `Cargo.toml` 文件中,所有**顶层** `[section]` header(列首 `[xxx]` 形式,不含 `[[xxx]]` 数组元素)如果不在文件最开头,就**必须正好有 1 行空行作为前导**。

**覆盖范围**:所有 13+ 种 cargo section,包括但不限于:

| Section | 说明 |
|---|---|
| `[package]` | root crate 元数据 |
| `[workspace.package]` | workspace 共享 package 字段 |
| `[workspace]` | workspace 元数据(resolver / members) |
| `[workspace.dependencies]` | dep 块(本规则的块内排序仍由 §13.7 round-4 负责) |
| `[dependencies]` | root 依赖 |
| `[dev-dependencies]` | 开发依赖 |
| `[build-dependencies]` | build script 依赖 |
| `[lib]` | library 配置(crate-type / name / path) |
| `[[bin]]` / `[[example]]` / `[[bench]]` / `[[test]]` | 数组元素**不**算顶层 section(是已声明 section 的元素),但与上一个 section 之间仍需空行 |
| `[profile.dev]` / `[profile.release]` / `[profile.<name>]` | profile 配置 |
| `[patch.crates-io]` / `[patch.<registry>]` | patch 配置 |
| `[package.metadata.wasm-pack.profile.*]` | wasm-pack 子配置 |
| `[features]` | feature 开关 |

### 13.8.1 不适用场景

- **文件第一个** section header:文件开头不需要前导空行。
- **`[[xxx]]` 数组元素**:本身是 array-of-tables 元素,延续上一个 section 的语义,**不需要**额外空行。但若 `[[bin]]` 跟在普通配置项(非 section)后面,仍需 1 行空行。
- **section 块内部的空行规则**:由 §13.7 round-4 负责(本地/三方边界唯一空行、entry 间无空行)。**§13.8 不参与**块内。

### 13.8.2 真仓命中样例(2026-09-27)

| 仓库 | 文件 | 行 | 违规 |
|---|---|---|---|
| hyperlane | `Cargo.toml` | L70 | `[dependencies]` 紧贴 `tokio-rustls = { ... ] }` 末尾 |
| hyperlane | `core/Cargo.toml` | L21 | `[dev-dependencies]` 紧贴 `lombok-macros = { workspace = true }` |
| hyperlane | `macros/Cargo.toml` | L23 | `[dev-dependencies]` 紧贴 `proc-macro2 = { workspace = true }` |
| hyperlane | `request/Cargo.toml` | L26 | `[dev-dependencies]` 紧贴 `tokio-tungstenite = { workspace = true }` |
| hyperlane | `type/Cargo.toml` | L26 | `[dev-dependencies]` 紧贴 `serde_urlencoded = { workspace = true }` |
| ctares | `Cargo.toml` | L76 | `[profile.dev]` 紧贴 `jsonwebtoken = { version = ..., features = ["rust_crypto"] }` |
| ctares | `color-log/Cargo.toml` | L18 | `[dev-dependencies]` 紧贴 `file-operation = { workspace = true }` |

所有命中都是「多行 entry 的闭合括号 `] }` 紧接下一个 section header,无空行」。

### 13.8.3 验证

```bash
# 单跑
python3 ~/.agents/skills/rust-standards/scripts/verify_section_blanks.py <repo>

# 全 audit(包含本规则作为 check 40)
python3 ~/.agents/skills/rust-standards/scripts/audit_rust_standards.py <repo>
# → check 40 "Cargo.toml section headers separated by blank line (§13.8)" PASS/FAIL
```

**Fix 方式**:每个违规位置插入 1 个空行,**不**动 entry 文本 / 不动块内排序。验证后 commit。

**跳过**:`target/` / `~/.cargo/registry/` / `*/tmp/test_*/`(crate-cli 集成测试动态生成的 fixture,不入仓)。

### 13.8.4 修订历史

| 日期 | 规则 |
|---|---|
| **2026-09-27(当前)** | user 原话 "Cargo.toml 不同配置字段之间需要保证有一个空行"。所有顶层 `[section]` header 之间必须 1 行空行,verifier `verify_section_blanks.py` + audit check 40 同步接入 |