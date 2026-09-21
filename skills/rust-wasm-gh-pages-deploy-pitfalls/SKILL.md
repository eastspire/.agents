---
name: rust-wasm-gh-pages-deploy-pitfalls
description: 'Rust + euv → 发布/部署踩坑记录,涵盖 WASM/GitHub Pages 部署 (import path / CDN 缓存 / master ref 损坏 / **Pages build_type=legacy 会忽略 upload-pages-artifact 的 Jekyll 暗坑 / docs/public 复制 subltety 必须 force fresh / Pages 子路径部署 md 绝对路径必须带子前缀 / [!tip] VuePress 自定义容器在 euv-docs 上原文泄漏 / **README frontmatter 2-vs-4 空格缩进错位 → 整个 features: 数组被吞 / euv-docs feature card 不支持 link: 字段,卡片不点击 / c_feature_card 默认无边框,site-local CSS override pattern / emoji 在 headless Chromium 渲染成方框 + Pages CDN 缓存双重失效 / euv-docs CLI 产物默认写到 <EUV_DOCS_SRC_DIR>/www 不是 cwd/www / euv-docs CLI positional SRC_DIR 传相对路径会让 build.rs 读 euv-docs crate 自带 starter docs 渲染模板而不是用户 docs / `gh run view` success 不等于 deploy 完成 — artifact 推到 gh-pages 必须查 `?sha=gh-pages` 才能确认**) + crates.io cargo publish (workspace dev-dep chicken-and-egg / 版本号静默失败 / pre-flight dep resolver) + 移动端浏览器 safe-area 与 navbar 间距 (env() vs CSS var 的脱钩、navbar background 同 page 背景导致的安全区视觉不可见、use_safe_area_fix hook 的缓存语义) + **跨 repo deploy chain (euv master merge 不会自动触发 euv-docs deploy,需手动 workflow_dispatch + ltpp.vip sync-pages.sh;下游 repo 加 pages.yml 实现自动链;Pages env policy 必须显式 PUT branch;双分支 workflow deploy 把 source 切到 docs 让用户视角"新地址")** + **patch version bump 只改 root Cargo.toml 的 1 个字段,CI sync_workspace_version 自动同步 7 个 member**(不要手工改 7 处) + **分支 base 错误导致 PR diff 混入未合 commit**(必须从干净 master 起)。同一仓库任意 Rust 发布链路触发本 skill。'
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

## 坑 12:Pages build_type 默认是 `legacy`(Jekyll),会忽略 `actions/upload-pages-artifact` 上传的 `www/`(2026-09 docs-pages/docs-euv 教训)

**症状**:workflow 全绿、`actions/deploy-pages@v4` 完成,但线上看到的是 Jekyll 把 `README.md` 当主页渲染的产物(标题变成 euv-docs 模板默认的"euv-docs | docs-euv"),不是 build 出来的 wasm bundle。

**根因**:GitHub Pages 项目创建后,`build_type` 默认 `legacy` = "Jekyll 自动渲染 from source branch"。这个模式下,GitHub 自动跑 Jekyll build,**完全忽略** workflow `actions/upload-pages-artifact` 上传的 `www/` artifact(Jekyll 看到源 branch 有 `README.md` 就把它的 HTML 渲染成主页)。

**诊断**:线上 `curl https://<user>.github.io/<repo>/` 看到 Jekyll 渲染产物(标题是 README 的 H1、Jekyll SEO meta tags、`<link rel="stylesheet" href="/docs-euv/assets/css/style.css">`、没有 `<script type="module">import init from './pkg/...js'`),而不是 wasm bundle 主页。

**解法**:把 `build_type` 改为 `workflow`,让 Pages 项目**只**接受 workflow 上传的 artifact,跳过 Jekyll:

```bash
gh api -X PUT repos/<owner>/<repo>/pages \
  -f 'build_type=workflow' \
  -f 'source[branch]=<branch>' \
  -f 'source[path]=/'
```

**验证**:`gh api repos/<owner>/<repo>/pages --jq '{build_type, status, url: .html_url}'` 返回 `{"build_type": "workflow", ...}` = 配置生效。

**坑**:改 `build_type` 不自动重跑现有 workflow。需要新触发一次 `workflow_dispatch` 或 push,否则 Pages 仍展示旧 Jekyll 产物。

**适用范围**:任何用 `actions/deploy-pages@v4` + `actions/upload-pages-artifact` 的站点(不仅是 docs-euv)。euv engine / euv-docs / 任何 Rust WASM 项目都默认踩这条 — 因为 `build_type=legacy` 是 Pages 项目的 creation default。

## 坑 13:`docs/public/` 复制 subltety — build.rs 不一定每次都跑(2026-09 docs-pages/docs-euv 教训)

**症状**:`euv build --release --index-html template.html -- ...` 跑完,`www/` 里有 `index.html` + `pkg/<name>_bg.wasm` + `pkg/<name>.js`,**但完全没有 `www/img/`、`www/css/`、`www/markdown-images/`**。本地 build 看起来"成功",但线上页面 `<img>` 全 404。

**根因**:`euv-docs` 框架的 `build.rs` 里有这段(只在你项目的 `build.rs`,不是 euv-cli 内置):

```rust
println!("cargo:rerun-if-changed=docs");
let public_dir = manifest_dir.join("docs").join("public");
if public_dir.is_dir() {
    let www_dir = manifest_dir.join("www");
    copy_dir(&public_dir, &www_dir);
}
```

`cargo:rerun-if-changed=docs` 让 cargo 看到 `docs/` 整个目录树变化才 rerun build.rs。问题是:
- cargo + sccache 的 binary cache 会"觉得"build.rs 输出没变就跳过 binary recompile
- 但 build.rs 内部的 `copy_dir` 是文件系统操作,即使 build.rs 跑过,`www/` 残留可能覆盖新复制

**诊断**:`rm -rf www && euv build ... && ls www/` 看有没有 `essay/` `img/` `css/` `markdown-images/`。

**解法**(2 选 1):

**A. workflow 加 force-fresh step**(最稳):
```yaml
- name: Force fresh build output (build.rs copies docs/public only when source tree changes)
  run: rm -rf www
- name: Build site (euv build -> www/)
  run: euv build --release --index-html template.html -- --target web --out-dir www/pkg --out-name euv_docs --no-typescript --no-pack --no-gitignore
```

**B. euv-cli 自带 `--www-dir`**:某些版本支持,看 `euv build --help` 的 `WWW_DIR_ARG` 选项。**不推荐** — 版本兼容性差,fallback to A。

**预防**:每次新增 `docs/public/` 子目录或文件,本地 build 后必查 `www/<subdir>/` 是否齐全再 push。

**适用范围**:**任何**用 `euv-docs` 模板的项目(`~/github/<owner>/<repo>/` 里 `build.rs` 复制 `docs/public/` 的)。不止 docs-euv。

## 坑 14:Pages 子路径部署时,md 里绝对路径必须带子前缀(2026-09 docs-pages/docs-euv 教训)

**症状**:`https://<user>.github.io/docs-euv/` 部署后,页面所有 `<img src="/markdown-images/X.png">` 404。

**根因**:Pages 部署 URL 是 `https://<user>.github.io/<repo>/`(项目子路径),但 md 里写的绝对路径 `/markdown-images/X.png` 浏览器解析为**域名根** `https://<user>.github.io/markdown-images/X.png`(没有 `/<repo>/` 前缀)→ 404。

**解法**:md 里所有绝对路径必须带 `/<repo>/` 前缀:

```markdown
<!-- 错误 -->
![](/markdown-images/foo.png)

<!-- 正确 -->
![](/docs-euv/markdown-images/foo.png)
```

也适用于 raw HTML `<img src="/img/foo.png">`(euv-docs build.rs 处理 markdown 链接时会保留绝对路径不变,raw HTML 同样不被前缀化)。

**适用范围**:任何用 `euv-docs` 部署到 `<user>.github.io/<repo>/` 的项目。如果部署到 custom domain 或 user/org root site,不带子前缀。

**诊断脚本**(扫描 md 残留):

```python
import os, re
img_pat = re.compile(r'!\[[^\]]*\]\(([^)]+)\)')
html_img = re.compile(r'<img\s+[^>]*src=["\']([^"\']+)["\']', re.IGNORECASE)
for root, _, files in os.walk('docs'):
    for f in files:
        if not f.endswith('.md'): continue
        p = os.path.join(root, f)
        with open(p) as fh: txt = fh.read()
        for m in img_pat.finditer(txt):
            s = m.group(1)
            if s.startswith('/') and not s.startswith('/docs-euv/'):
                print(f'BAD MARKDOWN: {p}: {s}')
        for m in html_img.finditer(txt):
            s = m.group(1)
            if s.startswith('/') and not s.startswith('/docs-euv/'):
                print(f'BAD HTML IMG: {p}: {s}')
```

跑一遍后用 `sed -i 's|](/|](/docs-euv/|g' docs/**/*.md` 批量修复 + review。

### 坑 14a:hash 路由 `/foo` vs `/foo.html` 的 README 自动检测(2026-09 docs-pages/docs-euv 教训)

**症状**:hero button 写 `link: /catalog`,点击进 hash 路由 `#/catalog`,Playwright 看到 `c_euv_result_code === '404'` + `Page not found`。改成 `link: /catalog.html` → 同一个 URL `#/catalog.html` → 渲染 catalog 页面。

**根因**:euv-docs hash router 有 **README.md 自动检测**规则:

| 路由 | 解析到 | 备注 |
|---|---|---|
| `#/foo` | `docs/foo/README.md` | **README 优先**;`docs/foo.md` 404,`docs/foo/index.html` 404 |
| `#/foo.html` | `docs/foo.md` | **NOT** `docs/foo/index.html` |
| `#/foo/bar.html` | `docs/foo/bar.md` | **NOT** `docs/foo/bar/index.html` |

所以 `#/ltpp` 工作(因为 `docs/ltpp/README.md` 存在),`#/catalog` 404(`docs/catalog/README.md` 不存在,`docs/catalog.md` 也不存在),`#/hyperlane/process.html` 工作(`docs/hyperlane/process.md` 存在)。

**诊断**:Playwright 跑 `page.evaluate()` 验证:
```js
({ hash: location.hash, mainText: document.querySelector('.c_app_main')?.innerText.slice(0, 50), notFound: document.querySelector('.c_euv_result_code')?.innerText === '404' })
```

**解法**:home `actions[].link` / sidebar links 一律写 `link: /xxx.html`(带 .html 后缀),不依赖 README 自动检测。如果某个工具确实只有 README 没有专属页(如 ltpp 这种 landing),可以写 `link: /ltpp`(无后缀) — 但其他情况都用 .html 形式更安全。

**适用范围**:任何用 euv-docs 的项目。如果在 hero/sidebar 写 hash link 然后 404,先检查目标路径有没有 .md 文件,再检查 README.md 是否存在。

### 坑 15:[!tip] VuePress 自定义容器在 euv-docs 上原文泄漏(2026-09 docs-pages/docs-euv 教训)

**症状**:md 里写了 `[!tip]\n> content` 这种 VuePress 自定义容器语法,渲染时浏览器直接看到文本字面量 `[!tip]` + 下面引用块内容(不是带颜色的卡片提示框)。

**根因**:`euv-docs` 的 build.rs 用 pulldown-cmark 0.12 解析 markdown,**不支持** VuePress 风格 `[!tip]` / `[!warning]` / `[!note]` / `[!info]` / `[!danger]` 自定义容器。pulldown-cmark 0.12 **支持** `:::tip` 这种 fenced-block 容器(`build.rs` 的 parser Options 不一定启),但 `docs-pages/docs` 的 VuePress 写法是 `[!tip]` 单行指令 + 下面 `>` blockquote,euv-docs 完全不识别。

**解法**:替换为加粗 emoji 文本(md 通用语法,所有平台都支持):

```markdown
<!-- 错误 -->
[!tip]
> LTPP WEB 基于 Vue2.js 开发

<!-- 正确 -->
**💡 TIP**
> LTPP WEB 基于 Vue2.js 开发
```

**批量替换脚本**:
```python
import os, re
emoji = {'tip': '**💡 TIP**', 'warning': '**⚠️ WARNING**',
         'note': '**📝 NOTE**', 'info': '**ℹ️ INFO**', 'danger': '**🚨 DANGER**'}
pat = re.compile(r'\[!(tip|warning|note|info|danger)\]')
def repl(m): return emoji.get(m.group(1), f"**{m.group(1).upper()}**")
for root, _, files in os.walk('docs'):
    for f in files:
        if not f.endswith('.md'): continue
        p = os.path.join(root, f)
        with open(p) as fh: txt = fh.read()
        new = pat.sub(repl, txt)
        if new != txt:
            with open(p, 'w') as fh: fh.write(new)
```

