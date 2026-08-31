---
name: rust-wasm-gh-pages-deploy-pitfalls
description: 'Rust + euv → 发布/部署踩坑记录,涵盖 WASM/GitHub Pages 部署 (import path / CDN 缓存 / master ref 损坏) + crates.io cargo publish (workspace dev-dep chicken-and-egg / 版本号静默失败 / pre-flight dep resolver) + 移动端浏览器 safe-area 与 navbar 间距 (env() vs CSS var 的脱钩、navbar background 同 page 背景导致的安全区视觉不可见、use_safe_area_fix hook 的缓存语义) + **跨 repo deploy chain (euv master merge 不会自动触发 euv-docs deploy,需手动 workflow_dispatch + ltpp.vip sync-pages.sh;下游 repo 加 pages.yml 实现自动链;Pages env policy 必须显式 PUT branch)** + **patch version bump 只改 root Cargo.toml 的 1 个字段,CI sync_workspace_version 自动同步 7 个 member**(不要手工改 7 处) + **分支 base 错误导致 PR diff 混入未合 commit**(必须从干净 master 起)。同一仓库任意 Rust 发布链路触发本 skill。'
---

# Rust → WASM + GitHub Pages 部署踩坑记录

## 核心教训:先验证 import path,再做任何复杂操作

### 坑 1:`wasm-pack`/`euv` 生成文件名带下划线还是连字符?
- `wasm-pack build` 默认 `--out-name` = crate 名(`-` 转 `_`)。crate `pixel-quest` → `pkg/pixel_quest.js`(**下划线**)。
- `index.html` 手写 `<script src="pkg/pixel-quest.js">` 永远 404。
- 必须先 `ls www/pkg/` 看实际文件名,再让 `index.html` 引用。
- 验证: `curl -sL https://<user>.github.io/<repo>/index.html | grep "import init"` 必须看到下划线路径。

### 坑 2:`patch` 工具可能因为 old_string == new_string 静默失败
- 改完文件以为生效,实际没改,后续部署一直在跑旧代码。
- 验证: `grep` 确认旧串消失,或 `git diff` 看 diff。

### 坑 3:GitHub Pages 边缘缓存 + 错误 import path = 灾难
- 即使后来 fix 了 path 并 push 成功,CDN 还可能缓存旧 HTML 10+ 分钟。
- 调试: `curl -sL https://<user>.github.io/<repo>/index.html | grep import` 必须看到正确路径。

### 坑 4:euv-engine 的 RAF 闭包要"自递归",不能调外部方法
- `request_animation_frame(g.borrow().update_frame())` 不工作,borrow 后没法再 borrow。
- 用 `Rc<RefCell<...>>` 包装,闭包内克隆 Rc 再 borrow_mut。
- 验证: 暴露 `get_frame_count()` 给 JS,headless 浏览器里调用看是否递增。

### 坑 5:GitHub master ref 一旦被损坏,git push 永久卡死
- 触发: 大文件 force push + pack-objects 校验失败 + 留下不完整 object。
- 症状: `remote unpack failed: did not receive expected object <sha>`。
- 严重程度: **可恢复**,**用一次 force-push 回滚到坏 commit 之前**通常就解了 — 别上来就走 API。
- 真正的解法: `git push -f origin <last_good_commit>`。新 pack 的可达图不引用死对象,pack-objects 不会再触发校验。
- **错误的第一反应**: 走 Contents API 单文件 PUT/重建 tree。浪费 token,且 CDN 缓存旧版 10-30 分钟。force-push 反而是最快路径。
- 预防:
  1. **CI/CD 必须在 day 1 设置好**(`actions/deploy-pages@v4`),不要手动 `git push -f` 大文件。
  2. 部署只走 `gh-pages`,master 只存源码。
  3. 大文件(WASM)用 `git-lfs` 或 actions artifact。
- 万一 force-push 也卡:
  1. `actions/deploy-pages@v4` 不依赖 git push,只走 HTTP API → **可绕过**。
  2. 临时: 用 Contents API 单文件 PUT/DELETE(无法改 git 历史)。
  3. 终极: 删 repo 重建,或联系 GitHub Support 让他们 `git gc`。

