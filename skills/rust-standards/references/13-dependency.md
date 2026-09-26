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

## 13.7 `[dependencies]` / `[dev-dependencies]` / `[build-dependencies]` / `[workspace.dependencies]` 块内顺序(2026-09-26 第四轮修订)

四个 dep 块(`[dependencies]` / `[dev-dependencies]` / `[build-dependencies]` / `[workspace.dependencies]`)统一遵循"**本地一组 + 三方一组 + 组边界唯一空行 + 组内按 entry 完整长度升序 + 长度相同按字典序升序**"规则。

### 13.7.1 三类块的分组定义

| 块 | 本地组(在前) | 三方组(在后) |
|---|---|---|
| `[dependencies]` / `[dev-dependencies]` / `[build-dependencies]` | `euv* = { workspace = true }`(workspace 内 path-dep crate 名,无论是否标 `path = "..."`) | 其他所有 crate 名(`serde`、`tokio`、`minify-js` 等) |
| `[workspace.dependencies]` | `euv* = { path = "xxx", version = "..." }` 形式 | 其他所有 crate 名 |

**判断"本地"**:dep 的 `value` 部分包含 `workspace = true` 引用 workspace dep、或 dep 名字是 workspace member name(在 `[workspace] members` 列表里)。判定时可一行看 dep 名,二行看 value。

### 13.7.2 块内顺序

- **本地组**:成员 crate 之间按 entry **完整字符串长度**(entry 跨多行则所有行 strip 后拼接,空白无关地计算总字符数,**含** `version = "..."` / `features = [...]` / `default-features = false` 等所有字段及引号、逗号、方括号)升序排序。长度相同的 entry 按 dep `key` ASCII 字典序升序。
- **本地与三方之间**:**唯一允许的空行**(恰好 1 行 `\n`,不多不少)。
- **三方组**:**与本地组使用同一条排序规则** —— entry 完整长度升序在前、长度相同按 dep key 字典序在后。
- **块内禁有多余空行**:任何 dep entry 之间都不允许出现额外空行(只有"本地组尾 / 三方组首"这一处例外)。

### 13.7.2a 跨段空行(cross-section rule)

每个 dep block(`[dependencies]` / `[dev-dependencies]` / `[build-dependencies]` / `[workspace.dependencies]`)末 entry 与下一个非 dep section(`[patch.crates-io]` / `[profile.dev]` / `[lib]` / `[[bin]]` / `[workspace.metadata.*]` 等)之间必须**恰好 1 行空行**。这是 §13.7 第二条规则,与"块内 entry 之间不允许空行"是互补的两条:

- 块内(组内):entry 紧贴,**不**允许空行(本地-三方组边界除外,1 行);
- 块外(块末 → 下个 section):**必须有且仅有 1 行**空行分隔。

| 状态 | 含义 | 调整 |
|---|---|---|
| 0 空行(紧贴) | dep block 末 entry 与下一段同行 | fix_dep_order.py 插 1 个 `\n` |
| 1 空行 | 标准,不动 | —— |
| ≥ 2 空行 | 块尾留有过多空行 | fix_dep_order.py 收敛到 1 个 |

`verify_dep_order.py` 把这一条同样作为 PASS/FAIL 判定,与 inner order rule(`local/length/lex`)并列为 `cross-section blank`。fix_dep_order.py `--write` 时一并修复。`fix_dep_order.py` 内部 SECTION_RE 用 `(?:[^\n]*\n)*?` 配合 `(?=\s*^\[\S+\]|\Z)` lookahead —— **block 末 trailing 空行被 lookahead 之外**,fix 自动按 1 行收敛。

**例外**:dep block 是文件**最后**内容(`m.end() == len(file)`)时,不需要任何 trailing 空行分隔 —— 这是 §13.7.2b EOF rule 的领地。

### 13.7.2b 文件末尾 newline(EOF rule, round 4 修正)

TOML 文件末尾必须恰好 **`\n` 收尾 —— trailing 1 个 `\n`**(标准 Unix line-terminator 风格,匹配 `cargo new` / `rustfmt` 等工具的默认输出)。这是 round 4 的最终规则,**不是** round 3 提的"trailing 2 个 `\n` = 1 行空行"——后者被用户明确 reject("末尾都是两个空行,只需要一个",2026-09-26)。

| trailing `\n` | 含义 | 调整 |
|---|---|---|
| 0 | POSIX 违规(空文件除外) | fix_dep_order.py 末尾追加 `\n` |
| **1** | **标准 Unix(合规)** | —— |
| 2 | 末尾多余 1 行空行(round 3 残留) | fix_dep_order.py 折叠到 1 |
| 3+ | 末尾多个连续空行 | 同上折叠到 1 |

**实施细节**:`fix_dep_order.py` 在 `_rewrite_file` 末尾对 candidate content 做 `if rewritten_full: stripped = rewritten_full.rstrip("\n"); rewritten_full = stripped + "\n"` —— 不论 dep-block spans 是否触达,都会把 trailing 归一到 1。空文件(`rewritten_full == ""`) 不动。

