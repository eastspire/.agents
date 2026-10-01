#!/usr/bin/env python3
"""Reply to the post under the cursor, through the reply box already on screen.

Replying needs no navigation: every article on the page carries a reply control,
clicking it opens a composer in place, and the same insertText path that
publishes a post publishes a reply. So this opens nothing and loads nothing —
it finds the target post on the open page, clicks its reply control, types,
compares and clicks send.

That is why the commit gate lets this file exist at the same time as
no-page-load: the reply is opened by a click on the page, not by a navigation.

Each reply is verified afterwards on the page: the target post's article must
gain a child article from the expected account carrying the same text prefix.
A click on send is not evidence, exactly as a click on post is not.

  python3 post_reply.py 9240 <status_id> <reply_text> [lang]
"""
from __future__ import annotations

import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cdp as C                                          # noqa: E402

DRAFT_CLS = "public-DraftEditor-content"
ME = "eastspire_sheng"

# Click the reply control on the article that OWNS this status id. Matching on
# any status link picks up a quoted post or a reply context instead, which is
# how a reply once targeted a stranger's post.
OPEN_REPLY = """(() => {
  for (const a of document.querySelectorAll('article')) {
    const own = [...a.querySelectorAll("a[href*='/status/']")]
      .find(x => x.getAttribute('href').split('/').pop() === SID
                && !/\\/(analytics|photo|video|retweets|likes)/.test(
                      x.getAttribute('href')));
    if (!own) continue;
    const btn = a.querySelector('[data-testid="reply"]');
    if (!btn) return 'NO_REPLY_BUTTON';
    btn.click();
    return 'CLICKED';
  }
  return 'TARGET NOT ON PAGE';
})()"""

COMPOSER = """(() => {
  const all = [...document.querySelectorAll('[data-testid="tweetTextarea_0"]')]
    .filter(n => n.className && n.className.indexOf(%s) >= 0
                 && n.offsetParent !== null);
  if (!all.length) return {ok: false, why: 'no visible editor'};
  // A reply composer sits inside a dialog; the one under it is the one the
  // reply belongs to. The tallest is the reply box on a timeline.
  const e = all.sort((a, b) => b.getBoundingClientRect().height
                             - a.getBoundingClientRect().height)[0];
  e.focus();
  let text = '';
  for (const n of e.childNodes) text += n.textContent || '';
  return {ok: true, len: text.length, text: text,
          buttons: [...document.querySelectorAll('button[data-testid]')]
            .filter(b => /^tweetButton/.test(b.dataset.testid))
            .map(b => b.dataset.testid + (b.disabled ? ':dis' : ':en'))};
})()""" % json.dumps(DRAFT_CLS)

SEND = """(() => {
  const all = [...document.querySelectorAll('button[data-testid]')]
    .filter(b => /^tweetButton/.test(b.dataset.testid) && !b.disabled);
  const b = all.find(x => x.dataset.testid === 'tweetButton') || all[0];
  if (!b) return {sent: null, why: 'no enabled send button'};
  b.click();
  return {sent: b.dataset.testid};
})()"""

# The reply is verified where it appears: nested under the target article, by
# this account, with the same text prefix. Nothing else counts.
VERIFIED = """(() => {
  for (const a of document.querySelectorAll('article')) {
    const own = [...a.querySelectorAll("a[href*='/status/']")]
      .find(x => x.getAttribute('href').split('/').pop() === SID
                && !/\\/(analytics|photo|video|retweets|likes)/.test(
                      x.getAttribute('href')));
    if (!own) continue;
    for (const child of a.querySelectorAll('article')) {
      const who = child.querySelector("a[href^='/']");
      if (!who || who.getAttribute('href').split('/').pop() !== WHO) continue;
      const box = child.querySelector('[data-testid="tweetText"]');
      return JSON.stringify({
        found: true,
        text: box ? box.innerText.replace(/\\s+/g, ' ').trim() : '',
        sid: ([...child.querySelectorAll("a[href*='/status/']")][0]
               || {}).href
      });
    }
    return JSON.stringify({found: false, why: 'no reply from ' + WHO});
  }
  return JSON.stringify({found: false, why: 'target gone'});
})()"""

