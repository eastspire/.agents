---
name: rust-pr-validation-checklist
description: 提交 Rust 项目 PR 前必跑的硬性验证清单 + 调研陷阱清单。在 user 提到 "PR / rust doc fix / 改 typo / wording" 时,涉及 Rust 工作必加载。结合 rust-pr-contribution-workflow 使用,聚焦"改后必跑 + 调研必复现"两件事。
---

# Rust PR 验证 + 调研 硬性清单

> 这次 session 栽过 4 个坑 (tracing 调研错方向、serde fix 不可观测、regression test 没 test 函数、push 撞坏 credential helper),所有规则都从这些坑里抽出。

---

## 1. 调研阶段 — 4 个硬性步骤

⚠️ **最大陷阱**: 看 issue 标题就直接选 issue,80% 翻车。

### 1.1 读完整 issue body
```bash
gh issue view N --repo owner/repo --json title,body,comments,state,labels
```
**目的**: 确认 issue 实际讲什么(不是标题说的什么)。

### 1.2 检查 issue 状态
- `state`: 必须是 `OPEN`
- `comments`: 扫一遍找 `I'll take this` / `I would like to work on this` / `claimed by` / `work in progress` — 有人在做就跳过
- `labels`: 优先 `good first issue` / `help wanted`

### 1.3 master 复现 — 必做
```bash
cd /tmp && rm -rf repo-check
git clone --depth 1 https://github.com/owner/repo.git repo-check
cd repo-check
```
然后用 `grep -n` / `sed -n` 找 issue 描述的精确代码位置:
```bash
grep -n "issue 提到的精确字符串" .
```

**红黑判定**:
- ✅ 找到 → 记录: 文件名 + 精确行号 + 原文本 + 建议改法 + 改动量
- ❌ 找不到 → **立即停止**,issue 描述过时,master 已修,不要硬上

### 1.4 改后可观察性验证
**这是这次最大的坑**——serde #1663 教训:
- 在 worktree **撤销** fix (`git restore`)，跑 issue 描述的最小 reproducer
- **确认没有 fix 也能复现** → 说明 fix 必要
- **确认有 fix 能修复** → 说明 fix 有效
- 两者都满足才能推

如果撤销 fix 后已不复现 → fix 不可观测,会被 maintainer 关闭,放弃

---

## 2. 改阶段 — 3 个最小化原则

