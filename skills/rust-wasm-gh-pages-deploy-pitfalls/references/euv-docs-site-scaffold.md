# euv-docs site scaffold end-to-end

端到端流程:从一个 md 文档源(可能是 VuePress / Hugo / 任何 markdown 站)用 `euv-docs` 引擎搭新站 + 部署到 GitHub Pages。本节是 `rust-wasm-gh-pages-deploy-pitfalls` 坑 12-16 的实操版,记录一次完整迁移案例(`docs-pages/docs` VuePress 2 + theme-hope → `docs-pages/docs-euv` WASM)。

适用场景:
- 用户说 "把 X 站用 euv-docs 重写" / "把 docs-pages/docs 迁到 euv-docs"
- 用户已有 md 文档(可能散布在多个仓,可能附有图片 / 自定义容器语法)
- 目标:用 `euv-docs` 模板(`~/github/euv-dev/euv-docs`)起新仓 + Pages 部署
- 排除范围明确(本案例: `src/essay/private/` 下 3 文件)

不适用:
- 修改 `euv-dev/euv-docs` 框架本身 — 那是 `euv-docs-contribution` skill 的 scope
- 改 `docs-pages/docs` VuePress 源仓 — 那是 `docs-pages-docs-contribution` skill

## 决策清单(开干前先确认)

写一行 todo 一次性问清,而不是来回多轮提问:

1. **目标仓名 + owner**:新仓 `docs-pages/docs-euv`(或用户指定)?继承现 org / 用户的 GitHub Pages 权限?(free plan Pages 仅 public 仓可用)
2. **是否排除某些内容**:`src/essay/private/` 这种用户明确说"排除"的目录?如果是 Contents API 下载时直接 filter 掉
3. **图片策略**:VuePress 的 `markdown-images/` / `.vuepress/public/img/` 怎么迁?复制源图到 `docs/public/<原相对路径>/` + 重写 md 的 `<img src>` 为 `/<repo>/<path>`(坑 14)
4. **本地化策略**:源仓是单 locale(zh-CN)还是多 locale?euv-docs build.rs 支持 `[[locales]]` + `zh-CN/` / `en/` 子目录,可以从 VuePress `i18n/` 目录推断
5. **是否需要新地址**:GitHub Pages 项目 URL 是固定的 `https://<user>.github.io/<repo>/`(坑 16),"新地址"= 切 source branch 到 `docs`(URL 不变但部署源是新分支)
6. **PR 工作流**:Track 1(eastspire / docs-pages 直推 master)还是 Track 2(fork + PR)?docs-pages/docs → docs-pages/docs-euv:新仓 owner 是 `docs-pages` org,eastspire 是 admin,可以直推 master,但用户偏好 `docs` 分支 + deploy 到 docs,master 保持锁定稳定

## 端到端步骤

### 1. 探测源仓结构(零拷贝)

GFW + 大仓库(>50MB)的 git clone 经常卡 15+ 分钟。**改走 Contents API metadata-only**:

```bash
# 1. tree (recursive=1, 无 content)
gh api repos/<owner>/<repo>/git/trees/<branch>?recursive=1 \
  --jq '.tree[] | select(.type=="blob") | .path' > /tmp/all_files.tsv

# 2. per-dir 计数
sort /tmp/all_files.tsv | awk -F/ '{print $1"/"$2}' | uniq -c | sort -rn

# 3. 排除范围 — 用户原话"排除 src/essay/private/"
grep -v '^src/essay/private/' /tmp/all_files.tsv > /tmp/keep_files.tsv
```

判断点:总文件数 / 总 KB / `.vuepress/config.ts` 配置(`nav` / `sidebar`)/ frontmatter schema(`title`/`home`/`icon` 字段)。

### 2. Content API 下载(per-file)

```bash
mkdir -p /root/_scaffold/<repo>
while read path; do
  gh api "repos/<owner>/<repo>/contents/$path" \
    --jq .content | base64 -d > "/root/_scaffold/<repo>/$path"
done < /tmp/keep_files.tsv
```

注意 `--jq .content`(**不是** `--jq -r '.content // empty'`,那个写法 gh CLI 不接受 `-r`)。

**坑**:60 文件后 `gh api` 偶尔 socket hangup,**不要一次性 pipe shell**,用 `while read` 顺序跑。慢但稳。

### 3. 写 migration script(per-md filter)

不要直接拷贝 md,必须做 4 件事:

1. **frontmatter filter**:euv-docs serde schema 只识别 `title` / `home` / `heroText` / `heroImage` / `tagline` / `actions[]` / `features[]` / `footer` / `order`。VuePress 字段 `head`/`icon`/`category`/`date`/`bgImageDark` 全部静默丢弃 — **保留它们让 md 长乱,直接删**
2. **VuePress 组件 strip**:`<Share/>` / `<Catalog/>` / `<Bottom/>` / `<Badge>text</Badge>` / `<CommentService/>` — euv-ui 没等价物,替换为单行斜体注释 `<!-- <Share/> stripped: euv-ui no equivalent -->`
3. **图片路径 rebase**:`![](./markdown-images/2025/09-19/X.jpg)` → `![](/<repo>/markdown-images/2025/09-19/X.jpg)`(坑 14)
4. **VuePress 自定义容器替换**:坑 15 — `[!tip]\n> ...` → `**💡 TIP**\n> ...`,跑 regex batch

```python
# 简化版:核心 regex
img_re = re.compile(r'!\[[^\]]*\]\((\.\.?/)?(markdown-images/[^)]+)\)')
def repl(m): return f'![](/<repo>/{m.group(2)})'

tip_re = re.compile(r'\[!(tip|warning|note|info|danger)\]')
emoji = {'tip': '**💡 TIP**', 'warning': '**⚠️ WARNING**', ...}
```

### 4. 复制静态资源到 `docs/public/<subdir>/`

build.rs 自动复制 `docs/public/*` 到 `www/`(坑 13):

```bash
# 源仓的 .vuepress/public/img/ → docs/public/img/
cp -r /root/_scaffold/<repo>/.vuepress/public/img/ /root/<new-repo>/docs/public/img/
cp -r /root/_scaffold/<repo>/ltpp/markdown-images/ /root/<new-repo>/docs/public/markdown-images/
# 注意: source 仓可能 <tool>/markdown-images/<file>.png 与 ltpp/markdown-images/<file>.png
# 重名 file 用 first-wins,后续同名覆盖(脚本里 os.path.exists check)
```

**坑**:VuePress 站点的 `.vuepress/public/` 和 `<tool>/markdown-images/` 是两个不同目录,前者复制时直接 `cp -r`,后者 md 里的相对路径必须同步重写为 `/<repo>/markdown-images/...`。

### 5. 用 euv-docs 模板起新仓

`~/github/euv-dev/euv-docs` 是模板基础(用户偏好)。直接拷:

```bash
# 1. download euv-docs base
mkdir -p /root/_scaffold/euv-docs-base
gh api repos/euv-dev/euv-docs/git/trees/master?recursive=1 --jq '.tree[].path' \
  > /tmp/euv_docs_paths.txt
while read p; do
  case $p in
    docs/*|target/*) continue ;;  # skip own docs and build artifacts
    *) gh api "repos/euv-dev/euv-docs/contents/$p" --jq .content | base64 -d \
         > "/root/_scaffold/euv-docs-base/$p" ;;
  esac
done < /tmp/euv_docs_paths.txt

# 2. copy to new repo local
cp -r /root/_scaffold/euv-docs-base/Cargo.toml /root/<new-repo>/
cp -r /root/_scaffold/euv-docs-base/build.rs /root/<new-repo>/
cp -r /root/_scaffold/euv-docs-base/src /root/<new-repo>/
cp -r /root/_scaffold/euv-docs-base/template.html /root/<new-repo>/
cp -r /root/_scaffold/euv-docs-base/.github /root/<new-repo>/
```

**坑**:euv-docs 自己带 docs/(grammar reference + README),如果新站只用 euv-docs 作为引擎,这些 docs/ 要清掉再拷 migration 后的 md 进来。

### 6. 自定义(template.html + config.toml + lib.rs)

- **`template.html`**:`<html lang="zh-CN">` / `<title>...</title>` / description / `<script type="module">` 用 `dynamic import + try/catch + __euvBootStatus` 模式(坑 16 — 防御性 boot script)
- **`docs/config.toml`**:单 `zh-CN` locale at `/`,navbar = 首页 / 目录 / GitHub
- **`Cargo.toml`**:改 `name = "<repo>"`,repository url = `<repo>`
- **`src/lib.rs`**:`Css::inject_css(EUV_MD_CSS); Css::inject_css("<site-local overrides>"); App::mount(...)` — 不要碰原 euv-docs 的 `main()` 逻辑

