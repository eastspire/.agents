#!/usr/bin/env python3
"""Minimal dependency-free CDP client over the raw websocket.

Every earlier attempt re-implemented this and each copy drifted. One module,
used by the clear-drafts and post steps alike.
"""
import base64, json, os, socket, struct, time, urllib.parse, urllib.request

STATE = os.path.expanduser("~/.hermes/state/chrome-real-profile.port")


_PORT = None


def port():
    global _PORT
    if _PORT is not None:
        return _PORT
    return int(open(STATE).read().strip())


def http(path, method="GET"):
    req = urllib.request.Request(f"http://127.0.0.1:{port()}{path}", method=method)
    with urllib.request.urlopen(req, timeout=25) as r:
        return json.load(r)


def tabs(kind=None):
    out = http("/json/list")
    return [t for t in out if kind is None or t.get("type") == kind]


def set_port(p):
    """Point the client at a specific shared instance.

    The state file records the port of the instance that last started, which is
    NOT necessarily the one you are talking to — another session may have
    started its own while you worked. Measured: the state file said 9228 while
    the live instance was on 9231.
    """
    global _PORT
    _PORT = int(p)
    return _PORT


def new_tab(url):
    return http("/json/new?" + urllib.parse.quote(url, safe=""), method="PUT")


def open_and_use(url):
    """new_tab + guaranteed close, even if the body raises.

    /json/new leaves an orphan behind if the caller never closes the target,
    and a few hundred orphans make the whole browser unresponsive — measured:
    the tab list reached 50 and every page load stopped completing. Context
    manager so "opened" and "closed" cannot drift apart.
    """
    return _Tab(url)


class _Tab:
    def __init__(self, url):
        self.info = new_tab(url)
        self.id = self.info["id"]
        self.cdp = Cdp(self.info["webSocketDebuggerUrl"])

    def __enter__(self):
        return self.cdp

    def __exit__(self, *exc):
        try:
            self.cdp.close()
        finally:
            close_tab(self.id)
        return False


def close_tab(target_id):
    try:
        return http(f"/json/close/{target_id}", method="GET")
    except Exception:
        return None


