# euv 框架踩坑表(consolidated index)

> **本文件是索引** — 每个坑的详细 repro / 修复 / 不该做的事放在各自 reference 文档中。

| # | 坑 | 详细 reference |
|---|---|---|
| 1 | `reactive if arm` 切换后,新 arm 的 button click handler 不响应(0.18.x 一直存在) | `references/euv-event-handler-rerender-pitfall.md` |
| 2 | `match { signal }` arm 切换后,page-level Signal 状态残留(tab 切回时 overlay/状态错位) | `references/euv-ios-tab-click-pitfall.md` + `references/portal-pitfalls.md` |
| 3 | iOS Safari 误判 `<div>` tap 为滚动 → delegated `onclick` 死(silent dead click) | `references/euv-ios-tab-click-pitfall.md` |
| 4 | fixed-aspect canvas 放进全屏容器被拉伸成椭圆 | `references/portal-pitfalls.md`(verified PR #104) |
| 5 | 移动端 header/drawer 顶部间距无条件信任 `env(safe-area-inset-top)` → letterbox 浏览器谎报 | `references/portal-pitfalls.md` + `references/mobile-web-debugging` skill |
| 6 | `euv fmt` 与 `cargo fmt --check` 不一致(impl match arm 行宽 / class! 嵌套) | `references/version-bump-summary.md` + 下方"工具冲突"段 |
| 7 | 下游工具仓(euv-docs / euv-cli) Cargo.toml 把 `euv = "*"` 浮动 → CSS API mismatch | `references/framework-engine-version-pin-rule.md` |
| 8 | bump + CI sync_workspace_version 写错版本号(regression,0.21.x → 0.21.y) | `references/version-bump-rule-2026-09-02.md` + `references/minor-bump-ci-red-by-design.md` |
| 9 | `use_async` 跨 hook arm 残留,component unmount 后仍 fire | `references/use-async-pitfalls.md` |
| 10 | `profiler` hook 集成在 hot path 上,生产 build 也要慎用 | `references/profiler-pitfalls.md` |
| 11 | Signal subscription 与 DOM 节点 lifetime mismatch → 内存泄漏 | `references/signal-subscription-bindings.md` |
| 12 | `inline_js!` / 内部 CSS minify pipeline 在某些输入爆栈 | `references/inline-js-minify.md` |
| 13 | portals / 多 root render 时 `use_node_ref` 跨 root 串号 | `references/portal-pitfalls.md` |
| 14 | signal re-render 路径(`patch_attributes` fast-path) 在某些 case 不被调用 | `references/renderer-signal-lifecycle.md` |
| 15 | css reset / keyframes 注入(`inject_app_global_css`) 与 page CSS 优先级冲突 | `references/inline-js-minify.md` |
| 16 | `crate-cli` `bump` 后漏 `git add -A`,master push 失败 | `references/version-bump-rule-2026-09-02.md` |
| 17 | euv-docs / euv-cli Cargo.toml `euv = "*"` 与框架版本不兼容 | `references/framework-engine-version-pin-rule.md` |
| 18 | release pipeline:crates.io publish 顺序写错 → path-dep resolver fail | `references/crates-io-release-pipeline-template.md` |
| 19 | `cross-repo-workflow-trigger` 限额(workflow 触发链 N 层上限) | `references/cross-repo-workflow-trigger-limits.md` |
| 20 | monorepo bump 后 sub-crate `[package] version` stale | `references/version-bump-rule-2026-09-02.md` |

## 工具冲突 quick map

| 工具 | 提供 | 不提供 |
|---|---|---|
| `euv-cli` | `watch / new / template / help / version`(实测,见 `api-cli.md`)| `bump / sync / fmt / publish`(全在 `crate-cli`)|
| `crate-cli`(`~/.cargo/bin/crate`) | `bump / sync / fmt / publish` | server / template 生成 |
| `cargo fmt` | impl 代码 | `class!` / `html!` 宏内重排 |
| `euv fmt` | `class!` / `html!` 宏内(macro-aware 重排) | impl 代码 |

## 关键词速查

- **click handler 不响应** → 坑 #1(arm 切换)、坑 #3(iOS delegated)
- **状态错位** → 坑 #2(arm 残留 Signal)、坑 #13(cross-root ref)
- **样式回退** → 坑 #7(version mismatch)、坑 #15(inject 优先级)
- **build / publish fail** → 坑 #6(fmt 不一致)、坑 #8(sync regression)、坑 #18(发布顺序)