---
name: multi-agent-team-setup
description: 'Hermes multi-agent team setup and the 4 coordination modes.'
license: MIT
metadata:
  version: 1.0.0
---

# Multi-Agent Team Setup

**核心**:Hermes 多 Agent 协作**不是堆砌 agent**,而是**角色隔离 + 流水线分工** —— 让不同 agent 各司其职,共同完成复杂任务。

**用户偏好(2026-08-19)**:
- 主 agent 配置和子 agent 保持一致(用 `hermes profile create --clone` 一键复刻)
- 主要目的是**解决上下文堆在主 agent 导致无效内容过多、单 agent 工作效率慢**
- 设计原则:**稳定性大于速度**(一个 agent 上下文崩溃,另一个可接手 —— 单 agent 做不到的冗余)
- **协同工作流程必须沉淀到 skill 和记忆** —— 不每次重设计

触发词:multi-agent, sub-agent, 子 agent, 委派, delegate, kanban, 看板, MoA, 模型合议, team setup, 团队, 角色隔离, profile create, SOUL.md, AGENTS.md, leader, orchestrator, 流水线, 角色分工。任何搭/调 Hermes 多个 agent 协同工作的任务(群聊代理、研究团队、流水线任务)都加载本 skill。

## 0. 四种模式速查(选哪个)

| 模式 | 工具入口 | 隔离级别 | 持久化 | 典型场景 |
|---|---|---|---|---|
| **Delegation 委派** | `delegate_task(goal, context, role, output_schema, background)` | 子 agent 隔离上下文,**只回摘要给主 agent** | 不持久(process-local) | 主任务拆成多个独立子任务;上下文分摊;`<5 min` 任务 |
| **Kanban 看板** | `hermes kanban <verb>` + `kanban_*` toolset | 任务边界硬隔离(`HERMES_KANBAN_BOARD` 钉入 env) | **持久**(SQLite board) | 多阶段、多 profile、多 worker 持久协作;任务状态从 todo 流转到 done;原子认领 / reclaimer / fail-blocking |
| **MoA 模型合议** | 多模型并行回答 → 主模型综合 | 仅 prompt 级别,共享工具 | 不持久 | 复杂/高风险决策,需要多角度听诊 |
| **Spawn 全进程** | `hermes chat -q '...'` / `hermes -w` via tmux PTY | 完全独立进程,独立 session + 工具 | 不持久,但 `hermes --continue / --resume` 可续 | 长跑任务(小时-天)、需交互 PTY、需完整工具访问 |

**选模式决策树**:
1. 任务 < 5 min + 需要摘要回主? → **Delegation**
2. 任务跨小时 + 多人接力? → **Kanban**
3. 决策类 + 需要多角度? → **MoA**
4. 需要交互、PTY、长期自主、长 session? → **Spawn**

**关键警告**:delegate_task 是 **process-local** —— 父进程 exit 子任务就丢。要持久或长跑 → 用 kanban / cron。

## 1. 5 步搭建团队

### Step 1:独立 Profile(子 agent 配置与主 agent 一致)

```bash
# 创建独立身份的 profile
hermes profile create "<角色名>"            # 全新配置

# 克隆当前 active profile —— 实现 "子 agent 配置和主 agent 保持一致"
hermes profile create "<角色名>" --clone   # 复刻所有 config + skills + memories + plugins + cron

# 改默认 profile (sticky)
hermes profile use "<角色名>"
# 或单次 CLI 调用: hermes -p <name> <cmd>
```

