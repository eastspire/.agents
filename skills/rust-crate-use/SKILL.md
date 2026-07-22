---
name: rust-crate-use
description: Rust crate 使用与版本核对规范：优先阅读 docs.rs 官方 API 文档，确认 crate 名称、版本、特性、模块路径和示例后再编写代码。
---

# Rust Crate Use

当需要使用、推荐、升级或排查 Rust crate 时，先访问并阅读 docs.rs 对应文档，不要仅凭记忆、crate 名称或搜索摘要推断 API。

## 工作顺序

1. 根据用户给出的 crate 名称定位 docs.rs 页面：`https://docs.rs/<crate-name>/`。
2. 先确认 crate 的实际包名与 Rust 代码中的导入名是否不同，例如连字符包名通常使用下划线导入。
3. 读取与项目 `Cargo.toml` 匹配的确切版本文档：优先使用 `https://docs.rs/<crate>/<version>/`，不要默认使用 `latest`。
4. 核对目标 API 的模块路径、公开可见性、函数签名、trait bound、feature gate、错误类型和最小示例。
5. 检查项目当前 Rust edition、已有依赖版本和 feature 配置，避免无意中引入不兼容版本或额外 feature。
6. 只有在版本与 API 已核对后，才修改 `Cargo.toml` 或生成 Rust 代码。

## 版本号匹配

- `Cargo.toml` 中的版本约束必须与实际查阅的 docs.rs 版本一致；记录并说明使用的是精确版本、兼容范围还是 workspace 继承版本。
- 注意 Cargo 的语义版本解析：`"1.2.3"` 通常表示兼容范围，而不是严格锁定到 `1.2.3`；需要严格固定时使用 `=1.2.3`，但先遵循项目既有约定。
- `Cargo.lock` 中的解析版本可能与 `Cargo.toml` 声明不同。以 `Cargo.lock` 的实际版本和 docs.rs 对应版本核对最终构建结果。
- docs.rs 的 `latest` 可能已经超出项目使用版本。旧版本 API、feature 或示例发生变化时，必须切换到匹配的版本页面。
- 若 docs.rs 没有目标版本或构建失败，明确说明无法完成官方文档核验，再查 crates.io、仓库源码或发布包；不得伪造已核验结论。

## 代码要求

- 优先使用官方文档中的最小示例，并根据项目结构与现有依赖调整。
- 不凭相似 crate 的 API 猜测导入路径、类型名称或 feature 名称。
- 使用前确认 feature 是否需要在 `Cargo.toml` 中显式启用，以及默认 feature 是否被项目关闭。
- 公开 API、错误处理和生命周期约束必须以目标版本文档为准。
- 修改后运行项目适用的 `cargo check`、测试或 lint，报告真实命令结果。

## 汇报格式

完成 crate 调研或接入时，至少说明：

- crate 名称与实际 Rust 导入名
- 查阅的 docs.rs URL 和确切版本
- `Cargo.toml` 中采用的版本约束及其与 lockfile 的关系
- 使用的 API、feature 和验证命令
- 未能核实的内容或版本差异
