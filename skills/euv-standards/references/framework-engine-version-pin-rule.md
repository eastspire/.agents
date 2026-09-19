# Framework Engine 版本 pin 铁律(下游工具仓)

> 2026-09-19 docs-pages 部署教训:euv-docs fork 把 `euv = "0.18"` 改 `"*"`,线上渲染 fallback 到旧样式 = "看起来修复全没"。本文件记录根因 + 复用模式。

## 1. 现象

`docs-pages/docs` 仓部署 euv-docs 引擎生成文档站,用户连续反馈:

- sidebar 对齐不对(应该和官方 example 一致)
- 首页边框缺失(应该有边框)
- "之前的修复全没了,一定是代码丢了"

实际排查:

- euv-dev/euv-docs upstream master HEAD `6c62600` 含 PR #2/#4/#18-#28/#35-#39 全部 sidebar / anchor / markdown 修复 ✓
- eastspire/euv-docs fork branch `fix/audit-r11-4-private-guard` HEAD `35febe7` 领先 upstream **仅 1 commit**
- 该 1 commit 内容:`Cargo.toml` 把 `euv = "0.18"` + `euv-ui = "0.18"` 改为 `"*"`

**`35febe7` 在 install 阶段**强制 engine 浮到 0.24.x,而 `euv-docs` 0.1.6 的 UI 渲染代码是按 0.18 CSS safe-area pattern + 0.18 组件签名写的 → 编译过 + 跑起来但样式 fallback 到旧 = "看起来没修复"。

## 2. 根因:framework engine CSS pattern 跨 minor 版本不稳

euv engine 在 0.18 → 0.24 之间经历:

- mobile safe-area CSS 模式改动(letterbox 浏览器 → immersive WebView 处理差异)
- `c_mobile_header` / `c_mobile_nav_drawer` 类样式更新
- 部分组件 prop 签名变更
- 主题色 token 集合新增/弃用

**对下游工具仓的影响**:任何在 `Cargo.toml` 写 `euv = "*"` 的下游仓,在 CI runner 上 install 时:

1. `cargo install --git https://...` resolve `euv = "*"` → 拉 crates.io 最新版(0.24.x)
2. `wasm-pack build` 编译时拿到的是新版 engine CSS 模式
3. 下游代码假设的 0.18 模式(`var(--euv-mobile-safe-top, 0px)`、safe-area CSS 等)与新版不匹配
4. wasm 产物在浏览器跑起来,**部分样式 fallback 到 default**,视觉上 = "修复没生效"

## 3. 上游故意 pin 的设计意图 (PR #13)

`euv-dev/euv-docs` 的 `Cargo.toml` 注释(2026-09-18 master `6c62600`):

```toml
# Pinned to the euv example's major version (workspace at 0.18.15) so the
# generated CSS for `c_mobile_header`, `c_mobile_nav_drawer`, etc. matches
# the official euv example 1:1 — required to keep the mobile nav rendering
# consistent with the example site on phones with `viewport-fit=cover`.
# `*` would float across 0.17 → 0.18 and silently drop the
# `var(--euv-mobile-safe-top, 0px)` safe-area pattern that the example uses.
euv = "0.18"
euv-ui = "0.18"
```

**理由**:

- 下游工具仓是**给用户演示 euv 渲染效果的官方 example**(像 euv-docs 是文档站)
- 要 1:1 渲染出 euv 官方 example 在 phone 上(`viewport-fit=cover`)的样式
- 必须 pin 到 euv engine 的"stable css-safe-area"版本
- 浮到最新会让 example 站渲染与 euv 官方 example 不一致,违反工具仓存在意义

**euv 主仓 vs 下游工具仓的版本策略对比**:

| 仓 | 角色 | 版本策略 | 理由 |
|---|---|---|---|
| `euv-dev/euv` (engine) | 框架本身 | 自身版本自管理(`0.24.x`) | 跨 minor 演进是常态 |
| `euv-dev/euv-docs` (docs engine) | euv 官方文档站生成器 | **pin `euv = "0.18"`** | 必须 1:1 对齐 engine stable CSS |
| `euv-dev/euv-cli` (CLI) | 调用 euv 命令行工具 | 待考察(目前 pin 0.18) | CLI 不渲染 UI,但调用栈共用 version |
| `euv-dev/euv-app` (Tauri Android) | Android 沉浸式 app | pin 0.18 (需要 safe-area 控制) | 见 euv-app skill 的 immersive architecture |
| 第三方 / 用户 fork | 任意 | 跟随上游 pin + 自己测试 | 升级前必须跑全套 e2e |

