---
name: rust-crate-use
description: Rust 第三方 crate 查询与使用。**任何涉及 Rust crate、crates.io、docs.rs、cargo add、use 路径、feature flag、依赖添加、Rust 库查询的任务,必须先调用 skill_view('rust-crate-use'),并运行 scripts/fetch_docs_rs.py 实地查询 docs.rs / crates.io,禁止基于训练数据记忆推断 API 签名**。触发词:rust crate、crates.io、docs.rs、cargo add、use 路径、API 文档、Rust 库、import 路径、feature flag、版本号、Cargo.toml 依赖、第三方库、external crate、kebab-case vs snake_case。当用户提到 serde、tokio、anyhow、lombok-macros、thiserror、axum、hyper、actix、reqwest 等任一具体 crate 名时立刻加载。
---

# Rust 第三方 crate 使用规范

## 调用时机(强制规则)

**不要**等 description 自动触发。**每个新会话 / 每个新任务**遵守以下规则:

1. **用户提到任何 Rust 第三方 crate** → 立刻 `skill_view('rust-crate-use')`
2. **用户提到"加这个依赖"、"用 XXX 库"、"查 docs.rs"、"这个 Rust API 怎么用"** → 立刻加载 + 跑 `scripts/fetch_docs_rs.py`
3. **看到任何具体 crate 名**(serde / tokio / anyhow / thiserror / axum / hyper / actix / reqwest / lombok-macros / ...) → 立刻加载
4. **即使 rust-standards 已经被加载**,只要涉及**第三方** crate,本 skill 必须**额外**叠加加载
5. **加载后**才写 `Cargo.toml`、写 `use` 语句、给 API 描述
6. **绝不基于训练数据记忆推断**:API 签名、模块路径、feature flag 名,必须实地查询
7. **优先级次于 rust-standards**:rust-standards 没加载时,本 skill 也不能完全生效(命名/导入/模板规则在 rust-standards)

## 标准工作流

```
1. 解析 crate 名(kebab-case vs snake_case)
2. 查 Cargo.toml 声明的版本约束,查 Cargo.lock 实际解析版本
3. 跑 scripts/fetch_docs_rs.py <crate> [--version x.y.z] 拿权威元信息
4. 根据返回的 crate_url 在 docs.rs 上找具体类型/函数签名
5. 把变更写入 Cargo.toml,跑 cargo check / cargo test 验证
6. 用 templates/crate-research-report.md 留底
```

## 检索方式

按 "我现在要做什么" 查表,跳到对应章节:

| 我要做什么 | 跳到 |
|-----------|------|
| 解析版本号 / 处理 Cargo.lock 漂移 | [references/version-resolution.md](references/version-resolution.md) |
| kebab-case vs snake_case 包名/导入名 | [references/package-name-vs-import.md](references/package-name-vs-import.md) |
| 添加新依赖前的尽职调查 | [templates/crate-research-report.md](templates/crate-research-report.md) |

## 必备脚本

| 脚本 | 用途 | 用法 |
|------|------|------|
| [scripts/fetch_docs_rs.py](scripts/fetch_docs_rs.py) | 查 crates.io 元信息 + docs.rs 页面摘要 | `python3 scripts/fetch_docs_rs.py <crate> [--version x.y.z] [--crate-info-only]` |

**脚本返回字段说明**:

```json
{
  "name":             "input crate name (as provided)",
  "package_name":     "official crates.io package name (e.g. 'lombok-macros')",
  "import_name":      "Rust import name with - → _ (e.g. 'lombok_macros')",
  "newest_stable":    "recommended version to inspect from crates.io",
  "target_version":   "the version we ended up querying docs.rs for",
  "total_versions":   "number of published versions (not the list itself)",
  "description":      "one-paragraph crate description",
  "repository":       "source repo URL",
  "documentation":    "official docs URL (usually docs.rs/<name>)",
  "downloads":        "lifetime download count",
  "recent_downloads": "last 90 days",
  "features":         "list of available feature flags",
  "crate_url":        "https://docs.rs/<name>/<target_version>/ — use this in browser",
  "target_modules":   "top-level modules in the rustdoc nav (first ~20)",
  "error":            "hard error — crate not found on crates.io (exit 2)",
  "warnings":         "soft warnings — e.g. version not built on docs.rs (exit 0)"
}
```

## 关键硬性规则

1. **必须实地查询**:`fetch_docs_rs.py` 是**强制工具**,不只是便利。**禁止**靠训练数据记忆 API 签名(API 经常在 minor version 变化)。
2. **版本必须匹配 docs.rs**:`--version` 不传时默认用 `newest_stable`(crates.io 推荐);传了则**严格匹配**传入版本,若 docs.rs 上是占位页(占位页把 version 字段归零为 `"0.0.0"`),返回 `warnings` 告知用户版本可能不存在。
3. **包名 vs 导入名**:`lombok-macros` 是 crates.io 包名,Rust 代码里写 `use lombok_macros::...`。脚本自动转换,不要在 `Cargo.toml` 里写 `lombok_macros = ...`(那是导入名不是包名)。
4. **优先复用现有依赖**:本项目内已经在用的 crate,直接复用;新依赖必须先评估是否能用现有依赖 + 内部宏实现(参见 rust-standards 的 13.1 节)。
5. **API 变更后必须留底**:`templates/crate-research-report.md` 记录:用哪个版本、用了哪些 API、必要的 feature、未能核实的部分。
6. **硬错误 vs 软警告**:`error` 字段非空 = exit 2(中断,告知用户 crate 找不到);`warnings` 字段非空 = exit 0(继续,但提醒用户核实,例如版本可能不存在)。
7. **不可伪造已核验结论**:`fetch_docs_rs.py` 没跑成功时,**不要**声称已查阅 docs.rs;显式告知用户无法核验。
8. **占位页陷阱**:docs.rs 对不存在的版本返回 200 + 占位页(嵌入 JSON 把 version 归零);脚本会**自动识别**这个占位页并写入 `warnings` 字段,不要把占位页当成真实文档。
9. **`--crate-info-only`**:只要 crates.io 元信息(不查 docs.rs),用于纯依赖体积、license、下载量等 metadata 查询场景。

## 与 rust-standards 配合

- 本 skill 解决"**怎么查**第三方 crate"的问题
- rust-standards skill 解决"**怎么组织** Rust 项目结构、命名、模块"的问题
- **优先 rust-standards**(优先级更高),本 skill 仅在涉及第三方 crate 时叠加生效
- 例如:加 `lombok-macros` 时 → 先 rust-standards 看 `Data/New/CustomDebug` 怎么用 → 再用本 skill 确认 `lombok_macros::Data` 在当前 0.1.4 版本确实存在且签名一致