### 2.1 改动范围最小化
- 只改 issue 提到的文件 + 行,**不 reformat 其他**
- 涉及 doc example → **README 和 src/lib.rs (rustdoc) 同步改** (anyhow #409 模式)
- 涉及 derive 宏 → **用 if/else 分支判断**,只给相关路径加 attribute (serde 调研方向,虽然没用上但模式对)

### 2.2 attribute 放置
参考 serde 现有 pattern:
```rust
#[automatically_derived]
#allow_deprecated          // 已有
#[allow(missing_docs)]     // 新加
impl #impl_generics #ident #ty_generics #where_clause {
```

### 2.3 不要触碰的非目标
- ❌ 不要 reformat (rustfmt 会破 PR)
- ❌ 不要"顺手"修其他 lint warning
- ❌ 不要给非目标路径加 attribute (blast radius 过大)

---

## 3. 验证阶段 — 4 步硬性清单 (按顺序跑,任一失败停)

**前提**: 工作目录里只**有** issue 相关改动,**没有**顺手 reformat / 修 lint。

### 3.1 cargo build
```bash
cargo build
```
- 大型 workspace 首次编译 10-20 分钟,给足 timeout
- 失败: 把错误贴回,**不要**试图修复超出 issue 范围的东西

### 3.2 cargo test (含 doc-test)
```bash
cargo test
# 改的是 doc example 时:
cargo test --doc
# 改的是 derive 宏时:
cargo test --workspace
```
- **改的 example / macro 必须编译过** (这是 issue 的核心)
- doc-test 重点 — 改 README/lib.rs rustdoc 时这是核心

### 3.3 cargo fmt
```bash
cargo fmt --all -- --check
```
- 干净 = pass
- 不干净 = **不要** `cargo fmt` 全部 (会改非目标文件),**只 fmt 自己改的文件**:
  ```bash
  cargo fmt -- <path/to/file>
  ```

### 3.4 cargo clippy (最严)
```bash
cargo clippy --all-targets -- -D warnings
# workspace 项目:
cargo clippy --workspace --all-targets -- -D warnings
```
- `-D warnings` 把 warning 升级为 error
- **预存 upstream clippy 问题** (tracing #1357 的坑) 怎么处理:
  - 在 **干净 worktree** (撤销自己改动) 复现一次
  - 确认是自己的改动引入的 → 修
  - 确认是预存 → **停下报告**,不要试图修

### 3.5 验证完成后 — Regression test (重要)

⚠️ **serde 调研的坑**: regression test 加了 `#[test]` 但用 `automod::dir!` 模式,test 函数没匹中,等于没测。

**正确模式**:
```rust
// test_suite/tests/regression/issueNNNN.rs
#![allow(dead_code)]
//! crate doc 必须有,否则 missing_docs 会先报 crate 级错

use ...;

#[test]
fn it_compiles_and_works() {
    // 至少要有 #[test] 函数
}
```

**严格验证**:
- 在 worktree **撤销 fix**, 跑 regression test
- **必须 fail** (否则 test 不严格, 加不加都过)
- 在 worktree **恢复 fix**, 跑 regression test
- **必须 pass**

两边都满足 → test 严格,可推。
只满足后者 → test 是 placebo,**别推 PR**。

---

## 4. push 阶段 — 2 个关键

### 4.1 credential helper 坏掉的坑

这次 anyhow push 撞到 `credential.helper=~/.git-credential-bin/store` 坏配置,**症状**: push 报 authentication failed 但 GH_TOKEN 是好的。

**解决**:
```bash
gh auth setup-git
```
重置后 push 正常。

**预防**: push 前先 `git remote -v` 看 URL 是不是用 token 鉴权,不是的话先 `gh auth setup-git`。

### 4.2 push 超时
参考已有 memory:
- 写通道通的,但默认 `git push` timeout 120s 经常不够
- 用 timeout 10 分钟 (600s),或 background + 监控
- **不要** `git push --dry-run` 测试 (走不同 protocol 反而更慢)

---

## 5. 开 PR 阶段

### 5.1 base 分支确认
- `gh repo view owner/repo --json defaultBranchRef --jq .defaultBranchRef.name` — 必须先确认
- 常见值: `master` (tracing/clap/serde/anyhow), `main` (tokio/cargo/很多现代项目)
- **不要假设**,开 PR 前用上面命令查

### 5.2 PR body 标准模板
```markdown
Closes #NNNN

## Summary
- <1-3 句话,改了哪个文件几行,为什么>

## Test plan
- [x] `cargo build` passes
- [x] `cargo test` passes (including doc-tests)
- [x] `cargo fmt --check` clean
- [x] `cargo clippy --all-targets -- -D warnings` clean
```

### 5.3 不在 PR body 写的内容
- ❌ "happy to help" / "happy to PR" / "I can implement" — 你的角色是"提问题",不是"揽活"
- ❌ "first contribution, please be gentle" — 不要装弱,会被打回
- ❌ emoji / 装饰 — 简洁即可

---

## 6. 红黑名单 (这次 session 教训)

### ❌ 不要做
| 行为 | 后果 |
|------|------|
| 看 issue 标题就选 | tracing 调研错方向,改了 Add→Call 但 issue 讲的是 EnvFilter |
| regression test 不验证撤销 fix 后还 fail | serde 写了 test 但加不加都过,fix 不可观测 |
| 工作目录顺手 reformat | PR 噪音,被 maintainer 反感 |
| 改 doc example 不跑 doc-test | clap #4904 模式必须 verify |
| `git push origin master` | 违反用户 master 保护规则 (memory 已记) |

### ✅ 必做
| 行为 | 理由 |
|------|------|
| 读完整 issue body | 80% 翻车是因为没读 |
| master 复现 (grep 找精确位置) | 确认 issue 仍 relevant |
| 撤销 fix 复现 issue | 确认 fix 必要 |
| 4 步验证全过才 push | 缺一不可,尤其 clippy |
| `gh auth setup-git` 前置 | credential helper 坏掉的坑 |
| 默认分支先查 | master vs main |

---

## 7. AI agent 子 agent 调研报告 — 必亲验, 不可信

**踩坑案例** (2026-08-18): 子 agent 报告"tafia/caldav-rs #61 (110 stars, 9 天前 push, master 复现已确认)" — 整个仓库 **404**, 全部细节是杜撰, 仓库从未存在。

**规则**:
- 子 agent 只跑 `gh` / `git` / `grep` 命令, 把 stdout 给我
- **不要**让子 agent 写"调研报告.md" 综合结论 → 幻觉高发区
- 候选 issue 在我亲自 `gh issue view N --json title,body,state,comments` + `gh repo view owner/repo --json defaultBranchRef` + `git clone --depth 1 https://github.com/owner/repo /tmp/check` + `grep -n "issue 字符串" /tmp/check` 验证前, 不可信
- 凡是子 agent 报告里"master 复现已确认"这种断言, **必自己跑一次 grep 验证**

**亲验过** (这次没翻车的): clap #6488 (亲 clone + grep "build_long_help" 确认), anyhow #457 (亲 grep "underlying error type" 确认)

## 8. crate-ci/committed conventional commits lint (clap/serde 等)

**踩坑案例** (2026-08-18, PR #6489 重提): PR subject "fix(doc): correct example in ArgGroup doc" → lint 报:
- ❌ subject 73 字符 > 50 限制
- ❌ `:` 后首字母小写 (要 `C`orrect, 不是 `c`orrect)

**规则**: 用 `crate-ci/committed` 强制 conventional commits 的 Rust 仓库, PR 标题必满足:
- subject ≤ 50 字符
- `:` 后首字母**大写** (`Fix:` / `Doc:` / `Chore:` 等 scope 后跟大写)
- body wrap 72 字符

**补救**:
```bash
gh pr edit N --title "fix: example in arggroup doc"  # 缩到 ≤ 50 + 大写
```

**Cross-fork PR reopen 陷阱**: amend + force-push 同分支, 试图 reopen closed PR → 常 `422 UNPROCESSABLE` (GitHub 拒绝 reuse closed PR number)。**正确做法**: 同一个 head ref `eastspire:fix/<scope>-<desc>` 直接开新 PR:
```bash
gh pr create --repo owner/repo --base master --head eastspire:fix/<scope>-<desc> --title "..." --body "...Closes #4904"
```
`Closes #4904` 仍生效, 新 PR number 替代旧的。

## 9. 与已有 skill 的关系

- **rust-pr-contribution-workflow**: 找项目 → 选 issue → 提交 PR 的端到端工作流,**流程层**
- **rust-pr-validation-checklist** (本 skill): 提交前必跑的硬性验证 + 调研陷阱清单,**执行层**
- **rust-standards**: Rust 代码规范,**代码层**
- **rust-crate-use**: 第三方 crate 查询 + docs.rs,**依赖层**

加载顺序: rust-pr-contribution-workflow → rust-pr-validation-checklist → (按需) 其他

---

## 10. workspace version bump — root-only 编辑 + CI 同步(euv pattern)

> 2026-08-27 verified on euv PR #25: root-only `Cargo.toml` 编辑即可,流水线自动同步子 crate。

### 10.1 现象

Cargo workspace 项目版本号分布在 7+ 个 `Cargo.toml`(root + 每个 member crate)。如果手动 sed 改每一处:

```bash
sed -i 's/version = "0.14.1"/version = "0.14.2"/g' Cargo.toml cli/Cargo.toml ...
```

**致命陷阱**: 同一 workspace 内第三方 crate 可能恰好在同一版本号(如 euv 的 `qrcode = "0.14.1"` 巧合),sed 会把无关的第三方 crate 也改掉,然后 `cargo check` 报 `failed to select a version for the requirement qrcode = "^0.14.2"`。

### 10.2 正确做法: 只改 root, 流水线补 sub-crate

euv 项目 `.github/workflows/rust.yml` 里有 `sync_workspace_version` job:

1. 读 root `Cargo.toml` 的 `[package] version`
2. sed 改 root 里所有 `[workspace.dependencies] <pkg> = { ..., version = "<old>" }` 为新版本
3. sed 改每个 `<member>/Cargo.toml` 的 `[package] version`
4. 提交一个 `chore: sync all package versions to <new>` follow-up commit 到当前分支
5. 在 `check` job 跑之前完成,所以 `cargo check` 在 CI 里绿

**用户偏好(2026-08-27)**:"只改根目录toml的version,其他不动,流水线会自动同步版本"。

### 10.3 本地 `cargo check` 会失败 — 预期行为

如果 root 已经 0.14.2 但 sub-crate 还是 0.14.1,本地跑:

```bash
cargo check --workspace
#  error: failed to select a version for the requirement `euv-core = "^0.14.2"`
```

这是 cargo 对 path-dep 的版本一致性强制(workspace dependency 的 `version` 必须匹配 path target 的 `package.version`)。**预期会失败**,由 CI 的 `sync_workspace_version` job 在 push 后修复。本地只验证:
- `euv fmt` 不改东西
- `cargo fmt --all` 干净
- `audit_*.py` 0 violations

PR body 要明示:"本地 cargo check 会失败直到 CI sync job 跑完"。

### 10.4 增量 sed 模式(如果要手动 sed sync)

如果 CI 没跑成、需要手动同步,**先**精确限定 sed 到 root 的 `[workspace.dependencies]` 块:

```bash
# 同步 root 的 path-dep entries
sed -i -E "s|^([a-z_-]+ = \{ path = \".+\", version = \")[^\"]+(\".*)|\1NEW_VERSION\2|" Cargo.toml
# 同步 root 的 [package] version
sed -i -E "0,/^(version = \")[^\"]+(\")/s||\1NEW_VERSION\2|" Cargo.toml
# 然后逐个 sub-crate (不能批量)
for m in cli core engine example macros ui; do
  sed -i -E "0,/^(version = \")[^\"]+(\")/s||\1NEW_VERSION\2|" "$m/Cargo.toml"
done
```

**关键**: `qrcode` 这种第三方 line 必须用更严格的 anchor(如 `path = "<dir>"`),或手工 skip。**永远不要**在 root Cargo.toml 上做 `s/version = "OLD"/version = "NEW"/g` 全局替换。