profile 布局 `~/.hermes/profiles/<name>/{skills, plugins, cron, memories/}`,与主 profile 同构。active profile 时**必须解析 `$HERMES_HOME``,**不要硬编** `~/.hermes`(见 `hermes-agent` skill)。

### Step 2:SOUL.md(角色隔离核心)

每个 profile 一份 `SOUL.md`,**明确定义**:
- **核心身份** —— 这个 agent 是谁(例:"研究院数据分析师 R1,专注量化分析与财报解读")
- **专长领域** —— 该 agent 能做什么(例:"statistical inference / pandas / 财务模型")
- **任务禁区** —— **不该**让该 agent 干的事(例:"不写代码、不做技术架构评估、不下最终结论 —— 那是 R2 / Leader")

SOUL.md 是**真正定义"角色"的文件**,不是 `hermes profile describe`。`profile describe` 给的是机器读的 metadata(`kanban orchestrator` 用),SOUL.md 是 agent 自己读的自我认知。

### Step 3:AGENTS.md(项目级共享事实)

在项目根目录创建 `AGENTS.md`,存:
- 项目**架构**(目录布局 / 关键模块 / 数据流)
- **协作规范**(commit message 风格、PR 流程、code review 红线、共享的 fmt 工具链)
- **任务进度**(哪些做了 / 哪些在做 / 谁负责 —— 主要给 leader 角色 agent 看)
- **共享上下文沉淀**(上次 PR 后的总结、跨 agent 都该知道的决策记录)

所有 profile 启动时都读 AGENTS.md 实现**任务背景的一致理解**。这也让 cron 任务、resume session、新加入的 agent 都能从这份 single source of truth 起步。

### Step 4:跨 Agent 通信

跨 agent 互操作需要**显式开启通信** —— Hermes **默认** profile 间相互隔离:

```yaml
# ~/.hermes/config.yaml
communication:
  cross_profile: true                 # 全局开关
  allowed_pairs:
    - [leader, researcher-1]
    - [leader, researcher-2]
    - [researcher-1, researcher-2]   # 研究员之间也允许(讨论),看场景
delivery:
  fan_out_targets:
    - researcher-1                    # Leader 发给 Researcher-1
    - researcher-2                    # Leader 也发给 Researcher-2
```

### Step 5:协作平台(消息群聊机器人)

```bash
hermes profile connect --platform feishu    # 飞书机器人
hermes profile connect --platform discord   # Discord 机器人
hermes profile connect --platform telegram  # Telegram bot
```

每个 profile 绑一个 channel / chat,组群后:**主 agent 在群里 @ 子 agent / 子 agent 用 `deliver: 'all'` 回放报告**。详见 `hermes-messaging-platform-setup` skill。

## 2. 实战:4 人 AI 研究团队

### 团队构成

| 角色 | profile 名 | 主要职责 | 模型选型 |
|---|---|---|---|
| Leader | `leader` | 汇总、决策、交付,**不直接参与讨论** | Pro / max-thinking 量级 |
| Researcher 1 | `r1-analyst` | 数据 + 财报分析 | 轻量模型(主力执行) |
| Researcher 2 | `r2-tech` | 技术架构 + 安全 | 轻量 |
| Researcher 3 | `r3-strategist` | 竞品分析 + 社区舆情 | 轻量 |
| (可选) Verifier | `verifier` | 关键流程校验 | 中量 |

### 协作流程

```
[User] -> [Leader via Feishu]
              |
              v
        Kanban board:
              +-- task R1 (analyst)    --> spawned researcher profile r1-analyst
              +-- task R2 (tech)       --> spawned r2-tech
              +-- task R3 (strategist)--> spawned r3-strategist
              |
              v
        Each researcher writes its section, mark complete on Kanban
              |
              v
        Leader watches board (heartbeat), consumes 3 deliverables
              |
              v
        Leader synthesizes into final report (Verifier optional)
              |
              v
        Final deliverable -> user via Feishu
```

### Profile 创建

```bash
hermes profile create leader --clone
hermes profile create r1-analyst --clone
hermes profile create r2-tech --clone
hermes profile create r3-strategist --clone
hermes profile create verifier --clone
# 每个 profile 配置 (示例 r1-analyst):
hermes profile use r1-analyst
# 编辑 SOUL.md: "你是 4 人研究团队的数据分析师。专长: pandas/财报/statistical inference。
#                禁区: 不写代码/不做技术评估/不下结论。只产出 <500 字 report + key numbers。"
hermes profile describe "data analyst — numbers, financials"
hermes profile connect --platform feishu --chat <chat_id_of_research_team> --bot-token <token>
```

### Cost 控制

每个 Researcher 用轻量模型(快/便宜),Leader 用 Pro 量级(准确/全面)。`config.yaml` profile-level model override:

```yaml
profiles:
  leader:
    model: anthropic/claude-opus-4
    max_thinking: high
  r1-analyst:
    model: anthropic/claude-haiku-4
  r2-tech:
    model: openai/gpt-4-mini
  r3-strategist:
    model: minimax-cn/MiniMax-M3
