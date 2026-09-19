---
name: rust-build-perf-vm
description: sccache + /tmp/target on VM-24-7. Use on cache misses.
version: 1.0.0
author: Hermes Agent + eastspire
license: MIT
category: devops
metadata:
  hermes:
    tags: [rust, cargo, sccache, build-performance, vm-24-7]
    related_skills: [rust-cargo-mirror-setup, rust-wasm-gh-pages-deploy-pitfalls]
---

# Rust build performance on VM-24-7-opencloudos

## When to use

- Configuring sccache as the default Rust compiler wrapper
- Diagnosing `sccache -s` showing `Non-cacheable calls`, `Compile requests executed = 0`, or `Non-cacheable reasons: missing input / crate-type`
- Setting `target-dir` to `/tmp/target` so cargo doesn't fill `~`
- Investigating why `cargo build` is slow despite sccache being "configured"
- After the daily `disk-hygiene` cron wipes `/tmp/target`

## Trigger

- Configuring sccache as the default Rust compiler wrapper
- Diagnosing `sccache -s` showing `Non-cacheable calls`, `Compile requests executed = 0`, or `Non-cacheable reasons: missing input / crate-type`
- Setting `target-dir` to `/tmp/target` so cargo doesn't fill `~`
- Investigating why `cargo build` is slow despite sccache being "configured"
- After the daily `disk-hygiene` cron wipes `/tmp/target`

## Three-layer sccache setup (canonical)

| Layer | File | Purpose |
|---|---|---|
| 1. cargo config | `~/.cargo/config.toml` `[build]` | `rustc-wrapper = "/root/.cargo/bin/sccache"` — applies to every cargo invocation |
| 2. env wrapper | `/etc/profile.d/sccache.sh` | `export RUSTC_WRAPPER=...` — covers non-cargo tools (rust-analyzer, LSP, ad-hoc scripts) |
| 3. server pre-warm | `/etc/profile.d/sccache.sh` (`sccache --start-server`) | Avoids first-build spawn cost; harmless to re-run |

`target-dir = "/tmp/target"` lives in the same `[build]` block as `rustc-wrapper`. `/tmp` is on the same root partition as `~` on this VM (60G), so `/tmp/target` does not actually free space — only changes the cleanup scope. Use it to make `target/` visible to the disk-hygiene cron.

## Diagnosing sccache not caching

Symptoms:

```
$ sccache -s
Compile requests                      8
Compile requests executed             0
Cache hits                            0
Cache misses                          0
Compilations                          0

Non-cacheable reasons:
missing input                         4
crate-type                            4
```

### Check 1: is the wrapper even invoked?

```bash
cd /tmp/sccache-test && cargo clean && touch src/main.rs && cargo build -v 2>&1 | grep Running
# Must show: Running `/root/.cargo/bin/sccache <rustc_path> ...`
```

If you see `Running .../rustc ...` directly (no sccache prefix), `rustc-wrapper` is not applied — check `~/.cargo/config.toml` and that no other config is overriding it.

### Check 2: is the env wrapper active in the current shell?

```bash
echo "RUSTC_WRAPPER=${RUSTC_WRAPPER:-<unset>}"
```

Login shells source `/etc/profile.d/sccache.sh`; non-login `bash -c`, systemd services, and cron jobs do **not**. Add `set -a; source /etc/profile.d/sccache.sh; set +a` to scripts that need sccache, or use the cargo config layer (it applies regardless of shell env).

### Check 3: version compatibility

Run `sccache --version` and check against `rustc --version`:

| sccache | cargo/rustc | Status |
|---|---|---|
| 0.5.x – 0.10.x | 1.70 – 1.85 | ✅ works |
| 0.10.x | 1.86 – 1.96 | ✅ works |
| 0.17.0 | **1.97.1** | ⚠️ **incompatible** (see below) |

### sccache 0.17 + cargo 1.97 incompatibility

This VM has `sccache 0.17.0` (built Sep 2 2026) and `cargo 1.97.1 / rustc 1.97.1`. sccache 0.17 expects rustc wrapper invocations to use `--input <path>` for the source file. Cargo 1.97.1 still uses the positional form `rustc ... src/main.rs`. Result: sccache parses the invocation, finds no `--input`, marks it `missing input`, and runs rustc passthrough without caching.

Evidence (from `strings $(which sccache)`):
```
Can't cache compilation, missing `input`
Can't cache compilation, missing `crate_type`
Can't cache compilation, missing `emit`
Can't cache compilation, missing `output_dir`
```

**Fix options** (in order of effort):

1. **Accept the no-op cache** — keep `[build] rustc-wrapper` configured; rustc still runs (slow path), no breakage, just no cache benefit. Status quo on this VM until upstream fixes either side.
2. **Downgrade sccache** to a known-good 0.10.x. `cargo install sccache --version "^0.10" --root /root/.cargo` then update the wrapper paths. Loses sccache 0.17's GHA/Azure/WebDAV/OSS backends (none of which this VM uses).
3. **Disable the wrapper**, rely on cargo's built-in incremental compilation. Faster to compile, but no cross-crate / cross-workspace cache. Equivalent to sccache not working.

Do **not** try `SCCACHE_DIRECT=false` or any other env knob — sccache 0.17 doesn't expose them. The binary's hard-coded `missing input` check happens before any env var is consulted.

## cron / disk-hygiene interaction

The `disk-hygiene-daily-7am` cron (script: `~/.hermes/scripts/disk-hygiene.sh`) wipes `/tmp` every day at 07:00 (keep-set excludes only `chrome-linux`, `node-compile-cache`, `systemd-private*`, `ssh-*`, `.{X11,ICE,font,Test}-unix`).

`/tmp/target` is **NOT in the keep-set** → cargo build artifacts are deleted every morning.

Mitigations:
- Add `/tmp/target` to the cron keep-set (preferred for shared dev use)
- Per-project `CARGO_TARGET_DIR=~/.cargo/target/<name>` (escapes `/tmp` entirely)
- Disable the cron job during multi-day incremental work

## Quick verify pipeline

```bash
# 1. sccache server alive
pgrep -fa sccache | grep -v grep

# 2. wrapper applied
cd /tmp/sccache-test && cargo clean && touch src/main.rs && cargo build -v 2>&1 | grep Running | head -1
# expect: Running `/root/.cargo/bin/sccache ...`

# 3. version + cache state
sccache --version
sccache -s | head -25
```

## Files on this VM

- `~/.cargo/config.toml` — `[source.crates-io]` (rsproxy mirror), `[build] rustc-wrapper + target-dir`
- `/etc/profile.d/sccache.sh` — env wrapper + `sccache --start-server`
- `/root/.cargo/bin/sccache` — binary (0.17.0)
- `~/.hermes/scripts/disk-hygiene.sh` + `~/.hermes/scripts/.tmp-clean.py` — cron hygiene that wipes `/tmp/target`

## Related skills

- `rust-cargo-mirror-setup` — handles the `[source.crates-io]` / rsproxy sparse-protocol part of `~/.cargo/config.toml`. Pairs with this skill.
- `rust-wasm-gh-pages-deploy-pitfalls` — uses `cargo build` heavily; sccache no-op affects deploy iteration speed.