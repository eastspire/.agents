# 坑 31:侧边栏树线"对齐文字左侧开头" = 线贴子项文字列(2026-09-19)

**症状**:用户报"侧边栏文字下的左边框没有对齐文字左侧开头位置"。此前实现把树线放在父组标题文字列(children `margin-left: 0.75rem` → 线 x=14/35/56,与父标题文字对齐),但子项文字在 x=35/56/77 —— 线与其分组的文字隔 21px,用户认为没对齐。

**用户语义**:树线属于它分组的**子项**,应贴着子项文字左边缘(留 ~5px 间隙,像引用条),不是对齐父标题列。

**几何公式**:`gap(线→子项文字) = 1px(border-left) + children 容器 padding-left + 子项 padding-left`。margin-left 只控制线的绝对位置,不影响 gap。要贴文字必须三值同时改。

**最终方案**(euv-docs site override in `euv-docs/src/lib.rs`;文字列不变 14/35/56/77,线移到 30/51/72):

```css
.c_euv_sidebar_children { padding-left: 0; margin-left: 1.25rem; }              /* 深度≥2 */
.c_euv_sidebar_children:not(.c_euv_sidebar_children .c_euv_sidebar_children) { margin-left: 1.75rem; }  /* 深度1 */
.c_euv_sidebar_children .c_euv_sidebar_group_title,
.c_euv_sidebar_children .c_euv_sidebar_link,
.c_euv_sidebar_children .c_euv_sidebar_link_active { padding-left: 0.25rem; }
```

- 深度1 margin 28px vs 深度≥2 20px:root 项 padL=12px、嵌套项 padL=4px,差 8px 由深度1 margin 补(28=20+8),保证每级缩进 21px 均匀。
- `:not(复杂选择器)` 是 CSS Selectors L4,Chrome 88+ 支持,用来区分"有没有 children 祖先"=深度层级。
- 验证断言:每个 children 容器 `childTextX - lineX == 5±1px`。用 Range API 取首个 text node 的 glyph x(document.createTreeWalker + createRange().getClientRects()[0].x),别用 element.getBoundingClientRect().x —— group title 里有 ▸ 箭头 span,element.x 会骗你。
- euv-ui 0.25 的 class! 宏只支持伪类/伪元素(`hover {}`),不支持后代选择器;框架级实现需 sidebar 组件递归时传 depth 参数(破坏性 API 变更),属独立设计任务。本次只改 euv-docs override 即上线(PR #243)。

**验证脚本**:/tmp/verify_align.py(gap 断言 + 文字列回归)+ /tmp/ascii_sb.py(PIL 把截图转 ASCII 艺术,无 vision provider 时用)。
