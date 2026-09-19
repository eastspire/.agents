# Viewport-Match Repro Recipe

**Trigger**: User reports a bug with a screenshot or describes mobile-specific symptoms ("列表错乱", "按钮被截掉", "导航没显示", etc.) — and you want to verify whether the bug exists in the current build before proposing any code change.

## Why this matters

The temptation when investigating a UI bug is to launch one headless Chrome at `--window-size=1280,900` and either reproduce the issue or declare "I can't reproduce it, please provide steps." Both moves are wrong:

- **"I can't reproduce" is not evidence the bug doesn't exist** — viewport, DPR, scroll container height, font metrics, and even layout-induced reflow timing can all be the trigger.
- **"Provide steps" deflects the work** — the user already provided the bug (screenshot). The job is to extract viewport dimensions from the screenshot and replicate.

## 1. Extract viewport + key dimensions from the user's screenshot

```bash
# Use vision_analyze on the screenshot to enumerate visible elements + their bounding boxes.
# What to ask for:
#   - "What is the visible viewport size in px? Estimate width and height of the visible app area."
#   - "List each row/item with its top-left coords and dimensions."
#   - "Is there a top status bar, nav header, or app bar? Estimate their heights in px."
#   - "Is there a floating button / FAB? Where?"
```

You want at minimum: viewport width, viewport height, one or two element pitches (e.g. row height for a list, button size for a tap target), and any visible bottom safe-area bar.

## 2. Cross-check the user's build state

Before doing anything else, confirm the user is testing the build you think they are:

```bash
# For euv / wasm-pack projects:
git -C /root/github/<owner>/<repo> show master:Cargo.toml | grep '^version'
ls -la example/www/pkg/ | head
# mtime of pkg/euv_bg.wasm should be within a day of any recent edit

# Is the element size in the screenshot consistent with the source constant?
# Euv example: VIRTUAL_LIST_DEMO_ITEM_HEIGHT = 44 in
#   /root/github/euv-dev/euv/example/src/page/virtual_list/view/const.rs
# If the user's screenshot shows ~170px row pitch and source says 44px,
# the user is on a different build (older fork, local change, cached wasm).
```

If dimensions don't match source constants, **stop and ask the user to rebuild** (`wasm-pack build --target web --out-dir www/pkg` or equivalent). Don't propose source changes for a build mismatch.

## 3. Multi-viewport sweep — the actual repro

For each viewport you care about (minimum: the user's reported viewport, your default desktop, and ≥2 intermediate):

```python
import json, os, subprocess, time, urllib.request, websocket
CHROME = "/root/LTPP-MINIMAX/chrome-linux/chrome"  # or playwright
VIEWPORTS = [(375, 667), (768, 1024), (1280, 900)]  # add more from screenshot

def run_sweep(width, height, url, predicate_js):
    proc = subprocess.Popen([
        CHROME, "--headless=new",
        f"--remote-debugging-port=9370",
        "--no-sandbox", "--disable-gpu", "--no-first-run",
        f"--user-data-dir=/tmp/sweep-{width}x{height}",
        "--remote-allow-origins=*",
        f"--window-size={width},{height}", url,
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
       env={**os.environ, "HOME": "/root"})
    try:
        # wait for debug port + page target
        for _ in range(40):
            try: urllib.request.urlopen("http://127.0.0.1:9370/json/version", timeout=1).read(); break
            except: time.sleep(0.25)
        time.sleep(1)
        with urllib.request.urlopen("http://127.0.0.1:9370/json") as r:
            targets = json.loads(r.read())
        page = next(t for t in targets if t["type"] == "page")
        ws = websocket.create_connection(page["webSocketDebuggerUrl"], timeout=10)
        # enable + wait route + paint
        ws.send(json.dumps({"id": 1, "method": "Runtime.enable"}))
        ws.recv()
        time.sleep(3)
        # run predicate: e.g. scroll to many positions, check for breaks
        for k in range(20):
            v = k * 5000
            ws.send(json.dumps({"id": 100+k, "method": "Runtime.evaluate",
                               "params": {"expression": f"(()=>{{const c=document.querySelector('.your-container');c.scrollTop={v};c.dispatchEvent(new Event('scroll'));}})()"}}))
            ws.recv()
            time.sleep(0.2)
        ws.send(json.dumps({"id": 999, "method": "Runtime.evaluate",
                           "params": {"expression": predicate_js, "returnByValue": True}}))
        result = json.loads(ws.recv())
        return result["result"]["result"].get("value")
    finally:
        proc.terminate()
        try: proc.wait(timeout=3)
        except: proc.kill()

# Sweep all viewports, aggregate
for w, h in VIEWPORTS:
    res = run_sweep(w, h, "http://localhost:8765/#/your-route", """
        (() => {
            const rows = Array.from(document.querySelectorAll('.your-selector'))
                .map(s => parseInt(s.textContent.trim(), 10));
            const breaks = [];
            for (let i = 1; i < rows.length; i++) {
                if (rows[i] !== rows[i-1] + 1) breaks.push({at: i, prev: rows[i-1], cur: rows[i]});
            }
            return JSON.stringify({viewport: [innerWidth, innerHeight], breaks});
        })()
    """)
    print(f"viewport {w}x{h}: {res}")
```

`scripts/multi-viewport-sweep.py` (in this skill) provides a parameterized version.

## 4. Interpret results before declaring "no bug"

| Result | Meaning |
|---|---|
| All viewports clean | Master is fine. User is on a different build. **Don't propose source changes.** |
| One viewport breaks | The bug is real and viewport-dependent (e.g. mobile-only). Now you have grounds to investigate code. |
| All viewports break | The bug is universal. Look at the diff/state-tracking logic, not viewport. |

The "5 viewports × 21 scrollTop positions = 105 cases" pattern from this session is the minimum bar for declaring "no bug found." Anything less can be dismissed by the user as "you didn't try my conditions."

## 5. If the bug only reproduces on the user's viewport

Don't speculatively change code. Ask for:

- Build identifier (`git rev-parse HEAD` of their local checkout, or `?v=N` cache-buster URL behavior)
- `document.querySelectorAll(...)` output at the failing moment
- Or: ship a `templates/viewport-diag.html`-style diagnostic page that displays scroll position, viewport, element positions, and a button to log them — they open it on their device and send back the JSON.

## Files

- `scripts/multi-viewport-sweep.py` — parameterized sweep runner.
- See `templates/env-diag.html` for a related pattern (safe-area/env() diagnostics).