**Pitfall(no-changes 早退会把 EOF / multi-blank 修复静默跳过)**: fixer 常见结构是 `if not changes: return False` —— 但 EOF 与 multi-blank 修复与 dep-block 重排是**正交**的两条规则。已经 round 4 合规的文件不该被跳过 EOF 检查,因为它们的 trailing 仍可能错(实测 `compress/Cargo.toml` 在 round 4 已合规但 trailing 1 `\n`,被早退漏修)。**正确做法**: 在 `if not changes:` 早退路径**也**做一段"是否需要 EOF / multi-blank 修复"的预览;两个都无需改 → 才真返回 `(False, [])`;任一个还需改 → fall through 到 `out_parts` 构造 + EOF normalize + write。也就是说 fixer 的早退短路**必须把 EOF / multi-blank 也纳入判断**,不能只看 dep-block 的 spans。

**Pitfall(verifier 与 fixer 必须共享 SECTION_RE / parse logic)**:`fix_dep_order.py` 与 `verify_dep_order.py` 不能各自写一套 SECTION_RE —— 两份 regex 必然分歧(同一 dep block 一边算 boundary 在 pos A 一边算 B,fixer 认为"刚好多 1 个 `\n`"而 verifier 报"违规多 1 个空行"循环套娃)。**正确做法**: fixer 用 `importlib.util.spec_from_file_location("v", ".../verify_dep_order.py")` 把 verifier 当模块 import,直接复用 `SECTION_RE`、`_entry_chars`、`find_cargo_tomls`、`read_local_crate_names`、`check_file_v2`。parse 层一处变更两处同时同步 —— verifier 改了,fixer 不需要重新 bake。

**Pitfall(SECTION_RE 的 trailing-`\n` 吞咽陷阱)**:`SECTION_RE` 形如 `^\[\s*<sec>\s*\]\s*\n(?P<body>.*?)(?=^\[\S+\]|\Z)` —— `.*?` 的懒匹配看起来"只到下一个 `[` 前",但 `(?P<body>.*?)` 含末尾一个 `.*` 行,**会把 block 末的 trailing blank line newline 也吞进 body**。后果:`m.end()` 指向"下一个 `[` 的位置"而不是"block 末 entry 之后的空行 newline",fixer 据此 `if text[m.end():m.end()+1].startswith("\n")` 判断 → 原文件 1 个空行 newline + 又加 1 个 → 实际产出 2 个空行 newline(= 2 行空行违规)。

**正确做法**: 让 `SECTION_RE` 显式不吞 trailing blank line:`(?P<body>(?:[^\n]*\n)*?)(?=\s*^\[\S+\]|\Z)` —— `body` 由"非空行 + `\n`"组成,block 后的空行 newline 在 lookahead 之前的 `\s*` 里。这样 `m.end()` 指向"第一个空行 newline 的下一个字符",fixer 的 cross-section 插入逻辑 `if text[m.end():m.end()+1].startswith("\n")` 才是正确的"已有空行 = 不加,无空行 = 加 1"。验证:拿一份原状是 `dep entry → \n\n → [next section]` 的 cargo.toml 跑 fix,**预期恰好 1 空行 newline**,跑出 2 行空行 = SECTION_RE bug 没修。

### 13.7.2c 多空行连续(3+ blank lines run)

不只 dep block 之间(`§13.7.2a`)和文件末尾(`§13.7.2b`),**整个文件的任何位置**都不允许出现 3 个或以上连续 `\n`(等价于 ≥ 2 行空行)。这条规则的涵盖范围补齐 `§13.7.2a` 的死角:非 dep section 之间(如 `[profile.dev]` → `[profile.release]`、`[lib]` → `[[bin]]`、`[package.metadata.*]` → 下个 `[profile.*]`)的多空行也会被逮到。

| run 长度 | 等价空行 | 调整 |
|---|---|---|
| 1 `\n` | 0(行结束) | —— |
| 2 `\n` | 1(1 行空行,合规) | —— |
| **3 `\n`** | **2 行空行(违规)** | fix_dep_order.py 用 `re.sub(r"\n\n\n+", "\n\n", rewritten_full)` 折叠 |
| 4+ `\n` | 3+ 行空行(违规) | 同上 |

**verify 实现**: `re.finditer(r"\n\n\n+", text)` 扫整个文件,每处匹配报 1 行 violation,带 `path:line` 定位方便 jump-to-line。

**fix 顺序**: `multi-blank-run → EOF trailing` —— 先把文件中段的全数折叠,再处理尾部。即使一个文件 dep block round 4 已合规但有 3+ mid-file 空行,`if not changes:` 早退路径会因 `has_multi_blank = bool(re.search(r"\n\n\n+", new))` 而 fall through,被同一 `re.sub` 一并修正。

**统一视觉节奏**: §13.7.2a + §13.7.2b + §13.7.2c 三条共同形成一条单一规则:**任何"段落边界"必须恰好 1 行空行,与边界是不是 dep block / 非 dep section / EOF 无关**。

