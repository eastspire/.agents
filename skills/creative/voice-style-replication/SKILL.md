---
name: voice-style-replication
description: 复刻真人文风的标准流水线:身份消歧 → quote 抓取 → 修辞分析 → 统一话术。避免 LLM 伪造人设。
when_to_use: 用户要做"复刻 X 话术 / X-style skill / 用 X 口吻写 / 模仿 X 文笔",且 X 是真实公众人物(创始人/名人/KOL)时强制加载。
license: MIT
metadata:
  hermes:
    tags: [voice-replication, persona-skill, celebrity-style, creative-writing, 话术复刻, 角色复刻]
    related_skills: [hermes-agent-skill-authoring, twitter-no-login, grounded-citations]
---

# Voice Style Replication — 真人文风复刻 skill 标准流水线

## Why this skill exists

2026-08-31 一次失败的复刻任务:**用户给 handle @zengying1107 要求做"曾颖风格 skill",我把它当成"孙宇晨的 TRON 太太 Stella(凡尔赛名媛)"写了 10K 字,完全错误**。@zengying1107 实际是曾颖(孙宇晨前女友,2026-08 因"颖学"白描讽刺派爆火)。凭 LLM 推断伪造了一个听起来 plausible 但人设相反的 skill。

这是 persona-replica skill 的典型失败模式:**LLM 容易把"听起来合理的人设"当成真实风格**。本 skill 把这种失败从根上堵住。

## When to Use (强制加载场景)

- "复刻 X 的文笔 / 话术 / 幽默逻辑" → 加载
- "用 X 的口吻写一篇..." → 加载
- "总结 X 的推特风格 / 微博风格 / 小红书风格" → 加载
- "X-style skill" / "voice imitation skill" / "persona skill" → 加载
- "模仿 X 的语言风格" → 加载

**不要用于**:
- 完全虚构角色(小说原创人物,无真实 quote)
- 抽象风格(不是某具体人,如"古风文言文")
- 用户只想要 1 段文案而不是个完整 skill
- 真实人物的隐私内容 / DM / 私信

## Hardline Rules(违反任何一条就停止重做)

### Rule 1 — 身份消歧先行

- 真实公众人物**经常重名**:`曾颖`在中文圈有多个;`孙宇晨`的伴侣不同时期不同人(早期 Stella vs 后期曾颖);同名 KOL 跨平台常见
- **用户提供 handle/链接时,handle 是权威身份源**(@zengying1107 就是 @zengying1107,不是 Stella)
- **用户只给名字不给 handle**:必须先 `clarify` 问"你指的是哪个 / 推特 handle 是什么 / 有具体主页吗"
- 搜名字时用 `"{name}" 真实身份 主页` 至少确认一次身份

### Rule 2 — 必须用真实 quote 抓取

- **真实 quote 优先于 LLM 推断**。不要因为"我大概知道 X 风格"就开写
- 至少 12-15 条 verbatim quote + URL 来源
- quote 来源优先级:
  1. 该人物本人公开内容(推特/微博/小红书 quote)
  2. 媒体报道 quote 该人物原文(带 URL)
  3. 该人物参与的访谈 / 演讲 / 公开发言
- 二手 quote 必须可定位到原始 URL

### Rule 3 — Quote 抓不到的诚实声明

- 如果抓不到真实 quote(网络/凭据/找不到),**不要**凭推断伪造
- 必须在 SKILL.md 的 Notes 部分明确写:`Based on LLM inference of public-known style; no verbatim quotes available`
- 这种 skill 可信度比"基于真实 quote"的低一档,frontmatter 要标 `[unverified-style]`

### Rule 4 — 对比相邻公众人物

- 公众人物很少孤立 —— 曾颖 style 必须在和孙宇晨"咯噔文学"的对比中才完整
- 抓 quote 时同时抓互动对象 / 同期人物的内容
- SKILL.md 要有"差异化"章节

## Quick Reference

