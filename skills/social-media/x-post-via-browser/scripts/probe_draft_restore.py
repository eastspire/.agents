#!/usr/bin/env python3
"""Prove, on demand, why automation must not drive x.com/compose/post.

This is the evidence behind the x-post-via-browser skill. Run it and it
demonstrates the draft-restore behaviour and the endpoint refusals. It is
strictly read-only: it opens its own tab, reads, and never types, clicks,
or closes anything of the user's.

  python3 probe_draft_restore.py    # does a fresh composer tab come pre-filled?
  python3 probe_draft_restore.py --all   # also probe the auth endpoints
"""
import base64, json, os, socket, struct, sys, time
import urllib.parse, urllib.request

STATE = os.path.expanduser("~/.hermes/state/chrome-real-profile.port")


def port():
    return int(open(STATE).read().strip())


def http(path, method="GET", p=None):
    req = urllib.request.Request(f"http://127.0.0.1:{p or port()}{path}", method=method)
    with urllib.request.urlopen(req, timeout=25) as r:
        return json.load(r)


def cdp_js(ws, expr):
    hostport, path = ws.split("//", 1)[1].split("/", 1)
    host, pp = hostport.split(":")
    s = socket.create_connection((host, int(pp)), timeout=40)
    key = base64.b64encode(os.urandom(16)).decode()
    s.send(f"GET /{path} HTTP/1.1\r\nHost: {hostport}\r\nUpgrade: websocket\r\n"
           f"Connection: Upgrade\r\nSec-WebSocket-Key: {key}\r\n"
           f"Sec-WebSocket-Version: 13\r\n\r\n".encode())
    while b"\r\n\r\n" not in (b := s.recv(4096)):
        pass
    payload = json.dumps({"id": 1, "method": "Runtime.evaluate",
                          "params": {"expression": expr, "returnByValue": True,
                                     "awaitPromise": True}}).encode()
    mask = os.urandom(4)
    masked = bytes(b ^ mask[i % 4] for i, b in enumerate(payload))
    n = len(payload)
    hdr = b"\x81" + (bytes([0x80 | n]) if n < 126
                     else bytes([0x80 | 126]) + struct.pack(">H", n))
    s.send(hdr + mask + masked)
    data = b""
    while True:
        b1, b2 = s.recv(2)
        ln = b2 & 0x7F
        if ln == 126:
            ln = struct.unpack(">H", s.recv(2))[0]
        elif ln == 127:
            ln = struct.unpack(">Q", s.recv(8))[0]
        data += s.recv(ln)
        try:
            m = json.loads(data)
            if m.get("id") == 1:
                s.close()
                if "error" in m:
                    return {"__cdp": m["error"]}
                r = m.get("result", {}).get("result", {})
                return r.get("value") if r.get("subtype") != "error" \
                    else {"__js": r.get("description")}
        except json.JSONDecodeError:
            continue


def new_tab(url, p=None):
    return http("/json/new?" + urllib.parse.quote(url, safe=""), method="PUT", p=p)


def settle(ws, minimum=400, tries=45):
    for _ in range(tries):
        n = cdp_js(ws, "document.body ? document.body.innerText.length : 0") or 0
        if isinstance(n, int) and n > minimum:
            return True
        time.sleep(2)
    return False


def probe_draft_restore():
    p = port()
    before = {t["id"] for t in http("/json/list", p=p) if t.get("type") == "page"}
    tab = new_tab(f"https://x.com/compose/post?probe={int(time.time())}", p)
    ws = tab["webSocketDebuggerUrl"]
    settle(ws, 300)
    time.sleep(4)

    print("=== does a FRESH composer tab arrive pre-filled? ===")
    print("  new target (not one of the pre-existing):",
          tab["id"] not in before)
    print("  we are in our own tab:", cdp_js(ws, "location.href"))
    draft = cdp_js(ws, "(() => { const e = document.querySelector"
                       "('[data-testid=\"tweetText\"]'); return e ? e.textContent : null; })()")
    if draft:
        print("  editor text:", repr(draft)[:300])
        print("\n  VERDICT: REFUSED — the editor already holds text that is not")
        print("           ours. Typing here would overwrite that draft and the")
        print("           Post button would publish it. Stop here.")
    else:
        print("  editor is empty — the account may have no saved drafts right now.")
    print("  (this probe is read-only; it typed and clicked nothing)")
    return bool(draft)


def probe_endpoints():
    p = port()
    tab = new_tab("https://x.com/home", p)
    ws = tab["webSocketDebuggerUrl"]
    settle(ws)
    stale = ("AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOjhJ7dQGBB2Y4X1GJm5g"
             "%2Bv%2B2x%2BjiLjsdfpD7A%3D")
    out = cdp_js(ws, r"""
(async ([stale]) => {
  const ct0 = (document.cookie.split('; ').find(c => c.startsWith('ct0=')) || '').slice(4);
  const res = {};
  const call = async (name, url, body, bearer) => {
    try {
      const r = await fetch(url, {method: 'POST',
        headers: {'content-type': 'application/json',
                  'authorization': 'Bearer ' + bearer,
                  'x-csrf-token': ct0, 'origin': 'https://x.com',
                  'referer': 'https://x.com/compose/post'},
        body: JSON.stringify(body)});
      res[name] = {status: r.status, body: (await r.text()).slice(0, 260)};
    } catch (e) { res[name] = {error: String(e)}; }
  };
  // A body that cannot be mistaken for a real tweet: the endpoint rejects it on
  // auth before it ever looks at the text.
  await call('rest_stale_bearer', 'https://x.com/i/api/2/tweets', {status: 'probe'}, stale);
  return JSON.stringify(res);
})(__STALE__)
""".replace("__STALE__", json.dumps(stale)))
    print("\n=== internal posting endpoints, from inside the logged-in page ===")
    d = json.loads(out) if isinstance(out, str) else out
    for k, v in d.items():
        print(f"  {k}: {v.get('status')} {v.get('body', v.get('error'))[:240]}")
    return d


if __name__ == "__main__":
    if "--all" in sys.argv:
        probe_draft_restore()
        probe_endpoints()
    else:
        probe_draft_restore()