### 坑 6:Contents API 单文件 PUT 无法用于 base_tree diff
- `POST /git/trees` 带 `base_tree` 会让服务端计算 diff,base_tree 在坏区会返回 `GitRPC::BadObjectState`。
- 解决: 不传 `base_tree`,只传 `tree: [...]` 完整列表。
- 限制: 单次最多 ~100k 条目。

## 推荐 CI/CD 模板

```yaml
name: Build & Deploy
on: { push: { branches: [master] } }
permissions:
  contents: read
  pages: write
  id-token: write
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: dtolnay/rust-toolchain@stable
        with: { targets: wasm32-unknown-unknown }
      - uses: Swatinem/rust-cache@v2
      - run: cargo install euv-cli --version 0.1.0
      - run: euv build --release
      - uses: actions/upload-pages-artifact@v3
        with: { path: www }
  deploy:
    needs: build
    runs-on: ubuntu-latest
    environment: { name: github-pages, url: ${{ steps.deployment.outputs.page_url }} }
    steps:
      - id: deployment
        uses: actions/deploy-pages@v4
```

**关键**:`actions/deploy-pages@v4` 走 GitHub 官方 API,**不依赖 git push**,即使 master ref 损坏也能部署。

## 端到端验证清单

1. `curl -sL https://<user>.github.io/<repo>/index.html | grep "import init"` — 正确 pkg 路径
2. `curl -IL https://<user>.github.io/<repo>/pkg/pixel_quest.js` — 200
3. Playwright headless + 移动 UA + touch,`wasm_bindgen.get_frame_count()` 1.5s 内递增
4. 多次 `getImageData(canvas, region)` 对比,看 canvas 变化
5. 触发 d-pad touch,player 区域像素变化
6. 等 20s 看 game over UI

## 用户铁律: 业务项目禁止修改依赖源码

**适用范围**: 用户交给我的任何项目,包括 monorepo 里的子项目。

具体含义:
1. **不要修改上游依赖**(`euv`、`euv-engine`、任何 `Cargo.toml` 里列的 crate)的源码 — 即使发现 bug,也只能提 issue 或加 patch crate,不能直接改 vendor 代码。
2. **业务项目** = 用户的目标项目。当它与依赖是同源目录结构时(如某 monorepo 把游戏作为子目录),我必须先 `git remote -v` 和 `git log --all` 确认仓库边界,再决定动哪个。
3. **修改前必须先确认**: 这个文件属于业务项目还是框架?如果拿不准,先列出 `git log --all -- <file>` 看 commit author 是不是用户自己。
4. 任何"改一下框架就能跑通"的诱惑,默认拒绝 — 正确做法是在业务项目侧绕过(用 raw API、加 wrapper、加 feature flag)。
5. **删除操作前更严格**: `rm -rf` 之前必须双重确认仓库边界(both remote 和 commit author)。混血仓库(一个 git 目录有多个 remote)是红旗。

此规则优先级高于任何技术便利性。

## Monorepo 子项目误判教训

- 我曾把 `/workspace/orgs/euv-dev/euv/` 当作"独立 euv 框架 repo",而 `pixel-quest/` 是它的子目录(由用户后续添加的 commit 引入)。`rm -rf pixel-quest/` 时,`git status` 显示 5181 行 deletions,误以为只是"删除我加的子目录",但其实把用户整个已部署的 game 项目源代码都删了。
- 铁律: 任何 git 操作(rm、reset、push)前,先做以下确认:
  1. `git remote -v` — 看当前目录属于哪个 remote
  2. `git log --all --oneline -- <path>` — 看这个路径的历史是谁引入的
  3. `git status --porcelain` 配合 `git diff --stat` 验证 — 不要被行数吓到
  4. 如果在 monorepo 下,先列出根目录所有子目录,确认我操作的范围
- 特别: `git diff --stat` 看到 5xxx 行 deletions 时,要警觉 — 可能没意识到这个目录的全部历史。

## CDN 缓存陷阱(已踩)

- GitHub Pages 边缘缓存 `cache-control: max-age=600`,`x-cache: HIT`。
- force-push 成功后,`curl` 旧 URL 仍返回旧内容几分钟到几十分钟。
- `raw.githubusercontent.com` 同步稍快但也非实时。
- 如果客户端报错但 API 确认 sha 已更新,等 10-30 分钟再验证,别急着再次 force-push。

## `actions/deploy-pages@v4` vs `peaceiris/actions-gh-pages`

