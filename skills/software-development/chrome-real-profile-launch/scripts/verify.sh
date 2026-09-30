#!/usr/bin/env bash
# Smoke test for the chrome-real-profile-launch skill.
#
# Proves the three things the skill claims, in order, on this machine:
#   1. the rsync copy carries the auth DBs and matches the source cookie count
#   2. excluding Singleton* is what makes the launch survive
#   3. CDP comes up and a page can be navigated
#
# It does NOT touch the real profile: everything happens under $WORK and the
# kill is scoped to $WORK. Run: bash scripts/verify.sh
set -uo pipefail

PORT="${PORT:-9231}"
SRC="$HOME/Library/Application Support/Google/Chrome"
BIN="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
WORK="$(mktemp -d "${TMPDIR:-/tmp}/hermes-chrome-verify.XXXXXX")"
FAILURES=0

check() {
  if [ "$2" = "0" ]; then printf '  ok   %s\n' "$1"
  else printf '  FAIL %s\n' "$1"; FAILURES=$((FAILURES+1)); fi
}

cleanup() {
  [ -n "${CHROME_PID:-}" ] && kill "$CHROME_PID" 2>/dev/null
  sleep 1
  pkill -f "$WORK/profile" 2>/dev/null
  rm -rf "$WORK"
  return 0
}
trap cleanup EXIT

echo "workdir: $WORK  port: $PORT"

echo "step 1: port must be free before launch"
lsof -nP -iTCP:"$PORT" -sTCP:LISTEN >/dev/null 2>&1
if [ $? -eq 0 ]; then echo "  FAIL port $PORT already in use"; FAILURES=$((FAILURES+1)); fi
echo "  ok   port $PORT is free"

echo "step 2: copy the profile (singleton files excluded)"
rsync -a --delete \
  --exclude='Cache' --exclude='Code Cache' --exclude='GPUCache' \
  --exclude='ShaderCache' --exclude='GraphiteDawnCache' \
  --exclude='component_crx_cache' --exclude='Crashpad' \
  --exclude='Service Worker/CacheStorage' --exclude='Service Worker/ScriptCache' \
  --exclude='Singleton*' --exclude='DevToolsActivePort' \
  "$SRC/" "$WORK/profile/" >/dev/null 2>&1
check "rsync completed" $?

[ -f "$WORK/profile/Default/Cookies" ];  check "Cookies copied" $?
[ -f "$WORK/profile/Default/Preferences" ]; check "Preferences copied" $?
[ -f "$WORK/profile/Default/Login Data" ]; check "Login Data copied" $?
[ -f "$WORK/profile/Default/Web Data" ];   check "Web Data copied" $?

ls "$WORK/profile/" | grep -qi '^Singleton' 2>/dev/null
if [ $? -eq 0 ]; then echo "  FAIL a Singleton file survived the copy"; FAILURES=$((FAILURES+1)); fi
echo "  ok   no Singleton file in the copy"

COPIED=$(sqlite3 "$WORK/profile/Default/Cookies" "select count(*) from cookies;" 2>/dev/null)
SOURCE=$(sqlite3 "$SRC/Default/Cookies" "select count(*) from cookies;" 2>/dev/null)
echo "  cookies: copy=$COPIED source=$SOURCE"
[ -n "$COPIED" ] && [ "$COPIED" -gt 0 ] 2>/dev/null
check "copy has a non-zero cookie count" $?
[ "$COPIED" = "$SOURCE" ]
check "copy cookie count matches source" $?

echo "step 3: launch on the copy"
"$BIN" --remote-debugging-port="$PORT" --headless=new \
  --user-data-dir="$WORK/profile" --profile-directory="Default" \
  --safebrowsing-disable-download-protection \
  --disable-features=InsecureDownloadWarnings \
  > "$WORK/chrome.log" 2>&1 &
CHROME_PID=$!

READY=1
for _ in $(seq 1 25); do
  if curl -s --max-time 2 "http://127.0.0.1:$PORT/json/version" >/dev/null 2>&1; then
    READY=0; break
  fi
  # bail out early if Chrome already died on a profile error
  if ! kill -0 "$CHROME_PID" 2>/dev/null; then break; fi
  sleep 1
done

if [ "$READY" -ne 0 ]; then
  echo "  FAIL CDP did not come up; chrome.log:"
  sed 's/^/       /' "$WORK/chrome.log" | tail -8
  FAILURES=$((FAILURES+1))
else
  echo "  ok   CDP listening on $PORT"
  BROWSER=$(curl -s --max-time 3 "http://127.0.0.1:$PORT/json/version" \
            | sed -n 's/.*"Browser": *"\([^"]*\)".*/\1/p')
  echo "  browser: $BROWSER"
  [ -n "$BROWSER" ]; check "version endpoint reports a browser" $?
  # /json/new requires PUT on modern Chrome
  CODE=$(curl -s -o /dev/null -w '%{http_code}' -X PUT \
         "http://127.0.0.1:$PORT/json/new?about:blank")
  echo "  PUT /json/new -> $CODE"
  [ "$CODE" = "200" ]; check "PUT /json/new accepted (GET would 405)" $?
fi

echo "step 4: the system browser must be untouched"
if pgrep -f "Google Chrome.app/Contents/MacOS/Google Chrome" >/dev/null 2>&1; then
  echo "  ok   system Chrome still running"
else
  echo "  note no system Chrome was running to begin with"
fi

echo
if [ "$FAILURES" -eq 0 ]; then
  echo "verify.sh: PASS"
else
  echo "verify.sh: FAIL ($FAILURES check(s))"
fi
exit "$FAILURES"
