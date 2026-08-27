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
- **commit message 同样必须纯英文**(subject + body):本 skill 早期版本仅约束 PR body,2026-08-27 用户扩展到 commit message。`rust-standards` §2.7 是该规则的规范化版本,跨 skill 引用
- **不要复述已有内容** — search existing issues first,comment 而不是开新 issue,补充新角度
- **不要主动揽活** — 不写 "happy to help / happy to PR / I can implement" 之类
- 不主动 ping reviewer / maintainer,发完等回复
- 三段式: `## Summary` / `## Verification` / `## Notes`
- 改动跨多 skill 时,Summary 顶部用 bullet 列出本次涉及的所有 skill
- commit subject 英文(符合 git 惯例),body 也英文(本 skill 一致性)
- commit subject 使用 git conventional commits 风格:`<type>(<scope>): <subject>`,type ∈ {feat, fix, refactor, perf, docs, test, build, ci, chore, style}

## 易踩的坑
1. **忘清 __pycache__** — 每次 commit 前必须清
2. **用 cp -r 而不是 symlink** — 历史坑:hermes 端 cp -r 后会跟 .agents 脱钩,改了一处另一边不知道,变成"两份内容各管各的"问题。**永远用 symlink**
3. **PR body 写中文** — 历史坑(本 skill 早期版本错误标记"中文偏好",已修正)。所有 PR/issue/discussion 一律英文
4. **PR body 用 heredoc 传** — 用 `cat <<'EOF'` 防止 `$` 字符被 shell 解析
5. **`gh api` vs GraphQL** — `read:org` 缺失时不要用 `gh pr view --json` 复杂查询(部分走 GraphQL),用 `gh api` 单条 REST 更稳
6. **PR title 跟内容不符** — 多个 commit 推到 head branch 后,gh pr create 不会自动改 title,需要用 `gh pr edit --title ...` 或 REST PATCH
7. **没搜重就开新 PR** — commit 之前先 `gh pr list --search` 看是否已有相关 PR
8. **`Path.exists()` / `is_file()` 在 broken symlink 上返回 False**(2026-08-18 踩雷)— 用它们判定"src 是否健康"会把 broken symlink 当不存在,导致 `if not src.exists()` 走错分支,删除真实目录后建了 self-loop symlink。**改用 `os.lstat` + `os.readlink` 验证** symlink 健康度
9. **`git checkout HEAD -- <path>` 不会覆盖 untracked 的 symlink 替换**(2026-08-18 踩雷)— 工作区如果有个 tracked 目录被替换成 symlink,git 看到工作区是 symlink 就保留,不会恢复。**需要先 `find . -type l -exec rm {} \;` 删 symlink,再 `git checkout HEAD -- <path>`**
10. **skill 库默认偏好"长期 / 通用 / 非单项目"**(2026-08-18 用户明说)— 不要把"单项目踩坑 / 单 bug 记录 / 一次性扩展 / show-and-tell"打包成 skill。单 bug 写 memory 即可,单项目踩坑不值得占库位
11. **`gh pr edit` GraphQL 字段失败会静默退出** — `login` / `name` / `slug` 字段需 `read:org` scope,缺这 scope 时 `gh pr edit` 静默无输出,看起"成功了"实际没改。**改 PR title/body 用 REST**: `curl -X PATCH -H "Authorization: token $GH_TOKEN" -d @payload.json https://api.github.com/repos/<owner>/<repo>/pulls/<n>`,并用 `curl GET` 验证替换结果
12. **临时 skill 筛选标准**(2026-08-18 总结):内容含"自荐 / show and tell"、单一 bug 记录(该写 memory)、单项目一次性踩坑、单工具偶尔用 — 都不该加进 skill 库
13. **已 merged PR 只改 body 不改代码**(2026-08-27 verified euv PR #23): 用户发现 PR body 是中文而 commits 是英文,要求"只是更新pr不改代码"。**正确做法**: `PATCH /repos/<owner>/<repo>/issues/<N` (issue endpoint 是 PR 的兼容别名,因为 PR 也是 issue) — 改 `body` 字段不需要 reopen,不需要 force-push,**不会触发 CI**。Python 模板:
    ```python
    import urllib.request, json, os
    with open('/tmp/pr-body.md') as fh: body = fh.read()
    req = urllib.request.Request(
        f'https://api.github.com/repos/{owner}/{repo}/issues/{n}',
        method='PATCH',
        data=json.dumps({'body': body}).encode('utf-8'),
        headers={'Authorization': 'Bearer ' + os.environ['GH_TOKEN'],
                 'Accept': 'application/vnd.github+json',
                 'User-Agent': 'hermes-cli',
                 'Content-Type': 'application/json'},
    )
    urllib.request.urlopen(req)
    ```
    验证后立刻 `GET /pulls/<N` 读 `body` 字段确认替换生效(`gh pr view --json body` 因 GraphQL scope 缺失可能返空,优先用 REST)。同样适用于 title 修改。**禁止**为改文案 reopen PR + force-push — 这会触发新的 CI run,引入额外 commit 历史噪音。
