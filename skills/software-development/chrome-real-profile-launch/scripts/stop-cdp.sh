#!/usr/bin/env bash
# stop-cdp.sh — kill every Chromium that was launched with a CDP debug port.
#
# Deliberately narrow. It matches on `--remote-debugging-port` in the process
# arguments, so the user's own browser (which never carries that flag) is never
# a candidate. "Kill all chrome" would be a data-loss bug, not a convenience.
#
# Usage:  bash stop-cdp.sh [--all-ports|--port N]
# Exit:   0 = nothing was running, or everything was stopped
set -uo pipefail

ALL_PORTS=1
PORT=""
while [ $# -gt 0 ]; do
  case "$1" in
    --all-ports) ALL_PORTS=1; shift ;;
    --port) PORT="${2:-}"; ALL_PORTS=0; shift 2 ;;
    *) echo "usage: $0 [--all-ports|--port N]" >&2; exit 2 ;;
  esac
done

# Collect candidates. `ps -eo pid,args` avoids pgrep's own pattern matching
# itself, and the bracket in the grep pattern is the second line of defence.
candidates=$(ps -eo pid=,args= \
  | grep -- '[-]-remote-debugging-port' \
  | grep -v 'stop-cdp\.sh' \
  | grep -viE 'grep|ps -eo' || true)

if [ -z "$candidates" ]; then
  echo "stop-cdp: no CDP browser running"
  exit 0
fi

stopped=0
while read -r pid args; do
  [ -z "${pid:-}" ] && continue
  if [ "$ALL_PORTS" -eq 0 ]; then
    case "$args" in
      *"--remote-debugging-port=$PORT"*) ;;
      *) continue ;;
    esac
  fi
  port=$(printf '%s\n' "$args" \
    | sed -n 's/.*--remote-debugging-port[= ]\([0-9]\{1,5\}\).*/\1/p' | head -1)
  if kill "$pid" 2>/dev/null; then
    # A child process is often already gone once its parent took the whole
    # group down; that is a success, not an error, so it is not reported.
    echo "stop-cdp: TERM pid $pid (port ${port:-?})"
    stopped=$((stopped+1))
  fi
done <<EOF
$candidates
EOF

# Chrome ignores SIGTERM while a modal is open; give it a moment, then force.
for _ in 1 2 3 4 5 6 7 8 9 10; do
  remaining=$(ps -eo pid=,args= | grep -- '[-]-remote-debugging-port' \
    | grep -v 'stop-cdp\.sh' || true)
  [ -z "$remaining" ] && break
  sleep 0.5
done
remaining=$(ps -eo pid=,args= | grep -- '[-]-remote-debugging-port' \
  | grep -v 'stop-cdp\.sh' || true)
if [ -n "$remaining" ]; then
  while read -r pid _; do
    [ -z "${pid:-}" ] && continue
    kill -9 "$pid" 2>/dev/null && echo "stop-cdp: KILL pid $pid (ignored SIGTERM)"
  done <<EOF
$remaining
EOF
  sleep 1
fi

echo "stop-cdp: stopped $stopped process(es)"
exit 0
