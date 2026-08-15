---
name: im-setup
description: 连接和配置 IM/消息平台（飞书、微信、Telegram、Discord、Slack、钉钉、企业微信等）
category: platform-setup
---

# IM 平台连接指南

当用户要求连接、绑定或配置任何 IM 平台时，按以下步骤操作。

## 通用流程

1. 向用户索要平台凭证（Token / App ID / Secret 等）
2. 将凭证写入 `~/.hermes/.env`（每行一个 KEY=VALUE）
3. 配置访问控制
4. 启动 Gateway：`hermes gateway run`

也可用交互式引导：`hermes gateway setup`

---

## 飞书 / Lark

**连接方式**：WebSocket（推荐）或 Webhook

**必需环境变量**：
```
FEISHU_APP_ID=cli_xxxxx
FEISHU_APP_SECRET=your_secret
FEISHU_DOMAIN=feishu
FEISHU_CONNECTION_MODE=websocket
```

**可选环境变量**：
```
FEISHU_ALLOWED_USERS=user_id1,user_id2    # 用户白名单
FEISHU_GROUP_POLICY=open                   # 群聊策略：open（@时回复）/ disabled
FEISHU_HOME_CHANNEL=chat_id               # 定时任务/通知投递频道
# Webhook 模式专用：
FEISHU_WEBHOOK_HOST=127.0.0.1
FEISHU_WEBHOOK_PORT=8765
FEISHU_WEBHOOK_PATH=/feishu/webhook
FEISHU_ENCRYPT_KEY=your_key               # 签名验证
FEISHU_VERIFICATION_TOKEN=your_token
```

