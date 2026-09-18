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
| [scripts/audit_rust_standards.py](scripts/audit_rust_standards.py) | 完整 19 条 audit 规则(覆盖 §1 / §2 / §5 / §6 / §9 / §11 / §14 / §17 / §R1.3c + check 19 fn-body blank lines)。**False-positive 列表**见 `references/audit-pitfalls.md`(§1-§42,新增 §39a `src/bin/<name>.rs` + `build.rs` 白名单 / §39b check 19 upstream-aware base + diff hunks scoping / §40 leaf-mod.rs use super 豁免 / §41 try_X().unwrap() 上游 idiom 豁免 / §42 sub-file ext::Type 上游 carry-over,2026-09-14 hyperlane PR #34 monorepo 迁移实测 + 2026-09-18 eastspire/euv-docs PR #31 feat/cli-binary 实测)。 |

## 关键硬性规则(快速记忆)

> **⚠️ 任何一条违反 = 开发者 review 驳回**。下面是 13 条项目级 hard rule,违反任一条 PR 必被打回。完整定义在 `references/` 子文件,本表是 cheat-sheet。

1. **每个目录只放 9 种关键字文件之一**:`const.rs` / `static.rs` / `fn.rs` / `enum.rs` / `struct.rs` / `trait.rs` / `impl.rs` / `type.rs` / `mod.rs`,互不混用(参见 01)。
   - **Pitfall(项目级 drift 易被复制)**: 如果当前 `src/page/<feature>/hook/` 目录里已经有 `*_fn.rs`(例 `lighting/hook/lighting_fn.rs`, `raytrace/hook/raytrace_fn.rs` 之前是同一个问题),新增/重命名文件**仍必须用 `fn.rs`**。**不要**为"保持一致"也跟着加 `*_fn.rs`——目录应该保持合法,drift 单独开 PR 修(改目录里全部 `*_fn.rs` → `fn.rs` + `mod.rs` 改成 `mod r#fn;`)。验证: 新写文件前先 `ls <dir>` 看现有命名, 再 grep 仓里同类目录是否已经有 drift 漂移。
   - **Pitfall(`fn.rs` 内禁止 `type` / `enum` / `struct` / `impl` 声明)**: 新写 `compute_child_ops_plan` 时如果顺手定义 `pub(crate) enum ChildOpPlan` 在 `fn.rs` 里,违反 §1.3 关键字文件纯净性。新 enum 必须放 `enum.rs` 并通过 `mod r#enum;` + `pub use r#enum::*;` 暴露,函数文件本身只能含 `fn` 与 `pub fn`。验证:`grep -nE '^(pub |pub\(crate\) )?(struct|type|enum|trait|impl)' <file>` 应只命中注释或 doc string,代码本体 0 行。**例外**:`#[cfg(test)] mod tests { ... }` 块内的 helper `type` 别名(测试专用,不污染 production purity)不算 violation。
2. **`mod.rs` 必须用 raw identifier**:`mod r#struct;` 而非 `mod struct;`,但**文件名**仍是 `struct.rs`(参见 01.4)。**关键字文件也走 raw identifier**:`fn` 是关键字 → `mod r#fn;` (对应 `fn.rs`)。
3. **`mod.rs` / `lib.rs` / `Cargo.toml` 不加任何注释** — 不写 `//!`、不写 `// xxx`、不写 `# xxx`。这三类文件纯结构,无解释性文字(参见 02.5 + 06)。
4. **`mod.rs` 三段式**:`mod r#xxx;` + `pub use`/`pub(crate) use` + 末尾 `use super::*;`,无空行(参见 06.2)。
5. **子文件第一行** `use super::*;`,**禁止** `use crate::xxx;` 长路径(参见 06.3)。
   - **Pitfall(lib.rs 统一导入 vs 子文件重复 import)**: 子文件已经通过 `use super::*;` 拿到父模块 `pub use std::{...}` block re-export 的所有符号,函数体内**禁止再次写 `use std::xxx::yyy;`**——`std` / 标准库集合类型(`HashMap` / `HashSet` / `Vec` / `VecDeque` / `Cow` / `Rc` 等)已在 lib.rs `pub use std::{...}` 集中导入,sub-file 直接写 `HashMap` / `HashSet` 不需要前缀。验证:写新 fn 时先 `grep -E '^pub use ' <crate>/src/lib.rs | head` 看 lib.rs 已 re-export 什么,再决定是否需要 fn 内 use。如果 fn 内仍然 `use std::xxx;` → clippy `unused_imports`(因为已经被 super::* 引入),review reject。
6. **所有变量 / 参数 / 返回值必须显式类型**,禁止 `let items = Vec::new();`(参见 05.1)。
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
12. **WASM 项目**禁止显示标注任何 `inline` 宏(参见 04.3)。
13. **commit 前必跑项目官方格式化器**(euv → `euv fmt`,hyperlane → `hyperlane fmt`,其它 → `cargo fmt --all`;`.toml` 顺手 `taplo fmt`,见 `code-formatting-tools` skill §0/§5)。
   - **Pitfall(euv fmt ≠ cargo fmt)**: 在 `euv-dev/euv` 等用 euv 框架的项目上, **CI 的 `Format check` job 跑的是 `cargo fmt --check`**,**不是 `euv fmt --check`**。两者在长行 wrap 上行为不一致——`euv fmt` 不强制 100col 硬换行,`cargo fmt` 强制。**commit 前必跑两者**:
     ```bash
     euv fmt && cargo fmt --all
     euv fmt && cargo fmt --all   # 二次幂等检查
     git status --short  # 期待零改动
     ```
     漏跑 `cargo fmt` → PR CI `Format check` job fail,需要 force-push amend commit。`cargo fmt --all -- --check` 0 exit = OK。
   - **同样适用** hyperlane: CI 可能跑 `cargo fmt --check` 而不是 `hyperlane fmt --check`(以 `.github/workflows/rust.yml` 实际 job 为准,开 PR 前 `gh run view <run-id> --log` 验证)。
   - **Pitfall(rebase conflict 解决后 `cargo fmt --check` 仍 fail,euv 仓 2026-09-13 PR #217→#219 实测)**: git rebase 处理 `<<<<<<<` 冲突块时,即使删掉中间内容后 `cargo check` 退出 0,`cargo fmt --check` 仍可能因「孤儿重复注释 / 行缩进错位」挂——`cargo check` 不读注释,`cargo fmt` 读。**预防**:rebase amend 之前先 `cargo fmt --all -- --check`,exit 非零先 `cargo fmt` 修一遍再 amend。
14. **禁止使用 `#[allow(...)]` / `#[allow(...)]` 类宏遮蔽 lint**(2026-09-14 user 原话:"从根源修复warn,禁止使用allow宏")。clippy / rustc 任何 warning(`needless_range_loop` / `unused_imports` / `dead_code` / `clippy::all` 等)**必须从根源修复**,**禁止用 `#[allow]`、`#[allow(unused)]`、`#[allow(clippy::xxx)]` 跳过**。
   - 例:`for j in i+1..i+end_len { out.push(bytes[j]); }` 触发 `clippy::needless_range_loop` → 改成 `for &b in &bytes[i+1..i+end_len] { out.push(b); }`,**不是** `#[allow(clippy::needless_range_loop)]`。
   - 例:`static_mut_refs` 安全情况下,改用 `&mut *(*std::ptr::addr_of_mut!(STATIC)).get_0().get()` 表达式包装,**不是** `#[allow(static_mut_refs)]`(参见 `euv-standards/references/signal-subscription-bindings.md` 2026-09-12 实测)。
   - **例外**(2 个真实工作流场景):(a) 第三方宏展开产生的 dead_code,无法在源层消除(极罕见);(b) `#[cfg(test)] mod tests` 内测试专用 helper 函数,production build 看不到 — 这两类先用 clippy `#[expect(...)]` 配合 issue 编号注释,**默认仍禁止**。
15. **`fn.rs` / `impl.rs` / `mod.rs` 文件体内禁止硬编码 byte / char / 多字符 string literal**(§R1.3c literal purity,2026-09-14 euv PR #233 实测)。任何 `b"<script"` / `b'<'` / `b'>'` / `"<!--"` / `"-a1b2c3"` 这类 magic byte / string literal 必须移到同目录的 `const.rs`(或更上游的 module-level const),通过 `pub const HTML_LT: u8 = b'<';` + `use super::*;` 引用。
   - **触发**:写 HTML / WASM / 协议解析 / 文本 tokenizer / 任何"按字节比较"的逻辑时,几乎必然出现 magic byte 序列;**直接 hardcode 进 fn body = review reject**。
   - **const 命名规范**:常量名应能描述 byte 含义(`HTML_LT` / `HTML_COMMENT_OPEN_BYTES` / `TOKEN_OPEN_PREFIX_BYTES`),**不是** `BYTE_60` 这种 octal-ish 数字命名。
   - **长度从 const 拿,不写 magic number**:`bytes[i..i + HTML_COMMENT_OPEN_BYTES.len()]` 优于 `bytes[i..i + 4]`。
   - **audit check 18**: `fn.rs hardcoded byte/string literals (R1.3c literal purity)` — 检测 PR diff 中 fn.rs / impl.rs 内 `b"..."` / `b'.'` / 非 trivial 长度 `&str` literal,排除 doc comment / `#[cfg(test)]` / `let` binding / 已知转义 (`b'\n'` `b'\t'` `b' '` `b'\0'`)。
   - **const.rs 内排序**(沿用现有 `const` 按 `(name_len, name_lex)` 排序):多个 byte literal const 加进 const.rs 时按 const 名长度优先,长度相同按字母序,与 §1.5 const.rs 内排序规则一致。

## 跨章节冲突时

按以下优先级(高 → 低):**安全 > 错误处理 > 项目既有规范 > 性能 > 命名 > 风格**。任何与此 skill 冲突的其他 skill 指引,以本 skill 为准。

## Pre-commit 必跑(顺序固定)

**这 4 步任一非零 exit = 不得 commit / push / 提 PR。开发者 review 时必看,缺一项驳回。**

**新 PR / 修改后跑这一组, 任一项非零 exit 必须修到 0 再 commit**:

```bash
# 1. 15 项硬性规则批量 audit(2026-09-14: 13 → 15 项,新增 §14 no-allow + §15 R1.3c literal purity)
python3 ~/.agents/skills/rust-standards/scripts/audit_rust_standards.py <repo-root>
# exit 0 = 全部通过;非零 = 逐项修(每条 FAIL 都打印 sample lines)

# 2. 官方格式化器幂等(双跑)
euv fmt && cargo fmt --all
euv fmt && cargo fmt --all
git status --short   # 期待空 = 幂等

# 3. clippy 0 警告(2026-09-14 user 原话:从根源修复,禁止 #[allow])
cargo clippy -p <your-crate> --all-targets --offline
# 输出含任何 warning = 不得 commit,改 source 修到 0 exit

# 4. test 编译通过
cargo test --no-run -p <your-crate>
```

PR 提交后 `gh pr checks <N>` 必须 build/clippy/tests/check/setup 5/5 pass。`Format check` job 单独注意——它跑 `cargo fmt --check` 而不是 `euv fmt --check`(参见 rule 13 pitfall)。

### 已知 audit 盲点(命中时不一定是真违规,先看 audit-pitfalls 再判断)

| audit rule | 盲点 | 缓解 |
|---|---|---|
| rule 6 (`mod.rs missing trailing use super::*`) | leaf mod.rs(子文件全不引用 parent symbol)加 `use super::*;` 触发 `unused_imports` warning | audit-pitfalls §40 — 加了智能豁免,leaf mod 不报 FAIL |
| rule 17 (`sub-file body uses external crate full path`) | 只扫根 `[workspace.dependencies]`,**不扫子包** `[dependencies]`(type annotation `proc_macro2::TokenStream` 在 macros 子包、`log::Level` 在 cli 子包不会被抓到) | audit-pitfalls §42 — 已知限制,monorepo PR 留 follow-up |
| rule 1 (`non-keyword prod files`) | 原本会把 `main.rs` 误报为 non-keyword | audit-pitfalls §39 — 加 `main.rs` 白名单 |
| rule 1 / rule 7 (covers `src/bin/<name>.rs` + `build.rs`) | 之前会把 cargo convention 路径误报为非关键字文件 / 子文件缺 `use super::*` | audit-pitfalls §39a — 加 `src/bin/<name>.rs` + `build.rs` 白名单(2026-09-18 euv-docs PR #31) |
| rule 19 (fn-body blank lines) | 默认 base 是 `origin/master`,fork 仓会把本地 master-only commits 算进 PR diff,误标 upstream 历史 | audit-pitfalls §39b — 用 `merge-base HEAD upstream/master` 作 base + diff hunks scoping |

**当 audit 报 FAIL 但 §xx 的 false-positive 描述符合**:先 git diff 看该文件是不是上游原状 carry-over,如果是,在 PR body 标注"upstream code, deferred to follow-up",**不要为了 PASS 改原代码语义**(会偏离 monorepo PR scope)。
