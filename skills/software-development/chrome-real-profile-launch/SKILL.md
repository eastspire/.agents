---
name: chrome-real-profile-launch
description: "Use when browser automation must run with the user's REAL Chrome logins — copy the profile to a scratch dir first, then launch Chrome on the copy over CDP. The system browser is never driven directly."
version: 1.0.0
author: local
license: MIT
platforms: [macos, linux, windows]
metadata:
  hermes:
    tags: [chrome, cdp, browser-automation, real-profile, logins, headless, remote-debugging, cookies, authenticated]
    related_skills: [chrome-devtools-protocol, hermes-real-profile-browser, blocked-page-recovery, inspecting-hermes-desktop-dom]
---

# Launch Chrome on a COPY of the real profile, over CDP

## THE RULE

**Every** browser operation that needs the user's real logins goes through this
procedure. There is no shortcut, no "just point at the real dir" variant, and
no "it's only a GET so I can skip the copy" exception.

Two hard requirements, both of them the user's:

1. **Never drive the real profile directory.** Copy it to a scratch dir first.
   Chrome holds `SingletonLock` on the live profile, and more importantly a
   second instance writing into the user's live `Default/` corrupts the session
   they are actually using.
2. **Never let the copy collide with the system browser.** A copied
   `SingletonLock` makes the new instance abort on startup with
   `ProcessSingleton ... Aborting now to avoid profile corruption.` — the copy
   is useless until those files are removed.

## Step 1 — copy the profile (macOS)

```bash
WORK="$HOME/.hermes/cache/scratch/chrome-real-$(date +%s)"
mkdir -p "$WORK"

rsync -a --delete \
  --exclude='Cache' \
  --exclude='Code Cache' \
  --exclude='GPUCache' \
  --exclude='ShaderCache' \
  --exclude='GraphiteDawnCache' \
  --exclude='component_crx_cache' \
  --exclude='Crashpad' \
  --exclude='Service Worker/CacheStorage' \
  --exclude='Service Worker/ScriptCache' \
  --exclude='Singleton*' \
  --exclude='DevToolsActivePort' \
  "$HOME/Library/Application Support/Google/Chrome/" "$WORK/profile/"
```

`--exclude='Singleton*'` and `--exclude='DevToolsActivePort'` are **not
optional**. Measured on this machine: a 4.8 GB profile copies in ~23 s; leaving
the singleton files in place makes every subsequent launch die immediately.

## Step 2 — launch on the copy (macOS)

```bash
# Pick any free port. It is a free choice, not a fixed constant — 9222/9223
# collide with an already-running debug Chrome often enough to matter, and
# 9222 is also agent-browser's default. Check first, then use.
PORT=9223   # <-- choose freely
lsof -nP -iTCP:$PORT -sTCP:LISTEN >/dev/null 2>&1 && { echo "port $PORT busy, pick another"; exit 1; }

"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --remote-debugging-port="$PORT" \
  --headless=new \
  --user-data-dir="$WORK/profile" \
  --profile-directory="Default" \
  --safebrowsing-disable-download-protection \
  --disable-features=InsecureDownloadWarnings
```

Run it as a **tracked background process** (Hermes `terminal(background=true)`),
not with `nohup`/`&` — a detached Chrome escapes cleanup and holds the port.

## Step 3 — verify before trusting it

```bash
curl -s --max-time 3 "http://127.0.0.1:$PORT/json/version"
```

Then confirm the copy actually carries the logins — the whole point of the
exercise. Counts must match the source profile:

```bash
sqlite3 "$WORK/profile/Default/Cookies" "select count(*) from cookies;"
sqlite3 "$HOME/Library/Application Support/Google/Chrome/Default/Cookies" "select count(*) from cookies;"
```

## Verify it yourself before trusting it

```bash
bash scripts/verify.sh              # full flow: copy -> launch -> CDP -> cleanup
bash scripts/negative-control.sh    # proves the Singleton pitfall is real
```

`verify.sh` copies the real profile, checks the auth DBs are present and the
cookie count matches the source, launches, checks `/json/version`, checks
`PUT /json/new` returns 200, and confirms the system browser is still running.
It never touches the real profile and scopes its own `pkill` to its own
scratch dir.

`negative-control.sh` is the part that matters for trust: it copies **without**
the `Singleton*` exclusion and asserts Chrome dies. Measured 2026-09-30: 3
singleton files copied -> `Failed to create .../SingletonLock` ->
`Aborting now to avoid profile corruption`. If that script ever prints
`SURVIVED`, the pitfall section of this skill is wrong and must be corrected.

Reference numbers from that run: 4.8 GB profile -> 4.2 GB copy in ~23 s,
1030 cookies copied and matching, CDP listening ~1 s after launch.

## Step 4 — drive it

See the `chrome-devtools-protocol` skill for CDP domains and a dependency-free
WebSocket client. One gotcha when opening a target from a script: Chrome 111+
requires **PUT** for `/json/new`, a GET returns `405 Method Not Allowed`.

## Cleanup

