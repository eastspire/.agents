#!/usr/bin/env python3
"""Read the open X tab and report which account's posts are on it.

The publisher's verification step prints whatever articles are visible, and a
reply context or a For You feed lists other people's posts alongside your own.
Reporting the first status id it finds is then meaningless — that id can be
someone else's post entirely. This separates by author so a claim about "the
new post" can only be made about a post by the expected account.

  python3 who_am_i_posting_as.py 9240
"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.expanduser(
    "~/.agents/skills/social-media/x-post-via-browser/scripts"))
import cdp as C                                          # noqa: E402

EXPECTED = "eastspire_sheng"

ARTICLES = r"""(() => {
  const out = [];
  for (const a of document.querySelectorAll('article')) {
    const st = a.querySelector("a[href*='/status/']");
    if (!st) continue;
    const who = a.querySelector("a[href^='/']");
    out.push({
      sid: st.href.split('/').pop(),
      who: who ? who.getAttribute('href').split('/').pop() : '?',
      when: (a.innerText || '').slice(0, 60).split('\n').join(' | ')
    });
  }
  return JSON.stringify(out.slice(0, 8));
})()"""


def main() -> int:
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 9240
    C.set_port(port)
    tabs = [t for t in C.tabs()
            if t.get("type") == "page" and "x.com" in t.get("url", "")]
    if not tabs:
        print("no x.com tab")
        return 1
    c = C.Cdp(tabs[0]["webSocketDebuggerUrl"])
    print("url   :", tabs[0]["url"])
    print("title :", c.js("document.title", wait=20, retries=4))
    print("logged:", c.js(
        """(() => {
          const a = [...document.querySelectorAll("a[href^='/']")]
            .map(x => x.getAttribute('href'))
            .find(h => /^\\/[A-Za-z0-9_]{2,15}$/.test(h) && h !== '/home' &&
                      h !== '/explore' && h !== '/notifications' &&
                      h !== '/search' && h !== '/messages' &&
                      h !== '/settings' && h !== '/i' && h !== '/about');
          return a || 'unknown';
        })()""", wait=25, retries=4))
    rows = json.loads(c.js(ARTICLES, wait=30, retries=5))
    mine = [r for r in rows if r["who"] == EXPECTED]
    print(f"\n{len(mine)} of the {len(rows)} visible articles are "
          f"@{EXPECTED}")
    for r in rows:
        tag = "MINE" if r["who"] == EXPECTED else "    "
        print(f"  {tag} {r['sid']}  @{r['who']}  {r['when']}")
    try:
        c.close()
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
