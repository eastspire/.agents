#!/usr/bin/env bash
# run.sh — the ONLY supported way to start Chrome on a copy of the real profile.
#
# Three things happen here, in this order, and the order is the point:
#   1. stop every previously launched CDP browser  (a stale one holds the port
#                                                 and the singleton lock)
#   2. force-overwrite the scratch profile dir    (no merging with yesterday's
#                                                 copy, no stale Local State)
#   3. launch Chrome on the fresh copy
#
# Nothing in this file touches the real profile except to READ it.
#
# Usage:
#   bash run.sh                  # auto port, default scratch dir
#   bash run.sh --port 9223
#   bash run.sh --work /path/dir --keep    # reuse a dir, skip the copy
#   bash run.sh --stop                    # just stop CDP browsers
set -uo pipefail

SELF_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PORT=""
WORK=""
KEEP=0
STOP_ONLY=0
HEADLESS_FLAG="--headless=new"

while [ $# -gt 0 ]; do
  case "$1" in
    --port)     PORT="${2:-}"; shift 2 ;;
    --work)     WORK="${2:-}"; shift 2 ;;
    --keep)     KEEP=1; shift ;;
    --stop)     STOP_ONLY=1; shift ;;
    --headed)   HEADLESS_FLAG="--headed"; shift ;;
    -h|--help)  sed -n '2,20p' "${BASH_SOURCE[0]}"; exit 0 ;;
    *) echo "unknown argument: $1" >&2; exit 2 ;;
  esac
done

# ---------------------------------------------------------------- platform ---
detect_platform() {
  case "$(uname -s)" in
    Darwin) echo macos ;;
    Linux)  echo linux ;;
    MINGW*|MSYS*|CYGWIN*) echo windows ;;
    *) echo unknown ;;
  esac
}
PLATFORM="$(detect_platform)"

case "$PLATFORM" in
  macos)
    SRC="$HOME/Library/Application Support/Google/Chrome"
    BIN="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    FALLBACK_BIN="$HOME/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    ;;
  linux)
    SRC="${CHROME_PROFILE_DIR:-$HOME/.config/google-chrome}"
    BIN="$(command -v google-chrome || command -v google-chrome-stable || command -v chromium || true)"
    FALLBACK_BIN=""
    ;;
  windows)
    SRC="${LOCALAPPDATA:-}/Google/Chrome/User Data"
    BIN="${PROGRAMFILES:-C:/Program Files}/Google/Chrome/Application/chrome.exe"
    FALLBACK_BIN="${PROGRAMFILES(X86):-}/Google/Chrome/Application/chrome.exe"
    ;;
  *)
    echo "run.sh: unsupported platform $(uname -s)" >&2; exit 2 ;;
esac

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

if [ -z "$WORK" ]; then
  WORK="$HOME/.hermes/cache/scratch/chrome-real-profile"
fi
mkdir -p "$(dirname "$WORK")" 2>/dev/null || true

if [ -z "$PORT" ]; then
  # pick the first free port from a small range; 9222 is agent-browser's default
  for candidate in 9223 9224 9225 9226 9227 9228; do
    if [ "$PLATFORM" = "windows" ]; then
      netstat -ano 2>/dev/null | grep -q ":$candidate .*LISTENING" || { PORT="$candidate"; break; }
    else
      lsof -nP -iTCP:"$candidate" -sTCP:LISTEN >/dev/null 2>&1 || { PORT="$candidate"; break; }
    fi
  done
  [ -z "$PORT" ] && { echo "run.sh: no free port in 9223-9228" >&2; exit 2; }
fi

echo "run.sh: platform=$PLATFORM port=$PORT"
echo "run.sh: source=$SRC"
echo "run.sh: work  =$WORK"

# ------------------------------------------------------- 1. stop old browsers ---
echo "run.sh: step 1/3 — stopping any previously launched CDP browser"
if [ "$PLATFORM" = "windows" ]; then
  # Only processes whose command line carries the debug flag, matched through
  # wmic so the user's own Chrome is never a candidate.
  # Single-quoted so PowerShell's own quoting needs no shell escaping.
  powershell -NoProfile -Command \
    'Get-CimInstance Win32_Process -Filter "Name=''chrome.exe''" |
       Where-Object { $_.CommandLine -like "*remote-debugging-port*" } |
       ForEach-Object { $_.ProcessId }' 2>/dev/null \
  | while read -r pid; do
      [ -z "$pid" ] && continue
      taskkill //PID "$pid" //T //F >/dev/null 2>&1 \
        && echo "run.sh: stopped pid $pid"
    done
else
  bash "$SELF_DIR/stop-cdp.sh"
fi

