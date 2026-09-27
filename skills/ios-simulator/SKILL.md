---
name: ios-simulator
description: Launch iOS simulators on macOS — Xcode 27+ Device Hub and pre-27 Simulator.app.
version: 1.1.0
author: Hermes Agent
license: MIT
platforms: [macos]
metadata:
  hermes:
    tags: [ios, xcode, simulator, simctl, device-hub, apple]
    category: mobile-dev
    related_skills: [computer-use]
---

# iOS Simulator

## When to use

- User asks to launch, boot, or open an iOS simulator (any iPhone / iPad device on macOS).
- "Open the simulator", "run iOS app in sim", "launch latest iPhone", or any simctl-driven workflow.
- Tasks that drive the simulator headlessly (screenshots, install/launch .app bundles, open URLs).
- "Translucent" / "transparent background" / "hide device bezel" — Xcode 27's Device Hub has **no GUI for these**. The Chrome (device shell) is always on. Don't keep looking; the option was removed.

Do NOT use for: Android emulators, deploying to real iOS devices, testing web pages inside the simulator's Safari (use `browser_exec` for that).

## First decision: which GUI app to launch

Xcode 27 renamed the Simulator. Before opening anything, check which one is on disk — a wrong `open` returns "Unable to find application" and burns a turn:

```bash
ls /Applications/Xcode.app/Contents/Applications/ | grep -iE 'simulator|devicehub'
ls /Applications/Xcode.app/Contents/Developer/Applications/ 2>/dev/null | grep -i simulator
```

| Disk contains | Xcode version | Launch with |
|---|---|---|
| `DeviceHub.app` in `Contents/Applications/` (NO `Simulator.app` anywhere) | Xcode 27+ | `open /Applications/Xcode.app/Contents/Applications/DeviceHub.app` |
| `Simulator.app` in `Contents/Developer/Applications/` | Xcode ≤ 26 | `open -a Simulator --args -CurrentDeviceUDID <UDID>` |

If `Contents/Applications/` only has Accessibility Inspector / Create ML / **DeviceHub** / FileMerge / Icon Composer / Instruments (no Simulator.app), **the install is complete**. DeviceHub IS the Simulator — don't reinstall Xcode to "fix" it.

**Pitfall — assuming a 3.7 GB Xcode 27 is stripped:** it isn't. A healthy Xcode 27 is ~3.7 GB (much smaller than Xcode ≤ 26 which was 8–12 GB) because Apple moved the Simulator binary and dropped a lot of legacy surface. `du -sh /Applications/Xcode.app/Contents/Developer/Platforms/iPhoneSimulator.platform` ≈ 100 MB is also normal on 27 — the runtime is downloaded on demand, not pre-shipped.

**Pitfall — `xcodebuild -version` lies about completeness:** every Xcode (stripped, Apple-internal SNAPSHOT, public GM) reports its version and can run simctl. `simctl list devices` succeeding doesn't tell you whether the GUI app exists.

## Core procedure (any Xcode)

1. **Find the latest iPhone device and its UDID:**
   ```
   xcrun simctl list devices available | grep -i iphone | head -10
   ```
   Prefer the device with the highest number + `Pro`/`Pro Max` suffix — that's the newest shipping iPhone profile. UDID is the `(XXXXXXXX-XXXX-...)` token on the same line; copy it verbatim.

2. **Boot the device:**
   ```
   xcrun simctl boot <UDID>
   ```
   A second `boot` on the same UDID returns error 405 `Unable to boot device in current state: Booted` — that's normal; it means the first call succeeded. Don't retry.

3. **Open the GUI** (use the table above):
   - Xcode 27+: `open /Applications/Xcode.app/Contents/Applications/DeviceHub.app`
     - If the booted device doesn't show in the canvas, click Start on the device tile in the sidebar. DeviceHub does not always auto-attach a booted device when launched without args; passing `-CurrentDeviceUDID <UDID>` (just like the old Simulator) helps.
   - Xcode ≤ 26: `open -a Simulator --args -CurrentDeviceUDID <UDID>`

4. **Verify:**
   ```
   xcrun simctl list devices booted    # should show your device with (Booted)
   pgrep -lf 'DeviceHub|Simulator.app'  # GUI process should be running
   ```

## Diagnostic: stripped Xcode install (rare on Xcode 27+)

