---
name: rust-standards
description: 'Rust 开发规范(最高优先级,与任何 skill 冲突时以此为准)。**任何写 / 改 / 审查 Rust 代码、`.rs` 文件、`Cargo.toml`、cargo 命令、euv / hyperlane / wasm / proc-macro / ServerHook / Signal 的任务,在写第一行代码 / 第一次回答之前必须 `skill_view("rust-standards")` —— 不靠 description 软触发。不加载本 skill 写出的 Rust 代码会被开发者 review 直接驳回,不得 commit / push / 提 PR**。互锁:euv 任务必同时加载 `euv-standards` + `euv-ui-standards`;hyperlane 任务必同时加载 `hyperlane-standards`。适用于:新项目脚手架、现有 Rust 代码维护、PR 审查、重构、模块划分、命名、错误处理、性能优化、依赖管理、测试策略。涵盖硬性规则:9 种关键字文件纯净 / raw identifier / mod.rs 三段式 / lib.rs 集中导入 / 显式类型 / 泛型 where / WASM 禁 inline / fmt 双幂等 / 测试放 tests/。'
---

# Rust 开发规范

## ⚠️ 强制加载声明(本节每次会话必须读)

**本 skill 是 Rust 代码开发的硬性 gate。** 不读本 skill 直接写 Rust 代码 = 开发者 review 直接驳回,PR 不得合并。

### 为什么这是强制的

1. **9 种关键字文件纯净性**(§1.3a)、`lib.rs` 集中导入(§6.1/§6.4)、`mod.rs` 三段式(§1/§6)、泛型 `where`(§9.2)、WASM 禁 `inline`(§4.3)、fmt 双幂等(§13)—— 这些是**只有读完本 skill 才能知道**的项目级约定,**没有第二个信号源**。
2. **漏一项就被驳回**。已实证案例:euv 仓 PR #202 全程 5 次违规被用户纠正才合入;`engine/src/renderer/impl.rs` 因 `fn cached_method_name` in `impl.rs` 触发 §1.3a review reject;fn 内 `use std::xxx;` 触发 §6.4 + clippy `unused_imports`;fn 体空行触发 §9.5。
3. **本 skill 是 eastspire/.agents 项目的 living spec**。其他 skill 不替代。

### 触发条件(满足任一即必须加载)

| 任务场景 | 必须加载 |
|---------|---------|
| 用户说"写 Rust 代码"、"改 Cargo.toml"、"修 .rs 文件" | ✅ |
| 用户提到 cargo / rustc / clippy / cargo fmt / cargo test | ✅ |
| 用户提到 euv / hyperlane / html! / class! / ServerHook / Signal | ✅(互锁 `euv-standards` + `euv-ui-standards` / `hyperlane-standards`) |
| 用户提到 wasm / wasm-pack / WebAssembly / wasm32 | ✅ |
| 用户提到 proc-macro / 过程宏 / `#[proc_macro_derive]` / `#[proc_macro_attribute]` | ✅ |
| 用户给一段 Rust 代码让你 review / 改 / 优化 / 重构 | ✅ |
| 用户让你 clone / fork 一个 Rust 项目 | ✅ |
| 你发现自己在 terminal 准备跑 `cargo ...` | ✅ |
| **你刚把 `use super::*;` 加进子文件,准备写 `external_crate::Sym` 调用** | ✅(先看下 §6.4 pitfall-b,audit 不覆盖这个)|
| **不确定是否相关** | ✅(错的代价是几 KB context,不加载的代价是 PR 被驳回) |

### 加载顺序(每次新会话第一件事)

1. `skill_view('rust-standards')` 加载本文件(必)
2. 写 Rust 代码前通读 `## 关键硬性规则`(15 条)
3. 写 Rust 代码前读对应子章节(目录结构 / mod.rs 三段式 / lib.rs 导入 / 测试位置 ...)
4. 写完后跑 `## Pre-commit 必跑`(audit + fmt 双幂等 + clippy + test 编译)
5. **跑完 18/18 audit + clippy 0 警告 + fmt 幂等 + 测试通过** → 才能 commit / push / 提 PR

### 违反本 skill 的后果(实证)

- ❌ **review reject**: maintainer / 开发者 review 时发现违规 → 打回 + 要求 fix + 重审 → 拖延 PR 合并数小时到数天
- ❌ **clippy 红**: 漏 §6.1/§6.4 → clippy `unused_imports`;漏 §9.5 → audit 红
- ❌ **CI fail**: 漏 fmt 双幂等 → `Format check` job fail
- ❌ **历史教训**: euv PR #202 因未先加载本 skill,5 次违规被纠正才入仓;rust PR #148-#151 因小版本 bump 铁律未加载 spec,被 revert 重做;PR #21 fn 命名违规导致 review 拖延

**结论**: 任何写 Rust 代码之前**必须**加载本 skill。**没读 = 不能写**。

## 始终生效的工程原则(2026-09-26)

> **「所有的校验应该通过使用脚本执行完成,提示词只是约束,脚本做验证」**——用户原话。

这条规则适用于 rust-standards 整套:任何 §13 / §14 / 任何 git hook / PR review / audit step,**禁止靠 prompt 里复述规则并期望 agent 心算"对的"。校验规则必须有可执行的脚本**:

| 校验类型 | 必有产物 |
|---|---|
| 结构合规 | `scripts/verify_*.py` 或 `scripts/verify_*.sh`,exit 0/1,被 audit 套件 wrap |
| 单调合规 | `scripts/strictify_*.py` 或 `scripts/fix_*.py`,**默认 dry-run** + `--write`,完成后自动 re-verify,二次运行幂等 |
| CI gate | `.github/workflows/*.yml` job 跑上述脚本,exit 非零 fail build |

**反面例子**(auto-detect 违规):只在 SKILL.md / references 里写规则文本,不写脚本 → PR review 时 reviewer 心算 → 主观不一致 → 漏检。**改任何 § 条款前先问:**"这条规则能不能写成一个 exit 0/1 的脚本?"——能 → 必须写;不能 → 在 § 里明确写"NIGHTLY-CHECK-FAIL-XX 必须人工 review",留给 audit-pitfalls 兜底。

**新增 audit check 的硬性流程**(2026-09-26 实测 fix_dep_order.py 接入):

1. **写校验脚本 `scripts/verify_<rule>.py`**:单一真相源,exit code 是唯一 truth
2. **写 auto-fixer `scripts/fix_<rule>.py`**:默认 dry-run,re-import 校验脚本的 parse logic(避免两套 parser 分歧)
   - **Pitfall(dry-run 阶段不要悄悄写盘)**:`fix_<rule>.py` 默认 `--dry-run` 但内部 `_rewrite_file(path)` 一旦 `if changed: path.write_text(...)` 会**让 dry-run 与第一次扫描在主进程里直接修改文件** —— 用户看到的"dry-run 输出"和"真实落盘"差异为 0,看起来"无副作用"实则悄悄改了文件。第二次跑 `--write` 改完后再 dry-run,**干跑反而覆盖了第一次的写盘**(实测 `fix_dep_order.py` 在 round-3 这样导致同一 section 被重复插入空行,污染成 4 行空行)。**正确做法**:`_rewrite_file` 加 `*, write: bool = True` 关键字参数;所有 `path.write_text(...)` 用 `if write:` 控;`if not args.write: return False, []` 在收集 spans 阶段早退,绝对不把 candidate 写盘。验证:第一次 `python3 fix_xxx.py <repo>`(无 `--write`)跑完,`git status --short` 必须空。
3. **双向 fixture 自测**:compliant 仓 → exit 0;violated 仓 → exit 1 + 打印实际 vs 期望 diff。**接入 audit 前必须两路都通过**
4. **在 audit 第 N 项 wrap**:用 `python3 "{{audit_script_dir}}/verify_<rule>.py` + `grep -v` 过滤成功尾随(`=== OK: N files` / `=== no-comments-in-tests: 0 violation(s)` 类 summary 行)+ `PIPESTATUS[0]` 传递 exit code。**Pitfall(FAIL trailer 必须走 stderr 不走 stdout)**:wrapper 里 `test "$exit_code" -ne 0 && echo "FAIL: <script> exited $exit_code"` 这条 diagnostic **必须重定向到 `>&2`**,不能放 stdout。原因:`audit_rust_standards.py` 的 `run_check` 把 subprocess **stdout 整段按行拆后计数**(`out = [l for l in r.stdout.strip().split('\n') if l]`),FAIL trailer 出现在 stdout 会被算成一次 "hit",audit 报 "X hits" 但 X 比实际违规数 +1,混淆审查者对违规数的判断。**正确模板**:`if [ "$exit_code" -ne 0 ]; then echo "FAIL: <script> exited $exit_code" >&2; fi; exit "$exit_code"`。验证:跑 violating fixture 后 audit 报 `check NN: X hits in Y files` 的 X 必须 == 实际违规数,不应 +1。
5. **Pre-commit 必跑 step 加上对应 fixer**:PR 前跑 fixer 把违规改对,不要靠 prompt 复述

