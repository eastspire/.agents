# Mobile safe-area 与 navbar 间距:四轮迭代才修对的坑

> **场景**: euv (或任何 WASM SPA) 部署到 GitHub Pages 后,移动端浏览器顶部 navbar 距离
> 浏览器顶部"过大空白"或"被状态栏/URL bar 盖住"。
>
> 涉及: `c_mobile_app_root` / `c_mobile_header` / `use_safe_area_fix` 钩子 / `min(env, 24px)`
> 这个组合不是某次随手想出来的,而是四轮 PR 迭代后才收敛到的。
>
> 用户原话:"example 导航栏距离浏览器顶部还是很大空白"→ 之后又出现"沉浸式顶部系统
> 导航栏的安全区域没有了"。这两个看似矛盾的诉求之间,最终落点是同一个表达式。

## 1. euv 的 safe-area 取值机制(为什么 headless 测不准)

`use_safe_area_fix` (在 `ui/src/component/layout/hook/impl.rs`) 在 wasm 启动时:

1. 创建一个 `<div style="padding-top: env(safe-area-inset-top, 0px)" />` sentinel
2. `getComputedStyle(sentinel).paddingTop` 读出 **实际像素值**(Linux Chrome = 0px)
3. **缓存**到 thread-local (`SAFE_AREA_INSET_TOP`)
4. `apply_cached_insets()` 把缓存值作为 **inline style** 写到 `.c_mobile_app_root` /
   `.c_app_root`:`element.style.setProperty("--safe-area-inset-top", "47px")`
5. 后续 `c_mobile_app_root` / `c_app_nav` 里的 `var(--safe-area-inset-top)` 解析为
   47px(而不是再次调 env())

**坑**: 任何 CSS 里通过 `var(--safe-area-inset-top)` 取值的声明,真正生效的是 euv hook
**缓存**的值,不是浏览器当前的 `env()` 函数返回。`env()` 在 fullscreen exit / immersive
切换后会变 0,但 euv 的缓存值是"粘性"的,锁在 wasm 启动那一刻。

## 2. 头部 Playwright 探针为什么测出来"没问题"

第一次 PR #54 后我用 headless Linux Chrome + Android UA 测过,布局完美:
- navbar `y=0..52`,title `y=68..122`
- `env(safe-area-inset-top) = 0px`(headless 无 safe-area)

但用户**真实 Android Edge**截图里 navbar 按钮出现在 y=158 logical,URL bar 底部在
y=88 logical,中间 70px 空白。中间这 70px **其实是 navbar background 在视觉上看不见**,
因为 `c_mobile_app_root` 和 `c_mobile_header` 的 `background` 都是 `var(--background)`
= white,而 page bg 也是 white。navbar 在 safe-area padding 区域的 background 跟 page
背景同色,**肉眼看像空白页**。

**教训**: headless 测出来 y=0 不代表用户设备看到 y=0,只是 headless 测出来 navbar 的
*容器* y=0,容器里的按钮被 safe-area-inset-top padding 推下去了。**只要 navbar 容器
背景 = page 背景,用户的视觉感知就是"navbar 被推下去了"**,不管容器是否真的在 y=0。

## 3. 怎么在 headless 里复现真实设备行为(Playwright 注入)

要在 headless 里验证"沉浸式 + 24px status bar"这种真实场景,**不能**用:
```js
page.add_init_script("document.documentElement.style.setProperty('--safe-area-inset-top', '24px')")
```
因为 euv hook 在 wasm 启动时会**覆盖**根元素的这个 inline 变量,而且 hook 的缓存值是从
`env()` 函数读的,不是从你注入的 CSS var。所以 init_script 改 :root 没用。

正确做法:**在 wasm 初始化完成后**,直接 inline-set 到 hook 写值的目标元素上,模拟 hook
检测完之后的状态:

```js
await page.goto(url, {waitUntil: "networkidle"});
await page.waitForTimeout(2000);  // 等 wasm 完成 use_safe_area_fix + apply_cached_insets
await page.evaluate(() => {
    const root = document.querySelector(".c_mobile_app_root");
    if (root) {
        root.style.setProperty("--safe-area-inset-top", "24px");
        root.style.setProperty("--safe-area-inset-bottom", "0px");
    }
});
```