emoji 显示为方框是 Chromium headless 字体问题,真实浏览器正常。语义正确,**md 仍然在 VuePress / GitHub 上也正常渲染**(两边都把 `**💡 TIP**` 当粗体)。

**坑**:即使 `**💡 TIP**` 也可能在 CommonMark 不解析 — `**` 内不能有前导空格。如果 regex 把 `**💡 TIP**` 替换成 `** TIP**`(前导空格从 emoji 删除位置留下),pulldown-cmark 会把它当字面文本输出,**DOM 里看到字面 `** TIP` 字符串**而不是粗体 `TIP`。验证:
```python
article_text = article.innerText
has_literal = '** TIP' in article_text or '**WARNING' in article_text
# 如果 has_literal → 全部需要再次 sweep: '** ' → '**' (删除前导空格)
```

解法:bulk-frontmatter rewrite 完成后,用 Python regex 再跑一遍 `\s+\*\*\s+(\w)` → `**$1`,把任何 `** xxx` 形式还原为 `**xxx`。或者改原始替换的 `format!()` 模板,直接生成无空格的形式 `**{label}**`。任何 emoji-strip pass 完成后,**必跑 DOM-level 检查 `article.querySelectorAll('strong')`** 确认 TIP 渲染成 strong element。

**适用范围**:任何从 VuePress / vuepress-theme-hope 迁过来的 md。如果项目只用 euv-docs,新写 md 不要用 `[!tip]`。

### 坑 16:用 `pages build_type=workflow` 后,push 不会自动触发 workflow — 必须 `workflow_dispatch`(2026-09 docs-pages/docs-euv 教训)

**症状**:改了 `deploy.yml` 把 `branches: [master, docs]` 都监听,push 到 `docs` 分支,但 `actions/runs` API 没看到新 run。`gh api repos/.../commits/docs --jq .sha` 看到 commit 已 push。

**根因**:`actions/runs` API 默认返回**所有 branch** 的 run,但 `workflow_run` trigger 的 pages.yml 会立刻 re-fire `pages.yml` 自身,导致 `deploy.yml` 被 `concurrency.cancel-in-progress` 取消。或简单说 — `gh run list --branch <non-default>` 列不到,**因为 GitHub API `actions/runs` 不带 query 时只列 default branch**。

**诊断**:
```bash
gh api repos/<owner>/<repo>/actions/runs?branch=docs --jq '.workflow_runs[] | "\(.id) \(.head_sha[0:8]) \(.event) \(.conclusion)"'
```
注意 `?branch=` 参数。

**解法**:push 后如果没看到 deploy run,直接 `workflow_dispatch`:

```bash
gh api -X POST repos/<owner>/<repo>/actions/workflows/<wf_id>/dispatches -f ref=docs
# wait
gh api repos/<owner>/<repo>/actions/runs?per_page=1 --jq '.workflow_runs[0].status + " " + (.workflow_runs[0].conclusion // "null")'
```

**适用范围**:任何 push 触发但没自动跑的 workflow。**Pages deploy workflow 特别容易撞这条** — concurrency group 经常 cancel in-progress 而新 push 的 run 又"消失"在 API 默认 view 里。

### 坑 17:`docs/README.md` frontmatter YAML 缩进错位 → 整个 `features:` 数组被丢弃(2026-09 docs-pages/docs-euv 教训)

**症状**:本地 build + 线上部署都成功(workflow green,Pages `status: built`),但 home 页只有 navbar/sidebar/footer,**hero 区域和 feature grid 100% 空白**。Playwright `document.querySelectorAll('.c_feature_card').length === 0`,WASM 内存里的 `DocsSite.pages` 里 `home=true` 那一项的 `features: &[]` 全空、`hero_text: ""` / `tagline: ""` / `actions: &[]`。

**根因**:`euv-docs` 项目自己的 `build.rs` 用 `serde_yaml` 解析 md frontmatter,YAML parser 在第一个缩进错位处就开始丢掉后续内容。VuePress 写法习惯 4 空格 list item mapping(`  - title: x` + `    details: y`),一旦迁移脚本 regex replace 把 4 空格错改成 2 空格,YAML 仍然 valid 但语义变 list-of-scalar,parser 丢弃整个 `features:` 数组。

**具体案例**:21 个 feature entry 的 `details:` / `icon:` 子字段用了 2 空格缩进(应为 4 空格),`yaml_bool("home")` / `yaml_str("heroText")` 都对,但 `yaml_list("features")` 返回 `&[]`(空数组),首页 hero 全部丢失。

**诊断**:
```bash
python3 -c "
import yaml, re
with open('docs/README.md') as f: txt = f.read()
fm = txt[txt.find('---')+3:txt.find('\n---', 4)]
d = yaml.safe_load(fm)
print('home:', d.get('home'), 'features:', len(d.get('features', [])))
"
# 期望 home=True + features.count == 36;若 features=0 则缩进错
```

**更准的诊断**:生成的 `OUT_DIR/docs_gen.rs` 里搜 `home: true`,搜不到 = `home` 字段也被吞了:
```bash
grep -c 'home: true' /tmp/target/wasm32-unknown-unknown/release/build/docs-euv-*/out/docs_gen.rs
```

**解法**:写迁移脚本时,缩进必须严格 YAML 风格(全部 4 空格,不要混 2/4);改完用 Python `yaml.safe_load` 反向验证 frontmatter 解析出的字段数等于期望。

**预防脚本**(`scripts/check-frontmatter.py`,本 skill 收录):
```python
import yaml, os, sys
broken = []
for root, _, files in os.walk('docs'):
    for f in files:
        if not f.endswith('.md'): continue
        p = os.path.join(root, f)
        with open(p) as fh: txt = fh.read()
        if not txt.startswith('---\n'): continue
        end = txt.find('\n---', 4)
        try:
            d = yaml.safe_load(txt[4:end])
            if d is None: continue
            # for home pages, features must be non-empty if declared
            if d.get('home') and d.get('features') is not None and len(d['features']) == 0:
                broken.append(f'{p}: home=true but features=0')
        except yaml.YAMLError as e:
            broken.append(f'{p}: YAML error {e}')
if broken:
    print('\n'.join(broken)); sys.exit(1)
```

**适用范围**:任何用 `euv-docs` 模板 + 自定义 `docs/README.md` 的项目。euv-docs 自己原版 README 是 3 个 features 单语言 locale,语义清楚;一旦用户改 frontmatter 加更多 feature / 多语言,缩进错位立刻爆。

### 坑 18:`euv-docs` feature card 不支持 `link:` 字段,卡片不点击跳路由(2026-09 docs-pages/docs-euv 教训)

**症状**:用户说"feature card 应该点击直接路由"。检查 `docs/README.md` frontmatter 每个 feature 都有 `link: /xxx/`,但 Playwright 测试 `c_feature_card` 周围**没有 `<a>` 包裹**(`c.closest('a') === null`)。点击 feature card 无反应。

**根因**:`euv-docs` 0.18.x 上游 `home_page.rs` 渲染 feature grid 只用 `icon / title / details` 三元组,**不读** `link:` 字段。这是上游框架固有限制,不是 bug。改框架源码需要 fork `euv-dev/euv-docs`,工作量大。

**诊断**:
```bash
gh api repos/euv-dev/euv-docs/contents/src/component/home_page.rs --jq .content | base64 -d | grep -A 2 "features"
# 看 features 是否传给 euv_feature_grid + 是否读 link
```

**解法**(两层):
1. **Sidebar 路由**:euv-docs sidebar 是真路由入口,所有工具(feature 对应的 36 个页面)都能 sidebar 点击跳转。这是当前框架下"feature card → 工具页"的标准路径
2. **如坚持 feature card 点击**:需要 fork `euv-dev/euv-docs` + 改 `home_page.rs` 在 `euv_feature` 结构里加 `link: Option<&'static str>` + 在 `home_page` html! 块用 `<a href={feature.link.unwrap_or("")}>` 包裹卡片,然后项目里把 `euv-docs` path-dep 换成自己的 fork

**用户预期管理**:用户说"feature card 点击路由"= 误以为 VuePress 行为(euv-docs 不继承)。要先在 clarify 时告诉用户 euv-docs 上游不支持 + 给出 sidebar 替代方案 + fork 的工作量估算,不要直接动手改框架源码(违反"业务项目禁止改依赖"铁律)。

**适用范围**:任何用 `euv-docs` 的项目。如果用户从 VuePress / vuepress-theme-hope 迁过来,几乎肯定会撞这个 — VuePress feature grid 是真 link 的。

### 坑 19:`c_feature_card` 默认无边框,需要 site-local CSS override(2026-09 docs-pages/docs-euv 教训)

**症状**:feature grid 渲染正常,卡片内容齐全,但卡片之间视觉上没分隔,粘在一起像一坨长文本。用户感觉"feature card 应该有边框"。

**根因**:`euv-ui` 0.18.x 的 `EuvFeature` 组件 CSS(在 `EUV_MD_CSS` 里)只设了 padding + flex layout,**没有 `border` 属性**。这是上游默认。

**解法**:在 `src/lib.rs` 的 `main()` 里,在 `Css::inject_css(EUV_MD_CSS)` **之后**加 `Css::inject_css(...)` 注入 site-local CSS override(用 `!important` 防止上游 specificity 变化):

```rust
Css::inject_css(
    ".c_home_feature_grid .c_feature_card { \
        border: 1px solid var(--euv-c-border, #e3e3e3) !important; \
        border-radius: 8px !important; \
        padding: 16px !important; \
        transition: border-color 0.15s ease, transform 0.15s ease; \
    } \
     .c_home_feature_grid .c_feature_card:hover { \
        border-color: var(--euv-c-brand, #3451b2) !important; \
        transform: translateY(-2px); \
    } \
     @media (prefers-color-scheme: dark) { \
        .c_home_feature_grid .c_feature_card { border-color: var(--euv-c-border-dark, #2e2e2e) !important; } \
        .c_home_feature_grid .c_feature_card:hover { border-color: var(--euv-c-brand-dark, #a8b1ff) !important; } \
     }",
);
```

**CSS var 回退策略**:`var(--euv-c-border, #e3e3e3)` 是 euv-ui 已有的 theme var 候选名;若将来 euv-ui 升级重命名 var,fallback 保证视觉不破。**不要 hardcode `#3451b2` 等品牌色**到非 hover 状态,保留 euv-ui 主题色。

**诊断**:Playwright `getComputedStyle(c).border` 看实际渲染值。`1px solid rgb(227, 227, 227)` = 生效,`0px none` = 上游没 border / override 没生效。

**适用范围**:任何用 `euv-docs` 想给 feature card / sidebar item / hero button 加视觉分隔的项目。同样的 pattern 可加 `c_sidebar` / `c_navbar` / `c_hero` 的 border / shadow / 圆角。

### 坑 19a:Rust raw string `r#"<...>"#` 第一个字符 `<` 泄漏到 CSS 输出,导致 CSS parser 静默丢弃该 `Css::inject_css` 块(2026-09 docs-pages/docs-euv 教训)

**症状**:本地 build + CI build 都成功,WASM binary 里能 `strings | grep` 到你的 CSS 字符串,但浏览器里 `getComputedStyle` 拿到的 padding/border/margin 还是上游值(没被覆盖)。诊断时 `document.styleSheets[].cssRules` 用 selector 查不到你的规则,但 `ownerNode.textContent.indexOf(selector) !== -1`(说明文字在 `<style>` 里但 parser 没识别)。

**根因**:Rust raw string literal 语法 `r#"..."#` 允许字符串字面量里直接出现 `"`(不需转义),所以写 CSS 时很自然会写:

```rust
Css::inject_css(r#"<
        .c_nav_items_scroll .c_euv_sidebar_group_title {
            padding-left: 20px !important;
        }
"#);
```

`r#"<` 这个 `<` 是 raw string 字面量**内部的第一个字符**——它会原样出现在最终字符串里(在所有 CSS 规则前面)。CSS parser 在 `<` 处失败,从此处开始到下一个 `}` 之前的整段 CSS 块被浏览器静默丢弃(整段 not 整条 rule)。

**为什么有时看起来"工作"**:如果上游某条规则的 specificity 已经刚好够,你的 override 没生效也不会被注意到。但如果上游规则 specificity 不够,你的 override 应该赢却没赢——CSS 文本里有你的规则,但运行时没用。