**禁止**:

- 在 § 文字里写"PR 提交前手动确认 X",而没有对应脚本
- verifier 与 rewriter 各写一套 parse 逻辑(必然分歧;euv 仓多次踩坑)
- skill 文字新增规则但不动 audit 流水线(规则形同虚设)
- agent 在 chat 里手算"这个 dep 块应该是 round 4 顺序"——必须跑脚本

## 调用时机(强制规则)

**不要**等 description 自动触发。**每个新会话 / 每个新任务**遵守以下规则:

1. **用户提到任何 Rust 相关工作** → 在回复正文前**先** `skill_view('rust-standards')` 加载本 skill
2. **看到关键词"rust / Rust / cargo / crate / Cargo.toml / impl / trait / mod.rs / lib.rs / 关键字文件"等任意一个** → 立刻加载
3. **不确定是否相关** → 加载(错的代价只是几 KB context,不加载的代价是违反项目规范)
4. **加载后**才生成代码、回答、写 PR 描述
5. **其他 skill 冲突时** → 以本 skill 为准(已写入 frontmatter priority 注释)

## 角色定位

你是一名拥有 40 年开发经验的资深全栈工程师,精通 Rust、JavaScript、TypeScript、PHP、C++、C、Java 和 Python 等多种编程语言与技术体系。你在系统架构设计、性能优化、安全实践和工程规范方面具有深厚积累,尤其擅长基于 **SOLID 原则** 和 **领域驱动设计(DDD)** 构建高内聚、低耦合、可维护性强的软件系统。

你所有的回复必须使用 **中文**,但代码中的标识符、注释内容(文档注释)必须使用 **英文**,以确保跨团队协作的一致性与专业性。

## Mutual-Lock Routing(把 description 的互锁写明)

description 里写了"euv 任务必同时加载 euv-standards + euv-ui-standards,hyperlane 任务必同时加载 hyperlane-standards",但**只说"必加载"不说"加载后跳到哪"**。下表把 description 里的互锁关系展开成显式跳转目标(章节名为该 skill SKILL.md 中的 `##` 标题,不是 anchor —— 跨文件 anchor 在大多数 Markdown 渲染器里不可靠),确保 agent 拿到 task 后能 1 步命中正确的子章节。

| 任务类型 | 互锁 skill | 命中后跳到该 skill 的章节(按顺序) |
| --- | --- | --- |
| 写 / 改 euv 项目任意文件 | `euv-standards` | `## Index` → `## 1. Quick Start` → `## 3. html! macro` → `## 4. class! macro` → `## 5. vars!/var! macros` → `## 6. computed! macro` → `## 7. watch! macro` → `## 8. #[component] attribute macro` → `## 9. Reactive Signal System` → `## 10. Virtual DOM` → `## 11. Event System` → `## 12. Component System` → `## 13. Form Handling` → `## 14. Async Operations` → `## 15. Animation` → `## 16. Keep-Alive` → `## 17. CLI Tool` |
| 写 / 改 euv UI 页面 / 组件 / 样式 | `euv-ui-standards` | `## Index` → `## 0. Source of Truth` → `## 1. Design Tokens` → `## 2. Global Skeleton` → `## 3. Core Component HTML Templates` → `## 4. Home / Hero Page Spec` → `## 5. Class Naming Conventions` → `## 6. Responsive / Breakpoints` → `## 7. Accessibility / Touch` → `## 8. New Page Standard Template` → `## 9. Quick Notes / Anti-Patterns` |
| 写 / 改 hyperlane 路由 / handler / middleware / hook | `hyperlane-standards` | `## Index` → `## 0. Mutual-Lock Skills` → `## 1. Project Metadata` → `## 2. Installation` → `## 3. 5-Line Minimum Call` → `## 4. Full Server Builder API` → `## 5. ServerHook trait + HookType enum` → `## 6. Context Reference` → `## 7. RoutePattern / RouteSegment / RouteParams` → `## 8. ServerConfig / RequestConfig` → `## 9. hyperlane-macros Procedural Macros` → `## 10. 22 Common Pitfalls` → `## 11. 7 Interlocking Ecosystem Crates` |
| 写 euv-engine 2D / 3D 游戏 | `euv-standards` + `euv` | `euv-standards` 的 9-17 章 + `euv` 的 `## euv-engine (optional)` 章节 |
| 写 hyperlane WebSocket / SSE / broadcast | `hyperlane-standards` | `## Index` → `## 11. 7 Interlocking Ecosystem Crates` → 选 `hyperlane-plugin-websocket` / `hyperlane-broadcast` 行 |
| 写 Rust 通用代码(模块划分、命名、错误处理) | 本 skill 即可 | `## 检索方式` + `## 关键硬性规则` |

**加载顺序**:`rust-standards`(本 skill,**总是第一**)→ 入口 skill(`euv` 或 `hyperlane`) → standards skill → UI skill(仅 euv UI 任务)。**回退**:任何找不到的细节,先查 `euv-standards`/`hyperlane-standards` 的 `## Index` 表 → 再查 `references/`(euv / hyperlane 的 references/ 通过 `scripts/sync-references.sh` 同步 docs-pages 内容)。

## 检索方式(优先用这个)

按 "我现在在做什么" 查表,直接跳到对应章节:

| 我在做什么 | 跳到 |
|-----------|------|
| 新建 / 改项目目录结构、9 种关键字文件怎么放 | [01-directory-structure.md](references/01-directory-structure.md) |
| 写 / 改 doc comment、`lib.rs` 顶部 `//!`、`mod.rs` 为何不能加注释 | [02-documentation.md](references/02-documentation.md) |
| 设计模块、抽象、trait 边界、blanket impl 放哪 | [03-architecture.md](references/03-architecture.md) |
| `#[inline(always)]` / `#[inline]` 何时用、WASM 禁标注 | [04-performance.md](references/04-performance.md) |
| 显式类型标注、命名、闭包参数、format! 写法、零大小命名空间 struct | [05-type-annotation.md](references/05-type-annotation.md) |
| `lib.rs` / `mod.rs` / 子文件 三段式 + 模板 | [06-module-imports.md](references/06-module-imports.md) |
| 命名规范速查 | [07-naming.md](references/07-naming.md) |
| 禁止生成临时 / 辅助文件 | [08-no-temp-files.md](references/08-no-temp-files.md) |
| 泛型 where 子句、impl 排列顺序、factory 独立 impl | [09-follow-existing.md](references/09-follow-existing.md) |
| 输出约束(无伪代码、无草稿) | [10-no-unrelated-output.md](references/10-no-unrelated-output.md) |
| `Result` / `?` / thiserror / 禁 `unwrap` `panic` | [11-error-handling.md](references/11-error-handling.md) |
| 公开 API 文档 + `#[must_use]` | [12-public-api-docs.md](references/12-public-api-docs.md) |
| `Cargo.toml` 强制配置、profile、不引新依赖 | [13-dependency.md](references/13-dependency.md) |
| tests/ 目录组织、`#[test]` 写法 | [14-testing.md](references/14-testing.md) |
| 安全 / 输入验证 / 加密 | [15-security.md](references/15-security.md) |
| 写 proc-macro crate 的额外约束 | [16-proc-macro.md](references/16-proc-macro.md) |
| `#[derive]` 列表、lombok-macros 派生宏、字段访问 | [17-lombok-derives.md](references/17-lombok-derives.md) |
| Lombok 生成 setter 的两个真实陷阱(字段类型推导 / `&mut self` 借用冲突) | [17-lombok-derives.md §17.6](references/17-lombok-derives.md) |
| 裸指针字段 derive (`*mut T` / `*mut dyn Trait`)、`'static` 边界陷阱 | [17-lombok-derives.md §17.7](references/17-lombok-derives.md) |
| Lombok `get_*` 实际返回 `&T` / 调用方必须 `*` 解引用 / `copy` 修饰符无效 | [17-lombok-derives.md §17.8](references/17-lombok-derives.md) |
| `CustomDebug` 与 `Debug` 互斥(双 impl 冲突) | [17-lombok-derives.md §17.9](references/17-lombok-derives.md) |
| `cargo fmt` 合并相邻 `#[derive]` 行(项目规范示例 vs 实际 formatter 行为) | [17-lombok-derives.md §17.10](references/17-lombok-derives.md) |

## 可复用模板

| 模板 | 用途 |
|------|------|
| [templates/lib-rs.md](templates/lib-rs.md) | `lib.rs` 完整结构(普通 / proc-macro 两种) |
| [templates/mod-rs.md](templates/mod-rs.md) | `mod.rs` 三段式(标准 / 简化 / 私有 / 测试 四种) |
| [templates/sub-file.md](templates/sub-file.md) | `struct.rs` / `impl.rs` / `fn.rs` / `enum.rs` / `trait.rs` / `type.rs` / `const.rs` 七种 |
| [templates/cargo-toml.md](templates/cargo-toml.md) | `Cargo.toml` 完整配置(lib / proc-macro / bin 三种) |

