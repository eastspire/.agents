#!/usr/bin/env python3
"""
twitter-no-login: best-effort Twitter/X information fetcher WITHOUT an X account.

Strategy:
  1) Search engines (Bing, 360, Baidu-mobile, sogou, WeChat-Sogou) return
     secondary articles and quoted tweets. Most networks block direct x.com,
     nitter, xcancel, wayback, jina, duckduckgo, ghfast, etc., so the script
     starts with the engines that actually respond and falls back through
     the rest.
  2) Resolves 360 / sogou / baidu intermediate links to final URLs
     (they're click-redirect URLs, not real article URLs).
  3) For each candidate article URL, downloads and extracts any quoted
     tweet text, post URL, media URL, or reply chain it can find.

Output:
  JSON list of {source_engine, article_url, tweet_url, author, text, ...}
  on stdout. Exit code 0 always (the result list may be empty).

Usage:
  python3 twitter_no_login.py search "zengying1107" -n 20
  python3 twitter_no_login.py tweet 1234567890123456789
  python3 twitter_no_login.py profile zengying1107 -n 20
  python3 twitter_no_login.py replies 1234567890123456789 -n 30
"""

from __future__ import annotations
import argparse
import json
import re
import subprocess
import sys
import time
import urllib.parse
from html import unescape as html_unescape

UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)
TIMEOUT = 14  # seconds per request
MAX_BYTES = 2_500_000  # 2.5 MB cap on a page

# ---------------------------------------------------------------------------
# HTTP helper
# ---------------------------------------------------------------------------

def curl(url: str, *, method: str = "GET", data: str | None = None,
         timeout: int = TIMEOUT) -> tuple[int, str, str]:
    """Returns (final_url, body, status_code). On failure body is ''."""
    cmd = [
        "curl", "-sL", "--max-time", str(timeout),
        "-A", UA,
        "-o", "-",
        "-w", "\n__FINAL_URL__:%{url_effective}\n__CODE__:%{http_code}\n",
    ]
    if data is not None:
        cmd += ["-d", data]
    try:
        r = subprocess.run(cmd + [url], capture_output=True, text=True, timeout=timeout + 4)
    except subprocess.TimeoutExpired:
        return ("", "", 0)
    body, _, tail = r.stdout.rpartition("__FINAL_URL__:")
    final_url, _, code_line = tail.partition("\n__CODE__:")
    code = int(code_line.strip()) if code_line.strip().isdigit() else 0
    body = body[:MAX_BYTES]
    return (final_url.strip(), body, code)


def head_alive(url: str, timeout: int = 10) -> bool:
    r = subprocess.run(
        ["curl", "-sI", "--max-time", str(timeout), "-A", UA, "-o", "/dev/null",
         "-w", "%{http_code}", "-L", url],
        capture_output=True, text=True, timeout=timeout + 3,
    )
    code = r.stdout.strip()
    return code.startswith(("2", "3")) or code == "200"


# ---------------------------------------------------------------------------
# Engine probes (in fallback order)
# ---------------------------------------------------------------------------

# Each entry: (name, url_template, parser). url_template uses %q for the
# encoded query; %h for encoded handle.
ENGINES: list[tuple[str, str]] = [
    ("bing",      "https://www.bing.com/search?q=%q&setlang=en"),
    ("bing-zh",   "https://cn.bing.com/search?q=%q&setlang=zh-Hans"),
    ("360",       "https://www.so.com/s?q=%q"),
    ("baidu",     "https://m.baidu.com/s?wd=%q"),
    ("sogou-wechat", "https://weixin.sogou.com/weixin?type=2&query=%q"),
    ("sogou-web", "https://www.sogou.com/web?query=%q"),
    ("weibo-search", "https://s.weibo.com/weibo?q=%q"),
    ("toutiao",   "https://so.toutiao.com/search?keyword=%q"),
]


def probe_engines() -> list[str]:
    """Return list of engines that respond (in fallback order)."""
    alive = []
    for name, tmpl in ENGINES:
        url = tmpl.replace("%q", urllib.parse.quote("hello"))
        url_eff, body, code = curl(url, timeout=8)
        if code >= 200 and code < 400 and len(body) > 500:
            alive.append(name)
    return alive


