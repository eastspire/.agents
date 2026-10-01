#!/usr/bin/env python3
"""Make sure a usable x.com tab exists, starting what is missing.

Three states, three actions, and nothing more:

  browser down          launch it through the real-profile launcher
  up but no x.com tab   open ONE tab at the composer
  up with an x.com tab  do nothing at all

The launcher is chrome-real-profile-launch/scripts/run.sh, not a raw
`Google Chrome --remote-debugging-port`, because the copy of the profile is
what carries the login. --no-tab is passed to it so the launcher does not open
a page of its own; this script decides what the one tab shows.

Opening a tab is a page load, and a page load makes the user confirm it in
their UI. That is why this is a separate script with a single narrow job and
the commit gate exempts only THIS FILE: every other script in the skill stays
forbidden from loading a page, so "the publisher opened a tab" remains a
defect rather than a shortcut.

  python3 ensure_browser.py 9240
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 9240
LAUNCH = os.path.expanduser(
    "~/.agents/skills/software-development/chrome-real-profile-launch/"
    "scripts/run.sh")
COMPOSE = "https://x.com/compose/post"


def cdp_up() -> bool:
    try:
        with urllib.request.urlopen(
                f"http://127.0.0.1:{PORT}/json/version", timeout=5) as r:
            return r.status == 200
    except Exception:
        return False


def x_tabs() -> list[dict]:
    try:
        with urllib.request.urlopen(
                f"http://127.0.0.1:{PORT}/json/list", timeout=8) as r:
            out = json.load(r)
    except Exception:
        return []
    return [t for t in out
            if t.get("type") == "page" and "x.com" in t.get("url", "")]


def launch() -> bool:
    """Start the real-profile copy, headed, with no tab of its own."""
    if not os.path.exists(LAUNCH):
        print(f"launcher not found at {LAUNCH}")
        return False
    print(f"browser is down — launching via {LAUNCH}", flush=True)
    p = subprocess.run(["bash", LAUNCH, "--port", str(PORT), "--headed",
                        "--fresh", "--no-tab"],
                       capture_output=True, text=True, timeout=420)
    tail = (p.stdout + p.stderr).strip().splitlines()[-6:]
    for line in tail:
        print("  " + line)
    return cdp_up()


def open_compose_tab() -> bool:
    """Open exactly one tab at the composer.

    /json/new is a GET, which is the documented way to ask the browser for a
    tab. It is a page load — the one this script exists to perform.
    """
    url = f"http://127.0.0.1:{PORT}/json/new?{COMPOSE}"
    req = urllib.request.Request(url, method="PUT")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            json.load(r)
    except urllib.error.HTTPError as e:
        if e.code not in (405, 501):
            print(f"  open failed: HTTP {e.code}")
            return False
        try:
            with urllib.request.urlopen(urllib.request.Request(url), timeout=30) as r:
                json.load(r)
        except Exception as e:
            print(f"  open failed: {e}")
            return False
    except Exception as e:
        print(f"  open failed: {e}")
        return False
    return True


def main() -> int:
    for _ in range(20):
        if cdp_up():
            break
        if not launch():
            print("could not start the browser")
            return 1
        time.sleep(3)

    for _ in range(20):
        tabs = x_tabs()
        if tabs:
            print(f"ready — {len(tabs)} x.com tab(s) open, "
                  f"using {tabs[0]['url'][:60]}")
            return 0
        print("browser is up but has no x.com tab — opening one at the composer",
              flush=True)
        if not open_compose_tab():
            return 1
        # X needs a moment before the Draft editor is queryable; a tab that is
        # opened and immediately driven returns "no visible Draft editor" and
        # looks like a failure rather than a page that has not painted yet.
        for _ in range(10):
            time.sleep(3)
            if x_tabs():
                break
    print("x.com tab is not reachable")
    return 1


if __name__ == "__main__":
    sys.exit(main())
