#!/usr/bin/env python3
"""Reply to a set of posts through the official X API, one verified at a time.

The browser path for replies does not work: X opens the inline reply box only
for a real click. Measured, not assumed — a synthesised mousedown/mouseup on
the control changes nothing, and with the overlays gone focus lands on it but
X ignores a synthesised Enter and Space. The official API needs no click.

This exists so the reply work is not blocked on the browser. It is separate
from post_reply.py on purpose: one is a screen, the other is HTTP, and the
two have nothing to share but the rule that a reply must carry a repository
from the organisation.

Requires an xurl app. Registering one needs a client secret pasted by hand,
so this script refuses to run rather than asking for one:

    xurl auth status

  python3 reply_via_api.py <reply_dir> [count]
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ORG_REPOS = (
    "github.com/crates-dev/",
    "github.com/euv-dev/",
    "github.com/hyperlane-dev/",
)

DECL = re.compile(r"^#\s*target-status:\s*(\d{15,25})\s*$", re.M)
HDR = re.compile(r"^#.*$\n?", re.M)


def xurl(*args: str) -> tuple[int, str, str]:
    p = subprocess.run(["xurl", *args], capture_output=True, text=True,
                       timeout=90)
    return p.returncode, p.stdout.strip(), p.stderr.strip()


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    reply_dir = Path(sys.argv[1])
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else 5

    code, out, _ = xurl("auth", "status")
    if "No apps registered" in out or code != 0:
        print("xurl has no app registered. Registering one needs a client "
              "secret pasted by hand:\n"
              "  xurl auth apps add <name> --client-id ... "
              "--client-secret ...\n"
              "  xurl auth oauth2 --app <name>\n"
              "  xurl auth default <name>", flush=True)
        return 1
    code, out, _ = xurl("whoami")
    if code != 0:
        print("xurl whoami failed:", out[:200], flush=True)
        return 1
    me = json.loads(out).get("data", {}).get("username", "?")
    print("posting as @%s\n" % me, flush=True)

    files = sorted(reply_dir.glob("*.txt"))
    if not files:
        print("no reply files in %s" % reply_dir, flush=True)
        return 1

    sent = 0
    for f in files:
        if sent >= limit:
            break
        raw = f.read_text(encoding="utf-8")
        m = DECL.search(raw)
        if not m:
            print("SKIP %s — no target-status declared" % f.name, flush=True)
            continue
        sid = m.group(1)
        body = HDR.sub("", raw).strip()

        # The two rules the browser path enforces, kept here too: the reply
        # carries a repository from the organisation, and it is not longer
        # than X allows. Neither is worth sending a broken reply for.
        if not any(r in body for r in ORG_REPOS):
            print("SKIP %s — no organisation repository in the reply"
                  % f.name, flush=True)
            continue
        if len(body) > 280:
            print("SKIP %s — %d characters, over the limit"
                  % (f.name, len(body)), flush=True)
            continue

        # Read the post first: replying to a post that no longer exists, or
        # answering the wrong one, is worse than not replying.
        code, out, _ = xurl("read", sid)
        if code != 0:
            print("SKIP %s — cannot read %s: %s" % (f.name, sid, out[:120]),
                  flush=True)
            continue
        data = json.loads(out).get("data", {})
        author = (data.get("author_id") or "?")
        print("→ replying to %s by %s" % (sid, author), flush=True)
        print("  %s" % (data.get("text", "")[:120]), flush=True)

        code, out, err = xurl("reply", sid, body)
        if code != 0:
            print("  FAILED: %s" % (out or err)[:200], flush=True)
            continue
        res = json.loads(out).get("data", {})
        print("  sent %s -> https://x.com/i/status/%s\n"
              % (res.get("id", "?"), res.get("id", "?")), flush=True)
        sent += 1
    print("%d sent" % sent, flush=True)
    return 0 if sent else 1


if __name__ == "__main__":
    sys.exit(main())