### 13.7.3 "完整长度"的精确定义

entry 的"完整长度"按以下方式计算:

1. **多行 entry**:每行都 strip 掉首尾空白(去掉 indent 与尾随空格);把所有非空行用 `""` 拼起来(等价于把续行接在同一行)。
2. **空白无关**:再把所有空白字符(空格、tab)去掉(保留字母、数字、`=`,`{`,`}`,`"`,`,`,`[`,`]`,`.`,`-`)。这一步是为了避免 `toml` formatter(`taplo`)的 `=` 两侧空格 / 4 空格缩进等 formatting 偏好影响排序。
3. **结果**:`len(re.sub(r"\s+", "", "<entry-joined>"))`。

示例:

| entry 写法 | 规范化后 | 长度 |
|---|---|---|
| `foo = "1.0"` | `foo="1.0"` | 9 |
| `serde = { version = "1.0.229", features = ["derive"] }` | `serde={version="1.0.229",features=["derive"]}` | 46 |
| `notify = { version = "8.2.0", default-features = false, features = [<br>    "macos_fsevent",<br>] }` | `notify={version="8.2.0",default-features=false,features=["macos_fsevent",]}` | 82 |

**为什么不取"key 长度"**:同一个 dep 名只能出现一次,key 长度对同一 dep 的不同 fields 形式无法区分(`serde = "1.0"` 与 `serde = { version = "1.0", features = ["derive"] }` 都是 `serde` key,但 entry 长度差很多)。entry 完整长度 = 包含 fields 后的总长,才能反映"这条 dep 总共占多少视觉空间"。

**为什么不取纯 alphabetic**:同一个 depset 里,短 entry 与长 entry 混杂时,alphabetic 与 length 给出截然不同的结果:

| dep | 长度 | alphabetic 序 | (长度,字典序) 序 |
|---|---|---|---|
| `serde_json = "1.0.151"` | 23 | 1 | 1 |
| `toml = "0.9.12"` | 14 | 3 | 2 |
| `serde = { version = "1.0.229", features = ["derive"] }` | 46 | 2 | 3 |

alphabetic 把短 entry 的 `serde` 排在了 `toml` 之后,但视觉上明显 `toml` 更短。**user 原话"完整长度(含特性等字段)升序"明确选了长度优先**。

### 13.7.4 为什么不再分组空行,而是只用 entry 长度排序

第三轮(已废)把"本地 vs 三方"用唯一空行分隔,但组内还是 alphabetic,导致三方组里又出现"短一条、长一条,无视觉规律"。第四轮改成 entry 完整长度升序:**短 entry 紧密堆在前,长 entry 渐次靠后,两组合在一起形成一条自然的视觉纵深,不再需要任何次级分组**。"本地组末尾空行"是分组语义,不是装饰——空着的两侧一边是 `euv*` 系列,一边是 `serde` / `tokio` / `chrono` 等三方 crate,扫一眼就知道"这边本地、那边三方",这是空行的语义价值;组内多空行(空行之间无分组差异)则是装饰,user 第三轮已废。

### 13.7.5 例(`example/Cargo.toml` `[dependencies]`,全用 `workspace = true`)

按 entry 完整长度排序:

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

每个 entry 规范化后形如 `key={workspace=true}`,长度 = key 长度 + 固定外壳 17 字符。

**本地组**:`euv`(20) → `euv-ui`(23) → `euv-core`(25) → `euv-engine`(27) → `euv-macros`(27,字典序 `euv-engine` < `euv-macros`)。

**三方组**:`serde`(20) / `tokio`(20,字典序 `serde` < `tokio`) → `chrono`(21) → `hyperlane`(23) → `serde_json`(25) → `color-output`(27) → `compare_version`(31) → `console_error_panic_hook`(41)。

跨组同长度实例:`serde_json`(25) 与 `euv-core`(25),各自组内字典序对齐,组与组无相对顺序。

### 13.7.6 例(根 `Cargo.toml` `[workspace.dependencies]`)

按 entry 完整长度升序排列(短 entry 在前,长 entry 在后)。workspace.dependencies 里的三元组每个 value 长度差异较大(`euv = { path = ".", version = "0.24.6" }` 短;`web-sys = { version = "0.3.103", features = [...] }` 长),排成由短到长的"金字塔",扫一眼就能找到新加 dep 应该插入的位置。

