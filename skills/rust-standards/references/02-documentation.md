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
/// - `The type of the first parameter` - Description of argument 1.
/// - `The type of the second parameter` - Description of argument 2.
/// - `GenericName: GenericConstraint` - Description of argument 3.
///
/// # Returns
///
/// - `Type of return value`: Explanation of return value.
///
/// # Panics
///
/// Explanation of when this function might panic.
```

**完整示例**:

```rust
/// Brief description of the item.
///
/// Extended explanation if needed.
///
/// # Arguments
///
/// - `A: AsRef<str>` - Description of argument 1.
/// - `B: String` - Description of argument 2.
///
/// # Returns
///
/// - `String`: Explanation of return value.
///
/// # Panics
///
/// Explanation of when this function might panic.
fn test<A>(_: A, _: String) -> String
where
    A: AsRef<str>,
{
    String::new()
}
```

## 2.3 字段级注释

- 结构体/枚举每个字段必须单独注释其用途。
- 元组结构体的每个字段同样要注释。

## 2.4 lib.rs 唯一注释

`lib.rs` 唯一注释在文件开头,格式如下:

```rust
//! Crates name
//!
//! Description
```

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
