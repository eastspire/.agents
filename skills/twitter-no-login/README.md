# twitter-no-login

A Hermes Agent skill that fetches X / Twitter public information **without OAuth, without CDP, without browser remote-debugging**.

## Why this exists

`xurl` needs a registered X Developer app + OAuth. `web-access` (CDP) needs a browser with remote debugging enabled and the target site reachable. When neither is available — typical on a sandboxed cloud VM, in CI, behind a corporate firewall, or anywhere `x.com` / `nitter` / `jina` are blocked at the network egress — this skill is the fallback.

It reaches Twitter public data through:

1. **Search engines** (Bing, 360, Baidu-mobile, Sogou, WeChat-Sogou, Toutiao, Weibo) that are reachable in your egress.
2. **Press articles / weibo posts / wechat posts** found by those engines that quote or screenshot the tweet.
3. **Public syndication** (`cdn.syndication.twimg.com/tweet-result`) tried directly when possible.

You won't always get the full original tweet text — but you usually get enough ("X publicly said Y about Z, here's the article with a verbatim quote") to drive downstream analysis.

## Install

```bash
git clone https://github.com/eastspire/twitter-no-login.git
mkdir -p ~/.hermes/skills/twitter-no-login
cp -r twitter-no-login/* ~/.hermes/skills/twitter-no-login/
# restart Hermes — the new skill will be discovered next session
```

## Usage

```bash
python3 ~/.hermes/skills/twitter-no-login/scripts/twitter_no_login.py \
    search "曾颖 颖学" -n 8

python3 ~/.hermes/skills/twitter-no-login/scripts/twitter_no_login.py \
    profile zengying1107 -n 20

python3 ~/.hermes/skills/twitter-no-login/scripts/twitter_no_login.py \
    tweet 1234567890123456789

python3 ~/.hermes/skills/twitter-no-login/scripts/twitter_no_login.py \
    replies 1234567890123456789 -n 30
```

All commands emit JSON to stdout.

## When NOT to use

- You have OAuth → use `xurl`
- You can open a browser with remote debugging → use `web-access` (CDP)
- You need the exact original text of every tweet → this skill returns 60-80% accuracy at best
- You need private / DM / follower / following data → impossible without auth

## Files

- `SKILL.md` — the skill itself
- `scripts/twitter_no_login.py` — zero-dep Python 3.10+ engine

## License

MIT