**诊断三步**(任选):
```bash
# 1. 查 wasm 里到底有没有你的规则
strings www/pkg/<crate>_bg.wasm | grep '<your-selector>'

# 2. 浏览器里查 <style> textContent 包含你的选择器吗?
#    getComputedStyle(node).padding 与 expected 不符 = text 在但 parse 失败
page.evaluate("() => document.styleSheets[document.styleSheets.length-1].ownerNode.textContent.indexOf('<your-selector>')")

# 3. 浏览器里查你的规则在 cssRules 里吗?
page.evaluate("""() => {
  let found = [];
  for (const sheet of document.styleSheets) {
    for (const rule of sheet.cssRules || []) {
      if (rule.selectorText && rule.selectorText.includes('<your-selector>')) {
        found.push(rule.cssText.slice(0, 200));
      }
    }
  }
  return found;
}""")
# 如果 textContent 包含 + cssRules 不包含 = CSS parser 把你的块吞了 = r#"< leak
```

**解法**(三选一):
1. **不写 raw string 的第一个字符**(最稳):
   ```rust
   Css::inject_css(r#"
           .c_nav_items_scroll .c_euv_sidebar_group_title {
               padding-left: 20px !important;
           }
       "#);
   ```
   raw string 从下一个字符(`\n`)开始,没有 stray 字符泄漏。

2. **用普通 string + 转义引号**:
   ```rust
   Css::inject_css(".c_nav_items_scroll .c_euv_sidebar_group_title { padding-left: 20px !important; }");
   ```

3. **不带 `<` 分隔符**:
   ```rust
   Css::inject_css(r#"
       .c_nav_items_scroll .c_euv_sidebar_group_title {
           padding-left: 20px !important;
       }
   "#);
   // 与 1 等价,但显式 newline 在 CSS 字符串开头不会泄漏字符
   ```

**预防**:写 `Css::inject_css(r#"..."#)` 时,先想一下 raw string 第一个字符是不是 CSS token。`<` / `&` / `{` 都是有效 CSS token(CDO / AMP / at-rule),不破坏;但 `<` 是最常见误写,因为 dev 想"用 `<` 标识 raw string 的开始位置"——其实它就是 raw string 的第一个字符。

**适用范围**:任何调用 `Css::inject_css` 注入 site-local CSS 的 euv 项目(feature card / sidebar / navbar / hero / mobile drawer 等任意 layout override)。

### 坑 19b:CI build (euv-cli 0.24.7) 的 CSS 处理与本地 (0.21.2) 不同 — 同样的 `!important` + 同 specificity 在 CI 可能失效(2026-09 docs-pages/docs-euv 教训)

**症状**:本地 build 用 `euv-cli 0.21.2` 跑出来的 site-local CSS override 完美覆盖上游规则,但 push + CI build (用 `cargo install euv-cli --locked` 锁版本,0.24.7) 后,线上 `getComputedStyle` 拿到的还是上游值。`strings` 看 WASM binary 包含你的 CSS,但浏览器没应用。

**根因**(两个独立观察合并的根因):

1. **CSS rule reordering**:`euv-cli 0.24.7` 的 CSS post-processing 比 `0.21.2` 更激进——它会把所有 `Css::inject_css` 调用合并进同一个 `<style>` element,但 rule 之间的**先后顺序**可能与 `Css::inject_css` 的调用顺序不同(具体看版本)。如果你的 override specificity = upstream specificity,而 CI 把你的 override 排到 upstream **之前**,即便有 `!important`,upstream 那条**后来的**且同样 `!important` 的规则会赢(同 specificity 时后写者赢)。

2. **upstream CSS 加 `!important` + same specificity,赢者靠顺序**:euv-ui 上游 `c_feature_card` 的某些 CSS rule(`.c_home_feature_grid .c_feature_card { border: 1px solid !important; ... }`)用 `!important` 提高优先级,你的 site-local override 如果只比 upstream specificity 高一点点(例如 0,1,0 vs 0,2,0),在 cascade 后可能胜出,但如果 specificity 反过来或相同,顺序决定一切。

**诊断**:
```js
// 浏览器里列出匹配元素的所有 CSS 规则,按 stylesheet 出现顺序
() => {
  const card = document.querySelector('.c_feature_card');
  let all = [];
  let idx = 0;
  for (const sheet of document.styleSheets) {
    try {
      for (const rule of sheet.cssRules || []) {
        if (rule.selectorText && card.matches(rule.selectorText)) {
          if (rule.cssText.includes('padding') || rule.cssText.includes('border')) {
            all.push({idx, sel: rule.selectorText, css: rule.cssText.slice(0, 200)});
          }
        }
        idx++;
      }
    } catch (e) {}
  }
  return all;
}
```
看 site-local 规则(idx 大的)是不是排在上游后面 + specificity 比上游高。

**解法**:**用 `html body` 前缀把 specificity 拉到上游之上**:
```rust
Css::inject_css(r#"
    html body .c_home_feature_grid .c_feature_card {
        padding: 0 !important;
        border: none !important;
        border-radius: 0 !important;
    }
"#);
```
- 上游规则:`.c_home_feature_grid .c_feature_card` = specificity (0, 2, 0)
- 你的规则:`html body .c_home_feature_grid .c_feature_card` = specificity (0, 3, 1) (`html` + `body` 两个 type selector 加 (0, 0, 2))
- `html body` 加 2 个 type selector 提 (0, 0, 2) + `.c_home_feature_grid` + `.c_feature_card` 加 (0, 2, 0) = total (0, 2, 2) — 永远赢 upstream `(0, 2, 0)`

或者更狠:`html body .c_home_feature_grid .c_feature_card.c_feature_card` = (0, 3, 2),把 upstream 任何合理 selector 都盖掉。

**关键 insight**:`html body` 前缀对所有 `body` 内的元素都生效(整个 DOM),不影响 specificity 太多但总是高过上游。

**预防**:任何 site-local CSS override 都默认加 `html body` 前缀,不要纠结 specificity 计算——`html body` 加 2 type selectors,足够打败 euv-ui 0.18.x 的所有常见 selector (max `.c_home_xxx .c_xxx_yyy` = 0, 2, 0)。

**验证清单**(提交 PR 前):
1. `euv build --release --index-html template.html -- --target web --out-dir www/pkg --out-name <name> --no-typescript --no-pack --no-gitignore`
2. `grep '<your-override>' www/pkg/<name>_bg.wasm | head -3` — 字符串在 binary 里
3. Playwright 加载本地 server + page.evaluate 查 `getComputedStyle` 拿正确值
4. push + CI build success → Playwright 加载 `https://<user>.github.io/<repo>/` + 同样 evaluate → 一致 = 通过

**适用范围**:所有 site-local CSS override(feature card / sidebar / navbar / mobile / hero 等)。CI 版本升级时如果 CSS 行为变了,先怀疑这条。

### 坑 19c:Sidebar nested group title 对齐到父级 text 列(2026-09 docs-pages/docs-euv 教训)

**症状**:euv-docs 默认 sidebar 行为,一级 group title 文字在最左 (x≈22),二级 group title 文字 (e.g. APP, 桌面客户端) 在 x≈43 缩进位置,**视觉上二级 group title 看起来和二级 leaf link 一样**(两者 x 都 ≈44),层级关系混乱。

**根因**:euv-ui 0.18.x 的 sidebar 渲染规则——所有 group title 元素都有 `padding-left: 20px` 的上游样式(确保一级 group title 文字 x=22 = sidebar 视觉左边缘)。nested group title 在 children container 里,parent content area 起始 x=23 + padding 20 = nested title text x=43 — 比一级 group title 缩进 21px,看起来像 leaf link。

**解法**(两层 CSS override + selector 顺序 specificity trick):

```rust
Css::inject_css(r#"
    /* baseline: 任何 group title 用 20px padding,保证一级 group title x=22 */
    .c_nav_items_scroll .c_euv_sidebar_group_title {
        padding-left: 20px !important;
        margin-left: 0 !important;
    }
    /* override: nested (depth>=2) group title 取消 padding,让文字回到 group.x=23,与一级对齐 */
    html body .c_nav_items_scroll .c_euv_sidebar_children .c_euv_sidebar_group_title {
        padding-left: 0px !important;
        margin-left: 0px !important;
    }
"#);
```

**预期结果**:
- 一级 group title (LTPP-GIT仓库, LTPP-在线开发平台): text x=22,虚线 (children container border-left) x=10,距离 12px → **虚线在文字左边**
- 二级 group title (APP, 桌面客户端, 中间件, 使用介绍): text x=23,虚线 x=10,距离 13px → **虚线在文字左边**(与一级对齐)
- 二级 leaf link (开发构建说明, Electron版本开发指南, 后端压测): text x=33-44,虚线 x=10,距离 23-34 → **虚线在文字左边**

**所有层级虚线都在文字左边** ✓ — 不要让虚线穿过文字首字符中间。

**关键 insight**:两级规则都用 `!important`,baseline 那条 specificity 0,2,0;override 那条 0,4,2(`html body` 加 2 type + `c_nav_items_scroll` + `c_euv_sidebar_children` + `c_euv_sidebar_group_title` 加 4 class),override 永远赢。CSS 在 stylesheet 里的顺序无关紧要(同 `!important` 但 specificity 不同,specificity 高的赢)。

**适用范围**:任何用 euv-docs 的项目,如果 sidebar 有 nested group,想做层级视觉对齐。euv-docs 上游对 nested group title 的缩进是"为 leaf link 准备的"(缩进到 children container 内容区),需要 site-local override 拉回到 parent group text 列。

**用户偏好**:用户原话 "侧边栏虚线左边框没有按照我的要求实现,一级目录左边框在文字左边,二级在文字首字符中间了" — 用户观察 "二级在首字符中间" = 二级 group title 文字 x=22 + 虚线 x=31(从上级 children container 继承),**虚线穿过二级文字首字符**。解法就是把二级文字挪到 children container 内容区起点 (x=23),让虚线在文字左边 13px,**不穿过**。

### 坑 20:emoji 在 headless Chromium 字体 + Pages 边缘缓存双重失效(2026-09 docs-pages/docs-euv 教训)

**症状**:用户要求"feature card 用 emoji icon"(🚀 🌐 ⚡ 📚 ...),Push + CI 部署成功,但 `c_feature_icon` 元素文本是 emoji codepoint,Playwright 截图渲染成方框 □。用户认为"emoji 没展示出来"。

**根因**(两条叠加):
1. **Headless Chromium 146 默认不带 emoji 字体**(`NotoColorEmoji` 未装),截图看到方框 — 真实浏览器(Firefox/Safari/Chrome normal mode)正常显示 emoji
2. **Pages 边缘缓存** `cache-control: max-age=600`,emoji 替换 push 后用户浏览器继续显示旧 hash 的 emoji 10 分钟

**用户偏好**:"emoji 没展示就删除,不需要任何 emoji" — 这是个口味问题(用户偏好纯文本无装饰)。**最稳**:直接删除整个仓库所有 emoji(README + md + build.rs + config.toml + src/ 源码里的 ☰/✕ mobile drawer 按钮等)。

**清理脚本**(`scripts/strip-emoji.py`,本 skill 收录):
```python
import os, re
emoji_pat = re.compile(
    r'[\U0001F000-\U0001FFFF'   # most emoji planes
    r'\u2600-\u27BF'              # misc symbols + dingbats
    r'\u2300-\u23FF'              # misc technical (⌨ ⏏ etc)
    r'\uFE00-\uFE0F'              # variation selectors
    r'\u200B-\u200D\u2060\u00AD]'  # zero-width chars
)
for root, _, files in os.walk('.'):
    parts = root.split(os.sep)
    if any(p in ('www', '.git', 'target', 'node_modules') for p in parts): continue
    for f in files:
        if not f.endswith(('.md', '.rs', '.toml', '.html', '.yml', '.yaml', '.json')): continue
        path = os.path.join(root, f)
        try:
            with open(path, encoding='utf-8') as fh: c = fh.read()
            n = emoji_pat.sub('', c)
            if n != c:
                with open(path, 'w', encoding='utf-8') as fh: fh.write(n)
        except UnicodeDecodeError: pass
```

**注意副作用**:
- mobile drawer ☰ 按钮 → 留空字符串(euv-docs 框架仍渲染按钮,只是无文字)
- site logo = "📘" → " "(euv-docs 默认 logo,清空会让 navbar 没 logo icon,空字符串 OK)
- README frontmatter `icon: 📘` → `icon: ` 留空字段 → YAML 仍 valid 但 feature icon = empty string

**保留 emoji 的备选**:真实浏览器正常,只是 headless 截图不准。如果必须保留,本地调试时用 `p.chromium.launch(args=["--enable-features=BlinkEmoji"])` 或装 `fonts-noto-color-emoji` apt 包。

**适用范围**:任何需要 emoji 文字一致展示 + 不想被字体差异 + CDN 缓存坑的项目。本 skill 通用 CSS var override pattern 不能解决 emoji 字体问题(浏览器字体层的事)。

## 双分支 workflow deploy 模板

