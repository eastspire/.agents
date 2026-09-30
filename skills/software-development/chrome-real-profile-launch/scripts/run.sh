#!/usr/bin/env bash
# run.sh — the ONLY supported way to get a browser session with the user's
# real Chrome logins, and the only way to get a NEW TAB in an existing one.
#
# Concurrency is the default assumption, not an edge case. Several Hermes
# sessions may need the browser at the same time, so:
#
#   - ONE shared instance on ONE shared port serves everyone
#   - a caller that finds a healthy instance gets a NEW TAB, and the running
#     browser is never stopped, re-copied or re-launched underneath them
#   - only when no healthy instance exists does the full sequence run:
#     stop stale CDP browsers -> force-overwrite the scratch profile -> launch
#
# A mkdir-based lock covers the start path, because "check then start" is a
# race: two sessions both seeing nothing would each `rm -rf` the other's
# half-built profile.
#
# Nothing here touches the real profile except to READ it.
#
# Usage:
#   bash run.sh [url]                # reuse the instance, or start one; new tab
#   bash run.sh --port 9223          # pin the shared port
#   bash run.sh --work /path/dir     # custom scratch dir
#   bash run.sh --fresh              # force a clean start (stop + re-copy)
#   bash run.sh --no-tab             # ensure an instance, open no tab
#   bash run.sh --headed             # visible window instead of headless
#   bash run.sh --stop               # stop the shared instance
#   bash run.sh --status             # report without changing anything
set -uo pipefail

SELF_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PORT=""
WORK=""
FRESH=0
NO_TAB=0
STOP_ONLY=0
STATUS_ONLY=0
HEADLESS_FLAG="--headless=new"
START_URL="about:blank"
LOCK_WAIT=180

while [ $# -gt 0 ]; do
  case "$1" in
    --port)     PORT="${2:-}"; shift 2 ;;
    --work)     WORK="${2:-}"; shift 2 ;;
    --fresh)    FRESH=1; shift ;;
    --no-tab)   NO_TAB=1; shift ;;
    --stop)     STOP_ONLY=1; shift ;;
    --status)   STATUS_ONLY=1; shift ;;
    --headed)   HEADLESS_FLAG="--headed"; shift ;;
    -h|--help)  sed -n '2,25p' "${BASH_SOURCE[0]}"; exit 0 ;;
    -*)         echo "unknown option: $1" >&2; exit 2 ;;
    *)          START_URL="$1"; shift ;;
  esac
done

# ---------------------------------------------------------------- platform ---
case "$(uname -s)" in
  Darwin) PLATFORM=macos
           SRC="$HOME/Library/Application Support/Google/Chrome"
           BIN="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
           FALLBACK_BIN="$HOME/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" ;;
  Linux)  PLATFORM=linux
           SRC="${CHROME_PROFILE_DIR:-$HOME/.config/google-chrome}"
           BIN="$(command -v google-chrome || command -v google-chrome-stable || command -v chromium || true)"
           FALLBACK_BIN="" ;;
  MINGW*|MSYS*|CYGWIN*)
           PLATFORM=windows
           SRC="${LOCALAPPDATA:-}/Google/Chrome/User Data"
           BIN="${PROGRAMFILES:-C:/Program Files}/Google/Chrome/Application/chrome.exe"
           FALLBACK_BIN="${PROGRAMFILES(X86):-}/Google/Chrome/Application/chrome.exe" ;;
  *) echo "run.sh: unsupported platform $(uname -s)" >&2; exit 2 ;;
esac

# State file: the agreed port for every session. Written on a successful
# launch, so a later session with no --port joins the same instance instead of
# silently starting a second one on a different port.
STATE_DIR="${HERMES_STATE_DIR:-$HOME/.hermes/state}"
STATE_FILE="$STATE_DIR/chrome-real-profile.port"
mkdir -p "$STATE_DIR" 2>/dev/null || true

[ -z "$WORK" ] && WORK="$HOME/.hermes/cache/scratch/chrome-real-profile"

# Resolve the shared port: explicit flag wins, then the agreed one, then a scan.
if [ -z "$PORT" ]; then
  if [ -f "$STATE_FILE" ]; then
    PORT="$(head -1 "$STATE_FILE" 2>/dev/null | tr -dc '0-9')"
  fi