| 任务 | 工具 |
|---|---|
| 身份消歧 | `clarify` 问 handle,或 Bing/360 search "{name} 真实身份 主页" |
| Quote 抓取(首选) | `xurl search "from:HANDLE" -n 50`(需 OAuth) |
| Quote 抓取(次选) | `web-access` CDP 浏览器(需 remote-debug) |
| Quote 抓取(兜底) | `twitter-no-login` skill(Bing/360/头条/搜狗/微博 search) |
| Quote 二次核验 | `grounded-citations` ledger 记录来源 URL |
| 发布 | `gh repo create eastspire/<handle>-skill --public`(personal 仓库免 PR) |

## Procedure(7 步,每步可验收)

### Step 1 — 身份消歧

**可验收**:已知道是谁 + 至少 2 条独立证据(handle / 媒体 quote / Wikipedia)。

```bash
# 用户给了 handle:直接信 handle
# 用户只给名字:clarify 工具问
# 第三方查证:用 web-search 搜 "{name}" handle 主页 真实身份
```

身份模糊直接停止,不靠 LLM 记忆。

### Step 2 — 抓 quote 语料

**可验收**:≥ 12 条 verbatim quote + 每条 URL 来源。

按 quote 来源优先级用工具链抓:

```bash
# 路径 A:有 OAuth
xurl search "from:HANDLE" -n 50

# 路径 B:有 CDP 浏览器
# 用 web-access skill 驱动 x.com / 微博 / 小红书

# 路径 C:出口受限(国内云常见)
python3 ~/.hermes/skills/twitter-no-login/scripts/twitter_no_login.py \
    profile <HANDLE> -n 30
# 然后 curl 每个 article_url 跑 extract_quoted_tweets(html)
```

每条 quote 用 `grounded-citations` 记 URL,带 verbatim quote 文本。

### Step 3 — 修辞分析

**可验收**:5-8 个明确句式模板 + 词汇表 + emoji/标点习惯 + 称谓系统 + 幽默逻辑。

从 quote 中提炼:
- **句式模板**(句首/句中/句尾公式)
- **必用词汇**(每类 5-10 个)
- **emoji / 标点习惯**(孙宇晨"!"密度 vs 曾颖"。"密度)
- **称谓系统**(对不同人用不同称呼:孙哥/某人/那位)
- **幽默逻辑**(自嘲?反讽?反差?排比?白描?)

### Step 4 — 写"统一话术" + Verification Checklist

**可验收**:有 5-8 条可勾选 checklist。

SKILL.md 中段必须包含:
- "修辞骨架"章节(模板/词汇/标点)
- "幽默逻辑"章节(他/她怎么搞笑)
- "统一话术"章节(可勾选的 5-8 条 checklist,每条可独立验证)

### Step 5 — Frontmatter + 触发词

**可验收**:description 含至少 3 个中英文 trigger word。

frontmatter description 必须:
- 简短(< 60 字符若 bundled,可较长若 personal repo)
- 含至少 3 个不同中英文 trigger(名字、handle、风格关键词)
- 用户能从 description 自我判断"这个 skill 是不是我要的"

### Step 6 — Disclaimer + 时间段

**可验收**:有 Notes 段声明"复刻而非冒名" + 时间段标注。

SKILL.md 末尾 Notes 段必须:
- "本 skill 是风格复刻工具,用于创意写作/角色扮演/教学,**不应**直接以本人账号发布冒充本人"
- 真实 handle 链接供查证
- 标注 quote 来自哪个时间段(早期 / 中期 / 后期)

### Step 7 — 发布到 eastspire 个人仓库

**可验收**:一个 persona 一个仓库 + 4 个基础文件。

```bash
mkdir -p ~/github/eastspire/<handle>-skill
# 写 SKILL.md / README.md / LICENSE / .gitignore
gh repo create eastspire/<handle>-skill --public \
    --description "..." --source=. --push
# personal 仓库(eastspire/*)免 PR,直接 master
```

每个 persona 一个独立仓库(用户偏好 2026-08-31 已确认)。

## Pitfalls

### Pitfall A — 身份消歧失败(本会话踩坑)