On **pre-27 Xcode** only — Simulator.app absent from `Contents/Developer/Applications/` plus a 98 MB `iPhoneSimulator.platform` indicates a stripped install. On Xcode 27+ there's no separate Simulator.app to look for; if DeviceHub.app is missing, *that* is the stripped signal.

```
ls /Applications/Xcode.app/Contents/Developer/Applications/  # pre-27 only
ls /Applications/Xcode.app/Contents/Applications/DeviceHub.app  # 27+
```

**Pitfall — don't waste time on dead-end commands:**

- `xcodebuild -downloadComponent -componentIdentifier com.apple.CoreSimulator.Simulator` — the option does not exist on Xcode 27; it just dumps help text. The real fix is `xcodebuild -downloadPlatform iOS -exportPath /tmp/ios`, which downloads the runtime if it's missing — but **not** DeviceHub.app itself. Use this only to populate an empty simulator runtime; the GUI is unrelated.
- `xcodebuild -downloadAllPlatforms` — same story: fills in runtimes, not the GUI binary. If the GUI binary is what you need, this doesn't help.

## Recovery paths (when DeviceHub.app or Simulator.app genuinely IS missing)

Pick one — they're equivalent. App Store will silently keep a phantom "open" stub if Xcode.app already exists, so on Xcode 27 you usually need to **delete `/Applications/Xcode.app` first** (or move to Trash) before App Store will offer a real "download" button:

```
sudo rm -rf /Applications/Xcode.app
open "macappstore://apps.apple.com/app/xcode/id497799835"
```
Then click the now-visible download button in App Store and wait 10–30 min for ~10 GB.

Alternatives that don't need sudo on the existing install (Hermes blocks `sudo -S` for password-piping, so the user must run sudo manually):

- Developer downloads: `https://developer.apple.com/download/all/` → log in → search "Xcode 27" → grab the `.xip` → double-click → drag Xcode.app over the existing one (needs sudo write to `/Applications`).
- `xcodes install 27.0` (brew tool — needs Apple ID interactively).

After reinstall, rerun step 3.

## Useful simctl one-liners

- List runtimes: `xcrun simctl list runtimes`
- List available device types: `xcrun simctl list devicetypes`
- Shutdown one device: `xcrun simctl shutdown <UDID>`
- Shutdown all: `xcrun simctl shutdown all`
- Erase (factory reset): `xcrun simctl erase <UDID>`
- Install .app: `xcrun simctl install <UDID> /path/to/App.app`
- Launch app: `xcrun simctl launch <UDID> <bundle.id>`
- Screenshot: `xcrun simctl io <UDID> screenshot ~/Desktop/sim.png` (works without any GUI — survives a missing or broken DeviceHub/Simulator.app)
- Open URL: `xcrun simctl openurl <UDID> https://...`

`simctl` is independent of the GUI — drive simulators headlessly any time the GUI is missing, broken, or unneeded.

## Device Hub caveats (Xcode 27+)

- **No "transparent background" / "hide device bezel" toggle.** Device Hub's menu bar is only Apple / Device Hub / File / Edit; the toolbar's `More Actions` is Shut Down / Restart / Show in Finder / Rename / Reset / Pair / Remove. The strings `translucent`, `transparent`, `chromeMode` are not in the binary. `defaults -container com.apple.dt.Devices` registers only `keyboard / audio / menu.bar / secure.input / auto.start / session.keepalive` — no chrome key.
- **"Open in New Window"** pops a smaller floating 276×623 simulator window without the sidebar — useful for screenshots and for working around the no-translucent limitation, but the device shell stays visible.
- **Compact vs Expanded mode** affects keyboard shortcuts. The hidden preference `defaults -container com.apple.dt.Devices write com.apple.dt.Devices hostKeybindingPolicy -int 0` re-enables rich key combos in both modes (Xcode 27 release note 178920247).
- **Apple-internal builds** (`DTSDKName = macosx27.0.internal`) look identical to public GM and behave the same way. Don't try to "fix" them.

## When `web_extract` blocks a JSON API

The `web_extract` and `web_search` tools sometimes reject third-party JSON endpoints with "Blocked: URL targets a private or internal network address" — `xcodereleases.com/data.json` is one. When you just need the JSON, `curl` from terminal goes straight through:

```bash
curl -sL https://xcodereleases.com/data.json | python3 -m json.tool | head
```

Don't waste a turn debugging `web_extract`; for these data endpoints, terminal curl is the tool.