---
name: responding-to-issue-comments
description: 用户在 GitHub issue / PR 下收到第三方评论,需要评估评论是否合理 + 起草回复时使用。涵盖"评论拆解 / 回应模式 / 何时 push back 数字"等模式,适用于所有开源上游 issue / PR 协作。
---

# 回应 GitHub issue / PR 第三方评论

## 触发场景

用户问"这个评论正常吗 / 担忧合理吗 / 怎么回",或者自己准备在 issue / PR 下回评论时。

也适用于:用户说"回复的人的担忧"但指代不明确,需要先核查 + 起草回复。

## 步骤

### 1. 核查评论存在性 (指代不明时)

不要凭空虚构评论内容。按以下顺序查:

1. `gh issue view <num> --repo <owner>/<repo> --comments` — 查 issue 本身的评论
2. 查 issue 标题暗示的 sibling (例如标题里 "sibling of #N",查对应 issue 状态)
3. `gh pr list --author <user> --repo <owner>/<repo>` — 查对应 PR
4. `gh pr view <num> --comments` — 查 PR 的 review 评论
5. **区分 bot 评论 vs 人类评论**: github-actions / pyrefly / coverage bot 留言不是"人"
6. 找不到就列"状态表"(issue / PR 各自 0 评论?),明确告知 + 让用户补信息

### 2. 拆评论为有效点 + 可商榷点

对每条评论:

- ✅ **采纳点**: 新角度、新 failure mode、合理原则 — 标记
- ⚠️ **可商榷点**: 数字偏大/偏小、方案对当前场景不适用 — 标记 + 准备 push back
- ❌ **错误点**: 事实错误 — 标记

### 3. 起草回复 (5 段式)

1. **感谢 + 明确采纳新角度**: "Thanks for X, both worth incorporating" / "you're right that I should have made Y explicit" — 真的接受,不只是客气
2. **承认补充的 failure mode**: 用具体场景说明这个角度为什么重要
3. **礼貌但坚定 push back 错误数字/方案**: 用具体数据论证
   - 例如: "1MB cap would defeat the parent-child chunking pattern — at that point the 'child' is the same size as the parent"
   - 不是空对空,是用**设计意图**说话
4. **承认对方隐含关切的合理内核**: 把深层意图识别出来,作为 follow-up 空间
   - 例如: "If a deployment needs a different cap, promoting the constant to a configurable parameter is a reasonable follow-up"
5. **不揽活**: 不写 "happy to update" / "let me push a follow-up" — 只描述方案,让 maintainer 决定下一步

### 4. Push back 数字的核心论证方式

评论者说 "some upper bound (e.g., 1MB)" 这类"原则对 + 数字错"的建议时:

- **采纳原则** ("yes, the schema should enforce some upper bound")
- **push back 数字** ("but X MB is too large for *this* field, because [设计意图]")

反驳时一定说"为什么对**这个字段**不适用",用字段的设计目的说话,而不是"我不同意"。

## 用户偏好 (跨上游通用)

参考已有 user profile 的 "GitHub issue / discussion 风格偏好" 章节:

- 英文、礼貌、no all caps、no demanding language
- 标题和正文像写给陌生同事的邮件
- 加评论而非开新 issue
- 内容增量 (不重复别人说过的)
- 不主动揽活 (不写 "happy to PR")