- `actions/deploy-pages@v4` 走 GitHub 官方 Pages API,**不依赖 git push**。即使 master ref 损坏也能部署。**首选**。
- `peaceiris/actions-gh-pages` 内部用 `git push` → 同样会卡在坏 object。**避免**。

## `cargo publish` 鸡生蛋鸡生蛋 + CI 静默吞失败

发布 euv / hyperlane / 任何 Cargo workspace 时,如果 `publish` step 看起来都 success 了,**直接去 `https://crates.io/api/v1/crates/<crate>` 查 `max_stable_version`**。workflow 的 retry+continue loop 会把 per-package publish 失败转 `continue`,run exit code = 0,但 crates.io 上的版本号是落后 git tag 的。

详细踩坑记录(circular workspace dev-dep、path-only 修复、TOML 不加注释、facade vs 底层 crate 选择)→ `rust-standards/references/13-dependency.md` §13.4–13.6。本 skill 只在 "发布链路失败但 CI 绿" 这条上下文下指向那条规范。

验证清单(命中 "发包失败" 时):

```bash
TOKEN=$(grep -oP 'export GH_TOKEN="\K[^"]+' /root/.bashrc.d/gh_token.sh)
for crate in euv euv-macros euv-ui euv-cli euv-core euv-engine; do
  curl -s -H "Authorization: Bearer $TOKEN" \
    "https://crates.io/api/v1/crates/$crate" \
    | python3 -c "import json,sys; d=json.load(sys.stdin); print(f'$crate = {d[\"crate\"][\"max_stable_version\"]}')"
done
```

任何一项落后 git tag → 走 §13.4–13.6 排查(鸡生蛋 / 路径 / 伞 vs 底层 / TOML 注释)。

## 同仓库多 PR 触发 publish 时的常见 sequence

- 每个 PR merge → GitHub Actions 触发 `publish` step
- 每个 PR 都可能改 crates.io
- 检查顺序:`git log --first-parent` 看 merge 顺序 → 对照 crates.io 查实际发布顺序 → 找出哪次 merge 后**没**真正 publish
- 关键 PR(`fix(macros)` 类)即使 CI 绿,实际可能根本没影响 crates.io —— 这是 `cargo publish` 静默失败的常见伪装

## 移动端 safe-area 与 navbar 间距:四轮迭代才修对

移动端部署后用户报告"navbar 距离浏览器顶部还有很大空白"——这条踩坑链需要单独存档,
因为它跨越了 WASM 部署 + CSS safe-area + 视觉感知误判三个独立子领域。
完整调试链、最终表达式、Playwright 复现脚本见:

→ `references/mobile-safe-area-navbar.md`

核心教训:**navbar 容器 `y=0` ≠ navbar *可见内容* `y=0`**;headless 测出来完美 ≠ 用户
看到完美,因为:
1. euv `use_safe_area_fix` hook 把 env() 值缓存后写 inline style,headless 测到的是缓存值
2. navbar `background = var(--background)` 同 page 背景同色,safe-area padding 区域视觉
   上和空白页无法区分
3. 沉浸式模式下 status bar / URL bar 仍然在 viewport 里,navbar 顶部被它们覆盖
4. Playwright init_script 改 :root --safe-area-inset-top 不会生效,因为 hook 在 wasm
   启动后会**覆盖**这个值;正确做法是 wasm init 完成后,inline-set 到
   `.c_mobile_app_root` 上

### 坑 7:euv-ui `*` 浮动 pin 导致 silent CSS 回归(2026-08-30 euv-docs PR #13)

**症状**:站点 CSS 突然出现 `c_mobile_header` 缺 `var(--euv-mobile-safe-top, 0px)` 模式,
navbar 顶部大片透明空白;但 git diff 没动 euv-ui 源码、Cargo.lock 也没改(因为
euv-docs 的 `/target`、`/www`、`Cargo.lock` 都在 .gitignore)。

**根因**:`Cargo.toml` 用 `euv-ui = "*"`(或 `euv = "*"`),CI 在两个相邻 build 之间
crates.io 上 0.18.x 系列从无到有的瞬间,旧 build 解析到 `0.17.x`、新 build 解析到
`0.18.x`,**而 0.17.x 的 `c_mobile_header` 没有 safe-area CSS var 契约**(0.18.12 起
才引入 `var(--euv-mobile-safe-top, 0px)` 模式,见 euv-ui-standards §2.3)。CI 跑通、
deploy 成功、Cargo.lock 在 .gitignore 里被忽略 → 看不到任何变化。