```

## 3. 避坑 + 进阶

### 从简开始

- ❌ 不要一开始就追求 5 agent 复杂团队
- ✅ 先「Planner + Synthesizer」**双角色** 跑通一个端到端任务,熟悉流程再扩

### 职责清晰,**禁止重叠**

- 两个 agent 都能干同一件事 → 任务冲突、重复劳动、互相覆盖
- 解决:SOUL.md 写明**任务禁区**(R1 不做技术评估、R2 不做市场分析)
- Kanban 上的任务**显式指派**(locked assignee),不要"谁有空谁认领"

### 关键流程加 Verifier

- 输出直接给用户前的最后一步,**加独立 verifier agent**(或同一个 profile 用 critic prompt 跑二遍)
- Verifier 拥有否决权;Verifier 不同意的输出 → 回到 worker 重做

### Bot Mode(Hermes Desktop)

Hermes Desktop 内置 Bot Mode 提供**友好团队管理界面**(vs 命令行手摆)。每个 Bot 可独立配:
- 角色 / SOUL 摘要
- 模型(per-bot)
- 记忆域(per-bot memories/)
- 工具白名单

走 GUI 而不是 CLI,**适合 5+ agent 团队**。CLI 模式适合开发调试 / 临时搭建。

### Skill 复用

- 一次稳定的多 agent 协作流程跑通 → **保存为 skill**(本 skill 就是这个例子)
- 下次类似任务 → skill 加载 + 复用 SOUL.md / AGENTS.md / profile 步骤,**不再从零设计**
- 写 SKILL.md 时**只写流程哲学 + 5 步 + 决策树**,具体工具语法链到 `hermes-agent` / `delegate_task` references

## 4. 互锁 skill / references

- **`hermes-agent`** (autonomous-ai-agents/) —— Hermes 操作 hub。`delegate_task` 工具接口、profile 路径解析、tmux PTY 多 agent 协作都在那里。本 skill 不重复。
- **`references/background-systems.md`** (in hermes-agent) —— Delegate / Cron / Curator / Kanban 四个后台系统的细节;本 skill §0 是浓缩版。
- **`hermes-messaging-platform-setup`** —— 飞书 / Discord / Telegram / Slack gateway 配置(Step 5)。
- **`merge-reconciler`** —— 多 agent 同时改同一份代码产生冲突时,调用中立 reconciler 解决。
- **`autonomous-ai-agents/{claude-code, codex, opencode}`** —— 这些是**外部** agent CLI 工具,Hermes 可以 spawn 它们当 worker(等同 §0 "Spawn" 模式),但权限/上下文由被 spawn 的工具自己管,需要额外配置。

## 5. 一行 cheat-sheet

**"我应该用哪种模式"**:
- < 5 min + 主 agent 上下文需要分摊 → `delegate_task`
- 跨小时 + 多人持久 → Kanban board
- 多角度决策 → MoA prompt
- 长跑 / 交互 / 完整工具 → `hermes chat` / `hermes -w` tmux

**"我该建几个 profile"**:
- 1 → 简单任务, 单 agent
- 2 → Planner+Synthesizer 双角色(起步)
- 3-5 → 真实团队(Leader + 多 Researchers + Verifier)
- > 5 → 启用 Hermes Desktop Bot Mode

**"Profile 该不该 --clone"**:
- 子 agent 配置和主 agent 一致 → `--clone`(用户偏好)
- 子 agent 需要**完全不同**的工具 / 能力 → 不要 `--clone`,手动 `profile create` 干净
