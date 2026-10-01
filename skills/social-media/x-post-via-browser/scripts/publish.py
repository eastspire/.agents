#!/usr/bin/env python3
"""Post to X over CDP alone, typing into the editor that is actually focused.

THE ROOT CAUSE of every earlier failure, found by probing with a marker
string and reading back all editable nodes:

  the page has TWO nodes with `data-testid="tweetTextarea_0"`. One carries
  the typed text and has `class="notranslate public-DraftEditor-content"`; the
  other is an empty duplicate. `document.querySelector` returns whichever
  comes first in document order, which is not stable between renders — so
  writes landed in one node and reads came from the other. That is why
  set_value appeared to work and then vanished, why `len` jumped to 194 or 0
  at random, and why clicking posted one stray character.

  The fix is to stop guessing: focus the editor with a real mouse click, then
  address `document.activeElement`. If the focused element is not the Draft
  editor, refuse.

Typing is per character through Input.insertText with newlines as a real
Return key, because a multi-line insertText writes 0 and a single multi-line
one reaches Draft as a single stale value. Every character is a real input
event, so Draft builds its own EditorState — which is what X submits.

  python3 publish.py 9237 --post 2 --go
  python3 publish.py 9237 --list
"""
import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cdp as C  # noqa: E402

# The copy to publish. Override with X_COPY=/path/to.json; the file beside
# this script is the default so the skill is self-contained.
COPY = os.environ.get("X_COPY") or os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "x_copy_example.json")
DRAFT_CLS = "public-DraftEditor-content"

# Does the focused composer hold a real link entity? A URL sitting in the
# editor as plain text is NOT a link: X will render it unclickable and it will
# not carry a card. urls_ok once passed on plain text that merely CONTAINED
# the URL, which is how a post went out with no link at all.
LINK_PRESENT = """(() => {
  const e = document.activeElement;
  if (!e || e.className.indexOf('public-DraftEditor-content') < 0)
    return 'NOT_EDITOR';
  const links = [...e.querySelectorAll('a[href]')]
    .map(a => (a.textContent || '').trim()).filter(Boolean);
  return links.length ? JSON.stringify({links: links}) : 'NO_LINK';
})()"""


def jd(v):
    try:
        return json.loads(v) if isinstance(v, str) else v
    except ValueError:
        return {"raw": str(v)[:200]}


IS_ACTIVE = """(() => {
  const a = document.activeElement;
  if (!a || a.getAttribute('data-testid') !== 'tweetTextarea_0') {
    return JSON.stringify({ok: false, why: 'active is not the editor',
      active: a ? a.tagName + '/' + a.getAttribute('data-testid') : 'none'});
  }
  const b = document.querySelector('button[data-testid="tweetButton"]');
  // A URL is rendered as an <a>, so it never appears in textContent. Walk the
  // tree and put each link's href back where the link sits, otherwise the
  // compare is missing every URL in the post.
  const read = (root) => {
    let out = '';
    for (const n of root.childNodes) {
      if (n.nodeType === 3) { out += n.nodeValue; continue; }
      if (n.nodeType !== 1) continue;
      if (n.tagName === 'A') {
        out += (n.textContent || n.getAttribute('href') || '');
      } else {
        out += read(n);
      }
    }
    return out;
  };
  return JSON.stringify({ok: true, len: a.textContent.length,
    text: read(a), raw: a.textContent,
    enabled: !!(b && !b.disabled)});
})()"""

EDITORS = """(() => {
  return JSON.stringify([...document.querySelectorAll(
    '[data-testid="tweetTextarea_0"]')].map(n => {
      const r = n.getBoundingClientRect();
      return {len: n.textContent.length, h: Math.round(r.height),
        w: Math.round(r.width),
        x: Math.round(r.left + r.width / 2),
        y: Math.round(r.top + r.height / 2),
        draft: n.className.indexOf('%s') >= 0,
        active: document.activeElement === n};
    }));
})()""" % DRAFT_CLS


def editors(c):
    return jd(c.js(EDITORS, wait=25, retries=6))


