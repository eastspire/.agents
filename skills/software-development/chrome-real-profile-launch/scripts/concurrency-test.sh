#!/usr/bin/env bash
# Concurrency test for run.sh.
#
# The claim under test: several sessions starting at the same time end up
# sharing ONE instance on ONE port, each with its own tab, and nobody's
# half-built profile gets deleted by anybody else.
#
# Method: cold-stop, then fire N run.sh calls simultaneously and inspect the
# result. A second phase fires N more against the already-running instance.
set -uo pipefail
S="$(cd "$(dirname "$0")" && pwd)"
N="${1:-4}"
PORT="${PORT:-9223}"
FAIL=0

ok()   { printf '  ok   %s\n' "$1"; }
bad()  { printf '  FAIL %s\n' "$1"; FAIL=$((FAIL+1)); }

targets() { curl -s --max-time 5 "http://127.0.0.1:$PORT/json/list" 2>/dev/null | grep -c '"type"'; }
pid_of()  { lsof -nP -iTCP:"$PORT" -sTCP:LISTEN -t 2>/dev/null | head -1; }
# Retries: during a --fresh the listener legitimately disappears for a moment.
pid_of_settled() {
  local p="" n=0
  while [ $n -lt 10 ]; do
    p="$(pid_of)"
    [ -n "$p" ] && { printf '%s' "$p"; return 0; }
    n=$((n+1)); sleep 1
  done
  return 1
}

echo "=== phase 0: cold stop ==="
bash "$S/run.sh" --stop >/dev/null 2>&1
rm -rf "${HERMES_STATE_DIR:-$HOME/.hermes/state}"/chrome-real-profile.lock
sleep 1
[ -z "$(pid_of)" ] && ok "no instance is running" || bad "something still on $PORT"

echo "=== phase 1: $N sessions start simultaneously from cold ==="
OUT="$(mktemp -d)"
echo "$OUT" > /tmp/chrome-conc-latest
trap 'rm -rf "$OUT"' EXIT
[ "${KEEP_LOGS:-0}" = "1" ] && trap - EXIT
for i in $(seq 1 "$N"); do
  ( bash "$S/run.sh" "https://example.com/?s=$i" > "$OUT/$i.log" 2>&1 ) &
done
wait

STARTED=0; REUSED=0; WAITED=0
for i in $(seq 1 "$N"); do
  if   grep -q "run.sh: ready" "$OUT/$i.log";                  then STARTED=$((STARTED+1))
  elif grep -q "reusing the running instance" "$OUT/$i.log";   then REUSED=$((REUSED+1))
  elif grep -q "while we waited" "$OUT/$i.log";                then WAITED=$((WAITED+1))
  fi
done
echo "  started=$STARTED  reused=$REUSED  waited-then-reused=$WAITED"
[ $((STARTED+REUSED+WAITED)) -eq "$N" ] && ok "every session got a browser" \
  || bad "some session failed: $(grep -l FAILED "$OUT"/*.log 2>/dev/null | tr '\n' ' ')"
# Exactly one session may do the cold start; more would mean the lock is broken.
[ "$STARTED" -le 1 ] && ok "at most one session did the cold start ($STARTED)" \
  || bad "$STARTED sessions each did a cold start — the lock is not working"
grep -q "force-overwriting" "$OUT"/*.log && ok "the profile was copied once" \
  || bad "no copy happened at all"

INSTANCES=$(pgrep -f "remote-debugging-port=$PORT" | wc -l | tr -d ' ')
[ "$INSTANCES" -ge 1 ] && ok "one browser process tree on $PORT" || bad "no process on $PORT"
CDP_PORTS=$(pgrep -fl 'remote-debugging-port=' | grep -oE 'remote-debugging-port=[0-9]+' | sort -u | wc -l | tr -d ' ')
[ "$CDP_PORTS" -eq 1 ] && ok "exactly one CDP port in use ($PORT)" \
  || bad "$CDP_PORTS distinct CDP ports are in use — sessions did not converge"

STATE_PORT="$(cat "${HERMES_STATE_DIR:-$HOME/.hermes/state}/chrome-real-profile.port" 2>/dev/null | tr -dc '0-9')"
[ "$STATE_PORT" = "$PORT" ] && ok "state file agrees on port $PORT" \
  || bad "state file says '$STATE_PORT', expected $PORT"

T1=$(targets)
echo "  targets after phase 1: $T1"
[ "$T1" -ge "$N" ] && ok "at least $N tabs exist" || bad "only $T1 targets for $N sessions"

echo "=== phase 2: $N more sessions against the running instance ==="
PID_BEFORE="$(pid_of_settled || true)"
for i in $(seq 1 "$N"); do
  ( bash "$S/run.sh" "https://example.org/?p=$i" > "$OUT/p$i.log" 2>&1 ) &
done
wait
PID_AFTER="$(pid_of_settled || true)"
if [ -n "$PID_BEFORE" ] && [ "$PID_BEFORE" = "$PID_AFTER" ]; then
  ok "instance pid unchanged ($PID_AFTER)"
else
  bad "pid changed ${PID_BEFORE:-none} -> ${PID_AFTER:-none}"
fi
REUSE2=$(grep -l "reusing the running instance" "$OUT"/p*.log 2>/dev/null | wc -l | tr -d ' ')
[ "$REUSE2" -eq "$N" ] && ok "all $N reused the instance" || bad "only $REUSE2 of $N reused"
T2=$(targets)
[ "$T2" -gt "$T1" ] && ok "tabs grew $T1 -> $T2" || bad "tabs did not grow ($T1 -> $T2)"

echo "=== phase 3: --fresh still forces a clean start ==="
bash "$S/run.sh" --fresh --no-tab > "$OUT/fresh.log" 2>&1
if [ $? -eq 0 ] && grep -q "force-overwriting" "$OUT/fresh.log"; then
  ok "--fresh re-copied and relaunched"
else
  bad "--fresh did not force a start"
fi
PID_FRESH="$(pid_of_settled || true)"
[ -n "$PID_FRESH" ] && ok "fresh instance is live (pid $PID_FRESH)" \
  || bad "fresh left no instance behind"
T_FRESH=$(targets)
[ "$T_FRESH" -ge 1 ] && ok "fresh instance is serving ($T_FRESH target(s))" \
  || bad "fresh instance serves nothing"

echo "  logs kept at: $OUT"
echo
if [ "$FAIL" -eq 0 ]; then echo "concurrency-test: PASS"; else echo "concurrency-test: FAIL ($FAIL)"; fi
exit "$FAIL"
