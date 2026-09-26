---
name: agent-skills-source-sync
description: 对账并修复 `.agents/skills/*/SKILL.md` 中过时的版本号/数值声明，与本地源仓库真实状态保持一致。适用于任何 skills 文档引用了具体源仓库版本/计数的场景。
---

# Agent Skills 与源仓库对账

## 适用场景
- `.agents/skills/*/SKILL.md` 文档中声明了具体版本号（如 `euv = "0.13.3"`）、class 计数、组件计数、子 crate 列表等
- 这些声明可能因为源仓库升级而漂移
- 用户要求 "同步"、"对账"、"检查版本"、"更新 skill 文档"

## 核心流程

### 1. 定位源仓库
- 文档中通常会显式声明源路径，例如 `/d/code/euv/Cargo.toml`
- 确认 Cargo.toml / package.json 等版本清单文件存在

### 2. 提取源真实状态
```bash
# 版本号
grep -E '^(version|euv) *=' Cargo.toml

# Workspace 子 crate 列表
sed -n '/^\[workspace\]/,/^\[/p' Cargo.toml

# 计数类（class 宏、组件、模块等）
grep -c '^pub c_[a-z_]* *{$' ui/src/style/class/fn.rs  # class!
ls -d ui/src/component/*/ | wc -l                      # 组件

# proc_macro 计数（用 -c 而不是 wc -l，处理跨行 #[proc_macro]）
grep -cE '^#\[proc_macro' macros/src/lib.rs
```

### 3. 扫描所有 skills 中的引用
```bash
# 找所有引用了该库版本的 SKILL.md
grep -rn '"0\.[0-9]*\.[0-9]*"' .agents/skills/*/SKILL.md

# 找所有版本相关的描述行
grep -rn 'euv *=' .agents/skills/*/SKILL.md
```

### 4. 逐项对账，输出表格
| Skill | 检查项 | 文档值 | 实际值 | 状态 |

### 5. 精准 patch（用 `replace_all: false`，匹配前必须读文件确认）
```bash
# 必读后改
sed -n '5,15p' .agents/skills/euv-standards/SKILL.md
# 然后 patch 精确字符串
```

### 5.5 大框架 skill 用 progressive loading 拆分（不是单文件膨胀）
框架类 skill（euv / hyperlane / rust 这类）源码 2000+ 个 pub item + 100+ 坑，单 SKILL.md 写到 1000 行也讲不完。**正确三层结构**：
| 层 | 文件 | 内容 | 触发 |
|---|---|---|---|
| 1 入口 | `<framework>/SKILL.md`（薄，~150 行） | trigger + 决策树 + 跳转表 + 5 行最小调用 | 任何涉及该框架的任务必加载 |
| 2 规范 | `<framework>-standards/SKILL.md`（~400 行） | workspace layout + 跨 crate 规则 + version bump + publish 顺序 | 涉及 monorepo 跨 crate 操作时加载 |
| 3 API 速查 | `<framework>/references/api-<crate>.md`（每 crate 一文件，按需） | 完整 pub API（自动生成）+ pitfalls | 写具体代码时按需加载 |

API 速查文档**自动生成**（Python os.walk + 多行 regex 跑一次出全部 pub item），源码 bump 后 regenerate 即可。生成脚本可放 `<framework>/scripts/gen_api_docs.py`（复用本 skill 的"提取源真实状态"流程）。

### 6. Commit + Push
```bash
cd <project root>
git add .agents/skills/<changed>/SKILL.md
git diff --cached --stat  # 确认只暂存自己的修改
git commit -m "fix(<skill>): bump version reference X.Y.Z -> A.B.C"
git push origin <branch>
```

## 易踩的坑（Pitfalls）

### ❌ grep 模式错误导致假阴性
错误：`grep -c '^class! {$' file.rs`  → 1（只匹配宏入口）
正确：`grep -c '^pub c_[a-z_]* *{$' file.rs` → 实际宏展开后的 304 个 class
**经验：当文档声称"宏展开的 N 个"时，必须搜宏展开后的 token 模式，不是宏定义本身**

### ❌ 误把 crate 依赖版本当作主库版本
例如：`euv-app/SKILL.md` 提到 `reqwest 0.12.28`，这是 **reqwest 自身版本**，不要替换为 euv 版本
**经验：grep 出来的版本号必须先看上下文，确认是哪个 crate 的版本**

### ❌ git add 看不到改动
症状：`git status` 显示 `M` 但 `git add` 后说 "no changes added"
原因：之前已经被 staged 过但没 commit；或被 `.gitignore` 局部忽略
解决：直接 `git add -f <file>` 强制加入

### ❌ sed -n 范围匹配错过内容
如果文件用 `## Header` 而非 `[section]`，sed 区间匹配失效 → 用 `grep -n` 定位行号

### ❌ 框架类 skill 写了具体数字就会过期
class 数（euv 的 365）、模块数（engine 的 21）、page 数（example 的 34）、proc_macro 数（hyperlane-macros 的 77）这些**全都会随源码升级而变**。
**正确做法**：文档里写 grep 命令 + "以源码为准"，不写死数字。例：
```
euv-macros proc_macro 数: grep -cE "^#\[proc_macro" macros/src/lib.rs 即得
```
**错误做法**：写 `euv-macros 8 个 proc_macro`——下次 bump 就过期。

