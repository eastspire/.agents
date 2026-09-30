---
name: chrome-real-profile-launch
description: "Use when browser automation must run with the user's REAL Chrome logins. Always go through scripts/run.sh — it stops previous CDP browsers, force-overwrites the scratch copy, and launches Chrome. Never drive the system profile directly."
version: 2.0.0
author: local
license: MIT
platforms: [macos, linux, windows]
metadata:
  hermes:
    tags: [chrome, cdp, browser-automation, real-profile, logins, headless, remote-debugging, cookies, authenticated, script-driven]
    related_skills: [chrome-devtools-protocol, hermes-real-profile-browser, blocked-page-recovery, inspecting-hermes-desktop-dom]
---

# Chrome on a COPY of the real profile

## THE RULE

**Every** browser operation that needs the user's real logins goes through
`scripts/run.sh`. There is no other supported path.

Three requirements, all mandatory, all enforced by that script:

1. **Never drive the real profile directory.** It is only ever read.
2. **Never start without stopping the previous CDP browser.** A stale instance
   holds both the port and the profile's singleton lock, so the new launch dies
   or silently attaches to the old process.
3. **Never merge into an existing scratch copy.** The directory is deleted and
   rebuilt, because an in-place sync leaves the singleton files and a
   `Local State` carrying the previous run's decisions.

## Use it

```bash
S="$HOME/.agents/skills/software-development/chrome-real-profile-launch/scripts"

bash "$S/run.sh"                  # auto-pick a free port
bash "$S/run.sh" --port 9223      # explicit port
bash "$S/run.sh" --work /path/dir # custom scratch dir
bash "$S/run.sh" --headed         # visible window instead of headless
bash "$S/run.sh" --stop           # just stop CDP browsers, copy nothing
bash "$S/run.sh" --keep           # reuse the existing copy, skip step 2
```

`run.sh` exits 0 only after CDP answers, and prints the browser version. It
refuses to launch if the copy is missing `Default/Cookies`, and it detects the
singleton failure explicitly rather than timing out.

Port selection is automatic and free to override: `run.sh` scans 9223-9228 for
a free port because 9222 is agent-browser's default and collides often. The
port is only yours to choose — there is no fixed constant.

## What run.sh does, in order

| Step | Action | Why it is not optional |
|---|---|---|
| 1 | `stop-cdp.sh` — TERM every process whose command line carries `--remote-debugging-port`, then KILL whatever ignores TERM | A previous instance holds the port and the singleton lock |
| 2 | `rm -rf "$WORK"` then rebuild by copy | An in-place sync keeps `Singleton*` and a stale `Local State` |
| 3 | Launch Chrome on the copy, wait for `DevTools listening` in the log **and** a working `curl` | A fixed sleep is wrong: a busy machine after killing a 4 GB instance outlives any guess |
| 4 | Refuse to start if `Default/Cookies` is absent | Copy failures otherwise show up much later as "logged out" |

`stop-cdp.sh` matches on the debug flag in the process arguments, so the user's
own Chrome is never a candidate. It is safe to run at any time.

## Stopping and cleaning up

```bash
bash "$S/stop-cdp.sh"                 # stop every CDP browser
bash "$S/stop-cdp.sh" --port 9223     # only that port
rm -rf ~/.hermes/cache/scratch/chrome-real-profile   # ~4 GB
```

Confirm the user's browser survived: `pgrep -f "Google Chrome.app/Contents"` must
still list their windows.

## Drive it

Use the `chrome-devtools-protocol` skill for CDP domains and a dependency-free
WebSocket client. One gotcha: Chrome 111+ requires **PUT** for `/json/new`;
a GET returns `405 Method Not Allowed`.

```bash
curl -s http://127.0.0.1:9241/json/version     # health
curl -s -X PUT "http://127.0.0.1:9241/json/new?about:blank"
```

## Verify the skill itself

```bash
bash "$S/verify.sh"              # full flow, 16 checks
bash "$S/negative-control.sh"    # proves the Singleton pitfall is real
```

`negative-control.sh` is the part that makes the pitfall section falsifiable: it
copies **without** the `Singleton*` exclusion and asserts Chrome dies. If it ever
prints `SURVIVED`, this skill is wrong and must be corrected.

Measured 2026-09-30 on macOS / Chrome 154.0.8037.58: 4.8 GB profile -> 4.2 GB
copy in ~23 s, 1031 cookies copied and matching the source, CDP ready ~2 s after
launch, and a second `run.sh` on the same port correctly killed 4 processes,
removed a planted `STALE_MARKER` (force-overwrite), and came back ready.

## The pitfalls, and what they cost

- **Copying `Singleton*` kills the launch.** Three files, then
  `Failed to create .../SingletonLock` -> `Aborting now to avoid profile
  corruption`. Hit on the first attempt of this skill's own creation.
- **"It's only a read, I can skip the copy."** No — headless Chrome still
  rewrites `Preferences`, `History` and `Local State` on exit, which is exactly
  what the user's live session must not see.
- **Merging into yesterday's copy.** `rsync --delete` into an existing dir keeps
  the singleton files. `run.sh` deletes the directory first for this reason.
- **Omitting `--profile-directory=Default`.** Chrome lands on `Profile 1` and
  looks logged out for a reason that has nothing to do with cookies.
- **A fixed readiness sleep.** After `stop-cdp` frees 4 GB of memory the machine
  is busy; poll the log's `DevTools listening` line instead.
- **A boolean guard read backwards.** `if [ "$READY" -ne 0 ]` reports failure
  when `READY=1` means success — it failed the whole flow twice before a `bash -x`
  trace showed `[ 1 -ne 0 ]` returning true. When a readiness flag is involved,
  trace the guard once.
- **macOS TCC.** Reading `~/Library/Application Support/Google/*` can fail with
  `EPERM` rather than a file lock — that is Full Disk Access. See
  `hermes-real-profile-browser` for the probe that tells the two apart.

## What the flags buy you

`--safebrowsing-disable-download-protection` and
`--disable-features=InsecureDownloadWarnings` suppress the two interstitials
that otherwise block a scripted download from an unfamiliar host. They are
**download-policy bypasses on a throwaway copy**. Never launch the user's system
browser with them, and never reuse this profile for anything they did not ask
for.

## Windows and Linux

`run.sh` detects the platform and takes the matching branch — the same three
steps, different paths and tools. It has **only been executed on macOS**; the
Windows and Linux branches are written from the equivalent semantics and are
marked unverified in this skill rather than presented as tested.

- **Windows**: `%LOCALAPPDATA%\Google\Chrome\User Data` -> `robocopy /E /XD /XF`
  (exit codes 0-7 are success, >=8 are failures), process matching through
  `Get-CimInstance Win32_Process` filtered on the command line, and
  `Start-Process` for launch. `$WORK` must be on a real volume — a 4 GB profile
  does not fit in the default `%TEMP%` and truncates silently. Cookies are
  DPAPI-encrypted and bound to **user AND machine**: a copy moved to another
  machine decrypts to nothing, so do not report "logged out" as a bug there.
  A `--user-data-dir=` path containing spaces must arrive as one argument.
- **Linux**: `~/.config/google-chrome`, plain `rsync`, `google-chrome`.
  A `snap`-installed Chrome is confined and cannot read that directory cleanly —
  use the deb/rpm build or a flatpak profile path.
