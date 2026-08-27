#!/bin/bash
# Headless Chromium visual verification script.
#
# Takes three screenshots — one per supported locale (English, Simplified
# Chinese, Arabic) — and dumps them to /tmp/<locale>.png. Each screenshot
# is captured AFTER a click on the corresponding entry in the language
# switcher footer, so the captured viewport reflects the real RTL/LTR
# layout, translated strings, and DOM attributes.

set -e

PORT=9234
USERDIR=/tmp/cp-shot-$$
LOG=/tmp/c-shot.log

rm -rf "$USERDIR"
mkdir -p "$USERDIR"

URL="https://eastspire.github.io/visa-tracker/?cb=$(date +%s%N)"

# Start Chromium in the background with remote debugging enabled.
"${CHROME:-/tmp/chrome-linux/chrome}" \
    --headless=new \
    --no-sandbox \
    --disable-gpu \
    --disable-dev-shm-usage \
    --disable-features=TranslateUI \
    --no-first-run \
    --disable-extensions \
    --disable-background-networking \
    --disable-sync \
    --no-default-browser-check \
    --no-pings \
    --metrics-recording-only \
    --hide-scrollbars \
    --window-size=1280,820 \
    --remote-debugging-port="$PORT" \
    --user-data-dir="$USERDIR" \
    --enable-logging=stderr \
    --v=1 \
    "$URL" \
    >"$LOG" 2>&1 &

CHROME_PID=$!
echo "chrome pid=$CHROME_PID port=$PORT"

# Wait for the debugger endpoint to come up before connecting.
for i in $(seq 1 20); do
    if curl -s --max-time 1 "http://127.0.0.1:$PORT/json/version" >/dev/null 2>&1; then
        echo "devtools ready after ${i} attempts"
        break
    fi
    sleep 0.5
done

# Find the page target.
PAGE_WS=$(curl -s "http://127.0.0.1:$PORT/json" \
    | python3 -c "import json,sys; t=[t for t in json.load(sys.stdin) if t.get('type')=='page'][0]; print(t['webSocketDebuggerUrl'])")
echo "ws=$PAGE_WS"

python3 <<EOF
import base64
import json
import sys
import time
import urllib.request

import websockets