```toml
[workspace.dependencies]
euv = { path = ".", version = "0.24.6" }
euv-ui = { path = "ui", version = "0.24.6" }
euv-cli = { path = "cli", version = "0.24.6" }
euv-core = { path = "core", version = "0.24.6" }
euv-engine = { path = "engine", version = "0.24.6" }
euv-example = { path = "example", version = "0.24.6" }
euv-macros = { path = "macros", version = "0.24.6" }

log = "0.4.33"
toml = "0.9.12"
clap = "4.6.4"
serde = "1.0.229"
chrono = "0.4.45"
ignore = "0.4.31"
if-addrs = "0.15.0"
syn = "2.0.119"
quote = "1.0.47"
js-sys = "0.3.103"
minify-js = "0.6.0"
hyperlane = "21.3.6"
qrcode = "0.14.1"
lombok-macros = "2.1.0"
proc-macro2 = "1.0.107"
color-output = "10.0.10"
serde_json = "1.0.151"
compare_version = "2.0.14"
hyperlane-cli = "0.1.25"
wasm-bindgen = "0.2.126"
serde-wasm-bindgen = "0.6.5"
console_error_panic_hook = "0.1.7"
wasm-bindgen-test = "0.3.76"
wasm-bindgen-futures = "0.4.76"
alloc-no-stdlib = "=2.0.4"
clap = { version = "4.6.4", features = ["derive"] }
serde = { version = "1.0.229", features = ["derive"] }
notify = { version = "8.2.0", default-features = false, features = [
    "macos_fsevent",
] }
syn = { version = "2.0.119", features = ["full", "extra-traits"] }
tokio = { version = "1.53.1", features = ["rt-multi-thread", "macros"] }
qrcode = { version = "0.14.1", default-features = false }
web-sys = { version = "0.3.103", features = [...] }
```

**本地组**:`euv = { path = ".", version = "0.24.6" }`(路径最短 `.`)长度最小,然后按 path 字符串长度递增到 `euv-macros = { path = "macros", version = "0.24.6" }`(`macros` 6 字符)。

**三方组**:从 `log = "0.4.33"`(约 14 字符)等短字符串 entry 开始,逐步过渡到 `web-sys = { version = "0.3.103", features = [...] }`(几十字符)、`notify = { ... features = [...] }`(多行 + 嵌套)、`tokio = { ... features = ["rt-multi-thread", "macros"] }`、`syn = { ... features = ["full", "extra-traits"] }` 等长 entry。**简短到长,排列成视觉纵深**。

> **注**:同一 dep 的不同 fields 形式(如 `clap = "4.6.4"` 与 `clap = { version = "4.6.4", features = ["derive"] }`)在视觉上长度差很多。**真实仓库里它们不会同存** —— workspace.dependencies 选中后总是用最长最全的 form(包含所有需要的 features),子 crate 用 `clap = { workspace = true }` 继承同一 entry。

### 13.7.7 PR 提交前自检(Python 按 entry 长度 + 字典序 sort 验证)

```bash
python3 -c "
import re, sys
path = sys.argv[1]
section = sys.argv[2]
text = open(path).read()
m = re.search(r'^\[' + section + r'\]\n(.*?)(?=^\[|\Z)', text, re.S | re.M)
if not m: sys.exit(0)
block = m.group(1)

# 1) 把 block 内所有 dep entry 切成完整的 (key, body_lines)
items = []
lines = block.splitlines()
cur_key, cur_lines = None, []
for line in lines:
    if not line.strip():
        if cur_key is not None:
            items.append((cur_key, ''.join(cur_lines)))
            cur_key, cur_lines = None, []
        continue
    mm = re.match(r'^([a-zA-Z0-9_-]+)\s*=', line)
    if mm:
        if cur_key is not None:
            items.append((cur_key, ''.join(cur_lines)))
        cur_key, cur_lines = mm.group(1), [line]
    elif cur_key is not None:
        cur_lines.append(line)
if cur_key is not None:
    items.append((cur_key, ''.join(cur_lines)))

# 2) 计算 entry 完整长度:strip 每行 → join → 去所有空白
def char_count(it):
    body = ' '.join(it[1].split())  # strip + 合并多行空白
    return len(re.sub(r'\s+', '', body))

# 3) 判定本地(workspace member 简化:本仓前缀 — 实际项目按 §13.7.1 调整)
def is_local(key):
    return key.startswith('euv')

# 4) 组内按 (entry 完整长度, 字典序) 升序
local = sorted([it for it in items if is_local(it[0])], key=lambda it: (char_count(it), it[0]))
third = sorted([it for it in items if not is_local(it[0])], key=lambda it: (char_count(it), it[0]))
expected = [k for k, _ in local] + [k for k, _ in third]
actual = [k for k, _ in items]
if actual != expected:
    print('MISMATCH:')
    for i, (a, b) in enumerate(zip(actual, expected)):
        if a != b: print(f'  position {i+1}: {a!r} -> should be {b!r}')
    sys.exit(1)
print('OK')
" Cargo.toml dependencies
```

`section` 可换成 `dev-dependencies` / `build-dependencies` / `workspace.dependencies` 同样适用。

**`is_local` 的边界**:简化判定按 dep key 前缀(`euv` 开头 = 本地)。真正的 workspace 可能本地组用别的命名(如 `crates`、`crates-*`、`type` / `cli` / `core` / `macros` / `engine` / `docs-pages` 等无统一前缀),改 `is_local` 函数读取 `[workspace] members` 列表 + 子 crate 的 `[package] name`,与 `verify_dep_order.py` 的 `read_local_crate_names` 一致。脚本里的 `is_local` 仅为示例,真实使用参考 `scripts/verify_dep_order.py`(已同步支持 entry 长度排序)。

