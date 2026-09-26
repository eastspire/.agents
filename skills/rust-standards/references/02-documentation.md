# 2. 注释规范

## 2.1 必须添加文档注释的对象

所有以下项目必须附带完整的 **英文文档注释(doc comment)**:

- 所有类型(结构体、枚举、trait、type 别名)
- 所有常量、静态变量
- 所有函数 / 方法
- 所有 `impl` 块(每个 `impl` 都必须有独立文档注释,**不能仅靠 `//` 行注释**)

## 2.2 doc comment 格式模板

```rust
/// Brief description of the item.
///
/// Extended explanation if needed.
///
/// # Arguments
///
/// - `Type` - Description of argument 1.
/// - `Name: Constraint` - Description of argument 2.
///
/// # Returns
///
/// - `Type` - Explanation of return value.
///
/// # Panics
///
/// Explanation of when this function might panic.
```

**关键约束(2026-09-26 user 加强,2026-09-27 user 第三次强化)**:

1. **`# Arguments` 与 `# Returns` 行必须紧跟空 `///` 行**(section header 之前留一行空 `///`,section 内容之前留一行空 `///`)。
2. **`# Arguments` 的 `- \`Type\` - description` 与 `# Returns` 的 `- \`Type\` - description` 各自使用 `-`(dash)分隔符(`Returns` 也允许 `:` 分隔符,但两种形式不可混用)**。
3. **类型签名精确匹配(2026-09-27 user 钦定,新加的硬约束)**:每个 `- \`Type\` -` 中的 `Type` 必须等于 fn 签名中的实际参数类型(保留 `&` 与 `` ` ``),**不允许**把泛型 `T` 写成 `T: Sized`、把 `&self` 写成 `Self`、把 `&'static mut T` 写成 `'static mut T`。完整规则:
   - `- \`&Self\` -` 用于 `&self` / `&mut self` 方法
   - `- \`T\` -` 用于泛型参数 `T`(不带 where 子句约束)
   - `- \`&str\` -` 用于 `&str` 参数(保留 `&`)
   - `- \`Result<u32, E>\` -` 用于 `Result<u32, E>` 返回类型(完整保留嵌套)
   - `- \`&'static mut T\` -` 用于 `&'static mut T` 返回类型(保留前置 `&` 与生命周期)
   - 同样适用于 `# Returns`:类型必须精确等于签名返回类型
4. **Brief description 必须在第一个 `#` section 之前**:doc 块的第一行非空 `///` 不能直接是 `/// # Arguments` —— 必须先有至少一行英文 prose 描述 fn 的功能。

**完整示例**:

```rust
/// Compares two `Context` instances for equality.
///
/// # Arguments
///
/// - `&Self` - The first `Context` instance.
/// - `&Self` - The second `Context` instance.
///
/// # Returns
///
/// - `bool` - True if the instances are equal, otherwise false.
#[inline(always)]
fn eq(&self, other: &Self) -> bool {
    self == other
}

/// Retrieves an internal framework attribute.
///
/// # Arguments
///
/// - `InternalAttribute` - The internal attribute key to retrieve.
///
/// # Returns
///
/// - `Option<V>`: The attribute value if it exists and can be cast to the specified type.
#[inline(always)]
fn try_get_internal_attribute<V>(&self, key: InternalAttribute) -> Option<V>
where
    V: AnySendSyncClone,
{
    None
}
```

**验证脚本**:`scripts/verify_doc_comment_format.py` 四层校验:

| Layer | 内容 |
|-------|------|
| 1 | 存在性 — 每个非测试 fn / impl 必须有 `///` 注释 |
| 2 | 完整性 — 有非 self 参数的 fn 必须有 `# Arguments`,非 () / Self 返回必须有 `# Returns` |
| 3 | 格式 — `Arguments` 与 `Returns` 的 `-` 行格式(`- \`Type\` - description` / `- \`Type\`: description`) |
| 4 | **签名类型匹配(2026-09-27 新加)** — `Arguments` 里每个 `- \`Type\` -` 的 `Type` 必须等于 fn 签名的实际参数类型;`Returns` 同理。doc 块第一个非空 `///` 不能直接是 `# Arguments`(必须有 prose 描述) |

被 `audit_rust_standards.py` check 35 调用,exit 1 即违规。**已知 caveat(2026-09-27 实测 801 真违规 in euv)**:本规则对旧代码是破坏性变更,authoritative enable 后会触发大量现存 doc comment 的连锁修改 —— 计划单独立 PR sweep(参考 2026-09-26 check 23-37 的接入节奏)。

## 2.3 字段级注释

- 结构体/枚举每个字段必须单独注释其用途。
- 元组结构体的每个字段同样要注释。

## 2.4 lib.rs 必须的 `//!` 头部注释 (2026-09-26 第五轮 user 钦定)

`lib.rs` 必须以 `//!` doc block 开头,**强制结构**:

```rust
//! <package_name>     // 文本必须等于 [package].name
//!
//! <description>      // 项目自身描述
```

第一行文本(`//!` 后)必须等于最近 `Cargo.toml` 的 `[package].name`
字段值 — 这是强制性对应关系,改名 crate 时 lib.rs 第一行必须同步改。

**user 原话**(2026-09-26 第五轮):"对于 lib.rs 必须要检查是否存在 `//!`
注释,注释第一行 `//!` 后是包名后面是一行 `//!` 再后面才是内容"。

**验证脚本**:`scripts/verify_lib_rs_doc_comment.py` 读最近 Cargo.toml
的 `[package].name`,校验 3 行结构 + 第 1 行文本匹配;被
`audit_rust_standards.py` check 37 调用,exit 1 即违规。

**euv 真仓命中**:
- `core/src/lib.rs:1` 写 `//! euv` 但包名是 `euv-core`(mismatch)
- `example/src/lib.rs:1` 写 `//! euv Example` 但包名是 `euv-example`
- `docs/src/lib.rs:1` 完全没 `//!` 块(直接 `mod component;` 开头)
- `cli/src/lib.rs:1` 写 `//! euv CLI` 但包名是 `euv-cli`
- `macros/src/lib.rs:1` 写 `//! euv_macros` 但包名是 `euv-macros`

**历史 audit-pitfalls §17** 的"lib.rs `//!` doc comment IS allowed"
条目标记为 **DEPRECATED** —— 这条规则从"可加可不加"升级为"必须
按固定 3 行结构加"。

## 2.5 mod.rs 硬性规则:不加任何注释

**`mod.rs` 不加任何注释**(既不写文件头 `//!`,也不写 `mod r#xxx;` 之间的 `// xxx 模块`),保持纯结构组织。**这一条是硬性规则,不可例外。**

## 2.6 impl 块内允许单行注释

`impl` 块内允许使用 `// ...` 形式的**单行注释**解释特定代码行的意图(如解释某段宏调用、某条 `#[derive]` 行为)。

## 2.7 PR body 与 commit message 必须纯英文

`rust-standards` 文档注释本身必须英文(§2.1 / §2.2),与代码同源;**提交说明 (commit message) 与 PR body / PR title 也必须纯英文**——这是用户的明确偏好,跨所有 GitHub 公开仓库。

适用范围:
- commit subject 与 body(无论 `git commit -m`、merge commit、squash commit)
- PR title 与 body
- PR 评论、issue、discussion 评论(若该仓库允许公开回复)
- `CHANGELOG.md` / `RELEASES.md` 此类面向发布受众的文件

非适用范围:
- 代码内的 `///` / `//!` / `//` 注释已在 §2.1 强制英文覆盖
- agent 与用户之间的中文对话本身(本规则约束的是**写入仓库的提交说明**,不是对话语言)
- agent 自己的 TODO / session 笔记 / `agent_helpers.py` 等本地脚本

写作风格:
- 三段式: `## Summary` / `## Verification` / `## Notes`
- 不要复述已有 issue / PR 内容,先 `gh issue list --search` / `gh pr list --search` 看是否已在讨论
- 不要主动揽活(不写 "happy to help / happy to PR / I can implement" 等)
- 不要主动 `@` reviewer / maintainer,发完等回复
- commit subject 使用 `git-conventional-commits` 风格:`<type>(<scope>): <subject>`,type ∈ {feat, fix, refactor, perf, docs, test, build, ci, chore, style}
- commit body 多段用空行隔开,bullet 列表用 `-`
- 中英术语混排时,以英文术语为主(例如写 `impl` 块而非 `impl 块`)

参考资料:`gh-pr-creation-workflow` skill 的 "PR body 风格" 章节给出了具体的 `gh pr create` heredoc 模板。
