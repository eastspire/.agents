# `hermes update` troubleshooting

`hermes update` does three things in sequence: `git fetch` → `git reset` → rebuild Python deps. Each can fail or stall in different ways; most "卡住" reports are actually one of three known patterns.

## 1. "fetch-pack: unexpected disconnect" / silent hang

The update.log will show `→ Fetching updates…` followed by either an outright error or just nothing for many minutes:

```
=== hermes update started 2026-08-18T17:20:06 ===
⚕ Updating Hermes Agent…
→ Fetching updates…
```

### Root cause: not a shallow clone

Hermes's installer uses `git clone --depth=1`, so a fresh install is shallow. But once anyone runs `git fetch --unshallow` (or a non-shallow `git clone`), the local repo holds the full history. `update_cmd.py` detects this and runs `git fetch origin <branch>` **without `--depth=1`** to avoid expanding history — which means it to fetch every object on every remote ref. For the `NousResearch/hermes-agent` repo that's **194,000+ objects at 20-30 KiB/s** = hours of hanging that looks like a stall.

Verify:

```bash
cd /usr/local/lib/hermes-agent
if [ -f .git/shallow ]; then
  echo "shallow: $(wc -l < .git/shallow) entries"
else
  echo "NOT shallow — this is the cause"
fi
```

### Fix: convert to shallow

```bash
cd /usr/local/lib/hermes-agent
git fetch --depth=1 --prune --progress origin main
```

This drops the object count to ~155 and the connection fetch to ~120 KiB / 30 seconds. Once `.git/shallow` exists, `hermes update` will reuse `--depth=1` on every subsequent run.

If `hermes update` itself is what's hanging and you can't interrupt it cleanly, `pkill -KILL -f "git.*fetch"` and re-run from scratch — the next fetch will use the same `--depth=1` path.

### Network-side issues (less common)

If the SSH connection itself is dropping:

```bash
# Test connectivity
timeout 5 bash -c 'echo > /dev/tcp/github.com/22'  # SSH
timeout 5 bash -c 'echo > /dev/tcp/github.com/443' # HTTPS
ssh -T -o ConnectTimeout=5 -o BatchMode=yes git@github.com 2>&1 | head -3

# Switch to HTTPS if SSH is flaky (and have a `gh` token / SSH key on HTTPS origin)
git -C /usr/local/lib/hermes-agent remote set-url origin \
  https://github.com/NousResearch/hermes-agent.git
```

## 2. "Updating Python dependencies..." takes 20+ minutes (Rust/C compilation)

After fetch+pull succeed, update rewrites the venv to fix the SQLite WAL-reset bug (Hermes bundles a custom CPython build), then `uv pip install -U faster-whisper` (and other heavy deps with Rust extensions).

### What's happening

`faster-whisper` pulls `ctranslate2 + onnxruntime + PyAV + numpy + tokenizers` — each has C or Rust extensions that compile at install time. The progress line `… still installing dependencies (30s elapsed) — compiling Rust/C extensions can take several minutes` is **normal**, not a hang.

Check real progress (don't trust elapsed time alone):

```bash
# Is there a uv subprocess running?
ps -ef | grep -E "uv pip|rustc|cc1" | grep -v grep | head

# Write activity (KB/s)
W1=$(cat /proc/<uv-pid>/io 2>/dev/null | grep wchar | awk '{print $2}')
sleep 30
W2=$(cat /proc/<uv-pid>/io 2>/dev/null | grep wchar | awk '{print $2}')
echo "wchar delta: $((W2 - W1)) bytes in 30s"
# Anything > 0 = real progress. > 50KB/s = actively writing wheel / .so.
```

### When to actually interrupt

- No `uv` subprocess running AND no `rustc`/`cc1` child AND `wchar` not moving for 5+ minutes → stuck, kill it.
- Active uv with active rustc/cc1 child writing bytes → keep waiting; full pass can take 30+ min on a slow link.

The `update.log` final line should be `✓ Update complete!` or a specific failure. Anything short of that after `hermes update` exits is a partial state — check `git log -1` to see if the code at least moved.

## 3. "Restoring Hermes Tools dependency set(s)" keeps timing out

After the core update succeeds, `hermes update` runs `uv pip install -U faster-whisper sounddevice numpy` (for `stt.faster_whisper`) and similar for each lazy backend. If those fail:

```
⚠ stt.faster_whisper failed to refresh: pip install failed: uv pip install timed out
⚠ platform.feishu failed to refresh: pip install failed: uv pip install timed out
Lazy backend(s) keep their previous version; probed packages look intact.
Rerun `hermes update` once the upstream issue is resolved.
```

This is **informational, not fatal** — the core upgrade already succeeded. The lazy backends (STT, Feishu, etc.) keep their previous wheel and load fine on first use. Re-run `hermes update` later when the link is faster if you want them refreshed.

## 4. The venv has been replaced — where did `python` go?

After `hermes update` rebuilds the runtime, `which python` from a fresh shell may resolve to a different interpreter than before. The new managed Python lives under:

```
/usr/local/lib/hermes-agent/.hermes-runtime/python/generation-<id>-<pid>-<hash>/cpython-3.11.16-linux-x86_64-gnu/bin/python3.11
```

`hermes update` leaves a recovery marker if the new runtime fails to import — see `hermes-cli/update_cmd.py` for the `Recovery marker detected` branch and `--force` flag. If your shell sessions all suddenly can't import hermes packages, run `hermes update --force` from a path with the old interpreter on PATH (or just log out and back in to refresh `$PATH`).

## 5. Verify the upgrade landed

```bash
hermes --version              # should match the upstream tag you fetched
cd /usr/local/lib/hermes-agent && git log -1 --oneline
grep '^version' /usr/local/lib/hermes-agent/pyproject.toml
/usr/local/lib/hermes-agent/venv/bin/python -c "import sqlite3; print(sqlite3.sqlite_version)"
```

All three should reflect the new release.

## Quick decision tree

| Symptom | Try first | If that fails |
|---|---|---|
| `→ Fetching updates…` hangs > 5 min | `git fetch --depth=1 --prune --progress origin main` | switch remote to HTTPS |
| `compiling Rust/C extensions` loop | wait (check `wchar` delta) | kill `uv`, retry with `--with` pins |
| `pip install timed out` warnings | ignore (lazy backends) | retry later when network is faster |
| Update completes but `python` import broken | `hermes update --force` | check `.hermes-runtime` marker |