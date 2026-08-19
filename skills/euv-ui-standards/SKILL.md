---
name: euv-ui-standards
description: '**euv UI 设计规范 + 306 个全局 class! + 22 个 euv_* 组件 + 29 个 example page — 用 euv 写页面/组件/UI 时必加载**。涵盖：(1) 全局 class! 注册表（`ui/src/style/class/fn.rs`，共 306 个，按 c_page_/c_home_/c_euv_button_/c_card_/c_modal_/c_vconsole_/c_nav_/c_app_/c_mobile_/等前缀分组）；(2) design tokens（`vars!` 主题变量 — monochrome 黑/白 + light/dark，spacing 阶 / 字号阶 / 圆角 / 阴影 / 缓动 / safe-area）；(3) 22 个 euv_* 组件 API + HTML 结构：渲染组件（euv_button / euv_card / euv_badge / euv_tag / euv_alert / euv_input / euv_checkbox / euv_field / euv_modal / euv_loading / euv_info / euv_logo / euv_header / euv_virtual_list — select/textarea 是 §3.7/§3.8 的裸 div，不用 euv_select）、导航组件（euv_nav_items / euv_nav_item / euv_mobile_nav_item）、路由组件（euv_routes / euv_page_router）、调试组件（euv_vconsole_panel / euv_vconsole_fab / euv_vconsole_drawer）；(4) 全 29 个 example page 列表（about / animation / async / attrs / badge / binding / browser / camera / canvas / conditional / counter / dynamic / event / file / form / game_2d / game_3d / keep_alive / lifecycle / list / modal / not_found / observer / select / sse / timer / virtual_list / webgpu_status / websocket + 1 个 home_page 入口）；(5) page 标准模板（用 `euv_header` 包装标题/icon/subtitle，27/29 页都用此模式，仅 about 是 hero 自定义）；(6) 响应式（唯一断点 `@media (max-width: 767px)`）+ 深色模式 + a11y（focus-visible 隐藏由 border 反转表达 / touch tap-highlight / prefers-reduced-motion）。触发词:euv ui, euv-ui, euv class!, euv_header, euv_field, euv_virtual_list, euv_routes, euv_vconsole, design tokens, design system, euv design system, 306 class, euv utility, btn class, card class, modal class, form class, euv page template, euv responsive, euv dark mode, euv theme, vars! 主题, spacing scale, color palette, typography scale, euv atomic CSS。**当且仅当任务完全不涉及 euv UI 页面/组件/样式**才不加载。'
  euv example/example 项目 UI 设计系统全量规范。涵盖 306 个全局 class!（注册于 `ui/src/style/class/fn.rs`，单一真源）、design tokens（colors / spacing / font-size / transition / safe-area）、22 个 euv_* 组件 HTML 结构（euv_header / euv_field / euv_button / euv_card / euv_badge / euv_tag / euv_alert / euv_input / euv_checkbox / euv_modal / euv_loading / euv_info / euv_logo / euv_virtual_list + 路由/导航/调试三组 euv_routes / euv_page_router / euv_nav_items / euv_nav_item / euv_mobile_nav_item / euv_vconsole_panel / euv_vconsole_fab / euv_vconsole_drawer — select/textarea 见 §3.7/§3.8 裸 div）、页面骨架（app 壳、page_router、page_container，**所有非 hero page 都以 `euv_header { icon title subtitle }` 开头**）、断点（@media (max-width: 767px)）、响应式规则、class 编写约定（不在 page 内写 class! 块）。触发词：euv UI、euv 样式、euv design token、c_page_container、c_home_、c_euv_button、c_card、c_badge、c_euv_tag、c_euv_input、c_modal_content、c_nav_item_active、c_app_root、c_app_nav、c_app_main、euv_header、euv_field、euv_routes、euv-ui-standards。
---

# euv example 项目 UI 设计规范（全量）

你正在为 **euv framework** 的 example / app 项目编写 UI。example 项目的 UI 必须遵守本规范，否则与设计系统冲突。

---

## Index