**获取凭证**：
1. 登录 [飞书开放平台](https://open.feishu.cn/)（国际版用 [Lark](https://open.larksuite.com/)）
2. 创建企业自建应用 → 启用机器人能力
3. 复制 App ID 和 App Secret
4. 事件订阅选择 WebSocket 模式（无需公网 URL）

**快捷方式**：运行 `hermes gateway setup` 可通过扫码自动创建机器人（QR scan-to-create）。

**依赖**：`lark-oapi`、`websockets`（WebSocket 模式）或 `aiohttp`（Webhook 模式）

**消息长度限制**：8000 字符

---

## Telegram

**连接方式**：长轮询（默认）或 Webhook

**必需环境变量**：
```
TELEGRAM_BOT_TOKEN=123456:ABC-DEF...
```

**可选环境变量**：
```
TELEGRAM_ALLOWED_USERS=user_id1,user_id2
TELEGRAM_HOME_CHANNEL=user_id             # 通知投递（DM 场景即你的 user ID）
# Webhook 模式（需要公网 HTTPS URL）：
TELEGRAM_WEBHOOK_URL=https://your-domain.com/telegram
TELEGRAM_WEBHOOK_PORT=8443
TELEGRAM_WEBHOOK_SECRET=your_secret
# 网络调优：
TELEGRAM_FALLBACK_IPS=149.154.167.220     # api.telegram.org 被墙时的备用 IP
TELEGRAM_REQUIRE_MENTION=false            # 群聊中是否需要 @
```

**获取凭证**：
1. 在 Telegram 中找 **@BotFather** → 发送 `/newbot`
2. 按提示创建机器人 → 复制 Bot Token
3. 查找 user ID：给 **@userinfobot** 发消息

**依赖**：`python-telegram-bot[webhooks]>=22.6`

**特性**：自动 DNS-over-HTTPS 发现备用 IP、消息批量合并、支持 Forum Topics

---

## Discord

**连接方式**：WebSocket（Discord Gateway）

**必需环境变量**：
```
DISCORD_BOT_TOKEN=your_bot_token
```

**可选环境变量**：
```
DISCORD_ALLOWED_USERS=user_id1,user_id2     # 支持数字 ID 或用户名
DISCORD_HOME_CHANNEL=channel_id
DISCORD_REQUIRE_MENTION=true                 # 频道中需要 @（默认 true）
DISCORD_FREE_RESPONSE_CHANNELS=ch1,ch2       # 无需 @ 的频道
DISCORD_AUTO_THREAD=true                     # @时自动创建线程
DISCORD_ALLOW_BOTS=none                      # none / mentions / all
DISCORD_PROXY=socks5://proxy:1080            # 代理
```

**获取凭证**：
1. 访问 [Discord Developer Portal](https://discord.com/developers) → New Application
2. 进入 **Bot** 页面 → Reset Token → 复制 Token
3. **Privileged Gateway Intents**（同一页面下方）：
   - 启用 **Message Content Intent**（必须，否则 bot 无法读取消息内容）
   - 如果 `DISCORD_ALLOWED_USERS` 中使用了用户名（非纯数字 ID），还需启用 **Server Members Intent**
4. 进入 **OAuth2 → URL Generator**：
   - Scopes 勾选：`bot` + `applications.commands`
   - Bot Permissions 勾选：
     - **Send Messages**（发送消息）
     - **Send Messages in Threads**（在线程中回复）
     - **Create Public Threads**（自动创建线程，`DISCORD_AUTO_THREAD` 默认开启）
     - **Read Message History**（读取历史消息）
     - **Attach Files**（上传文件/图片）
     - **Add Reactions**（处理中 👀 / 完成 ✅❌ 表情反馈）
     - **Use External Emojis**（可选）
5. 复制生成的 URL，在浏览器中打开邀请 bot 到服务器
6. Discord 设置 → Advanced → 开启 **Developer Mode**
7. 右键用户 → Copy User ID（填入 `DISCORD_ALLOWED_USERS`）
8. 右键频道 → Copy Channel ID（填入 `DISCORD_HOME_CHANNEL`）

**依赖**：`discord.py[voice]>=2.7.1`

---

## Slack

**连接方式**：Socket Mode（WebSocket，无需公网 URL）

**必需环境变量**：
```
SLACK_BOT_TOKEN=xoxb-...
SLACK_APP_TOKEN=xapp-...
```

**可选环境变量**：
```
SLACK_ALLOWED_USERS=U12345,U67890
SLACK_REQUIRE_MENTION=true            # 频道中需要 @（默认 true）
SLACK_FREE_RESPONSE_CHANNELS=C1,C2   # 无需 @ 的频道
SLACK_ALLOW_BOTS=none                 # none / mentions / all
```

**获取凭证**：
1. 访问 [Slack API](https://api.slack.com/apps) → Create New App → From Scratch
2. Settings → Socket Mode → Enable → 创建 App-Level Token（scope: `connections:write`）→ 复制 `xapp-...`
3. OAuth & Permissions → Bot Token Scopes 添加：
   `chat:write`, `app_mentions:read`, `channels:history`, `channels:read`, `groups:history`, `im:history`, `im:read`, `im:write`, `users:read`, `files:write`
4. Event Subscriptions → 订阅：`message.im`, `message.channels`, `app_mention`
5. Install to Workspace → 复制 `xoxb-...` Token
6. **每次修改 scope 或 event 后需重新安装应用**
7. 在频道中 `/invite @YourBot` 邀请机器人

**依赖**：`slack-bolt>=1.18.0`、`slack-sdk>=3.27.0`

---

## 钉钉 / DingTalk

**连接方式**：Stream Mode（WebSocket）

**必需环境变量**：
```
DINGTALK_CLIENT_ID=your_app_key
DINGTALK_CLIENT_SECRET=your_app_secret
```

**可选环境变量**：
```
DINGTALK_ALLOWED_USERS=user_id1,user_id2
```

**获取凭证**：
1. 访问 [钉钉开放平台](https://open-dev.dingtalk.com) → 创建应用
2. 凭证管理 → 复制 AppKey（Client ID）和 AppSecret（Client Secret）
3. 在机器人设置中启用 **Stream 模式**
4. 将机器人添加到群聊或直接私聊

**依赖**：`dingtalk-stream>=0.1.0`、`httpx`

**回复方式**：通过消息附带的 session_webhook URL 发送 Markdown 格式回复

---

## 微信 / WeChat（个人号）

**连接方式**：iLink Bot API 长轮询（无需公网端点）

**连接流程**：微信连接需要扫码登录，**请在 Web 端点击「连接微信」按钮扫码完成绑定**。命令行无法完成此操作。

**绑定后的环境变量**（自动写入，无需手动配置）：
```
WEIXIN_ACCOUNT_ID=your_account_id
WEIXIN_TOKEN=your_bot_token
WEIXIN_BASE_URL=https://ilinkai.weixin.qq.com
```

**可选环境变量**：
```
WEIXIN_DM_POLICY=open                          # open / allowlist / disabled / pairing
WEIXIN_ALLOWED_USERS=user_id1,user_id2         # DM 白名单（需 allowlist 策略）
WEIXIN_GROUP_POLICY=disabled                   # open / allowlist / disabled（默认 disabled）
WEIXIN_GROUP_ALLOWED_USERS=group_id1,group_id2 # 群聊白名单
WEIXIN_HOME_CHANNEL=chat_id                    # 定时任务/通知投递
```

**注意事项**：
- 此适配器适用于**个人微信账号**，不是企业微信（WeCom）
- 群组策略默认 `disabled`（与其他平台不同），因为个人微信可能加入大量群组
- 登录会话可能过期（errcode=-14），需要重新扫码
- 媒体文件通过 AES-128-ECB 加密 CDN 传输，需要 `cryptography` 包

**依赖**：`aiohttp`、`cryptography`

**消息长度限制**：4000 字符

---

## 企业微信 / WeCom — AI Bot 模式

**连接方式**：WebSocket（`wss://openws.work.weixin.qq.com`）

**必需环境变量**：
```
WECOM_BOT_ID=your_bot_id
WECOM_SECRET=your_secret
```

**可选环境变量**：
```
WECOM_DM_POLICY=open                    # open / allowlist / disabled / pairing
WECOM_ALLOW_FROM=user1,user2            # DM 白名单（需 allowlist 策略）
WECOM_GROUP_POLICY=open                 # open / allowlist / disabled
WECOM_GROUP_ALLOW_FROM=group1,group2    # 群聊白名单
WECOM_HOME_CHANNEL=chat_id
WECOM_WEBSOCKET_URL=wss://...           # 自定义 WS 端点
```

**获取凭证**：
1. 企业微信管理后台 → 应用管理 → 创建 AI 机器人
2. 复制 Bot ID 和 Secret

**依赖**：`aiohttp`、`httpx`

**媒体限制**：图片 10MB、视频 10MB、语音 2MB（仅 AMR）、文件 20MB

---

## 企业微信 / WeCom — 自建应用回调模式

**连接方式**：HTTP 回调（企业微信推送到你的服务器）

**必需环境变量**：
```
WECOM_CALLBACK_CORP_ID=ww1234567890abcdef
WECOM_CALLBACK_CORP_SECRET=your_secret
WECOM_CALLBACK_AGENT_ID=1000002
WECOM_CALLBACK_TOKEN=your_token
WECOM_CALLBACK_ENCODING_AES_KEY=your_aes_key
```

**可选环境变量**：
```
WECOM_CALLBACK_PORT=8645                   # HTTP 监听端口
WECOM_CALLBACK_ALLOWED_USERS=user1,user2
```

**获取凭证**：
1. 企业微信管理后台 → 应用管理 → 创建自建应用
2. 在 API 接收消息 → 设置回调 URL、Token、EncodingAESKey

**依赖**：`aiohttp`、`httpx`

**特性**：支持多企业/多应用（通过 config.yaml 的 `apps` 列表）、AES-128-CBC 加密验证

**消息长度限制**：2048 字符

---

## Matrix

**连接方式**：Matrix Sync API（长轮询）

**必需环境变量**（二选一认证方式）：
```
# 方式一：Access Token（推荐）
MATRIX_HOMESERVER=https://matrix.example.com
MATRIX_ACCESS_TOKEN=your_access_token

# 方式二：密码登录
MATRIX_HOMESERVER=https://matrix.example.com
MATRIX_USER_ID=@bot:example.com
MATRIX_PASSWORD=your_password
```

**可选环境变量**：
```
MATRIX_ENCRYPTION=true                        # 启用端到端加密
MATRIX_DEVICE_ID=HERMES_BOT                   # E2EE 设备 ID（跨重启持久化）
MATRIX_RECOVERY_KEY=your_key                  # 交叉签名验证
MATRIX_ALLOWED_USERS=@user1:server,@user2:server
MATRIX_HOME_ROOM=!room_id:server
MATRIX_REQUIRE_MENTION=true
MATRIX_AUTO_THREAD=true
```

**获取凭证**：
1. 在任意 Matrix 服务器创建账号（self-hosted Synapse/Conduit 或 matrix.org）
2. Element → 设置 → Help & About → Access Token
3. 或通过 API：`curl -X POST https://server/_matrix/client/v3/login -d '{"type":"m.login.password","user":"@bot:server","password":"..."}'`

**依赖**：`mautrix`（E2EE 需 `mautrix[encryption]` + libolm C 库）

---

## Email

**连接方式**：IMAP 轮询（收）+ SMTP（发）

**必需环境变量**：
```
EMAIL_ADDRESS=bot@example.com
EMAIL_PASSWORD=your_password
EMAIL_IMAP_HOST=imap.gmail.com
EMAIL_SMTP_HOST=smtp.gmail.com
```

**可选环境变量**：
```
EMAIL_IMAP_PORT=993
EMAIL_SMTP_PORT=587
EMAIL_POLL_INTERVAL=15                    # 轮询间隔（秒）
EMAIL_ALLOWED_USERS=user1@mail.com,user2@mail.com
```

**常用邮箱配置**：
- Gmail：IMAP `imap.gmail.com:993`、SMTP `smtp.gmail.com:587`，需使用 [App Password](https://myaccount.google.com/apppasswords)（需先开 2FA）
- Outlook：IMAP `outlook.office365.com:993`、SMTP `smtp.office365.com:587`

**消息长度限制**：50000 字符

---

## WhatsApp

**连接方式**：Node.js Bridge（本地子进程）

**配置流程**（需交互式操作）：
1. 运行 `hermes whatsapp`
2. 选择模式：
   - **Bot 模式**：独立手机号（推荐，需第二个号码）
   - **Self-chat 模式**：给自己发消息与 agent 对话
3. 配置允许的用户
4. 扫描 QR 码配对（手机端：设置 → 链接设备 → 扫码）

**环境变量**（自动写入）：
```
WHATSAPP_MODE=bot                        # bot / self-chat
WHATSAPP_ENABLED=true
WHATSAPP_ALLOWED_USERS=+1234567890       # 手机号白名单
WHATSAPP_HOME_CHANNEL=+1234567890        # 通知投递号码
```

**依赖**：Node.js + npm（Bridge 自动安装依赖）

**会话文件**：`~/.hermes/whatsapp/session/creds.json`

**消息长度限制**：4096 字符

---

## Signal

**连接方式**：signal-cli HTTP daemon + SSE 事件流

**前置条件**：需要先安装并运行 signal-cli daemon。

**安装 signal-cli**：
- Linux：从 [GitHub Releases](https://github.com/AsamK/signal-cli/releases) 下载
- macOS：`brew install signal-cli`
- Docker：`bbernhard/signal-cli-rest-api`

**链接账号**：
```bash
signal-cli link -n "HermesAgent"
# 输出 signal:// URI → 在 Signal 手机端添加链接设备
```

**启动 daemon**：
```bash
signal-cli --account +YOURNUMBER daemon --http 127.0.0.1:8080
```

**必需环境变量**：
```
SIGNAL_HTTP_URL=http://127.0.0.1:8080
SIGNAL_ACCOUNT=+15551234567
```

**可选环境变量**：
```
SIGNAL_ALLOWED_USERS=+1234567890,uuid1    # 手机号或 UUID
SIGNAL_GROUP_ALLOWED_USERS=group_id1,*    # 群组白名单，* 为全部
```

**依赖**：signal-cli 可执行文件、`httpx`

**消息长度限制**：8000 字符

---

## iMessage（BlueBubbles）

**连接方式**：Webhook（BlueBubbles 推送到本地 HTTP 服务器）

**前置条件**：需要一台运行 BlueBubbles Server 的 macOS 设备。

**安装 BlueBubbles**：
1. 从 [bluebubbles.app](https://bluebubbles.app/) 下载并安装
2. 完成设置向导，登录 Apple ID
3. 在 Settings → API 中获取 Server URL 和 Password

**必需环境变量**：
```
BLUEBUBBLES_SERVER_URL=http://192.168.1.10:1234
BLUEBUBBLES_PASSWORD=your_password
```

**可选环境变量**：
```
BLUEBUBBLES_ALLOWED_USERS=+1234567890,user@icloud.com
BLUEBUBBLES_HOME_CHANNEL=+1234567890
BLUEBUBBLES_WEBHOOK_HOST=127.0.0.1
BLUEBUBBLES_WEBHOOK_PORT=8645
BLUEBUBBLES_WEBHOOK_PATH=/bluebubbles-webhook
```

**要求**：macOS + BlueBubbles Server 24/7 运行、Hermes 和 Mac 在同一网络（或 SSH 隧道）

**消息长度限制**：4000 字符

---

## 访问控制（所有平台通用）

三种模式（在 `~/.hermes/.env` 中配置）：

| 模式 | 配置 | 说明 |
|------|------|------|
| 开放访问 | `GATEWAY_ALLOW_ALL_USERS=true` | 任何人都能与 bot 对话 |
| 用户白名单 | `<PLATFORM>_ALLOWED_USERS=id1,id2` | 只允许指定用户 |
| DM 配对（默认） | 无需配置 | 新用户收到配对码，管理员审批 |

DM 配对审批命令：
```bash
hermes pairing approve <platform> <pairing_code>
```

---

## 启动 Gateway

```bash
hermes gateway run
```

## 参考

完整平台配置逻辑在 `hermes_cli/gateway.py`，搜索 `_PLATFORMS` 查看所有平台定义。各平台适配器实现在 `gateway/platforms/` 目录。