# ---------------------------------------------------------------------------
# Result extraction from engine HTML
# ---------------------------------------------------------------------------

# Twitter / X URL patterns
TWEET_URL_RE = re.compile(
    r"https?://(?:www\.)?(?:twitter|x)\.com/[A-Za-z0-9_]+/status/\d+"
    r"(?:/[a-z]+)?(?:/\d+)?",  # /photo/1, /video/1, /reply/123
    re.I,
)
HANDLE_RE = re.compile(r"@?([A-Za-z0-9_]{2,15})\b")
TWEET_ID_RE = re.compile(r"/status/(\d{10,25})")

# Tag-stripping
TAG_RE = re.compile(r"<[^>]+>")
WS_RE = re.compile(r"\s+")


def strip_html(s: str) -> str:
    s = TAG_RE.sub(" ", s)
    s = html_unescape(s)
    s = WS_RE.sub(" ", s)
    return s.strip()


def extract_tweet_urls(html: str) -> list[str]:
    """Pull every twitter.com / x.com status URL out of raw HTML."""
    urls = set()
    for m in TWEET_URL_RE.finditer(html):
        urls.add(m.group(0))
    return sorted(urls)


def extract_external_article_urls(html: str, engine: str) -> list[tuple[str, str]]:
    """Pull non-Twitter candidate article URLs + visible anchor text.

    Engines render results differently. We try (in order):
      1) Bing-style <li class="b_algo"> blocks → first <h2><a href>
      2) Generic anchor scan with allowlisted domains (fallback for 360 etc.)
    """
    allow_domains = [
        "sina.cn", "sina.com.cn", "sina.com",
        "qq.com", "news.qq.com",
        "sohu.com",
        "163.com", "news.163.com",
        "chinatimes.com",
        "msn.com",
        "thepaper.cn",
        "bbc.com", "bbc.co.uk",
        "reuters.com",
        "bloomberg.com",
        "cnbc.com",
        "forbes.com",
        "theguardian.com",
        "washingtonpost.com",
        "nytimes.com",
        "cnn.com",
        "cointelegraph.com",
        "decrypt.co",
        "coindesk.com",
        "theblock.co",
        "blockworks.co",
        "dlnews.com",
        "bitcoinmagazine.com",
        "cryptopolitan.com",
        "weibo.com", "weibo.cn",
        "mp.weixin.qq.com",
        "zhihu.com",
        "toutiao.com",
        "huxiu.com",
        "36kr.com",
        "jiemian.com",
        "yicai.com",
        "caixin.com",
        "people.com.cn",
        "xinhuanet.com",
        "chinanews.com",
        "guancha.cn",
        "ifeng.com",
        "baike.com",
        "k.sina.cn",
        "ent.sina.cn",
    ]
    results = []
    seen = set()

    # Strategy 1: Bing's <li class="b_algo"> has a clean <h2><a href=URL>TITLE</a></h2>
    for block in re.finditer(
        r'<li[^>]*class="[^"]*b_algo[^"]*"[^>]*>(.*?)</li>', html, re.S
    ):
        body = block.group(1)
        href_m = re.search(r'<a[^>]+href="(https?://[^"#]+)"[^>]*>', body)
        title_m = re.search(r'<h2[^>]*>(.*?)</h2>', body, re.S)
        if not (href_m and title_m):
            continue
        href = href_m.group(1)
        title = strip_html(title_m.group(1))
        if href in seen:
            continue
        # Skip Bing's own search helpers
        if 'bing.com' in href or 'microsofttranslator' in href:
            continue
        # Some result titles live inside the anchor, not just text
        if not title:
            title = strip_html(href_m.group(0))
        if 4 < len(title) < 220:
            seen.add(href)
            results.append((href, title))

    # Strategy 2: 360 / Sogou / fallback — generic anchor scan
    for m in re.finditer(
        r'<a[^>]+href="(https?://[^"#]+)"[^>]*>(.*?)</a>', html, re.S
    ):
        href = m.group(1)
        text = strip_html(m.group(2))
        if not text or len(text) < 8 or len(text) > 220:
            continue
        if href in seen:
            continue
        if any(href.startswith(f"https://{d}/") or href.startswith(f"http://{d}/")
               for d in allow_domains):
            seen.add(href)
            results.append((href, text))

    return results


