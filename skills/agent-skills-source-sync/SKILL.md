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

## 验证清单（Commit 前自检）
- [ ] 所有引用的版本号已与 Cargo.toml 对齐
- [ ] 计数类（class/组件/sub-crate）已用 grep 二次确认
- [ ] 依赖 crate 的版本号（如 reqwest）未误改
- [ ] diff 干净，只包含目标文件
- [ ] commit message 明确说明 bump 方向