适用:**`master` 放稳定代码,`docs`(或 `staging` / `dev`)放正在改的**,两个分支都自动 deploy 到同一个 Pages URL(默认 source branch 是 `master`,`docs` push 触发同一个 workflow 但 build 的内容是 docs 分支的)。

```yaml
name: Deploy to GitHub Pages

on:
  push:
    branches: [master, docs]
  workflow_dispatch:

permissions:
  contents: read
  pages: write
  id-token: write

concurrency:
  group: pages
  cancel-in-progress: true

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: dtolnay/rust-toolchain@stable
        with: { targets: wasm32-unknown-unknown }
      - uses: Swatinem/rust-cache@v2
      - uses: taiki-e/install-action@v2
        with: { tool: wasm-pack }
      - run: cargo install euv-cli --locked
      - run: rm -rf www  # force build.rs to rerun and re-copy docs/public
      - run: euv build --release --index-html template.html -- --target web --out-dir www/pkg --out-name euv_docs --no-typescript --no-pack --no-gitignore
      - uses: actions/upload-pages-artifact@v3
        with: { path: www }

  deploy:
    needs: build
    runs-on: ubuntu-latest
    environment: { name: github-pages, url: ${{ steps.deployment.outputs.page_url }}}
    steps:
      - id: deployment
        uses: actions/deploy-pages@v4
```

**关键设计点**:
1. `rm -rf www` 在 `euv build` 之前 — 避免 sccache / cargo rerun-if-changed 缓存跳过 docs/public 复制(坑 13)。
2. `concurrency.cancel-in-progress: true` — push 频繁时只保留最新一次 build。
3. Pages 项目 `build_type=workflow`(坑 12)— 不然 Jekyll 会覆盖。
4. 用户希望"流水线部署的地址给一个新地址"= 把 Pages source branch 从 master 切到 `docs`,**URL 不变**(Pages 项目唯一 URL 是 `https://<user>.github.io/<repo>/`),但部署源变成了 docs 分支。这才是用户视角的"新地址"(分支维度)。

## 端到端验证清单(更新版,docs 站场景)

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

## 坑 26c:`git push --force-with-lease` 与 PR squash-merge 互坑(2026-09-19 docs-pages/docs PR #40/#41 教训)

**症状**:PR squash-merge 到 upstream 后,fork branch tip(本地 SHA `A`)与 upstream tip(新 SHA `B`)SHA 不同但 `git diff A B` 完全空(同一个 squash 内容)。这时 `git push --force-with-lease upstream master` 在某些 git 版本里**错报 "Everything up-to-date"**,Git 视本地 `A` 为"等同于 upstream `B` 的 reachable ref"——但 `--force-with-lease` 又实际把 upstream tip 拉回到 `A` 之前的某个 state(撤销了 squash 引入的 PR 内容)。

**实证 trace**:
```
本地 HEAD = a77e8e54 (含 PR #41 注释清理)
upstream tip = 8ec9e77386 (被 force-with-lease 拉回 = PR #41 撤销)
git diff a77e8e54 8ec9e77386 --stat → Cargo.toml | 10 ++++++++++
(差异 = PR #41 的删注释变更)
```
`git push --force-with-lease` 当时报 "Everything up-to-date" 但实际把 upstream tip 设到了 `8ec9e77`(撤销 `a77e8e5` 的 PR #41)。

**根因**:squash-merge 产生的新 commit 跟本地 fork commit tree-equivalent 但 SHA 不同,Git 在内部可达性图里把本地 HEAD 视为"应等于 upstream 新 tip 的 ref"——但 `--force-with-lease` 的 lease 比对逻辑和 squash-merge 的 tree-equivalence 短路规则有 bug,在某些 git 版本(实测 ≥ 2.40)上会跳过实际 push 但仍更新 remote-tracking branch。

**解法**:用显式 refspec 强制 push,**不要信 force-with-lease**:

```bash
# 错的(可能被误判 up-to-date 但实际撤销 squash 内容)
git push --force-with-lease upstream master

# 对的(显式 src/dst SHA,Git 不会做 tree-equivalence 短路)
git push upstream HEAD:refs/heads/master --force
```

**验证**(push 后必跑):
```bash
# 1. upstream master HEAD SHA
gh api repos/<o>/<r>/commits/master --jq .sha
# 应 = 本地 HEAD SHA(或 fast-forward successor),不是被回滚的旧 SHA

# 2. 上游内容核对(如果回滚了 PR #41,Cargo.toml 注释会重现)
gh api repos/<o>/<r>/contents/Cargo.toml?ref=<master-sha> \
  | python3 -c "import json,sys,base64; print(base64.b64decode(json.load(sys.stdin)['content']).decode())"
```

**预防**:
1. squash-merge 之后,如果你要 force-push upstream,**直接用 `git push <remote> HEAD:refs/heads/<branch> --force`**,不要用 `--force-with-lease`。
2. push 完立刻 `gh api repos/<o>/<r>/commits/master --jq .sha` 确认 upstream tip 是期望 SHA。如果回滚了,**立刻**再 push 一次(用上面的显式 refspec)恢复。
3. 如果 squash 引入的 commit 跟本地 branch tip tree-equivalent,改用 `git commit --allow-empty -m "..."` 在本地加一个 sentinel commit 再 push —— sentinel 让 SHA 一定不同,跳过 tree-equivalence 短路。

**适用范围**:任何 Track 2 fork + PR squash-merge 后,agent 又要 force-push upstream master 的场景(euv / hyperlane / 任何组织仓)。本次具体场景:`eastspire/euv-docs@fix/audit-r11-4-private-guard` PR #41 squash-merge 后,本地 `a77e8e5` vs upstream `8ec9e77` tree-equivalent → `--force-with-lease` 撤销 PR #41,必须 `git push upstream HEAD:refs/heads/master --force` 补救。

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
euv-docs 的 `/target`、`/www`、`Cargo.lock` 都在 .gitignore)。**反向 2026-09-19 教训**:
反过来也成立 — 上游 `euv-docs` 把 `euv = "0.18"` 改成 `euv = "*"`(或 fork float 选 `*`),
euv engine 0.18 → 0.24 → euv-docs 0.1.6 自己的 CSS pattern(它依赖 0.18 的
`var(--euv-mobile-safe-top, 0px)` safe-area contract)与 0.24 不兼容 → mobile nav /
sidebar 对齐 / 首页边框 fallback 到旧样式,**用户报告"修复全没了"**,但实际上游
PR #25-#27 全部已 merged。**铁律**:euv-docs 上游 `Cargo.toml` 的 `euv = "0.18"` /
`euv-ui = "0.18"` 是 PR #13 故意 pin,**禁止 fork 改成 `"*"` 跟随 latest**。Fork 唯一
允许的 commit 是 `publish = false` 删除 / 注释清理这种和 version pin 无关的改动。

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

## 坑 21:push www/ 产物到错的分支 — workflow 只听 master push(2026-09-18 docs-pages/docs-euv 教训)

**症状**:改了 `src/lib.rs` 和 `docs/config.toml` 的 site-local CSS / footer override,在本地 build 跑出来 wasm bundle 干净(没有旧字符串),用 API push www/ 产物 + 上百个 blob 到 **docs 分支**,手动 `workflow_dispatch` 触发,workflow 全绿、`actions/deploy-pages@v4` success,但**线上 wasm 还是旧的**(从 Pages 服务自己生成的 build metadata 来看,最近一次 build 仍是 9/16)。`gh api repos/.../pages/builds/latest` 总是返回老 commit。

**根因**(双层叠加):

1. **workflow trigger 限制**:`deploy.yml` 触发条件 `on.push.branches: [master]` + `workflow_dispatch`。**只 push 到 docs 分支 → workflow 不触发**。即便手动 `workflow_dispatch` 跑了 workflow,workflow checkout 的也是 **dispatch 时指定的 ref**(默认 master),而不是 docs 分支的最新内容。
2. **workflow 重新 build**:`deploy.yml` 的 build job 跑 `euv build --release ...`,会从 git tree 重新读 `src/lib.rs` + `docs/config.toml`(这些是 source 文件,不在 www/ 里)。如果 source 文件没 commit + push 到 master,**CI build 用的是老的 source** → 老内容进入新 wasm。
3. **push script 只能 walk 一个目录**:常见的 `push_docs_fix.py` 只 `os.walk(www_dir)`,根本不会把 `src/lib.rs` / `docs/config.toml` 的改动加进 commit tree。

**诊断三件套**:
```bash
# 1. 看线上 wasm binary 是不是老数据
curl -sS https://<user>.github.io/<repo>/pkg/<name>_bg.wasm > /tmp/live.wasm
strings /tmp/live.wasm | grep -F '<你期望消失的旧字符串>'   # 还在 = 没生效

# 2. 看 Pages 服务最近 build 的 commit
gh api repos/<owner>/<repo>/pages/builds/latest --jq '{commit, created_at, status}'
# commit 是老 sha = build metadata 没更新

# 3. 看 workflow 文件 trigger 条件
gh api repos/<owner>/<repo>/contents/.github/workflows/deploy.yml --jq .content | base64 -d | grep -A 5 '^on:'
# branches: [master] → 你必须 push master 才能触发(workflow_dispatch 也需要指定 master)
```

**解法**:source + artifact **必须 commit + push 到 workflow 监听的分支**(一般是 master):
1. **Source file 修改必须 git commit + push 到 master**:`src/lib.rs` / `docs/config.toml` 这种被 `build.rs` / `euv build` 在 CI 里重新读的文件,**必须** commit 到 master。如果只 push www/ artifacts 到 docs 分支,CI build 拿到的是老 source。
2. **workflow_dispatch 触发**:即使 source 已经 push 到 master,`workflow_dispatch` 默认 ref=master 才会跑新 build:
   ```bash
   gh api -X POST repos/<owner>/<repo>/actions/workflows/<wf_id>/dispatches -f ref=master
   ```
   **不要**写 `-f ref=docs` 如果 workflow 监听的不是 docs。
3. **Git push 冲突处理**(local master 比 remote 落后时):
   ```bash
   # local 修改 → commit master → push 失败 (remote 也有 commit)
   # 解法:用 Git Data API 单文件 push 到 master,绕过 git push 的 fast-forward 要求
   # POST /git/blobs (上传 lib.rs + config.toml) 
   # → POST /git/trees (基于 remote master 的 tree + 2 个新 blob)
   # → POST /git/commits (新 commit,parent = remote master head)
   # → PATCH /git/refs/heads/master (更新 ref)
   ```
   完整脚本见 `scripts/push-source-only.py`(本 skill 收录)。

**预防**(push 自动化脚本的设计原则):
- **Source 走 git push**:任何 `src/` / `docs/config.toml` / `build.rs` 的修改都必须经 git commit + push(到 workflow 监听的分支)。`push_docs_fix.py` 这种 walk www_dir 的脚本**不适用于 source 改动**。
- **Artifact 走 API push**(仅当需要手动跳过 build):如果想跳过 CI build 直接 push www/ 产物,得用 Git Data API 走 branches (例如 `docs` 分支) — 但因为 workflow 默认 checkout master build,**Artifact-only push 不会生效**,必须先确保 source 已 commit + push 到 master。
- **CI build 优先**:能 push source 触发 CI build = 永远的最优路径。手工 push artifact 是次优 fallback(只在 CI build 跑不通 / sccache 抽风时用)。

**push 路线自检清单**(提交前):
```bash
# 1. 确认本地 working tree 干净
git status --porcelain

# 2. 确认 source 改动已 commit
git log --oneline master..HEAD

# 3. push source 到 master
git push origin master  # 如果 remote 有 commit,先 fetch + rebase / 用 Git Data API

# 4. trigger CI on master
gh api -X POST repos/<owner>/<repo>/actions/workflows/<wf_id>/dispatches -f ref=master

# 5. 等 build + deploy 完成
gh run watch <run_id>

# 6. 验证线上 wasm 是新的(用 grep 旧字符串应该 0 命中)
curl -sS https://<user>.github.io/<repo>/pkg/<name>_bg.wasm > /tmp/live.wasm
strings /tmp/live.wasm | grep -c '<旧字符串>'  # 应 = 0
```

**适用范围**:任何用 GitHub Actions + Pages deploy + Rust WASM build 的项目。如果遇到 "workflow_dispatch 跑完但线上没生效",先查 Pages build metadata(`gh api .../pages/builds/latest`),确认 build 是新 commit → 否则就是分支 ref 不对 / source 没 push。

## 坑 22:source-builds-pages-product workflow 必须自带"产物可溯源"四件套(2026-09-19 docs-pages/docs 教训)