**预防**:
1. **永远 pin major**(`euv-ui = "0.18"` 而非 `*`)。euv example workspace 自己就
   是 major pin(workspace 写在 0.18.15),跟随它。
2. PR 描述里写一句为什么不能 `*`,留 trace 给 reviewer。
3. **不要 pin 完整版本**(`=0.18.15`)——会跟 euv 框架本身的版本升级脱钩,需要手动
   bump。major pin 是甜区。
4. 如果项目里同时有 `euv = "*"` 和 `euv-ui = "*"` 都要 pin,且 pin 一致(`euv =
   "0.18"` + `euv-ui = "0.18"`)。euv 0.18.x 内部依赖 `euv-core 0.18.x` + `euv-macros
   0.18.x`,但**不依赖 euv-ui**——euv-ui 是用户自己加的。
5. 升级 euv-ui major 前,先在本地 `cargo update -p euv-ui && euv build --release`
   跑一遍,对比 emitted CSS 字节(`mobile-web-debugging/scripts/css-byte-diff.py`
   对 euv example vs 本地 build)确认 `c_mobile_*` 仍含 safe-area 模式。

**诊断**:`strings pkg/<crate>_bg.wasm | grep euv-ui-` 看实际编译进去的版本号。
0.17.x → 没 safe-area;0.18.12+ → 有。**不要相信 Cargo.lock 里写版本号**——它可能
是上次 `cargo update` 留下的,不是当前 build 用的。

### 坑 8:本地验证 mobile CSS 修复(headless env=0 困局)

headless Chrome 永远 `env(safe-area-inset-*) === 0px`,所以 safe-area 类修复在
merge 前无法靠像素验证。**唯一可靠路径**:把目标站点和已知正确的参考站点
(euv example、其他项目)用 Playwright 加载,遍历 `document.styleSheets` 收集
emitted CSS rules,逐 class 比对字节级一致——因为 CSS 字符串一致 ⇒ runtime 行为
一致,无论 env() 是 0 还是 41px。

可执行脚本和模式见 `mobile-web-debugging` skill §4 字节级 CSS 对比 + `scripts/css-byte-diff.py`。
**把这条验证纳入 PR 提交清单**:任何改 euv-ui safe-area CSS / `c_mobile_*` /
`c_app_*` class 的 PR,提交前必须跑 css-byte-diff 对比 euv example 和本地 build,
identical=true 才能提。

### 坑 9:euv master merge 不会自动触发 euv-docs 部署(跨 repo deploy chain)

**症状**: euv 框架 PR merge 完成后,euv-docs 站点的 wasm bundle 还是旧版本(用户
访问 `ltpp.vip/euv-docs/` 看不到新行为)。`rust.yml` 全绿、`pages.yml` 部署完成、
但 docs 站没动。

**根因**: euv 和 euv-docs 是**两个独立 GitHub repo**,euv 的 `pages.yml` workflow_run
trigger 只 listen `workflows: [Rust]`(同一 repo 的 CI),不会跨 repo 通知 euv-docs。
euv-docs 的 `deploy.yml` 只监听 `push: branches: [main]`(自己 repo) + `workflow_dispatch`
(手动)。两 repo 之间**没有任何 automation 串起来**。

**正确流程**:euv PR merge 完成后,**手动**走两步收尾:

1. 触发 euv-docs workflow_dispatch(让 docs 站重新 build,引用最新 euv crate):

   ```bash
   gh workflow run deploy.yml --repo euv-dev/euv-docs --ref main
   ```

2. 等部署完成后,手动调用 ltpp.vip 镜像同步 API:

   ```bash
   scripts/sync-pages.sh euv-dev/euv-docs
   ```

   端点:`POST https://ltpp.vip/api/github/pages/sync/<owner>/<repo>`,镜像站
   刷新延迟 ~1 分钟(见 `static-site-deploy-verification/references/ltpp-vip-mirror.md`)。

**复制以下脚本到 `/root/scripts/sync-pages.sh` 或 `scripts/sync-pages.sh`**——这是
euv 仓库 `.github/workflows/pages.yml` 里 `Sync Pages` step 的直接剥离,60 次
重试,默认每次间隔 60s:

```bash
#!/usr/bin/env bash
set -euo pipefail
TARGET="${1:-euv-dev/euv}"
MAX_RETRIES="${MAX_RETRIES:-60}"
RETRY_DELAY="${RETRY_DELAY:-60}"
URL="https://ltpp.vip/api/github/pages/sync/${TARGET}"
for i in $(seq 1 "${MAX_RETRIES}"); do
  if curl -sf -X POST "${URL}" -H "Connection: close"; then
    echo ""; echo "[sync-pages] Sync succeeded on attempt $i"; exit 0
  fi
  echo "[sync-pages] Attempt $i of ${MAX_RETRIES} failed"
  [ "$i" -lt "${MAX_RETRIES}" ] && sleep "${RETRY_DELAY}"
done
exit 1
```

**测试**: 脚本完成后,**真实验证** = Playwright 加载 `https://<user>.github.io/<repo>/`
(gh-pages 源)确认新内容;再用 `curl --compressed https://ltpp.vip/github/pages/<owner>/<repo>/`
确认镜像也已刷新(短 alias 路径 `/euv` / `/euv-docs` 仍返回 0 字节,这是 ltpp.vip nginx
反代配置 bug,不是 sync 失败)。

**反向**:同样的 chain 也适用于 euv-app(android build 用最新 euv wasm)、hyperlane
quick-start 等下游项目。流程统一:**framework repo PR merge → 手动 trigger 下游
docs/example repo workflow → sync API 推镜像**。

**正向上自动触发(下游 repo 加 pages.yml)**: euv-docs 自己也有同样的问题 —— euv
合并新版本后,euv-docs 不手动 dispatch 就一直用旧 euv。**euv-docs 仓 0.18.x 起
自带 `pages.yml`**(2026-08 PR #15 合并到 euv-dev/euv-docs master,run id `33319151908`
首次成功):触发条件 `workflow_run: workflows: [Deploy to GitHub Pages]` + `workflow_dispatch`,
**共用 `concurrency.group: pages`** 防止与上游 `deploy.yml` 抢着跑,build + deploy +
ltpp.vip sync 三件套全打包。Fork(`eastspire/euv-docs`)部署 GitHub Pages **会失败**
—— GitHub inherent 限制 fork 无 Pages 权限,error 文案 `Ensure GitHub Pages has been
enabled: https://github.com/eastspire/euv-docs/settings/pages`,只测试完整链用
upstream。

**Pages env policy 暗坑**:`actions/deploy-pages@v4` 会读 repo env policy 的
`deployment-branch-policies`(默认允许 `main`)。但 euv-docs 的 deploy.yml listen
的是 `main`,而 fork 用 `master` 测试会失败 `Branch "master" is not allowed to deploy
to github-pages due to environment protection rules` —— 即使 euv-docs 默认 branch
是 master 也要走 `gh api PUT /repos/<org>/<repo>/environments/github-pages/deployment-branch-policies`
加 `[master]`。**做法**:测试 fork 部署前先 PUT 加 branch + DELETE 默认的 `main`,
否则 workflow_run 立刻 fail。

**为什么不自动化**:在 euv repo 加 `repository_dispatch` 跨 repo 通知是可行的,
但需要 euv-docs repo 端 `repository_dispatch` trigger 配置(目前没配),且会引入
"framework 发了 PR → 自动 build docs → 没 review 窗口"的不可逆副作用。建议先
保持手动触发,等 euv / euv-docs 协同发布节奏稳定后再加 automation。

## Support files