### 13.7.8 spirit 延伸(const.rs / 关键字文件内部顺序,2026-09-14 PR #233 实测)

本规则字面只覆盖 Cargo.toml 的 4 个 dep 块,但同样的"短在前 + 字典序 tiebreak"精神适用于同文件内同类声明的顺序。新增 `pub const FOO: T = ...;` 到 `const.rs` 时,按 (key 长度, ASCII 字典序) 找到正确位置插入,而不是 append 到末尾或紧跟在"语义相关的另一个 const"后面。

示例:`const.rs` 新增 `SNIPPETS_DIR_NAME`(长度 17)和 `SNIPPET_FILE_PREFIX`(长度 19) 时,正确位置是 `SRC_DIR_NAME`(12) 之后、`CARGO_TOML_FILE_NAME`(20) 之前——具体来说 `SNIPPETS_DIR_NAME`(17) 在 `GITIGNORE_FILE_NAME`(18) 之前,`SNIPPET_FILE_PREFIX`(19) 在 `GITIGNORE_FILE_NAME` 之后。**按字符长度,不要按"它们在 src 里属于同一 feature 就相邻"**。

`fn.rs` 内部的 `pub fn` 排序在多数项目里保留"调用顺序"(高层 wrapper 在前、底层 helper 在后),不强行套用本规则——但当一个文件里出现多个独立的 `pub fn` 且无明确调用链时(如 `pub fn` 是相互独立的 utility),同样按 `(name length, lex)` 排序更易扫读。

### 13.7.9 修订历史

| 日期 | 版本 | 规则 |
|---|---|---|
| 2026-09-14 第一轮 | user 原话"toml导入遵守整体长度从小到大排序,一样长度按照字典序从小到大排序" | 块内 (key 长度, 字典序) |
| 2026-09-14 第二轮 | §13.7 主体讲 `[dependencies]` / `[dev-dependencies]` / `[build-dependencies]` (len, lex),workspace.dependencies 单独 alphabetic,不分本地/三方 | (len, lex) + workspace.dependencies alphabetic,**无分组空行** |
| 2026-09-14 第三轮 | user 指出"三方依赖之间还有空行,只有本地依赖和三方依赖之间需要空行"——视觉上分组必须有明确语义,不能"无意义空行" | 本地 vs 三方分组,组内 alphabetic,**唯一空行在组边界** |
| **2026-09-26 第四轮(当前)** | user 原话"toml依赖导入需要严格遵守顺序,首先本地依赖是同一组,外部依赖是一组,不同组之间需要空行分割,同组之间按照完整的长度(含特性等字段)升序排序,一样的长度按照字典序升序"——第三轮组内 alphabetic 让"短 entry 与长 entry 混杂"看不到规律,改成"完整长度"排序形成视觉纵深 | 本地 vs 三方分组(保留),组内按 **entry 完整长度** 升序 + 长度相同按字典序,唯一空行在组边界 |

第四轮是最终版。前三轮是迭代实验——user 给出简化后立即采纳,不保留任何"也许保留分组更合理"的犹豫。**第三轮 → 第四轮的关键 diff**:第三轮组内 `sorted(local) + sorted(third)`(alphabetic),第四轮组内 `sorted(local, key=(len, lex)) + sorted(third, key=(len, lex))`(长度优先 + 字典序 tiebreak)。



## 13.7.1 实战 pitfall:apply §13.7 时最容易漏 workspace.dependencies(2026-09-14 验证)

**踩坑实录**:第一次 PR review "toml 顺序"时,只盯 `[dependencies]` / `[dev-dependencies]` / `[build-dependencies]` 三个 block 重排,**完全漏掉根 `Cargo.toml` 的 `[workspace.dependencies]` 块** —— 那块有 35 个 entry 是按插入序排的。user 第二次指出后才补上,造成 2 轮返工。

**为什么会漏**:skill §13.7 主体讲 `[dependencies]` 排序规则,`[workspace.dependencies]` 单独一段说"按 alphabetic 排",视觉上像"小例外"。实际 workspace.dependencies 是 **35+ 行的最显眼 dep 块**,违反影响范围最大,反而最容易被误以为是"已经排过"的(因为 alphabetic 看起来"已经有序"了)。

**自检 Checklist — PR 提交前必跑**(覆盖 4 类 block × N 文件):

- [ ] `[dependencies]` 按 (entry 完整长度, dep key ASCII 字典序) 升序排,本地组在前,三方组在后,唯一空行在组边界
- [ ] `[dev-dependencies]` 同上
- [ ] `[build-dependencies]` 同上
- [ ] `[workspace.dependencies]` 同上(**最容易漏**)
- [ ] workspace 内所有 `Cargo.toml` 都跑过一遍,不止当前修改的那个

**自检脚本**:`scripts/verify_dep_order.py`,扫所有 workspace Cargo.toml 文件,检查 4 类 block 顺序(按 entry 完整长度 + 字典序),违规时打印实际顺序 vs 期望顺序对比,exit 1。**PR 提交前必跑**(类似 `cargo fmt --check`)。