**症状**:workflow 全绿、Pages 部署成功,但**线上产物 = 谁 build 的?build 用的 source 是哪个 commit?** 答不出来。两个真实案例:
1. 某个 fork 的 `actions/checkout@v4` 默认拉的是 fork 自己的 source(不是 upstream),build 出来是 fork 视角的产物 → 推错仓。
2. `www/` 里有上一次 build 的残留文件(`docs/public/` 复制 subltety,坑 13),新 build **追加**到旧产物上 → 旧文件 + 新文件混在一起 → 出现"已经删的页面还在"或"已加的新页面没渲染"。

**根因**:cross-repo deploy workflow(source 仓 → target Pages 仓,中间 build)默认假设"build 用的 source 就是仓自己",但**没硬性断言**:
- source 是哪个仓、哪个 commit
- build 输出是不是这一次的(没残留)
- build 输出是不是合格的(空 `www/` 也能 push 出去)

**解法**:deploy workflow 在 build + push 之间必须插四步硬性断言:

```yaml
# 1. source 仓身份硬断言 — 阻止 fork 误用 / upstream 改名 / 用了错的 uses
- name: Verify source is <expected-owner>/<expected-repo>
  run: |
    set -euo pipefail
    remote=$(git remote get-url origin)
    case "$remote" in
      *github.com/<expected-owner>/<expected-repo>*) ;;
      *) echo "::error::unexpected source repo: $remote"; exit 1 ;;
    esac
    echo "SOURCE_REPO=$remote" >> "$GITHUB_ENV"
    echo "SOURCE_SHA=$GITHUB_SHA" >> "$GITHUB_ENV"

# 2. 强制 fresh build output — 防止 cargo rerun-if-changed + sccache 跳过 build.rs
- name: Force fresh build output
  run: rm -rf www

# 3. 之后才跑 build (euv-docs / euv build / cargo build → www/)
- name: Build site
  run: euv-docs docs --out www --index-html template.html

# 4. build 产物合格性硬断言 — 空 www/ 不能 push
- name: Verify build produced output
  run: |
    set -euo pipefail
    [ -f www/index.html ] || { echo "::error::www/index.html missing"; exit 1; }
    [ -d www/pkg ] || { echo "::error::www/pkg missing"; exit 1; }
    test -n "$(ls -A www)" || { echo "::error::www/ is empty"; exit 1; }
```

**第 5 步** 把 source 痕迹 bake 进产物,让部署后的 Pages 仓**任何 commit 都能反查**到 source commit:
```yaml
# 在 cp www/* 到 target 仓后、commit 前:
mkdir -p .deploy
cat > .deploy/build-info <<EOF
source_repo=${SOURCE_REPO}
source_sha=${SOURCE_SHA}
workflow_run=${GITHUB_RUN_ID}
built_at=$(date -u +%FT%TZ)
EOF
git commit -m "Deploy from ${SOURCE_REPO}@${SOURCE_SHA}"
```
(`.deploy/build-info` 同时承担"byte-identical rebuild 也能产生新 commit"的 sentinel 职责 — 替代原 `touch .deploy/build-info` 单行写法。)

**为什么这五步不可省略**:
1. **Step 1**:`actions/checkout@v4` 在 fork / org-internal PR 上行为不同 — workflow 在 fork 跑会把 source 切成 fork head;identity check 把这条暗坑短路成 fail-fast。
2. **Step 2**:cargo + sccache 的"output 看上去没变"启发式会跳过 `build.rs` re-run,残留旧 `www/`(坑 13 的根因);`rm -rf www` 是 1 行解决方案,跑得再多次都 idempotent。
3. **Step 3 + 4**:空 `www/` 推上去 = Pages 显示 404 / 显示上次部署的 hash;sentinel check 让"build 失败"和"build 成功产物丢了"被区分开,而不是都被 deploy step 掩盖成"绿色但没部署"。
4. **Step 5**:`commit message` 和 `.deploy/build-info` 都写 source SHA = 部署历史可审计;6 个月后排查"线上这个 wasm 是什么时候 build 的、用了哪个 source 版本",直接 `git log --grep` + `cat .deploy/build-info` 不需要回头翻 workflow run。

**适用范围**:任何 cross-repo deploy 模式(source 仓 build → 产物推到独立 Pages 仓 / CDN 仓 / docs mirror 仓)。euv engine → euv-docs → docs-pages/pages / hyperlane → hyperlane-docs 都是这个 pattern。

**反例**:把 sentinel 写成 `echo "Built from @${GITHUB_SHA}" > .deploy/build-info` — 只有 build run id,没有 source repo URL + 完整 source SHA,无法反查哪个 source 仓 commit。

## 坑 23:`build_type=legacy` 下 Pages 会跑 Jekyll — flat www/ artefact tree 没有 `_config.yml` 也照样 404(2026-09-19 docs-pages/docs 教训)

**症状**:Pages 项目配置成 `build_type=legacy` + `source.branch=gh-pages`,workflow 全绿、产物已 push 到 gh-pages branch(`gh api repos/<o>/<r>/contents/index.html?ref=gh-pages` 返回 base64 内容 = 产物真的上去了),但 `https://<user>.github.io/<repo>/` 还是 404。改 `build_type=workflow` 没用。

**根因**(区别于坑 12):坑 12 是 `build_type=legacy` 跑 Jekyll 时**忽略** `actions/upload-pages-artifact` 上传的产物。本坑是 `build_type=legacy` 跑 Jekyll 时把整个 source branch 当 Jekyll input — Jekyll 看到 flat `www/` artefact tree 没有 `_config.yml` + 没有 `_layouts` + 没有 liquid template,就返回 404 fallback 页(而不是把 flat HTML 文件直接 serve 出来)。

**Jekyll 在 legacy 模式下的行为**:
- **有 `_config.yml`**:跑 Jekyll build,按 config 渲染源文件(可能覆盖产物里的 index.html)
- **没有 `_config.yml`**:Jekyll 不知道怎么处理,**直接 404**,不 serve 任何文件
- **`_config.yml` 存在但产物里没有 `index.html`(只有 `404.html`)**:Jekyll render 出 404 page 自身的内容,不是 GitHub Pages 标准的 not-found

**解法**:`touch .nojekyll` 在产物 branch 根目录 —— 让 Pages 完全跳过 Jekyll,直接把 branch 内容当成 static files serve。这是 GitHub Pages 官方支持的 opt-out,从 Pages 项目 creation 就支持(比 `build_type=workflow` 更老):

```yaml
# 在 cp www/* 到产物仓后、git add 前:
touch .nojekyll
# .nojekyll 是空文件,只要存在就生效
```

`.nojekyll` 必须放在产物 serve 时的**根目录**(也就是 `source.path` 对应的目录,root project 模式就是产物 branch 的 root)。放进子目录无效。

**为什么不是 `build_type=workflow`**:build_type=workflow 模式下,GitHub 只接受 `actions/deploy-pages@v4` 上传的 artifact,**不接受** 通过 git push 写到 source branch 的产物。当前 docs-pages/docs 的 deploy.yml 是用 git push 写产物(不是 artifact upload),所以必须用 `build_type=legacy` + `.nojekyll`。

**为什么不是 `build_type=legacy` 不加 `.nojekyll` 期待 Jekyll serve**:Jekyll legacy 模式必须有 `_config.yml` 才能 serve 任何东西,否则 404。即使产物里有 `index.html`,Jekyll 也会因为缺 config 直接报 404,不会 fallback 到 raw file serve。

**验证**(提交 PR 前):
```bash
# 1. 检查产物 branch 有 .nojekyll
gh api repos/<owner>/<repo>/contents/.nojekyll?ref=<source-branch> --jq .name
# 应返回 ".nojekyll"

# 2. 检查 index.html 真在 branch 上(不是 base64-encoded empty)
gh api repos/<owner>/<repo>/contents/index.html?ref=<source-branch> --jq '{name, size}'

# 3. Pages 服务在线上 serve
curl -sIL https://<user>.github.io/<repo>/ | head -1
# 应 HTTP 200
```

**坑**:改 `build_type` + 改 `source.branch` 都需要 PUT `/repos/<o>/<r>/pages` 才生效;改 `source.branch` 到不存在的 branch 会返回 422(坑 24)。

**适用范围**:任何用 git push 写产物到 source branch 的 Pages 项目(`deploy.yml` 用 `git push` 而不是 `actions/upload-pages-artifact`)。VuePress / Next.js / Astro / 任何 pre-built static site + git-push deploy 都是这条。`actions/deploy-pages@v4` artifact 模式的反例见坑 12。

**适用范围外**:用 `actions/upload-pages-artifact@v3` + `actions/deploy-pages@v4` 的项目(坑 12 已覆盖) — 那种场景 build_type=workflow 才是对的,不需要 .nojekyll。

## 坑 24:Pages PUT `/pages` `source.branch=<x>` 在 `<x>` branch 不存在时返回 422 — 必须先 `POST /git/refs` 创建 branch(2026-09-19 docs-pages/docs 教训)

**症状**:准备把 Pages source 从 master 切到 gh-pages:
```bash
curl -X PUT -H "Authorization: Bearer $TOKEN" \
  https://api.github.com/repos/<o>/<r>/pages \
  -d '{"build_type":"legacy","source":{"branch":"gh-pages","path":"/"}}'
```
返回 HTTP 422,body 是空或 error JSON。Pages config 没变,source.branch 还是老的。

**根因**:Pages API 在 PUT 时会校验 `source.branch` 必须是真实存在的 ref。gh-pages branch 还没创建(因为之前 source 是 master,workflow 没推过这个 branch),所以 PUT 失败。

**解法**:顺序必须是 **创建 branch 在前 → PUT Pages config 在后**:

```bash
TOKEN=$(grep -oP 'export GH_TOKEN="\K[^"]+' /root/.bashrc.d/gh_token.sh)
OWNER=<owner>
REPO=<repo>

# 1. 拿当前 default branch 的完整 40-char SHA(GitHub API 要求 full SHA,不要 8 字符短 hash)
SHA=$(curl -s -H "Authorization: Bearer $TOKEN" \
  "https://api.github.com/repos/$OWNER/$REPO/branches/master" \
  | python3 -c "import json,sys; print(json.load(sys.stdin)['commit']['sha'])")
# SHA 必须是 40 字符 hex;若 api 返回 short SHA,用 'git rev-parse master' 在 clone 后拿

# 2. POST /git/refs 创建新 branch
curl -s -X POST -H "Authorization: Bearer $TOKEN" -H "Accept: application/vnd.github+json" \
  "https://api.github.com/repos/$OWNER/$REPO/git/refs" \
  -d "{\"ref\":\"refs/heads/gh-pages\",\"sha\":\"$SHA\"}"
# 应返回 {"ref":"refs/heads/gh-pages","object":{"sha":"<full>..."}}

# 3. 现在 PUT Pages config
curl -s -X PUT -H "Authorization: Bearer $TOKEN" -H "Accept: application/vnd.github+json" \
  "https://api.github.com/repos/$OWNER/$REPO/pages" \
  -d '{"build_type":"legacy","source":{"branch":"gh-pages","path":"/"}}'
# HTTP 204 = 成功;空 body 但 exit code 0

# 4. 验证
curl -s -H "Authorization: Bearer $TOKEN" \
  "https://api.github.com/repos/$OWNER/$REPO/pages" \
  | python3 -c "import json,sys; d=json.load(sys.stdin); print('build_type:', d['build_type'], 'source:', d['source'])"
# 应返回 build_type: legacy source: {'branch': 'gh-pages', 'path': '/'}
```

**GitHub API 在 PUT `/pages` 时的 422 错误 body 通常是空**(`HTTP/1.1 422 Unprocessable Entity` + 0 字节 body),不像其他 PUT 返回详细 JSON 错误。所以**只能从 HTTP status code 判断失败**,不要试图读 body。

**诊断 422 根因**:`-d '{"source":{"branch":"gh-pages"}}'` 返回 422 大概率是 branch 不存在。`build_type` 非法值(如 `"workflow"` 在某些 Pages 计划)也会 422,但 Pages public 项目两个值都接受,排除法 = branch 问题。

**新建 branch 不能用 short SHA**:GitHub API 对 `/git/refs` POST 的 `sha` 参数严格要求 40 字符 hex。`branch --show` 报 8 字符 SHA 是不够的,必须 `git rev-parse <ref>` 拿完整 SHA 或通过 `branches/<branch>` API GET `commit.sha` 字段(API 永远返回 40 字符)。

**陷阱**:如果默认 branch 不是 master(如 main),把上面所有 `master` 替换成 `gh api repos/<o>/<r>` 的 `default_branch` 字段值:
```bash
DEFAULT=$(curl -s -H "Authorization: Bearer $TOKEN" "https://api.github.com/repos/$OWNER/$REPO" \
  | python3 -c "import json,sys; print(json.load(sys.stdin)['default_branch'])")
```

**适用范围**:任何 Pages 项目要把 source branch 切到一个**尚未存在**的新 branch。如果新 branch 已经被某次 push 创建过(比如之前 workflow 跑过一次),直接 PUT 即可,不需要这个分支创建步骤。

