#!/usr/bin/env python3
"""Fresh-context verification that a deployed static site serves the new build.

Hops: (1) poll page HTML until the served CSS hash flips to --expect-css,
(2) fetch that CSS with Accept-Encoding and grep for --grep markers,
(3) measure a selector's computed style + geometry in a fresh Playwright
context, optionally with a host-injected CSS variable (immersive simulation).

Requires: playwright (python), a Chromium/Chrome binary.

Examples:
  CHROME_PATH=/root/LTPP-MINIMAX/chrome-linux/chrome \
  python3 check_deployed_site.py \
    --url "https://docs.ltpp.vip/github/pages/docs-pages/pages/euv/" \
    --expect-css app-DNjTxDit.css \
    --grep euv-mobile-safe-top \
    --selector .vp-navbar --expect-prop paddingTop=0px

  # immersive-host simulation (var injected on <html>, 1.3s settle):
  python3 check_deployed_site.py --url ... --expect-css app-DNjTxDit.css \
    --selector .vp-navbar --set-var --euv-mobile-safe-top=41px \
    --expect-prop paddingTop=41px --expect-prop height=93px
"""
import argparse, os, re, sys, time, urllib.request, gzip, io


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"Accept-Encoding": "gzip, deflate"})
    with urllib.request.urlopen(req, timeout=30) as r:
        data = r.read()
        if r.headers.get("Content-Encoding") == "gzip" or data[:2] == b"\x1f\x8b":
            data = gzip.GzipFile(fileobj=io.BytesIO(data)).read()
        return data


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", required=True, help="user-facing page URL (the real root, not a short alias)")
    ap.add_argument("--expect-css", required=True, help="expected new CSS filename, e.g. app-AbCdEf12.css")
    ap.add_argument("--grep", action="append", default=[], help="substring that must appear in the served CSS (repeatable)")
    ap.add_argument("--poll", type=int, default=10, help="hash-poll attempts, 30s apart (default 10)")
    ap.add_argument("--selector", default=None, help="selector to measure in a fresh browser context")
    ap.add_argument("--set-var", default=None, help="CSS var to inject on <html>, form name=value")
    ap.add_argument("--expect-prop", action="append", default=[], help="computed-style assertion prop=value (repeatable); 'height'/'top' use bounding box px")
    ap.add_argument("--width", type=int, default=390)
    ap.add_argument("--height", type=int, default=844)
    args = ap.parse_args()

    # Hop 2: poll until mirror serves the expected CSS hash
    served = None
    for i in range(args.poll):
        html = fetch(args.url).decode("utf-8", "replace")
        if len(html) == 0:
            print(f"[{i+1}] WARNING: empty body (check URL — short alias paths can 200 with 0 bytes)")
        found = sorted(set(re.findall(r'assets/[^"\']*\.css', html)))
        print(f"[{i+1}] css refs: {found}")
        if any(args.expect_css in f for f in found):
            served = next(f for f in found if args.expect_css in f)
            print("SYNCED")
            break
        time.sleep(30)
    if not served:
        print(f"FAIL: mirror never served {args.expect_css} after {args.poll} polls")
        return 1

    # Hop 2b: grep the served CSS (always with gzip handling)
    css_url = args.url.rsplit("/", 1)[0] + "/../" + served
    from urllib.parse import urljoin
    css_url = urljoin(args.url, served)
    css = fetch(css_url).decode("utf-8", "replace")
    print(f"css bytes (decompressed): {len(css)}")
    for g in args.grep:
        n = css.count(g)
        print(f"grep {g!r}: {n} occurrence(s)")
        if n == 0:
            print(f"FAIL: {g!r} not in served CSS")
            return 1

    if not args.selector:
        print("PASS (hash + grep hops)")
        return 0

    # Hop 3: fresh-context headless measurement
    from playwright.sync_api import sync_playwright
    chrome = os.environ.get("CHROME_PATH", "/root/LTPP-MINIMAX/chrome-linux/chrome")
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path=chrome, args=["--no-sandbox"])
        pg = b.new_context(viewport={"width": args.width, "height": args.height}).new_page()
        pg.goto(args.url, wait_until="domcontentloaded", timeout=45000)
        pg.wait_for_selector(args.selector, timeout=15000)
        if args.set_var:
            name, val = args.set_var.split("=", 1)
            pg.evaluate(f"document.documentElement.style.setProperty({name!r}, {val!r})")
        pg.wait_for_timeout(1300)  # let CSS transitions (e.g. sidebar padding) settle
        m = pg.evaluate("""(sel) => {
          const el = document.querySelector(sel);
          const cs = getComputedStyle(el), r = el.getBoundingClientRect();
          return new Proxy({}, { get: (_, k) =>
            k === 'top' ? `${r.top}px` : k === 'height' ? `${r.height}px` : cs[k] });
        }""", args.selector)
        ok = True
        for ep in args.expect_prop:
            prop, want = ep.split("=", 1)
            got = pg.evaluate(f"(() => {{ const el = document.querySelector({args.selector!r});"
                              f" const cs = getComputedStyle(el), r = el.getBoundingClientRect();"
                              f" return {prop!r} === 'top' ? `${{r.top}}px` : {prop!r} === 'height' ? `${{r.height}}px` : cs[{prop!r}]; }})()")
            status = "ok" if got == want else "MISMATCH"
            if got != want:
                ok = False
            print(f"  {prop}: got={got} want={want} [{status}]")
        b.close()
        print("PASS" if ok else "FAIL")
        return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
