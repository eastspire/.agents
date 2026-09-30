# Open-source mirror fallback chain and the Safari-UA trick

## When vendor primaries fail

These official URLs all return HTML/302/404 to a bare `curl` because they sit behind JS-rendered tracking redirects that don't fire in a non-browser client:

- `https://download.blender.org/release/<branch>/<file>`
- `https://app.warp.dev/download?version=...`
- `https://code.visualstudio.com/...` (returns landing page HTML)

Don't loop on the same URL with different curl flags. Switch to a mirror.

## Working mirror list (Linux/macOS GUI apps)

Probe with HEAD and pick lowest latency. All currently host Blender, VS Code, OBS, Krita, Godot:

| Mirror | Base URL | Notes |
|---|---|---|
| Tsinghua | `https://mirrors.tuna.tsinghua.edu.cn/<project>/` | Sometimes lags upstream by a release; verify version exists |
| Aliyun | `https://mirrors.aliyun.com/<project>/` | **Blocks aria2, see below** |
| Clarkson | `https://mirror.clarkson.edu/<project>/` | US-East; SSL handshake sometimes drops mid-download |
| Dotsrc | `https://mirror.dotsrc.org/<project>/` | Slow (~2 MB/s from CN) but reliable |
| Yandex | `https://mirror.yandex.ru/mirrors/<project>/` | Wide coverage, decent from CN |

Always re-derive the path per project — many projects don't use the same directory layout as upstream.

## The Safari-UA trick

Aliyun (and several other CN mirrors) fingerprint download clients by User-Agent and **return HTTP 403 to any client that isn't a real browser**:

- `curl` with no `-A` → 403
- `curl -A "curl/8.x"` → 403
- `aria2c` with default UA → 403 (regardless of `-x1` vs `-x16`)
- `curl -A "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15"` → 200, ~10 MB/s

So for any large download from Aliyun (or unknown CN mirrors), default to curl + Safari UA before trying aria2. Save the aria2 path for known-friendly hosts.

## Range-request verification

Before committing to a mirror for a >100 MB file, confirm `Accept-Ranges: bytes` and a sane `Content-Length` — these are how you'll verify integrity later (no `.sha256` is usually published for GUI apps).

```bash
curl -sIL --max-time 15 -A "<Safari UA>" <url> | grep -iE "content-length|accept-ranges"
```

Then after download:

```bash
[ "$(stat -f %z <file>)" = "$(curl -sIL <url> | awk '/content-length/{print $2}' | tr -d '\r')" ] && echo OK
```