---
name: chrome-real-profile-launch
description: "Use when browser automation must run with the user's REAL Chrome logins. Always go through scripts/run.sh — it reuses one shared Chrome instance across sessions (new tab, never a relaunch) and only cold-starts when none is healthy. Never drive the system profile directly."
version: 3.0.0
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

Four requirements, all mandatory, all enforced by that script:

0. **One shared instance per machine, one port, one tab per caller.** Several
   Hermes sessions need the browser at once. They must not each start their
   own — see "Concurrent sessions" below.

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

bash "$S/run.sh"                          # reuse or start; opens a tab
bash "$S/run.sh" https://example.com      # same, on a given URL
bash "$S/run.sh" --no-tab                 # just make sure one is running
bash "$S/run.sh" --port 9223              # pin the shared port
bash "$S/run.sh" --work /path/dir         # custom scratch dir
bash "$S/run.sh" --status                 # report, change nothing
bash "$S/run.sh" --headed                 # visible window
bash "$S/run.sh" --fresh                  # force a clean start
bash "$S/run.sh" --stop                   # stop the shared instance
```

`run.sh` exits 0 only after a browser is actually serving the request, and
prints the browser version. It refuses to launch if the copy is missing
`Default/Cookies`, and it detects the singleton failure explicitly rather than
timing out.

**Calling it twice is the normal case, not an error.** The first call starts
the shared instance; every later call reuses it and returns a new tab. Do not
"clean up" a browser you are about to reuse, and do not call `stop-cdp.sh`
because you finished one piece of work while another session is mid-task.

Port selection is automatic and free to override: the first launch scans
9223-9228 and then publishes its choice to
`~/.hermes/state/chrome-real-profile.port`, so later sessions join that same
port instead of starting a second browser. 9222 is skipped because it is
agent-browser's default and collides often.

## Concurrent sessions

Sessions share a browser. They do not each get one.

| Situation | What `run.sh` does |
|---|---|
| An instance is already healthy | Opens a new tab. Nothing is stopped, copied or relaunched. |
| No instance, several sessions arrive at once | Exactly one takes the lock and cold-starts; the others wait, then find it ready and open a tab. |
| A session wants a clean state | Pass `--fresh` explicitly, knowing it evicts every other session's tabs. |

The `mkdir` lock covers the start path because "check, then start" is a race:
without it, two sessions both see nothing and each `rm -rf` the other's
half-built profile. A lock older than 10 minutes is treated as abandoned and
cleared, so a killed process cannot wedge every future session.

Each call gets its own tab, so two sessions never fight over one page. Tabs
accumulate — a session that opened twenty leaves twenty. Close tabs via CDP
(`/json/close/<targetId>`) rather than restarting the browser, because
restarting is exactly what disrupts the other sessions.

Measured with 4 concurrent sessions from cold: 1 performed the start, 3 waited
and reused, the profile was copied once, one port was in use, and 4 tabs
existed. A second wave of 4 all reused, took no new port, and grew the target
count instead.

## What run.sh does, in order

Only when no healthy instance exists. If one does, none of this runs.

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
bash "$S/verify.sh"                 # full flow, 16 checks
bash "$S/concurrency-test.sh 4      # 4 sessions race for one instance
bash "$S/negative-control.sh"       # proves the Singleton pitfall is real
```

`concurrency-test.sh` is what keeps the sharing claim honest. It fires N
sessions simultaneously from cold and fails unless exactly one did the start,
the profile was copied once, only one CDP port is in use, the state file
agrees, and a second wave reuses the same pid. If it ever reports two cold
starts, the lock has regressed.

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
- **Treating a live instance as something to clean up.** Stopping it because
  *your* task finished pulls the ground out from under every other session.
  The lifecycle is the shared instance's, not the caller's.
- **Tabs as a shared resource.** Each session gets its own tab; they are not
  reused across sessions, and a long session leaves them behind. Close them
  over CDP.
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
