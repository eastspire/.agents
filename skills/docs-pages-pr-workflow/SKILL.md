---
name: docs-pages-pr-workflow
description: 在 docs-pages/docs 仓库上做内容/导航修改并开 PR 的端到端流程（VuePress 2 + GitHub API + PAT）
---

# docs-pages/docs 仓库 PR 流程

## 仓库结构
- 源仓库：`https://github.com/docs-pages/docs`，本地路径 `/workspace/orgs/docs-pages/`
- 文档源：`src/`（不是 `docs/src/`，也别被 `pages/` 混淆——`pages/` 是 huge 的 build output，已被 `.gitignore`）
- 导航配置：`src/.vuepress/navbar.ts`（TypeScript）
- 配置文件：`src/.vuepress/config.ts`
- 主分支：`master`

## 环境
- GitHub PAT 存于 `~/.bashrc` 和 `~/.profile` 的 `GH_TOKEN` / `GITHUB_TOKEN`，文件权限 600
- `gh` CLI 不一定可用，但 `curl + GH_TOKEN` 调 GitHub REST API 稳定
- 提交身份：`user.name=eastspire, user.email=root@ltpp.vip`
- `execute_code` 子进程的 bash env 不会自动 source `~/.bashrc`，用 `curl` 时必须显式 `source ~/.bashrc` 或直接读 token

## Git 操作
- 沙盒里先 `cd /workspace` 再操作（不要用相对路径，否则 shell 会卡在已删除目录）
- clone 大仓库用 background + 长 timeout，或先 `mkdir .git/ && git init && git remote add origin` 然后 `git fetch` 拉单分支
- 不需要 history 的话 `git clone --depth 1 --filter=blob:none` 最快

## 开 PR（无 gh CLI 时）
```bash
curl -X POST https://api.github.com/repos/{owner}/{repo}/pulls \
  -H "Authorization: token $GH_TOKEN" \
  -H "Accept: application/vnd.github+json" \
  -d '{"title":"...","head":"branch","base":"master","body":"..."}'
```

## 修改完后要核对的点
1. `src/**/*.md` 全量 grep 失效引用（`./LICENSE`、`/LTPP-.../` 等大小写敏感）
2. 改动后 git status 确认 working tree 干净
3. PR force-push 后 head SHA 变了，要重新核对 PR 的 `head.sha` 字段

## 常见坑
- README 的 `LICENSE` 引用应当用 `git mv license.md LICENSE` 解决，**不要**删链接包装（参考"教训"）
- VuePress 是 Linux 部署，文件名大小写敏感；`LICENSE` 和 `license` 视为不同文件
- `/users/{user}/repos` 包含协作仓库，要严格 ownership 用 `affiliation=owner`

## ⚠️ fontawesome icon 必坑（最常见失误）
`src/.vuepress/theme.ts` 里配置的是：
```ts
icon: {
  assets: `${base_path}js/fontawesome.all.min.js`,
  type: 'fontawesome',
},
```
这意味着 navbar/sidebar 等所有 `icon: '...'` 字段必须用**完整 fontawesome 类名**：
- ❌ `icon: 'github'`（加载失败 — 裸名 fontawesome 找不到）
- ❌ `icon: 'laptop-code'`（同上）
- ✅ `icon: 'fa-brands fa-github'`（GitHub 类用 `fa-brands`）
- ✅ `icon: 'fa-solid fa-laptop-code'`（通用类用 `fa-solid`）
- ✅ `icon: 'fa-solid fa-qrcode'`

字体文件 `webfonts/fa-brands-400.woff2` 等 build 时自动生成到产物里。改完后用 grep 验证：
```bash
grep -r "icon: 'github'" pages/   # 应该 0 匹配
grep -r "fa-brands fa-github" pages/  # 应该 ≥ 1 匹配
```

## yarn 4 + Node 环境
- 项目要求 `packageManager: yarn@4.10.3`，Node `engines: ">=22.0.0"`
- 沙盒里 yarn 4 不预装，需手动启用 corepack：
  ```bash
  npm install -g corepack
  chmod +x /opt/node/lib/node_modules/corepack/dist/corepack.js
  /opt/node/lib/node_modules/corepack/dist/corepack.js enable yarn
  # 或：
  export PATH="/opt/node/lib/node_modules/corepack/dist:$PATH"
  corepack enable yarn
  ```
- Node 20.18.0 实测可正常 build（engines 22 声明 over-restrictive）
- `yarn install` ~1.5 min（546 包，235.8 MiB）
- `yarn build` ~2 min（典型 197 页）

## 反向 sync：把 docs-pages 内容推送到下游 consumers（如 skills `references/`）

当一个外部项目（典型是 skills 仓库的 `skills/<name>/references/`）需要镜像 docs-pages 里的部分 markdown 时，**不要用 ad-hoc `cp`**。用一个可复现的 pipeline：