- @zengying1107 真实身份是**曾颖**(前女友,颖学讽刺派),不是 TRON 太太 Stella(凡尔赛名媛)
- 类似的身份混淆:`Mike Wang` 在加密圈 vs AI 圈是不同人;同名 CEO 跨公司常见
- **教训**:handle 是权威身份源;LLM 的"听起来 plausible 的人设"必须经 handle 验证

### Pitfall B — 网络 egress 限制(国内云)

- nitter / xcancel / jina / web.archive / ghall / DuckDuckGo / Yandex 在国内云基本全 timeout
- **替代通道**:Bing + 360 + 头条 + 搜狗 + 微博 search(详见 `twitter-no-login` skill)
- 不要在 SKILL.md 推荐 nitter / jina 这类在国内不可达的镜像

### Pitfall C — 二手 quote 二次解读错误

- 媒体 quote 一个人,可能掐头去尾或改字
- quote 后面标注媒体源,让 reviewer 自己核对原文
- 不要把媒体**标题**的修辞当成该人物的修辞(如"曾颖幽默小作文勾画孙割嘴脸"是腾讯新闻标题,不是曾颖本人写的)

### Pitfall D — 跨平台账号混用

- 公众人物可能在多个平台有不同账号(微博/推特/小红书),风格可能不同
- 标 quote 时写明平台;不要把微博风格和推特风格混在一起
- @tenten19901107(早期)和 @zengying1107(后期)同一个人的不同账号,quote 要分别标注

### Pitfall E — 时间段误读

- 公众人物的话术随时间变化(曾颖 2024-2025 严肃陈述 → 2026-08+ 玩梗自嘲)
- SKILL.md 要标注 quote 来自哪个时间段
- 不要默认"早期风格 = 当前风格"

### Pitfall F — 过度堆砌词汇表

- 词汇表是工具不是圣经 —— 一句文案用 3-5 个目标词足够
- 不要让 LLM 写一条推文时把所有目标词都用上(那是填字游戏)

### Pitfall G — 同名人物混用导致的"配偶档"错误

- 孙宇晨的伴侣不同时期不同人:Stella(早期,凡尔赛太太)≠ 曾颖(后期,前女友讽刺派)
- 写"夫妻档互动" skill 前必须确认身份和关系时间线
- 错配的配偶档会让 skill 输出尴尬矛盾内容

## Verification

SKILL.md 完成后自检:

- [ ] 身份有 2 条以上证据确认(handle + 媒体 quote + Wikipedia 至少 2 条)?
- [ ] ≥ 12 条 verbatim quote + URL?
- [ ] quote 来源覆盖 5 个不同场景(营销/自嘲/危机/事件/日常)?
- [ ] 5-8 条统一话术模板?
- [ ] Frontmatter description 含触发词?
- [ ] 有 Notes 段 disclaimer?
- [ ] 有 Verification checklist(5-8 条可勾选项)?
- [ ] 时间段标注?
- [ ] 发布到 eastspire/x-style 单仓库(每个 persona 一个仓)?
- [ ] README + LICENSE + .gitignore 都到位?

10 项全勾 = 这个 voice-style-replication skill 可发布。

## 与其他 skill 的关系

- **`hermes-agent-skill-authoring`**(user-owned,需 adopt 才能改):通用 skill 写作规范。本 skill 是它的"persona-replica"子场景补充,**强烈建议**两者都加载
- **`twitter-no-login`**:本 skill 真实 quote 抓取阶段首选 fallback(见 Procedure Step 2)
- **`xurl`**:本 skill 真实 quote 抓取阶段首选(若有 OAuth)
- **`web-access`**:本 skill 真实 quote 抓取阶段次选(若有 CDP 浏览器)
- **`grounded-citations`**:本 skill 来源溯源工具,所有 quote URL 入 ledger

## Notes

- 本 skill 是元技能(meta-skill),不是某个具体 persona。它给"做名人 X 的复刻 skill"提供标准流水线
- 历史踩坑:见 `references/zeng-ying-mistakes.md`(@zengying1107 → 曾颖,而非 Stella)
- 后续 persona-replica 任务:任何 X 的复刻 skill,加载本文档走 7 步流水线,违反任何 Hardline Rule 立即停止重做