if [ "$STOP_ONLY" -eq 1 ]; then
  echo "run.sh: --stop given, exiting without copying or launching"
  exit 0
fi

# ------------------------------------------------------------- 2. force copy ---
if [ "$KEEP" -eq 1 ] && [ -d "$WORK/profile" ]; then
  echo "run.sh: step 2/3 — --keep given, reusing the existing copy"
else
  echo "run.sh: step 2/3 — force-overwriting the scratch profile"
  # Remove the whole directory first. An in-place rsync --delete leaves behind
  # the singleton files and a `Local State` carrying the previous run's
  # decisions, both of which break the next launch.
  rm -rf "$WORK"
  mkdir -p "$WORK"

  if [ "$PLATFORM" = "windows" ]; then
    # robocopy exit codes 0-7 are SUCCESS; >=8 are failures.
    robocopy "$SRC" "$WORK\\profile" /E /R:1 /W:1 \
      /XD Cache "Code Cache" GPUCache ShaderCache component_crx_cache Crashpad \
          "Service Worker\\CacheStorage" "Service Worker\\ScriptCache" \
      /XF SingletonLock SingletonCookie SingletonSocket DevToolsActivePort \
      > "$WORK/rsync.log" 2>&1
    rc=$?
    if [ "$rc" -ge 8 ]; then
      echo "run.sh: robocopy failed with exit $rc" >&2
      tail -5 "$WORK/rsync.log" >&2
      exit 1
    fi
  else
    rsync -a --delete \
      --exclude='Cache' \
      --exclude='Code Cache' \
      --exclude='GPUCache' \
      --exclude='ShaderCache' \
      --exclude='GraphiteDawnCache' \
      --exclude='component_crx_cache' \
      --exclude='Crashpad' \
      --exclude='Service Worker/CacheStorage' \
      --exclude='Service Worker/ScriptCache' \
      --exclude='Singleton*' \
      --exclude='DevToolsActivePort' \
      "$SRC/" "$WORK/profile/"
    rc=$?
    if [ "$rc" -ne 0 ]; then
      echo "run.sh: rsync failed with exit $rc" >&2
      exit 1
    fi
  fi

  # Belt and braces: even with the excludes, drop them if anything slipped.
  rm -f "$WORK/profile/SingletonLock" "$WORK/profile/SingletonCookie" \
        "$WORK/profile/SingletonSocket" "$WORK/profile/DevToolsActivePort" 2>/dev/null || true
fi

if [ ! -f "$WORK/profile/Default/Cookies" ]; then
  echo "run.sh: copy is missing Default/Cookies — refusing to launch" >&2
  exit 1
fi
echo "run.sh: copy verified (Default/Cookies present)"

# --------------------------------------------------------------- 3. launch ---
echo "run.sh: step 3/3 — launching Chrome on the copy"
T_LAUNCH=$(date +%s)
LOG="$WORK/chrome.log"
if [ "$PLATFORM" = "windows" ]; then
  # $WORK is on a real volume, not %TEMP%: a 4 GB profile does not fit in the
  # default session temp and truncates silently.
  # PowerShell Start-Process. A path containing spaces must arrive as ONE
  # argument, so the whole --user-data-dir= value stays inside a single
  # single-quoted string; the backslashes are doubled for PowerShell itself.
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
  CHROME_PID=$!
  disown "$CHROME_PID" 2>/dev/null || true
fi

# ------------------------------------------------------------- 4. readiness ---
echo "run.sh: waiting for CDP on $PORT (launched $(( $(date +%s) - T_LAUNCH ))s ago)"
# Readiness is read from the log's own "DevTools listening on ws://..." line,
# not from a fixed sleep: after killing a previous 4 GB-profile instance the
# machine is busy enough that a curl poll window can expire while Chrome is in
# fact already listening. The log is the authoritative signal; curl confirms.
READY=0
for _ in $(seq 1 90); do
  if grep -q "DevTools listening on ws://127.0.0.1:$PORT/" "$LOG" 2>/dev/null; then
    if curl -s --max-time 3 "http://127.0.0.1:$PORT/json/version" >/dev/null 2>&1; then
      READY=1; break
    fi
  fi
  # bail out early if Chrome died on a profile error rather than waiting 90s
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

BROWSER=$(curl -s --max-time 3 "http://127.0.0.1:$PORT/json/version" \
  | sed -n 's/.*"Browser": *"\([^"]*\)".*/\1/p')
echo "run.sh: ready — $BROWSER"
echo "run.sh: attach with  curl -s http://127.0.0.1:$PORT/json/version"
echo "run.sh: stop with   bash $SELF_DIR/stop-cdp.sh"
exit 0