| I want to... | Jump to |
| --- | --- |
| Find the source files that define all 306 classes | [Source of Truth](#0-source-of-truth) |
| Use `var!(xxx)` to reference colors / spacing / fonts | [Design Tokens](#1-design-tokens) |
| Build the app shell, page container, nav, main area | [Global Skeleton](#2-global-skeleton) |
| Use a built-in component (button / card / badge / tag / alert / input / checkbox / nav / header / field / virtual_list / vconsole / routes) | [Core Component HTML Templates](#3-core-component-html-templates) |
| Build the special Home / Hero page layout (only `/about`) | [Home / Hero Page Spec](#4-home--hero-page-spec) |
| See all 29 example pages & their hooks | [All 29 example Pages — 速查表](#4a-all-29-example-pages--速查表) |
| Name a new class correctly (c_ prefix, page scope) | [Class Naming Conventions](#5-class-naming-conventions) |
| Apply responsive rules and breakpoint behavior | [Responsive / Breakpoints](#6-responsive--breakpoints) |
| Add a11y / touch optimization / safe-area | [Accessibility / Touch](#7-accessibility--touch) |
| Scaffold a brand-new page using `euv_header` | [New Page Standard Template](#8-new-page-standard-template) |
| Recall forbidden patterns at a glance | [Quick Notes / Anti-Patterns](#9-quick-notes--anti-patterns) |

---

## 0. Source of Truth

- 全局 class! 注册表（**306 个 class，单一真源**）：`ui/src/style/class/fn.rs`（约 3338 行）
- 全局 vars! token：`ui/src/style/var/fn.rs`（light + dark 主题，约 285 行）
- 全局 CSS reset & keyframes：`ui/src/style/css/fn.rs`（由 `inject_app_global_css()` 注入）
- 22 个 euv_* 组件 view HTML：`ui/src/component/<name>/view/fn.rs`
  - 渲染组件：alert / badge / button / card / checkbox / field / header / info / input / loading / logo / modal / tag / virtual_list（14）
  - 导航：nav（提供 euv_nav_items / euv_nav_item / euv_mobile_nav_item）（3+1）
  - 路由：router（提供 euv_routes / euv_page_router）（2）
  - 调试：vconsole（提供 euv_vconsole_panel / euv_vconsole_fab / euv_vconsole_drawer）（3）
  - 工具 hook-only：theme（主题切换）/ touch（手势） / browser / camera / layout（这些不在模板里写 euv_* 调用，只在 hook/ 文件内供其他组件消费；不进 euv_* 渲染树）
- 项目内二次封装（仅供 example 调用、不得新增全局 class）：`example/src/style/class/fn.rs`（16 个本地 class：`c_game_*` / `c_keep_alive_*` / `c_binding_*` / `c_canvas_pixelated` / `c_anim_scale_*` / `c_slider_value` 等）
- 29 个 example page：`example/src/page/<name>/{mod,view/fn}.rs`（27 用 `euv_header` 开头，仅 `about` 是 hero 自定义；`not_found` 也用 euv_header）

| 数量类别         | 数值        | 验证命令                                       |
| ---------------- | ----------- | ---------------------------------------------- |
| 全局 class       | 306         | `grep -oE '\bc_[a-z_]+\b' ui/src/style/class/fn.rs | sort -u | wc -l` |
| example 本地 class | 16         | `grep -oE '\bc_[a-z_]+\b' example/src/style/class/fn.rs | sort -u | wc -l` |
| euv_* 组件       | 22          | `ls ui/src/component/*/view/fn.rs | wc -l`（参与渲染的函数） |
| example page     | 29          | `ls example/src/page | grep -v mod.rs | wc -l` |

> **强制约束**：
> 1. **所有 class! 块都在 `ui/src/style/class/fn.rs` 这一个文件里维护**，page 自己的 `view/fn.rs` **不写** `class! { … }` 块，**只引用** `c_xxx()` 函数。
> 2. **必须以 `c_` 前缀 + page/component 名 + 元素名** 命名（例：`c_video_list_viewport`、`c_home_title`、`c_euv_button_primary_md`）。
> 3. 跨 page 复用的样式，命名里不带 page 名（如 `c_card`、`c_euv_button_primary_md`、`c_app_root`）。

---

## 1. Design Tokens

### 1.1 颜色（黑/白单色设计 — shadcn / monochrome）

```
                 light          dark
background   ── #ffffff   ──  #000000
foreground   ── #000000   ──  #ffffff
muted-fg     ── #000000   ──  #ffffff
accent       ── #000000   ──  #ffffff
accent-muted ── #ffffff   ──  #000000
border       ── #000000   ──  #ffffff
ring         ── #000000   ──  #ffffff
text-on-accent (色上文字) ─ #ffffff (光) / #000000 (暗)
bg-overlay   ── rgba(0,0,0,0.45) / rgba(0,0,0,0.60)
```

注意：`muted-foreground` 在 light 下与 foreground 同色，但**语义不同** — 用于次级文字/占位。
阴影、滚动条都只用黑/白 alpha，永远**不引入彩色**。

### 1.2 间距（shadcn/ui Tailwind 间距）

| token        | px  |
| ------------ | --- |
| `space-2xs`  | 2   |
| `space-xs`   | 4   |
| `space-sm`   | 8   |
| `space-md`   | 12  |
| `space-lg`   | 16  |
| `space-xl`   | 20  |
| `space-2xl`  | 24  |
| `space-3xl`  | 32  |
| `space-4xl`  | 40  |
| `space-7xl`  | 80  |

**复合间距 token**（更常用，优先用）：

| token                       | 用途                           |
| --------------------------- | ------------------------------ |
| `gap-section`               | 区块间距 16                    |
| `gap-section-mobile`        | 12                             |
| `gap-component`             | 组件间距 12                    |
| `gap-component-mobile`      | 10                             |
| `gap-element`               | 元素间距 8                     |
| `gap-inline`                | 行内间距 8                     |
| `page-block-gap`            | 页面块垂直间距 24              |
| `page-block-gap-mobile`     | 20                             |
| `padding-main-top/bottom`   | 主区域 24                      |
| `padding-main-horizontal`   | 主区域桌面 28                  |
| `padding-main-horizontal-mobile` | 主区域移动 16             |
| `gap-page-header`           | 页头 16                        |
| `gap-page-title`            | 标题间距 6                     |
| `safe-area-inset-{top,right,bottom,left}` | `env(safe-area-inset-*)` |
| `padding-shell-top/bottom`  | 同 safe-area-inset-*           |
| `min-height-base` / `min-height-sm` | 控件最小高 36          |
| `nav-width`                 | 桌面导航宽 248                 |
| `content-max-width`         | 内容最大宽 820                 |
| `mobile-header-height`      | 移动 header 高 52              |

### 1.3 字体（无 web font，system-ui）

```css
font-family: system-ui, -apple-system, sans-serif;
font-family（代码）: ui-monospace, monospace;
```

| token      | rem    | px      |
| ---------- | ------ | ------- |
| `font-xs`  | 0.75   | 12      |
| `font-sm`  | 0.875  | 14      |
| `font-base`| 1      | 16      |
| `font-md`  | 1.125  | 18      |
| `font-lg`  | 1.125  | 18      |
| `font-xl`  | 1.25   | 20      |
| `font-2xl` | 1.5    | 24      |
| `font-3xl` | 1.875  | 30      |
| `font-4xl` | 2.25   | 36      |
| `font-5xl` | 3      | 48      |
| `font-6xl` | 3.75   | 60      |

font-smoothing: `antialiased`（webkit）/ `grayscale`（moz）。
text-rendering: `optimizeLegibility`。

### 1.4 圆角

几乎全用 **`border-radius: 0px`**（直角、shadcn-sharp 风）。
例外只在交互控件：

- `c_binding_slider`、`c_canvas_fullscreen_range_input`：thumb `50%`，track `3px`。
- `c_spinner`：圆环 `50%`。

### 1.5 阴影（几乎不用）

唯一全局 token：

```css
shadow-sm:      0 1px 3px rgba(0,0,0,.08), 0 1px 2px rgba(0,0,0,.04)   /* light */
shadow-modal:   0 25px 50px -12px rgba(0,0,0,.18)
shadow-drawer:  4px 0 20px rgba(0,0,0,.08)
shadow-accent-sm:  0 1px 3px rgba(0,0,0,.08)
shadow-accent-lg:  0 10px 15px -3px rgba(0,0,0,.12)
```

dark 主题下 alpha 用白色（255,255,255,...）。**绝不要自己写 CSS box-shadow**，先看 var 里有没有。

### 1.6 动画与过渡

全局 keyframes（在 `inject_app_global_css` 内）：

- `euv-spin`：rotate 0→360
- `euv-fade-in`：opacity 0+4px → 1+0
- `euv-pulse`：scale 1↔1.15
- `euv-progress`：width 0%→100%
- `euv-scale-in-modal`：opacity + translateY(24) scale(.95) → 1 / 0 / 1

过渡 token：

| token                    | 值                                  |
| ------------------------ | ----------------------------------- |
| `duration-fast`          | 0.15s                               |
| `duration-normal`        | 0.2s                                |
| `duration-slower`        | 0.4s                                |
| `duration-overlay`       | 0.2s                                |
| `duration-modal-overlay` | 0.15s                               |
| `duration-modal-content` | 0.3s                                |
| `ease-out`               | `cubic-bezier(0.4, 0, 0.2, 1)`      |
| `ease-in`                | `cubic-bezier(0.4, 0, 1, 1)`        |
| `ease-in-out`            | 同 ease-out                         |
| `ease-bounce`            | `cubic-bezier(0.34, 1.56, 0.64, 1)` |

transition 写法：``format!("{property} {duration} {ease}", var!(duration-fast), var!(ease-out))``。

### 1.7 滚动条

- 桌面：`::-webkit-scrollbar { width: 6px }`，thumb `border-radius: 0`，半透明黑（光）/ 白（暗）。
- 移动（max-width: 767px）：隐藏滚动条（`scrollbar-width: none`）。

### 1.8 全局 Reset（`c_app_root` 注入，必背）

```
*, *::before, *::after { box-sizing: border-box }
h1..h6, p, ul, ol, dl, dd, figure, blockquote, pre, hr { margin:0; padding:0 }
a { color: inherit; text-decoration: none }
button { appearance:none; border:none; padding:0; margin:0; background:transparent; font:inherit; cursor:pointer }
input/textarea/select { font:inherit; background:transparent; border:none; outline:none; appearance:none }
img/svg/video/canvas/audio/iframe/embed/object { display:block; max-width:100% }
:focus-visible { outline: none }    // 隐藏焦点环 — 通过 box-shadow 自定义
strong/b { font-weight:700 } em/i { font-style:italic }
code/pre/kbd/samp { font-family: ui-monospace, monospace }
// 移动端 input/select/textarea { font-size: 16px } 防止 iOS 缩放
```

⚠️ 所有 input 默认 16px（移动端），不要覆写成更小，会触发 iOS 自动放大。

---

## 2. Global Skeleton

### 2.1 App 根

```
c_app_root           flex; height:100%; safe-area padding; background:var!(background); color:var!(foreground)
c_app_nav (desktop)  width:var!(nav-width)=248px; border-left:2px solid var!(border); flex-direction:column
                     @media (max-width:767px) { display:none }
c_app_main           flex:1; height:100%; overflow:auto; padding:var!(padding-main-top) var!(padding-main-horizontal) var!(padding-main-bottom) ...;
                     @media (max-width:767px) padding 改 24/16/24/16; scrollbar-width:none
```

### 2.2 Page（**所有 page 共用入口**）

```
div class=c_page_router  flex:1; display:flex; flex-direction:column
  div class=c_page_container  width:100%; max-width:var!(content-max-width)=820; margin:0 auto
    // 各 page 内容（典型顺序）
```

**所有 29 个 example page 中的 27 个** 用 `euv_header` 组件开头（见 §3.X），而不是裸 div page header：

```
div class=c_page_router
  div class=c_page_container
    euv_header { icon:"🎬" title:"Animation" subtitle:"CSS transitions…" }
    euv_card { title: "..."
      // 内容
    }
    euv_card { title: "..." ... }
```

> ⚠️ **仅 `about` page** 用裸 div + `c_page` / `c_page_glow` / `c_page_content` / `c_page_icon` / `c_page_title` / `c_page_subtitle` 自己拼 hero —— 这是 §4 Home / Hero Page Spec 的唯一用户。所有其它 page 一律走 `euv_header`。

**`euv_header` 展开后的裸 div 结构**（仅在你不能用 `euv_header` 时参考，比如 SSR 渲染场景）：

```
div class=c_page                // position:relative; text-align:center
  div class=c_page_glow         // 装饰性径向光（绝对定位）
  div class=c_page_content      // position:relative; z-index:1
    div (可选) class=c_page_icon        // 36px / 移动 40px; padding-bottom: var!(space-md)
    h1 class=c_page_title               // font-size:var!(font-4xl); font-weight:800; letter-spacing:-0.03em; mobile font-3xl
    p  class=c_page_subtitle            // var!(font-lg); color:var!(muted-foreground); max-width:560px; mobile font-base
```

### 2.3 移动端（< 768px）

- 桌面 `c_app_nav` 隐藏
- 顶部出现 `c_mobile_header`（sticky top:0, height `mobile-header-height`=52, border-bottom:1px solid var(--border), z-index:100）：
  - 左侧 `c_mobile_menu_button`（40×40，emoji "≡" 或 svg）
  - 中间 logo
  - 右侧 `c_mobile_theme_button`（40×40）
- 点击菜单后：底部遮罩 + 左侧 drawer（`c_mobile_nav_drawer` width 240, `translateX(-100%)` ↔ 0）
- drawer 用 `transform` + `transition` 滑入，不用 `display` 切。

### 2.4 Nav（桌面侧栏）

```
nav c_app_nav
  a c_nav_header                       // padding:space-xl space-xl; flex; gap:space-md; position:relative
    ::after                            // 底部 1px 渐变线（trans-border-trans）
    span (logo, 32px)
    span c_nav_brand_title             // font-xl, 700, letter-spacing:-0.02em
  p c_nav_section_label                // 区间标签：xs/12px/20; padding space-md/xl/xs/xl; uppercase; letter-spacing:0.10em; font-xs
  div c_nav_items_scroll               // flex:1 overflow:auto
    a c_nav_item_inactive              // 默认
    a c_nav_item_active                // 选中: bg=accent color=text-on-accent font-weight:600
                                       // hover(inactive): bg=accent-muted; color=accent; 左侧 4px 内嵌 border
  div c_nav_theme_toggle               // 桌面专属；移动 hidden
    button c_nav_theme_button          // 1px dashed border; 36 high
      span c_theme_icon_sun/_moon      // 20×20，data-url SVG
  div c_nav_footer                     // 上 1px 渐变线 + 版权文字
    span c_nav_footer_text
    span c_nav_footer_brand            // font-weight:700 color:var!(accent)
```

`c_nav_item_*` 共用：padding `space-md space-xl`，gap `space-sm`，font-base；icon `c_nav_item_icon { flex-shrink:0 }`，label `c_nav_item_label { flex:1 }`。

---

## 3. Core Component HTML Templates

### 3.1 Button（`euv_button`，**唯一**主按钮/轮廓按钮）

```
euv_button { variant: Primary | Outline  label: "..."  onclick: handler }
```

`Primary` → `c_euv_button_primary_md`：
- display:flex; justify/align:center; gap:space-sm
- **flex:1 1 120px**（自适应多按钮行），height:42
- padding 0 space-xl；background var!(accent)；color text-on-accent
- font-base/500；white-space nowrap；user-select none
- :hover = active state；:disabled = bg muted-foreground + cursor not-allowed
- :active 不变色（与 accent 同色）

`Outline` → `c_euv_button_outline_md`：
- 同结构，color foreground；border 1px solid var!(border)
- :hover { bg accent-muted; border-color accent; color accent }

**禁止**：自定义 `<button>` 写自己的 class。除非你是写"主页面 hero 大按钮"那种用例，使用 `c_home_btn_primary/secondary`（已经是 1.5px 边、space-sm/space-2xl padding）。

按钮成组：包一层 `c_button_controls` (display:flex; flex-wrap:wrap; gap:gap-element; margin-top:gap-component)。

### 3.2 Card（`euv_card`）

```
euv_card { title: "…"  children }
→ <div class=c_card><h3 class=c_card_title>…</h3>children</div>
```

`c_card` 仅设 color+box-sizing。**注意**：euv 项目**几乎不用卡片边框/底色**（因为黑/白极简），如需分区用 `c_card_title` 的 dashed 下划线：

```
c_card_title {
  margin: var!(gap-component) 0px;
  font-size: var!(font-lg) ; font-weight: 600;
  padding-bottom: var!(gap-component);
  border-bottom: 1px dashed var!(border);
  letter-spacing: -0.01em;
  // mobile font-md
}
```

### 3.3 Badge（`euv_badge`）

```
euv_badge { text outline on_click }
```

`c_badge`（实色）：inline-flex；padding `space-2xs space-sm`；border `1px solid var!(accent)`；bg accent；color text-on-accent；font-xs/600。

`c_badge_outline`（线框）：同结构、bg 透明、color foreground、border `1.5px solid var!(border)`。

多枚徽章：包 `c_badge_row`（flex; gap:gap-inline; flex-wrap:wrap; align-items:center）。提示文本 `c_badge_hint`。

### 3.4 Tag（`euv_tag`，语义标签，4 变体）

```
euv_tag { variant: Solid | Outline  color: Black | White  text  on_click }
```

| 类                       | 适用场景                                       | 关键样式                                                    |
| ------------------------ | ---------------------------------------------- | ----------------------------------------------------------- |
| `c_euv_tag_solid_black`  | 浅色主题上的实心黑标                           | bg accent，color text-on-accent，padding space-xs/space-md   |
| `c_euv_tag_solid_white`  | 深色主题上的实心白标                           | border `1.5px solid accent`                                 |
| `c_euv_tag_outline_black`| 黑边描边（在浅底上）                           | border `1.5px solid accent`，color accent，xs/sm            |
| `c_euv_tag_outline_white`| 白边描边（在深底上）                           | border `1.5px solid border`，color foreground               |

均 font-weight:600 + cursor:pointer（可点击）。尺寸比 badge 大一档：sm 字号。

### 3.5 Alert / Error / Success

```
euv_alert { variant: Error | Success  children }
```

`c_error_box` / `c_success_box`：margin gap-component 0；background accent-muted；color foreground；font-base；box-sizing border-box。

**错误/成功视觉差异不是颜色，是图标 + 文案**。两者类一致。

### 3.6 Input

```
euv_input { value on_change placeholder… }
```

`c_euv_input`：
- width:100%; min-height 36px（var!）
- padding `0 space-lg`（左右 16）
- border `1px solid var!(border)`
- :hover/:focus { border-color accent; bg accent-muted }  ← 极简交互色反转

错误态：`c_euv_input_error`（border `1px solid var!(foreground)`，仍是黑色，**靠加粗边框表达错误**）。

行布局：包 `c_euv_input_wrapper`（width 100%; margin `gap-element 0`）。

行内（input + button 一行）：`c_inline_input_row`（flex）+ `c_inline_input_button_wrap`（flex-shrink 0）。

### 3.7 Textarea

`c_textarea_input`：同 input 但 padding `space-md space-lg`，resize vertical，word-wrap break-word，font-family inherit。计数行 `c_textarea_counter` (text-align right) + `c_textarea_counter_text` (font-sm)。

### 3.8 Select

`c_select_input` 与 input 一致外观。Chevron 用背景图标或裸 ▼，**不依赖浏览器原生外观**。

### 3.9 Checkbox

```
euv_checkbox { id name autocomplete checked label }
→ <div c_form_checkbox_row>
    <input type=checkbox class=c_form_checkbox id=… name=… checked …>
    <label for=… class=c_form_checkbox_label>label</label>
  </div>
```

`c_form_checkbox` (16×16 box，cursor pointer)；`c_form_checkbox_label` font-base + inherit；行 `c_form_checkbox_row { margin: gap-component 0px }`。

### 3.10 Form Label

`c_form_label`（display block; margin-bottom space-sm; font-base/500）— 跟随 form_label 写。

### 3.11 Info（键值对行）

```
euv_info { label "…" }
→ <div c_info_row>
    <span c_info_label>label</span>
    <span c_info_value>value</span>     // 自动省略 + ui-monospace + 600 weight
  </div>
```

label：min-width 72px, flex-shrink 0, font-sm/500/muted-foreground, letter-spacing 0.02em。
value：flex:1, ui-monospace, font-base/600, **省略处理由 c_text_ellipsis 注入**。
链接版 `c_info_link`（color accent + ui-monospace）。两者共用 c_text_ellipsis。

### 3.12 Nav Item（已在 2.4）

### 3.13 Logo

`euv_logo`：`background accent`；color text-on-accent；正方形；`c_euv_logo_nav` 32×32 font-lg；`c_euv_logo_fab` 36→44（mobile）。

### 3.14 Loading / Spinner

`c_loading_container { display:flex }` + `c_loading_text_col` + `c_loading_title`（color foreground）+ `c_loading_subtitle`（muted-foreground）。
Spinner: `c_spinner { width:28px; border-radius:50%; animation: euv-spin 0.8s linear infinite }`。
Overlay: `c_loading_overlay(background: &str)` 接受一个背景色参数（绝对定位覆盖层）。

### 3.15 Modal

```
euv_modal { open children }
→ <div c_modal_overlay>     // fixed; bg var!(bg-overlay); z-index:1000; euv-fade-in
    <div c_modal_content>   // max-width 480 / mobile calc(100% - 32); euv-scale-in-modal 0.3s ease-bounce
      <div c_modal_header flex>
        <h3 c_modal_title margin:0>title</h3>
        <button c_modal_close_button>×
      </div>
      <div c_modal_body padding:0 space-xl space-md space-xl>children</div>
      <div c_modal_actions flex>…</div>
    </div>
  </div>
```

- 移动端（max-width: 767px）：`max-width:100%; width:calc(100% - 32px); max-height:85vh; overflow-y:auto`。
- 关闭按钮：`c_modal_close_button` 有 transition opacity 0.15s。

### 3.16 Tabs（手写，无组件）

```
div c_tab_bar (flex; border-bottom:1px dashed var!(border); gap:gap-element; mb:gap-component)
  button c_tab_item_active   { padding:space-md space-xl; color:text-on-accent; bg:accent; font-weight:600 }
  button c_tab_item_inactive { padding:space-md space-xl; color:foreground; font-weight:400; :hover bg:accent-muted color:accent }
```

### 3.17 List

`c_list_ul { list-style:none }`；行 `c_list_item { display:flex; justify:space-between; align-items:center; gap:gap-component; min-height:36; margin:gap-element 0 }`；左 `c_list_item_text { flex:1 }`；右操作 `c_list_item_button { max-width:120px }`。

### 3.18 Event / Drag-drop / Wheel / Touch / Form

均有 area-marker class（`c_event_drag_zone { border:2px dashed var!(border); padding:space-4xl space-xl; text-align:center; cursor:pointer }`，active 态 `c_event_drop_zone_active { border:2px dashed var!(accent); background:var!(accent-muted) }`），均复用 4xl/40px 内边距。

### 3.19 Counter

`c_counter_row { display:grid; grid-template-columns:1fr 1fr; gap:gap-component }`，移动 1 列；`c_counter_value { font-2xl/700 color:var!(accent) }` 移动降 font-xl。

### 3.20 Animation

- Fade：`c_anim_fade_in { margin-top:gap-component; animation:euv-fade-in 0.5s var!(ease-out) }`
- Spin：`c_anim_spin { font-5xl; animation:euv-spin 1.5s linear infinite }`；停止版 `c_anim_spin_stopped { font-5xl }`（同时存在，切换类）。
- Pulse：`c_anim_pulse { font-5xl; animation:euv-pulse 1.5s ease-in-out infinite }`；停止版 `c_anim_pulse_stopped`
- Scale：`c_anim_scale_box { transition:transform var!(duration-normal) var!(ease-out) }` + 子用 `c_anim_scale_shrink { transform:scale(.85) }` / `c_anim_scale_normal { transform:scale(1) }`

### 3.21 Progress

`c_progress_container { width:100%; height:12; margin:space-lg 0; overflow:hidden }`；running `c_progress_bar_running { background:var!(accent); animation:euv-progress 1.6s var!(ease-in-out) forwards }`；stopped bar `c_progress_bar_stopped` 不动。

### 3.22 Camera / Canvas / Game

属于 example 内 page 才用的辅助类，统一写在 `example/src/style/class/fn.rs`：
- `c_game_stats_bar / c_game_stats_label / c_game_description / c_game_canvas_wrapper(ar) / c_game_3d_canvas / c_game_2d_canvas / c_canvas_pixelated / c_game_loading_overlay / c_game_stats_count_value / c_game_stats_fps_value / c_game_stats_total_value`
- `c_keep_alive_tab_visible / c_keep_alive_tab_hidden` / `c_binding_slider_label_accent` / `c_binding_color_preview_bg(bg)` / `c_anim_scale_shrink / c_anim_scale_normal / c_slider_value`

⚠️ 命名 + 前缀约定：**`c_<page>_<element>`**（如 `c_keep_alive_*`），不污染全局 ui 包。

### 3.A euv_header — **所有 27/29 page 的事实入口**（组件层封装，不是裸 div）

```rust
euv_header {
    icon: "🎬"
    title: "Animation"
    subtitle: "CSS transitions, keyframe animations, and reactive style cha..."
}
```

Props（强类型 `EuvHeaderProps`）：

| 字段      | 类型             | 必填 | 说明                                          |
| --------- | ---------------- | ---- | --------------------------------------------- |
| `icon`    | `&'static str`   | ✓    | emoji 图标，3xl 字号（桌面） / 2xl（移动）    |
| `title`   | `&'static str`   | ✓    | 主标题 → `h1 class=c_page_title` (font-4xl)   |
| `subtitle`| `&'static str`   | ✓    | 副标题 → `p class=c_page_subtitle` (font-lg)  |

**展开后的 DOM**：
```
div.c_page                flex column; text-align:center; mb:space-xl (mb:space-lg 移动)
  div.c_page_glow         装饰性径向光 (absolute)
  div.c_page_content      relative; z-index:1
    div.c_page_icon       font-3xl (2xl 移动); pb:space-md
    h1.c_page_title       font-4xl/800 (-0.03em)  → font-3xl 移动
    p.c_page_subtitle     font-lg/muted-fg/max-width:560px → font-base 移动
```

> 看到 page 第一行是 `euv_header {...}` 而不是手撸 div 即知道是「现代 page」；只有 `about`（hero 页）走裸 div + `c_home_*` 路径。

### 3.B euv_field — 表单 label + input + error 三件套（替换 §3.6 里的「裸 label + input」模式）

```rust
euv_field {
    id: "username"
    name: "username"
    label: "用户名"
    input_type: "text"
    placeholder: "请输入用户名"
    autocomplete: "username"
    value: signal_username_value
    error: signal_username_error        // Option<Signal<String>>，非空时切 error 样式
    // oninput 留 None 自动绑 on_input_value(value)
}
```

Props（强类型 `EuvFieldProps`）：

| 字段            | 类型                          | 必填 | 说明                                                                 |
| --------------- | ----------------------------- | ---- | -------------------------------------------------------------------- |
| `id`            | `&'static str`                | ✓    | `<label for>` + input `id`                                           |
| `name`          | `&'static str`                | ✓    | input `name`                                                         |
| `label`         | `&'static str`                | ✓    | label 文案                                                           |
| `input_type`    | `&'static str`                | ✓    | `text` / `email` / `password` / `number` 等                          |
| `placeholder`   | `&'static str`                | ✓    |                                                                      |
| `autocomplete`  | `&'static str`                | ✓    | HTML autocomplete hint                                                |
| `value`         | `Signal<String>`              | ✓    | 绑定当前值                                                            |
| `error`         | `Option<Signal<String>>`      | ✕    | 非 Some 且 `.get()` 非空 → input 切换 `c_euv_input_error`            |
| `oninput`       | `Option<Rc<dyn Fn(Event)>>`   | ✕    | None → 自动绑 `UseEuvInput::on_input_value(value)` 并 scroll-into-view |

**展开后的 DOM**：
```
div.c_euv_input_wrapper         width:100%; margin:gap-element 0
  label.c_form_label              display:block; margin-bottom:space-sm; font-base/500
  input.c_euv_input_no_transition 或 .c_euv_input_error (出错时)
  p (仅当 error 非空)             error 文案
```

> 提示：`error` 是 `Option<Signal<String>>`，不是裸 `Signal`。要永久禁用校验就传 `None`，永远不显示错误行。

### 3.C euv_virtual_list — 大量数据的虚拟滚动（替换 §3.17 裸 div + for）

```rust
euv_virtual_list {
    config: EuvVirtualListConfig {
        id: "users-list".to_string(),
        total_count: 10_000,
        item_height: 48,
        overscan_count: 6,
    }
    item_renderer: Rc::new(|index: i32| html! {
        div { class: c_virtual_list_row() "{index}" }
    })
    on_scroll: None
    on_visible_range_change: None
}
```

Props（`EuvVirtualListProps`）：

| 字段                       | 类型                          | 必填 | 说明                                                                 |
| -------------------------- | ----------------------------- | ---- | -------------------------------------------------------------------- |
| `config.id`                | `String`                      | ✓    | 容器 ID，多个虚拟列表必须唯一                                        |
| `config.total_count`       | `usize`                       | ✓    | 总条目数                                                              |
| `config.item_height`       | `i32`                         | ✓    | 单条高度（px）— 必须是定值；不能每条高度不同                         |
| `config.overscan_count`    | `usize`                       | ✓    | viewport 上下额外渲染的条数（默认 ~6）                               |
| `item_renderer`            | `VirtualListItemRenderer`     | ✓    | 闭包 `(i32) -> VirtualNode`                                          |
| `on_scroll`                | `Option<VirtualListScrollHandler>`    | ✕ | 自定义滚动回调                                              |
| `on_visible_range_change`  | `Option<VirtualListRangeHandler>`     | ✕ | 可见区间变化回调                                           |

伴随 class（`c_virtual_list` / `c_virtual_list_viewport` / `c_virtual_list_row` / `c_virtual_list_spacer`）：高度 = `total_count * item_height`，用 spacer 撑出真实滚动条；viewport 内只渲染可见 + overscan 条数。

### 3.D 路由组件 — euv_routes + euv_page_router

```rust
euv_page_router {
    route_signal: route,                  // 当前路由路径 Signal
    fallback: || html! { "Page not found" }
}

// 内部用 euv_routes 渲染当前路由对应的 page:
euv_routes {
    route_signal: route,
    routes: vec![
        EuvRouteConfig { path: "/about",       component: Rc::new(|| page_about(...)) },
        EuvRouteConfig { path: "/counter",     component: Rc::new(|| page_counter(...)) },
        // ...29 条
    ],
    fallback: Rc::new(|| page_not_found(...))
}
```

| 组件              | 用途                                                              |
| ----------------- | ----------------------------------------------------------------- |
| `euv_page_router` | 路由容器 — 包 `<div class=c_page_router>` 后塞 children           |
| `euv_routes`      | 路由分发 — 匹配 `route_signal` 命中 `routes[].path`，渲染对应 `component()`，未匹配走 `fallback` |

⚠️ **迁移提示**：当前 example 项目在 `about` page 内部硬编码了 nav 项；新 page **不要在 `mod.rs` 注册时省略 `EuvRouteConfig`**，否则路由不可达。

### 3.E 调试组件 — vConsole 三件套

```rust
euv_vconsole_panel {
    panel_open: panel_open_signal        // 控制 drawer 开合的 Signal<bool>
}
```

| 组件                    | 用途                                                                |
| ----------------------- | ------------------------------------------------------------------- |
| `euv_vconsole_fab`      | 浮动按钮 (右下角，**`euv_logo` variant=Fab**)，显示未读日志 badge   |
| `euv_vconsole_drawer`   | 半页底部抽屉 — 显示 `Console::log/warn/error` 全部条目，支持 level 过滤 |
| `euv_vconsole_panel`    | 上面两者的组合包装 — 给一个 `Signal<bool>` 即可                      |

**z-index 层级**（已记入 §9）：vconsole fab `9999` / panel `10001` —— 凌驾于 modal(1000) 之上，方便调试生产问题。

不要在 production 业务里重度依赖它 —— 仅 dev/debug 期间通过 `panel_open` 控制何时打开。

---

## 4. Home / Hero Page Spec

`page_about`（路由 `/about`）是**唯一的 hero 页面** —— 它**不**走 `euv_header`，而是用 `c_home_*` 系列 class 自己拼。所有其它 27 个页面一律 `euv_header { icon title subtitle }` 起手（见 §3.A）。

> 页头区分速判：grep `c_home` 出现在 `view/fn.rs` 里 → 一定是 `about`；grep `euv_header` → 普通 page。

- `c_home`（flex column; justify center; relative; mb space-xl，移动 mb space-lg + flex:0 0 auto）
- `c_home_content` (position relative; z-index 1)
- `c_home_title` (font-5xl/800 / letter-spacing -0.03em / mb space-xs，移动降 font-4xl)
- `c_home_subtitle` (font-lg；max-width 520；mb space-lg)
- `c_home_badge_row` (inline-flex; gap space-sm; mb space-md)
- `c_home_badge` (inline-flex; padding space-xs space-sm; color accent; border 1px solid accent; font-xs/600)
- `c_home_actions` (flex; gap space-md; justify-center; flex-wrap wrap)
- `c_home_btn_primary` (inline-flex; padding space-sm space-2xl; bg accent; color text-on-accent; font-base/600; border 1.5px solid transparent)
- `c_home_btn_secondary` (inline-flex; 同 padding；color accent；border 1.5px solid accent)
- `c_home_stats` (grid; template columns repeat(4,1fr); gap space-md; mb space-xl；移动 2 列 gap space-sm)
- `c_home_stat_card` (column flex; gap space-xs)
- `c_home_stat_icon` font-2xl / `c_home_stat_value` font-xl / `c_home_stat_label` font-sm
- `c_home_section_title` font-2xl/700 / letter-spacing -0.02em
- `c_home_section_desc` font-base / mb space-2xl
- `c_home_feature_grid` (grid repeat(2,1fr) gap space-md；移动 1 列)
- `c_feature_card` column flex gap space-sm padding 0 overflow hidden
- `c_feature_header` flex gap space-sm (icon 2xl + name)
- `c_feature_name` font-lg
- `c_feature_desc` font-sm

数字大块（value 默认 1.5xl→2xl 字，accent 加重）+ 节标题（2xl/700）。

---

## 4.A All 29 example Pages — 速查表

example 项目现共 **29 个 page**（`example/src/page/` 下 29 个目录）。27 用 `euv_header`，唯独 `about` 是 hero 模板。下表第一列 = 文件夹名（即路由 path），第二列 = `euv_header` 渲染出的标题，第三列 = 该 page 主演示的能力——新 page 设计用途可对照这张表定位。

| 路由 path       | `euv_header` 标题              | 演示什么                              | Hook 模块 |
| --------------- | ------------------------------- | ------------------------------------- | --------- |
| `/about`        | — (hero，无 euv_header)         | 整个 demo 的入口 / home page          | — |
| `/animation`    | Animation                       | CSS transition / @keyframes / 响应式 style | `hook/` |
| `/async`        | Async Data                      | `use_async_*` 异步状态                | `hook/` |
| `/attrs`        | Custom Attributes               | html! / class! 宏里的动态 attribute   | — |
| `/badge`        | Badge                           | `euv_badge` 实色/线框 + 点击 log      | — |
| `/binding`      | Component Binding               | Props 下传 + Signal 双向绑定          | `hook/` |
| `/browser`      | Browser APIs                    | storage / clipboard / window metrics  | — |
| `/camera`       | Camera                          | 设备摄像头扫描 QR                     | — |
| `/canvas`       | Canvas                          | 自由绘画（color picker + 粗细）       | `hook/` |
| `/conditional`  | Conditional Rendering           | `if` 表达式 / 条件渲染                | `hook/` |
| `/counter`      | Counter                         | `Signal<i32>` 响应式 counter          | `hook/` |
| `/dynamic`      | Dynamic Tag                     | 动态 tag name / 动态 class            | `hook/` |
| `/event`        | Event Handling                  | keyboard / mouse / focus / touch 全套 (1493 行，最大 page) | `hook/` |
| `/file`         | File Upload                     | `<input type=file>` 多文件 + accept   | — |
| `/form`         | Form Demo                       | 注册表单 + 双向 Signal 实时校验       | — |
| `/game_2d`      | 2D Game Engine                  | euv-engine 物理 demo（弹球）          | `hook/` |
| `/game_3d`      | 3D Game Engine                  | euv-engine 旋转立方体（Vector3D / Quaternion） | `hook/` |
| `/keep_alive`   | Keep-Alive                      | CSS display 跨 tab 切换保活           | `hook/` |
| `/lifecycle`    | Lifecycle                       | render count + watch! 宏              | — |
| `/list`         | List Rendering                  | 动态 todo (Signal 增删)               | — |
| `/modal`        | Modal Dialog                    | overlay dialog 多种内容模式           | `hook/` |
| `/not_found`    | 404 Not Found                   | 兜底页                               | — |
| `/observer`     | Observer                        | `IntersectionObserver` 进入离开视口   | — |
| `/select`       | Select & Textarea               | 下拉 / 级联 country-city / textarea   | — |
| `/sse`          | Server-Sent Events              | SSE 实时流                           | — |
| `/timer`        | Timer                           | `use_interval` 计时器 / 倒计时        | — |
| `/virtual_list` | Virtual List                    | `euv_virtual_list` 大量数据滚动       | — |
| `/webgpu_status`| (内嵌 const.rs，**无 view/ 子目录，无 euv_header**) | WebGPU 状态常量展示页 | — |
| `/websocket`    | WebSocket Chat                  | WS 自动 UUID + chat                   | `hook/` |

**hook/ 子目录出现频率高**（17/29）—— 多数 page 都把页面级 `Signal` / `watch!` / `use_*` 抽到 `hook/` 下，模板里只剩 UI。**新 page 复制此约定：状态多就建 `hook/`，单页就内联在 `view/fn.rs` 顶部 `let state = use_xxx();`。**

**唯一示例规律**：`event` 1493 行（最大）、`lifecycle` 60 行（最小）—— 范围跨度很大，按需自取。

---

## 5. Class Naming Conventions

| 类别        | 命名                                                           | 示例                                   |
| ----------- | -------------------------------------------------------------- | -------------------------------------- |
| 跨 page     | `c_<component>` 单段名                                         | `c_card` `c_euv_button_primary_md`     |
| Layout/Shell| `c_app_*` / `c_page_*` / `c_mobile_*`                          | `c_app_root` `c_page_title`            |
| Nav         | `c_nav_*`                                                      | `c_nav_item_active`                    |
| 业务 page   | `c_<page>_...`（page 用 snake_case）                           | `c_home_title` `c_keep_alive_panel`    |
| 子组件内部  | `c_<component>_<element>`                                      | `c_euv_input_wrapper` `c_euv_logo_nav` |
| 主题/状态   | `_active` / `_inactive` / `_visible` / `_hidden` / `_closed`   | `c_nav_item_active`                    |
| Type token  | `_primary` / `_outline` / `_solid` / `_error` / `_sm` / `_md`  | `c_euv_button_outline_md`              |
| 参数化 class| `<name>(arg: &str)`                                            | `c_game_canvas_wrapper(ar)`            |
| 复用 mixin  | `c_xxx();` 在另一个 class 体内展开（CSS 复用）                 | `c_info_value { c_text_ellipsis(); ... }` `c_euv_input_no_transition` |

⚠️ snake_case，全小写。允许复数（`c_nav_items_scroll`）。允许双前缀（`c_home_stat_card`）。

---

## 6. Responsive / Breakpoints

**唯一**断点：`@media (max-width: 767px)`（移动端范围 0–767，桌面 ≥768）。

常见响应式变化：

- nav → drawer（`c_app_nav` display:none；`c_mobile_*` 出现）
- padding main 28→16
- font-title 5xl→4xl；page-title font-4xl→font-3xl；page-subtitle lg→base
- grid 4 列→2 列 / 2 列→1 列 / 1fr 1fr→1fr
- 滚动条：桌面 6px / 移动 hidden

---

## 7. Accessibility / Touch

```
:focus-visible { outline: none }      // 所有自定义控件靠 border color 表达 focus
@media (prefers-reduced-motion: reduce) { *, *::before, *::after { animation-iteration-count:1 !important; scroll-behavior:auto !important } }
@media (hover: none) and (pointer: coarse) {
  * { -webkit-tap-highlight-color: transparent }
  .c_card:hover, .c_home_stat_card:hover, .c_home_btn_primary:hover, .c_home_btn_secondary:hover { transform:none !important }
}
```

不要在自定义 class 覆盖这些全局规则。

---

## 8. New Page Standard Template

> ⚠️ **现代 page 模板从 27/29 个 example 抽象而来**，唯一例外是 §4 的 hero page。**不要**再用 §2.2 末尾的裸 div pattern。

**步骤**：
1. `example/src/page/<page_name>/` 建：`mod.rs`（`pub mod view;`）、`view/fn.rs`、可选 `hook/` 子目录（如果用 `use_xxx` 状态）。
2. `view/fn.rs` 写 `#[component] fn page_<name>(node: VirtualNode<Page<Name>Props>) -> VirtualNode`，全 html!。
3. **不要**在 `view/fn.rs` 写 `class! { ... }`。新样式 → `git diff` 提给 ui 包 `ui/src/style/class/fn.rs` 加，或本地 `example/src/style/class/fn.rs`（仅当该样式只本页用）。
4. `#[component]` 首行 `let Page<Name>Props = node.try_get_props().unwrap_or_default();`（命名强约束，便于后续补 props）。
5. 视图顺序：`page_router > page_container > euv_header > 若干 euv_card`，卡之间用 `page-block-gap=24px`（mobile 20）隔开（外层 gap 或 `style="margin-top:var!(page-block-gap)"`）。
6. 路由注册：`example/src/page/mod.rs` 加 `mod <name>;` + `pub(crate) use <name>::*;`，并在 `euv_routes` 的 `routes: Vec<EuvRouteConfig>` 数组里追加 `{ path: "/<name>", component: ... }`。
7. 导航暴露：在 nav 配置（`example/src/navigation.rs` 或内联）的 `c_nav_items` 数组里追加 `EuvNavItem`，desktop 端点中显示、移动端 drawer 也复用。

**最小 page（基于 `lifecycle` 真实例子）**：

```rust
use crate::*;

#[component]
pub(crate) fn page_demo(node: VirtualNode<PageDemoProps>) -> VirtualNode {
    let PageDemoProps: PageDemoProps = node.try_get_props().unwrap_or_default();

    html! {
        div {
            class: c_page_container()
            euv_header {
                icon: "🎯"
                title: "Demo Page"
                subtitle: "A demo to show how a page composes."
            }
            euv_card {
                title: "Section A"
                p { class: c_render_count_text()
                    "This page has been rendered "
                    span { class: c_counter_value() "0" }
                    " times."
                }
                div {
                    class: c_button_controls()
                    euv_button {
                        variant: EuvButtonVariant::Primary
                        label: "Click me"
                        onclick: |_| {}
                    }
                }
            }
            euv_card {
                title: "Section B"
                euv_field {
                    id: "demo-input"
                    name: "demo_input"
                    label: "请输入"
                    input_type: "text"
                    placeholder: "demo"
                    autocomplete: "off"
                    value: signal_demo_value
                    error: None
                }
            }
        }
    }
}

#[derive(Clone, Copy, Debug, Default, Eq, Hash, Ord, PartialEq, PartialOrd)]
pub(crate) struct PageDemoProps;
```

**Hero page 模板**（仅 `/about` 一处使用，见 §4）：

```rust
// 不走 euv_header，自己拼 c_home_* div
div { class: c_home()
    div { class: c_home_content()
        div { class: c_home_badge_row()
            // 徽章行
        }
        h1 { class: c_home_title() "..." }
        p  { class: c_home_subtitle() "..." }
        div { class: c_home_actions()
            // c_home_btn_primary / c_home_btn_secondary
        }
        // stat grid → feature grid
    }
}
```

判别：路由名是 `/about` 才走 hero，否则一律 `euv_header`。

---

## 9. Quick Notes / Anti-Patterns

❌ 写 class! 时硬编码颜色/间距 — 一律 `var!(xxx)`。
❌ 添加阴影、彩色背景、圆角 — design system 是黑/白硬边。
❌ 在 page 里写新 class! — 全局或本地 class! 块集中维护。
❌ 自定义 `<button class="mybtn" />` — 用 `euv_button`。
❌ 使用 emoji 当 icon 装饰主流程 ─ 但 example 项目现大量用 emoji（⚡🦀🎨📦🌲🌐🏗️），允许（小图标、stat 内）。
❌ 改 :focus-visible outline:none 的全局规则。
❌ 把 `c_card` 当成"有边框卡" — 它没边框；边框/分隔请用 `c_card_title` 的 dashed 下边界。
❌ 三按钮行不包 `c_button_controls` — 没 gap 不好看。
✅ 复合间距优先 `gap-component / gap-section / gap-element / gap-inline / page-block-gap`，而非 `space-md` 等。
✅ "value" 用 `var!(accent)` 加重，"label" 用 `var!(muted-foreground)` 减重——黑底双色靠权重而非颜色。
✅ 列表分隔、卡片下划线 → `1px dashed var!(border)`。
✅ 在桌面 nav / drawer / modal / FAB，所有 z-index：modal 1000；mobile overlay 200；drawer 201；vconsole fab 9999；vconsole panel 10001。
✅ Safe-area：所有"贴屏幕边"的浮层（fab、drawer、mobile nav）都要 `var!(safe-area-inset-*)`。
