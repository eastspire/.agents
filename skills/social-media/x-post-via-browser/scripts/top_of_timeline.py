#!/usr/bin/env python3
"""Read the timeline's newest entries with their ids and times, in order.

Six posts verified, then the last three `match=True` + `CLICKED` and never
appeared. Two candidates: a rate limit, or the composer silently refusing. Read
the top of the timeline with timestamps so a gap is visible, and look for X's
rate-limit notice text in the page.

  python3 top_of_timeline.py 9237
"""
import json
import sys
import time

sys.path.insert(0, "/Users/sqs/.hermes/cache/scratch")
import cdpx as C  # noqa: E402


def jd(v):
    try:
        return json.loads(v) if isinstance(v, str) else v
    except ValueError:
        return {"raw": str(v)[:200]}


def main():
    C.set_port(int(sys.argv[1]))
    tab = next((t for t in C.tabs()
                if t["type"] == "page"
                and "x.com/eastspire_sheng" in t.get("url", "")), None)
    if tab is None:
        tab = C.new_tab("https://x.com/eastspire_sheng")
        time.sleep(14)
    c = C.Cdp(tab["webSocketDebuggerUrl"])
    c.send("Page.bringToFront", wait=25, retries=6)
    c.settle(ceiling=300)
    for _ in range(3):
        c.js("window.scrollTo(0, 0)", wait=20, retries=4)
        time.sleep(2.5)

    raw = c.js("""(() => {
      const arts = [...document.querySelectorAll(
        'article[data-testid="tweet"]')];
      const rows = arts.map(a => {
        const u = (a.querySelector('a[href*="/status/"]')||{}).href || '';
        const t = a.querySelector('[data-testid="tweetText"]');
        const tm = a.querySelector('time');
        const links = [...a.querySelectorAll(
          'a[href*="t.co"], a[href*="github.com"]')]
          .map(x => (x.innerText || '').trim()).filter(Boolean);
        return {id: (u.match(/status\\/(\\d+)/)||[])[1] || '',
                when: tm ? tm.getAttribute('datetime') : '',
                text: t ? t.textContent.slice(0, 64) : '(none)',
                links: links};
      });
      const body = document.body.innerText;
      return JSON.stringify({rows: rows,
        rateLimited: /rate limit|速率限制|频率限制|try again later/i
          .test(body)});
    })()""", wait=30, retries=6)
    st = jd(raw)
    print(f"rateLimited: {st.get('rateLimited')}\n", flush=True)
    for r in st.get("rows", []):
        print(f"  {r['when'][:19]}  id={r['id'] or '(none)'}", flush=True)
        print(f"      {r['text']}", flush=True)
        if r["links"]:
            print(f"      links={r['links']}", flush=True)
    c.close()


if __name__ == "__main__":
    main()
