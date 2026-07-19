---
name: euv-ui-standards
description: >
  euv example/example 项目 UI 设计系统全量规范。涵盖 304 个 class! 的全局 class 名表（按前缀分类）、design tokens（colors / spacing / font-size / radius / shadow / animation / transition / safe-area）、核心组件 HTML 结构（euv_button / euv_card / euv_badge / euv_tag / euv_alert / euv_input / euv_checkbox / euv_nav_item / euv_card / euv_home）、页面骨架（app 壳、page_container、page_title、page_subtitle）、断点（@media (max-width: 767px)）、响应式规则、class 编写约定（不在 page 内写 class! 块）。触发词：euv UI、euv 样式、euv design token、c_page_container、c_home_、c_euv_button、c_card、c_badge、c_euv_tag、c_euv_input、c_modal_content、c_nav_item_active、c_app_root、c_app_nav、c_app_main、euv-ui-standards。
---

# euv example 项目 UI 设计规范（全量）

你正在为 **euv framework** 的 example / app 项目编写 UI。example 项目的 UI 必须遵守本规范，否则与设计系统冲突。

## 0. 规范来源（事实依据）

- 全局 class! 注册表：`ui/src/style/class/fn.rs`（304 个 class，单文件统一维护）
- 全局 vars! token：`ui/src/style/var/fn.rs`（light + dark 主题）
- 全局 CSS reset & keyframes：`ui/src/style/css/fn.rs`（由 `inject_app_global_css()` 注入）
- 组件 view HTML：`ui/src/component/<name>/view/fn.rs`
- 项目内二次封装（仅供调用、不得新增 class）：`example/src/style/class/fn.rs`（game_stats / canvas / keep_alive / binding 域）

> **强制约束**：
> 1. **所有 class! 块都在 `ui/src/style/class/fn.rs` 这一个文件里维护**，page 自己的 `view/fn.rs` **不写** `class! { … }` 块，**只引用** `c_xxx()` 函数。
> 2. **必须以 `c_` 前缀 + page/component 名 + 元素名** 命名（例：`c_video_list_viewport`、`c_home_title`、`c_euv_button_primary_md`）。
> 3. 跨 page 复用的样式，命名里不带 page 名（如 `c_card`、`c_euv_button_primary_md`、`c_app_root`）。

---

## 1. Design Tokens（必须通过 `var!(xxx)` 引用，禁止硬编码）

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

## 2. 全局骨架（必掌握）

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

**典型 page header**：

```
div class=c_page                        // position:relative; text-align:center
  div class=c_page_glow                 // 装饰性径向光（绝对定位）
  div class=c_page_content              // position:relative; z-index:1
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

## 3. 核心组件 HTML 模板（直接复用 `ui/src/component/<name>`）

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
- `c_game_stats_bar / c_game_stats_label / c_game_description / c_game_canvas_wrapper(ar)` / `c_game_3d_canvas` / `c_game_2d_canvas` / `c_canvas_pixelated`
- `c_keep_alive_tab_visible / c_keep_alive_tab_hidden` / `c_binding_slider_label_accent` / `c_binding_color_preview_bg(bg)` / `c_anim_scale_shrink / c_anim_scale_normal`

⚠️ 命名 + 前缀约定：**`c_<page>_<element>`**（如 `c_keep_alive_*`），不污染全局 ui 包。

---

## 4. Home / Hero 页规范（特殊，仅首页用）

`page_about` 是唯一 hero 页面，所有样式已在 example 项目里：

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

## 5. Class 命名约定（必读）

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

## 6. 响应式 / 断点

**唯一**断点：`@media (max-width: 767px)`（移动端范围 0–767，桌面 ≥768）。

常见响应式变化：

- nav → drawer（`c_app_nav` display:none；`c_mobile_*` 出现）
- padding main 28→16
- font-title 5xl→4xl；page-title font-4xl→font-3xl；page-subtitle lg→base
- grid 4 列→2 列 / 2 列→1 列 / 1fr 1fr→1fr
- 滚动条：桌面 6px / 移动 hidden

---

## 7. a11y / 触摸优化（`c_app_root` 注入）

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

## 8. 写新 page 的标准模板

**步骤**：
1. `example/src/page/<page_name>/` 建：`mod.rs`（导出 `pub mod view;`）、`view/{fn,struct,const,mod}.rs` 四件套。
2. `fn.rs` 写 `#[component] fn page_<name>(node: VirtualNode<Page<Name>Props>) -> VirtualNode`，全 html!。
3. **不要**在 `view/fn.rs` 写 `class! { ... }`。新样式 → 直接 `git diff` 提给 ui 包 `ui/src/style/class/fn.rs` 加，或本地 `example/src/style/class/fn.rs`（仅当该样式只本页用）。
4. `#[component]` 的 component 内首行 `let Page<Name>Props = node.try_get_props().unwrap_or_default();`（命名强约束，便于后续补 props）。
5. 视图顺序：`<div class=c_page_router><div class=c_page_container>{你的分块}</div></div>`，分块用 `page-block-gap=24px (mobile 20)` 隔开（直接用 `style="margin-top:var!(page-block-gap)"` 或外层 gap）。
6. 路由注册：`example/src/page/mod.rs` 加 pub use；并在 navigation 配置里挂上 nav-item。

**最小的"玩具 page"模板**：

```rust
use crate::*;

#[component]
pub(crate) fn page_demo(_: VirtualNode<PageDemoProps>) -> VirtualNode {
    html! {
        div {
            class: c_page_container()
            div {
                class: c_page()
                div {
                    class: c_page_content()
                    div {
                        class: c_page_icon()
                        "🎯"
                    }
                    h1 { class: c_page_title() "Demo Page" }
                    p  { class: c_page_subtitle() "A demo to show how a page composes." }
                }
            }
            euv_card { title: "Section"
                euv_button { variant: EuvButtonVariant::Primary label: "Click me" onclick: |_| {} }
            }
        }
    }
}

#[derive(Clone, Copy, Debug, Default, Eq, Hash, Ord, PartialEq, PartialOrd)]
pub(crate) struct PageDemoProps;
```

---

## 9. 速记 / 反模式

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
