#!/usr/bin/env python3
"""Post one long post to X through the composer that is already open.

The shortest path that works. Every step was measured, and everything else was
tried and measured to break the text:

  focus the real Draft editor -> one insertText for the whole body ->
  compare -> click the post button -> verify with verify_post.py

These do NOT work, and none of them is here:

  * imeSetComposition for the URL — strands the URL's first character in the
    body, so the editor reads "…edition。h" against a source of "…"
  * a paste for the URL (commands=["paste"]) — X folds the separator into the
    host and the sentence comes back as "https://\ncrates.io"
  * clearing the composer — leaves 4–24 characters, and a later reload raises
    Chrome's unsaved-changes dialog, which blocks every step after it
  * looking for button[data-testid="tweetButton"] — the inline composer mounts
    tweetButtonInline and often mounts no tweetButton at all

  python3 publish.py 9240 --post 0 --go
  python3 publish.py 9240 --show          # the copy, touches nothing
  python3 publish.py 9240 --tabs          # the open X tab, touches nothing
"""
from __future__ import annotations

import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cdp as C                                          # noqa: E402

COPY = os.environ.get("X_COPY") or os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "x_copy_example.json")
DRAFT_CLS = "public-DraftEditor-content"

# Two nodes carry data-testid="tweetTextarea_0" and only one is the real
# editor; the other is an empty decoy. Document order is not stable between
# renders, so the taller visible one is the one that holds the text.
EDITOR = """(() => {
  const all = [...document.querySelectorAll('[data-testid="tweetTextarea_0"]')]
    .filter(n => n.className && n.className.indexOf(%s) >= 0
                 && n.offsetParent !== null);
  if (!all.length) return {ok: false, why: 'no visible Draft editor'};
  const e = all.sort((a, b) => b.getBoundingClientRect().height
                             - a.getBoundingClientRect().height)[0];
  const a = document.activeElement;
  let text = '';
  for (const n of e.childNodes) text += n.textContent || '';
  return {
    ok: true, focused: a === e || (a && e.contains(a)),
    len: text.length, text: text,
    buttons: [...document.querySelectorAll('button[data-testid]')]
      .filter(b => /^tweetButton/.test(b.dataset.testid))
      .map(b => b.dataset.testid + (b.disabled ? ':dis' : ':en'))
  };
})()""" % json.dumps(DRAFT_CLS)

# Either button posts. X mounts tweetButtonInline for the inline composer and
# does not reliably mount tweetButton, so a lookup that requires tweetButton
# finds nothing on a composer whose button is right there and enabled — which
# reads as "the button never enabled" and silently drops the post.
BUTTON = """(() => {
  const all = [...document.querySelectorAll('button[data-testid]')]
    .filter(b => /^tweetButton/.test(b.dataset.testid));
  const b = all.find(x => x.dataset.testid === 'tweetButton')
         || all.find(x => !x.disabled);
  if (!b) return {clicked: null, why: all.length ? 'disabled' : 'no post button',
                  present: all.map(x => x.dataset.testid)};
  if (b.disabled) return {clicked: null, why: 'disabled',
                          present: all.map(x => x.dataset.testid)};
  b.click();
  return {clicked: b.dataset.testid,
          present: all.map(x => x.dataset.testid)};
})()"""

STRIP = lambda s: re.sub(r"https?://\S+", "\x00", s or "")
FLAT = lambda s: "".join((s or "").split())


def canon(s: str) -> str:
    """Source and editor text reduced to a comparable form.

    Whitespace goes everywhere: X removes a space at a Latin/CJK boundary
    while typing ("AI 时代" -> "AI时代") and the Draft editor keeps hidden
    nodes of its own, so a raw length compare reads 860 against an 859
    character source on a post that is character-for-character correct. What
    is left is the non-space characters, and those must match exactly — a
    dropped or mangled character cannot hide behind a space.
    """
    return FLAT(STRIP(s))


def jd(v):
    """js() returns a value or a distinguishable error marker; unwrap both."""
    if isinstance(v, dict) and any(k in v for k in
                                   ("__js_error", "__socket_error",
                                    "__timeout", "__cdp_error")):
        return {}
    return v if isinstance(v, dict) else {}


def read(c):
    return jd(c.js(EDITOR, wait=25, retries=5))


def focus_editor(c, tries=12):
    """Address the composer's Draft editor, opening it by clicking if needed.

    No navigation and no reload: every page load makes the user confirm it in
    their UI, so the composer is opened the way a person opens it — by
    clicking the compose control already on screen.
    """
    for _ in range(tries):
        st = read(c)
        if st.get("ok"):
            c.js("""(() => {
              const all = [...document.querySelectorAll(
                '[data-testid="tweetTextarea_0"]')]
                .filter(n => n.className && n.className.indexOf(%s) >= 0
                             && n.offsetParent !== null);
              if (!all.length) return false;
              all.sort((a, b) => b.getBoundingClientRect().height
                                - a.getBoundingClientRect().height)[0].focus();
              return true;
            })()""" % json.dumps(DRAFT_CLS), wait=20, retries=3)
            time.sleep(0.4)
            st = read(c)
            if st.get("focused"):
                return st
        time.sleep(0.6)

    opened = c.js("""(() => {
      const btn = [...document.querySelectorAll(
        '[data-testid="SideNav_NewTweetButton"], a[href*="/compose/post"], '
        + '[data-testid="appTabBarPostBtn"]')]
        .filter(e => e.offsetParent !== null)[0];
      if (!btn) return 'NO_COMPOSE_CONTROL';
      btn.click(); return 'CLICKED_COMPOSE';
    })()""", wait=25, retries=5)
    time.sleep(7)
    for _ in range(tries):
        st = read(c)
        if st.get("ok"):
            return st
        time.sleep(0.6)
    print(f"  no composer on this page and {opened} — open the composer "
          f"yourself; nothing was reloaded", flush=True)
    return st


