#!/usr/bin/env bash
# Negative control for the chrome-real-profile-launch skill.
#
# The skill claims that copying Singleton* into the scratch profile makes the
# launch die with "Aborting now to avoid profile corruption". This proves it by
# copying WITHOUT the exclusion and checking whether Chrome survives.
#
# If this reports SURVIVED, the skill's pitfall section is wrong.
set -uo pipefail

PORT=9232
WORK="$(mktemp -d "${TMPDIR:-/tmp}/negctl.XXXXXX")"
trap 'rm -rf "$WORK"' EXIT

rsync -a --delete \
  --exclude='Cache' --exclude='Code Cache' --exclude='GPUCache' \
  --exclude='ShaderCache' --exclude='GraphiteDawnCache' \
  --exclude='Crashpad' --exclude='component_crx_cache' \
  --exclude='Service Worker/CacheStorage' --exclude='Service Worker/ScriptCache' \
  "$HOME/Library/Application Support/Google/Chrome/" "$WORK/profile/" >/dev/null 2>&1

count=$(ls "$WORK/profile/" | grep -ci singleton)
echo "singleton files copied: $count"

"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --remote-debugging-port="$PORT" --headless=new \
  --user-data-dir="$WORK/profile" --profile-directory="Default" \
  > "$WORK/log" 2>&1 &
PID=$!
sleep 8

if kill -0 "$PID" 2>/dev/null; then
  echo "NEGCTRL: chrome SURVIVED -> the skill's pitfall claim is WRONG"
  pkill -f "$WORK/profile"
  exit 1
fi
echo "NEGCTRL: chrome DIED, as the skill claims"
grep -oE 'Aborting now to avoid profile corruption|Failed to create [^ ]*Singleton[A-Za-z]*' \
  "$WORK/log" | sort -u
exit 0