然后再读 `getComputedStyle(header).paddingTop` 才准确。

## 4. 四轮迭代 + 最终表达式

| PR | `c_mobile_header` 改法 | 用户反馈 | 为什么 |
|---|---|---|---|
| #53 | inner padding 24→16 (`padding-main-top-mobile`)，c_home `justify-content: flex-start` | 内层 gap 缩小 ✓ | navbar 下到内容间距修好 |
| #54 | `padding: env(safe-area-inset-top) 0 0 var(--space-lg)` + `height: calc(52 + env)` + `background: var(--background)` | "顶部空白还是很大" | env 在 Android Edge = 47~70,navbar 容器 background 同 page 色,**视觉上看不见但占 47~70px** |
| #55 | 完全去掉 safe-area,`padding: 0`, `height: 52` | "沉浸式顶部系统导航栏的安全区域没有了" | 真沉浸 (env=0) 没问题,假沉浸 (status bar 还在 / URL bar 还在) navbar 顶部被系统栏盖 |
| #56 ✅ | `padding: min(env-safe-area-inset-top, 24px) 0 0 var(--space-lg); height: calc(52 + min(...))` | (待用户验) | 同时兼顾两种场景 |

**最终表达式**:
```rust
pub c_mobile_header {
    padding: format!("min({}, 24px) 0px 0px {}", var!(safe-area-inset-top), var!(space-lg));
    height: format!("calc({} + min({}, 24px))", var!(mobile-header-height), var!(safe-area-inset-top));
    background: var!(background);
    border-bottom: format!("1px solid {}", var!(border));
    /* ... position: sticky; top: 0; ... */
}
```

`min()` 在所有现代浏览器都支持,fallback 不需要(若浏览器不支持 min(),整个 var 解析失败,
navbar 直接用默认 0 padding,反而退回到 #55 的行为,不算 worse)。

## 5. 不要做的事

- ❌ **不要**只 curl wasm / 截图验证布局就报"修复完成"。curl 看到 200 + wasm 字节加载
  不等于 layout 正确。需要 headless 浏览器实测,而且要模拟真实设备的 safe-area
  状态(见 §3)。
- ❌ **不要**把 navbar `background` 改成不同颜色来"让它可见"。euv 设计原则是 monochrome
  black/white;改 navbar bg 破坏设计系统,深色模式更乱。
- ❌ **不要**完全去掉 safe-area padding(PR #55 的错误)。会破坏真沉浸模式的 status bar
  区域覆盖。
- ❌ **不要**只在内层(c_mobile_main padding-top)修。navbar 容器本身的 height +
  padding-top 也参与布局,只改一边会留下单边空白。

## 6. 同类坑在其他框架的表现

任何在 mobile browser / PWA / WebView 里有 `env(safe-area-inset-*)` 的栈都有类似问题
(React Native Web、Tailwind 的 `pt-safe` 工具类、Flutter web、Cupertino 风格 web 组件)。
共同的判别模式:

1. UI 元素 `y=0` ≠ UI 元素 *可见* `y=0`(容器被 padding 推下去了)
2. env 值 ≠ CSS var 值(框架 hook 缓存后会脱钩)
3. 背景同色 = 视觉上看不出边界(用户会误判为"空白页")

如果以后看到"顶部空白过大"或"顶部被覆盖"的用户截图,**先**用 `vision_analyze` 量化
像素位置(URL bar 底、navbar 按钮顶、navbar border),**再**用 Playwright 在 .c_mobile_app_root
inline-set --safe-area-inset-top 复现,**最后**才动 CSS。

## 7. 关键 SHAs (euv 0.18.x navbar 修复链)

- PR #53 `bed6ae3` fix(ui): reduce mobile top whitespace between navbar and page content
- PR #54 `06725d9` fix(ui): extend mobile navbar background under notch / safe area
- PR #55 `00bfd3e` fix(ui): remove safe-area padding from mobile header *(走过头)*
- PR #56 `4d27f87` fix(ui): cap mobile header safe-area padding at 24px ✅
- 4 个 sync_workspace_version commits 把 root version 同步到 7 个 crate

修改文件: `ui/src/style/class/fn.rs::pub c_mobile_header` (一处的 padding + height)