def focus_editor(c, tries=12):
    """Put DOM focus on the real Draft editor, without the mouse.

    Earlier this dispatched a real mouse click at the editor's coordinates,
    which moved the user's pointer. The editor accepts Input.insertText as soon
    as it is the document's active element, so el.focus() is enough. The node
    is still identified by measurement (the Draft class and the taller box),
    because the page carries a duplicate `tweetTextarea_0` and picking the
    wrong one is what made writes vanish.
    """
    for _ in range(tries):
        ok = c.js("""(() => {
          const all = [...document.querySelectorAll(
            '[data-testid="tweetTextarea_0"]')];
          if (!all.length) return false;
          const a = document.activeElement;
          const n = (a && a.getAttribute('data-testid') === 'tweetTextarea_0')
            ? a
            : (all.find(e => e.className.indexOf('%s') >= 0
                             && e.getBoundingClientRect().height > 24)
               || maxByHeight(all));
          n.focus();
          const blocks = [...n.children].filter(b => b.nodeType === 1);
          const r = document.createRange();
          r.selectNodeContents(blocks[blocks.length - 1] || n);
          r.collapse(false);
          const s = window.getSelection();
          s.removeAllRanges(); s.addRange(r);
          return document.activeElement === n;
        })()""" % DRAFT_CLS, wait=25, retries=6)
        time.sleep(0.5)
        st = jd(c.js(IS_ACTIVE, wait=20, retries=4))
        if st.get("ok"):
            return st
        time.sleep(0.5)
    return jd(c.js(IS_ACTIVE, wait=20, retries=4))


def maxByHeight(nodes):
    return sorted(nodes, key=lambda e: e.getBoundingClientRect().height)[-1]


BACKSPACE = [
    {"type": "rawKeyDown", "modifiers": 0, "key": "Backspace",
     "code": "Backspace", "windowsVirtualKeyCode": 8,
     "nativeVirtualKeyCode": 8},
    {"type": "keyUp", "modifiers": 0, "key": "Backspace",
     "code": "Backspace", "windowsVirtualKeyCode": 8,
     "nativeVirtualKeyCode": 8},
]


CURSOR = {"x": 0, "y": 0}


class DraftReplaced(Exception):
    """The composer was refilled from the server-side draft mid-typing."""

    def __init__(self, at, expect=0):
        super().__init__(
            f"draft replaced at char {at} (had {expect} characters)")
        self.at = at
        self.expect = expect


def refocus(c):
    """Restore DOM focus WITHOUT touching the mouse or OS focus.

    The earlier version dispatched a synthetic mouse click at remembered
    coordinates, which moved the user's pointer and stole the window — the
    user objected to that. el.focus() plus a selection restore is enough for
    Input.insertText to land, and it touches neither the mouse nor the OS
    focus (Page.bringToFront is deliberately not called anywhere here).
    """
    c.js("""(() => {
      const all = [...document.querySelectorAll(
        '[data-testid="tweetTextarea_0"]')];
      const a = document.activeElement;
      const n = (a && a.getAttribute('data-testid') === 'tweetTextarea_0')
        ? a
        : (all.find(e => e.className.indexOf('%s') >= 0
                         && e.getBoundingClientRect().height > 24)
           || all[0]);
      if (!n) return false;
      n.focus();
      const blocks = [...n.children].filter(b => b.nodeType === 1);
      const last = blocks[blocks.length - 1] || n;
      const r = document.createRange();
      r.selectNodeContents(last); r.collapse(false);
      const s = window.getSelection();
      s.removeAllRanges(); s.addRange(r);
      return true;
    })()""" % DRAFT_CLS, wait=20, retries=5)
    time.sleep(0.4)


def caret_to_end(c):
    """Put the caret at the end of the last block of the live editor."""
    c.js("""(() => {
      const all = [...document.querySelectorAll(
        '[data-testid="tweetTextarea_0"]')];
      const a = document.activeElement;
      const n = (a && a.getAttribute('data-testid') === 'tweetTextarea_0')
        ? a
        : (all.find(e => e.className.indexOf('%s') >= 0
                         && e.getBoundingClientRect().height > 24)
           || all[0]);
      n.focus();
      const blocks = [...n.children].filter(b => b.nodeType === 1);
      const last = blocks[blocks.length - 1] || n;
      const r = document.createRange();
      r.selectNodeContents(last); r.collapse(false);
      const s = window.getSelection();
      s.removeAllRanges(); s.addRange(r);
      return true;
    })()""" % DRAFT_CLS, wait=20, retries=5)


def click_post(c):
    return c.js("""(() => {
      const b = document.querySelector('button[data-testid="tweetButton"]');
      if (!b) return 'NO_BUTTON';
      if (b.disabled) return 'DISABLED';
      b.click(); return 'CLICKED';
    })()""", wait=20, retries=4)