**多行 entry 的边界识别坑**(重排 workspace.dependencies 时实测踩过 2 次):

| 错误做法 | 失败模式 |
|---|---|
| 按 `key =` 字符串切片,忽略 array 多行延续 | `tokio` 的 `features = [ ... ]` 块被中途切走,生成 `tokio = { version = "1.53.1", features = [
    "rt-multi-thread",` 然后丢失续行 |
| 用 regex 找下一个 `key =` 行,但忽略 array `[` `]` bracket 深度 | array 内部的 `"Gpu",` 行被错误识别为"下一个 key 行",array 被截断;或 `]` 后下一行真正新 key 被跳过 |
| **正确做法**:`^[a-zA-Z0-9_-]+\s*=` 只匹配**行首**(无缩进),array 续行以 4 空格开头不匹配新 key;逐 entry 收集直到遇到下一个行首 `key =` 或块结束 |

**多行 entry 完整性校验**:重排完成后**用 `tomllib.loads()` parse 一遍**重排后的 Cargo.toml,如果 key 列表与重排前 tomllib parse 的 key 列表一致 → entry 切片没断。如果不一致 → 重新做,别发布。

**不要手 patch workspace.deps**:之前我尝试手 patch 的两次,都因为 array 多行识别错误破坏了文件,最后只能 `git checkout HEAD -- Cargo.toml` 回退,从头来。多行 entry 顺序调整 = 必须程序化处理,人工不靠谱。

**修订历史**:本规则在 2026-09-26 第四轮升级为"entry 完整长度 + 字典序"组合排序。前三轮(2026-09-14 第一轮 (key 长度, 字典序) → 第二轮 workspace.dependencies alphabetic → 第三轮 本地 vs 三方分组 + 组内 alphabetic)迭代到 user 明确指出"完整长度(含特性等字段)升序",第四轮定稿。**verify_dep_order.py 已同步升级**:本地与三方分组保留,组内排序 key 从 `lambda x: x[0]`(纯字典序)改为 `lambda x: (len(re.sub(r"\s+", "", "".join(x[1]))), x[0])`(entry 完整长度 + 字典序 tiebreak)。旧版的"alphabetic 简单可计算"动机已被"完整长度能传达视觉纵深"取代 —— 单 rule 不变,排序键换了。

## 13.8 `[workspace.package]` 字段聚合(2026-09-26 verified ctares workspace 迁移)

把多个 `[package]` 块的共享字段统一到根 `[workspace.package]` + 子 crate `*.workspace = true` 是 workspace 维护的常规整理。规则:哪些字段能聚合、哪些不能、迁移时哪些 CI 路径会断,以及聚合后的版本/bump 流程。

### 13.8.1 字段聚合决策表

**能聚合**(所有子 crate 取值相同 → 提升到 `[workspace.package]`):

| 字段 | 取值例 | 备注 |
|---|---|---|
| `version` | `"10.1.7"` | 提升后所有子 crate 同 version;统一打 tag / `cc publish` 时单一 source of truth |
| `edition` | `"2024"` | 长期不变,聚合后无修改成本 |
| `rust-version` | `"1.85"` | MSRV 字段;全 workspace 相同 MSRV |
| `license` | `"MIT"` | 项目级许可,统一 |
| `license-file` | `"LICENSE.md"` | 仅当所有子 crate 同一许可文件时 |
| `readme` | `"README.md"` | 全 workspace 同一 readme |
| `authors` | `["root@ltpp.vip"]` | 项目维护者列表 |
| `repository` | `"https://github.com/crates-dev/ctares"` | crates.io 链接主页 |
| `homepage` | `"https://..."` | 同上 |
| `documentation` | `"https://..."` | 同上 |
| `exclude` | 聚合**去重**:每个子 crate 原来 `exclude = [..]` 的并集,保留所有出现过的条目;典型的 10 项 `[**/*.log, **/*.pid, .github, Cargo.lock, debug, img, logs, sh, target, uploads]` | |
| `include` | 同 `exclude` 聚合去重(一般项目用不到) | |

**不能聚合**(每个子 crate 异构 → 必须保留每个 `[package]` 块独立):

| 字段 | 为什么不能聚合 |
|---|---|
| `name` | crates.io 主键,每个 crate 必须独立,workspace inheritance 对 `name` **不生效** |
| `description` | crates.io 搜索结果展示,语义每个 crate 不同 |
| `keywords` | 同上,搜索相关,每 crate 不同的 5 词组 |
| `categories` | **per-crate 语义**:同一 workspace 里 `bin-encode-decode` 上 `[encoding]`,`gtl` 上 `[development-tools, command-line-interface]`,`jwt-service` 上 `[authentication, cryptography, encoding]` —— crates.io 分类的语义是"这个 crate 是什么",不是"这个 workspace 是什么"。**不可聚合**(见 `references/13-dependency.md §13.8.4` 反例案例)。聚合后 `categories = [...]` 会被 workspace inheritance 强制成同一份,所有 crate 显示同一组 categories,crates.io 会标 "category mismatch"(尤其当 `bin-encode-decode` 显示 `[development-tools, command-line-interface]` 时,它**不是** CLI 工具) |
| `publish` | `publish = false` 只对 root / example / playground crate 用;其他 crate 默认 `true` |