### ❌ os.walk 漏掉 sub-crate
monorepo 里 `core/` `macros/` `ui/` 是 workspace root 的 **sibling**，不是 `root/src/` 的子目录。`os.walk(root/src)` 只 yield 1 个目录。**正确做法**：`os.walk(root)` 跨所有 sub-crate，且跳过 `tests/` `examples/` `benches/` `target/` `.git/`。验证：`grep -cE "^members" Cargo.toml` 拿 member 列表。

### ❌ 多行 pub item regex 失效
pub fn 常在 `impl.rs` 多行展不开，`^\s*pub fn` 单独行匹配不上。**正确 regex**（多行 + 跳过 impl 块）：
```python
r'^\s*pub(\s*\([^)]*\))?\s+((?:async\s+|const\s+|unsafe\s+)?(?:fn|struct|enum|trait|type|static|mod|macro_rules!))\s+([A-Za-z0-9_!]+)'
```
在 `os.walk` 遍历的每个 `.rs` 文件全文 multi-line 扫描（`re.finditer(..., re.MULTILINE | re.DOTALL)`）。impl 块内的 pub fn 是 method，不是"模块 pub API surface"——要剔除。

### ❌ proc_macro 提取正则不够激进
77 个 proc_macro 分散在 macros/src/lib.rs 里，被大量 doctest 注释和空白隔开。**工作 regex**：
```python
r'#\[proc_macro(?:_attribute)?[^\]]*\][\s\S]{0,200}?pub fn ([A-Za-z0-9_]+)\s*\(([^)]*)\)'
```
注意：`{0,200}?` 非贪婪窗口 + `[\s\S]` 跨行，捕获 `fn_name` + 签名 `(attr: TokenStream, item: TokenStream)`。

### ❌ 删除大段 section 后子编号没顺移
当你删 `## 4` 把后面 `## 13.x` 改成 `## 6.x` 时，所有 `### 13.1` `### 13.2` 等子章节必须一起改；Index 表里的 `[§13 Monorepo](#13-monorepo)` anchor 也得改。漏一处就 anchor 死链。**正确流程**：先 grep `### 1[3-9]\.` 拿到所有编号，再 sed 一次性替换；改完用 `grep -nE "^## "` 验证 §3/§4/§5/§6/§7 编号连续无跳号。

### ❌ Index 表 anchor 死链
文档顶部 Index 表的链接 `(#13-monorepo-layout--internal-deps)` 是 hand-written，不是从 section heading 自动生成。删/移 section 后，anchor 不会自动跟。**必跑验证**：用脚本 `grep -nE '^\(#?[0-9]+-'` 把所有 anchor 链接 dump 出来，跟实际 `^## N.` 对照。

### ❌ write_file 对超大已有文件"沉默成功"
旧 SKILL.md 800+ 行时，write_file 新内容后 read_file 可能仍返回旧版（缓存/原子写竞争）。**正确做法**：
1. 先 `wc -l` 看旧大小；
2. patch 用 `replace_all: false` 精准替换，每改一个 section 立刻 read 验证；
3. 全文 rewrite 只用于 < 300 行的薄 skill；大文件用 patch 串行修改。

### ❌ description 里漏掉 frontmatter 的 description
patch `## X` 章节时经常忘改 frontmatter 的 `description:`——它也含具体数字。**必查**：每次改完用 `grep -nE '^\d+(\.\d+)?( 个| crates|模块| items| pub)` .agents/skills/*/SKILL.md` 做最后一道 pass。

### ❌ 把"事件叙事"和"current state"混在一起
PR #238 / #220 / #34 的引用是 past-incident（保留）。但 "monorepo 内部 6 个 crate" 这种是 current state——必须随源码改。**判别**：含 PR 号/日期/ticket ID → 事件叙述（保留）；含具体数字/版本号 → current state（必须对账）。

## 验证清单（Commit 前自检）
- [ ] 所有引用的版本号已与 Cargo.toml 对齐
- [ ] 计数类（class/组件/sub-crate）已用 grep 二次确认
- [ ] 依赖 crate 的版本号（如 reqwest）未误改
- [ ] diff 干净，只包含目标文件
- [ ] commit message 明确说明 bump 方向
- [ ] **最后一道全 grep pass**：跑 `grep -nE '(\d+ 个 \w+|~?\d+ 项|crates|members)' .agents/skills/*/SKILL.md` 把所有数字/列表声明列出来，逐个跟源码实际值对照
- [ ] **Index 表 anchor 验证**：跑 `grep -nE '\[.*\]\(#' .agents/skills/*/SKILL.md` 列所有 anchor 链接，确认每条都对应一个 `^## N.` heading
- [ ] **section 子编号顺移**：如果动了 §X 的位置，所有 `### X.Y` 跟着改，验证 `grep -nE '^### ' .agents/skills/*/SKILL.md` 输出编号连续无跳号
