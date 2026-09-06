---
name: rust-standards
description: 'Rust 开发规范(最高优先级,与其他 skill 冲突时以此为准)。**任何涉及 Rust、Rust 代码、cargo、crate、impl、trait、derive、Result、所有权、借用、生命周期、mod.rs、lib.rs、关键字文件、raw identifier、lombok、过程宏、proc-macro、euv、hyperlane、html!、class!、ServerHook、Signal<T>、tokio、http server、wasm-pack、WebAssembly、UI framework 的任务,必须先调用 skill_view("rust-standards"),不靠 description 软触发**。互锁 skill:euv 任务必同时加载 euv-standards + euv-ui-standards;hyperlane 任务必同时加载 hyperlane-standards。适用于:新项目脚手架、现有 Rust 代码维护、PR 审查、重构、模块划分、命名、错误处理、性能优化、依赖管理、测试策略。'
---

# Rust 开发规范

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

## 可复用模板

| 模板 | 用途 |
|------|------|
| [templates/lib-rs.md](templates/lib-rs.md) | `lib.rs` 完整结构(普通 / proc-macro 两种) |
| [templates/mod-rs.md](templates/mod-rs.md) | `mod.rs` 三段式(标准 / 简化 / 私有 / 测试 四种) |
| [templates/sub-file.md](templates/sub-file.md) | `struct.rs` / `impl.rs` / `fn.rs` / `enum.rs` / `trait.rs` / `type.rs` / `const.rs` 七种 |
| [templates/cargo-toml.md](templates/cargo-toml.md) | `Cargo.toml` 完整配置(lib / proc-macro / bin 三种) |

## 关键硬性规则(快速记忆)

1. **每个目录只放 9 种关键字文件之一**:`const.rs` / `static.rs` / `fn.rs` / `enum.rs` / `struct.rs` / `trait.rs` / `impl.rs` / `type.rs` / `mod.rs`,互不混用(参见 01)。
   - **Pitfall(项目级 drift 易被复制)**: 如果当前 `src/page/<feature>/hook/` 目录里已经有 `*_fn.rs`(例 `lighting/hook/lighting_fn.rs`, `raytrace/hook/raytrace_fn.rs` 之前是同一个问题),新增/重命名文件**仍必须用 `fn.rs`**。**不要**为"保持一致"也跟着加 `*_fn.rs`——目录应该保持合法,drift 单独开 PR 修(改目录里全部 `*_fn.rs` → `fn.rs` + `mod.rs` 改成 `mod r#fn;`)。验证: 新写文件前先 `ls <dir>` 看现有命名, 再 grep 仓里同类目录是否已经有 drift 漂移。
2. **`mod.rs` 必须用 raw identifier**:`mod r#struct;` 而非 `mod struct;`,但**文件名**仍是 `struct.rs`(参见 01.4)。**关键字文件也走 raw identifier**:`fn` 是关键字 → `mod r#fn;` (对应 `fn.rs`)。
3. **`mod.rs` / `lib.rs` / `Cargo.toml` 不加任何注释** — 不写 `//!`、不写 `// xxx`、不写 `# xxx`。这三类文件纯结构,无解释性文字(参见 02.5 + 06)。
4. **`mod.rs` 三段式**:`mod r#xxx;` + `pub use`/`pub(crate) use` + 末尾 `use super::*;`,无空行(参见 06.2)。
5. **子文件第一行** `use super::*;`,**禁止** `use crate::xxx;` 长路径(参见 06.3)。
6. **所有变量 / 参数 / 返回值必须显式类型**,禁止 `let items = Vec::new();`(参见 05.1)。
7. **泛型约束必须用 `where`**,不允许 `fn f<T: Bound>()` 直接写(参见 09.2)。
8. **struct / enum 优先用 lombok-macros 派生** `Data` + `New` + `CustomDebug`,禁止手写 getter(参见 17)。
9. **不引入新第三方依赖**优先于 `Cargo.toml` 整洁度(参见 13.1)。
10. **proc-macro crate 必须** `[lib] proc-macro = true;`,且 `#[proc_macro_attribute]` 全在 `lib.rs` 中实现(参见 16.1)。
11. **测试目录** `tests/` 用 `mod xxx;`(子模块名不带 `r#`),开头 `use crate_name::*;`(参见 14.1)。
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

## 跨章节冲突时

按以下优先级(高 → 低):**安全 > 错误处理 > 项目既有规范 > 性能 > 命名 > 风格**。任何与此 skill 冲突的其他 skill 指引,以本 skill 为准。

## Pre-commit 必跑(顺序固定)

**新 PR / 修改后跑这一组, 任一项非零 exit 必须修到 0 再 commit**:

```bash
# 1. 13 项硬性规则批量 audit
python3 ~/.agents/skills/rust-standards/scripts/audit_rust_standards.py <repo-root>
# exit 0 = 全部通过;非零 = 逐项修(每条 FAIL 都打印 sample lines)

# 2. 官方格式化器幂等(双跑)
euv fmt && cargo fmt --all
euv fmt && cargo fmt --all
git status --short   # 期待空 = 幂等

# 3. clippy 0 警告
cargo clippy -p <your-crate> --all-targets --offline

# 4. test 编译通过
cargo test --no-run -p <your-crate>
```

PR 提交后 `gh pr checks <N>` 必须 build/clippy/tests/check/setup 5/5 pass。`Format check` job 单独注意——它跑 `cargo fmt --check` 而不是 `euv fmt --check`(参见 rule 13 pitfall)。
