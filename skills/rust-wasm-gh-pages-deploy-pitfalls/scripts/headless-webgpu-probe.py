#!/usr/bin/env python3
"""Swiftshader / headless WebGPU sanity probe.

Use this to determine whether your Chromium is running on a real GPU or
swiftshader (CPU-based WebGPU). Swiftshader silently fails to execute
fragment shaders — see rust-wasm-gh-pages-deploy-pitfalls §坑 18.

The script loads a 30-line minimal WebGPU page that draws a single red
triangle, then checks whether the canvas's center pixel is red.

Expected outcomes:
  * real GPU                → center pixel = red (255, 0, 0)
  * swiftshader             → center pixel = white (255, 255, 255) — backing store default
  * WebGPU unavailable      → adapter is null

Usage:
    python3 scripts/headless-webgpu-probe.py [--port 9010]

Outputs:
    prints one line: `RESULT: <env> center=rgba(r,g,b,a) clear=rgba(r,g,b,a)`
    exits 0 if real GPU, 1 if swiftshader, 2 if WebGPU unavailable

Dependencies: playwright with chromium installed.
"""

from __future__ import annotations
import argparse
import http.server
import socketserver
import threading
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

PROBE_HTML = """<!DOCTYPE html>
<html><head><style>body{margin:0;background:#000;color:#fff;font:12px monospace}</style></head>
<body><canvas id="c" width="200" height="200"></canvas><pre id="log"></pre>
<script type="module">
const log = (s) => { const el = document.getElementById('log'); el.textContent += s + '\\n'; console.log(s); };
window.__result = { env: 'unknown', center: null, clear: null, err: null };
(async () => {
    if (!navigator.gpu) { window.__result = { env: 'no-gpu', err: 'navigator.gpu undefined' }; log('NO GPU'); return; }
    const adapter = await navigator.gpu.requestAdapter();
    if (!adapter) { window.__result = { env: 'no-adapter', err: 'adapter null' }; log('NO ADAPTER'); return; }
    const info = adapter.info || {};
    log('adapter.vendor=' + info.vendor + ' architecture=' + info.architecture);
    if ((info.vendor || '').toLowerCase().includes('google')) {
        window.__result = { env: 'swiftshader', err: 'google vendor = swiftshader' };
        log('SWIFTSHADER');
        return;
    }
    window.__result = { env: 'real-gpu', err: null };
    const device = await adapter.requestDevice();
    const canvas = document.getElementById('c');
    const ctx = canvas.getContext('webgpu');
    const format = navigator.gpu.getPreferredCanvasFormat();
    ctx.configure({ device, format, alphaMode: 'opaque' });
    const module = device.createShaderModule({
        code: `
            @vertex fn vs(@builtin(vertex_index) i: u32) -> @builtin(position) vec4f {
                let p = array<vec2f,3>(vec2f(0.0,0.6), vec2f(-0.6,-0.6), vec2f(0.6,-0.6));
                return vec4f(p[i], 0.0, 1.0);
            }
            @fragment fn fs() -> @location(0) vec4f { return vec4f(1.0, 0.0, 0.0, 1.0); }
        `,
    });
    const pipeline = device.createRenderPipeline({
        layout: 'auto',
        vertex: { module, entryPoint: 'vs' },
        fragment: { module, entryPoint: 'fs', targets: [{ format }] },
        primitive: { topology: 'triangle-list' },
    });
    const encoder = device.createCommandEncoder();
    const pass = encoder.beginRenderPass({
        colorAttachments: [{
            view: ctx.getCurrentTexture().createView(),
            clearValue: { r: 0.0, g: 0.0, b: 0.5, a: 1.0 },
            loadOp: 'clear', storeOp: 'store',
        }],
    });
    pass.setPipeline(pipeline); pass.draw(3); pass.end();
    device.queue.submit([encoder.finish()]);
    // Give the worker thread a moment to flush before reading.
    await new Promise(r => setTimeout(r, 500));
    // Force the browser to composite the canvas.
    document.body.getBoundingClientRect();
    window.__result = { env: 'real-gpu-painted', err: null };
    log('SUBMITTED — now read center pixel');
})().catch(e => { window.__result = { env: 'err', err: e.message }; log('ERR: ' + e.message); });
</script></body></html>
"""

def serve(port: int) -> socketserver.TCPServer:
    """Start a one-shot HTTP server in a daemon thread."""
    class Handler(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a, **kw): pass
    httpd = socketserver.TCPServer(("127.0.0.1", port), Handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=9010)
    ap.add_argument("--chromium", default="/root/LTPP-MINIMAX/chrome-linux/chrome")
    ap.add_argument("--timeout", type=int, default=8000)
    args = ap.parse_args()

    tmpdir = Path("/tmp/webgpu-probe")
    tmpdir.mkdir(exist_ok=True)
    (tmpdir / "index.html").write_text(PROBE_HTML)
    httpd = serve(args.port)
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                executable_path=args.chromium,
                headless=True,
                args=["--enable-unsafe-webgpu", "--no-sandbox", "--disable-dev-shm-usage"],
            )
            ctx = browser.new_context(viewport={"width": 320, "height": 320})
            page = ctx.new_page()
            page.on("pageerror", lambda e: print(f"PAGEERR: {e}"))
            page.on("console", lambda m: print(f"CONSOLE {m.type}: {m.text}"))
            page.goto(f"http://127.0.0.1:{args.port}/index.html", wait_until="load")
            page.wait_for_timeout(args.timeout)
            # Get the meta first (which catches JS errors that prevent canvas creation)
            meta = page.evaluate("window.__result")
            # Then screenshot the full page and sample the canvas region (200x200 at top-left)
            try:
                png_bytes = page.screenshot(clip={"x": 0, "y": 0, "width": 200, "height": 200})
                try:
                    from PIL import Image
                    import io
                    im = Image.open(io.BytesIO(png_bytes))
                    pixel = list(im.getpixel((100, 100)))
                except ImportError:
                    pixel = ["no-pil"]
                center = pixel
            except Exception as e:
                center = f"screenshot-err: {e}"
            browser.close()
    finally:
        httpd.shutdown()

    env = (meta or {}).get("env", "unknown")
    err = (meta or {}).get("err")
    if isinstance(center, list) and len(center) == 4 and all(isinstance(x, int) for x in center):
        r, g, b, a = center
        print(f"RESULT: env={env} center=rgba({r},{g},{b},{a}) err={err}")
        if env in ("no-gpu", "no-adapter"):
            return 2
        if env == "real-gpu-painted" and r > 200 and g < 50 and b < 50:
            return 0  # real GPU, fragment painted red
        if env == "real-gpu-painted":
            print("HINT: env=real-gpu but center pixel is not red → check if swiftshader was bypassed")
            return 1
        # env == swiftshader / err — center pixel will be white (255,255,255) or black (0,0,0)
        return 1  # not real GPU
    else:
        print(f"RESULT: env={env} center={center!r} err={err}")
        if env in ("no-gpu", "no-adapter"):
            return 2
        return 1

if __name__ == "__main__":
    raise SystemExit(main())