### 7. 本地 build + 验证

```bash
cd /root/<new-repo>

# IMPORTANT: rm www before first build to force build.rs to rerun (坑 13)
rm -rf www
euv build --release --index-html template.html -- --target web --out-dir www/pkg --out-name euv_docs --no-typescript --no-pack --no-gitignore

# 检查 www/ 完整性
find www -type d | sort
# 期望:www/essay/ www/img/ www/css/ www/markdown-images/ www/pkg/ www/webfonts/

# 起 server
cd www && python3 -m http.server 5188 &
sleep 2
```

**坑**:`euv-cli` 版本差异(本地 0.21.2 vs CI 0.24.7)— 本地 build 出来的 `www/pkg/<name>.js` filename 不一定匹配 CI,只是 dev 测试不需要严格一致。**CI 用固定版本 `cargo install euv-cli --locked`**。

### 8. Playwright 真实路径验证

不用 curl(curl 抓不到 JS console error + `<img>.complete` 状态)。headless + per-page:

```python
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(
        headless=True,
        executable_path='/usr/bin/ungoogled-chromium',
        args=['--no-sandbox', '--disable-dev-shm-usage'],
    )
    ctx = browser.new_context(viewport={'width': 1280, 'height': 800})
    page = ctx.new_page()
    
    failed = []
    page.on('response', lambda r: failed.append(f'{r.status} {r.url}') if r.status >= 400 else None)
    
    tests = [
        ('home', 'http://127.0.0.1:5188/'),
        ('essay-09-19', 'http://127.0.0.1:5188/#/essay/posts/2025/09-19.html'),
        ('hyperlane-root', 'http://127.0.0.1:5188/#/hyperlane/'),
    ]
    
    for name, url in tests:
        failed.clear()
        page.goto(url, wait_until='networkidle', timeout=30000)
        page.wait_for_timeout(5000)
        imgs = page.evaluate('''() => Array.from(document.images).map(i => ({
            src: i.currentSrc || i.src,
            complete: i.complete,
            nw: i.naturalWidth || 0,
        }))''')
        loaded = sum(1 for i in imgs if i['complete'] and i['nw'] > 0)
        broken = sum(1 for i in imgs if i['complete'] and i['nw'] == 0)
        print(f'[{name}] imgs={len(imgs)} loaded={loaded} broken={broken} failed={len(failed)}')
        if broken > 0:
            print(f'  broken_srcs={[i["src"] for i in imgs if i["complete"] and i["nw"]==0][:3]}')
        if failed:
            print(f'  failed_reqs={failed[:3]}')
```

判定:
- `broken > 0` 或 `failed > 0` → md 路径仍错(坑 14 没修干净)或 assets 没复制(坑 13 没 force-fresh)
- `loaded=0 not_yet=N` → CDN 慢,等更长;最终仍 broken → 回到 md/assets 排查

### 9. 推到新仓(GFW 环境)

`git push origin master` 在 GFW 下经常 135s timeout,改走 Git Data API:

```python
# scripts/push-via-git-data-api.py (本 skill scripts/ 下)
# Steps: POST blob (per file) → POST tree with base_tree → POST commit → PATCH ref
# Token: source from /root/.bashrc.d/gh_token.sh (subshell)
# 速度: ~300 files / ~5 分钟(每个 blob 单独 POST)
```

**坑**:terminal tool 在 foreground 跑 300-file upload 会 timeout(5 分钟 max)。**必须 background 跑**:用 `subprocess.Popen(..., start_new_session=True)` 起 daemon,poll `/tmp/push_log.txt`。多个相同 push script 同时跑会竞争同一个 log,**只保留一个**(kill 旧的)。

**坑 2**:Python 的 stdout 缓冲会让日志看不到 — 用 `python3 -u`(unbuffered)。

### 10. Pages 配置(build_type=workflow + 双分支)