fi
if [ -z "$PORT" ]; then
  for candidate in 9223 9224 9225 9226 9227 9228; do
    if [ "$PLATFORM" = "windows" ]; then
      netstat -ano 2>/dev/null | grep -q ":$candidate .*LISTENING" || { PORT="$candidate"; break; }
    else
      lsof -nP -iTCP:"$candidate" -sTCP:LISTEN >/dev/null 2>&1 || { PORT="$candidate"; break; }
    fi
  done
fi
[ -z "$PORT" ] && { echo "run.sh: no free port in 9223-9228" >&2; exit 2; }

# ------------------------------------------------------------------ helpers ---
port_is_live() {
  curl -s --max-time 3 "http://127.0.0.1:$PORT/json/version" >/dev/null 2>&1
}

open_tab() {
  # Chrome 111+ requires PUT for /json/new; a GET returns 405.
  local url="$1" out
  out=$(curl -s --max-time 10 -X PUT \
        --data-urlencode '' \
        "http://127.0.0.1:$PORT/json/new?$(python3 -c 'import sys,urllib.parse;print(urllib.parse.quote(sys.argv[1],safe=""))' "$url" 2>/dev/null || printf '%s' "$url")" 2>/dev/null)
  if [ -z "$out" ]; then
    # python3 may be absent on a stripped host; retry with the raw URL
    out=$(curl -s --max-time 10 -X PUT "http://127.0.0.1:$PORT/json/new?$url" 2>/dev/null)
  fi
  printf '%s' "$out"
}

target_count() {
  curl -s --max-time 5 "http://127.0.0.1:$PORT/json/list" 2>/dev/null \
    | grep -c '"type"' 2>/dev/null || echo 0
}

# ------------------------------------------------------------------- status ---
if [ "$STATUS_ONLY" -eq 1 ]; then
  echo "run.sh: port=$PORT work=$WORK"
  if port_is_live; then
    echo "run.sh: instance UP, $(target_count) target(s)"
    curl -s --max-time 3 "http://127.0.0.1:$PORT/json/version" \
      | sed -n 's/.*"Browser": *"\([^"]*\)".*/run.sh: browser=\1/p'
  else
    echo "run.sh: instance DOWN"
  fi
  exit 0
fi

if [ "$STOP_ONLY" -eq 1 ]; then
  echo "run.sh: stopping the shared instance"
  if [ "$PLATFORM" = "windows" ]; then
    powershell -NoProfile -Command \
      'Get-CimInstance Win32_Process -Filter "Name=''chrome.exe''" |
         Where-Object { $_.CommandLine -like "*remote-debugging-port*" } |
         ForEach-Object { $_.ProcessId }' 2>/dev/null \
    | while read -r pid; do
        [ -z "$pid" ] && continue
        taskkill //PID "$pid" //T //F >/dev/null 2>&1 && echo "run.sh: stopped pid $pid"
      done
  else
    bash "$SELF_DIR/stop-cdp.sh"
  fi
  rm -f "$STATE_FILE"
  exit 0
fi

# ------------------------------------------------- fast path: reuse the instance
# Healthy instance and not explicitly restarting -> hand back a new tab.
if [ "$FRESH" -eq 0 ] && port_is_live; then
  BROWSER=$(curl -s --max-time 3 "http://127.0.0.1:$PORT/json/version" \
    | sed -n 's/.*"Browser": *"\([^"]*\)".*/\1/p')
  echo "run.sh: reusing the running instance on port $PORT ($BROWSER)"
  if [ "$NO_TAB" -eq 0 ]; then
    TAB=$(open_tab "$START_URL")
    if [ -n "$TAB" ]; then
      TAB_ID=$(printf '%s' "$TAB" | sed -n 's/.*"id": *"\([^"]*\)".*/\1/p')
      echo "run.sh: opened tab $TAB_ID"
      echo "run.sh: total targets now $(target_count)"
    else
      echo "run.sh: WARNING — could not open a tab; the instance is still up" >&2
    fi
  fi
  echo "run.sh: no copy and no relaunch — the running browser was left alone"
  exit 0
fi

