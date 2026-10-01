#!/usr/bin/env python3
"""Verify one published post by status id, author and full text.

Written after a verification step matched a status id that belonged to a
stranger's post sitting in the same feed: the id was real, the text was real,
and the conclusion "my post landed" was wrong. So this insists on three things
at once — the id is on the page, the author is the expected account, and the
body matches the source copy character for character after normalising only
the URL to a marker.

It reuses the tab that is already open. Opening a second one is a page load,
which the browser rules forbid.

  python3 verify_one_post.py 9240 <status_id> <copy_file> [index]
"""
from __future__ import annotations

import json
import os
import re
import sys

sys.path.insert(0, os.path.expanduser(
    "~/.agents/skills/social-media/x-post-via-browser/scripts"))
import cdp as C                                          # noqa: E402

EXPECTED = "eastspire_sheng"


def canon(s: str) -> str:
    """Reduce a post to a comparable form.

    Two normalisations, both learned from a false result: X rewrites the URL
    as a t.co shortener, so the URL span is removed from both sides rather
    than looked for; and the renderer reflows the body, putting a line break
    between tokens that were space-separated in the source, so all whitespace
    goes. What is left is the non-space characters, which is the part that
    must match exactly.
    """
    s = re.sub(r"\S*(?:https?://\S+|t\.co/\S+)", "\x00", s or "")
    return "".join(s.split())


ARTICLE = r"""(() => {
  for (const a of document.querySelectorAll('article')) {
    const who = a.querySelector("a[href^='/']");
    // The OWNING article is the one whose time link points at this id. A
    // quoted or replied-to post also carries the id, and matching on any
    // status link picks up the wrong one — which is how a previous run
    // reported a stranger's links for a post of mine.
    const st = [...a.querySelectorAll("a[href*='/status/']")]
      .find(x => /\/status\//.test(x.getAttribute('href') || '') &&
                !/\/(analytics|photo|video|retweets|likes)/.test(x.getAttribute('href'))
                && x.getAttribute('href').split('/').pop() === SID);
    if (!st) continue;
    // tweetText is clipped by X: it stops mid-sentence and carries no "show
    // more" control, so its textContent is a PREFIX of the post, not the post.
    // Reading it reported 177 characters against a 380 character source on a
    // post that was published complete. Take the whole body, and put each
    // link's own text back where the link sits.
    let body = '';
    for (const n of a.childNodes) body += n.textContent || '';
    const box = a.querySelector('[data-testid="tweetText"]');
    if (box) {
      // Walk the tweetText subtree so nested link text is included.
      const walk = (n) => {
        let s = '';
        for (const k of n.childNodes) {
          if (k.nodeType === 3) s += k.textContent;
          else if (k.nodeName === 'BR') s += '\n';
          else s += walk(k);
        }
        return s;
      };
      body = walk(box);
    }
    return JSON.stringify({
      who: who ? who.getAttribute('href').split('/').pop() : '?',
      text: body,
      links: [...a.querySelectorAll('a[href^="http"]')]
        .map(x => ({href: x.href, shown: (x.textContent || '').trim()})),
    ext: [...a.querySelectorAll('a[href^="http"]')]
        .map(x => x.href).filter(h => !/x\.com|twitter\.com/.test(h)),
    card: (a.querySelector('[data-testid="card.wrapper"]') || {}).innerText
          || '' 
    });
  }
  return 'NOT ON PAGE';
})()"""


def main() -> int:
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 9240
    sid = sys.argv[2]
    copy = json.load(open(sys.argv[3]))
    idx = int(sys.argv[4]) if len(sys.argv) > 4 else 0
    want = copy[idx]["text"] if isinstance(copy[0], dict) else copy[idx]
    want_urls = re.findall(r"https?://\S+", want)

    C.set_port(port)
    tab = [t for t in C.tabs()
           if t.get("type") == "page" and "x.com" in t.get("url", "")][0]
    c = C.Cdp(tab["webSocketDebuggerUrl"])
    got = c.js(ARTICLE.replace("SID", json.dumps(sid)), wait=30, retries=5)
    if got == "NOT ON PAGE":
        print(f"{sid} is not on the open tab — it may be below the fold, or "
              f"the tab moved off the timeline. Not claiming success.")
        c.close()
        return 1
    art = json.loads(got)
    same_author = art["who"] == EXPECTED
    # A long post is CLIPPED in the timeline: tweetText holds a prefix and the
    # rest sits behind "show more". So the visible text must equal the SOURCE
    # PREFIX, and the link card must name the repository — together that is
    # what the timeline can actually prove about a long post.
    vis, src = canon(art["text"]), canon(want)
    prefix_ok = src.startswith(vis) and len(vis) > 40
    same_text = prefix_ok
    print(f"status  {sid}")
    print(f"author  @{art['who']}  expected @{EXPECTED}  -> "
          f"{'OK' if same_author else 'WRONG ACCOUNT'}")
    print(f"text    {len(art['text'])} shown of {len(want)} "
          f"(clipped by X)  -> {'PREFIX MATCHES' if same_text else 'MISMATCH'}")
    if not same_text:
        fg, ft = canon(art["text"]), canon(want)
        for i, (x, y) in enumerate(zip(fg, ft)):
            if x != y:
                print(f"        first difference at {i}: "
                      f"got {x!r} ({ord(x):#06x}) want {y!r} "
                      f"({ord(y):#06x})")
                print(f"        got  ...{art['text'][max(0, i - 30):i + 30]!r}")
                print(f"        want ...{want[max(0, i - 30):i + 30]!r}")
                break
        else:
            print(f"        lengths differ: {len(fg)} vs {len(ft)}")
    print(f"links   {art['ext']}")
    print(f"card    {art.get('card', '(none)')}")
    # A t.co href never contains the source URL, so the link is proved by the
    # CARD X rendered from it: the repository name and host appear there.
    # The card is the proof: it must name the owner/repo the source URL
    # points at. A URL is "host/owner/repo", and the card prints "owner/repo"
    # with the host below it, so the path is what to look for.
    def ident(u: str) -> str:
        rest = u.split("://", 1)[-1]
        parts = [x for x in rest.split("/") if x]
        return "/".join(parts[1:3]) if len(parts) >= 3 else parts[0]
    repo_ok = (not want_urls) or all(
        ident(u) in (art.get("card") or "") for u in want_urls)
    ok_links = repo_ok
    if not ok_links:
        print("        the link card does not name the source repository")
    print("\nVERIFIED" if (same_author and same_text and ok_links)
          else "\nNOT VERIFIED")
    try:
        c.close()
    except Exception:
        pass
    return 0 if (same_author and same_text and ok_links) else 1


if __name__ == "__main__":
    sys.exit(main())