async def main():
    async with websockets.connect("$PAGE_WS", max_size=64 * 1024 * 1024) as ws:
        next_id = 0
        async def call(method, params=None):
            nonlocal next_id
            next_id += 1
            msg = {"id": next_id, "method": method}
            if params is not None:
                msg["params"] = params
            await ws.send(json.dumps(msg))
            while True:
                raw = await ws.recv()
                data = json.loads(raw)
                if "id" in data and data["id"] == next_id:
                    return data

        # Navigate to the URL (re-issuing in case the auto-launch URL
        # raced the debugger endpoint).
        await call("Page.enable")
        # Set viewport explicitly so screenshots are predictable size.
        await call("Emulation.setDeviceMetricsOverride", {
            "width": 1280,
            "height": 1600,
            "deviceScaleFactor": 1,
            "mobile": False,
        })
        # Warm-up: open the page and let the wasm binary download into
        # the in-memory cache. Then a second navigate triggers main()
        # without the cold-start fetch latency.
        await call("Page.navigate", {"url": "$URL"})
        await asyncio.sleep(8.0)
        # Reload to re-init the app with everything in cache.
        await call("Page.reload", {"ignoreCache": True})
        await asyncio.sleep(4.0)
        await call("Page.navigate", {"url": "$URL"})

        async def evaluate(expression):
            res = await call("Runtime.evaluate", {
                "expression": expression,
                "returnByValue": True,
                "awaitPromise": True,
            })
            return res.get("result", {}).get("result", {}).get("value", "?")

        # Poll until [ready] shows up in the title — that's our cue that
        # wasm init + the first render of the euv tree both finished.
        for _ in range(80):
            ready = await evaluate('''
                (() => {
                    const t = document.title;
                    const switches = document.querySelectorAll('span');
                    const found_en = Array.from(switches).some((s) => (s.textContent || '').trim() === 'English');
                    const style_count = document.querySelectorAll('style').length;
                    return JSON.stringify({
                        title: t,
                        ready: t.includes('[ready]'),
                        found_english: found_en,
                        style_count: style_count,
                    });
                })()
            ''')
            print("polling:", ready)
            if '"ready":true' in ready and '"found_english":true' in ready and '"style_count":1' in ready:
                print("wasm mounted + CSS injected, breaking out of poll")
                break
            await asyncio.sleep(0.5)
        await asyncio.sleep(1.5)  # one more tick for App::mount to settle

        async def shoot(label, target_filename):
            # Take a screenshot of the viewport.
            shot = await call("Page.captureScreenshot", {"format": "png", "captureBeyondViewport": False})
            png_b64 = shot["result"]["data"]
            with open(target_filename, "wb") as fh:
                fh.write(base64.b64decode(png_b64))
            print(f"{label}: saved {target_filename} ({len(png_b64)//4} bytes b64)")

        async def evaluate(expression):
            res = await call("Runtime.evaluate", {
                "expression": expression,
                "returnByValue": True,
                "awaitPromise": True,
            })
            return res

        async def click_span_with_text(text):
            # dispatch a click via the existing DOM, then wait for the
            # euv runtime to flush the next render tick.
            expr = '''
                (() => {
                    const spans = Array.from(document.querySelectorAll('span'));
                    const t = spans.find((s) => (s.textContent || '').trim() === %r);
                    if (!t) return JSON.stringify({found: false, text: %r});
                    const rect = t.getBoundingClientRect();
                    const x = rect.left + rect.width / 2;
                    const y = rect.top + rect.height / 2;
                    t.dispatchEvent(new MouseEvent('mousedown', {bubbles: true, clientX: x, clientY: y}));
                    t.dispatchEvent(new MouseEvent('mouseup',   {bubbles: true, clientX: x, clientY: y}));
                    t.dispatchEvent(new MouseEvent('click',     {bubbles: true, clientX: x, clientY: y}));
                    return JSON.stringify({found: true, x, y, text: %r});
                })()
            ''' % (text, text, text)
            return await evaluate(expr)

        async def click_span_with_text(text):
            return await _click(text)

        async def _click(text):
            expr = '''
                (() => {
                    const spans = Array.from(document.querySelectorAll('span'));
                    const t = spans.find((s) => (s.textContent || '').trim() === %r);
                    if (!t) return JSON.stringify({found: false, text: %r});
                    const rect = t.getBoundingClientRect();
                    const x = rect.left + rect.width / 2;
                    const y = rect.top + rect.height / 2;
                    t.dispatchEvent(new MouseEvent('mousedown', {bubbles: true, clientX: x, clientY: y}));
                    t.dispatchEvent(new MouseEvent('mouseup',   {bubbles: true, clientX: x, clientY: y}));
                    t.dispatchEvent(new MouseEvent('click',     {bubbles: true, clientX: x, clientY: y}));
                    return JSON.stringify({found: true, x, y, text: %r});
                })()
            ''' % (text, text, text)
            r = await evaluate(expr)
            print("click %s:" % (text), r.get("result", {}).get("result", {}).get("value", "?"))
            await asyncio.sleep(2.0)
            confirm = await evaluate('''
                (() => {
                    const h = document.documentElement;
                    const root = document.querySelector('[class*="c_page_container"]');
                    const h1 = document.querySelector('h1');
                    return JSON.stringify({
                        htmlLang: h.getAttribute('lang'),
                        htmlDir: h.getAttribute('dir'),
                        rootLang: root ? root.getAttribute('lang') : null,
                        h1: h1 ? h1.textContent : null,
                    });
                })()
            ''')
            print("  -> %s" % (confirm.get("result", {}).get("result", {}).get("value", "?")))
            return r

        # 1. Initial state — should be either en-US (default) or zh-CN
        #    (browser-detected). Don't switch yet, just snap.
        await shoot("initial", "/tmp/initial.png")

        # 2. Switch to English (force even if default).
        r = await click_span_with_text("English")
        print("click English:", r.get("result", {}).get("result", {}).get("value", "?"))
        await asyncio.sleep(1.5)
        await shoot("english", "/tmp/english.png")

        # 3. Switch to Simplified Chinese.
        r = await click_span_with_text("简体中文")
        print("click 简体中文:", r.get("result", {}).get("result", {}).get("value", "?"))
        await asyncio.sleep(1.5)
        await shoot("chinese", "/tmp/chinese.png")

        # 4. Switch to Arabic — this should also flip the document dir to rtl.
        r = await click_span_with_text("العربية")
        print("click العربية:", r.get("result", {}).get("result", {}).get("value", "?"))
        await asyncio.sleep(1.5)
        # Read the html element's lang/dir AFTER the click to confirm.
        probe = await evaluate('''
            (() => {
                const h = document.documentElement;
                const root = document.querySelector('[class*="page_container"]');
                const body = document.body;
                const switches = Array.from(document.querySelectorAll('span'));
                const spansText = switches.map.map((s) => (s.textContent || '').trim());
                const h1Text = document.querySelector('h1') ? document.querySelector('h1').textContent : null;
                return JSON.stringify({
                    htmlLang: h.getAttribute('lang'),
                    htmlDir: h.getAttribute('dir'),
                    bodyDir: body.getAttribute('dir'),
                    rootLang: root ? root.getAttribute('lang') : null,
                    rootDir: root ? root.getAttribute('dir') : null,
                    title: document.title,
                    h1: h1Text,
                    active_locale: spansText.find((s) => /English|简体中文|العربية/.test(s)),
                    span_texts: spansText,
                });
            })()
        ''')
        print("post-ar-probe:", probe.get("result", {}).get("result", {}).get("value", "?"))
        await shoot("arabic", "/tmp/arabic.png")

        await ws.close()

import asyncio
asyncio.run(main())
EOF

# Tear down Chromium.
kill "$CHROME_PID" 2>/dev/null || true
sleep 1
pkill -9 -f "user-data-dir=$USERDIR" 2>/dev/null || true

echo "done."
ls -la /tmp/{initial,english,chinese,arabic}.png 2>&1 | head -5