**特例**(聚合后**禁用**默认值,显式设回):

- 子 crate 的 `[lib]` / `[[bin]]` 段:这些是 `[package]` **之外的**段,**不能被 workspace inheritance**。子 crate 的 proc-macro 必须 `proc-macro = true;`、bin 的 `name = "..."` / `path = "src/main.rs"` 必须各自保留(workspace inheritance 只作用于 `[package]` 段的特定字段列表)

### 13.8.2 子 crate `[package]` 块标准模板(聚合后)

```toml
[package]
name = "<crate-name>"
description = "<crate-specific>"
keywords = ["<crate-specific>"]
categories = ["<crate-specific>"]
version.workspace = true
edition.workspace = true
rust-version.workspace = true
license.workspace = true
readme.workspace = true
authors.workspace = true
repository.workspace = true
exclude.workspace = true
```

7 个 `*.workspace = true` 必须**紧贴无空行**(`name` 之后空 1 行再开始,后续字段间无空行;`description` / `keywords` / `categories` 之前空 1 行作为 `[package]` 段内的视觉分组)。这与 `§13.7.2a` 一致:workspace inheritance 字段 = 一个组,与下面的"per-crate 字段"(description/keywords/categories)段间恰好 1 行空行。

### 13.8.3 根 `Cargo.toml [workspace.package]` 标准模板

```toml
[workspace]
resolver = "2"
members = ["<dir>", ...]

[workspace.package]
version = "10.1.7"
edition = "2024"
rust-version = "1.85"
license = "MIT"
readme = "README.md"
authors = ["root@ltpp.vip"]
repository = "https://github.com/crates-dev/ctares"
exclude = ["**/*.log", "**/*.pid", ".github", "Cargo.lock", "debug", "img", "logs", "sh", "target", "uploads"]
```

**字段顺序无强制**(不像 `[dependencies]` 那样的强排序)。但**经验上**保持与子 crate `[package]` 同序,便于扫读:

```
version → edition → rust-version → license → readme → authors → repository → exclude
```

### 13.8.4 **Pitfall(`categories` 不能聚合到 `[workspace.package]`)**

用户的反例:**先**建议把 `categories` 也聚合(我做了 22 子 crate + 根 `[workspace.package].categories = [...10 项...]`),**下一轮立刻推翻**("categories 不需要")。完整 revert:根块删除 `categories`,22 子 crate 各自回退到原始 hardcoded `categories = [...]`。

**为什么会推翻**:crates.io 的 `categories` 是单 crate 语义,不是 workspace 语义。聚合后所有 crate 显示同一组 categories,**对 crates.io 搜索是错的**(例:`bin-encode-decode` 显示 `[command-line-interface]` 但它不是 CLI 工具)。crates.io 上传后会发 "category mismatch" 警告,某些 category 甚至可能被 review 拒绝。

**Workflow 行为**:用户的反转信号是 **first-class** —— 任何 `*.workspace = true` 建议都应当作 tentative 直到用户 commit。**两个相邻回合内**用户反复调整 workspace 决策(用/不用 workspace)是常态,不要把第一轮提交当作定稿。

### 13.8.5 **Pitfall(workspace field 迁移会让 CI 的 `grep '^version = '` 失效)**

**踩坑实录**(ctares):迁移到 `[workspace.package].version = "10.1.7"` 后,所有子 crate 的 `version = "..."` 被替换成 `version.workspace = true`。**`.github/workflows/rust.yml` 里两处 setup job** 用 `grep '^version = ' crate-cli/Cargo.toml | head -1 | sed -E 's/^version = "([^"]+)".*/\1/'` 提取版本号。**新结构下 `crate-cli/Cargo.toml` 不再有 `^version = ` 匹配**,grep 返回空,VERSION 为空,job exit 1。CI run 全部下游 job `skipped`,**本地 `cargo check / clippy / fmt` 全绿**但 GitHub Actions 报错。

**根因**:CI 把"某子 crate 的硬编码 `version` 行"当作 version source of truth。当 version 提升到 workspace 后,这种 grep **必须改成读根 `Cargo.toml`**。

**修复**(具体 patch):

```diff
- VERSION=$(grep -E '^version = ' crate-cli/Cargo.toml | head -1 | sed -E 's/^version = "([^"]+)".*/\1/')
+ VERSION=$(grep -E '^version = ' Cargo.toml | head -1 | sed -E 's/^version = "([^"]+)".*/\1/')
```

**两处都要改**(setup job + publish job 的 `SYNCED_VERSION`)。