# ------------------------------------------------------------------- start ---
if [ -z "$BIN" ] || [ ! -x "$BIN" ]; then
  if [ -n "$FALLBACK_BIN" ] && [ -x "$FALLBACK_BIN" ]; then
    BIN="$FALLBACK_BIN"
  else
    echo "run.sh: Chrome binary not found" >&2; exit 2
  fi
fi
if [ ! -d "$SRC" ]; then
  echo "run.sh: profile dir not found: $SRC" >&2; exit 2
fi

# mkdir is the only atomic lock primitive guaranteed on macOS, Linux and
# Windows-without-extra-deps. The loser of the race waits, then re-checks.
LOCK_DIR="$STATE_DIR/chrome-real-profile.lock"
acquire_lock() {
  local waited=0
  while ! mkdir "$LOCK_DIR" 2>/dev/null; do
    # a lock older than 10 minutes belongs to a process that died
    if [ -d "$LOCK_DIR" ]; then
      local age=$(( $(date +%s) - $(stat -f %m "$LOCK_DIR" 2>/dev/null || stat -c %Y "$LOCK_DIR" 2>/dev/null || echo 0) ))
      [ "$age" -gt 600 ] && { echo "run.sh: clearing a stale lock (${age}s old)" >&2; rm -rf "$LOCK_DIR"; continue; }
    fi
    waited=$((waited+1))
    [ "$waited" -gt "$LOCK_WAIT" ] && return 1
    sleep 1
  done
  return 0
}
release_lock() { rmdir "$LOCK_DIR" 2>/dev/null || true; }
trap release_lock EXIT INT TERM

echo "run.sh: no healthy instance on port $PORT — starting one"
acquire_lock || { echo "run.sh: timed out waiting for another session to finish starting" >&2; exit 1; }

