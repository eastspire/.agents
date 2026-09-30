---
name: brew-install-on-mac
description: Install Homebrew via Terminal.app when brew is missing.
---

# Install Homebrew from Hermes TUI

Use when the user says `brew install ...`, `brew cask ...`, `install brew`, or asks for software normally installed via Homebrew Cask (Warp, Rectangle, AltTab, etc.) and `brew` is not yet on PATH (`which brew` returns nothing, `/opt/homebrew/bin/brew` absent).

## Why this needs a special path

The official install script (raw.githubusercontent.com/Homebrew/install/HEAD/install.sh) requests sudo to write to /opt/homebrew. On macOS the sudo prompt is a GUI authentication box that only appears when the script runs under a TTY. Hermes background terminal sessions have no TTY, so:

- With NONINTERACTIVE=1 the script self-rejects ("Need sudo access on macOS!").
- Without that var it still exits 1 ("stdin is not a TTY").
- Setting SUDO_PASSWORD in ~/.hermes/.env works but the user will rightly not want a password on disk.

The clean path is to launch the script inside the user's actual Terminal.app, where the GUI auth box renders and Touch ID works.

## Procedure

1. Confirm brew is missing: which brew empty, /opt/homebrew does not exist.
2. Sanity-check admin rights: id sqs | grep -q admin.
3. Launch in Terminal.app via osascript do script, then activate.
4. Tell the user to authenticate in the Terminal window. Brew install takes 5 to 10 min (longer if Xcode CLT also needs to install).
5. After user confirms brew is installed, prepend the brew shellenv eval to the same shell BEFORE invoking brew: `eval "$(/opt/homebrew/bin/brew shellenv)"`. Without this, `brew install --cask ...` fails with command not found even though `/opt/homebrew/bin/brew` exists. The eval line that the installer appends to ~/.zprofile only takes effect in new shells. Then run the originally requested cask.

## Verification

- brew --version returns a version
- /opt/homebrew/bin/brew exists
- ~/.zprofile contains the eval brew shellenv line brew appends

## Things that look correct but fail

- brew install --cask warp directly: brew command not found.
- curl-downloading app.warp.dev/download with or without cookies: server returns HTML, file header is zlib compressed data (broken). Use App Store or Homebrew Cask, never bare curl for Warp.
- Running the brew install script in a Hermes background job with or without NONINTERACTIVE: always exits 1 before any sudo prompt can render.