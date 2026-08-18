---
name: rust-pr-contribution-workflow
description: 找高星 Rust 项目 → 挑 easy issue → 提交 PR 的端到端工作流。包含项目挑选标准、并行子 agent 调研模板、候选汇报格式、PR 改写流程、踩坑记录、验证清单。
---

# Rust 开源项目 PR 贡献工作流

**触发场景**: 用户要"找高星 Rust 项目 → 找容易改的 issue → 提交 PR",目标 N 个 PR。

**核心原则**:
- **质量 > 数量**: 宁可换项目也不强凑 PR
- **容易改 = 优先范围**: 文档 typo / wording 改进 / 文档过时引用 / 错误信息改进 / 明确标注 good first issue 的小重构
- **不可逆操作要确认**: 改代码 + push 分支 + 开 PR 前,先向用户汇报候选清单,等明确确认
- **严格遵守 master/main 禁止 push 规则**

## 1. 选项目 (并行调研)

**挑选标准** (全部满足):
- 高星 (≥5k,优先 ≥10k)
- 活跃 (最近 1-3 个月有 commit)
- **必须有 good first issue / help wanted / E-easy 池** (用 `gh issue list --label "good first issue" --state open` 验证 ≥3 个,否则跳过)
- 欢迎外部贡献 (CONTRIBUTING.md 明确,或历史 PR 接受率高)
- 未归档

**优先候选池** (验证过有 easy issue 的高星项目):
- tokio-rs/tracing, tokio-rs/axum (⚠️ 容易枯竭,先验证)
- clap-rs/clap, serde-rs/json, serde-rs/serde
- rust-lang/cargo, rust-lang/rust-clippy
- image-rs/image, burn-rs/burn
- dtolnay/thiserror, dtolnay/anyhow

**启动并行子 agent**: 每个项目一个 delegate_task,任务描述固定模板:
```
任务: 调研 {owner/repo} 仓库的 easy issue
1. `gh issue list --repo {owner}/{repo} --state open --label "good first issue" --limit 50`
2. `gh issue list --repo {owner}/{repo} --state open --label "E-easy" --limit 50`
3. `gh issue list --repo {owner/{repo}} --state open --label "help wanted" --search "documentation OR typo OR wording" --limit 30`
4. 过滤出 1-2 个**最适合**的候选:
   - 无人认领 (无 "I'd like to work on this" 类评论)
   - 范围明确 (改哪几行/哪个文件)
   - 难度 ★☆☆ ~ ★★☆
   - 维护者态度积极 (最近评论说"可做"/"欢迎 PR" 或沉默但无反对)
5. **不实际改代码**,只报告:
   - 候选 issue 编号 + 标题 + 链接
   - 类型 (typo / wording / 文档过时 / 小重构)
   - 建议改法 (文件 + 大概行数)
   - 维护者态度摘要
   - 风险点
```

## 2. 候选清单汇报模板

向用户汇总时用表格,字段:
| # | 项目 | Star | Issue | 难度 | 类型 | 维护者态度 | 风险 |

明确告诉用户:
- 哪些项目被跳过 + 原因 (如 axum 0 good first issue)
- 备选候选 (供用户挑选/替换)
- 让用户在 A/B/C/D 方案中拍板 (常见: A 接受全部 / B 换项目 / C 减目标 / D 自己选)

## 3. 改 PR 流程 (用户确认后)

**每个 PR 都走标准流程**,绝不批量自动化:
1. **fork 到 eastspire/<repo>** (用 gh CLI `gh repo fork` 或 web UI)
2. **clone fork** 到本地 (注意 clone 的是 eastspire fork,不是 upstream)
3. **加 upstream remote**: `git remote add upstream https://github.com/{owner}/{repo}.git`
4. **同步 master**: `git fetch upstream && git checkout master && git merge upstream/master`
5. **创建 fix 分支**: `git checkout -b fix/<scope>-<desc>` (scope = 文件名或 issue 关键词, desc = 动词短语)
6. **改代码**: 最小改动,只改 issue 涉及的内容,**不加无关 formatting / unrelated changes**
7. **commit 规范** (见 git-standards skill):
   - 标题: `fix(<scope>): <desc>` 或 `docs(<scope>): <desc>`
   - 正文: 引用 issue `Fixes #NNNN` 或 `Closes #NNNN`
8. **push feature 分支** (不是 master): `git push -u origin fix/<scope>-<desc>`
   - **长 timeout 必备** (见 memory: 默认 120s 不够,用 10 分钟)
9. **创建 PR**: `gh pr create --repo {owner}/{repo} --base master --head eastspire:{branch} --title "..." --body "..."`
   - body 模板: "Closes #NNNN\n\n## Summary\n- <改了什么>\n\n## Test plan\n- [ ] <怎么验证>"

## 4. 踩坑 (从 2026-08-17 调研总结)

- **axum 等热门项目**: good first issue 池容易枯竭,**先验证再选**,不要看 star 高就上
- **cargo 仓库**: 维护者对 README 绝对 URL 改造态度保守 (见 cargo #16865 案例),**改动前先在 issue 里 ping 确认**
- **clap**: 维护者 epage 会在 issue 里直接表态"可做"或"等发版",态度透明
  - clap #5163 ("docs: link to table of contents") 已被 master 吸收,选 issue 前**必须读 body 全文**,不能只看标题
  - clap A-docs 标签下 issue 多被认领或需大改,极简 doc-only 候选稀缺(仅 #4904 Arg::default_value_if doctest 谓词较干净)
- **tracing**: 文档引用 feature 经常过时 (issue #3518 案例),改文档 risk 低
- **GH_TOKEN 在 sandbox 拿不到**: 子 agent (delegate_task / execute_code) 跑 `gh issue list` 不会自动继承 shell env,**主进程先 export 或子 agent 用 `source ~/.bashrc`** 验证
- **delegate_task 子 agent 反馈格式**: 不强制要求,主进程整合时统一表格化
- **git push 到 fork 失败**: credential helper 脚本在某些环境不生效,直接用 `https://x-access-token:${GH_TOKEN}@github.com/{owner}/{repo}.git` 一次性 URL 最稳
- **2026-08-17 失败案例**: 选了 clap #5163,没读 body,误判为"add error link",实际 issue 是"tutorial 链接改 ToC"且已被吸收。commit 后 force push 撤销。**核心教训: 任何改代码操作前必须先汇报候选 + 等用户确认**

## 5. 验证清单 (每个 PR 提交前)

- [ ] 分支名规范 (`fix/<scope>-<desc>`)
- [ ] commit 标题 + Fixes/Closes 引用 issue
- [ ] 改动**只**包含 issue 相关内容
- [ ] 没直接 push master/main
- [ ] PR title 不超过 70 字符
- [ ] PR body 包含: Closes # + Summary + Test plan
- [ ] 维护者最近 30 天评论过类似 PR (说明仓库活跃接收贡献)

## 6. 完成后

向用户报告:
- 每个 PR 链接 (URL)
- 等待 review 的预期时间 (看仓库历史 PR 关闭速度)
- **不主动 ping maintainer** (符合用户"礼貌、不主动揽活"偏好)
- 在 memory 里更新"已开 PR 列表",方便后续 follow-up