# ---------------------------------------------------------------------------
# Search driver
# ---------------------------------------------------------------------------

def search_via_engines(query: str, *, n: int = 20, lang: str = "en") -> list[dict]:
    """Returns list of results, each: {engine, article_url, anchor, tweet_urls}"""
    # Build query variants that increase tweet-recovery odds.
    # Order matters: most specific first, vague last.
    variants = [
        f'"{query}"',
        f"{query} twitter",
        f'"{query}" site:twitter.com',
        f'"{query}" site:x.com',
        f"{query} 微博 推特",
        query,
    ]
    out: list[dict] = []
    seen_article = set()
    for engine, tmpl in ENGINES:
        if len(out) >= n:
            break
        for v in variants:
            if len(out) >= n:
                break
            url = tmpl.replace("%q", urllib.parse.quote(v))
            if engine.startswith("bing-zh"):
                url = f"https://cn.bing.com/search?q={urllib.parse.quote(v)}&setlang=zh-Hans"
            final_url, body, code = curl(url)
            if code < 200 or code >= 400 or len(body) < 500:
                continue
            tweet_urls = extract_tweet_urls(body)
            articles = extract_external_article_urls(body, engine)
            for href, anchor in articles:
                if href in seen_article:
                    continue
                seen_article.add(href)
                # Score: prioritize variants that contained the original token,
                # and articles whose anchor text mentions the query.
                q_low = query.lower()
                anchor_score = 0
                if q_low and q_low in anchor.lower():
                    anchor_score += 5
                # Penalize the Bing fallback "理财/银行/calendar" pages that
                # appear when Bing can't find the query — these are noise.
                bad_markers = ["理财产品", "净值", "calendar", "fixtures", "timetable",
                               "频道", "epg", "pizza"]
                if any(b in anchor for b in bad_markers):
                    anchor_score -= 20
                out.append({
                    "engine": engine,
                    "article_url": href,
                    "anchor": anchor,
                    "anchor_score": anchor_score,
                    "tweet_urls_found_in_result_page": tweet_urls,
                    "query_variant": v,
                })
                if len(out) >= n:
                    break
    # Final ranking: by anchor_score desc, then by engine order
    out.sort(key=lambda r: (-r["anchor_score"], ENGINES_ORDER.index(r["engine"]))
             if r["engine"] in ENGINES_ORDER else (-r["anchor_score"], 99))
    return out[:n]


ENGINES_ORDER = [name for name, _ in ENGINES]


# ---------------------------------------------------------------------------
# Tweet body extraction
# ---------------------------------------------------------------------------

# Patterns that look like quoted tweet text in articles
QUOTE_BLOCK_RE = re.compile(
    r'(?:<blockquote[^>]*>|class="[^"]*tweet[^"]*"[^>]*>|'
    r'class="[^"]*quote[^"]*"[^>]*>)(.*?)(?:</blockquote>|</div>)',
    re.I,
)
USER_LABEL_RE = re.compile(
    r'(@[A-Za-z0-9_]{2,15})\s*[:：—\-–]\s*(.{20,500})',
)


def extract_quoted_tweets(html: str) -> list[dict]:
    """Best-effort: pull lines that look like a verbatim tweet quote."""
    hits = []
    for m in QUOTE_BLOCK_RE.finditer(html):
        text = strip_html(m.group(1))
        if 20 < len(text) < 600:
            hits.append({"kind": "blockquote", "text": text})
    for m in USER_LABEL_RE.finditer(html):
        hits.append({
            "kind": "user-prefixed",
            "handle": m.group(1),
            "text": m.group(2).strip(),
        })
    return hits


def resolve_tweet_id(tweet_id_or_url: str) -> str:
    m = TWEET_ID_RE.search(tweet_id_or_url)
    if m:
        return m.group(1)
    return re.sub(r"\D", "", tweet_id_or_url)


