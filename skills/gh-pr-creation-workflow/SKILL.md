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

## 同步到 hermes 加载器
**改完 ~/.agents/skills/ 一定要同步到 ~/.hermes/skills/**,否则 hermes 读不到新 skill:
```bash
cp -r ~/.agents/skills/<skill-name> ~/.hermes/skills/
chmod +x ~/.hermes/skills/<skill-name>/scripts/*.py 2>/dev/null
```

## PR body 风格
- 中文(用户偏好)
- 不主动 ping reviewer(用户偏好"善后:发完不需要主动 ping")
- 列"改动说明 / 验证 / 注意事项"三段式
- 改动跨多 skill 时,在 body 顶部用 bullet 列出本次涉及的所有 skill

## 易踩的坑
1. **忘清 __pycache__** — 每次 commit 前必须清
2. **忘同步 ~/.hermes/skills/** — 改完 .agents 后必须 cp -r 过去
3. **commit 信息用中文 vs 英文** — commit subject 用英文(符合 git 惯例),body 可中文
4. **PR body 用 heredoc 传** — 用 `cat <<'EOF'` 防止 `$` 字符被 shell 解析
5. **`gh api` vs GraphQL** — `read:org` 缺失时不要用 `gh pr view --json` 复杂查询(部分走 GraphQL),用 `gh api` 单条 REST 更稳
