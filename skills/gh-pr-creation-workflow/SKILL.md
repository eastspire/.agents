---
name: gh-pr-creation-workflow
description: 用 gh CLI(已装 2.97.0)在 eastspire/.agents 仓库上 commit / push / 创建 PR 的端到端流程。当需要给 ~/.agents/skills/ 改动开 PR 时使用。
---

# gh CLI 创建 PR 工作流

## 适用场景
- 给 `eastspire/.agents`(用户个人 skill 仓库)开 PR
- 改动通常在 `~/.agents/skills/<skill-name>/` 下,涉及拆分/重组/新增/删除 SKILL.md / references / templates / scripts

## 关键前置
- gh 2.97.0 已装(见 memory)
- `GH_TOKEN` 环境变量已配,scope `repo` 够用,**缺 `read:org`**,GraphQL 会失败 → 用 `gh api` (REST)
- **禁改组织**:`hyperlane-dev`、`euv-dev`、`crates-dev` — 这三个组织下的项目任何写操作都禁止(包括 eastspire 个人仓库里若是 fork 也要小心)

## 标准流程

### 1. 检查改动 + 状态
```bash
cd ~/.agents/skills
git status
git log --oneline -5   # 看最近 commit
git branch --show-current
```

### 2. 清理 Python 缓存(每次都要)
```bash
# 先清再 add,避免 .pyc / __pycache__/ 进 commit
find . -name __pycache__ -type d -exec rm -rf {} + 2>/dev/null
find . -name "*.pyc" -delete
# 确认 .gitignore 里有:
#   __pycache__/
#   *.pyc
```

### 3. Commit
```bash
git add -A
git commit -m "<type>(<scope>): <subject>

<body 中文,列出本次改动要点>"
# 常用 type: refactor / feat / chore / fix / docs
```

### 4. Push
```bash
git push -u origin <branch>
# 若是新分支,gh 会提示创建 PR URL,但别用浏览器,直接走 gh CLI
```

### 5. 创建 PR(用 gh,不用 urllib)
```bash
gh pr create \
  --title "<type>(<scope>): <subject>" \
  --body "$(cat <<'EOF'
## 改动说明
<中文描述,列出关键变更>

## 验证
<列出本次验证步骤,例如:行数检查 / frontmatter 解析 / 脚本可执行>

## 注意事项
<如有遗留事项或设计权衡,在这里说明>
EOF
)" \
  --base master \
  --head <branch>
```

### 6. 确认 PR
```bash
gh pr view <num> --json url,state,title,files
gh pr diff <num> --stat
```

## 同步到 hermes 加载器(用 symlink,**不要 cp -r**)
改完 `~/.agents/skills/<skill>/` 必须让 hermes 也能读到,否则下次 session 的 skill 加载器看不到改动。

**正确做法:用 symlink 指向 .agents/skills,而不是 cp -r 复制**。`.agents` 是 single source of truth,hermes 端是视图,自动跟随更新,避免双份内容脱钩:
```bash
# 1) 如果 ~/.hermes/skills/<skill>/ 已经是真实目录(历史 cp -r 留下)
#    删除它,建 symlink
SKILL=<skill-name>
if [ -d ~/.hermes/skills/$SKILL ] && [ ! -L ~/.hermes/skills/$SKILL ]; then
  rm -rf ~/.hermes/skills/$SKILL
fi
ln -sfn ~/.agents/skills/$SKILL ~/.hermes/skills/$SKILL

# 2) 验证
test -f ~/.hermes/skills/$SKILL/SKILL.md && echo "✅ symlink resolved"
```

**hermes-specific 例外**(以下两类保留为真实目录,不进 .agents):
- 依赖 Hermes 平台 API 的:`hermes-cronjob-daily-news-html`(用 cronjob 调度)、`openclaw-migration`(Hermes Agent 工具)
- 这两类不写进本 skill 库,在 hermes 端独立维护

## PR body 风格
- **英文**(用户铁律:所有 GitHub 公开仓库的 issue/PR/discussion 礼貌、英文、有内容,见 memory)
- **不要复述已有内容** — search existing issues first,comment 而不是开新 issue,补充新角度
- **不要主动揽活** — 不写 "happy to help / happy to PR / I can implement" 之类
- 不主动 ping reviewer / maintainer,发完等回复
- 三段式: `## Summary` / `## Verification` / `## Notes`
- 改动跨多 skill 时,Summary 顶部用 bullet 列出本次涉及的所有 skill
- commit subject 英文(符合 git 惯例),body 也英文(本 skill 一致性)

## 易踩的坑
1. **忘清 __pycache__** — 每次 commit 前必须清
2. **用 cp -r 而不是 symlink** — 历史坑:hermes 端 cp -r 后会跟 .agents 脱钩,改了一处另一边不知道,变成"两份内容各管各的"问题。**永远用 symlink**
3. **PR body 写中文** — 历史坑(本 skill 早期版本错误标记"中文偏好",已修正)。所有 PR/issue/discussion 一律英文
4. **PR body 用 heredoc 传** — 用 `cat <<'EOF'` 防止 `$` 字符被 shell 解析
5. **`gh api` vs GraphQL** — `read:org` 缺失时不要用 `gh pr view --json` 复杂查询(部分走 GraphQL),用 `gh api` 单条 REST 更稳
6. **PR title 跟内容不符** — 多个 commit 推到 head branch 后,gh pr create 不会自动改 title,需要用 `gh pr edit --title ...` 或 REST PATCH
7. **没搜重就开新 PR** — commit 之前先 `gh pr list --search` 看是否已有相关 PR
