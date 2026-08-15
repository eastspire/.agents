---
name: skill-index-and-english-titles
description: 大批量修改 eastspire/.agents skill 库中多个 SKILL.md 的标准流程:加 ## Index 表格 + 章节标题中→英 + 加 ## Mutual-Lock Routing 路由表 + 同步到 hermes。**任何涉及批量改多个 SKILL.md / 重构 skill 互锁链 / 提高 skill 命中率的维护任务必加载**。关键词:SKILL.md, frontmatter, description, index, 互锁, mutual-lock, eastspire/.agents, gh-pr-creation-workflow.
---

# Skill 库批量维护:Index + 英化 + 互锁路由

## 何时用

- 一次会话要改 ≥ 3 个 SKILL.md(互锁链重构、版本对齐、命中率优化)
- 任何对 `~/Documents/workspace/eastspire/eastspire.github.io/.agents/skills/**/SKILL.md` 的批量编辑
- 重构 skill 触发链(加互锁、改 description、改章节结构)
- 不适用于单文件小改(直接用 rust-standards 或 git-standards 就够)

## 仓库与路径

| 用途 | 路径 |
|---|---|
| 远程 | `https://github.com/eastspire/.agents` (main) |
| 本地 | `~/Documents/workspace/eastspire/eastspire.github.io/.agents/skills/` |
| hermes 加载 | `~/.hermes/skills/` (必须同步,否则 agent 不见新版本) |

## 标准流程(6 步)

### 1. 摸清现状

```bash
ls ~/Documents/workspace/eastspire/eastspire.github.io/.agents/skills/
# 然后对每个目标 SKILL.md:
wc -l path/to/SKILL.md
grep -E "^## " path/to/SKILL.md | head -50  # 列所有章节
```

### 2. 章节标题英化映射(高频)

参考以下映射表(用户已认可):

**euv-standards** (16 章): 概览→Overview / 项目元信息→Project Metadata / 安装→Installation / 5 行最小调用→5-Line Minimum Call / 等

**euv-ui-standards** (10 章): 规范来源→Source of Truth / 全局骨架→Global Skeleton / 核心组件 HTML 模板→Core Component HTML Templates / 等

**hyperlane-standards** (13 章): 互锁 skill→Mutual-Lock Skills / 项目元信息→Project Metadata / 22 个常见坑→22 Common Pitfalls / 等

**euv / hyperlane 入口 skill**:只改 `## 项目元信息`→`## Project Metadata` + 加 Index,**不重构入口 skill 的 legacy 章节**

**rust-standards**: **不全盘英化**。它在中文环境用,章节标题中文化是设计意图。只在前面加 `## Mutual-Lock Routing` 路由表。

### 3. 加 `## Index` 表格

每个多章节 SKILL.md 在 frontmatter 之后、第一个 `## N. xxx` 之前插入:

```markdown
## Index

| I want to... | Go to |
|---|---|
| ... | `## N. Section Name` |
| ... | `## N. Section Name` |

> 跨文件 anchor (`#section-name`) 在大多数 Markdown 渲染器里不可靠 → 字面用 `## Section Name`。
```

### 4. 加 `## Mutual-Lock Routing` 路由表(只在 rust-standards)

在 `## 检索方式` 之前插入路由表,显式列出"做 euv 任务跳 euv-standards 哪一节"等。

### 5. 同步到 hermes

```bash
rsync -av --exclude='__pycache__' \
  ~/Documents/workspace/eastspire/eastspire.github.io/.agents/skills/ \
  ~/.hermes/skills/
```

### 6. Commit + PR(走 gh-pr-creation-workflow)

```bash
git add .agents/skills/
git commit -m "chore(skills): add ## Index + English titles + Mutual-Lock Routing"
gh pr create --base main --title "chore: skill Index + English titles for hit-rate" \
  --body "## Summary ... ## Why ... ## Files ... ## Test plan ..."
```

## 硬性规则(踩过的坑)

1. **跨文件 anchor 不可靠** — 用字面 `## Section Name`,不用 `#section-name`
2. **Index 表格不要省略章节** — 95% 跳转目标覆盖,留空缺 agent 会回退到全文扫描
3. **rust-standards 的章节标题保留中文** — 不要英化(它本身就是中文环境用)
4. **入口 skill 不重构** — 只做"加 Index + 英化项目元信息"两件最小改动
5. **同步到 hermes 是最后一步,不能省** — 不然新会话 agent 加载的还是旧版
6. **description 写"必加载场景"** — 例: "Any Rust work — code, review, refactor — must load before generating Rust." 比 "Rust best practices" 命中率高
7. **章节标题 English-only**(除 rust-standards) — 用户已明确接受,理由是 LLM token 化效率

## 验证

```bash
# 1. 检查每个文件都有 ## Index
for f in ~/Documents/workspace/eastspire/eastspire.github.io/.agents/skills/{euv,euv-standards,euv-ui-standards,hyperlane,hyperlane-standards}/SKILL.md; do
  echo "=== $f ==="
  grep -E "^## Index" "$f" || echo "MISSING ## Index"
done
# 2. 检查中文章节标题(除 rust-standards)
grep -lE "^## [0-9]*\.[\xe4-\xe9][\x80-\xbf]{2}" ~/Documents/workspace/eastspire/eastspire.github.io/.agents/skills/*/SKILL.md
# 3. 检查 hermes 同步
diff -q ~/Documents/workspace/eastspire/eastspire.github.io/.agents/skills/euv-standards/SKILL.md ~/.hermes/skills/euv-standards/SKILL.md
```

## 关联 skill

- `gh-pr-creation-workflow` — commit + push + PR 的端到端流程
- `git-standards` — 章节标题 English-only 等编码规则的来源
- `rust-standards` — 互锁路由的入口 skill
- `agent-skills-source-sync` — 定期对账远程与本地 SKILL.md 数字声明是否一致
