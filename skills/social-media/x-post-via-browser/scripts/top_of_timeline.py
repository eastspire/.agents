#!/usr/bin/env python3
"""Read the newest entries on the profile timeline, with ids and times.

This is the verification step: `CLICKED` is not evidence that a post happened,
so every post is confirmed here.

It REUSES the x.com tab that is already open. It never opens one, never
navigates, and never reloads — a page load makes the user confirm it in their
UI, and a verification step that breaks the rules it verifies is worse than no
verification at all. If no x.com tab is open, it says so and stops.

  python3 top_of_timeline.py 9240
"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cdp as C                                          # noqa: E402


def jd(v):
    """Parse a CDP evaluate result, which is JSON text or a plain value."""
    try:
        return json.loads(v) if isinstance(v, str) else v
    except ValueError:
        return {"raw": str(v)[:200]}


READ = """(() => {
  const arts = [...document.querySelectorAll(
    'article[data-testid="tweet"]')];
  const rows = arts.map(a => {
    const u = (a.querySelector('a[href*="/status/"]')||{}).href || '';
    const t = a.querySelector('[data-testid="tweetText"]');
    const tm = a.querySelector('time');
    // A URL is an <a>, so it is not in tweetText's textContent; read the
    // link's own visible text. X rewrites href to t.co, so href is useless.
    const links = [...a.querySelectorAll('a[href*="t.co"], a[href*="github"]')]
      .map(x => (x.innerText || '').trim()).filter(Boolean);
    return {id: (u.match(/status\\/(\\d+)/)||[])[1] || '',
            when: tm ? tm.getAttribute('datetime') : '',
            text: t ? t.textContent.slice(0, 80) : '(none)',
            links: links};
  });
  return JSON.stringify({
    href: location.href,
    rows: rows,
    rateLimited: /rate limit|速率限制|频率限制|try again later/i
      .test(document.body.innerText)});
})()"""


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 9240
    C.set_port(port)

    x_tabs = [t for t in C.tabs()
              if t.get("type") == "page" and "x.com" in t.get("url", "")]
    if not x_tabs:
        print("no open x.com tab. Open the profile once; this script will "
              "not open it for you, because that would be a page load.",
              flush=True)
        return
    tab = x_tabs[0]
    c = C.Cdp(tab["webSocketDebuggerUrl"])
    # No Page.bringToFront: the user's pointer and OS focus are never taken.
    time.sleep(2)
    for _ in range(3):
        c.js("window.scrollTo(0, 0)", wait=20, retries=4)
        time.sleep(2.5)

    st = jd(c.js(READ, wait=30, retries=6))
    if not isinstance(st, dict) or "rows" not in st:
        print("could not read the page:", st, flush=True)
        c.close()
        return

    # A 403 page has a tiny body and no articles, and would otherwise look
    # like an empty timeline — which reads as "nothing was posted".
    if not st["rows"] and "x.com" not in st.get("href", ""):
        print("this is not an x.com page:", st.get("href"), flush=True)
        c.close()
        return

    print(f"rateLimited: {st['rateLimited']}\n", flush=True)
    for r in st["rows"]:
        print(f"  {r['when'][:19]}  id={r['id'] or '(none)'}", flush=True)
        print(f"      {r['text']}", flush=True)
        for link in r["links"]:
            print(f"      link: {link}", flush=True)
    c.close()


if __name__ == "__main__":
    main()