# Re-check under the lock: another session may have started it while we waited.
if [ "$FRESH" -eq 0 ] && port_is_live; then
  release_lock; trap - EXIT INT TERM
  echo "run.sh: another session started the instance while we waited — reusing it"
  [ "$NO_TAB" -eq 0 ] && { TAB=$(open_tab "$START_URL"); \
    printf '%s' "$TAB" | grep -q '"id"' && echo "run.sh: opened tab $(printf '%s' "$TAB" | sed -n 's/.*"id": *"\([^"]*\)".*/\1/p')"; }
  echo "run.sh: port=$PORT targets=$(target_count)"
  exit 0
fi

echo "run.sh: platform=$PLATFORM port=$PORT"
echo "run.sh: source=$SRC"
echo "run.sh: work  =$WORK"

# --- step 1: stop stale CDP browsers (they hold the port and the singleton lock)
echo "run.sh: step 1/3 — stopping stale CDP browsers"
if [ "$PLATFORM" = "windows" ]; then
  powershell -NoProfile -Command \
    'Get-CimInstance Win32_Process -Filter "Name=''chrome.exe''" |
       Where-Object { $_.CommandLine -like "*remote-debugging-port*" } |
       ForEach-Object { $_.ProcessId }' 2>/dev/null \
  | while read -r pid; do
      [ -z "$pid" ] && continue
      taskkill //PID "$pid" //T //F >/dev/null 2>&1
    done
else
  bash "$SELF_DIR/stop-cdp.sh"
fi

# --- step 2: force-overwrite the scratch profile
echo "run.sh: step 2/3 — force-overwriting the scratch profile"
# Delete first. An in-place sync keeps Singleton* and a `Local State` carrying
# the previous run's port decision, both of which break the next launch.
rm -rf "$WORK"
mkdir -p "$WORK"

if [ "$PLATFORM" = "windows" ]; then
  # robocopy exit codes 0-7 are SUCCESS; >=8 are failures.
  robocopy "$SRC" "$WORK\\profile" /E /R:1 /W:1 \
    /XD Cache "Code Cache" GPUCache ShaderCache component_crx_cache Crashpad \
        "Service Worker\\CacheStorage" "Service Worker\\ScriptCache" \
    /XF SingletonLock SingletonCookie SingletonSocket DevToolsActivePort \
    > "$WORK/copy.log" 2>&1
  rc=$?
  if [ "$rc" -ge 8 ]; then
    echo "run.sh: robocopy failed with exit $rc" >&2
    tail -5 "$WORK/copy.log" >&2
    exit 1
  fi
else
  rsync -a --delete \
    --exclude='Cache' --exclude='Code Cache' --exclude='GPUCache' \
    --exclude='ShaderCache' --exclude='GraphiteDawnCache' \
    --exclude='component_crx_cache' --exclude='Crashpad' \
    --exclude='Service Worker/CacheStorage' --exclude='Service Worker/ScriptCache' \
    --exclude='Singleton*' --exclude='DevToolsActivePort' \
    "$SRC/" "$WORK/profile/"
  rc=$?
  if [ "$rc" -ne 0 ]; then
    echo "run.sh: rsync failed with exit $rc" >&2
    exit 1
  fi
fi
rm -f "$WORK/profile/SingletonLock" "$WORK/profile/SingletonCookie" \
      "$WORK/profile/SingletonSocket" "$WORK/profile/DevToolsActivePort" 2>/dev/null || true

if [ ! -f "$WORK/profile/Default/Cookies" ]; then
  echo "run.sh: copy is missing Default/Cookies — refusing to launch" >&2
  exit 1
fi
echo "run.sh: copy verified (Default/Cookies present)"

# --- step 3: launch
echo "run.sh: step 3/3 — launching Chrome on the copy"
T_LAUNCH=$(date +%s)
LOG="$WORK/chrome.log"
if [ "$PLATFORM" = "windows" ]; then
  WIN_PROFILE_DIR=$(printf '%s' "$WORK\\profile" | sed 's/\\/\\\\/g')
  powershell -NoProfile -Command \
    "Start-Process -FilePath '$BIN' -ArgumentList @('--remote-debugging-port=$PORT','$HEADLESS_FLAG','--user-data-dir=$WIN_PROFILE_DIR','--profile-directory=Default','--safebrowsing-disable-download-protection','--disable-features=InsecureDownloadWarnings') -RedirectStandardError '$LOG'" \
    >/dev/null 2>&1
else
  "$BIN" \
    --remote-debugging-port="$PORT" \
    "$HEADLESS_FLAG" \
    --user-data-dir="$WORK/profile" \
    --profile-directory="Default" \
    --safebrowsing-disable-download-protection \
    --disable-features=InsecureDownloadWarnings \
    > "$LOG" 2>&1 &
  disown $! 2>/dev/null || true
fi

# --- readiness: the log's own "DevTools listening" line, confirmed by curl.
READY=0
for _ in $(seq 1 90); do
  if grep -q "DevTools listening on ws://127.0.0.1:$PORT/" "$LOG" 2>/dev/null; then
    if port_is_live; then READY=1; break; fi
  fi
  if grep -q "Aborting now to avoid profile corruption" "$LOG" 2>/dev/null; then
    echo "run.sh: FAILED — Chrome refused the profile (singleton):" >&2
    grep -oE "Failed to create .*Singleton[A-Za-z]*" "$LOG" | head -1 >&2
    exit 1
  fi
  sleep 1
done

if [ "$READY" -ne 1 ]; then
  echo "run.sh: FAILED — CDP never came up. last log lines:" >&2
  tail -8 "$LOG" >&2 2>/dev/null || true
  exit 1
fi

# Publish the agreed port BEFORE releasing the lock, so a session arriving in
# the gap joins this instance instead of starting a second one.
printf '%s\n' "$PORT" > "$STATE_FILE" 2>/dev/null || true
release_lock
trap - EXIT INT TERM

BROWSER=$(curl -s --max-time 3 "http://127.0.0.1:$PORT/json/version" \
  | sed -n 's/.*"Browser": *"\([^"]*\)".*/\1/p')
echo "run.sh: ready — $BROWSER (launched in $(( $(date +%s) - T_LAUNCH ))s)"
if [ "$NO_TAB" -eq 0 ]; then
  TAB=$(open_tab "$START_URL")
  printf '%s' "$TAB" | grep -q '"id"' \
    && echo "run.sh: opened tab $(printf '%s' "$TAB" | sed -n 's/.*"id": *"\([^"]*\)".*/\1/p')"
fi
echo "run.sh: port=$PORT  other sessions will reuse this instance and open their own tabs"
exit 0
