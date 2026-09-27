---
name: hermes-real-profile-browser
description: "Use when Hermes browses with your real Chrome logins."
version: 1.0.0
author: local
license: MIT
platforms: [macos]
metadata:
  hermes:
    tags: [hermes, browser, chrome, tcc, security, real-profile]
---

# Hermes real-profile browsing (agent acts as you, on your real Chrome)

## When to use

- Configuring `browser.use_real_profile` so the agent browses with the user's real Chrome
  logins instead of a throwaway profile.
- A real-profile session fails with "[profile-locked] ... quit your browser".
- Checking whether saved passwords / cookies are actually present in the snapshot at
  `~/.hermes/browser-profile/`.

`browser.use_real_profile: true` makes the agent browse with your real logins instead of
a throwaway profile. It works by **snapshotting** the active profile of your OS default
Chromium into `~/.hermes/browser-profile/<browser>/`, launching your **real browser
binary** on that copy, and attaching agent-browser over CDP.

```bash
hermes config set browser.use_real_profile true
hermes config set browser.engine chrome     # don't fall back to lightpanda
```
Tool changes take effect on the **next session** (`/reset`), never mid-conversation.

Why the real binary and not a bundled Chromium: the launch must NOT carry
`--use-mock-keychain` / `--password-store=basic`, or macOS Chrome silently drops every
keychain-encrypted cookie and the session opens signed out. Your live profile is never
driven directly — the snapshot is a separate dir, so it never fights your running browser
for the lock and sidesteps Chrome 136+'s block on remote-debugging the default profile.

## The three things that bite

### 1. "[profile-locked] ... quit your browser" is often NOT a lock

On macOS this message is frequently a **TCC denial disguised as a file lock**.
`hermes_cli/browser_connect.py::_profile_is_locked()` maps *any* `PermissionError` to
"locked, quit Chrome and retry" — and macOS 27's App Data protection gives
`~/Library/Application Support/Google/*` an EPERM that looks identical.

Tell them apart before telling the user to close anything:

| Probe | Real file lock | TCC denial |
|---|---|---|
| `stat` the path | fails only if missing | **succeeds**, mode is your own `drwx------` |
| `open()` it | `EBUSY` / `database is locked` | `EPERM` (errno 1), "Operation not permitted" |
| `xattr -l` | works | refused |

Fix for TCC: **Warp** (or whatever terminal hosts the agent) needs **Full Disk Drive
Access** — System Settings → Privacy & Security → Full Disk Access → add the app, then
fully quit and reopen it. `tccutil` can only reset, never grant. If the agent runs under
a launchd gateway instead of a terminal app, the *gateway's* host app needs it too.

### 2. There is NO built-in password boundary — install the purge plugin

Stock `use_real_profile` copies `Login Data`, `Login Data For Account` and `Web Data`
(saved passwords + the encryption keys that make them recoverable + credit cards) into
the snapshot, and nothing stops the agent reading them back: Chrome autofill fills a
page's password field, and `browser_console` can read `input[type=password].value`. That
plaintext then sits in the conversation and goes to the model provider every turn.

Upstream docs are explicit that the toggle is *"a consent-gated convenience, not an
isolation boundary"*. So supply the boundary yourself.

`~/.hermes/plugins/no-password-exposure/` (enabled, verified) does it in two layers:

1. **Primary** — `pre_tool_call` purges the password stores out of
   `~/.hermes/browser-profile/<browser>/`. It runs on **every** browser call, not just
   the first: upstream re-syncs auth files on *every fresh session launch*, so a one-shot
   purge is silently undone.
2. **Defense-in-depth** — `transform_tool_result` redacts password/card/OTP shapes from
   any tool result (Luhn-checked so real card numbers are caught and long ids are not).

Purge keeps `Cookies`, `Network/Cookies` and `Preferences`, so the agent keeps its real
logins — that is the whole point of the feature. Kill switch: `NO_PASSWORD_EXPOSURE_DISABLE=1`.

**What it does not fix:** the agent still acts *as you*, so a malicious page can still
drive a filled form. Redaction is a net, not a guarantee. Don't over-promise it.

### 3. Auth DBs need a fully quit browser

`Cookies` snapshots fine while Chrome runs. `Login Data` may too. But `Web Data` and
`Login Data For Account` are typically held with a hot write lock, and Hermes fails
closed rather than raw-copying (a raw copy can lose committed logins). So: quit the
browser before the first real-profile launch, reopen after. `hermes browser
close-profile` does it, but it is DESTRUCTIVE (loses unsaved tabs) and the agent must
ask first. `browser.real_profile_autoclose: true` only arms the *offer*.

## Verify like this, not by "config looks right"

```bash
cd ~/.hermes/hermes-agent && ./venv/bin/python - <<'PY'
import sys; sys.path.insert(0, ".")
from hermes_cli.browser_connect import detect_default_chromium, snapshot_real_profile
b = detect_default_chromium()
dst, err = snapshot_real_profile(b)
print(b, "->", dst or f"FAILED: {err}")
PY
```
Then confirm the secrets are actually gone and the cookies survived:
```bash
ls ~/.hermes/browser-profile/chrome/Default/ | grep -iE "login data|web data"  # must be empty
ls ~/.hermes/browser-profile/chrome/Default/Cookies                           # must exist
```

Note the snapshot dir is written with umask-wide perms on first pass (`-rw-r--r--` on
`Login Data`) before `_secure_snapshot(contents=True)` heals it — a brief window where a
password file is world-readable. Purge it if a failed session left one behind.