STRIP = lambda s: re.sub(r"https?://\S+", "\x00", s or "")
canon = lambda s: "".join(STRIP(s).split())


def js(c, tpl, sid=None):
    """Evaluate a template, always handing back a dict.

    cdp.js returns whatever the expression produced, or an error marker string.
    Callers here ask structured questions and then read .get() on the answer, so
    a bare string would raise instead of reporting — the same class of silent
    false conclusion the rest of this skill exists to avoid.
    """
    r = c.js(tpl.replace("SID", json.dumps(sid or ""))
              .replace("WHO", json.dumps(ME)), wait=25, retries=5)
    if isinstance(r, dict):
        return {k: v for k, v in r.items()
                if not k.startswith("__")}
    return {"_raw": str(r)[:160]}


def main() -> int:
    port = int(sys.argv[1])
    sid = sys.argv[2]
    text = open(sys.argv[3], encoding="utf-8").read() if os.path.exists(
        sys.argv[3]) else sys.argv[3]
    C.set_port(port)
    tabs = [t for t in C.tabs("page") if "x.com" in t.get("url", "")]
    if not tabs:
        print("no x.com tab", flush=True)
        return 1
    c = C.Cdp(tabs[0]["webSocketDebuggerUrl"])

    # X linkifies any dotted token and the replaced span reads back as a line
    # break, which splits the sentence. Refuse before typing, not after.
    stray = [w for w in re.findall(r"[A-Za-z0-9_-]+\.[A-Za-z]{2,}", text)]
    if stray:
        print(f"REFUSING: {stray} will be linkified and read back broken",
              flush=True)
        c.close()
        return 1

    opened = js(c, OPEN_REPLY, sid)
    print("open reply:", opened, flush=True)
    # Stop before typing anything if the target post is not on this page. A
    # missing reply control once let the flow fall through to the main
    # composer, type 643 characters into it and click its send button.
    if opened.get("_raw") != "CLICKED":
        print("NOT SENDING — target post is not on the open page", flush=True)
        c.close()
        return 1
    time.sleep(3)
    st = {}
    for _ in range(10):
        st = js(c, COMPOSER)
        if st.get("ok"):
            break
        time.sleep(1.5)
    if not st.get("ok"):
        print("reply composer did not appear:", st, flush=True)
        c.close()
        return 1
    if st.get("len", 0) == 0:
        c.send("Input.insertText", text=text, wait=40, retries=6)
        time.sleep(2.0)
    c.close_composition("")
    time.sleep(1.0)

    st = js(c, COMPOSER)
    ok = canon(st.get("text", "")) == canon(text)
    print(f"  LEN {st.get('len')} want {len(text)} match={ok} "
          f"buttons {st.get('buttons')}", flush=True)
    if not ok:
        print("  text does not match, not sending", flush=True)
        c.close()
        return 1

    res = js(c, SEND)
    for _ in range(8):
        if res.get("sent"):
            break
        time.sleep(3)
        res = js(c, SEND)
    c.close_composition("")
    print("SEND", res, flush=True)
    if not res.get("sent"):
        c.close()
        return 1

    time.sleep(6)
    for _ in range(6):
        raw = c.js(VERIFIED.replace("SID", json.dumps(sid))
                   .replace("WHO", json.dumps(ME)), wait=30, retries=5)
        v = json.loads(raw) if isinstance(raw, str) else raw
        if v.get("found"):
            same = canon(v.get("text", "")).startswith(canon(text)[:60])
            print(f"VERIFIED reply by @{ME}: {v.get('sid','')} "
                  f"prefix_ok={same}", flush=True)
            c.close()
            return 0 if same else 1
        time.sleep(5)
    print("NOT VERIFIED — the reply did not appear under the target", flush=True)
    c.close()
    return 1


if __name__ == "__main__":
    sys.exit(main())