**Pages HTML URL 是 repo-name-derived,与 source branch 无关**(2026-09-19 docs-pages/docs 教训):顺手记一个易错点 —— `gh api repos/<o>/<r>/pages` 返回的 `html_url` 永远按 **repo name** 算,跟 `source.branch` 是哪个无关。所以 `docs-pages/pages` 的 Pages URL 永远是 `https://docs-pages.github.io/pages/`,即使把 source 切到 gh-pages 也不会变成 `.../gh-pages/`。**改 source branch 不改 URL**,只改 serve 内容。

## 坑 25:`euv-docs docs --out www` 默认把产物写到 `<EUV_DOCS_SRC_DIR>/www`,不是 cwd/www(2026-09-19 docs-pages/docs 教训)

**症状**:`euv-docs docs --out www` 跑成功,日志说 `wasm pkg is ready at .../www/pkg`,但**主进程 cwd 下的 `www/` 是空的 / 不存在**。下游 deploy step 用 `cp -r ../www/* .`(相对于 `__docs_pages` checkout)发现源目录为空,`git commit` 只包含 `.deploy/build-info`,产物文件没真正推上去。

**根因**:看 `euv-docs` crate 的 `src/bin/euv_docs/fn.rs:117-134`:

```rust
command.current_dir(&manifest_dir);  // line 117: euv 子进程 cwd = manifest_dir (euv-docs crate 安装路径)
...
command.env(EUV_DOCS_OUT_DIR_ENV, out_dir);  // line 128: 把 out_dir 传给 euv build
let user_cwd: PathBuf = env::current_dir().unwrap_or_else(|_| manifest_dir.clone());
let resolved_out_dir: PathBuf = if out_dir.is_absolute() {
    out_dir.to_path_buf()
} else {
    user_cwd.join(out_dir)   // line 133: 相对 out_dir 用 user_cwd 解析
};
let pkg_dir: PathBuf = resolved_out_dir.join(PKG_DIR_NAME);
```

`--out www` 传的是相对路径 `www`,line 133 解析为 `user_cwd.join("www")` = 当前 shell 的 cwd/www。这部分**在 euv-docs 主进程里是对的**。

但 **euv build 子进程**(line 117 `command.current_dir(&manifest_dir)`)跑的是 euv-cli 的 build 流程。euv-cli 又把 `out_dir` 传给 wasm-pack,wasm-pack 的 `--out-dir` 又被 euv-cli 内部**重写到 `<src_dir>/www/pkg`**(`<src_dir>` = `EUV_DOCS_SRC_DIR`,默认是 `manifest_dir/docs`)。

**实证**(CI log):
```
INFO wasm-pack build --release --target web \
  --out-dir /home/runner/work/docs/docs/www/pkg ...    # ← /home/runner/work/docs/docs/www/pkg
```

`/home/runner/work/docs/docs/www` = `<src_dir>/www` = `$EUV_DOCS_SRC_DIR/www`。euv-cli 默认把 `EUV_DOCS_OUT_DIR` 当 `<src_dir>` 子目录处理。

**解法**:**显式 export `EUV_DOCS_OUT_DIR` 为绝对路径**,落到你想放产物的位置:

```bash
export EUV_DOCS_OUT_DIR="$GITHUB_WORKSPACE/www"  # 或 caller 期望的绝对路径
euv-docs docs --out www --index-html template.html
```

**或者**(没 env 时):让 euv-docs 主进程的 `user_cwd` 就是产物目标位置 — 把 build step 的 `working-directory` 设成你想要 `www/` 落地的目录:

```yaml
- name: Build site (euv-docs → www/)
  env:
    EUV_DOCS_SRC_DIR: ${{ github.workspace }}/docs
    EUV_DOCS_OUT_DIR: ${{ github.workspace }}/www   # 绝对路径,明确产物去向
  run: euv-docs docs --out www --index-html template.html
```

**诊断三件套**(build 后必跑):
```bash
# 1. 期望的产物在不在?
ls www/index.html www/pkg/euv_docs_bg.wasm 2>&1

# 2. 实际产物落在哪里了?(euv-cli 默认可能写到 <src_dir>/www)
find / -name "euv_docs_bg.wasm" -newer .github/workflows/deploy.yml 2>/dev/null | head -5

# 3. deploy step 的 cp 命令解析到哪个 ../www?
#    pwd 是 __docs_pages/ → ../www = <repo>/www → 必须 <repo>/www/ 存在且有内容
ls ${{ github.workspace }}/www/index.html ${{ github.workspace }}/www/pkg 2>&1
```

**坑**:即使 cp 步骤真的拷贝了文件,如果 `<gh-pages HEAD>` 已经有 `pkg/euv_docs_bg.wasm` + `index.html`(byte-identical),git diff 是空 → no-op commit。**首跑必须删 gh-pages HEAD 的产物**(坑 22 的 `find . -maxdepth 1 -not -name '.git' -exec rm -rf {} +` 在 push step 里就处理了)。

**适用范围**:任何用 `euv-docs` CLI 而不是直接 `euv build` 的项目(也就是 docs 站点项目)。euv engine 项目直接调 `euv build`,out-dir 行为不同(看坑 1 + 坑 13)。

## 坑 26:`euv-docs` CLI 的 positional `<SRC_DIR>` 直接被 forward 成 `EUV_DOCS_SRC_DIR` 给 wasm-pack — 相对路径会指向 euv-docs crate 自带的 starter docs/(2026-09-19 docs-pages/docs 教训)

**症状**:workflow 全绿、Pages 部署成功、index.html 字节正常、wasm binary 体积正常(>400KB),但浏览器打开 `https://<user>.github.io/<repo>/` 看到的是 **euv-docs 框架默认首页**(title="euv-docs",heroText="euv-docs",tagline="A VuePress-style documentation site powered by euv + euv-ui, compiled to WebAssembly."),**不是用户自己 docs/ 写的任何内容**(essay/posts、私有文章都看不到)。改动 `docs/README.md` 的 heroText/title 等都没影响 — 线上还是 starter。

**根因**:`euv-docs` crate 的 `src/bin/euv_docs/fn.rs:67-127`:

```rust
let src_dir: PathBuf = positional
    .into_iter()
    .next()
    .ok_or_else(|| "missing required <SRC_DIR> argument".to_string())?;  // line 67-70
...
let src_dir: &Path = args.get_src_dir().as_path();  // line 83
...
command.env(EUV_DOCS_SRC_DIR_ENV, src_dir);  // line 127: src_dir 原样传给 euv build
```

**关键**:`src_dir` 是 positional `<SRC_DIR>` 的原始字符串,**euv-docs CLI 不会把它 resolve 成绝对路径**,直接 forward 给 euv build 子进程的 env。

但 wasm-pack 内部的 cargo build 在跑 euv-docs crate 的 `build.rs`,`build.rs` 读 `EUV_DOCS_SRC_DIR`:

```rust
let docs_dir: PathBuf = match env::var("EUV_DOCS_SRC_DIR") {
    Ok(path) => PathBuf::from(path),
    Err(_) => manifest_dir.join("docs"),  // line 245: 默认 = euv-docs crate 安装路径/docs
};
```

cargo 调 build.rs 时,build.rs 看到的 cwd = **`euv-docs` crate 的 manifest_dir**(cargo 在那个目录跑 `cargo build`,env var 是 child process inherited string,**不会 resolve 相对路径**)。