```bash
pkill -f "$WORK/profile"     # stop the copy, never the system browser
rm -rf "$WORK"               # 4+ GB per session
```

Verify the system browser survived: `pgrep -x "Google Chrome"` should still list
your own windows. If it does not, you launched the wrong binary or the wrong
profile dir — that is the failure this whole procedure exists to prevent.

## Windows

Same three steps, different paths and quoting. `%LOCALAPPDATA%` instead of
`~/Library/Application Support`, `Copy-Item` / `robocopy` instead of `rsync`,
and the binary lives at `%ProgramFiles%\Google\Chrome\Application\chrome.exe`.

```powershell
$WORK = "$env:LOCALAPPDATA\Temp\hermes-chrome-real-$(Get-Random)"
New-Item -ItemType Directory -Force -Path "$WORK" | Out-Null

# robocopy: /E recurse, /XD exclude dirs, /XF exclude files
# NOTE: robocopy exit codes 0-7 are SUCCESS, >=8 are failures.
robocopy "$env:LOCALAPPDATA\Google\Chrome\User Data" "$WORK\profile" `
  /E /R:1 /W:1 `
  /XD Cache "Code Cache" GPUCache ShaderCache component_crx_cache Crashpad `
      "Service Worker\CacheStorage" "Service Worker\ScriptCache" `
  /XF SingletonLock SingletonCookie SingletonSocket DevToolsActivePort
if ($LASTEXITCODE -ge 8) { throw "robocopy failed with $LASTEXITCODE" }

# the singleton files may already exist if a previous copy was reused
Remove-Item "$WORK\profile\Singleton*","$WORK\profile\DevToolsActivePort" -Force -ErrorAction SilentlyContinue

$port = 9223   # <-- choose freely
$busy = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
if ($busy) { throw "port $port already in use" }

Start-Process -FilePath "$env:ProgramFiles\Google\Chrome\Application\chrome.exe" `
  -ArgumentList @(
    "--remote-debugging-port=$port",
    "--headless=new",
    "--user-data-dir=$WORK\profile",
    "--profile-directory=Default",
    "--safebrowsing-disable-download-protection",
    "--disable-features=InsecureDownloadWarnings"
  )
```

Differences that actually bite on Windows:

- **`$env:TMP` is session-scoped and tiny.** A 4 GB profile will not fit in the
  default temp; put `$WORK` on a real volume or the copy silently truncates.
- **`Get-NetTCPConnection` needs no admin**, but `netstat -ano | findstr :$port`
  works everywhere if the cmdlet is missing (older Server Core images).
- **Cookies are DPAPI-encrypted and bound to the user account AND the machine.**
  A copy is readable by the same user on the same machine, which is the intended
  case. A copy moved to another machine decrypts to nothing — do not report
  "logged out" as a bug there.
- **Path quoting**: `--user-data-dir=$WORK\profile` must be a single argument.
  If `$WORK` contains spaces, wrap the whole `--user-data-dir=` value in
  escaped quotes or Chrome silently starts with the default profile.

## Linux

```bash
WORK="$HOME/.cache/hermes/chrome-real-$(date +%s)"
mkdir -p "$WORK"
rsync -a --delete \
  --exclude='Cache' --exclude='Code Cache' --exclude='GPUCache' \
  --exclude='Singleton*' --exclude='DevToolsActivePort' \
  "$HOME/.config/google-chrome/" "$WORK/profile/"

google-chrome --remote-debugging-port=9223 --headless=new \
  --user-data-dir="$WORK/profile" --profile-directory=Default \
  --safebrowsing-disable-download-protection \
  --disable-features=InsecureDownloadWarnings
```

On Linux, `snap`-installed Chrome is confined and cannot read
`~/.config/google-chrome` cleanly; use the `.deb`/`.rpm` build or a flatpak
profile path instead.

## What the flags do and do not buy you

`--safebrowsing-disable-download-protection` and
`--disable-features=InsecureDownloadWarnings` suppress the two interstitials
that otherwise block a scripted download from an unfamiliar host. They are
**download-policy bypasses on a throwaway copy** — never launch the user's
system browser with them, and never reuse this profile for anything the user
did not ask for.

## Pitfalls that cost real time

- **Do not skip the copy "because it's only a read".** A read still opens the
  DBs, and headless Chrome still rewrites `Preferences`, `History` and
  `Local State` on exit. The user's browser must not see that.
- **Do not reuse a scratch dir across sessions.** `--delete` plus the singleton
  cleanup makes that safe, but a stale `Local State` can carry a dead
  `--remote-debugging-port` decision forward. Fresh dir per session.
- **`--profile-directory=Default`** is what makes the copy behave like the real
  profile. Omitting it lands on `Profile 1` and looks "logged out" for a reason
  that has nothing to do with cookies.
- **macOS TCC**: reading `~/Library/Application Support/Google/*` can fail with
  `EPERM` rather than a file lock. That is Full Disk Access, not a lock — see
  the `hermes-real-profile-browser` skill for the probe that tells them apart.
- **`--headless=new` is required**, not optional. Old headless has no
  `Page.navigate` fidelity and breaks login redirects.
