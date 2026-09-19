# euv-docs 迁入 euv monorepo 后的部署拓扑 + 本地验证循环 + Playwright 大图验证坑

2026-09-19 docs-pages/docs 修复链(PR #238/#239)实测记录。

## 1. 拓扑:euv-docs 已并入 euv-dev/euv monorepo

- 路径:`euv-dev/euv/euv-docs/`,**workspace-excluded**(根 `Cargo.toml` 的
  `members = ["cli","core","engine","example","macros","ui"]` 不含它),有自己的
  `Cargo.lock`,`version = 0.25.x`,依赖 crates.io 的 `euv = "0.18"` / `euv-ui = "0.18"`。
- 旧独立仓 `euv-dev/euv-docs` 的写法(`cargo install --git .../euv-docs`)已过时,
  docs-pages/docs 的 deploy.yml 现在用:
  `cargo install --target-dir /tmp/euv-docs-target --git https://github.com/euv-dev/euv --branch master euv-docs --bin euv-docs --force`
  (positional `euv-docs` 是 package 名,cargo 在 monorepo 里找到子包)。
- **euv-docs 修复不发 crates.io、不动版本号**(非 workspace member,sync_workspace_version
  不管它);合入 euv master 后,`workflow_dispatch` docs-pages/docs 的 deploy(ref=master)
  即重建生效。端到端链:euv master merge → dispatch docs-pages/docs → build → push 到
  docs-pages/pages 的 `gh-pages`(build_type=legacy + `.nojekyll`)→ 验 wasm
  `last-modified` 变了再跑浏览器验证。
- euv-docs 的 CI 覆盖:rust.yml 的 check/tests/clippy/build 会跑到它(尽管不在 workspace
  members —— CI 配置层面单独处理了);本地提交前至少跑
  `cargo check/clippy --manifest-path euv-docs/Cargo.toml`(host target 即可过)。

## 2. 本地验证循环(热缓存 ~1 分钟)

VM-24-7 上复用 `/tmp/euv-docs-target` 缓存,全循环 ≈3 分钟:

```bash
# 1. 装本地改过的 euv-docs CLI(热缓存只重编本 crate)
cd ~/github/euv-dev/euv/euv-docs
CARGO_BUILD_JOBS=2 cargo install --path . --target-dir /tmp/euv-docs-target --bin euv-docs --force

# 2. 构建站点(positional 与 env 都必须绝对路径,见坑 25/26)
cd ~/github/docs-pages/docs && rm -rf www
CARGO_BUILD_JOBS=2 CARGO_TARGET_DIR=/tmp/euv-docs-target \
  EUV_DOCS_SRC_DIR=$PWD/docs EUV_DOCS_OUT_DIR=$PWD/www \
  euv-docs $PWD/docs --out $PWD/www --index-html template.html

# 3. 起服务 + Playwright 验证
cd www && python3 -m http.server 8899 &
```

硬断言:`grep -c '<某内容页路由>' $(find /tmp/euv-docs-target -name docs_gen.rs | head -1)`
> 0 = 页面真进了构建(比浏览器快,能区分"没构建"与"渲染错")。

## 3. Playwright 大图验证三坑(实测)

站点 essay 页单页 ~16MB 照片(每张 0.3–4MB),本地 14/14 秒过、线上"FAIL"
— 全是带宽假象。三个坑:

1. **`wait_until='networkidle'` 永不 settle**:大图一直在下载,60s 超时。
   用 `wait_until='domcontentloaded'` + `page.wait_for_selector('article img',
   state='attached')` 再等图片。
2. **`wait_for_selector` 默认等"可见"**:未加载的 `<img>` 是 0 尺寸,永远不可见,
   超时但 log 显示 "locator resolved to N elements"。必须 `state='attached'`。
3. **`naturalWidth == 0` ≠ 404**:可能是还在下载。区分法:
   - 挂 `page.on('response')` 收集 ≥400 的状态码 — 无 4xx 则不是缺文件;
   - 对样本 URL `curl -sI` 看 200 + `content-length`(1.4MB+ = 慢,不是缺);
   - 要"全加载完"的结论就给足预算:`wait_for_function(
     "[...document.querySelectorAll('article img')].every(i => i.complete)",
     timeout=120000)`,或直接 HEAD sweep 全部 URL 判可用性(确定性,不等带宽)。

## 4. 重复投递消息的处理(模型切换后 session 重建)

用户首条消息与历史会话首条**逐字相同**时(本会话:模型 MiniMax-M3 → kimi-k3 切换后
重投递),不要当成新任务重跑,也不要直接回"已修完"。流程:

1. `session_search` 找到原会话,确认当时的结论与产物(PR、deploy、验证记录);
2. **亲自核线上当前状态**(API + headless),因为(a)可能真回归,(b)原会话可能漏项;
3. 只对"实际仍坏"的项动手。本会话实测:6 项里 4 项已在线上修好,2 项(标题对齐、
   图片)是真残留 —— 且图片项背后还有两个新根因(坑 27/28),若只当重复消息跳过就漏了。