def main():
    port = int(sys.argv[1])
    if "--list" in sys.argv:
        C.set_port(port)
        for t in C.tabs():
            if t["type"] == "page":
                print(t["id"][:8], t.get("url", "")[:70], flush=True)
        return

    idx = int(sys.argv[sys.argv.index("--post") + 1]) \
        if "--post" in sys.argv else 0
    go = "--go" in sys.argv
    # The flat copy: paragraph breaks are unreachable in this composer (after
    # insertParagraph the caret orphans and no further character lands, measured
    # across many runs), so each post is typed as a single line.
    text = json.load(open(COPY))[idx]
    # A long post keeps its paragraph breaks: X accepts them and the text is
    # unreadable without them. The whole string goes in one insertText, so the
    # earlier "newlines make X submit" problem does not apply.

    C.set_port(port)
    # Reuse the ONE x.com tab. If it is not on the composer, navigate it there
    # rather than opening another tab.
    pages = [x for x in C.tabs() if x["type"] == "page"
             and "x.com" in x.get("url", "")]
    if not pages:
        print("no x.com tab open — open one first (one_tab.py)", flush=True)
        return
    tab = pages[0]
    c = C.Cdp(tab["webSocketDebuggerUrl"])
    # No navigation and no reload anywhere in this script: the user has to
    # confirm each page load, so the composer is opened the way a person opens
    # it — by clicking the compose control already on screen.
    st = focus_editor(c)
    if not st.get("ok"):
        opened = c.js("""(() => {
          const btn = [...document.querySelectorAll(
            '[data-testid="SideNav_NewTweetButton"], '
            + 'a[href*="/compose/post"], [data-testid="appTabBarPostBtn"]')]
            .filter(e => e.offsetParent !== null)[0];
          if (!btn) return 'NO_COMPOSE_CONTROL';
          btn.click(); return 'CLICKED_COMPOSE';
        })()""", wait=25, retries=5)
        time.sleep(7)
        st = focus_editor(c)
        print(f"  opened composer: {opened}", flush=True)
    print("FOCUS", json.dumps(st, ensure_ascii=False)[:160], flush=True)
    if not st.get("ok"):
        print("no composer on this page and no compose control to click — "
              "open the composer yourself, nothing was reloaded", flush=True)
        c.close()
        return
    # The composer is NOT cleared. Clearing raises Chrome's unsaved-changes
    # dialog, which blocks every later step; the flow below reads what is there
    # and only types into an empty box.

    # X rewrites a link's href to a t.co shortener, so the URL cannot be
    # compared literally from either side. Strip URLs from both and check the
    # link count separately, so a dropped or duplicated link is still caught.
    flat = lambda s: "".join((s or "").split())
    nourl = lambda s: re.sub(r"https?://\S+", "\x00", s or "")

    def canon(s):
        """Source and editor text reduced to a comparable form.

        Whitespace is dropped everywhere, and so is the space X itself removes
        at a Latin/CJK boundary as you type ("AI 时代" -> "AI时代"). The
        character count is compared separately against the raw source length,
        so relaxing the spacing here cannot hide a dropped character.
        """
        # The space before a URL is part of the URL as X consumes it: the
        # composition takes " https://…" and the body is left holding the
        # leading "h". Without this, the editor reads back "…h\x00" against a
        # source of "…\x00" and an otherwise perfect post is rejected.
        s = re.sub(r"[ \t]+(?=https?://)", " ", s or "")
        s = flat(nourl(s))
        return re.sub(r"(?<=[A-Za-z0-9]) (?=[\u4e00-\u9fff])"
                      r"|(?<=[\u4e00-\u9fff]) (?=[A-Za-z0-9])", "", s)
    ok = False
    def type_pass(c, body):
        """Put one post into the composer.

        Measured: a whole single line lands in one Input.insertText and in no
        time (600 characters, 0.0s); character-by-character was only needed to
        get around newlines, and an X Premium long post has none — X expands
        past 280 characters into a thread on its own. A URL is different: X
        turns it into a link entity mid-stream and drops the rest, so the
        link is composed in one piece with imeSetComposition.
        """
        # Split so the whitespace BEFORE a URL goes in with the URL. Leaving it
        # in the body made the editor read back "…edition。h\x00" — X committed
        # the composition but the URL's own first character stayed in the body,
        # so a correct post was rejected. Feeding " https://…" as one unit puts
        # the space inside the link where it belongs.
        parts = re.split(r"([ \t]*(?=https://))|(https://\S+)", body)
        for part in [x for seg in parts for x in (seg if isinstance(seg, tuple)
                                                  else (seg,)) if x]:
            if part.lstrip().startswith("https://"):
                caret_to_end(c)
                time.sleep(0.4)
                # A URL is the only thing that needs an IME composition, and an
                # open composition is what makes Chrome claim the page holds
                # unsaved changes. Set it and commit it back to back, and end
                # the whole interaction with an explicit close so no composition
                # is ever left open.
                # Set the composition and let X linkify it. Committing it with
                # insertText(same text) is what stopped the link from forming:
                # the committed string arrived already formed and X had nothing
                # to linkify, leaving plain text with a stray leading "h".
                c.send("Input.imeSetComposition", text=part,
                       selectionStart=len(part), selectionEnd=len(part),
                       wait=25, retries=5)
                time.sleep(1.6)
                linked = c.js(LINK_PRESENT, wait=25, retries=4)
                if not linked:
                    # No entity yet: seal the composition by committing the same
                    # text through the IME's own commit path, which is a
                    # key event rather than an insertText.
                    c.send("Input.imeSetComposition", text="",
                           selectionStart=0, selectionEnd=0,
                           wait=20, retries=3)
                    time.sleep(1.2)
                c.close_composition("")
                continue
            c.send("Input.insertText", text=part, wait=30, retries=5)
            time.sleep(1.2)
            st = jd(c.js(IS_ACTIVE, wait=25, retries=4))
            if not st.get("ok"):
                refocus(c)
            elif st.get("len", 0) == 0:
                raise DraftReplaced(0, len(part))

    def read_links(c):
        """The visible text of every link entity in the composer."""
        r = jd(c.js(LINK_PRESENT, wait=25, retries=4))
        if isinstance(r, str):
            return [] if r in ("NOT_EDITOR", "NO_LINK") else [r]
        if isinstance(r, dict):
            return r.get("links", [])
        return []

    def read(c):
        return jd(c.js(IS_ACTIVE, wait=25, retries=6))

    def reopen(c):
        """Make the composer usable again WITHOUT reloading the page.

        Navigating with location.assign would reload the page, which the user
        has to confirm in their UI, so it is not done. Everything here works on
        the page as it stands: re-focus the editor, and if X has replaced the
        composer with the home timeline, click the compose affordance that is
        already on screen.
        """
        if focus_editor(c).get("ok"):
            return True
        # The inline composer on /home is the same editor and posts a top-level
        # tweet when its own button is used.
        opened = c.js("""(() => {
          const all = [...document.querySelectorAll(
            '[data-testid="tweetTextarea_0"]')];
          if (all.length) return 'ALREADY_THERE';
          const btn = [...document.querySelectorAll(
            '[data-testid="SideNav_NewTweetButton"], '
            + 'a[href*="/compose/post"], [data-testid="appTabBarPostBtn"]')]
            .filter(e => e.offsetParent !== null)[0];
          if (!btn) return 'NO_COMPOSE_CONTROL';
          btn.click();
          return 'CLICKED_COMPOSE';
        })()""", wait=25, retries=5)
        time.sleep(6)
        st = focus_editor(c)
        print(f"  reopen: {opened} -> focus={st.get('ok')}", flush=True)
        return bool(st.get("ok"))

    # Nothing here may empty the composer. Clearing it, reloading the page and
    # navigating all raise Chrome's unsaved-changes dialog, and that modal then
    # blocks every later step until the user dismisses it — measured, not
    # assumed. So the flow is: read what the box holds, type only if it is
    # empty, and if it already holds exactly this post, post it as it stands.
    st = focus_editor(c)
    if not st.get("ok"):
        opened = c.js("""(() => {
          const btn = [...document.querySelectorAll(
            '[data-testid="SideNav_NewTweetButton"], '
            + 'a[href*="/compose/post"], [data-testid="appTabBarPostBtn"]')]
            .filter(e => e.offsetParent !== null)[0];
          if (!btn) return 'NO_COMPOSE_CONTROL';
          btn.click(); return 'CLICKED_COMPOSE';
        })()""", wait=25, retries=5)
        time.sleep(7)
        st = focus_editor(c)
        print(f"  opened composer: {opened} focus={st.get('ok')}", flush=True)
    if not st.get("ok"):
        print("no composer on this page and nothing was reloaded — open the "
              "composer yourself, then re-run", flush=True)
        c.close()
        return

    have = read(c)
    got = have.get("text", "") or ""
    want_urls = re.findall(r"https?://\S+", text)
    fg_now, ft = canon(got), canon(text)
    already = (fg_now == ft) and all(u in got for u in want_urls)

    if already:
        print(f"  the composer already holds this exact post "
              f"({have.get('len')} chars) — posting it as it stands",
              flush=True)
    elif have.get("len", 0) == 0:
        print(f"  composer is empty — typing {len(text)} characters in one "
              f"insertText", flush=True)
        try:
            type_pass(c, text)
        except DraftReplaced as exc:
            print(f"  {exc} — the composer was refilled, stopping without "
                  f"clearing it", flush=True)
            c.close_composition("")
            c.close()
            return
        time.sleep(1.5)
    else:
        print(f"  the composer holds {have.get('len')} characters that are NOT "
              f"this post. It is left untouched: clearing it would raise the "
              f"unsaved-changes dialog.", flush=True)
        print(f"    has: {got[:70]!r}", flush=True)
        print(f"    want: {text[:70]!r}", flush=True)
        c.close_composition("")
        c.close()
        return

    c.close_composition("")      # never leave an open composition behind
    st = read(c)
    got = st.get("text", "") or ""

    # A link is rendered as an <a>, so it is not in textContent; read()
    # substitutes the link's own visible text, which is the URL as posted. A
    # truncated link therefore shows up as a short visible string, which is
    # exactly the defect that made earlier posts get deleted.
    # A URL must be a real <a> entity, not text that happens to contain the
    # string. read() matches the URL inside plain text, so checking the text
    # alone passed a post whose link was never a link.
    urls_ok = all(u in got for u in want_urls)
    if want_urls:
        linked = read_links(c)
        urls_ok = urls_ok and all(
            any(u in l for l in linked) for u in want_urls)
    fg, ft = canon(got), canon(text)
    # X only ever removes a SPACE while typing (at a Latin/CJK boundary); it
    # never drops or invents a non-space character. So the two texts must be
    # identical once spaces are removed, and the editor must not be LONGER than
    # the source. This cannot be fooled by a dropped character and cannot be
    # tripped by the space X legitimately removes.
    # The compare is the gate. The raw editor length is NOT: X's Draft editor
    # keeps hidden text nodes of its own, so it reads 860 against an 859
    # character source even when the visible text matches exactly (fg == ft with
    # no differing index). Requiring len(fg) <= len(ft) instead keeps the
    # "nothing was invented" guarantee without failing on that hidden node.
    ok = (fg == ft) and urls_ok and len(fg) <= len(ft)

    print(f"  LEN {st.get('len')} want {len(text)} enabled {st.get('enabled')} "
          f"match={ok} urls={len(want_urls)} urls_ok={urls_ok}", flush=True)
    if not ok:
        fi = next((x for x in range(min(len(fg), len(ft)))
                   if fg[x] != ft[x]), None)
        print(f"  MISMATCH — first difference at {fi} "
              f"(editor {len(fg)} / source {len(ft)}), not clicking", flush=True)
        if fi is not None:
            lo, hi = max(0, fi - 20), fi + 20
            print(f"    got : {fg[lo:hi]!r}", flush=True)
            print(f"    want: {ft[lo:hi]!r}", flush=True)
        c.close()
        return

    if not st.get("enabled"):
        print("  text is right but the button is disabled — waiting", flush=True)
        for _ in range(8):
            time.sleep(4)
            st = read(c)
            if st.get("enabled"):
                break
    ok = ok and st.get("enabled")

    if not ok:
        print("not clicking: the button never enabled", flush=True)
        c.close()
        return

    c.close_composition("")      # never leave an open composition behind
    if not ok:
        print("not clicking: text never matched", flush=True)
        c.close()
        return

    if not go:
        print("(dry run — not clicking)", flush=True)
        c.close()
        return
    print("CLICK", click_post(c), flush=True)
    c.close_composition("")      # the post button may have opened one
    c.close()


def show_copy():
    """Print the copy with lengths. Touches nothing."""
    posts = json.load(open(COPY))
    print(f"{COPY}\n{len(posts)} posts\n")
    for i, s in enumerate(posts):
        urls = re.findall(r"https?://\S+", s)
        print(f"  [{i}] {len(s):5} chars, {len(urls)} url(s)")
        print(f"      {s[:60]!r}...")
    return 0


def show_tabs(port):
    """Print the open X tabs. Touches nothing."""
    C.set_port(port)
    for t in C.tabs():
        if t.get("type") == "page" and "x.com" in t.get("url", ""):
            print(f"  {t['id'][:8]} {t['url'][:60]}")
    return 0


if __name__ == "__main__":
    if "--show" in sys.argv:
        sys.exit(show_copy())
    if "--tabs" in sys.argv:
        port = next((a for a in sys.argv if a.isdigit()), "9240")
        sys.exit(show_tabs(int(port)))
    main()
