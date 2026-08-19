---
name: code-formatting-tools
description: 'Format files (web/MD/YAML/TOML/Rust) before commit.'
license: MIT
metadata:
  version: 1.0.0
---

# Code Formatting Tools

**核心规则**:**改文件 → 跑对应官方 fmt 工具 → 再 commit**。不在 commit / PR 里出现纯空白 diff。

触发词:format, fmt, eslint, prettier, yamlfmt, taplo, cargo fmt, euv fmt, hyperlane fmt, 格式化, format-on-save, lint --fix, rustfmt, 代码风格。任何涉及 `.rs / .ts / .tsx / .css / .md / .yml / .toml` 的 diff 在 commit 前都加载本 skill 选工具。

## 0. Decision Tree

| 文件类型 | 工具 | 命令 |
| --- | --- | --- |
| `.ts / .tsx / .js / .jsx / .css / .scss / .vue / .svelte` | ESLint + Prettier | `npm run lint -- --fix && npx prettier --write "<file>"` |
| `.md` | Prettier | `npx prettier --write "**/*.md"` (或 scoped 到改过的 md) |
| `.yaml / .yml` | yamlfmt | `yamlfmt <file>` (fallback `taplo fmt <file>`) |
| `.toml` | taplo | `taplo fmt <file>` |
| `.rs` 在 **euv** 项目 | euv-cli | `euv fmt` —— 真的会展开 `html!` / `class!` / `vars!` macros 后再格式化 |
| `.rs` 在 **hyperlane** 项目 | hyperlane CLI | `hyperlane fmt`(实测是 `cargo fmt` 的 wrapper,不会展开 hyperlane-macros) |
| 其它 `.rs` | rustfmt | `cargo fmt --all` |
| `.json` | Prettier | `npx prettier --write <file>` |
| `.html` (非 euv macro 输出) | Prettier | `npx prettier --write <file>` |

## 1. Web 项目 (JS/TS/JSX/CSS/Vue/Svelte)

```bash
# 标准组合：eslint 修 lint + Prettier 修格式
npm run lint -- --fix     # 或 npx eslint . --ext .ts,.tsx,.js,.jsx,.vue --fix
npx prettier --write "src/**/*.{ts,tsx,js,jsx,css,vue,svelte}"

# 校验（CI 用，不要 --fix）
npm run lint
npx prettier --check "src/**/*.{ts,tsx,js,jsx,css,vue,svelte}"
```

**为什么不是手 reformat**:手动改缩进会触发 git blame 噪音 + 在 PR 里加纯空白 diff（违反用户偏好）。让工具决定。

## 2. Markdown

Prettier 是事实标准 —— frontmatter / ordered / unordered lists / code-fence 风格一致:

```bash
npx prettier --write "**/*.md"
# 校验模式（CI 推荐）
npx prettier --check "**/*.md"
```

如果项目用 markdownlint（lint-only，不重写），先用 prettier 重写、再 markdownlint 校验剩余 lint 问题。

## 3. YAML

```bash
# 主选：Google yamlfmt（Google 内部使用，统一处理 quoting / anchor / 缩进）
yamlfmt <file>
# 备选：taplo（同样支持 YAML/TOML，多语言项目用这一个工具链）
taplo fmt <file>
```

不要混用：同一项目锁定一个工具；CI 加 `--check` 校验。

## 4. TOML

```bash
taplo fmt <file>
taplo fmt --check  # CI 校验
```

典型应用:`Cargo.toml` / `pyproject.toml` / `taplo.toml`。在 Rust 项目里,`cargo fmt` 不格式化 `.toml`,需要独立跑 taplo。

## 5. Rust 项目

| 项目类型 | 第一选择 | fallback |
| --- | --- | --- |
| euv 项目（含 `html!`/`class!`/`vars!` macros） | `euv fmt` | `cargo fmt --all`（euv macros 内不会被处理） |
| hyperlane 项目（含 `#[route]` / `#[hyperlane]` macros） | `hyperlane fmt` | 等同 `cargo fmt`(hyperlane-cli 只是 wrapper,不展开 macros) |
| 其它 Rust / 通用 crate | `cargo fmt --all` | — |

```bash
# euv 路径
cargo install euv-cli         # 装过一次即可
euv fmt
# 或在 euv 项目根目录：`cargo install` 后 `euv fmt` 自动定位 `Cargo.toml`

# hyperlane 路径（hyperlane CLI 通常由 `cargo install hyperlane-cli` 装出）
hyperlane fmt
# fallback
cargo fmt --all
```

**关键差异**:
- euv `html! { ... }` 内 child 缩进、`class! { ... }` 嵌套、`vars! { ... }` 缩进,`cargo fmt` 不管 —— **必须用 `euv fmt`**(真的会展开 macro)。
- `hyperlane fmt` **只是 `cargo fmt` 的 wrapper**(hyperlane-cli v0.1.25 实测),不做 macro 展开 —— 等同直接跑 `cargo fmt`。走 `hyperlane fmt` 只是为了"用项目官方入口"这一契约,不期待 macro 内特殊行为。macro 内部要做严格对齐,需要 nightly rustfmt + `rustfmt.toml`,或手调。
- 通用 Rust 没有 macro 折行需求的项目,直接 `cargo fmt --all` 即可,不必装 euv-cli / hyperlane-cli。

## 6. 流程（commit / PR 前）

1. 改完一个文件 → 一行命令 fmt（见上表）
2. **commit 之前** → 跑一次项目的 `fmt:check` / `lint:check` 确认无 diff
3. **开 PR 之前** → 再跑一次（多个 commit 累积格式漂移）
4. CI 通常跑 `--check` 模式:发现本地未跑 fmt 的 diff → CI 红 → 浪费时间

**反模式（不要做）**：
- ❌ 在 PR review 之前手动 reformat —— PR comment 已经被 fuzz 化
- ❌ 跳过项目 fmt 工具、改用 `sed` / `awk` 改空白
- ❌ 在 `.rs` 文件里手动对齐宏折行 —— `euv fmt` / `hyperlane fmt` 会重排
- ❌ 跨类型用错工具（如 `cargo fmt` 改 YAML） —— Cargo fmt 不支持

## 7. 互锁 / 邻近 skill

- **`euv`**（/ `euv-standards` / `euv-ui-standards`）—— euv 项目代码里用 `euv fmt`。该 skill 的 `## euv-cli` 章节现在已能引用本 skill。
- **`hyperlane`**（/ `hyperlane-standards`）—— hyperlane 项目代码里用 `hyperlane fmt`。
- **`git-standards`** —— commit / PR 文案规范（与本 skill 互补,本 skill 管代码格式、git-standards 管 commit 措辞）。
- **`rust-standards`** —— Rust 项目通用规范,Rust fmt 工具链走本 skill。
