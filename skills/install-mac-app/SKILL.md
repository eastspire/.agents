---
name: install-mac-app
description: Install macOS GUI apps from DMG/ZIP outside the App Store.
---

# Install a third-party macOS GUI app from DMG/ZIP

When the user wants an app that ships outside the App Store and outside `brew install --cask`, install it from the vendor's official mirror directly to `/Applications`. Prefer 4.x/5.x LTS branches when available — they keep working when "latest" breaks.

## Procedure

1. **Detect arch.** Run `uname -m`. arm64 → pick the arm64/silicon build; x86_64 → x64/intel build. arm64 Macs CAN run x86 builds via Rosetta but lose 20–40% perf for nothing.
2. **Probe mirrors with HEAD requests** in parallel before committing to one:
   ```bash
   for url in <vendor-primary> <tsinghua> <aliyun> <clarkson> <dotsrc>; do
     curl -sI --max-time 8 -A "<Safari UA>" "$url" | grep -iE "content-length|HTTP/"
   done
   ```
   Pick the lowest-latency 200 OK. Many vendor primaries (download.blender.org, app.warp.dev) return HTML/302 because JS-rendered redirects don't fire under curl — go straight to a mirror.
3. **Download.** `curl -L -A "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15" -o <out> <url>`. The Safari UA is mandatory — see `references/mirrors-and-ua.md`.
4. **Verify integrity.** No `.sha256` is usually published. Compare `stat -f %z` to the `Content-Length` from step 2's HEAD; `hdiutil verify` for DMGs; for ZIPs, `unzip -t` then check the inner binary's arch with `file` (`Mach-O 64-bit executable arm64`).
5. **Mount → copy → unmount** (DMG only):
   ```bash
   hdiutil attach -nobrowse -quiet <dmg>
   cp -R "/Volumes/<Name>/<App>.app" /Applications/
   hdiutil detach -quiet "/Volumes/<Name>"
   rm <dmg>
   ```
   For ZIPs, just `unzip` and `cp -R` the inner `.app`.
6. **Strip Gatekeeper quarantine** so first-launch isn't blocked by an unidentified-developer dialog:
   ```bash
   xattr -dr com.apple.quarantine /Applications/<App>.app
   codesign -dv /Applications/<App>.app/Contents/MacOS/<bin>  # confirm signature
   ```
7. **Smoke-test by version flag, not GUI launch**:
   ```bash
   /Applications/<App>.app/Contents/MacOS/<bin> --version
   ```
   GUI launch is best left to the user (you can't see their screen in this session, and a stuck splash screen eats turns).

## Standing preferences

- **Don't ask the user to click through GUI wizards.** Do the full install headlessly; tell the user the app is ready and how to launch it (`open /Applications/<App>.app`).
- **Don't accumulate cruft in `~/Downloads`.** `rm` the DMG/ZIP as the last step.
- **Don't skip `xattr -dr com.apple.quarantine`.** Without it, double-click launches hang on Gatekeeper and the user blames the install.
- **Prefer LTS / stable branches.** For Blender that's 4.5 LTS (supported to 2027), not 5.x bleeding-edge.

## Pitfalls

- **Aliyun blocks aria2 entirely** — both `-x16` and `-x1` return HTTP 403. Curl with a Safari UA is the only downloader that works at full speed (~10 MB/s). See `references/mirrors-and-ua.md`.
- **Vendor "download" URLs often 404 under curl** because they require JS. Don't retry the same URL — go to the mirror list directly.
- **`hdiutil verify` is cheap and catches corruption** before you mount a half-written DMG; always run it on anything >100 MB.
- **Don't launch the GUI to "verify it worked"** — the binary's `--version` output is the same signal with no risk of a stuck window.
- **A binary that ships as x64 on an arm64 Mac works but is wrong** — always pick the arm64 build when offered, and confirm with `file`.

## References

- `references/mirrors-and-ua.md` — mirror list and the Safari-UA trick
- `references/gatekeeper-and-codesign.md` — first-launch errors and signature verification