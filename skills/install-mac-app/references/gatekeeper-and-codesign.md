# Gatekeeper, quarantine, and first-launch errors

## The default problem

When you copy a `.app` from a mounted DMG into `/Applications`, macOS applies the `com.apple.quarantine` extended attribute to the new files. On first launch, Gatekeeper intercepts with an "unidentified developer" dialog and refuses to open the app — even if the binary IS signed by a Developer ID.

Always strip the quarantine immediately after copy:

```bash
xattr -dr com.apple.quarantine /Applications/<App>.app
```

`xattr -d` deletes a single attribute; `-r` recurses; combining `-dr` is the standard one-liner.

## Confirming the signature survived

```bash
codesign -dv /Applications/<App>.app/Contents/MacOS/<bin>
```

Look for:
- `Identifier=org.<vendor>.<app>` — present
- `Format=app bundle with Mach-O thin (arm64)` — correct arch
- `Authority=Developer ID Application: <Vendor> (...)` — notarized by Apple
- `Signature size=...` — non-zero

If `codesign` reports `code object is not signed at all`, the signature may have been stripped during copy (rare on `/Applications`, common on network shares) — re-download and verify with `hdiutil verify`.

## When the app still won't launch

Likely culprits, in order:
1. macOS version too old (check `<App>.app/Contents/Info.plist` `LSMinimumSystemVersion`).
2. Rosetta missing for an x64-only build on arm64: `softwareupdate --install-rosetta`.
3. Notarization revoked — check `spctl -a -t exec -vv /Applications/<App>.app`; if rejected, the app needs a re-download from the vendor.
4. SIP blocking a privileged path — `/Applications` is fine; `/usr/local` is not always.