---
name: hermes-cronjob-daily-news-html
description: 用 Hermes cronjob 创建每日定时任务，自动抓取科技资讯 → 生成单文件 HTML → 上传 MCP CDN → 飞书推送链接。适用于"每天 X 点推送新闻/报告/汇总"的场景。
---

# Hermes Cronjob 每日新闻 HTML 推送

## 适用场景
用户要"每天早上 X 点推送最近 N 小时内的 XX 资讯/新闻/报告"，输出形式是：
1. 抓取内容
2. 渲染为单文件 HTML（CSS/JS 内联，无需后端）
3. 上传到 CDN 拿到可访问 URL
4. 通过 IM（飞书/微信等）推送 URL

## 创建任务的核心命令

```bash
hermes cronjob create \
  --name "任务中文名" \
  --schedule "0 8 * * *" \
  --push-to origin \
  --prompt "执行步骤..." \
  --skills ""  # 如果不需要加载 skills，传空字符串
```

### 关键参数说明
- `--schedule`：标准 crontab 5 字段格式（分 时 日 月 周）
- `--push-to`：推送目标（origin = 飞书，需先在 im-setup 配置）
- `--prompt`：任务执行逻辑的完整 prompt，要包含所有步骤和工具名
- `--skills`：逗号分隔的 skill 列表。**如果 skills 不在系统 ~/.hermes/skills/ 下，必须传空字符串或省略，否则任务加载报错**
- `--timezone`：可选，默认 UTC；如果用户在中国，时区要注意（"0 8 * * *" UTC = 北京时间 16:00）

### prompt 模板
```
[任务描述]

步骤：
1. 用 web_search 搜索过去 24 小时的 [主题] 资讯，抓取 10-15 条
2. 用 execute_code 渲染为单文件 HTML（CSS 内联，移动端友好卡片式）
3. 用 terminal 把 HTML 保存到 /root/[dir]/[filename].html
4. 用 mcp_matrix_upload_to_cdn 把文件上传到 CDN
5. 用 message 工具（飞书/微信）把 CDN URL 推送给用户
6. 报告完成
```

## 手动触发

```bash
hermes cronjob get <id>      # 查看详情
hermes cronjob run <id>      # 入队（不立即执行）
hermes cronjob delete <id>   # 删除
```

**注意**：`run` 命令只把任务入队，需等调度器下一轮轮询才会真正执行。如果要立即看到效果，**自己执行 prompt 里的步骤**。

## 本机网络限制（已踩坑）

本机出站限制：
- **25/465/587 端口**全部超时 → 任何 SMTP 邮件发送都不可能
- **apt update 超时** → 不能用 apt 装包
- **storage.googleapis.com 下载经常超时/损坏** → puppeteer 的 chrome-headless-shell 装不下来
- **443 出站可用** → HTTPS API 可用

**结论**：
- ❌ 邮件推送方案在本机行不通
- ❌ hyperlane-upload skill（依赖 puppeteer+Chrome）也跑不起来
- ✅ mcp_matrix_upload_to_cdn 是最可靠的外部分发方案

## HTML 生成要点

- 单文件，CSS/JS 全内联，无外部依赖
- 移动端优先（max-width: 600px，padding 16-20px）
- 卡片式布局：每条新闻一张卡片，标题（链接到原文）、来源、时间、摘要
- header 包含日期和条数
- footer 包含生成时间戳
- 中文字体优先 -apple-system, "PingFang SC", "Microsoft YaHei"

## 任务调度最佳实践

- 改任务**不直接 edit**，而是 delete 旧的 + create 新的（更稳定）
- prompt 写在多行用双引号包裹，hermes 内部会处理转义
- 测试时手动 `run` + 等待调度器轮询；或自己直接执行 prompt 步骤验证 HTML 渲染效果
- 用户的偏好是"完成就行"，不要在 prompt 里写"如果失败请报告"这类话术，直接给最终输出
