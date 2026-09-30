---
name: crates-cli-usage
description: Use when running cc/crates-cli bump/sync/publish or in CI.
---

# crates-cli (cc) 使用规范

**Status: superseded by `rust-workspace-release`.** This skill predates the
`crates-cli` → `crate-cli` (binary `cc` → `crate`) rename and the
`--target-version` conditional. Use `rust-workspace-release` for the
current binary name, the two-branch conditional rule, and the
maintainer-triggered dispatch pattern. This skill is kept only as a
historical reference for `crates-cli` / `cc` invocations and the
`git install` retry loop shape.

Tool: `~/code/ctares/crates/crates-cli`, lib `crates_cli`, bin `cc`.

## 安装

- **只能 git 安装**：`cargo install --git https://github.com/crates-dev/ctares.git crates-cli`（CI 里套 8 次重试循环）。
- `cargo install crates-cli` 必失败（"could not find in registry"）——crates.io 归一化后与 willothy 的 `crates_cli` 冲突，永远 publish 不上去。hyperlane run 36198290126 实证。

## 命令语义

- `cc bump [--patch|--minor|--major]`：三架构通吃——单 crate / virtual workspace（全员同幅度）/ 有根包 monorepo。bump 后自动 realign 依赖方对被 bump 本地依赖的 version 引用（含根 `[workspace.dependencies]`）。成员用 `version.workspace = true` 时只改 `[workspace.package].version`。
- `cc sync`：把 `[workspace.dependencies]` 本地 path 条目的 version 对齐根版本；**含根包自引用 `path = "."`**；解析 `version.workspace = true` 继承。
- `cc publish`：按 `[workspace.members]` **声明序**发布——成员顺序必须依赖在前（不是字母序！）。根包无成员依赖时最后发布，有成员依赖时插入拓扑位置。`publish = false` 成员自动跳过。`version.workspace = true` 自动解析。

## 坑

- **path-only dev-dependencies 不约束发布顺序**（cargo publish 剥离 dev-deps，纯 path 无 version 的不查 registry）；带 version 的 dev-dep 仍约束。euv-macros dev-dep 根包 `euv = { path = "../" }` 就是这种。
- members 顺序错会报 `invalid publish order: ... reorder [workspace.members]`——按拓扑序重排 members 即可（euv: `[core, macros, cli, ui, engine, example]`）。
- 非成员的 crate（如 euv `docs/`，不在 workspace）cc 完全不管，CI 需单独薄处理（sed 版本 + `cargo publish --manifest-path`）。
- 改 Cargo.toml 字段必须 toml_edit 保格式（rust-standards §15）；改完跑 `python3 ~/.agents/skills/rust-standards/scripts/verify_dep_order.py <repo>` 须 0 违规。

## CI 参考实现

- hyperlane `.github/workflows/rust.yml`：install(git+retry) → `cc bump --patch` + `cc sync` + commit/push → cargo login → `cc publish` → crates.io 验证。每次 master push 自动 patch 升版。
- euv `.github/workflows/rust.yml`：dev 驱动版本（CI 不 bump），publish job 内 `cc sync` → `cc publish` → docs 单独发布 → 验证。
- 首战实证：euv run 36200393154 全绿，7 crate 0.26.3 上 crates.io，example 正确跳过。