```bash
# 创建后立即改 build_type(坑 12)
gh api -X PUT repos/<owner>/<repo>/pages \
  -f 'build_type=workflow' \
  -f 'source[branch]=master' \
  -f 'source[path]=/'

# 用户希望 "流水线部署的地址给一个新地址" = source branch 切到 docs 分支
gh api -X PUT repos/<owner>/<repo>/pages \
  -f 'build_type=workflow' \
  -f 'source[branch]=docs' \
  -f 'source[path]=/'

# workflow deploy.yml 加 docs branch trigger + rm -rf www step(坑 13)
# 详见 rust-wasm-gh-pages-deploy-pitfalls §"双分支 workflow deploy 模板"

# 触发首次 deploy
gh api -X POST repos/<owner>/<repo>/actions/workflows/<deploy_id>/dispatches -f ref=docs

# 轮询
while true; do
  s=$(gh api repos/<owner>/<repo>/actions/runs?per_page=1 \
    --jq '.workflow_runs[0].status + " " + (.workflow_runs[0].conclusion // "null")')
  echo "$s"
  [[ "$s" == "completed "* ]] && break
  sleep 10
done
```

### 11. 线上 Playwright 复测

把本地 URL 换成 `https://<user>.github.io/<repo>/`,再跑一遍 §8 脚本。`broken=0` + `failed=0` + `loaded=loaded_count`(CDN 慢,acceptable) = 通过。

**坑**:GitHub Pages 边缘缓存 `cache-control: max-age=600`,wait 30-60s 或加 `?cb=<num>` cache-buster。

## 用户偏好(沉淀)

- **不要补全文档内容** — 用户原话 "没让你直接 euv-docs 完成文档补全"。意思是:迁移原始 md,**不**做内容审阅 / 重写 / 翻译 / 优化
- **新地址 = 新分支** — Pages 项目唯一 URL 不变;切 source branch 到 `docs` 让用户感受到"流水线部署变了"
- **保持 master 锁定稳定 + 在 docs 分支改** — 用户原话 "撤销改动"指的是 "不要让 master 跟着变",不是 "git revert"
- **排除 src/essay/private/** — 用户原话一次性给,直接 filter 掉,不要事后追问"这个 README 要不要保留"

## 验证清单

- [ ] 新仓 GitHub Pages 启用,URL 200
- [ ] Pages `build_type=workflow`(不是 `legacy`)
- [ ] `deploy.yml` listen `branches: [master, docs]`
- [ ] workflow 含 `rm -rf www` step(坑 13)
- [ ] md 绝对路径全部带 `/<repo>/` 前缀(坑 14)
- [ ] `[!tip]` 等 VuePress 容器全部替换为 `**💡 TIP**`(坑 15)
- [ ] `template.html` 用 dynamic import + try/catch boot script
- [ ] README.md frontmatter YAML 缩进全部 4 空格,`python3 scripts/check-frontmatter.py docs/` 验证 features 数量正确(坑 17)
- [ ] **feature card 没有 `link:` 字段**(坑 18 — 框架不支持,塞了也无效)
- [ ] **feature card `icon:` 字段**:要么删(emoji 不显示),要么用 euv-docs 默认 logo(坑 20)
- [ ] site-local CSS `c_feature_card` 加 border 在 `src/lib.rs` 的 `main()` 里(坑 19)
- [ ] 本地 Playwright 6+ 页测试 `broken=0 failed=0`
- [ ] 线上 Playwright 6+ 页测试 `broken=0 failed=0`
- [ ] 用户排除范围(如 essay/private)真的没出现在 `docs/`
- [ ] GitHub Actions deploy run success

## README.md frontmatter 模式(权威模板)

```markdown
---
home: true
title: 首页
heroText: <大字标题>
tagline: <副标题>
actions:
  - text: <按钮文字>
    link: /<target>
    icon: <fontawesome-name-or-empty>
    type: primary
features:
  - title: <工具名>
    details: <一句话描述>
    icon: <emoji-or-empty>
  - title: <工具2>
    details: <描述>
    icon: <emoji-or-empty>
footer: <页脚文本>
---

## 正文 markdown

任何 hero 字段都不会渲染到 features 卡片上,所以正文留空 / 放品牌说明都行。
```

**关键约束**(从坑 17 / 18 / 20 学到):
- `actions:` 块 2 空格 list,内部字段 4 空格(`    link:`, `    icon:`, `    type:`)
- `features:` 块同样 2 空格 list,内部字段 4 空格
- feature entry **不要**写 `link:`(euv-docs 不读,塞了 build.rs 静默丢弃)
- feature entry 的 `icon:` 在 headless Chromium 不显示 emoji,如果不想折腾字体就**留空**(或干脆删 `icon:` 行)
- `home: true` 必须有,否则 euv-docs 不渲染 hero
- YAML 全部用 4 空格,不用 tab,不要混 2/4