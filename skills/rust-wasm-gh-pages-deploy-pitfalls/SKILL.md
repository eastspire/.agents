---
name: rust-wasm-gh-pages-deploy-pitfalls
description: Rust + euv → WASM + GitHub Pages 部署踩坑记录,涵盖 import path 错误、CDN 缓存、master ref 损坏的解法
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