## 4. deploy 引用下游工具仓的 pin 模式

任何 deploy 脚本(workflow / shell / docker)要 cargo install 下游工具仓时:

**DO**:

```bash
# 1. pin 绝对 SHA (而非 main / master)
cargo install --git https://github.com/euv-dev/euv-docs \
  --rev 6c62600d95abe0e97524ae8c3b5da07d4ca47836 \
  --bin euv-docs --locked --force

# 2. 配合 --target-dir /tmp/<name>-target 强制新 build dir,避开 cargo 缓存
cargo install --target-dir /tmp/euv-docs-target \
  --git https://github.com/euv-dev/euv-docs \
  --rev <sha> \
  --bin euv-docs --locked --force
```

**DON'T**:

```bash
# ❌ 用 branch / master - 漂移风险
cargo install --git https://github.com/euv-dev/euv-docs --branch master ...

# ❌ 用 fork + 激进 engine bump - 引入 CSS API mismatch
cargo install --git https://github.com/eastspire/euv-docs --rev 35febe7 ...
# (35febe7 把 euv="0.18" 改成 "*",会让 engine 跳到 0.24.x)
```

**fork 仍可用的情况**:fork 仅做**纯 additive** 改动(如新增 doc 路由 / 新增 copy-public-assets CLI flag / 改 docs/private/ 鉴权),**不修改 framework engine 依赖**。这种情况下 fork 是合法的,但 PR body 必须明确声明 "no changes to framework version pins"。

## 5. bump 检查清单

升级下游工具仓(euv-docs) SHA 前必须跑:

```bash
# 1. 看上游 engine pin 变化(从 euv-dev/euv 仓)
git -C ~/github/euv-dev/euv show master:Cargo.toml | grep -E '^euv[^-]|^euv-ui' | head -3

# 2. 看 fork 的 Cargo.toml diff 是否动了 engine pin
gh pr diff <fork-pr-number> --repo eastspire/euv-docs | grep -E '^[+-]euv[^-]|^[+-]euv-ui'

# 3. 本地编译测试(模拟 CI runner)
EUV_DOCS_SRC_DIR=/tmp/real-docs EUV_DOCS_OUT_DIR=/tmp/www \
  /root/.cargo/bin/euv-docs /tmp/real-docs \
  --out /tmp/www --index-html /tmp/template.html

# 4. headless chromium DOM 验证(关键 CSS class + 主元素 box-model)
python3 /tmp/cdp-probe.py   # 或自己写
# 检查:.c_app_main / .c_euv_sidebar_link / .c_home 的 computed border / padding / box-shadow
```

## 6. 已发布版本的 fallback

如果因 fork float 导致线上样式错乱,**回滚路径**:

1. **立即改 deploy.yml / build.sh** 从 fork 改回 upstream,提交 + push master → 触发 workflow → 重建部署 → 验证
2. **不必 revert fork 分支**(保留作历史;后续如需保留 fork 的"私有鉴权"等合法改动,rebase 到 upstream master + cherry-pick 非版本相关 commit 即可)
3. **告知用户修复点**:不是代码丢了,而是 fork 的 `*` 让 engine 升到 0.24.x 与 euv-docs 0.1.6 UI 代码 mismatch
4. **CDP 截图前后对比**:用 `/tmp/cdp-compare.py` 类脚本拉两次部署的线上 `https://docs-pages.github.io/pages/`,对比 `.c_home` / `.c_app_main` / sidebar 元素的 computed style

## 7. 关联 references

- `euv-standards/SKILL.md` §12 坑表行"下游工具仓 engine 版本 pin"(2026-09-19 加入)
- `euv-standards/SKILL.md` §17 版本升级规则(同源:patch bump 铁律 + CI sync)
- `references/cross-repo-workflow-trigger-limits.md`(deploy reference 模板)
- `/root/.hermes/skills/euv-app`(euv-app 的 immersive architecture 与 euv engine pin 关系)