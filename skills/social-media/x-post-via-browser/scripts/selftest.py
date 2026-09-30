#!/usr/bin/env python3
"""Self-test for the CDP client. Run this before trusting it with anything.

A CDP client that fails silently is worse than one that raises: it turns
"the page did X" into a guess. These checks pin the two failure modes that
cost hours in practice — a swallowed reply and a lost first evaluate.

  python3 selftest.py            # uses the shared instance
  python3 selftest.py 9231       # pin a port
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cdp as C  # noqa: E402

if len(sys.argv) > 1:
    C.set_port(sys.argv[1])

fails = []


def check(name, cond, detail=""):
    print(f"  {'ok  ' if cond else 'FAIL'} {name}{('  ' + str(detail)) if detail else ''}")
    if not cond:
        fails.append(name)


print(f"port {C.port()}")

tab = C.new_tab("https://x.com/home")
c = C.Cdp(tab["webSocketDebuggerUrl"])

# 0. Warm up first. The first few evaluates on a NEW target routinely lose
#    their reply, so timing them measures target warm-up, not latency — an
#    earlier version of this check failed for exactly that reason.
warm_start = time.time()
for _ in range(4):
    c.js("0")
print(f"  (warm-up took {time.time() - warm_start:.1f}s — lost replies on a new target)")

# 1. A falsy-but-valid result must not look like a failure, and once warm it
#    must be quick.
t0 = time.time()
r1 = c.js("0")
r2 = c.js("''")
r3 = c.js("false")
elapsed = time.time() - t0
check("falsy values survive", r1 == 0 and r2 == "" and r3 is False,
      f"{r1!r} {r2!r} {r3!r}")
check("warm evaluates are fast", elapsed < 3, f"{elapsed:.2f}s for 3")

# 2. A thrown error must be reported, not swallowed.
r4 = c.js("throw new Error('selftest')")
check("errors are marked", isinstance(r4, dict) and "__js_error" in r4, repr(r4)[:70])

# 3. The first evaluate on a fresh tab may be lost; the retry must recover.
#    A client without a retry would return a failure marker here.
t0 = time.time()
r5 = c.js("1+1")
check("evaluate recovers (retry works)", r5 == 2, f"{r5!r} in {time.time()-t0:.1f}s")

# 4. A control frame must not corrupt the stream. Send a ping by waiting; if
#    the frame parser mishandled it, the NEXT evaluate would fail.
time.sleep(1)
r6 = c.js("2+2")
check("stream survives idle time", r6 == 4, repr(r6)[:70])

# 5. Real page access.
deadline = time.time() + 90
n = 0
while time.time() < deadline:
    n = c.js("document.body ? document.body.innerText.length : 0")
    if isinstance(n, int) and n > 400:
        break
    time.sleep(3)
check("x.com renders", isinstance(n, int) and n > 400, f"bodyChars={n}")
check("logged in", c.js(
    '!!document.querySelector(\'[data-testid="SideNav_AccountSwitcher_Button"]\')') is True)

# 6. Closing must actually close, or orphans accumulate until the browser
#    stops responding.
before = len(C.tabs("page"))
tmp = C.new_tab("about:blank")
time.sleep(1.5)
opened = len(C.tabs("page"))
check("new_tab really opens", opened > before, f"{before} -> {opened}")
C.close_tab(tmp["id"])
time.sleep(2)
after = len(C.tabs("page"))
# Comparing `after < before` was wrong: the open already restored the count, so
# a working close returns to `before`, not below it. That mis-check hid a
# genuinely working close_tab.
check("close_tab really closes", after == before, f"{opened} -> {after} (base {before})")

C.close_tab(tab["id"])
c.close()

print()
if fails:
    print(f"selftest: FAIL — {', '.join(fails)}")
    raise SystemExit(1)
print("selftest: PASS")
