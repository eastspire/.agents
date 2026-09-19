#!/usr/bin/env python3
"""Multi-viewport headless sweep for bug repro.

Tests a URL across multiple viewport sizes, runs a scroll-sweep, and evaluates
a predicate JS at each step. Useful for verifying whether a UI bug reproduces
on the user's reported viewport or only on a specific build of the app.

Usage:
    python3 scripts/multi-viewport-sweep.py \
        --url http://localhost:8765/#/virtual-list \
        --predicate-js-file /tmp/predicate.js \
        --viewports 375x667,768x1024,1280x900 \
        --scroll-steps 20

The predicate JS must return a JSON-stringifiable value. Typical predicate:

    const rows = Array.from(document.querySelectorAll('.c_virtual_list_row_index'))
        .map(s => parseInt(s.textContent.trim(), 10));
    const breaks = [];
    for (let i = 1; i < rows.length; i++) {
        if (rows[i] !== rows[i-1] + 1) breaks.push({at: i, prev: rows[i-1], cur: rows[i]});
    }
    return JSON.stringify({viewport: [innerWidth, innerHeight], breaks});

Defaults:
- Chrome: /root/LTPP-MINIMAX/chrome-linux/chrome
- Each viewport gets its own --user-data-dir under /tmp/sweep-<W>x<H>
- Debug port: 9370 (single Chrome at a time; sequential viewports)
- Per-step scroll is applied to the FIRST .scrollable container (anything with
  overflow-y: auto/scroll on the page). Override via --scroll-selector.
"""
import argparse, json, os, subprocess, sys, time, urllib.request, websocket

CHROME = "/root/LTPP-MINIMAX/chrome-linux/chrome"


def wait_for_debug(port, timeout=20):
    for _ in range(int(timeout * 4)):
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{port}/json/version", timeout=1).read()
            return
        except Exception:
            time.sleep(0.25)
    raise RuntimeError(f"chrome debug port {port} never came up")


def find_page(ws_url):
    with urllib.request.urlopen("http://127.0.0.1:9370/json") as r:
        targets = json.loads(r.read())
    return next(t for t in targets if t["type"] == "page")


def run_viewport(width, height, url, predicate_js, scroll_steps, scroll_selector, settle_ms, debug_port=9370):
    profile = f"/tmp/sweep-{width}x{height}-{int(time.time())}"
    proc = subprocess.Popen([
        CHROME, "--headless=new", f"--remote-debugging-port={debug_port}",
        "--no-sandbox", "--disable-gpu", "--no-first-run",
        "--disable-background-timer-throttling",
        f"--user-data-dir={profile}",
        "--remote-allow-origins=*",
        f"--window-size={width},{height}", url,
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
       env={**os.environ, "HOME": "/root"})
    try:
        wait_for_debug(debug_port)
        time.sleep(1)
        page = find_page(debug_port)
        ws = websocket.create_connection(page["webSocketDebuggerUrl"], timeout=10)
        ws.send(json.dumps({"id": 1, "method": "Runtime.enable"}))
        ws.recv()
        time.sleep(3)  # wasm load + first paint + viewport measure

        # determine scroll height
        ws.send(json.dumps({"id": 50, "method": "Runtime.evaluate",
                            "params": {"expression": f"""
                                JSON.stringify({{
                                    scrollHeight: document.querySelector('{scroll_selector}')?.scrollHeight || 0,
                                    clientHeight: document.querySelector('{scroll_selector}')?.clientHeight || 0,
                                }})
                            """, "returnByValue": True}}))
        info = json.loads(ws.recv())["result"]["result"]["value"]
        info = json.loads(info)
        max_scroll = max(0, info["scrollHeight"] - info["clientHeight"])

        results = []
        for k in range(scroll_steps):
            v = int(max_scroll * k / max(1, scroll_steps - 1))
            ws.send(json.dumps({"id": 100 + k, "method": "Runtime.evaluate",
                                "params": {"expression": f"""
                                    (() => {{
                                        const el = document.querySelector('{scroll_selector}');
                                        if (el) {{ el.scrollTop = {v}; el.dispatchEvent(new Event('scroll')); }}
                                    }})()
                                """}}))
            ws.recv()
            time.sleep(settle_ms / 1000.0)
            ws.send(json.dumps({"id": 200 + k, "method": "Runtime.evaluate",
                                "params": {"expression": predicate_js, "returnByValue": True}}))
            r = json.loads(ws.recv())
            try:
                results.append({"step": k, "scrollTop": v, "result": json.loads(r["result"]["result"]["value"])})
            except Exception:
                results.append({"step": k, "scrollTop": v, "result": r.get("result", {}).get("result", r)})
        ws.close()
        return {"viewport": [width, height], "scrollHeight": info["scrollHeight"],
                "clientHeight": info["clientHeight"], "results": results}
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except Exception:
            proc.kill()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", required=True)
    ap.add_argument("--predicate-js-file", required=True, help="Path to JS that returns JSON-stringifiable value")
    ap.add_argument("--viewports", default="375x667,768x1024,1280x900")
    ap.add_argument("--scroll-steps", type=int, default=20)
    ap.add_argument("--scroll-selector", default=".c_virtual_list_container")
    ap.add_argument("--settle-ms", type=int, default=200)
    args = ap.parse_args()

    predicate_js = open(args.predicate_js_file).read()
    summary = []
    for v in args.viewports.split(","):
        w, h = v.strip().split("x")
        w, h = int(w), int(h)
        print(f"=== viewport {w}x{h} ===", file=sys.stderr)
        result = run_viewport(w, h, args.url, predicate_js, args.scroll_steps, args.scroll_selector, args.settle_ms)
        # verdict: any step's result has non-empty `breaks`?
        bad = [r for r in result["results"]
               if isinstance(r["result"], dict) and r["result"].get("breaks")]
        verdict = "BROKEN" if bad else "CLEAN"
        print(f"  verdict: {verdict} ({len(bad)} bad of {len(result['results'])} steps)", file=sys.stderr)
        if bad:
            print(f"  first bad: {json.dumps(bad[0])[:200]}", file=sys.stderr)
        summary.append({"viewport": [w, h], "verdict": verdict, "bad_steps": len(bad)})

    print(json.dumps({"url": args.url, "summary": summary}, indent=2))


if __name__ == "__main__":
    main()