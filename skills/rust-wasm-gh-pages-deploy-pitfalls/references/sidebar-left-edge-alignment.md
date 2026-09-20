# 侧边栏左边缘对齐 — 三轮迭代(R4→R6)最终定论(2026-09-19/20)

> 本文件取代 `references/sidebar-tree-line-alignment.md`(该文件停在 R5 状态,描述的几何已过时)。

## 最终几何不变式

**侧边栏列 = 单一左边缘**:section label 文字、条目文字(分组标题+链接)、树线、footer 文字、footer 分隔线,**全部共享同一 x**。桌面 = 14px(2px 容器边框 + 12px 条目 padding),移动端抽屉 = 12px。

树线 = 从父分组标题文字的第一列垂下(**不是**子项文字列,也**不是**"贴近子项文字")。文字列保持 21px/级缩进(桌面 14/35/56/77),树线列 = 标题文字列(14/35/56)。

euv-docs 站点 override(euv-docs/src/lib.rs,注入 CSS)最终形态:
```css
.c_euv_sidebar_group_title { padding: 0.4rem 0.75rem !important; box-sizing: border-box !important; }
.c_euv_sidebar_children { padding-left: 0.5rem !important; margin-left: 0.75rem !important; }  /* 线=父标题文字列 */
.c_nav_footer_divider { left: 0.75rem !important; right: 0.75rem !important; }
.c_nav_section_label { padding-left: 0.75rem !important; }  /* euv-ui 0.18 默认 space-xl=20px,偏右 8px */
.c_nav_footer { padding-left: 0.75rem !important; }          /* euv-ui 0.18 默认 space-lg=16px,偏右 4px */
.c_euv_sidebar_link { display: block !important; padding: 0.4rem 0.75rem !important; }
.c_euv_sidebar_link_active { padding: 0.4rem 0.75rem !important; }
```
统一 `margin-left: 0.75rem`(12px):children 容器的 border-left 恰好落在父级标题文字列(父内容区 x + 12 = 父标题 padL 12px 的文字起点),各级自洽 14/35/56。**不要用 `:not(...)` 做深度补偿几何**(R4 试过,破坏左边缘统一性且选择器脆弱)。

## 三轮反馈链(误读史)

1. **R4**:"侧边栏文字下的左边框没有对齐文字左侧开头位置" → 我把线从父标题列移到子项文字列(留 5px 间隙)。**误读**,且制造了 R5 的回归。
2. **R5**:"现在侧边栏的文字最左侧和下面边框最左侧没有对齐" → "现在" = R4 改动造成的回归(最左线 30 vs 最左文字 14)。改回线挂父标题列,顺带把 footer divider 从 18px 对齐到 14px。
3. **R6(移动端)**:"移动端侧边栏标题下左边框没有对齐文字左侧" → 实测线上构建 20 个分组的树线与标题**全部已对齐**;真正残留未对齐的是 `文档` section label(padL 20px)和 footer(padL 16px),偏右 8px/4px(PR #246 修)。

**教训 A — 用户抱怨里的"文字/边框"指代会变,先枚举整列所有元素**:树线、label、footer、divider、条目文字。别只盯树线。
**教训 B — "现在/还是"类回归措辞 = 与上一版对比**,先 diff 两版几何再动手。
**教训 C — 部署后用户立刻报"还没好",先实测线上构建再改**:R6 投诉的几何(线偏右 16px)与 R4 中间态完全一致 = 用户手机缓存了旧 wasm。线上 DOM 测量正确时,回复"强刷"而不是再改几何。GitHub Pages `cache-control: max-age=600`,移动端 SPA 还会常驻内存。

## 验证方法(像素级,双端)

- **移动端抽屉**:Playwright viewport 390×844 + device_scale_factor=3 + has_touch/is_mobile → `click('.c_mobile_menu_button')` → 所有测量 scope 到 `.c_mobile_nav_drawer`(桌面侧边栏在移动端被隐藏,直接查 document 会拿到隐藏元素,x 全 0 误判)。
- **逐组断言**:每个 `.c_euv_sidebar_group` 取 `:scope > .c_euv_sidebar_group_title` 的 glyphX(Range API 首个 text node 的 getClientRects()[0].x)与 `:scope > .c_euv_sidebar_children` 的 getBoundingClientRect().x,|diff| ≤ 1px。
- **整列断言**:label/footer/divider 的 x 与最左条目文字列 |diff| ≤ 1px。
- 参考脚本(会话临时):`/tmp/verify_mobile_align.py`(8 项 = 双端 × [组线对齐 + label + footer + divider])。

## 同轮新增的 euv-docs build.rs 能力(PR #245,0.25.4)

- **叶子提升**:只有 README 的目录不再从侧边栏消失(children 空 → 作为叶子链接出现)。此前 ~30 个单页项目目录(各 crate)在侧边栏完全不可见,根因是 `if children.is_empty() { continue; }`。
- **`sidebar_order: [name, ...]` frontmatter**(写在目录 README 上,根级 = home README):VuePress 风格显式固定该层子项顺序;条目 = 目录名或文件 stem(`.md` 可省,`./`、`/` 容忍);未列出项按 (order, title) 排在列出项之后。docs 仓顶层顺序固定在 `docs/README.md` frontmatter(ltpp 系 → hyperlane 系 → crates 字母序 → essay → appreciate)。