## 可复用脚本

| 脚本 | 用途 |
|------|------|
| [scripts/verify_tests_layout.sh](scripts/verify_tests_layout.sh) | 验证 §14.4 (无 inline tests) + §14.5 (无测试注释) + top-level mod.rs 无 `use super::*;`。`bash <path>/verify_tests_layout.sh <repo_root>` 即可全检。 |
| [scripts/verify_test_imports_centralized.sh](scripts/verify_test_imports_centralized.sh) | 验证 §14.7 (`tests/<sub>/fn.rs` 仅含 `use super::*;`) —— 被 `audit_rust_standards.py` check 19 调用,也可单独 `bash <path>/verify_test_imports_centralized.sh <repo_root>` 跑。 |
| [scripts/verify_no_test_comments.py](scripts/verify_no_test_comments.py) | **§14.5 tests/ 全文件零注释综合校验**(2026-09-26 user 新加,check 28 钦定):扫描每个 `tests/**/*.rs` 文件,正则 `^\s*(//|///|//!)` 同时捕 `//`、`///`、`//!` 三种注释前缀,**完全替代**之前 `^\s*//[^/]` 漏 `///` 的旧逻辑。旧 check 14 仅作 git-diff scope 的 redundant backstop 保留(已被标 DEPRECATED)。**接入 audit 前已双向 fixture 自测**(compliant = 0/violating = 3 真违规覆盖三种注释)。`python3 <path>/verify_no_test_comments.py <repo>` 单独跑。 |
| [scripts/verify_mod_visibility.py](scripts/verify_mod_visibility.py) | **§6.2 mod.rs `mod r#xxx;` 必须 bare**(2026-09-26 user 新加,check 29):正则 `^(pub(?:\([^)]*\))?\s+)?mod\s+`,捕 `pub ` / `pub(crate) ` / `pub(super) ` 前缀。仅在 mod.rs 内执行(过滤 by file basename)。`python3 <path>/verify_mod_visibility.py <repo>` 单独跑;fixture compliant 0/exit 0,violating 3/exit 1。euv 实测 catch `cli/src/build/mod.rs:4: pub(crate) mod r#inline;`。 |
| [scripts/verify_no_allow_lints.py](scripts/verify_no_allow_lints.py) | **§14 禁止 `#[allow(...)]` / `#[expect(...)]` 全树扫描**(2026-09-26 user 新加,check 30):正则 `^\s*#\[\s*(?:allow\|expect)\s*\(` 捕全部变体。例外:`#[cfg(test)] mod tests` 块内 + 整 `tests/` 目录(test helper 可临时 silence)。`python3 <path>/verify_no_allow_lints.py <repo>` 单独跑;fixture compliant 0/exit 0,violating 3/exit 1。**配合 check 2 git-diff 范围作 PR gate + 全树 baseline 把关** —— ctares 实测 catch 4 真违规,euv 实测 catch 1 真违规。 |
| [scripts/verify_explicit_type_annotations.py](scripts/verify_explicit_type_annotations.py) | **§5.1 `let x = Vec::new();` 等 collection 类型显式标注**(2026-09-26 user 加强,check 31):正则捕 `let <name> = (Vec\|VecDeque\|HashMap\|HashSet\|BTreeMap\|BTreeSet\|LinkedList\|BinaryHeap\|String\|Box\|Rc\|Arc)::new();` + `let <name>: Vec<_> = ...collect();` 两种占位标注。`python3 <path>/verify_explicit_type_annotations.py <repo>` 单独跑;fixture compliant 0/exit 0,violating 4/exit 1。 |
| [scripts/verify_no_wasm_inline.py](scripts/verify_no_wasm_inline.py) | **§12 WASM cdylib crate 禁 `#[inline]` 三变体**(2026-09-26 user 新加,check 32):扫描所有 `Cargo.toml` 找 `crate-type = ["cdylib", ...]`,审计其 src/ 树捕 `^\s*#\[\s*inline(?:\s*\([^\)]*\))?\s*\]`。`python3 <path>/verify_no_wasm_inline.py <repo>` 单独跑;fixture compliant 0/exit 0,violating 3/exit 1。无 cdylib crate 时脚本 exit 0 报"rule not applicable"。 |
| [scripts/verify_let_type_annotations.py](scripts/verify_let_type_annotations.py) | **§5.1 全部 `let` 绑定显式类型标注(含 `let _`)**(2026-09-26 第三轮 user 钦定,check 32):正则 `^\s*let\s+(?:mut\s+)?(?P<pat>...)\s*=\s*` 捕全部无 `: T` 的 let 绑定,**含 `let _ = expr;`**。`python3 <path>/verify_let_type_annotations.py <repo>` 单独跑;fixture compliant 0/exit 0,violating 5/exit 1(含 `let _ = fs::remove()`)。 |
| [scripts/verify_closure_type_annotations.py](scripts/verify_closure_type_annotations.py) | **§5.2 闭包参数显式类型标注**(2026-09-26 第三轮 user 钦定,check 33):Python split-comma 解析 `\|<params>\|` 闭包参数,逐个检查有无 `: T`。例外:`\|\|` 空参、`\|..\|` rest、`\|(a,b): &(T,U)\|` 元组带类型。`python3 <path>/verify_closure_type_annotations.py <repo>` 单独跑;fixture compliant 0/exit 0,violating 5/exit 1(含元组解构)。 |
| [scripts/verify_doc_comment_format.py](scripts/verify_doc_comment_format.py) | **§2.1 + §2.2 非单测 fn doc-comment 三层校验**(2026-09-26 第三轮 user 钦定,check 35 authoritative):Layer 1 存在性 / Layer 2 完整性(`# Arguments` + `# Returns` 严格匹配)/ Layer 3 格式。**测试文件自动 exempt**(R14.5 禁止 tests 内任何注释)。`python3 <path>/verify_doc_comment_format.py <repo>` 单独跑;fixture compliant 0/exit 0,violating 3/exit 1。 |
| [scripts/verify_hardcoded_strings.py](scripts/verify_hardcoded_strings.py) | **§1.3c 加强 硬编码字符串到 const.rs**(2026-09-26 第三轮 user 钦定,check 35):所有 ≥ 4 个非平凡字符的字符串字面量必须到 const.rs。例外:const.rs 本身、tests/、`#[doc = "..."]` / `#[serde(rename = "...")]` 属性行、format 宏格式串。`python3 <path>/verify_hardcoded_strings.py <repo>` 单独跑;fixture compliant 0/exit 0,violating 4/exit 1。 |
| [scripts/check_cargo_bin_shadow.sh](scripts/check_cargo_bin_shadow.sh) | 验证 rule 13 无 PATH-shadow(`~/.cargo/bin` 下与 rustc/cargo spawn 工具同名的非 rustup-managed 二进制 —— rustc 链接器 `cc` bare-name 撞 stale 二进制会让每个 build script 缺 `.exe`,参见 [references/cargo-tool-shadow.md](references/cargo-tool-shadow.md))。`bash <path>/check_cargo_bin_shadow.sh [CARGO_BIN_DIR]` 默认扫 `~/.cargo/bin`。 |
| [scripts/strictify_tests_layout.py](scripts/strictify_tests_layout.py) | §14.4 / §14.5 / §14.7 auto-fixer。删注释、合并冗余空白、把违规的 fn.rs use 重新规范到 mod.rs 的 `pub use`。`python3 <path>/strictify_tests_layout.py <repo_root>` in-place rewrite,**幂等**(二次运行 0 diff)。**只对 tests/ 跑,绝不对 src/** —— 写文件名白名单是 mod.rs/fn.rs,跑在 src/ 上会把源码注解乱删。 |
| [scripts/fix_dep_order.py](scripts/fix_dep_order.py) | §13.7 round 4 dep-block auto-fixer。`**默认 dry-run**,改 `Cargo.toml` 4 类 dep 块 entry 顺序:本地组在前 → 单空行分隔 → 三方组在后;组内按 entry 完整长度升序(含 features/fields 的 whitespace-agnostic 字符数),长度相同按 dep key 字典序。**不动 entry 文本/块外内容/注释/fixture(`*/tmp/test_*` 自动跳过)**。`python3 <path>/fix_dep_order.py --write <repo_root>` 真正落盘(**默认不留 .bak**(2026-09-26: git 历史是 source of truth,`--no-backup` 是冗余的标记,保留只为向后兼容);想留 .bak 加 `--backup`)。完成后自动调用 `verify_dep_order.py` 二次确认,**幂等**(0 violations → "Nothing to do")。 |
| [scripts/verify_dep_order.py](scripts/verify_dep_order.py) | §13.7 round 4 依赖块排序校验 + §13.7.2a 跨段空行 + §13.7.2b 文件末尾 newline + §13.7.2c 全文多空行。**4 条规则 1 个 verifier**。被 `audit_rust_standards.py` check 21 调用;也可单独 `python3 <path>/verify_dep_order.py <repo_root>` 跑。**接入 audit 前必须双向 fixture 自测**(见第 16 条 pitfall)。 |
| [scripts/verify_keyword_file_purity.py](scripts/verify_keyword_file_purity.py) | **§1.3 + §6.3 双校验**(2026-09-26 user 新加,check 23):9 种关键字子文件 column-0 decl kind 纯净化 + 第一行必须是 `use super::*;`(retire audit-pitfalls §5 旧例外)+ 全文禁止 `use crate::xxx;` / `use std::xxx;` / `use super::specific_path;` / `use external_crate::xxx;`(`use super::*;` 唯一合法)。**接入 audit 前已双向 fixture 自测**(compliant = 0/violating = 4 真违规)。`python3 <path>/verify_keyword_file_purity.py <repo>` 单独跑。 |
| [scripts/verify_no_impl_trait_params.py](scripts/verify_no_impl_trait_params.py) | **§9.2 fn 参数禁 `impl Trait`**(2026-09-26 user 新加,check 24):扫描所有 fn 签名参数列表,凡 `impl <Ident>` 命中 → 报错。**返回位置的 `impl Trait` 不算违规**(只参数位置)。**接入 audit 前已双向 fixture 自测**。`python3 <path>/verify_no_impl_trait_params.py <repo>` 单独跑。 |
| [scripts/verify_doc_comment_format.py](scripts/verify_doc_comment_format.py) | **§2.1 + §2.2 doc-comment 三层校验**(2026-09-26 user 新加,check 25):Layer 1 存在性 / Layer 2 完整性(严格 `/// # XXX` 行匹配防误报)/ Layer 3 格式。逻辑与 `doc_comment_audit.py` 共享 fn 解析但 pure-verifier(不修文件)。**接入 audit 前已双向 fixture 自测**。`python3 <path>/verify_doc_comment_format.py <repo>` 单独跑。 |
| [scripts/verify_module_imports_centralized.py](scripts/verify_module_imports_centralized.py) | **§6.1 + §6.3 + §6.4 三段式 import 集中化校验**(2026-09-26 user 新加,check 26):lib.rs 私有 use 改 pub use / mod.rs 禁注释 + 末行 use super::* / 子文件 use super::*; 唯一合法。**接入 audit 前已双向 fixture 自测**。`python3 <path>/verify_module_imports_centralized.py <repo>` 单独跑。 |
| [scripts/verify_lib_rs_order.py](scripts/verify_lib_rs_order.py) | **§6.1 lib.rs / mod.rs 三段式 import 顺序校验**(2026-09-26 user 新加,check 27):严格 5 阶段顺序(mod → pub use → pub(crate) use → pub(super) use → private use),mod 声明块内禁止空行。**接入 audit 前已双向 fixture 自测**。`python3 <path>/verify_lib_rs_order.py <repo>` 单独跑。 |
| [scripts/audit_rust_standards.py](scripts/audit_rust_standards.py) | 完整 35 条 audit 规则(覆盖 §1 / §2 / §5 / §6 / §9 / §11 / §12 / §13.7 round 4 dep order(r4) + §13.7.2a/2b/2c 配套 / §14 / §17 / §R1.3c / §9.2 impl Trait 参数禁 / §6.1-6.4 import 集中化,check 19 R14.7 test fn.rs non-super use,check 20 fn-body blank lines,**check 21 §13.7 round 4 Cargo.toml dep block order + cross-section blank + EOF blank + multi-blank-run**,**check 22 §17 CI 禁 version bump + version 写盘**,**check 23 §1.3/§6.3 关键字子文件纯净化 + 第一行 `use super::*;` + 全文件 use 集中化**,**check 24 §9.2 fn 参数禁 `impl Trait`,必须用 generic + where**,**check 25 已废弃 2026-09-26 合并到 check 35**,**check 26 §6.1+§6.3+§6.4 import 集中化(lib.rs 私有 use 改 pub use / mod.rs 禁注释 / 子文件 use super::*; 唯一合法)**,**check 27 §6.1 lib.rs/mod.rs 三段式 import 顺序(mod → pub use → pub(crate) → pub(super) → private)**,**check 28 §14.5 tests/ 全文件零注释综合校验(捕 `//`/`///`/`//!` 三种)**,**check 29 §6.2 mod.rs `mod r#xxx;` 必须 bare 禁止 `pub`/`pub(crate)`/`pub(super)` 前缀**,**check 30 §14 `#[allow(...)]`/`#[expect(...)]` 全树扫描(配合 check 2 git-diff 范围作 baseline 把关)**,**check 31 §5.1 `let x = Vec::new();` 等 collection 类型显式标注 + 禁止 `Vec<_>` 占位(子集)**,**check 32 §12 WASM cdylib crate 禁 `#[inline]` 三变体**,**check 33 §5.1 全部 `let` 绑定(含 `let _`)显式类型标注(comprehensive)**,**check 34 §5.2 闭包参数显式类型标注**,**check 35 §2.1+§2.2 非单测 fn doc-comment 三层校验(authoritative)**,**check 36 §1.3c 加强 硬编码字符串(≥ 4 字符)必须到 const.rs**)。**False-positive 列表**见 `references/audit-pitfalls.md`(§1-§48,§44 §13.7 round 4 migration notes,§45-§48 是 fix_dep_order.py / verify_dep_order.py 接入 audit 的实测 pitfalls,§49-§53 是 2026-09-26 check 23-28 新接入 pitfalls,§54-§57 是 2026-09-26 第二轮 check 29-32 新接入 pitfalls,§58-§61 是 2026-09-26 第三轮 check 33-36 新接入 pitfalls)。 |