**前置检查**:任何 `*.workspace = true` 迁移前,**先 `grep -rn 'version[[:space:]]*=' .github/workflows/`**,把硬编码的"`xxx-crate/Cargo.toml` 路径"全部列出来,**对每个 grep 都切换成根 `Cargo.toml`** 或更稳定的 `cargo metadata --format-version=1 | jq -r '.packages[] | select(.name=="crate-cli") | .version'`。后者更稳(不依赖 grep 文本格式)。

**其他 CI 路径会断**(同模式):
- `setup` job 之外任何 step 用了 `^version = "X.Y.Z"` regex 匹配子 crate
- 文档生成脚本(`docs/Cargo.toml` 或 `mkdocs.yml` 引用子 crate version)
- release-note 自动生成器
- 第三方 release tooling(dependabot / release-please)读 git tree

**Pitfall(本地 `cargo check` / `cargo clippy` / `cargo fmt` 全绿但 CI 红)**: 这是 workspace field 迁移的典型 CI-only 失败模式。**提交前必跑一次实际 GitHub Actions**:本地 verify 不能覆盖 CI 的 `grep` / `sed` 路径,因为 CI grep 的是 git tree 而不是本机解析后的 manifest。

### 13.8.6 **Pitfall(workspace field 迁移后 `crate bump` / `cc bump` 行为改变)**

**`crate bump` 三种架构模式**(`crates-cli-usage` 已记录):

1. **单 crate**(非 monorepo):bump 那个 crate
2. **virtual workspace**(members only):bump 每个 member,**模式 3**(heterogeneous workspace,无 `[workspace.package].version`):每个 member **保留自己的 major.minor**,+1 patch。`color-output@10.1.6 → 10.1.7`、`crate-cli@0.2.8 → 0.2.9` 同一 pass
3. **monorepo with root package**:bump root + 所有 members

**workspace field 迁移后**:`[workspace.package].version` 已设,`*.workspace = true` 已铺好 → `crate bump --patch` 应当**只改根的 `[workspace.package].version` 一行**,子 crate 自动跟随。如果 `crate bump` 仍然 touch 子 crate 的 `version = "..."` 行,说明子 crate 没改成 `version.workspace = true` —— 检查迁移是否彻底。

**`crate sync` 行为**(`crates-cli-usage` 已记录 + 2026-09-26 ctares workspace migration 验证):

- 有 `[workspace.package].version` 的 workspace:把 `[workspace.dependencies]` 的 path entries **对齐到根版本**
- 无 `[workspace.package].version` 的 heterogeneous workspace:把每个 path entry **对齐到该 member 自己的 version**
- 有 `path = "."` 的根包自引用:**总是对齐**

**`crates-cli-usage` 已记录**这些行为,但**用户在迁移后是第一次体验到完整链路**:先 `crate bump --patch`(模式 3 自动进入,bump 22 子 crate 到 X.Y.7)→ 把所有子 crate 改成 `version.workspace = true` → 把根 `[workspace.package].version` 设到最大 +1 → **`crate sync` 把 4 个 `[workspace.dependencies]` path entries 对齐到根版本**(否则 `cargo check` 失败,dep 引用 stale)。`crate sync` 的 idempotency 保证迁移安全:重复跑不产生额外 diff。

### 13.8.7 迁移 checklist(PR review 必跑)

- [ ] 根 `[workspace.package]` 含所有要聚合的字段(`version` / `edition` / `rust-version` / `license` / `readme` / `authors` / `repository` / `exclude` 聚合去重)
- [ ] 每个子 crate `[package]` 只保留 `name` + per-crate 字段(`description` / `keywords` / `categories`)+ 7 个 `*.workspace = true`
- [ ] **categories 没被聚合**(每个子 crate `categories = [...]` 仍是各自的)
- [ ] 子 crate `[lib]` / `[[bin]]` 段未被修改(workspace inheritance 不影响这些段)
- [ ] **`grep -rn '^version[[:space:]]*=' .github/workflows/`** 列出所有 CI grep,对每个 grep 切换 grep 目标到根 `Cargo.toml` 或用 `cargo metadata`
- [ ] **`cargo check --workspace`** + `cargo fmt --all -- --check` + `cargo clippy --workspace --all-targets -- -D warnings` 全 0
- [ ] **`crate sync`** 跑过且 idempotent(re-run 不产生新 diff)
- [ ] **真实 GitHub Actions 跑一次**(不是只看本地 verify) — CI-only 失败模式必须用 CI 检验
- [ ] **`verify_ci_no_bump.py <repo>`** 仍然 exit 0(workspace 迁移不该触发这个 verifier 失败,但 sed/perl/python3 重写 `version =` 行的 inline script 会触发)

### 13.8.8 修订历史

| 日期 | 版本 | 规则 |
|---|---|---|
| 2026-09-26 第一轮 | ctares 22 子 crate 聚合 `readme` / `edition` / `authors` / `repository` / `exclude` / `version` / `license` / `rust-version` 到根 `[workspace.package]` | 字段聚合决策表(§13.8.1)+ `categories` 反例(§13.8.4)+ CI grep 失效 pitfall(§13.8.5)+ `crate bump` / `crate sync` 迁移后行为(§13.8.6) |