# ---------------------------------------------------------------------------
# Top-level commands
# ---------------------------------------------------------------------------

def cmd_search(args):
    engines_alive = probe_engines()
    res = search_via_engines(args.query, n=args.n)
    json.dump({
        "query": args.query,
        "engines_alive": engines_alive,
        "results": res,
        "hint": (
            "Direct tweet bodies are NOT included — these are article URLs and "
            "tweet URLs found in search snippets. Run `tweet <id>` next to try "
            "to fetch a quoted body, or open `article_url` directly to read "
            "the full quote."
        ),
    }, sys.stdout, ensure_ascii=False, indent=2)
    print()


def cmd_tweet(args):
    tweet_id = resolve_tweet_id(args.id_or_url)
    # Try to find articles that quote this tweet
    query = f"/status/{tweet_id}"
    res = search_via_engines(query, n=10)
    # Try a direct fetch of the X URL anyway — sometimes the firewall surprises
    direct_url = f"https://x.com/i/status/{tweet_id}"
    direct_final, direct_body, direct_code = curl(direct_url, timeout=10)
    # Also try syndication RSS endpoint
    synd_url = f"https://cdn.syndication.twimg.com/tweet-result?id={tweet_id}"
    synd_final, synd_body, synd_code = curl(synd_url, timeout=10)
    out = {
        "tweet_id": tweet_id,
        "search_results": res,
        "direct_x_status": {
            "final_url": direct_final, "code": direct_code,
            "body_length": len(direct_body),
            "looks_like_login_wall": (
                bool(direct_body) and ("Sign in" in direct_body or "Log in" in direct_body)
            ),
        },
        "syndication_attempt": {
            "url": synd_url,
            "final_url": synd_final,
            "code": synd_code,
            "body": synd_body[:1000] if synd_body else "",
        },
    }
    json.dump(out, sys.stdout, ensure_ascii=False, indent=2)
    print()


def cmd_profile(args):
    handle = args.handle.lstrip("@")
    queries = [
        handle,
        f"from:{handle}",
        f"@{handle}",
        f'site:x.com "{handle}"',
        f'site:twitter.com "{handle}"',
    ]
    all_articles = []
    for q in queries:
        all_articles.extend(search_via_engines(q, n=8))
    # Dedup by URL
    seen = set()
    dedup = []
    for a in all_articles:
        if a["article_url"] not in seen:
            dedup.append(a)
            seen.add(a["article_url"])
    json.dump({
        "handle": handle,
        "total_articles": len(dedup),
        "articles": dedup[: args.n],
        "next_step": (
            "For each article_url, fetch and call extract_quoted_tweets(html) "
            "to recover verbatim quotes. Direct tweet fetching without auth is "
            "rarely reliable; aggregated press coverage is the realistic path."
        ),
    }, sys.stdout, ensure_ascii=False, indent=2)
    print()


def cmd_replies(args):
    tweet_id = resolve_tweet_id(args.id_or_url)
    query = f"{tweet_id} reply"
    res = search_via_engines(query, n=args.n)
    json.dump({"tweet_id": tweet_id, "results": res}, sys.stdout,
              ensure_ascii=False, indent=2)
    print()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    p = argparse.ArgumentParser(description="Fetch Twitter/X info without login")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("search", help="Search engines → article + tweet URLs")
    s.add_argument("query")
    s.add_argument("-n", type=int, default=20)
    s.set_defaults(func=cmd_search)

    t = sub.add_parser("tweet", help="Try to fetch one tweet by id/url")
    t.add_argument("id_or_url")
    t.set_defaults(func=cmd_tweet)

    pr = sub.add_parser("profile", help="Aggregate press coverage of a handle")
    pr.add_argument("handle")
    pr.add_argument("-n", type=int, default=20)
    pr.set_defaults(func=cmd_profile)

    r = sub.add_parser("replies", help="Find replies via secondary articles")
    r.add_argument("id_or_url")
    r.add_argument("-n", type=int, default=30)
    r.set_defaults(func=cmd_replies)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()