def stray_linkifiers(text: str, urls) -> list:
    """Dotted tokens X will turn into links even though they are not URLs.

    X linkifies any dotted token, not just one it recognises as a URL, and the
    span it replaces then reads back as a line break — a bare "crates.io" in
    the body split a sentence in two and shipped twice before it was refused
    here. So the check is on the COPY, before a character is typed.
    """
    hosts = {u.split("://", 1)[1].split("/", 1)[0] for u in urls}
    return [w for w in re.findall(r"[A-Za-z0-9_-]+\.[A-Za-z]{2,}", text)
            if w not in hosts]


def main() -> int:
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 9240
    if "--show" in sys.argv:
        posts = json.load(open(COPY))
        print(f"{COPY}\n{len(posts)} posts\n")
        for i, s in enumerate(posts):
            n_urls = len(re.findall(r"https?://\S+", s))
            print(f"  [{i}] {len(s):5} chars, {n_urls} url(s)")
            print(f"      {s[:60]!r}...")
        return 0
    if "--tabs" in sys.argv:
        C.set_port(port)
        for t in C.tabs("page"):
            if "x.com" in t.get("url", ""):
                print(f"  {t['id'][:8]} {t['url'][:70]}")
        return 0

    idx = int(sys.argv[sys.argv.index("--post") + 1]) \
        if "--post" in sys.argv else 0
    go = "--go" in sys.argv
    text = json.load(open(COPY))[idx]
    urls = re.findall(r"https?://\S+", text)

    bad = stray_linkifiers(text, urls)
    if bad:
        print(f"REFUSING: {bad} will be linkified by X and read back broken. "
              f"Rewrite the copy without the dotted token.", flush=True)
        return 1

    C.set_port(port)
    pages = [t for t in C.tabs("page") if "x.com" in t.get("url", "")]
    if not pages:
        print("no x.com tab open — open one first", flush=True)
        return 1
    c = C.Cdp(pages[0]["webSocketDebuggerUrl"])

    st = focus_editor(c)
    if not st.get("ok"):
        c.close()
        return 1
    print(f"FOCUS {st.get('len')} chars, buttons {st.get('buttons')}",
          flush=True)

    have = st.get("text", "") or ""
    if have:
        # The composer is never cleared. Read what is there and act on it.
        if canon(have) == canon(text):
            print(f"  already holds this exact post ({st.get('len')} chars) — "
                  f"posting it as it stands", flush=True)
        else:
            print(f"  holds {st.get('len')} characters that are NOT this post. "
                  f"Left untouched — clearing raises the unsaved-changes "
                  f"dialog.", flush=True)
            print(f"    has: {have[:70]!r}", flush=True)
            print(f"    want: {text[:70]!r}", flush=True)
            c.close()
            return 1
    else:
        print(f"  empty — inserting {len(text)} characters in one insertText",
              flush=True)
        # One insertText for the WHOLE body, URL included. 2500 characters
        # land in no time. The URL is not special to the editor; splitting it
        # out to compose or paste it is what broke the text, five ways.
        c.send("Input.insertText", text=text, wait=40, retries=6)
        time.sleep(2.0)

    c.close_composition("")     # never leave an open composition behind
    st = read(c)
    got = st.get("text", "") or ""
    fg, ft = canon(got), canon(text)
    # The compare is the gate. The raw editor length is NOT: X's Draft editor
    # keeps hidden text nodes of its own, so it reads 860 against an 859
    # character source even when the visible text matches exactly. Requiring
    # len(fg) <= len(ft) keeps the "nothing was invented" guarantee without
    # failing on that hidden node.
    ok = fg == ft and len(fg) <= len(ft)
    # The URL must survive as text. It is NOT required to be an <a> here: this
    # composer never renders a link entity however the text arrives (ten input
    # methods measured, zero <a> nodes) and X resolves the URL server-side.
    # canon() strips whitespace, so also require a space before each URL — X
    # folded a newline into the host and read back "https://\ncrates.io", the
    # characters were all present, and the text compare passed anyway.
    sep_ok = all(m.start() == 0 or got[m.start() - 1] == " "
                 for u in urls for m in re.finditer(re.escape(u), got))
    urls_ok = all(u in got for u in urls) and sep_ok

    print(f"  LEN {st.get('len')} want {len(text)} match={ok} "
          f"urls={len(urls)} urls_ok={urls_ok}", flush=True)
    if not ok or not urls_ok:
        if not ok:
            i = next((x for x in range(min(len(fg), len(ft)))
                      if fg[x] != ft[x]), None)
            print(f"  MISMATCH — first difference at {i}, not clicking",
                  flush=True)
            if i is not None:
                lo = max(0, i - 20)
                print(f"    got : {fg[lo:i + 20]!r}", flush=True)
                print(f"    want: {ft[lo:i + 20]!r}", flush=True)
        else:
            print(f"  the URL did not survive intact, not clicking", flush=True)
        c.close()
        return 1

    if not go:
        print("(dry run — not clicking)", flush=True)
        c.close()
        return 0

    res = jd(c.js(BUTTON, wait=25, retries=5))
    for _ in range(8):
        if res.get("clicked"):
            break
        time.sleep(4)
        res = jd(c.js(BUTTON, wait=25, retries=4))
    c.close_composition("")     # the button may have opened one
    print(f"CLICK {res.get('clicked') or res.get('why')} "
          f"(buttons {res.get('present')})", flush=True)
    c.close()
    return 0 if res.get("clicked") else 1


if __name__ == "__main__":
    sys.exit(main())
