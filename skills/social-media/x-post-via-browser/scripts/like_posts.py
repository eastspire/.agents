#!/usr/bin/env python3
"""Like the posts on the open page that are worth liking.

Liking is the one engagement that cannot go wrong in the way the others do:
there is no text to truncate, no link to break, and a like is not a claim
anyone has to hold you to. It also needs no text input, which is why it keeps
working while replying does not.

The target is read from the page as it is at that moment, never from a file
written by an earlier scroll — the timeline replaces posts continuously, so a
saved id names something that is no longer there. Posts already liked are
skipped, and the button state after the click is what gets recorded.

  python3 like_posts.py 9240 [count]
"""
from __future__ import annotations

import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cdp as C                                          # noqa: E402

ME = "eastspire_sheng"

# A like is worth making when the post is about the same work: languages an
# agent writes, agent tooling, context and token cost, inference, compilers.
# The list is intentionally narrow — a like is cheap but it is still a signal
# about what this account reads.
AI_WORDS = (
    "rust", "cargo", "wasm", "webassembly", "compile", "compiler", "macro",
    "agent", "llm", "token", "context window", "prompt", "mcp", "tool call",
    "inference", "model serving", "code review", "refactor", "debugging",
    "programming", "developer", "type system", "static typing",
    "编程", "模型", "编译", "工具", "宏", "上下文", "智能体", "推理", "代码",
)

READ = """(() => {
  const out = [];
  const seen = new Set();
  for (const a of document.querySelectorAll('article')) {
    const own = [...a.querySelectorAll("a[href*='/status/']")]
      .find(x => x.getAttribute('href').split('/').pop()
                && !/\\/(analytics|photo|video|retweets|likes)/.test(
                      x.getAttribute('href')));
    if (!own) continue;
    const sid = own.getAttribute('href').split('/').pop();
    if (seen.has(sid)) continue;
    seen.add(sid);
    const who = a.querySelector("a[href^='/']");
    const box = a.querySelector('[data-testid="tweetText"]');
    const like = a.querySelector('[data-testid="like"]')
              || a.querySelector('[data-testid="unlike"]');
    out.push({sid: sid,
              who: who ? who.getAttribute('href').split('/').pop() : '?',
              text: box ? box.innerText.replace(/\\s+/g, ' ').trim() : '',
              like: like ? like.dataset.testid : null});
  }
  return JSON.stringify(out);
})()"""

LIKE = """(() => {
  for (const a of document.querySelectorAll('article')) {
    const own = [...a.querySelectorAll("a[href*='/status/']")]
      .find(x => x.getAttribute('href').split('/').pop() === SID
                && !/\\/(analytics|photo|video|retweets|likes)/.test(
                      x.getAttribute('href')));
    if (!own) continue;
    const btn = a.querySelector('[data-testid="like"]')
             || a.querySelector('[data-testid="unlike"]');
    if (!btn) return 'NO_LIKE_BUTTON';
    const was = btn.dataset.testid;
    if (was === 'unlike') return 'ALREADY_LIKED';
    btn.click();
    return 'CLICKED';
  }
  return 'TARGET NOT ON PAGE';
})()"""

STATE = """(() => {
  for (const a of document.querySelectorAll('article')) {
    const own = [...a.querySelectorAll("a[href*='/status/']")]
      .find(x => x.getAttribute('href').split('/').pop() === SID
                && !/\\/(analytics|photo|video|retweets|likes)/.test(
                      x.getAttribute('href')));
    if (!own) continue;
    const btn = a.querySelector('[data-testid="like"]')
             || a.querySelector('[data-testid="unlike"]');
    return JSON.stringify({state: btn ? btn.dataset.testid : 'gone'});
  }
  return JSON.stringify({state: 'target gone'});
})()"""


def js(c, tpl, sid=""):
    r = c.js(tpl.replace("SID", json.dumps(sid)), wait=25, retries=5)
    if isinstance(r, str):
        try:
            return json.loads(r)
        except ValueError:
            return {"_raw": r[:120]}
    return r


def main() -> int:
    port = int(sys.argv[1])
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else 5
    C.set_port(port)
    tabs = [t for t in C.tabs("page") if "x.com" in t.get("url", "")]
    if not tabs:
        print("no x.com tab", flush=True)
        return 1
    c = C.Cdp(tabs[0]["webSocketDebuggerUrl"])

    raw = c.js(READ, wait=30, retries=5)
    rows = json.loads(raw) if isinstance(raw, str) else raw
    if not isinstance(rows, list):
        print("could not read the page:", str(rows)[:120], flush=True)
        c.close()
        return 1
    picks = [r for r in rows
             if r.get("who") != ME and r.get("text")
             and any(w in r["text"].lower() for w in AI_WORDS)]
    print("%d posts on the page, %d worth liking" % (len(rows), len(picks)),
          flush=True)

    done = 0
    for row in picks:
        if done >= limit:
            break
        sid = row["sid"]
        res = js(c, LIKE, sid)
        if res.get("_raw") != "CLICKED":
            print(f"  {sid} @{row['who']}: {res.get('_raw') or res}",
                  flush=True)
            continue
        time.sleep(2.5)
        after = js(c, STATE, sid)
        liked = after.get("state") == "unlike"
        print(f"  {'LIKED' if liked else 'NOT CONFIRMED'} {sid} "
              f"@{row['who']} — {row['text'][:90]}", flush=True)
        if liked:
            done += 1

    print(f"\n{done} liked", flush=True)
    c.close()
    return 0 if done else 1


if __name__ == "__main__":
    sys.exit(main())
