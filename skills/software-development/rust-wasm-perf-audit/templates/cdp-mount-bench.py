"""CDP mount benchmark template for euv/WASM framework verification.

Usage:
    1. Start `python3 -m http.server 8765 --bind 127.0.0.1` from example/www/
    2. Start headless chromium:
       chromium --headless=new --no-sandbox --disable-gpu \
                --remote-debugging-port=9222 \
                --user-data-dir=/tmp/cdp-profile \
                http://127.0.0.1:8765/index.html
    3. Wait 2-3 s for chromium to start
    4. Run this script: python3 /tmp/bench-mount.py
    5. Compare per-element counts and digest across N reloads; they must
       be stable to claim "DOM equivalent".

What you measure:
    - allNodes, divs, dataEuvIds, dataEuvDyn, dataEuvSig: structural
      counts; any change = renderer broke.
    - digest: byte fingerprint of tagName + textContent length sum;
      any change = visible content broke.
    - nav.duration: warm reload median; reflects mount commit cost.

Required: pip install websockets

Pitfalls (2026-09-05):
    - Page.reload returns instantly; wait at least 3 s after for the
      wasm module to fetch, init, and main() to run before polling DOM.
    - Cold start nav.duration is dominated by wasm fetch (~300 ms+).
      Only compare warm reload median across runs.
    - If you put the HTML in example/www/ for the server, expect
      wasm-pack build to delete it on next build. Use /tmp/ for HTML
      fixtures.
"""

import asyncio
import json
import statistics
import subprocess
import sys
import time
import urllib.request

import websockets

CHROME = "/root/LTPP-MINIMAX/chrome-linux/chrome"
URL = "http://127.0.0.1:8765/index.html"
RUNS = 7
WAIT_AFTER_RELOAD_S = 3.0


def _start_chrome() -> subprocess.Popen:
    subprocess.run(
        ["pkill", "-9", "-f", "chrome.*--remote-debugging"],
        stderr=subprocess.DEVNULL,
    )
    time.sleep(1)
    proc = subprocess.Popen(
        [
                CHROME,
                "--headless=new",
                "--no-sandbox",
                "--disable-gpu",
                "--remote-debugging-port=9222",
                "--user-data-dir=/tmp/cdp-profile",
                URL,
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    for _ in range(60):
        try:
            if (
                urllib.request.urlopen(
                    "http://127.0.0.1:9222/json/version", timeout=1
                ).status
                == 200
            ):
                break
        except Exception:
            time.sleep(0.5)
    time.sleep(2)
    return proc


def _kill_chrome(proc: subprocess.Popen) -> None:
    proc.kill()
    time.sleep(1)
    subprocess.run(
        ["pkill", "-9", "-f", "chrome.*--remote-debugging"],
        stderr=subprocess.DEVNULL,
    )


async def measure() -> list[dict]:
    targets = json.loads(
        urllib.request.urlopen("http://127.0.0.1:9222/json", timeout=2).read()
    )
    ws_url = next(
        (
            t["webSocketDebuggerUrl"]
            for t in targets
            if "index.html" in t.get("url", "")
        ),
        targets[0]["webSocketDebuggerUrl"],
    )

    seq = 0
    results: list[dict] = []

    async with websockets.connect(ws_url, max_size=20_000_000) as ws:
        async def call(method: str, params=None, await_promise: bool = False):
            nonlocal seq
            seq += 1
            await ws.send(
                json.dumps({"id": seq, "method": method, "params": params or {}})
            )
            pending = [seq]
            while pending:
                msg = json.loads(await ws.recv())
                if msg.get("id") in pending:
                    if "error" in msg:
                        raise RuntimeError(msg)
                    if await_promise:
                        return msg
                    return msg.get("result", {})

        await call("Runtime.enable")
        await call("Page.enable")

        for run in range(RUNS):
            await call("Page.reload", {"ignoreCache": True})
            await asyncio.sleep(WAIT_AFTER_RELOAD_S)
            js = r"""(() => {
                const all = document.querySelectorAll('#app *');
                let digest = 0;
                for (let i = 0; i < all.length; i++)
                    digest = (digest + all[i].tagName.length + (all[i].textContent || '').length) | 0;
                return {
                    allNodes: all.length,
                    divs: document.querySelectorAll('div').length,
                    dataEuvIds: document.querySelectorAll('[data-euv-id]').length,
                    dataEuvDyn: document.querySelectorAll('[data-euv-dynamic-id]').length,
                    dataEuvSig: document.querySelectorAll('[data-euv-signal-addrs]').length,
                    bodyText: document.body.innerText.slice(0, 250),
                    nav: (performance.getEntriesByType('navigation')[0] || {}),
                    digest,
                };
            })()"""
            r = await call(
                "Runtime.evaluate",
                {"expression": js, "returnByValue": True},
            )
            v = r["result"]["value"]
            results.append(v)
            nav_d = v["nav"].get("duration", 0) if v.get("nav") else 0
            print(
                f"  cycle {run}: nav.duration={nav_d:.1f}ms "
                f"ids={v['dataEuvIds']} divs={v['divs']} all={v['allNodes']} "
                f"dyn={v['dataEuvDyn']} sig={v['dataEuvSig']} digest={v['digest']}"
            )
    return results


def main() -> int:
    proc = _start_chrome()
    try:
        results = asyncio.run(measure())
    finally:
        _kill_chrome(proc)

    print()
    print("=== Final stability report ===")
    for k in (
        "allNodes",
        "divs",
        "dataEuvIds",
        "dataEuvDyn",
        "dataEuvSig",
        "digest",
    ):
        vals = [r[k] for r in results]
        print(
            f"  {k}: min={min(vals)} max={max(vals)} "
            f"median={statistics.median(vals)}"
        )
    nav_durs = [r["nav"].get("duration", 0) for r in results]
    print(
        f"  nav.duration: min={min(nav_durs):.1f}ms "
        f"median={statistics.median(nav_durs):.1f}ms "
        f"max={max(nav_durs):.1f}ms"
    )

    # Sanity gate: digest must be stable across all reloads.
    digests = {r["digest"] for r in results}
    if len(digests) != 1:
        print(f"FAIL: digest varied across reloads: {digests}")
        return 1
    print("PASS: digest stable across all reloads.")
    return 0


if __name__ == "__main__":
    sys.exit(main())