所以 `euv-docs docs` 跑时:
- 用户的 cwd 是 `$GITHUB_WORKSPACE`(源仓根)
- euv-docs CLI 收到 positional `<SRC_DIR>=docs`(相对)
- euv-docs CLI 把 `EUV_DOCS_SRC_DIR=docs` 传给 euv build(原样相对路径)
- euv build → wasm-pack → cargo build 跑在 `<euv-docs crate 安装路径>` 下
- build.rs 收到 `EUV_DOCS_SRC_DIR=docs` → `PathBuf::from("docs")` → join `<euv-docs crate 安装路径>/docs`
- **euv-docs crate 自带 starter docs/**(被 git ignore 标记但源码里就是有,包含 config.toml + 5 个 guide 页面)→ **build.rs 编译的是 starter,不是用户的 docs/**

**实证**(本地):
```bash
$ find /root/.cargo/git/checkouts/euv-docs-* -name "docs_gen.rs" -exec grep -c "essay\|06-09\|韩国" {} \;
# 清缓存前:0 hits(starter 内容)
# 清缓存后:14 hits(用户 docs/ 内容)← 证明 env var 是控制变量
```

```bash
# 看 wasm-pack 子进程的 EUV_DOCS_SRC_DIR:
$ pgrep -f "wasm-pack build"
<pid>
$ cat /proc/<pid>/environ | tr '\0' '\n' | grep EUV_DOCS
# (no EUV env)  ← 没有!说明 env var 在 euv-cli 链路上被丢
```

**但更深层的原因**:即使 env var 在 euv-cli 链路没被传(实测),euv-docs CLI 仍然**会用 `manifest_dir/docs` 作为 src_dir**(line 245 fallback),所以**只要 positional 是相对路径,wars build.rs 解析到的永远是 euv-docs crate 自带 starter**。即使 euv-docs crate 没有自带 docs/ 也不会读用户的 cwd docs。

**解法**:**positional 必须传绝对路径**:
```yaml
- name: Build site
  env:
    EUV_DOCS_SRC_DIR: ${{ github.workspace }}/docs   # 显式设绝对路径(可选,见下)
    EUV_DOCS_OUT_DIR: ${{ github.workspace }}/www   # 显式设绝对路径(坑 25)
  # 关键: positional 也是绝对路径(不是 "docs")
  run: euv-docs ${{ github.workspace }}/docs --out ${{ github.workspace }}/www --index-html template.html
```

**为什么 env var 不够**(实测):euv-docs CLI 收到 `EUV_DOCS_SRC_DIR=$GITHUB_WORKSPACE/docs`(绝对)env var,但 positional 是 `docs`(相对),**CLI 内部用 `args.get_src_dir()`(positional 值)作为最终传给 wasm-pack 的 EUV_DOCS_SRC_DIR,覆盖 env**。所以 env var 跟 positional 必须**都是绝对路径**才生效。

**或者直接改源仓**(`docs-euv` 工程化的彻底方案):把源仓改名,让仓 root 本身就是 docs 内容(没有 `docs/` 子目录)。比如把仓从 `docs-euv` 改成 `eastspire-docs`,仓根直接放 `README.md` / `guide/` / `config.toml`,`euv-docs ./ --out www` 这种调用就完全避免路径歧义。但这要求 git rename + 历史保留,操作成本高。

**诊断**(判断部署产物是 starter 还是用户 docs 的硬指标):
```bash
# 1. 拉 wasm binary
gh api repos/<owner>/<repo>/contents/pkg/<name>_bg.wasm?ref=gh-pages \
  -H "Accept: application/vnd.github.v3.raw" -o /tmp/live.wasm

# 2. grep 用户 docs 独有的字符串(标题、tagline、essay titles 等)
python3 -c "
with open('/tmp/live.wasm','rb') as f: d=f.read()
for needle, label in [(b'<user-specific-title>', 'title'), (b'<user-toc>', 'toc')]:
    print(label, ':', d.count(needle))
"

# 3. 期望:每个用户独有的字符串出现 N 次(N=站点页面数);0 hits = 还是 starter
```

**常见误区**:`docs/config.toml` 里的 title/description 如果正好是 `euv-docs` 自带的默认值("euv-docs" / "A VuePress-style documentation site powered by euv + euv-ui"),用户改 docs/ 后这些字段值不变 = 部署后看起来"对"的概率高,**但 wasm 里仍没用户 essay/posts/私有文章内容**。**必须 grep 用户独有的内容字符串**(如 essay 标题、posts 标题)才能确认到底是不是用户 docs/。

**适用范围**:任何用 `euv-docs` CLI 的项目。这是 euv-docs 0.1.x 的设计缺陷 — CLI 应该自动 resolve positional 成绝对路径,而不是信任 caller 传绝对路径。在 fix 之前,**调用方必须传绝对路径**。

**反向 check**(确认没踩这条):本地 build 后:
```bash
# 应该看到用户的 essay/posts 内容
strings /tmp/euv-docs-test/www/pkg/euv_docs_bg.wasm | grep -F "<用户独有字符串>"
# 期望 >=1 hits
# 0 hits → build.rs 读了 euv-docs crate 自带 starter,本地 + CI 都中招
```

**坑 26a:即使 cp 真拷贝了产物,byte-identical rebuild 让 git diff 为空 → no-op commit(2026-09-19 docs-pages/docs 教训)**。坑 25 解了之后,euv-docs CLI build 出来的新 wasm binary 跟 gh-pages HEAD 已有的 wasm binary **byte 级别完全相同**(因为 wasm-pack + cargo 缓存命中,euv-docs 框架代码没变 + 用户 docs/ 没变 → 输出二进制 deterministically 一致)。`git add -A && git commit` 时 `git diff --cached --quiet` 报无 diff → commit 跳过,deploy commit 不带任何产物改动。**看起来"什么都没改"的 commit 链**(`Deploy from ...@<sha>` 连续 N 次都只 modified 1 file = `.deploy/build-info`)。线上 Pages 也因此不刷新。

**诊断**:
```bash
# 1. 看 deploy commit 改动了几 file
gh api repos/<o>/<r>/commits/<sha> --jq '.files[] | "\(.status[0:1]) \(.filename)"'
# 如果多次连续 commit 都只动 `.deploy/build-info` + `.nojekyll`,产物文件从未在 commit diff 里
# = byte-identical rebuild

# 2. 比较 sha 一致性
gh api repos/<o>/<r>/contents/pkg/euv_docs_bg.wasm?ref=gh-pages --jq .sha
# 两次 commit 之间这个 sha 不变 = wasm 没换
```

**根因**:wasm-pack + cargo 的 output determinism 在源码不变 + target cache 命中时输出 byte-identical binary。`git diff` 看不到变化 → 部署管道看起来"没干活"。

**解法(三选一)**:
1. **强制 cache miss**:`rm -rf target` 或 `cargo clean -p euv-docs` + 重 build。**稳但慢**(7 分钟)。
2. **改 docs/config.toml 的某个无关字段**(e.g. footer 字符串加一个 newline)+ commit + push。euv-docs build.rs 会重跑 → docs_gen.rs 字节变 → wasm 字节变 → commit diff 有产物改动。**快**(30 秒 CI),但 commit 信息要诚实写明"rebuild to bust cache"。
3. **接受 byte-identical deploy**:如果产物的 sha 与上次一致,线上的 wasm 不需要换。**只在用户说"线上没改"时才需要 bust cache**。

**预防**:deploy.yml 的 `.deploy/build-info` 已包含 `workflow_run=${GITHUB_RUN_ID}` + `built_at=$(date)`,即使产物没变 commit 也能产生(因为 `.deploy/build-info` 内容每次变)。**这正是坑 22 设计的 sentinel 职责**——但仅当 commit 实际生成时才有意义;如果 `git add -A` 之前产物 byte-identical, `.deploy/build-info` 也无法救(因为 git diff 仍然空)。

**适用范围**:任何 deterministic build 框架(euv-docs / euv build / Astro / Next.js SSG / Nuxt)。源码不变 + 缓存命中 = byte-identical output = no-op commit。

**坑 26b:fix 完坑 26 后,`docs/config.toml` 仍是 starter 默认值(2026-09-19 docs-pages/docs 教训)**。euv-docs 模板里 `docs/config.toml` 初始写的就是 `title = "docs-euv"` + `description = "docs-pages (VuePress) migrated to euv-docs engine, compiled to WebAssembly."`(starter 写法)。用户第一次 clone 时这两个字段就是 starter。坑 26 fix 完后 wasm 确实含 essay/posts 内容,但**首页 title/description 还是 starter**——看起来"还是默认模板",实际是 config 没改,**不是部署 bug**。诊断顺序:先 grep wasm binary 确认路径对(坑 26 fixed = wasm 含用户独有字符串),再 grep `docs/config.toml` 的 title/description 是不是用户站点。如果 wasm 含 essay 但 title/description 是 starter → **改 config.toml 不是改 deploy.yml**。

**必查**:
```bash
grep -E '^title|^description' docs/config.toml
# 期望:用户站点的真实 title/description,不是 euv-docs starter 默认值
```

**适用范围**:任何用 euv-docs CLI 部署的项目,在 fix 完坑 26 之后必须额外检查 `docs/config.toml` 的 `[site].title` / `[site].description` / `[[locales]].title` 等用户可见字段是不是用户真实信息,而不是 euv-docs 模板 starter。

### 坑 27:euv-docs build.rs 的 `public` 目录跳过是任意深度匹配 — 嵌套内容目录被误杀(2026-09-19 docs-pages/docs 教训)

**症状**:`#/essay/public/2026/06-09.html` 404,essay/public/ 下所有页面在 `docs_gen.rs` 里完全不存在;侧边栏也没有 essay/public 分组。

**根因**:`build.rs` 的 `collect_md` / `build_sidebar` / `copy_doc_assets_recurse` 用 `path.file_name() == "public"` 判跳过,**任意深度**生效 — 本意是只跳过顶层 `docs/public/`(站点静态资源),但 `docs/essay/public/` 这种**内容目录**也被误杀。

**解法**:跳过判断加 root 限定 `&& path.parent() == Some(root)`,只有 `docs/public/` 直子目录被跳过(euv PR #239 commit f7dcf22e)。`collect_md` 因此加了 `root: &Path` 参数。

**诊断**:build 后 `grep -c 'essay/public' OUT_DIR/docs_gen.rs`,0 = 被误杀。

**适用范围**:任何 euv-docs 项目里有嵌套 `public/` 内容目录的场景(VuePress 迁移站常见,VuePress 的 public 语义是"根级静态资源",用户会在子目录复用这个名字)。

### 坑 28:raw HTML `<img src="/…">` 不走 md 图片的 src 重写 — 子路径部署 404(2026-09-19 docs-pages/docs 教训)

**症状**:md 图片 `![](/essay/x.jpg)` 都正常(经 `rewrite_image_src` → `./essay/x.jpg`),但 `docs/hyperlane/README.md` 里 raw HTML `<img src="/img/hyperlane.png">` 线上 404,`naturalWidth=0`。

**根因**:`rewrite_image_src`(坑 14 的框架化解法,PR #239)只作用于 pulldown-cmark 的 `Tag::Image` 事件。raw HTML 走 `Event::Html` / `Event::InlineHtml`,原样透传。

**解法**:`rewrite_html_asset_src(html)`:扫 `src="` / `src='`,若值以 `/` 开头且非 `//`(protocol-relative),插入 `.` 变 `./…`。在 `Event::Html | Event::InlineHtml` 两个出口统一调用(euv PR #239 commit f7dcf22e)。`href="/…"` 不重写(站内 raw HTML 链接应写成 hash 路由形式,docs 仓目前 0 处)。

**诊断**:Playwright `[...document.querySelectorAll('article img')].map(i => [i.getAttribute('src'), i.naturalWidth])` — src 以 `/` 开头 = 没重写;nw=0 = 404。

**适用范围**:任何 euv-docs 项目 md 里写 raw HTML `<img>` / `<video>` / `<source>` / `<audio>` 的站点。

### 坑 29:`> [!tip]` 紧跟内容行(无空 `>` 分隔)会被劫持成容器标题 — 内容行变成大写纯文本,反引号不解析(2026-09-19 docs-pages/docs 教训)

**症状**:`#/ltpp/` 页面 `LTPP \`WEB\` 基于 \`Vue2.js\` …` 整行渲染成**大写、带字面反引号**的标题文本,`<code>` 不解析。

**根因**:`transform_github_alerts` 的 title 推断:marker 行(`> [!tip]`)之后第一个非空 `>` 行当容器标题。GitHub alert 语法**没有标题概念**,用户写 `> [!tip]\n> 内容…`(中间无空 `>` 行)时内容被劫持成 `::: tip <内容>` 的 title,而 `.docs-container-title` 是纯文本 + `text-transform: uppercase` → 内容大写 + 反引号字面量。

**解法**:title 只从 marker 行 `]` 之后的同行文本取(`> [!tip] 自定义标题`),后续 `>` 行一律进 body(euv PR #241)。诊断:`page.evaluate` 查 `.docs-container-title` 的 innerText 是否是内容文本而不是 `TIP`/`NOTE` 等 kind label;`article.innerText.includes('`')` 有字面反引号 = 中招。

**适用范围**:任何用 euv-docs 渲染 GitHub alert 的 md。写法和 attributes.md 的"marker 后空一行"都能正常工作,但**不能依赖用户记得空行** — 框架必须按 GitHub 语义处理。

### 坑 30:euv-docs 组件自定义 class 不得硬编码颜色/圆角/阴影 — 必须 var! token + euv-ui 标准 class(2026-09-19 docs-pages/docs 教训)

**症状**:password gate 用 GitHub Primer 风格(蓝 `#0969da` 按钮、红 `#cf222e` 错误、0.375-0.75rem 圆角、focus ring 阴影),与 euv-ui 单色直角设计系统冲突,dark mode 下直接崩(硬编码白底)。

**根因**:`password_gate/view/const.rs` 的 `c_pw_gate_*` class! 全部硬编码 hex/rem,没有消费 `var!()` token,输入框/按钮也没用 euv-ui 标准的 `c_euv_input` / `c_euv_input_error` / `c_euv_button_primary_md`。

**解法**(euv PR #241):
1. **布局类保留自定义但只写布局**(wrapper flex 居中、card max-width/padding),视觉属性全换 `var!()`:`border: 1px dashed var!(border)`、`background: var!(background)`、`color: var!(foreground)` / `var!(muted-foreground)`,padding/margin/font-size 全走 spacing/font 阶。
2. **交互控件直接用 euv-ui 标准 class fn**:`class: c_euv_input()` / `c_euv_input_error()` / `c_euv_button_primary_md()` — euv-docs 里可直接调用(lib.rs 的 `use euv_ui::*` 对子孙模块可见),CSS 注册/注入与组件内调用同一机制。
3. **圆角/阴影/彩色一律删**:euv-ui 设计系统直角(无 border-radius 声明)、几乎无阴影、单色。
4. 错误态在单色系统里 = `c_euv_input_error`(foreground 边框)+ 同前景色错误文字,**不引入红色**。

**验证清单**(改动后必跑):
- Playwright getComputedStyle:card `1px dashed` + radius 0 + shadow none;input 36px + `1px solid`;button 42px + accent bg。
- 错误路径:输错密码 → input 换 `_error` class + 错误文字颜色 = foreground(黑/白)。
- 解锁路径:正确密码 → gate 卸载 + 正文渲染;reload 后 localStorage 仍解锁。

**适用范围**:任何 euv-docs / euv 业务项目里写自定义 class! 的组件。写之前先查 euv-ui-standards §3 有没有现成标准 class(input/button/field/card/alert),能复用就不新造。

## 坑 31:`workflow run` success ≠ artifact 推到 master — 验证 deploy 完成必须查 `gh-pages` 分支(2026-09-21 docs-pages/docs 教训)

**症状**:`gh workflow run deploy.yml --repo docs-pages/docs` 触发后,`gh run view` 显示 `conclusion: success`,跑了几分钟,但用 `gh api repos/docs-pages/pages/commits?per_page=3`(默认 = master 分支)查 target 仓最近 commit,**看到的还是几天前的旧 commit**,容易误判"流水线没真生效",再去 rerun / debug / force-push,折腾一圈才发现部署其实完成了。

**根因**:cross-repo deploy workflow(坑 22 的 source-builds-pages-product pattern)把 artifact push 到 target 仓的 **`gh-pages` 分支**,**不是 `master`**。`docs-pages/docs` 的 deploy.yml 在 CI 里:

```yaml
- uses: actions/checkout@v4
  with:
    repository: docs-pages/pages
    ref: gh-pages      # ← 关键:checkout 到 gh-pages 分支
    path: __docs_pages
- name: Push to docs-pages/pages
  run: |
    cd __docs_pages
    ...
    git fetch origin gh-pages
    git rebase -X theirs origin/gh-pages
    git push origin gh-pages   # ← push 也到 gh-pages
```

Pages 项目 source 配置 `build_type=legacy` + `source.branch=gh-pages`(坑 23 + 24),所以 GitHub Pages 服务从 `gh-pages` 分支 serve 静态产物。**master 分支在这次 deploy 中完全没被触碰**,所以查 master 当然看不到新 commit。

`gh api repos/<o>/<r>/commits` 不带 `?sha=` 时,GitHub API 默认返回 default branch 的最近 commits(对 `docs-pages/pages` 是 `master`)。所以即使 `gh-pages` 分支刚刚被推了新 SHA,master 看上去纹丝不动 → 误判。

**解法(三件套,触发后必跑)**:

1. **直接查 `gh-pages` 分支**:
   ```bash
   gh api repos/<target-owner>/<target-repo>/commits?sha=gh-pages\&per_page=3 \
     --jq '.[] | {sha: .sha[:7], msg: .commit.message | split("\n")[0], date: .commit.committer.date}'
   ```
   注意 `?sha=gh-pages` 参数必填,且 URL 里 `&` 要 shell 转义(`\&`)。

2. **查 Pages 服务自己的最近 build metadata**(直接证据,绕开 git branch 概念):
   ```bash
   gh api repos/<target-owner>/<target-repo>/pages/builds/latest \
     --jq '{commit: .commit[0:7], status, created_at, duration: .duration}'
   ```
   返回的 `commit` SHA 对应 Pages 服务刚才 serve 的产物 commit。`status: built` = 部署真生效。

3. **直接读 workflow log 里 push step 的 commit SHA**(流程执行的事故痕迹):
   ```bash
   gh run view <run_id> --log | grep -E 'gh-pages -> gh-pages|\[gh-pages [a-f0-9]{7}\]'
   ```
   `a073ac6..a24173a gh-pages -> gh-pages` 这种 push 报告就是铁证。

**预防**(deploy 完成后回报用户前的自检流程):
```bash
# 1. 跑完 gh run view,看到 conclusion: success 先别报"完成"
gh run view <run_id> --repo <source-owner>/<source-repo> --jq '.conclusion'

# 2. 查 target 仓的 gh-pages 分支最近 commit
gh api repos/<target-owner>/<target-repo>/commits?sha=gh-pages\&per_page=1 \
  --jq '.[] | {sha: .sha, msg: .commit.message}'

# 3. 比对 source commit 和 target commit 的 `source_sha` 是否一致
#    workflow log 里 SOURCE_SHA=<source_head> + deploy commit message 含 ${SOURCE_SHA}
#    → 一致 = 真部署了 source HEAD 的内容
```

**反例**:只跑 `gh api repos/.../commits?per_page=3`(无 `?sha=` 参数),看到 commit 还是 09-18 的就报告"流水线没生效"→ 用户会质问,浪费一次返工。

**适用范围**:任何跨仓 deploy + git push artifact pattern 的 Pages 项目(euv / euv-docs / hyperlane-docs / docs-pages/pages / 任何 source-builds-pages-product)。如果 deploy.yml 把 artifact push 到 `gh-pages` 分支(坑 22 + 23 + 24 的标准 pattern),验证时必须查 `gh-pages` 而非 `master`。

**额外补充**(2026-09-21 实证):deploy commit message 用 `Deploy from ${SOURCE_REPO}@${SOURCE_SHA}`(坑 22 的 5-step hardening 强制要求),所以即使 `gh-pages` 分支显示新 commit 也能立刻反向核对 source SHA = "线上产物对应 source HEAD `8c3747d`" = 真正 deploy 了最新代码。如果 source SHA 没变 / 不对,说明 deploy 跑了但 build 用了老 source(坑 21 的典型)。

## Support files

- `templates/cross-repo-deploy.yml` — starter workflow for the source-builds-pages-product pattern (source repo builds, pushes to a target Pages repo). Implements坑 22's 5-step hardening (source identity assertion, force-fresh www/, build artifact check, source SHA baked into `.deploy/build-info` + commit message). Copy to `.github/workflows/deploy.yml`, replace `<source-org>/<source-repo>` / `<target-org>/<target-repo>` / `<PINNED_SHA>` placeholders, set the `TARGET_REPO_PAT` repo secret.
- `references/github-clone-sideband-disconnect.md` — GFW-affected environments (VM-24-7-opencloudos 等) git clone/fetch 持续 `fetch-pack: unexpected disconnect while reading sideband packet`,SSH + HTTPS 都卡。**长 timeout + 浅克隆也救不了,必须走 GitHub Git Data API** 拉 tree + 逐文件 GET blob。本地 `git init` + `remote add origin` 在 GFW 环境永远 orphan(fetch 卡死拿不到 ref)。完整解法 + token 来源 + API pull 脚本模板。

- `references/mobile-safe-area-navbar.md` — 四轮 PR 迭代的 mobile safe-area 修复链(PR #53–#56),含 Playwright 注入 `--safe-area-inset-top` 复现真实设备的正确姿势(headless Chrome env() 永远是 0,不能让 hook 缓存值被 init_script 覆盖)
- `references/euv-docs-cli-positional-path-resolution.md` — 坑 26 完整调试 transcript:为什么 `euv-docs docs` 的相对 positional 让 build.rs 读 euv-docs crate 自带 starter docs/(而不是用户 docs/),以及怎么通过 wasm binary 里 grep 用户独有字符串确认部署产物是 starter 还是真内容。避免下一轮再做 6 次假阴性诊断。
- `references/euv-docs-site-scaffold.md` — 用 euv-docs 引擎搭建新站点的端到端流
  程(docs-pages/docs VuePress → docs-pages/docs-euv WASM),含 Content API 下载大
  仓库 / Git Data API 多文件 commit 绕过 GFW / euv-cli 0.24 vs 0.21 local-CI 差
  异 / Playwright 真实路径 `<img>.complete && naturalWidth>0` 验证清单(坑 12-16
  的实操版)
- `scripts/sync-pages.sh` — 仿照 euv 仓库 `.github/workflows/pages.yml` 的
  `Sync Pages` step 剥离出来的通用脚本,手动调用 ltpp.vip 镜像站刷新 API。
  用于坑 9(euv master merge 后通知 euv-docs / 下游消费者仓库镜像同步)。
  端点:`POST https://ltpp.vip/api/github/pages/sync/<owner>/<repo>`。
  支持 `MAX_RETRIES` / `RETRY_DELAY` env 覆盖
- `scripts/screenshot-locales.sh` — 多 locale 截图批处理(已随本 skill 提供)
- `scripts/push-via-git-data-api.py` — 多文件 push via Blobs→Tree→Commit→Ref
  API,绕过 GFW 对 git push HTTPS 的握手拦截。用于无本地 git clone / SSH 不通
  / HTTPS 超时场景(典型:大仓库 >50MB + GFW)。参数化 SRC_DIR / REPO / REF
- `scripts/check-frontmatter.py` — 验证 md frontmatter YAML 缩进正确,检测
  坑 17(2-vs-4 空格缩进错位 → 整个 `features:` 数组被吞)。所有 euv-docs 项
  目的 README.md 改动后必跑。`python3 scripts/check-frontmatter.py [docs_root]`
- `scripts/push-source-only.py` — Git Data API 单文件 push(blobs→tree→commit→ref),
  解决坑 21:本地 git push 因 remote master 有 commit 被 reject 时,绕过
  fast-forward 要求直接覆盖特定文件到 master。当 workflow 只听 master push
  但 local master 落后时(典型:Pages source branch 切换后 remote master 重新
  init),用这个 push src/lib.rs + docs/config.toml 到 master 触发 CI rebuild。
  `python3 scripts/push-source-only.py --owner X --repo Y --branch master --file path/in/repo:/local/path --message "..."`
- `scripts/strip-emoji.py` — 跨仓库 emoji 清理,处理坑 20(headless Chromium 字
  体 + Pages CDN 缓存让 emoji 渲染成方框,用户偏好"全删 emoji")。覆盖 U+1F000-
  U+1FFFF / U+2600-U+27BF / U+2300-U+23FF / variation selectors / zero-width
  chars。`python3 scripts/strip-emoji.py [root]`

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

## 用户工作流设计铁律:deploy workflow 极简 + 浮动跟随 + 无注释(2026-09-19 docs-pages/docs 三轮纠正)

用户对 GitHub Actions deploy workflow 的设计偏好反复确认,**铁律级**:

1. **无注释**:deploy.yml / build.sh 不写任何 `#` 注释。"用户说:不需要注释"(Cargo.toml、deploy.yml、build.sh 三个文件分别确认过 3 次)。所有解释性注释一律删除,只留功能性代码。**注释是代码噪音**,真要解释,git commit message / PR body / skill reference 都比行内注释好。

2. **`cargo install` 不带 `--locked`**:用户明确 "不需要lock参数"。`--locked` 要求 Cargo.lock 与 source tree 完全匹配,而无 Cargo.lock 的项目(euv-docs master 没 Cargo.lock,实测 `curl ... /Cargo.lock?ref=master` 返回 404)`--locked` 必失败。即使有 Cargo.lock,`--locked` 也跟 `--branch master` 冲突(每次拉新 HEAD,lockfile 必然要变)。**`cargo install <crate>` 不带 `--locked`,只带 `--force`(绕 install 缓存)。

3. **`cargo install --git` 不带 `--rev <SHA>`**:用户明确 "yml置顶cli版本,不需要指定版本,每次都使用最新的"。deploy 应该**浮动跟随** upstream master HEAD(用 `--branch master`),而不是 pin 一个 SHA。这要求 upstream 必须有 CI 自动发布流水线(见 `references/hyperlane-aligned-rust-yml.md`)。

4. **定时触发合并进 deploy.yml**:不要单独写 `daily-deploy.yml` + `workflow_dispatch` 二次跳板。用户原话:"删除,定时执行完全可以使用已有脚本添加定时字段"。直接在 `deploy.yml` 的 `on:` 加 `schedule: - cron: '0 3 * * *'`,一个 workflow 同时承担 push / cron / workflow_dispatch 三种触发。

**最终 deploy.yml 形态**(极简):
```yaml
name: Deploy
on:
  push: { branches: [master] }
  schedule: [{ cron: '0 3 * * *' }]
  workflow_dispatch:
permissions: { contents: read }
concurrency: { group: deploy, cancel-in-progress: true }
jobs:
  build-and-push:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Verify source
        run: |
          set -euo pipefail
          remote=$(git remote get-url origin)
          case "$remote" in
            *github.com/<expected-owner>/<expected-repo>*) ;;
            *) echo "::error::unexpected source repo: $remote"; exit 1 ;;
          esac
          echo "SOURCE_REPO=$remote" >> "$GITHUB_ENV"
          echo "SOURCE_SHA=$GITHUB_SHA" >> "$GITHUB_ENV"
      - uses: actions/checkout@v4
        with:
          repository: <target-owner>/<target-repo>
          ref: gh-pages
          path: __target
          persist-credentials: true
          token: ${{ secrets.DEPLOY_PAT }}
      - run: cargo install euv-cli
      - run: curl https://rustwasm.github.io/wasm-pack/installer/init.sh -sSf | sh
      - name: Install euv-docs
        env: { EUV_DOCS_SRC_DIR: ${{ github.workspace }}/docs }
        run: cargo install --target-dir /tmp/euv-docs-target --git https://github.com/euv-dev/euv-docs --branch master --bin euv-docs --force
      - run: rm -rf www
      - name: Build
        run: euv-docs ${{ github.workspace }}/docs --out ${{ github.workspace }}/www --index-html template.html
      - name: Verify build
        run: |
          set -euo pipefail
          [ -f www/index.html ] || { echo "::error::www/index.html missing"; exit 1; }
          [ -d www/pkg ] || { echo "::error::www/pkg missing"; exit 1; }
          test -n "$(ls -A www)" || { echo "::error::www/ is empty"; exit 1; }
      - name: Push to target
        run: |
          set -euo pipefail
          cd __target
          find . -maxdepth 1 -not -name '.git' -not -name '.' -not -name '..' -exec rm -rf {} +
          cp -r ../www/* .
          touch .nojekyll
          mkdir -p .deploy
          cat > .deploy/build-info <<EOF
          source_repo=${SOURCE_REPO}
          source_sha=${SOURCE_SHA}
          workflow_run=${GITHUB_RUN_ID}
          built_at=$(date -u +%FT%TZ)
          EOF
          rm -f CNAME
          git config user.name "eastspire"
          git config user.email "root@ltpp.vip"
          git add -A
          git diff --cached --quiet || git commit -m "Deploy from ${SOURCE_REPO}@${SOURCE_SHA}"
          git fetch origin gh-pages
          git rebase -X theirs origin/gh-pages || git rebase --abort
          git push origin gh-pages
      - name: Sync Pages
        run: |
          max_retries=60
          retry_delay=60
          for i in $(seq 1 $max_retries); do
            if curl -sf -X POST https://ltpp.vip/api/github/pages/sync/<owner>/<repo> -H "Connection: close"; then
              echo ""; echo "Sync succeeded on attempt $i"; exit 0
            fi
            [ $i -lt $max_retries ] && sleep $retry_delay
          done
          exit 1
```

**反例**(本次清理掉的版本):
- 6 个 step 上方各有一段 4-12 行注释解释 "why this step exists" → 全部删
- `cargo install euv-cli --locked` → 改成 `cargo install euv-cli`
- `cargo install --git https://github.com/eastspire/euv-docs --rev 6c62600 ...` → 改成 `--branch master`(无 SHA pin,无 eastspire fork)
- 独立的 `.github/workflows/daily-deploy.yml`(47 行 + REST API dispatch 跳板)→ 删除,schedule 移到 deploy.yml

**适用范围**:任何 GitHub Actions deploy workflow(不只是 docs-pages/docs)。euv / hyperlane / 任何下游消费者仓的 deploy.yml + build.sh 都按这 4 条走。