- `references/mobile-safe-area-navbar.md` — 四轮 PR 迭代的 mobile safe-area 修
  复链(PR #53–#56),含 Playwright 注入 `--safe-area-inset-top` 复现真实设备的
  正确姿势(headless Chrome env() 永远是 0,不能让 hook 缓存值被 init_script 覆
  盖)
- `scripts/sync-pages.sh` — 仿照 euv 仓库 `.github/workflows/pages.yml` 的
  `Sync Pages` step 剥离出来的通用脚本,手动调用 ltpp.vip 镜像站刷新 API。
  用于坑 9(euv master merge 后通知 euv-docs / 下游消费者仓库镜像同步)。
  端点:`POST https://ltpp.vip/api/github/pages/sync/<owner>/<repo>`。
  支持 `MAX_RETRIES` / `RETRY_DELAY` env 覆盖
- `scripts/screenshot-locales.sh` — 多 locale 截图批处理(已随本 skill 提供)

## 坑 10:patch version bump 只改 root Cargo.toml,sync_workspace_version CI 自动同步(2026-08 验证)

**症状**:bug fix PR merge 后,需要 patch bump 让下游(euv-docs / crates.io 用户)
拿到 fix 后的版本。**错误做法**:手工改 7 个 member crate 的 `[package].version`
+ `[workspace.dependencies]` 里的 7 个 path-dep `version`,然后 commit + push。
这会**和 CI 后面跑的 `sync_workspace_version` 打架**(root 改了 member 没改 → CI
检测到不一致 → 推送一个 `chore: sync all package versions to X.Y.Z` commit 覆盖
你的 7 处修改 → 实际重复 commit)。

**正确流程**(只 1 行 diff):
1. `git checkout master && git pull upstream master && git checkout -b chore/bump-X.Y.Z`
2. 只改**根** `Cargo.toml` 第 3 行 `version = "X.Y.W" → "X.Y.Z+1"`(一个字段,
   一个 diff)。
3. `git commit -am "chore: bump version to X.Y.Z+1"`(commit message 简洁说明 fix
   关联,例如"PR #NN is the first user-visible change since X.Y.Z")。
4. `git push upstream master`(**注意**:直接推 upstream,不是 fork;新 commit
   `chore:` 走 fast-forward,git 直推即可,无需 PR 流程)。
5. 等 `Rust` workflow 的 `sync_workspace_version` job 跑完(约 6 分钟),它会
   自动 push 一个 commit `chore: sync all package versions to X.Y.Z+1`,把根 +
   7 个 member crate + 7 个 workspace dependency 全部对齐到 X.Y.Z+1。
6. **不要**自己再 force push sync fork master —— CI 已 push 一次,你再 force
   会和它打架(force-with-lease 也会因 stale 而 rejected)。

**验证**(确认 7 个文件全对齐):
```bash
git fetch upstream master
grep -rn '^version = "X.Y' --include=Cargo.toml | sort
```
应输出 14 行(7 个 member + 7 个 `[workspace.dependencies]` path-dep),全部同一版本号。

**发布 crates.io 时**:同样的 patch bump chain 会触发 `publish` step,如果某 member
crate 已经发了前一版本,CI 会按 workspace order 顺序 publish 全部 → 检查 crates.io
`max_stable_version` 确认(见上面"cargo publish 鸡生蛋鸡生蛋"章节)。

**为什么不让 `sync_workspace_version` job 自己改 root version**:这个 job 只读 root
version 然后同步到 member,**不**改 root 自身。所以 bump root version 必须手工
—— 这是 Cargo workspace 的固有限制,所有根 crate(只有 `version` + `pub use`)的
版本号 = 整个 workspace 的对外版本号,人为 bumping 才符合 release 流程语义。

## 坑 11:分支 base 错误导致 PR diff 混入未合 commit(2026-08-29 docs-pages/docs PR #19 教训)

**症状**:在前一个未合 PR 的 feature 分支上 `git checkout -b new-feature`,
导致 new-feature 分支的 base = 旧 PR 的 head,**新的 PR diff 包含前一个 PR 的
所有 +N/-M 改动**,显示 70 文件 +2893/-72,实际只改 52 文件 +0/-7934。reviewer
review diff 看到一堆不在描述里的改动,误以为 PR 范围失控。

**规则**:`git checkout -b <new-branch>` 前**必须** `git checkout master && git pull
origin master`,确认当前就是 origin/master 顶端,然后再 checkout 新分支。

**例外**:stacked / dependent PR(后一个 PR 的 base 是前一个 PR 的 head)是合法
模式,只在描述里说清楚"依赖 #NN,等 #NN 合了再 review 这个",且只用 stacked PR
替代大 PR 的写法。

**诊断**:开 PR 后立刻 `gh pr diff N --stat`,看到不在本 PR commit 范围内的 stat
变更 → branch base 错了。**立刻** `gh pr close N --comment "Superseded by #M+1,
branch base 错了" && git push origin --delete <wrong-branch> && git checkout master
&& git checkout -b <correct-branch> && git cherry-pick <own-commits>` 重开。