class Cdp:
    def __init__(self, ws_url, timeout=60):
        hostport, path = ws_url.split("//", 1)[1].split("/", 1)
        host, pp = hostport.split(":")
        self.s = socket.create_connection((host, int(pp)), timeout=timeout)
        key = base64.b64encode(os.urandom(16)).decode()
        self.s.send(f"GET /{path} HTTP/1.1\r\nHost: {hostport}\r\nUpgrade: websocket\r\n"
                    f"Connection: Upgrade\r\nSec-WebSocket-Key: {key}\r\n"
                    f"Sec-WebSocket-Version: 13\r\n\r\n".encode())
        buf = b""
        while b"\r\n\r\n" not in buf:
            buf += self.s.recv(4096)
        self.buf, self.id, self.replies, self.events = buf, 0, {}, []

    def _recv(self, n, deadline=None):
        """Read exactly n bytes. Returns None if the deadline passes.

        A bare `continue` on socket.timeout is wrong: with a non-zero
        settimeout the socket stays in non-blocking-ish mode, so the next recv
        blocks forever instead of polling again. Bounding each read by an
        absolute deadline is what makes the wait loops terminate.
        """
        deadline = deadline if deadline is not None else time.time() + 30
        while len(self.buf) < n:
            if time.time() > deadline:
                return None
            try:
                self.s.settimeout(max(0.05, min(1.0, deadline - time.time())))
                chunk = self.s.recv(65536)
            except (socket.timeout, TimeoutError):
                continue
            except OSError as e:
                raise ConnectionError(str(e))
            if not chunk:
                raise ConnectionError("socket closed")
            self.buf += chunk
        out, self.buf = self.buf[:n], self.buf[n:]
        return out

    def _frame(self, payload):
        mask = os.urandom(4)
        masked = bytes(b ^ mask[i % 4] for i, b in enumerate(payload))
        n = len(payload)
        hdr = b"\x81"
        if n < 126:
            hdr += bytes([0x80 | n])
        elif n < 65536:
            hdr += bytes([0x80 | 126]) + struct.pack(">H", n)
        else:
            hdr += bytes([0x80 | 127]) + struct.pack(">Q", n)
        self.s.send(hdr + mask + masked)

    def _drain(self, seconds):
        """Read frames for up to `seconds`, returning early once the buffer
        holds something. Returns False only when the socket is gone."""
        end = time.time() + seconds
        while time.time() < end:
            # One frame per drain pass; the outer loop supplies the pacing.
            head = self._recv(2, deadline=min(end, time.time() + 0.25))
            if head is None:
                continue
            b1, b2 = head
            ln = b2 & 0x7F
            if ln == 126:
                ext = self._recv(2, deadline=time.time() + 5)
                if ext is None:
                    return False
                ln = struct.unpack(">H", ext)[0]
            elif ln == 127:
                ext = self._recv(8, deadline=time.time() + 5)
                if ext is None:
                    return False
                ln = struct.unpack(">Q", ext)[0]
            # WebSocket control frames share the framing but are not JSON.
            # opcodes: 0=continuation 1=text 2=binary 8=close 9=ping 10=pong.
            # Parsing a ping payload as JSON raises UnicodeDecodeError, and
            # swallowing that as "no reply" is what made every earlier
            # evaluate() look like it had never run.
            opcode = b1 & 0x0F
            payload = self._recv(ln, deadline=time.time() + 10)
            if payload is None:
                return False
            if opcode == 0x8:
                return False
            if opcode == 0x9:                       # ping -> pong
                try:
                    self.s.send(b"\x8a" + bytes([0x80 | ln]) + os.urandom(4)
                               + bytes(b ^ os.urandom(4)[i % 4] for i, b in enumerate(payload)))
                except OSError:
                    return False
                continue
            if opcode in (0xA, 0x2, 0x0):
                continue                            # pong / binary / continuation
            try:
                m = json.loads(payload)
            except (json.JSONDecodeError, UnicodeDecodeError, OSError,
                    ConnectionError):
                continue
            if "id" in m and "method" not in m:
                self.replies[m["id"]] = m
            else:
                self.events.append(m)
        return True

    def send(self, method, _id=None, wait=20, **params):
        if _id is None:
            self.id += 1
            _id = self.id
        self._frame(json.dumps({"id": _id, "method": method,
                                "params": params}).encode())
        end = time.time() + wait
        while _id not in self.replies and time.time() < end:
            # _drain blocks up to its own deadline, so a fixed 0.5s slice adds
            # latency to EVERY call even when the reply is already buffered —
            # measured a flat 0.50s per evaluate. Drive the wait off the socket
            # instead: the loop exits as soon as the reply lands.
            if not self._drain(min(0.5, max(0.02, end - time.time()))):
                break
        r = self.replies.pop(_id, None)
        if r is None:
            return None
        if "error" in r:
            return {"__cdp_error": r["error"]}
        return r.get("result", {})

    def js(self, expr, wait=6, retries=4):
        """Evaluate and return the value.

        A freshly opened tab can drop the first Runtime.evaluate: the renderer
        swaps execution contexts while navigating, so the reply is lost and
        the id never comes back. Retrying is correct and cheap — the earlier
        version returned a __timeout dict and every caller treated that as a
        silent no-op, which is how "the click did nothing" was misread twice.
        """
        for attempt in range(retries + 1):
            # The first evaluate on a freshly opened tab ALWAYS times out while
            # the renderer swaps execution contexts — measured 26s wasted, then
            # instant success on the retry. So: fail fast, retry immediately.
            res = self.send("Runtime.evaluate", wait=wait, expression=expr,
                            returnByValue=True, awaitPromise=True)
            if res is not None and "__cdp_error" not in res:
                r = res.get("result", {})
                if r.get("subtype") == "error":
                    return {"__js_error": r.get("description", "")}
                if "value" in r:
                    return r["value"]
            time.sleep(0.4)
        return {"__timeout": "Runtime.evaluate did not reply"}

    def wait_for(self, expr, timeout=60, interval=2):
        end = time.time() + timeout
        last = None
        while time.time() < end:
            last = self.js(expr)
            if isinstance(last, dict):
                last = None            # timeout / error: keep waiting
            elif last is True or (isinstance(last, str) and last):
                return last
            time.sleep(interval)
        return None

    def close(self):
        try:
            self.s.close()
        except OSError:
            pass


EDITOR = "[data-testid='tweetText']"
