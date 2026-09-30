#!/usr/bin/env python3
"""Measure evaluate() latency, to see whether the retry logic is expensive."""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cdp as C  # noqa: E402

C.set_port(sys.argv[1] if len(sys.argv) > 1 else None)
tab = C.new_tab("https://x.com/home")
c = C.Cdp(tab["webSocketDebuggerUrl"])
time.sleep(10)
for _ in range(3):
    c.js("1+1")            # warm up: the first replies are always lost

for expr in ["0", "''", "false", "1+1", "2+2", "3+3"]:
    t0 = time.time()
    v = c.js(expr, wait=6, retries=0)
    print(f"  {expr!r:8} -> {v!r:8} in {time.time() - t0:.2f}s")
C.close_tab(tab["id"])
c.close()