### 必备三件套
1. **`scripts/sync-references.mapping`** — TSV 格式，每行 `<dest_path>\t<source_path> [note]`，例：
   ```
   skills/euv/references/animation.md	src/euv/engine/animation.md
   skills/hyperlane/references/route.md	src/hyperlane/usage-introduction/route.md	# manual override
   ```
2. **`scripts/sync-references.sh`** — clone 源仓库（`--depth 1 --filter=blob:none`）→ 走 mapping → 对每个文件 strip VuePress-only frontmatter + 加 `synced_from` / `sync_method` / `sync_date` 元数据 + 写 manual-edit warning HTML comment
3. **`scripts/verify-references.sh`** — `git diff --stat HEAD` 报告 changed/orphaned/untracked/drift

### Frontmatter 改写规则
- **保留**：`title`、`category`、`tags`、`description`
- **剥离**（VuePress-only，对下游无意义）：`head`、`icon`、`order`、`dataset`、`index`、`keywords`、`sidebarDepth`、`prev`、`next`
- **注入**：
  ```yaml
  ---
  title: <from source>
  category: <from source>
  tags: <from source>
  description: <from source>
  synced_from: https://github.com/docs-pages/docs/blob/master/<source_path>
  sync_method: scripts/sync-references.sh
  sync_date: 2026-08-15
  ---
  ```
  + 正文顶部 `<!-- DO NOT EDIT: auto-synced from docs-pages. To update, run scripts/sync-references.sh -->\n`

### Manual override 模式
有些文件需要人工注解（如 `euv/async.md` 里有手写的"原始 API 链接"列表，source 里没有）。在 mapping 同一行末加 `# manual override` 注释，**脚本必须跳过这些行**并在输出里 warn 让 maintainer 知道有 dest 没覆盖。Verify 脚本也要把这些排除在 drift 报告外（它们**应该**有 diff，那是 expected drift）。

### 参数
```bash
bash scripts/sync-references.sh                  # 真实跑：clone source → 改写
bash scripts/sync-references.sh --dry-run       # 只列 mapping 解析 + source 存在性
bash scripts/sync-references.sh --source-dir /path/to/local/clone  # 不 clone，直接用本地
bash scripts/sync-references.sh --force         # 覆盖 manual override 行
bash scripts/verify-references.sh               # diff 验证
```

### Force-push 后必做
1. `git push --force-with-lease`（比 `--force` 安全，会拒绝远端有未拉取改动的情况）
2. 用 curl 重新读 PR，确认 `head.sha == 本地 HEAD`，**不要相信 PR UI 里的 sha**
3. 更新 PR body 用 `curl PATCH /repos/{owner}/{repo}/pulls/{n}`，body 用 `--data-binary @file.json`（curl 默认会做 URL-encoding 但 JSON body 里的换行有时会出错，更稳的是 `python3 -c "import urllib.request,json,os; req=urllib.request.Request(...); req.data=json.dumps(json.load(open('body.json'))).encode(); ..."`）

## Commit 卫生
**`yarn install` 会重排 `package.json` 字段顺序**作为副作用，**不要**让它污染功能修复 commit：
```bash
git status
# 如果看到 package.json 改动了（只有字段顺序变化），revert 它：
git checkout HEAD -- package.json
# 然后只 add 想改的文件
git add <specific files>   # 不要 git add .
```

`src/.vuepress/sidebar.js` 在 build 时会被 `creat-sidebar.js` 插件**自动清理**（删除 src 下不存在的目录条目），这属于正常 build 副作用，**可以提交**，但要知道来源。

## 完整修改→验证→PR 流程
1. `cd /workspace/orgs/docs-pages && git status` 确认干净
2. `git checkout -b chore/<descriptive-name>`
3. 改 `src/.vuepress/navbar.ts`（注意 fontawesome icon 类名）
4. `yarn install`（首次或 package.json 改过才需要）
5. `yarn build` 验证（不要 `| tail -60` 截断，看到 `✔ Compiling with vite` 后还可能继续跑 vite 编译 ~2 min）
6. grep 验证产物：
   - 旧跳链完全清掉（例：`grep -r "ltppx.cn" pages/`）
   - 新 fontawesome icon 已写入（`grep -r "fa-brands fa-github" pages/`）
7. **commit 前清理**：`git checkout HEAD -- package.json`（如果改了）
8. `git add <specific> && git commit && git push -u origin chore/<name>`
9. 用 `gh pr create` 或 curl GitHub API 开 PR

## 修改完后要核对的点
1. `src/**/*.md` 全量 grep 失效引用（`./LICENSE`、`/LTPP-.../` 等大小写敏感）
2. 改动后 git status 确认 working tree 干净
3. PR force-push 后 head SHA 变了，要重新核对 PR 的 `head.sha` 字段
4. **fontawesome icon 用完整类名**（最常踩的坑）
5. **yarn install 副作用别污染 commit**
