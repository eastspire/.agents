---
name: github-fork-issue-pr-workflow
description: End-to-end workflow for picking up a good first issue / help wanted on a large open-source repo (dify, euv, hyperlane, etc.), making a minimal correct fix, and opening a PR from your fork back to upstream. Use when the user says "fork X project, work on a simple issue, then open a PR".
---

# Fork + Good First Issue + PR Workflow

适用场景:用户要求 "fork 某项目 → 找简单 issue → 写代码 → 提 PR"。

## 1. 检查 fork 是否已存在

```bash
gh repo view <user>/<repo> 2>/dev/null && echo "fork exists" || echo "need to fork"
```

如果已存在,直接走第 2 步;否则:

```bash
gh repo fork <upstream>/<repo> --clone=false --remote
```

⚠️ 不要 `--clone`(默认会全量 clone 大仓库)。

## 2. 大仓库 sparse + shallow clone (避免 500MB 灾难)

以 dify 492MB 为例:

```bash
git clone --depth=1 git@github.com:<user>/<repo>.git ~/projects/<repo>
cd ~/projects/<repo>
git sparse-checkout init --cone
git sparse-checkout set \
  api/* web/* docker/* dev/* \
  AGENTS.md CONTRIBUTING.md README.md LICENSE Makefile
# Python 项目: 加 tests/*; Rust: src/* Cargo.toml
git read-tree -mu HEAD
```

`--depth=1` 跳过历史; cone 模式用 `/*` 通配根目录; 一级子目录需显式列出。

## 3. 找 good first issue + 排查重复 PR

```bash
gh issue list --repo <upstream>/<repo> \
  --label "good first issue,help wanted" \
  --state open --limit 20 --json number,title,labels,comments,createdAt
```

对每个候选 issue:
- 看 comments 数量 (>10 通常是大型讨论,避开)
- 看 createdAt (>6 个月未动,可能已 stale 或难)
- **关键**: 搜上游已存在的 PR `gh pr list --search "issue:NNN"` 排除已被接的
- 关注"系列 PR"线索:issue 里 mention "example: #NNN" → 找那个 PR 看模式

## 4. 选定 issue 后的尽职调查

**先看 AGENTS.md / CONTRIBUTING.md** — 项目有规范,严格遵守 (例: dify 的 `api/AGENTS.md` 规定 `make lint / type-check / test`,migration 必须配套 model 变更)。

**找先例**:
```bash
ls migrations/versions/ | grep -i "<关键词>"  # dify 用 alembic
gh pr list --search "keyword in:<repo>"
```

**扫代码库找范围**:
- 用 ripgrep 找问题模式,统计数量
- AST 解析 (Python 用 `ast`) 比 regex 更可靠
- 注意 `ast.Assign` vs `ast.AnnAssign` — annotated assignment 经常漏掉

## 5. 写代码前的等价性检查

涉及"删除某属性"这种 refactor,**必须证明行为不变**:
- 删 `server_default=X` 前,确认已有等价的 `default=X` 在 application 层
- 删 enum 字符串前,确认 `EnumMember.value == 'string_literal'`
- 写脚本逐 case 验证,**不能只靠 grep**

## 6. 切分支 + 改 + 迁移 (适用 Python/SQLAlchemy + alembic)

遵循项目规范 (例: dify):
- 创建 `chore/<scope>-<desc>` 或 `fix/<scope>-<desc>` 分支,**绝不直接动 main**
- 改 model 文件
- 配套 alembic migration: `down_revision` 必须是当前 head
- 用 `alembic heads` 拿 head,**注意 tuple 格式的 down_revision** (`('rev1', 'rev2')`)

## 7. 验证 (lint / type-check / test)

按 AGENTS.md:
```bash
make lint
make type-check
make test TARGET_TESTS=./api/tests/test_models/
```

## 8. Push + 开 PR

```bash
git push -u origin <branch>
gh pr create --base main --head <branch> --repo <upstream>/<repo> \
  --title "chore(scope): short description" \
  --body "Fixes #NNN. ..."
```

PR body 模板:
- 一句话说明改了什么
- 列出改动文件 + 行为等价性论证
- 引用先例 PR (如果有) 表明模式一致
- 引用上游 AGENTS.md 规范 (表明遵循)
- ⚠️ 不用写 "happy to PR / I can implement" — 用户风格偏好是只发 issue,不当揽活

## 常见坑

1. **AST 漏 AnnAssign** — `Mapped[bool] = mapped_column(...)` 是 `ast.AnnAssign`,不是 `ast.Assign`
2. **alembic down_revision tuple** — merge 节点用 `('a', 'b')` 格式,正则容易漏
3. **enum vs string** — `EnumMember` 在 DB 层是字符串,但 SQLAlchemy `default=Enum.X` 自动 cast,删 `server_default='x'` 前必须验证 value 字段
4. **sparse-checkout cone `/*` 只匹配根目录** — 子目录 `api/*` 不会自动包含,需显式列出
5. **`gh` 子进程不继承 GH_TOKEN env** — 从 `~/.bashrc` 读 token 后用 curl 直连
6. **大仓库 `git push` 超时** — 用 `--quiet` + 长 timeout (10min),或 background 监控

## 参考

- dify 案例: Issue #29314 → dataset.py 12 列 + alembic migration,基于 `56124e050600` head
- 先例: PR #39886 (HandSonic) 改 2 文件 11 列,模式相同
- 先例 migration: `2026_02_09_0950-c3df22613c99_drop_server_default_for_app_trail_.py`
