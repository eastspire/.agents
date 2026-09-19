# 坑 31:侧边栏树线对齐 — 用户要的是"线从父标题文字左边缘垂下"(2026-09-19,两轮纠正后定论)

**两轮反馈链**:
1. R4:"侧边栏文字下的左边框没有对齐文字左侧开头位置" → 我把线从父标题列(x=14)移到子项文字列(x=30,留 5px 间隙)。**误读**。
2. R5:"现在侧边栏的文字最左侧和下面边框最左侧没有对齐" → "现在"=R4 改动造成的回归。用户真正语义:**树线属于父标题,从标题文字的第一个字符垂下;侧边栏所有文字的最左边缘(x=14)必须与最左侧树线(x=14)共享同一条竖线**。

**最终几何**(euv-docs site override,文字列 14/35/56/77 不变):
```css
.c_euv_sidebar_children { padding-left: 0.5rem; margin-left: 0.75rem; }  /* 线=父标题文字列 */
.c_nav_footer_divider { left: 0.75rem; right: 0.75rem; }                 /* 底部分隔线也对齐 14 */
```
- 统一 `margin-left: 0.75rem`(12px):children 容器的线恰好落在父级标题文字列(父内容区 x+12 = 父标题 padding-left 12px 的文字起点),各级自洽 14/35/56。
- 验证断言:**像素级**用 inkrows 扫描(首个墨点 x),DOM 级用 Range API 首个 text node 的 glyph x;目标 = 每级 `lineX == 该级标题 textX ±1px`,且 `min(lines) == min(texts)`。
- euv-ui 的 `c_nav_footer_divider` 默认 `left/right: space-lg(16px)`,与文字列(padL 12px)差 4px,站点 override 拉回 12px。

**教训**:同一位置两轮相反描述时,以最新一轮 + "现在/还是"等回归措辞为准;改之前先 pixel-scan 当前态与上一态确认哪个对齐关系被破坏。不要用 `:not(复杂选择器)` 做深度补偿几何(脆弱且破坏左边缘统一性)。

**同轮新增能力**(euv-docs build.rs):
- `build_sidebar` 叶子提升:只有 README 的目录不再消失,作为叶子链接出现(此前 ~30 个单页项目目录在侧边栏不可见)。
- frontmatter `sidebar_order: [name, ...]`(目录 README 上,VuePress 风格)显式固定子项顺序;条目 = 目录名或文件 stem(.md 可省);未列出项按 (order, title) 排在列出项之后。根级顺序写在前页 README(docs/README.md)的 frontmatter。
- 验证脚本:/tmp/verify_round5.py(46 顶层条目顺序逐对 diff + 线/文字/分隔线 x 对齐)。
