# euv 设计空白清单 (2026-08 实地摸底)

> Source paths: `/root/github/euv-dev/euv/{core,macros,ui,engine,cli}/src/`。
> Coverage baseline: core 6333 LOC / tests 130 LOC ≈ 2% coverage; example 29 pages / 18240 LOC.

## 状态 (2026-08-23 更新)

| 缺口 | 状态 |
|---|---|
| 🔴 P0 #1 NodeRef / DOM 引用 | ✅ 已合并 [euv-dev/euv#15](https://github.com/euv-dev/euv/pull/15) |
| 🔴 P0 #4 dangerouslySetInnerHTML (`inner_html:` attribute) | ✅ 已合并 [euv-dev/euv#16](https://github.com/euv-dev/euv/pull/16) |
| 其余 18 项 | ❌ 待办 |

**给新 html! attribute 的标准流程**已抽出到 SKILL.md §18,本文件继续记录 18 项剩余缺口和验证命令。

## 验证方法

每个缺口都用 ripgrep 在源码里搜过 —— "0 结果" = 框架级 API 缺失,不是没找到合适关键词:

```bash
# Ref / DOM 引用 — 应有但没有
rg -l "use_node_ref|NodeRef|forwardRef" /root/github/euv-dev/euv/{core,ui,macros}/src
# → 0

# async data fetching — 应有但没有
rg -l "use_async|use_resource|Suspense|ErrorBoundary" /root/github/euv-dev/euv
# → 0

# SSR / 字符串渲染
rg -l "render_to_string|hydrate|StaticRender" /root/github/euv-dev/euv
# → 0

# Portal
rg -l "create_portal|teleport" /root/github/euv-dev/euv
# → 0

# dangerouslySetInnerHTML
rg -l "inner_html|dangerouslySetInnerHTML|raw_html" /root/github/euv-dev/euv/macros
# → 0

# Form / FormAction
rg -l "FormData|useFormStatus|form_action" /root/github/euv-dev/euv
# → 0

# 嵌套路由 / Outlet
rg -l "nested_route|<Outlet>|sub_route" /root/github/euv-dev/euv
# → 0
```

确认**有的**(避免误判):
```bash
# Fragment — 有(走 <slot style="display:contents">)
rg "Fragment" /root/github/euv-dev/euv/core/src/vdom/node/enum.rs

# use_window_event / use_interval / use_cleanup — 有
rg "pub fn use_" /root/github/euv-dev/euv/core/src/app/impl.rs

# 路由 + popstate + overlay history — 有
ls /root/github/euv-dev/euv/ui/src/component/router/

# 热重载 — 有(/__euv_reload endpoint)
rg "RELOAD_ROUTE" /root/github/euv-dev/euv/cli/src/build/const.rs

# TransitionEvent / MediaStream 等 web-sys feature — 已开
rg "TransitionEvent|MediaStream" /root/github/euv-dev/euv/Cargo.toml
```

## 缺口清单(按影响度排序)

### 🔴 P0 — 缺了等于"框架级"的东西

**1. 没有 Ref / DOM 引用机制**
所有需要拿 DOM 的组件(焦点、measure、canvas、第三方库)都自己 `document.get_element_by_id(...)` + `dyn_into`,见 `ui/src/component/virtual_list/hook/impl.rs:114` 和 `example/src/page/file/hook/fn.rs:84`。期望 API:
```rust
let input_ref: NodeRef<HtmlInputElement> = use_node_ref();
html! { input { ref: input_ref.clone() } }
input_ref.get().map(|el| el.focus());
```

**2. 没有 async data fetching 模型**
- ❌ `use_async` / `use_resource` / `Suspense` —— 0 结果
- ❌ `useTransition` / `startTransition`
- ❌ `ErrorBoundary`

后果:`fetch().await` + signal.set 必须走 `wasm_bindgen_futures::spawn_local`,但**不在 hook 上下文**(同 skill §8 已记的 silent panic)。现代 web app 数据流脊柱缺失。

**3. 没有 SSR / 字符串渲染**
`render_to_string` / `hydrate` / `StaticRender` 全 0。意味着 SEO、邮件 HTML、VDOM snapshot test 都做不了。

**4. 没有 dangerouslySetInnerHTML**
之前用户问过 inline `<script>` —— 框架不走 `eval`/innerHTML 路径。Markdown 渲染产物 / 第三方 widget HTML 字符串没法注入。建议加显式 opt-in `html! { div { raw_html: trusted_string } }`(防 XSS 文档化)。

### 🟠 P1 — 严重阻塞常见场景

**5. 没有 Portal** — Modal/Drawer/Tooltip 渲染到 `<body>` 末尾避免被父 `overflow:hidden` 裁掉,目前要退出 VDOM 手动 `append_child`。

**6. 没有 Transition / AnimatePresence** — 出场/退场动画只能 CSS transition + signal,难做。

**7. 路由只支持扁平** — `euv_routes` 是 path → component 字典,**没有嵌套 layout / `<Outlet>`**。共享侧栏得每页手动包。

**8. 测试覆盖率 ~2%** — core 6333 LOC / tests 130 LOC(3 files)。重构是赌博。

**9. CLI dev server HMR 是整页 reload** — `/__euv_reload` 走 `location.reload()`,signal/route/scroll 全丢。Solid/Vite 是 hot-swap 组件保留 state。

### 🟡 P2 — 体验级

**10. 没有 useEffect / onMount / onUnmount** — 搜不到。生命周期要么 `watch!`(易死循环)、要么 `App::use_window_event` / `App::use_cleanup`(更底层不像 hook)。React 用户困惑。

**11. 没有 Form / FormAction** — React 19 `form-as-action` 模式没有;表单就是裸 `oninput`。

**12. 没有 dev-only assertions / `<Debug />`** — Solid `<Show when={DEBUG}>` 包子树,euv 没。

**13. TS 类型质量低** — wasm-bindgen 生成的 `.d.ts` 把 Signal / VirtualNode 全暴露成 `any`,拒真 TS 用户。

**14. 没有 `<KeepAlive>` 路由缓存** — example 里 `page_keep_alive` 是手撸的。

**15. 没有 `lazy()` / 路由级代码分割** — 所有 page 静态进 wasm bundle。

### 🟢 P3 — 锦上添花

16. 没有 SSR streaming / RSC
17. 没有 Profiler / Performance API 集成
18. 没有 `unsafe_no_inline` escape hatch(高级用户裸 JSX)
19. Fragment 没有 keyed diff(走 positional,见 `core/src/renderer/render/impl.rs:464`)
20. 没有 i18n / l10n helper

## 建议优先级(就开发 ROI 排)

如果只能做 3 个:

1. **Ref / NodeRef** — 解锁 canvas / focus / measure / 第三方库集成,所有"非纯渲染"场景的入口
2. **use_async + Suspense + ErrorBoundary 三件套** — 现代 web app 数据流脊柱
3. **测试覆盖率拉到 30%+** — snapshot test + signal lifecycle test,极大降低后续 PR 风险

第三个性价比最高:现在每改一个 macro/signal 行为都是薛定谔。

## 与 euv-game-real-api-notes 的关系

那份 skill 已经记录了部分 hook panic / canvas escape hatch 的实战坑。本文件聚焦**框架级 API 缺口**(feature comparison 角度),两份互补:
- `euv-game-real-api-notes` — 用 euv 搭游戏时的踩坑记录 / workaround
- 本文件 — 框架本身缺什么 / 应该有什么
