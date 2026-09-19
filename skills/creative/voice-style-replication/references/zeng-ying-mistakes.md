# Zeng Ying Mistakes — 2026-08-31 案例研究

## 事件经过

用户在消息 4 给出 handle `@zengying1107`,要求做"曾颖 skill"。我做了以下错误推断:

1. **错误默认**:我读到"曾颖 + 跟孙宇晨相关" → 直接归类为"TRON 太太/Stella"
2. **错误假设**:LLM 推断孙宇晨周围女性人物都是"凡尔赛名媛 / 恩爱秀 / 高奢生活秀"调性
3. **错误执行**:写了 10K 字 SKILL.md + 推到 eastspire/zeng-ying-skill 仓库
4. **错误继续**:用户没纠正前我没自查

## 真实数据

**@zengying1107 = 曾颖** = 孙宇晨**前女友**(2024 年底被以"咖位不同"分手),2026-08 因"颖学"风格全网爆火。

真实身份要素(从腾讯新闻、新浪娱乐、msn 等媒体二手 quote 整理):

- 1990-11-07 生,南京人,早稻田大学金融系
- 日本同道文化株式会社创始人/CEO
- 2017-2024 与孙宇晨恋爱七年,曾颖自述倾尽积蓄支持收购日本加密交易所
- 2025-04 开撕孙宇晨
- 2026-08-28 发微博喊话景甜 `#最佳前任#` + "教你洗内裤"梗,过亿阅读
- 媒体对她的修辞关键词:**冷幽默 / 白描 / 讽刺 / 松弛 / 围观 / 视角清醒 / 拒绝华丽辞堆砌**
- 对比"**咯噔文学**"(孙宇晨 AI 模板化自我感动)vs "**颖学**"(曾颖白描讽刺)
- 关键金句:`孙学的本质是赢学,是拒绝情感,利益至上`(曾颖原话)
- 排比招牌:`是那个在我去美国时穿着貂皮大衣,带着我入住招待所的孙哥 / 也是那个在吃完饭拿出无数优惠券...`

## 错在哪几个环节

### 1. 身份消歧失败

- 用户给了 handle `@zengying1107`,我应该立即相信 handle 的权威性
- 我没去查 "@zengying1107 是谁",直接套用了我对"曾颖"名字的 LLM 记忆
- 实际上 `@zengying1107` 在 x.com 上的真实身份是曾颖(孙宇晨前女友),不是 TRON 太太 Stella

### 2. 配偶档错配

- 我把 Stella(早期 TRON 太太 / 凡尔赛名媛)和曾颖(后期前女友 / 颖学讽刺派)混淆
- 这两个**不是同一个人**,且立场完全相反(恩爱 vs 开撕)
- 写出来的"夫妻档互动" skill 完全不成立

### 3. 没抓真实 quote 就开写

- 第一次写 zeng-ying-skill 时,我完全凭 LLM 推断写了 10K 字
- 真实 quote 是用户在第三次消息里说"https://x.com/zengying1107 这是曾颖主页"之后,我用 Bing 搜了 5 分钟才抓到
- 应该第一次就先去抓 quote,而不是靠"听起来 plausible"推断

## 修复方式

### 立即修复(本会话已做)

1. ✅ 删除原 zeng-ying-skill 仓库里的错误 SKILL.md
2. ✅ 重新搜索 @zengying1107 / @tenten19901107 / "曾颖" / "颖学" 真实 quote
3. ✅ 真实 quote 抽取后重写 zeng-ying-skill SKILL.md(白描讽刺 + 排比 + 细节反差 + 松弛围观)
4. ✅ 更新仓库 GitHub description

### 防止再犯(本 skill 创建)

✅ 创建 `voice-style-replication` 元技能,强制 7 步流水线:

1. 身份消歧(用户给 handle → 信 handle)
2. 抓 quote(必须 ≥ 12 条 verbatim + URL)
3. 修辞分析
4. 写统一话术 + checklist
5. Frontmatter + 触发词
6. Disclaimer + 时间段
7. 发布

**任何 Hardline Rule 违反立即停止重做,不靠"看起来对"判断**。

## 教训总结(给后续 agent)

| 教训 | 应用 |
|---|---|
| Handle 是权威身份源 | 用户给 handle → 立即按 handle 写,不靠"这个名字听起来像谁" |
| LLM 推断 ≠ 真实风格 | 没有 12 条 verbatim quote 不开始写 SKILL.md |
| 同名公众人物混用最危险 | 写"配偶档"前必须验证关系时间线 |
| 国内云抓推特走搜索引擎兜底 | nitter/jina 全 timeout,必须用 twitter-no-login skill |
| 错误早暴露成本更低 | 10K 字写完才发现错 = 浪费用户信任 + 时间 |
| 元技能能挡住一类错误 | 不只修这一个错,提炼流水线挡住未来同类错误 |

## 相关引用

- 已发布的正确 zeng-ying-skill: https://github.com/eastspire/zeng-ying-skill
- 同期 sun-yuchen-skill(孙宇晨): https://github.com/eastspire/sun-yuchen-skill
- 兜底 quote 抓取 skill: https://github.com/eastspire/twitter-no-login
- 元技能(本文):`creative/voice-style-replication/SKILL.md`

## Notes

- 本案例后续应该进** `references/zeng-ying-mistakes.md`** 作为 persona-replica skill 的反例素材
- 如果后续有类似"用户给名字但实际另有所指"的情况,把这个 case 提出来提醒用户
- 不要再混淆 Stella / 曾颖 —— 这两个是公开身份上完全不同的两个人