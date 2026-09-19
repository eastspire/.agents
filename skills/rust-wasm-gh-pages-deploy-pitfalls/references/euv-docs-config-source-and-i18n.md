# 坑 32:euv-docs 站点配置真实来源 = 根 README.md frontmatter(config.toml 是 decoy)+ i18n 硬编码串 + sidebar:false + LICENSE 本地化(2026-09-19)

## 32a. 站点配置来源:`<SRC_DIR>/../README.md` frontmatter,不是 docs/config.toml

**症状**:改 `docs/config.toml` 的 title/footer/navbar/labels 完全无效,线上一直是旧值。wasm 里 `strings | grep` 不到 config.toml 的任何 label。

**根因**:`euv-docs/build.rs` 的 `load_config_from_readme(&docs_dir)` 读 **`<SRC_DIR>/../README.md` 的 YAML frontmatter**(site + locales 两段),从不读 `docs/config.toml`。迁移时留下的 config.toml 是 decoy,仓 README 注释还曾谎称它管 navbar/footer。

**解法**:
- 站点 title/description/locales/navbar/footer/toc_label/prev_label/next_label → 改**根 README.md frontmatter**。
- 浏览器标签页 title → 改 `template.html` 的 `<title>`(静态;wasm 运行时不改 document.title)。
- decoy `docs/config.toml` 直接删,并把 README 里"config.toml configures site"的错误说明改成指向根 README frontmatter。

**诊断**:`strings www/pkg/euv_docs_bg.wasm | grep -c '<你的label>'` — 0 = 配置没被读。构建后必跑。

## 32b. euv-docs 硬编码 UI 串(locale 配置覆盖不了,只能改源码)

locale frontmatter 只管 footer/toc_label/prev_label/next_label/navbar。以下串硬编码在组件里(本站已全部中文化,PR #244):

| 位置 | 原串 → 现串 |
|---|---|
| `password_gate/view/fn.rs` | This article is password-protected… / Password / Unlock / Verifying… / Incorrect password. → 中文 |
| `not_found/view/fn.rs` | Page not found / Home → 页面不存在 / 首页 |
| `layout/view/fn.rs` nav_footer | "Built with Euv & Wasm" → "基于 Euv & Wasm 构建" |
| `layout/view/fn.rs` section_label | fallback `"Docs"` → `"文档"`;优先取第一个内部非首页 navbar 项文本 |
| `layout/view/fn.rs` | "Toggle theme" / "Language" tooltip → 切换主题 / 语言 |

**排查清单**:用户报"某处英文"时,先 `grep -rn '"[A-Z][a-zA-Z ]\{2,\}"' src/component/ --include="*.rs"` 捞硬编码串,再核对哪些来自 frontmatter。

## 32c. 附属页(md)不进侧边栏:`sidebar: false` frontmatter

build.rs 的 `build_sidebar` 默认把**每个** `*.md`(除 README/index)收进侧边栏树。放 LICENSE.md 这类附属页会污染侧边栏(34 个 crate = 34 条垃圾 entry)。PR #244 给 build.rs 加了 page frontmatter `sidebar: false`:可路由、可直连,但不进侧边栏、不进 prev/next 分页链。写法:

```yaml
---
title: 开源许可证
sidebar: false
---
```

**注意**:加完 `sidebar: false` 必须重 build 验证侧边栏条数(`querySelectorAll('.c_euv_sidebar_link')` 里不含 LICENSE href)。

## 32d. crate README 的 LICENSE 链接 404 → 从 GitHub 下载本地化

**症状**:crate 页里 `[![](…/crates/l/x.svg)](./LICENSE)` 和 `[license](LICENSE)` 点击 404——docs 树里根本没有 LICENSE 文件。

**解法**(脚本见 `scripts/vendor-license-mds.py`):
1. 从每个 README 的 `[GITHUB 地址](https://github.com/<org>/<repo>)` 提取仓库;
2. `GET api.github.com/repos/<org>/<repo>/contents/LICENSE`(Accept raw,自动跟随默认分支;404 则试 LICENSE-MIT / LICENSE.md / LICENSE.txt);
3. 存为 `docs/<crate>/LICENSE.md`,frontmatter `title: 开源许可证` + `sidebar: false`,正文包 ` ```text ` 围栏(保留原文换行,md 会把单换行折叠成一段);
4. README 里 `](./LICENSE)` / `](LICENSE)` 全部改指 `](./LICENSE.md)` / `](LICENSE.md)` —— `rewrite_link` 见到 `.md` 后缀会路由化成 `#/<crate>/LICENSE.html`,router 命中该文件正常渲染。

**验证**:点 badge 的 license 链接 → `#/<crate>/LICENSE.html` 渲染许可证全文;侧边栏无 LICENSE 条目。

## 32e. euv-ui 全局 reset `img { width: 100% }` 撑爆 badge

**症状**:shields.io / docs.rs badge(natural ~78-110px)渲染成内容区全宽(816px)。`getComputedStyle(img).width == 容器宽`。

**根因**:`ui/src/style/css/fn.rs` 全局 reset `img, picture, video, canvas, svg { display: block; width: 100%; }`。docs override 只写了 `max-width: 100%` 没覆盖 `width`,于是 width:100% 生效。

**修法**(双管齐下,PR #244):
- 框架(euv-ui master):reset 改 `max-width: 100%`(0.25.3 已发布);
- 站点(euv-docs override,因 docs 走 crates.io euv-ui 0.18 吃不到框架修复):`.md-body img { width: auto !important; max-width: 100% !important; }`。

**教训**:override 别人的样式时,要把对方声明过的**每一个**属性都显式覆盖——只写 max-width 不抵消 width。