## 关键硬性规则(快速记忆)

> **⚠️ 任何一条违反 = 开发者 review 驳回**。下面是 13 条项目级 hard rule,违反任一条 PR 必被打回。完整定义在 `references/` 子文件,本表是 cheat-sheet。

1. **每个目录只放 9 种关键字文件之一**:`const.rs` / `static.rs` / `fn.rs` / `enum.rs` / `struct.rs` / `trait.rs` / `impl.rs` / `type.rs` / `mod.rs`,互不混用(参见 01)。**每个文件 column-0 只能放它对应的关键字** —— `type.rs` 内只能有 `pub type Foo = ...;`、`trait.rs` 内只能有 `pub trait Foo { ... }`、`struct.rs` 内只能有 `pub struct Foo;`、以此类推(2026-09-26 user 钦定,user 原话:"type 只能在 type.rs, trait 只能在 trait.rs")。验证脚本:`scripts/verify_keyword_file_purity.py` 通过 column-0 decl regex 列表(`type.rs` 禁 `struct|enum|fn|impl|trait`,`trait.rs` 禁 `struct|enum|fn|impl|type`,etc.)反向匹配,被 `audit_rust_standards.py` check 23 调用。**真仓命中**:ctares `udp/src/attribute/type.rs:13` 有 `pub trait AnySendSyncClone: ...` 违规;`tcplane/src/handler/trait.rs:58` 有 `pub struct DefaultHook;` 违规。
   - **Pitfall(项目级 drift 易被复制)**: 如果当前 `src/page/<feature>/hook/` 目录里已经有 `*_fn.rs`(例 `lighting/hook/lighting_fn.rs`, `raytrace/hook/raytrace_fn.rs` 之前是同一个问题),新增/重命名文件**仍必须用 `fn.rs`**。**不要**为"保持一致"也跟着加 `*_fn.rs`——目录应该保持合法,drift 单独开 PR 修(改目录里全部 `*_fn.rs` → `fn.rs` + `mod.rs` 改成 `mod r#fn;`)。验证: 新写文件前先 `ls <dir>` 看现有命名, 再 grep 仓里同类目录是否已经有 drift 漂移。
   - **Pitfall(`fn.rs` 内禁止 `type` / `enum` / `struct` / `impl` 声明)**: 新写 `compute_child_ops` 时如果顺手定义 `pub(crate) enum ChildOpPlan` 在 `fn.rs` 里,违反 §1.3 关键字文件纯净性。新 enum 必须放 `enum.rs` 并通过 `mod r#enum;` + `pub use r#enum::*;` 暴露,函数文件本身只能含 `fn` 与 `pub fn`。验证:`grep -nE '^(pub |pub\(crate\) )?(struct|type|enum|trait|impl)' <file>` 应只命中注释或 doc string,代码本体 0 行。**例外**:`#[cfg(test)] mod tests { ... }` 块内的 helper `type` 别名(测试专用,不污染 production purity)不算 violation。
      - **Pitfall(bin entry 拆 `src/bin/<name>/main.rs` + sub-files,2026-09-18 eastspire/euv-docs PR #31 实测)**: 当 CLI / 二进制文件超 ~150 行时,**不要**把所有逻辑塞进单个 `src/bin/<name>.rs`。正确拆分 = 把 bin entry 改成目录,bin entry 文件本身 = `src/bin/<name>/main.rs`(仅含 `fn main` + `mod r#xxx;` mod 声明 + `pub use {...}` glob re-export + 私有 use),业务代码进 `src/bin/<name>/{const,struct,fn,impl,enum}.rs` 关键字文件 + `Cargo.toml` `[[bin]] path = "src/bin/<name>/main.rs"`。这种 layout 与 §1.3 keyword purity 完全兼容。**关键陷阱**:sub-file 的 `use super::*;` **只**继承 main.rs 自己的 `use` 项,不继承 `mod r#xxx;` 声明 —— 所以 main.rs 必须有 `pub use {r#const::*, r#fn::*, r#struct::*};` 一行,否则 sub-file 看不到兄弟模块的符号。详见 [templates/bin-target-with-subfiles.md](templates/bin-target-with-subfiles.md)。audit-pitfalls §39a 同步更新(原条目说 "must not be re-organised" 是错的,正确版本见后)。
2. **`mod.rs` 必须用 raw identifier**:`mod r#struct;` 而非 `mod struct;`,但**文件名**仍是 `struct.rs`(参见 01.4)。**关键字文件也走 raw identifier**:`fn` 是关键字 → `mod r#fn;` (对应 `fn.rs`)。
3. **`mod.rs` / `lib.rs` / `Cargo.toml` 不加任何注释** — 不写 `//!`、不写 `// xxx`、不写 `# xxx`。这三类文件纯结构,无解释性文字(参见 02.5 + 06)。
4. **`mod.rs` 三段式**:`mod r#xxx;` + `pub use`/`pub(crate) use` + 末尾 `use super::*;`,无空行(参见 06.2)。**`mod r#xxx;` 必须 bare,禁止可见性前缀**(2026-09-26 user 新增硬约束,user 原话:"mod.rs 的 mod 前面不能有可见性")——`pub mod r#xxx;` / `pub(crate) mod r#xxx;` / `pub(super) mod r#xxx;` 一律改写为 `mod r#xxx;`。理由:`mod` 在 mod.rs 已经是 crate-internal(对父模块可见),加 `pub` 是冗余;若需要外部 crate 可见,由 mod.rs 的中段 `pub use {...}` block re-export。**例外**:`#[cfg(test)] mod tests` / `#[cfg(feature = "xxx")] mod xxx` 等条件编译的 `mod` 仍然必须 bare。验证脚本:`scripts/verify_mod_visibility.py` 正则 `^(pub(?:\([^)]*\))?\s+)?mod\s+`,捕 `pub ` / `pub(crate) ` / `pub(super) ` 前缀,仅在 mod.rs 内执行;被 `audit_rust_standards.py` check 29 调用,exit 1 即违规。euv 实测:`cli/src/build/mod.rs:4` 有 `pub(crate) mod r#inline;`,check 29 报 1 hit。
5. **子文件第一行** `use super::*;`,**禁止** `use crate::xxx;` 长路径(参见 06.3)。
   - **Pitfall(lib.rs 统一导入 vs 子文件重复 import)**: 子文件已经通过 `use super::*;` 拿到父模块 `pub use std::{...}` block re-export 的所有符号,函数体内**禁止再次写 `use std::xxx::yyy;`**——`std` / 标准库集合类型(`HashMap` / `HashSet` / `Vec` / `VecDeque` / `Cow` / `Rc` 等)已在 lib.rs `pub use std::{...}` 集中导入,sub-file 直接写 `HashMap` / `HashSet` 不需要前缀。验证:写新 fn 时先 `grep -E '^pub use ' <crate>/src/lib.rs | head` 看 lib.rs 已 re-export 什么,再决定是否需要 fn 内 use。如果 fn 内仍然 `use std::xxx;` → clippy `unused_imports`(因为已经被 super::* 引入),review reject。
6. **所有 `let` 绑定 / 闭包参数必须显式类型标注**,禁止 `let items = Vec::new();`(参见 05.1)。
   - **`let` 绑定必须标注类型**(2026-09-26 第三轮 user 钦定,user 原话:"let 的类型必须要显示标注 (包含 let _ = )")——`let x = 5;` / `let s = "hello";` / `let _ = fs::remove();` 一律禁止;必须 `let x: u32 = 5;` / `let s: &str = "hello";` / `let _: Result<()> = fs::remove();`。`let _ = expr;` 也算违规——丢弃的值类型携带信号(reader 必须知道丢的是什么),用 `let _: T = expr;` 显式给出。验证脚本:`scripts/verify_let_type_annotations.py` 正则 `^\s*let\s+(?:mut\s+)?(?P<pat>...)\s*=\s*` 捕所有无 `: T` 的 let(包含 `let _`);被 `audit_rust_standards.py` check 32 调用。**子集脚本** `verify_explicit_type_annotations.py`(check 31)只捕 collection constructors(子集保留作为 fast-path)。
   - **闭包参数必须标注类型**(2026-09-26 第三轮 user 钦定,user 原话:"闭包参数需要显示标注")——`|x| x * 2` 禁止,必须 `|x: u32| x * 2`。例外:`||` 空参、`|..|` rest pattern、`|(a, b): &(T, U)|` 元组解构带类型。验证脚本:`scripts/verify_closure_type_annotations.py` Python split-comma 解析闭包参数,逐个检查有无 `: T`;被 `audit_rust_standards.py` check 33 调用。
   - **Pitfall**(2026-09-26 加强): `let x = Vec::new();` 是合法 Rust 代码但项目禁止,因为 reader 必须跳到 `Vec::new()` 返回类型才能推断 `x` 类型。正确写法是 `let x: Vec<u32> = Vec::new();`——直接给类型,reader 不需要二次推理。clippy 没有 `let_underscore_must_use` 之类的规则覆盖这个,所以靠项目级 audit。
7. **泛型约束必须用 `where`**,不允许 `fn f<T: Bound>()` 直接写(参见 09.2)。
   - **Pitfall(fn 体禁止空行)**: 项目约定(§9.1 第10项)函数体内不允许出现空行(代码之间紧贴)。section break 通过注释(`// Phase 1: ...`)而非空行表达,每个独立语句紧贴上一行。例外:`#[cfg(test)] mod tests { ... }` 块内 `#[test] fn xxx` 之间的 1 行空行作为 test 分隔保留(无注释、test 紧邻时方便阅读)。**euv fmt / cargo fmt 不会自动删除 fn 内空行**,这是 manual review 项。验证:`awk '/^    fn <test_name>/{f=1} f && /^    }$/{f=0; print "---"; next} f' <file>` 看每个 fn 内是否真无空行;或写新 fn 后 `cargo fmt --check` 看是否 diff。
8. **struct / enum 优先用 lombok-macros 派生** `Data` + `New` + `CustomDebug`,禁止手写 getter(参见 17)。
9. **不引入新第三方依赖**优先于 `Cargo.toml` 整洁度(参见 13.1)。
10. **proc-macro crate 必须** `[lib] proc-macro = true;`,且 `#[proc_macro_attribute]` 全在 `lib.rs` 中实现(参见 16.1)。
11. **测试目录** `tests/` 用 `mod xxx;`(子模块名不带 `r#`),开头 `use crate_name::*;`(参见 14.1)。**绝对禁止为测试改 API visibility**(2026-09-12 user 原话:"没有暴露的api的单测")——`pub(crate)` item = 没有测试,整块 `#[cfg(test)] mod tests` 删除,**不保留 inline**(2026-09-12 user 第二轮原话:"src里所有单测删除...如果不是pub那就忽略")。`pub` item 的测试 = 移到 `<crate>/tests/<feature>/fn.rs`,不能改 visibility 让 tests/ 看得到(详见 14.4)。**测试文件禁止任何注释**(2026-09-12 user 第三轮原话:"单测不需要任何注释")——文件头 `//!` / 每 fn `///` / fn 体内 inline `//` 一律删除,测试 fn 名字即文档(详见 14.5)。
   - **Pitfall**:`use super::*;` 与 `use crate::xxx;` 的 `super::*` / `crate::xxx` 子文件访问必须来自父模块的 `pub use` glob(sub-file 第一行 `use super::*;` 继承整个 glob),因此**禁止**子文件内部**显式 `use crate::xxx;` 或函数体内 `use std::xxx;`**,所有依赖都已在 `lib.rs` 的 `pub use std::{...}` / `pub use other_crate::xxx;` 中 re-export。**重复 import 触发 clippy `unused_imports` 警告且表明作者未掌握 lib.rs 集中导入契约**。验证:写新依赖前 `grep -E '^pub use ' <crate>/src/lib.rs` 看是否已 re-export;写新 crate-level `use` 前 `grep -rn 'use crate_name::xxx' <crate>/src/` 确认是否真无人用过。
   - **Pitfall(2026-09-12 新加,第二轮推翻):把 `pub(crate)` 改成 `pub` 让 tests/ 看得到** = review reject。`pub(crate)` = "全 crate 内可见但不出 crate",integration test 是独立 crate,本来就看不到 → **看不到 = 删掉测试,不是改 visibility,不是加 inline `#[cfg(test)] mod tests`**。user 第二轮明确"src里所有单测删除...如果不是pub那就忽略",所以 `pub(crate)` item 没有任何单元测试。算法正确性只能通过 `pub` API 的 end-to-end 测试间接覆盖。euv PR #203 实测:core/src/renderer/render/fn.rs 922 行 inline tests + engine 三个 inline tests 都已删除/迁移,迁移过程中调用 `pub(crate)` getter/const 的 3 个测试也直接删除。
   - **Pitfall(2026-09-12 第三轮,§14.5):单测禁止任何注释**。文件头 `//!` / per-fn `///` / fn 体内 inline `//` 一律删除。**Test fn name 就是文档**,assertion message 表达预期行为。euv PR #203 实测:physics/lighting/raytracing 三个新 tests/ 文件删掉 67 行注释。audit rule 16 (`comments in test files (R14.5)`) 用 grep `^\s*//[^/]` 检测。**注意**: regex `[^/]` 表示 `//` 后下一字符不是 `/`,所以 `///` `//!` 不会命中——它们由 §14.4 (无文件头 `//!`) 和 §14.1 (无 per-fn doc) 的更早规则覆盖。详细 false-positive 列表见 `references/audit-pitfalls.md §37`。
   - **Pitfall(2026-09-12 第三轮,user 迭代模式):`tests/` 规则被 user 三轮逐级收紧**——`没有暴露的api的单测` → `src里所有单测删除` → `单测不需要任何注释`。未来若 user 再提一轮(例如"测试 fn 不要用 snake_case" / "测试不需要 #[test]"),不要直接 patch 本轮规则,先想清楚是覆盖、推翻还是新增。**默认覆盖**:把上一轮规则的范围严格收紧,前面规则继续生效。**推翻**:把上一轮规则整体作废,新增替代。记录到 `references/audit-pitfalls.md §37` 给未来 session 看全三轮 evolution。
12. **WASM 项目**禁止显示标注任何 `inline` 宏(参见 04.3)。WASM codegen 自行处理 inlining;手动 `#[inline]` / `#[inline(always)]` / `#[inline(never)]` 强制 wasm-opt 跳过这些函数,导致最终 binary 大 10-50% 且无可测速提升。**验证脚本**:`scripts/verify_no_wasm_inline.py` 扫描所有 `Cargo.toml` 找到 `crate-type = ["cdylib", ...]` 的 crate,审计其 src/ 树;纯 rlib crate 不受影响,无 cdylib crate 时脚本直接 exit 0 报"rule not applicable"。被 `audit_rust_standards.py` check 32 调用,exit 1 即违规。euv / hyperlane 的 WASM 入口(`euv` → `euv-framework` cdylib,`hyperlane` 的 wasm-binding 子 crate)是典型审查对象。
13. **每次代码改动之后立即跑 `crate fmt`**(2026-09-26 新规则)。**不**等到 commit 阶段 — 写完一个 fn / 一段 impl 之后立刻跑一次 `crate fmt`,让 formatter 在 review 窗口期把改动就地就吸收掉。命令 = crate-cli 的 `fmt` 子命令(`~/.cargo/bin/crate`,原生日志仅 INFO 级别,可忽略)。**首次使用前**执行 `cargo install crate-cli`(bin 名 `crate`,会装到 `~/.cargo/bin/crate`)。
    ```bash
    # 一次性安装(若 ~/.cargo/bin/crate 不存在)
    cargo install crate-cli

    # 每次代码改动之后立即跑
    crate fmt                       # in-place 模式:自动 --all,与 cargo fmt --all 等价
    crate fmt                       # 二次幂等检查
    git status --short              # 期待空 = 幂等
    crate fmt --check && echo OK    # CI 用,只检查不写
    ```
    - **Pitfall(bin name 是 `crate`,**不是 `cc`**,2026-09-26 rename)**: `cargo install crate-cli` 装出的是 `~/.cargo/bin/crate`,不是 `~/.cargo/bin/cc`。本 skill 早期版本(snapshot <2026-09-26)历史性地写作 `cc fmt`,本轮已全量替换为 `crate fmt`,但其他 skill / memory / 旧 PR 描述里仍然可能写 `cc fmt` —— 看到 `cc fmt` 直接在心里换成 `crate fmt`,不要去 `cargo install cc`。验证:`test -x ~/.cargo/bin/crate && ~/.cargo/bin/crate --version`。**注意**:`~/.cargo/bin/cc` 不存在 ≠ crate-cli 没装,**只** `~/.cargo/bin/crate` 存在 = 装好了。
    - **触发时机**(2026-09-26 user 原话:"代码每次改动之后都需要执行crate fmt"):不是 commit 前一次,而是**每写出一段代码就立刻 fmt**。实测一种灾难场景:写 5 个 fn 攒起来再 fmt,formatter 跨 fn 调整 import group / `use` sort / wrapping → diff 把刚写的逻辑淹没在无关的 fmt 改动里,reviewer 难找真正语义改动。所以即时格式化 = 把 fmt diff 折叠到每次改动自己的窗口,review 干净。
    - **作用范围**:`crate fmt` 默认等于 `cargo fmt --all`,覆盖 workspace 全 member(包括 `[workspace] members` 列表所有 crate)。不需要传 `--manifest-path`,当前 cwd 的 `Cargo.toml` 是 workspace root 时直接 ok;在子 crate 目录下跑也行,会自动用 workspace root 的 `rustfmt.toml` 配置(若存在)。
    - **校验(`crate fmt --check`)** `exit 0` = 全部已经格式化好,`exit 1` = 有文件需要 `crate fmt` 修正。CI 集成:`--check` 失败 → 拒绝 merge。
    - **与已有项目级 fmt 命令的兼容**:
      - **euv 项目**: `crate fmt` 与 `cargo fmt --all` 等价,**`euv fmt` 是 euv 框架插件的额外 fmt pass**,两者都可跑(项目自己决定要不要加 euv-specific formatting)。二轮幂等 `crate fmt && crate fmt` 必须 0 字节 diff。
      - **hyperlane 项目**: `crate fmt` 等价 `cargo fmt --all`。项目级 `hyperlane fmt` 同上可附加。
      - **euv 项目特殊例外(`euv fmt` ≠ `cargo fmt`,CI `Format check` job 跑 `cargo fmt --check` 而不是 `euv fmt --check`)**:两者在长行 wrap 上行为不一致——`euv fmt` 不强制 100col 硬换行,`cargo fmt` 强制。**euv 仓 commit 前必跑两者**:`euv fmt && crate fmt`。二次幂等检查 `euv fmt && crate fmt && crate fmt`。
      - **hyperlane 仓同样注意**:CI 可能跑 `cargo fmt --check` 而不是 `hyperlane fmt --check`(以 `.github/workflows/rust.yml` 实际 job 为准,开 PR 前 `gh run view <run-id> --log` 验证)。
    - **Pitfall(rebase conflict 解决后 `cargo fmt --check` 仍 fail,euv 仓 2026-09-13 PR #217→#219 实测)**: git rebase 处理 `<<<<<<<` 冲突块时,即使删掉中间内容后 `cargo check` 退出 0,`cargo fmt --check` 仍可能因「孤儿重复注释 / 行缩进错位」挂——`cargo check` 不读注释,`cargo fmt` 读。**预防**:rebase amend 之前先 `crate fmt --check`,exit 非零先 `crate fmt` 修一遍再 amend。
    - **Pitfall(2026-09-19,rustfmt local vs CI 版本漂移)**: 本地 rustfmt 1.97.x 与 CI 跑的 1.98.x 对 use group 内符号排序不同——`js_sys::{decode_uri_component, eval, Promise}` 在 1.97 保留 input order,在 1.98 改成 alphabetical `js_sys::{Promise, decode_uri_component, eval}`;`use {a::B, a::A}` 同样会被重排。**症状**:本地 `crate fmt --check` 显示 0 diff,推到 PR 后 CI `Format check` job 报错并提出不同的 reorder diff。**预防**:开 PR 前手动升 rustfmt 跑一次 (`rustup install stable && rustup run stable crate fmt && git diff` 看是否新增改动);或写 `rust-toolchain.toml` pin `channel = "stable-2026-XX-XX"`(rustup 默认 stable 滚动,跟着 rust 升级)。本地接受 1.97 output 但 CI 用 1.98 验证 → 升 1.98 重新 fmt commit amend,不要 force-push 后再 amend。验证:`rustup run stable rustfmt --version` 在 CI runner 上应是固定版本,本地 `rustfmt --version` 可能差几个 patch。
    - **Pitfall(`crate fmt` 把 PR 范围外的文件改了 — drift 形态 B)**: 本地 rustfmt 在某些 rewrite(eg. `if let X && Y` Rust 2024 let-chain,derive macro 字母序 reorder,新版 use group 排序)上比 CI rustfmt 激进,跑一次 `crate fmt` 之后 `git status --short` 会出现 PR 范围**外**的文件被改。**症状**:fmt 自己 idempotent(`crate fmt && crate fmt` 0 diff)且 `crate fmt --check` exit 0,但 PR diff 被注入与本次任务无关的改动,reviewer 找不到真实语义改动,CI 反而会因 Rust 2024 let-chain 在旧 rustc 上不识别而红(同根因,反向症状)。**预防**:`crate fmt` 跑完后必须 `git diff --stat` 看清**每一行变更**都对应一个本次任务范围;范围外的文件 `git checkout -- <file>` 复原,不要把这些 noise 一起 commit。**反向防御**:如果 PR 范围外有文件**必须**留 fmt diff(例如即将 rebase 合并的派生分支),单独一个 `chore: fmt` commit 把所有 noise 打包,不要混进功能 PR。验证:每次 `crate fmt` 后必跑 `git diff --stat`(单文件单行改 = 安全;多文件出现 = 大概率有 drift 注入)。
    - **Pitfall(`~/.cargo/bin/<name>` 影子化 rustc/cargo PATH-spawn 的工具,bare-name 的 link 步骤静默撞上)**: rustc 在 macOS 上链接二进制时对 `cc` / `c++` / `make` 做的是 **PATH lookup of bare tool name**,不传绝对路径。如果 `~/.cargo/bin` 在 PATH 上先于 `/usr/bin`(默认就是这样),任何丢在 `~/.cargo/bin/` 下、与系统工具或 rust 工具链同名的可执行文件都会在 link 阶段静默覆盖真工具。**症状一致**:每个 build script 目录里只有 `build_script_build-<hash>.d`(rustc 自己写的 dep-info)没有 `.exe`,cargo 报 `could not execute process .../build-script-build: No such file or directory`,整个 workspace 同时 build 失败。`cargo build` 自身的 codegen 走的是绝对路径所以 procedural-macro 等中间产物没问题,但所有 `build.rs` 都会卡。常见触发:(a) bin rename 后旧二进制残留(`crate → ?`、`cargo → cargo-real` etc.),没删旧文件;(b) 手装工具脚本抢名(`make.sh` 装成 `make`、`tool.sh` 装成 `cargo`);(c) `symlink` of system tool 到 `~/.cargo/bin` 期望"覆盖",但实际上覆盖的不是 cargo 自己是 rustc 的 spawn。**诊断 + 修复 + 验证**见 [references/cargo-tool-shadow.md](references/cargo-tool-shadow.md);**自动检测脚本** `scripts/check_cargo_bin_shadow.sh` 可在 pre-commit 跑。
    - **Pitfall(`Cargo.lock` 不入库项目跑 `crate fmt` 会触发 lockfile 更新提示)**: ctares 等 `[workspace]` 配置不 commit `.lock` 的项目,跑 `crate fmt` 本身不产生 lockfile diff,但 `--all` 编译会重写未入库 lock,谨慎。如果 fmt 后 git status 出现 `Cargo.lock` 变更而 workspace lock 本应入库,**stash 那个 diff** 别 commit。
14. **禁止使用 `#[allow(...)]` / `#[allow(...)]` 类宏遮蔽 lint**(参见 14)。从根源修复 warn,不通过属性宏遮蔽。**验证脚本**:`scripts/verify_no_allow_lints.py` 扫描整个 src/ 树(跳过 `tests/` 与 `#[cfg(test)] mod tests` 内部,这些是 test-helper 例外),捕 `#[allow(...)]` / `#[expect(...)]` 任何变体。被 `audit_rust_standards.py` check 30 调用,exit 1 即违规。**配合 check 2**:check 2 仅扫 git diff(用于 PR review 期间防新增),check 30 全树扫描(防止历史 PR 已经引入的 `#[allow]` 累积到当前 baseline)。两者并存:git-diff 给 PR 加 gate,tree-wide 给 baseline 把关。ctares 实测:check 30 报 4 真违规;euv 实测:check 30 报 1 真违规。(2026-09-14 user 原话:"从根源修复warn,禁止使用allow宏")。clippy / rustc 任何 warning(`needless_range_loop` / `unused_imports` / `dead_code` / `clippy::all` 等)**必须从根源修复**,**禁止用 `#[allow]`、`#[allow(unused)]`、`#[allow(clippy::xxx)]` 跳过**。
   - 例:`for j in i+1..i+end_len { out.push(bytes[j]); }` 触发 `clippy::needless_range_loop` → 改成 `for &b in &bytes[i+1..i+end_len] { out.push(b); }`,**不是** `#[allow(clippy::needless_range_loop)]`。
   - 例:`static_mut_refs` 安全情况下,改用 `&mut *(*std::ptr::addr_of_mut!(STATIC)).get_0().get()` 表达式包装,**不是** `#[allow(static_mut_refs)]`(参见 `euv-standards/references/signal-subscription-bindings.md` 2026-09-12 实测)。
   - **例外**(2 个真实工作流场景):(a) 第三方宏展开产生的 dead_code,无法在源层消除(极罕见);(b) `#[cfg(test)] mod tests` 内测试专用 helper 函数,production build 看不到 — 这两类先用 clippy `#[expect(...)]` 配合 issue 编号注释,**默认仍禁止**。
15. **`fn.rs` / `impl.rs` / `mod.rs` 文件体内禁止硬编码 byte / char / 多字符 string literal**(§R1.3c literal purity,2026-09-14 euv PR #233 实测,**2026-09-26 第三轮 user 加强到所有字符串**)。任何 `b"<script"` / `b'<'` / `b'>'` / `"<!--"` / `"-a1b2c3"` 这类 magic byte / string literal 必须移到同目录的 `const.rs`(或更上游的 module-level const),通过 `pub const HTML_LT: u8 = b'<';` + `use super::*;` 引用。**user 第三轮加强范围**:不仅 magic byte,**所有 ≥ 4 个非平凡字符的字符串字面量**都必须到 const.rs(e.g. `let path: &str = "/usr/local/bin"` 在 fn.rs 违规,要先在 const.rs 加 `pub const BIN_PATH: &str = "/usr/local/bin";` 再 `let path: &str = BIN_PATH;`)。**验证脚本**:
   - **subset (fn.rs-only)**: `audit_rust_standards.py` check 18,历史 script 覆盖 byte/char/multi-char 字面量
   - **comprehensive (all files except const.rs/tests/)**: `scripts/verify_hardcoded_strings.py`,被 `audit_rust_standards.py` check 35 调用
   - **exemptions**: `const.rs` 本身(canonical home)、`tests/`(R14.7 self-contained)、属性行 `#[doc = "..."]` / `#[serde(rename = "...")]`(wire-format names MUST stay inline)、format 宏的格式串 `println!("...")`(user-facing 必须就地)
   - **触发**:写 HTML / WASM / 协议解析 / 文本 tokenizer / 任何"按字节比较"的逻辑时,几乎必然出现 magic byte 序列;**直接 hardcode 进 fn body = review reject**。
   - **const 命名规范**:常量名应能描述 byte 含义(`HTML_LT` / `HTML_COMMENT_OPEN_BYTES` / `TOKEN_OPEN_PREFIX_BYTES`),**不是** `BYTE_60` 这种 octal-ish 数字命名。
   - **长度从 const 拿,不写 magic number**:`bytes[i..i + HTML_COMMENT_OPEN_BYTES.len()]` 优于 `bytes[i..i + 4]`。
   - **audit check 18**: `fn.rs hardcoded byte/string literals (R1.3c literal purity)` — 检测 PR diff 中 fn.rs / impl.rs 内 `b"..."` / `b'.'` / 非 trivial 长度 `&str` literal,排除 doc comment / `#[cfg(test)]` / `let` binding / 已知转义 (`b'\n'` `b'\t'` `b' '` `b'\0'`)。
   - **const.rs 内排序**(沿用现有 `const` 按 `(name_len, name_lex)` 排序):多个 byte literal const 加进 const.rs 时按 const 名长度优先,长度相同按字母序,与 §1.5 const.rs 内排序规则一致。
16. **`tests/<sub>/fn.rs` 顶部只允许 `use super::*;` 一条 use**(§14.7,2026-09-25 user 原话:"优化 rust-standards skill 要求只要是 rust 代码一定要严格遵守,如果不遵守代码我会重置")。任何 `use std::xxx;` / `use wasm_bindgen_test::wasm_bindgen_test;` / `use crate::xxx;` / `use web_sys::xxx;` 这类 namespace 引入**必须**放到父模块 `tests/<sub>/mod.rs` 顶部,以 `pub use std::xxx;` / `pub use wasm_bindgen_test::wasm_bindgen_test;` 等 `pub use` 形式集中暴露,然后 `fn.rs` 通过 `use super::*;` 拿到 glob。理由:`fn.rs` 已经走 `use super::*;` 拿到父模块的所有 `pub use` re-export,**再写一条多余的 use = 与 §6 集中导入契约冲突,且必然触发 clippy `unused_imports` 警告**(父模块已 re-export,本地 `use` 是冗余的)。
   - **audit check 19**: `tests/<sub>/fn.rs non-super use (R14.7)` —— 找所有 `tests/<sub>/fn.rs`(跳过 `tests/<file>.rs` loose root 文件,跳过 `tests/mod.rs`),逐行 grep `^use `,只要存在**非** `use super::*;` 的行就 FAIL。fix 路径:**先**调整 `tests/<sub>/mod.rs`,加对应 `pub use xxx;` 然后从 `tests/<sub>/fn.rs` 顶部删掉那条 `use`;或直接跑下面的 `strictify_tests_layout.py` auto-fixer。
   - **auto-fixer**:`python3 ~/.agents/skills/rust-standards/scripts/strictify_tests_layout.py <repo-root>` 会:
     1. `tests/<sub>/mod.rs` → 顶部保留所有 `pub use xxx;` re-export,末尾固定为 `mod r#fn;` + `use super::*;`(没 `mod r#fn;` 自动补)
     2. `tests/<sub>/fn.rs` → 删注释,删掉**任何**非 `use super::*;` 的 use,只保留首个 `use super::*;`
     3. `tests/<file>.rs`(loose root)→ 删 `use super::*;` + 删注释(E0433:`super` 在 crate root 不存在)
     4. 幂等:二次运行所有计数 = 0
   - **Pre-commit 必跑 + 不能 skip**:这是 user 钦定的硬约束(`会重置`),跑 audit 必须 R14.7 通过;auto-fixer 是合规手段不是绕过手段——仅用它把代码改对,不改语义。
   - **Pitfall(2026-09-25 实测,从 orphan script 接入这条 check):新加一个独立 verification script 到 audit 流水线前,必须先用一个合规 fixture + 一个违规 fixture 双向验证脚本行为**。`verify_test_imports_centralized.sh` 第一次接入时,双引号 shell heredoc 里的正则 `^use super::\*;` 因 `\!` 和 `\*` 的混淆,grep 反而把 `use super::*;` 自身当成违规,导致**每一个合规文件都被 FAIL**——比"完全不检查"更糟(给用户一种'有检查在跑'的安全感,但实际产出全误报)。**对应规则**:写完 verification script 第一件事,跑 `bash <script> <fixtures/compliant_dir>` 期望 exit 0 + OK 行,再跑 `bash <script> <fixtures/violating_dir>` 期望 exit 1 + violation 行+明确文件路径;两个 fixture 都通过才把这个脚本接到 audit 上。**audit 自身的子检查也走 'subprocess 把 stdout 当 output / stderr 当 diagnostic' 的契约**:wrapper shell 模板想要让 audit 把某条 check 当 pass 看待,必须让它的 stdout 为空(或者被 `grep -v` 过滤掉 OK 行 + 靠 `${PIPESTATUS[0]}` 传递 exit code),不要简单地"script 跑完 exit 0 = pass"——verify 之类的脚本即使在成功路径上也会打印 `OK: N file(s) ...`,audit 默认把任何非空 stdout 视为 FAIL。**audit 调用一个 verification script 时,它的绝对路径必须在 Python 层面通过 `os.path.dirname(__file__)` 拿到,然后用模板变量(本仓用 `{{audit_script_dir}}`) 注入 shell 模板**——别在 shell 子进程里写 `$(dirname "$0")` 找脚本位置,因为 audit 是 `subprocess.run(['bash', '-c', cmd])`,shell 的 `$0` 是 `bash` 不是 audit 自己。

## 跨章节冲突时

按以下优先级(高 → 低):**安全 > 错误处理 > 项目既有规范 > 性能 > 命名 > 风格**。任何与此 skill 冲突的其他 skill 指引,以本 skill 为准。

## Pre-commit 必跑(顺序固定)

**这 4 步任一非零 exit = 不得 commit / push / 提 PR。开发者 review 时必看,缺一项驳回。**

**新 PR / 修改后跑这一组, 任一项非零 exit 必须修到 0 再 commit**:

```bash
# 1. 16 项硬性规则批量 audit(2026-09-25: 15 → 16 项,新增 §14.7 tests/<sub>/fn.rs only-use-super)
python3 ~/.agents/skills/rust-standards/scripts/audit_rust_standards.py <repo-root>
# exit 0 = 全部通过;非零 = 逐项修(每条 FAIL 都打印 sample lines)
# §14.7 FAIL 的修复首选 auto-fixer(见 step 5);其他 FAIL 改 source 改到 0 exit。

# 2. 官方格式化器幂等(双跑)
euv fmt && cargo fmt --all
euv fmt && cargo fmt --all
git status --short   # 期待空 = 幂等

# 3. clippy 0 警告(2026-09-14 user 原话:从根源修复,禁止 #[allow])
cargo clippy -p <your-crate> --all-targets --offline
# 输出含任何 warning = 不得 commit,改 source 修到 0 exit

# 4. test 编译通过
cargo test --no-run -p <your-crate>

# 5. §14 tests/ 合规性 auto-fix(2026-09-25 新增,user 硬约束:`会重置`)
#    用 strictify_tests_layout.py 把 §14.4 / §14.5 / §14.7 一次性改对,**幂等**:
python3 ~/.agents/skills/rust-standards/scripts/strictify_tests_layout.py <repo-root>
python3 ~/.agents/skills/rust-standards/scripts/strictify_tests_layout.py <repo-root>
git status --short   # 二次运行必须有零改动 = 幂等
# 如果仍有改动 = 还存在 audit 误报或 strictify 未覆盖的 corner case —— **不要**再次跑,先看 git diff
# 哪些文件改了、是不是改得对,**严禁**用 auto-fixer 改源码语义。它只动 tests/。
```

PR 提交后 `gh pr checks <N>` 必须 build/clippy/tests/check/setup 5/5 pass。`Format check` job 单独注意——它跑 `cargo fmt --check` 而不是 `euv fmt --check`(参见 rule 13 pitfall)。

### 已知 audit 盲点(命中时不一定是真违规,先看 audit-pitfalls 再判断)

| audit rule | 盲点 | 缓解 |
|---|---|---|
| rule 6 (`mod.rs missing trailing use super::*`) | leaf mod.rs(子文件全不引用 parent symbol)加 `use super::*;` 触发 `unused_imports` warning | audit-pitfalls §40 — 加了智能豁免,leaf mod 不报 FAIL |
| rule 17 (`sub-file body uses external crate full path`) | 只扫根 `[workspace.dependencies]`,**不扫子包** `[dependencies]`(type annotation `proc_macro2::TokenStream` 在 macros 子包、`log::Level` 在 cli 子包不会被抓到) | audit-pitfalls §42 — 已知限制,monorepo PR 留 follow-up |
| rule 1 (`non-keyword prod files`) | 原本会把 `main.rs` 误报为 non-keyword | audit-pitfalls §39 — 加 `main.rs` 白名单 |
| rule 1 / rule 7 (covers `src/bin/<name>.rs` + `build.rs`) | 之前会把 cargo convention 路径误报为非关键字文件 / 子文件缺 `use super::*` | audit-pitfalls §39a — 加 `src/bin/<name>.rs` + `build.rs` 白名单(2026-09-18 euv-docs PR #31) |
| rule 19 (`tests/<sub>/fn.rs non-super use`, R14.7) | 顶层 `tests/<file>.rs` loose 文件(没有中间 mod.rs 子目录)应有 `use crate::...` 而不是 `use super::*;` —— 本 rule 不扫这些,所以不报 FALSE,but 注意 loose `tests/<file>.rs` 由 §14.4 限制(否则就是 integration test crate root,`super` 不存在 = E0433)。**新加的 check,没有已知盲点**;若报 FAIL,先看 audit-pitfalls §43,大概率是 true positive,跑 `strictify_tests_layout.py` auto-fixer。 | audit-pitfalls §43 — R14.7 exception list(2026-09-25 新增) |
| rule 20 (fn-body blank lines) | 默认 base 是 `origin/master`,fork 仓会把本地 master-only commits 算进 PR diff,误标 upstream 历史 | audit-pitfalls §39b — 用 `merge-base HEAD upstream/master` 作 base + diff hunks scoping |

**当 audit 报 FAIL 但 §xx 的 false-positive 描述符合**:先 git diff 看该文件是不是上游原状 carry-over,如果是,在 PR body 标注"upstream code, deferred to follow-up",**不要为了 PASS 改原代码语义**(会偏离 monorepo PR scope)。
