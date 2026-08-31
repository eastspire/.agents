---
name: twitter-no-login
description: 在**没有 X/Twitter 账号、无 OAuth、无 CDP 浏览器**的环境下,获取推特账号信息 / 单条推文 / profile / replies 的兜底方案。**触发词**:免登录抓推特、no-login twitter、anonymous tweet lookup、不登录拿推文、x.com fetch without auth、推特匿名抓取、推文搜索引擎、被墙环境拉推特、x.com 镜像、nitter 替代、xurl 替代品、cdn.syndication 抓取、推特数据采集。
when_to_use: 当用户需要 x.com / twitter.com 公开信息,但本机没 OAuth 没 CDP 浏览器(常见:服务器、沙箱、CI、出口被墙的网络),且不能要求用户去注册 X Developer 账号时。
---

# twitter-no-login — 免登录获取 X/Twitter 公开信息的兜底方案

## 这 skill 不做什么

- **不绕过 X 鉴权墙**——X v2 API 需要 OAuth,x.com 直链要求登录 cookie,这俩都不可行
- **不爬付费订阅 / 私密账号 / 关注列表**——公开数据是天花板
- **不保证拿到推文全文**——多数情况拿到的"二次描述"(媒体 quote)
- **不替代 `xurl` 或 web-access CDP**——有鉴权或能开浏览器时,那些更准,本 skill 是兜底

## 这 skill 提供什么

在没有 OAuth、没有浏览器远程调试、没有 x.com 网络出口的环境里,通过**搜索引擎 → 媒体二手 quote → 公开 syndication RSS** 三层 fallback,**让用户拿到推特账号 / 单条推文 / profile / replies 的可用信息**。

## When to Use

- 服务器 / 沙箱 / CI / 国内云出口环境,直接 `curl x.com` / `nitter.net` / `xcancel.com` / `r.jina.ai/x.com` 全部 timeout
- 不能让用户去 X Developer Portal 注册 app 走 OAuth
- 不能让用户在自己浏览器开 remote-debugging
- 任务只需要公开推文/账号的概要信息(不要求精确全文)
- **不要用于**:需要 100% 原文、实时性要求强(分钟级)、需要 DM / 私密账号 / 关注列表

## Quick Start

```bash
# 直接调脚本
python3 ~/.hermes/skills/twitter-no-login/scripts/twitter_no_login.py \
    search "曾颖 颖学" -n 8

python3 ~/.hermes/skills/twitter-no-login/scripts/twitter_no_login.py \
    profile zengying1107 -n 20

python3 ~/.hermes/skills/twitter-no-login/scripts/twitter_no_login.py \
    tweet 1234567890123456789

python3 ~/.hermes/skills/twitter-no-login/scripts/twitter_no_login.py \
    replies 1234567890123456789 -n 30
```

输出 JSON 到 stdout,字段:`engine / article_url / anchor / tweet_urls_found_in_result_page / query_variant / anchor_score`。

## 路径选择逻辑(Path-of-Least-Resistance)

**实测过的可达 / 不可达通道**(2026-08 在国内云环境验证):

| 通道 | 状态 | 说明 |
|---|---|---|
| Bing (`www.bing.com` / `cn.bing.com`) | ✅ 通 | 默认 fallback 引擎 |
| 360 search (`so.com`) | ✅ 通 | 链接经过中转,二次解析 |
| Baidu mobile (`m.baidu.com`) | ✅ 响应,但常被 captcha | 备选 |
| 头条搜索 (`so.toutiao.com`) | ✅ 通 | 中文结果较丰富 |
| 搜狗微信 (`weixin.sogou.com`) | ✅ 通 | 公众号文章 quote 推文 |
| 搜狗网页 (`www.sogou.com`) | ✅ 通 | 通用 |
| 微博搜索 (`s.weibo.com/weibo`) | ✅ 通 | 跨平台 quote(常含 twitter 截图) |
| **nitter.net / nitter.privacydev.net / nitter.poast.org** | ❌ timeout | 国内云防火墙屏蔽 |
| **xcancel.com** | ❌ timeout | 同上 |
| **r.jina.ai / jina 任何 prefix** | ❌ timeout | 同上 |
| **web.archive.org / Wayback Machine** | ❌ timeout | 同上 |
| **x.com / twitter.com / api.x.com** | ❌ 全部立即返回登录页 | 无 cookie 拿不到内容 |
| **cdn.syndication.twimg.com** | ❌ 大多 timeout / 403 | 偶尔通 |
| **ghfast.top / xcancel 任何反代** | ❌ 403 | Cloudflare 风控 |
| DuckDuckGo / Yandex / Startpage | ❌ captcha 或 timeout | 反爬 |
| Ecosia | ❌ 重定向到 Bing 首页 | 不可独立用 |

## How to Run (Through Hermes Tools)

把脚本放进 `~/.hermes/skills/twitter-no-login/scripts/`,通过 `terminal` 工具调用:

```python
terminal(
    command="python3 ~/.hermes/skills/twitter-no-login/scripts/twitter_no_login.py search '曾颖 颖学' -n 8",
    timeout=60,
)
```

JSON 输出直接给到后续 LLM 推理或 `write_file` 落盘。

## Procedure

### 步骤 1:探活引擎(可选)

`probe_engines()` 函数会并发测每个引擎可达性,输出 `engines_alive` 列表。**首次跑某个新环境时建议调用**,以确认出口白名单。

### 步骤 2:选择最可能出结果的 query 模板

按"信息密度从高到低"排序的 query 模板:

1. `"{handle}"` — 引号包裹精确 token,命中率最高
2. `{handle} twitter`
3. `"{handle}" site:twitter.com`
4. `"{handle}" site:x.com`
5. `{handle} 微博 推特`(中文 fallback)
6. `{handle}` — 裸 query(可能命中无关结果)

### 步骤 3:多引擎 fan-out + 锚文本打分

- 对每个 query 变体 × 每个活引擎组合,curl 一次
- 解析 `<li class="b_algo">`(Bing) 或通用 `<a href>` 提取
- **降权噪音**:命中"理财产品/净值/calendar/timetable/pizza"等 Bing 兜底词的结果 anchor_score -20
- **升权命中**:anchor 里出现 query 原文 → anchor_score +5
- 最终按 score desc 排序

### 步骤 4:二次抓取文章正文 quote

对排序后前 N 个 article_url 调 `extract_quoted_tweets(html)`(当前 CLI 没暴露,但可直接 import):

```python
import sys
sys.path.insert(0, "~/.hermes/skills/twitter-no-login/scripts")
from twitter_no_login import extract_quoted_tweets, curl

_, html, code = curl("https://ent.sina.cn/2026-08-28/...")
quotes = extract_quoted_tweets(html)
# quotes: [{kind: "blockquote", text: "..."}, {kind: "user-prefixed", handle: "@...", text: "..."}]
```

### 步骤 5:反推 tweet ID

如果文章 quote 里带了 `@handle: 文本` 或 `twitter.com/.../status/12345...` 这种行,用 `TWEET_ID_RE` 抽 ID,然后用 `cmd_tweet` 二次跑。

## Quick Reference

| 任务 | 命令 |
|---|---|
| 模糊搜 keyword | `python3 ... search "<keyword>" -n 20` |
| 找账号的所有公开 quote | `python3 ... profile <handle> -n 30` |
| 单条推文 | `python3 ... tweet <id\|url>` |
| 推文回复 | `python3 ... replies <id\|url> -n 30` |
| Probe 引擎可达性 | (脚本启动时自动跑,通过 `engines_alive` 字段输出) |
| 程序化 quote 抽取 | `from twitter_no_login import extract_quoted_tweets` |

## Pitfalls

1. **Bing 把未知 token 当拼写错误**——返回一堆字典/金融页 fallback。**必须用引号包裹 query**(脚本默认会加),否则 anchor_score 会被噪音主导
2. **360 链接是中转 URL**(`/link?m=...`),不是真实文章地址。需要再 follow 一次 302 才能拿到最终 URL — 当前脚本没自动 follow,后续可加(用 curl 的 `-L` 已自动 follow 大部分)
3. **百度 mobile 经常 captcha**——`<title>百度安全验证</title>`,跳过不要重试
4. **新浪等大站有 referer / UA 校验**——脚本的 UA 是 Chrome 124 Linux,实测够用,但偶尔需要补 `Referer: <原域名>` header
5. **TLS timeout 不要 retry**——直接 timeout 一般是防火墙级别,retry 只会浪费 ~14s/次
6. **脚本不解析 JS**——所有动态加载内容拿不到(SPA-style 媒体站)。若 article_url 拿到后页面是空,大概率是 SPA,需要切到 web-access CDP 路径
7. **tweet body 拿不到是常态**——大多数情况下你能拿到"X 发了关于 Y 的 quote",拿不到 Y 的全文。**不要假装拿到了**——read_file 然后让 LLM 基于 anchor/quote 总结
8. **profile 拿不到 timeline**——只能拿到"媒体引用过这个 handle 的文章"。一个完全没被媒体报道的账号,本 skill 拿不到任何东西
9. **真实出口环境先 probe 再用**——`probe_engines()` 第一次跑会做 8 次 curl,后续通过 `engines_alive` 字段已知哪些能通,可手工改 `ENGINES` 顺序跳过 timeout 引擎

## Verification

跑完搜索后,自检:

1. `engines_alive` 至少含 1 个引擎?✅
2. 返回的 `article_url` 域名不在 `bing.com / microsoft.com / so.com / baidu.com`(那是搜索引擎自己)?✅
3. 至少一条 `article_url` anchor 文本里出现 query 的关键词?✅
4. (可选)二次 curl 那个 URL 拿到正文,正文里 quote 推文内容含 `@handle`?✅
5. 没有命中 bad marker("理财产品/净值/calendar/pizza" 等 fallback)?✅

5 项全过 = 这次结果可用。

## 与其他 skill 的关系

- **`xurl`(social-media/xurl)**:首选,有 OAuth 时直接走,数据 100% 干净。本 skill 是 `xurl` 拿不到 auth 时的兜底
- **`web-access`(主域)**:有浏览器远程调试时,本 skill 完全可被 web-access CDP 替代。**当 web-access 不可用时,本 skill 是 fallback chain 的下一档**
- **搜索引擎 API(Bing Web Search / 360 / Baidu)**:本 skill 用的是直接 curl,而不是 API key。如果有 Bing Web Search API key,效果更好但本 skill 不需要

## Notes

- 脚本是 `scripts/twitter_no_login.py`,~370 行,单文件零依赖(只用 `subprocess` + `re` + `urllib`),Python 3.10+
- 上游 `xurl`(官方 CLI)若有,优先 `xurl search "from:HANDLE"` 而不是本 skill
- 当真实出口网络变化(防火墙白名单调整、新增 DNS 污染),重跑 `probe_engines()`,把 dead 引擎从 `ENGINES` 列表头部去掉可加速
- 二手 quote 是**最常见的成功路径**,不要追求"拿原始推文"——拿到"X 公开说 Y"已经足够大多数分析任务