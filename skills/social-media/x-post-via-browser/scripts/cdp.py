#!/usr/bin/env python3
"""CDP client built on websocket-client instead of a hand-rolled websocket.

The hand-written protocol layer was the root cause of a long chain of silent
failures: control frames parsed as JSON, lost replies reported as "the page did
not react", and a fixed drain interval that put a floor under every call.
websocket-client handles framing, keepalive and control frames, so none of
that is ours to get wrong.

Install:  pip3 install websocket-client
"""
import json
import os
import time
import urllib.parse
import urllib.request

import websocket  # from websocket-client

STATE = os.path.expanduser("~/.hermes/state/chrome-real-profile.port")
_PORT = None


def set_port(p):
    global _PORT
    _PORT = int(p) if p else None
    return _PORT


def port():
    if _PORT is not None:
        return _PORT
    try:
        return int(open(STATE).read().strip())
    except (OSError, ValueError):
        return 9222


def http(path, method="GET"):
    req = urllib.request.Request(f"http://127.0.0.1:{port()}{path}", method=method)
    with urllib.request.urlopen(req, timeout=25) as r:
        return json.load(r)


def tabs(kind=None):
    out = http("/json/list")
    return [t for t in out if kind is None or t.get("type") == kind]


# There is deliberately no new_tab() here. Opening a tab is a page load, and
# every page load makes the user confirm it in their UI. A client that offers
# the call is a client that gets used; the caller reuses the tab already open.


class Cdp:
    def __init__(self, ws_url, timeout=30):
        # Chrome rejects websocket upgrades from an Origin header it does not
        # expect; suppress it.
        # url and timeout are kept so _reconnect() can rebuild the socket with
        # the same settings after Chrome drops an idle connection.
        self.url = ws_url
        self.timeout = timeout
        self.ws = self._connect()
        self.id = 0

    def _connect(self):
        return websocket.create_connection(
            self.url, timeout=self.timeout, origin=None,
            suppress_origin=True, enable_multithread=True)

    def send(self, method, wait=20, **params):
        self.id += 1
        mine = self.id
        try:
            self.ws.send(json.dumps({"id": mine, "method": method,
                                     "params": params}))
        except Exception:
            self._reconnect()
            self.ws.send(json.dumps({"id": mine, "method": method,
                                     "params": params}))
        end = time.time() + wait
        while time.time() < end:
            try:
                self.ws.settimeout(max(0.2, end - time.time()))
                raw = self.ws.recv()
            except websocket.WebSocketTimeoutException:
                continue
            except Exception as e:
                return {"__socket_error": str(e)[:120]}
            if not raw:
                return {"__socket_error": "empty frame"}
            try:
                m = json.loads(raw)
            except ValueError:
                continue                      # non-JSON payload; ignore
            if m.get("id") == mine:
                if "error" in m:
                    return {"__cdp_error": m["error"]}
                return m.get("result", {})
        return None

    def js(self, expr, wait=8, retries=4):
        """Evaluate, returning the value or a distinguishable error marker.

        Never returns None on failure: a silent None is what made earlier
        rounds conclude "the click did nothing" when the reply was simply lost.
        The first evaluates on a fresh target lose their reply while the
        renderer swaps contexts, so this retries quickly rather than waiting.
        """
        for _ in range(retries + 1):
            r = self.send("Runtime.evaluate", wait=wait, expression=expr,
                          returnByValue=True, awaitPromise=True)
            if isinstance(r, dict) and "__socket_error" not in r \
                    and "__cdp_error" not in r and r is not None:
                res = r.get("result", {})
                if res.get("subtype") == "error":
                    return {"__js_error": res.get("description", "")[:200]}
                if "value" in res:
                    return res["value"]
            time.sleep(0.4)
        return {"__timeout": "Runtime.evaluate did not reply"}

    def settle(self, minimum=300, ceiling=180):
        """Wait for a rendered SPA. Returns the body length it saw."""
        end = time.time() + ceiling
        n = 0
        while time.time() < end:
            n = self.js("document.body ? document.body.innerText.length : 0")
            if isinstance(n, int) and n > minimum:
                return n
            time.sleep(3)
        return n

    def _reconnect(self):
        """Re-open the socket after Chrome closed an idle connection.

        A long settle() leaves the socket untouched for minutes and Chrome
        eventually drops it, which surfaced as
        WebSocketConnectionClosedException in the middle of a post while the
        browser itself was still healthy. Reconnecting once and retrying the
        call is enough; the page state is untouched.
        """
        try:
            self.ws.close()
        except Exception:
            pass
        self.ws = self._connect()
        return self

    def close_composition(self, final=""):
        """End any open IME composition.

        imeSetComposition STARTS a composition. Leaving it open makes Chrome
        treat the page as holding unsaved input, which is what produces the
        "系统可能不会保存您所做的更改" dialog on any later unload — and Escape
        discards the whole composition, not one character. An insertText
        carrying the final text commits it once and closes it.
        """
        self.send("Input.imeSetComposition", text=final, selectionStart=len(final),
                  selectionEnd=len(final), wait=15, retries=2)
        if final:
            self.send("Input.insertText", text=final, wait=15, retries=2)
        return True

    def close(self):
        try:
            self.ws.close()
        except Exception:
            pass
