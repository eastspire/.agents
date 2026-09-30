---
name: rust-toolchain-macos
description: Install and configure a low-disk Rust toolchain on macOS.
version: 0.1.0
author: sqs, Hermes Agent
license: MIT
platforms: [macos]
metadata:
  hermes:
    tags: [rust, cargo, macos, build-cache, disk-usage]
    related_skills: [brew-install-on-mac]
---

# Rust toolchain setup on macOS (low-disk posture)

Use when the user asks to install Rust toolchain components, configure a build cache backend (sccache, mold, lld), reduce Cargo disk usage, or relocate Cargo caches. Triggers: "install rust", "cargo config", "sccache", "rust build cache", "cargo takes too much disk", "minimize cargo footprint".

Out of scope: writing Rust code, debugging compile errors inside a specific project, cross-compiling to non-Apple targets.

## When to Use

- First-time Rust install on a fresh Mac.
- Relocating Cargo state out of `~/.cargo` and `~/.rustup` to keep `$HOME` small.
- Adding a build cache (sccache) and verifying it actually caches.
- User pastes a snippet like `[build]\nrustc-wrapper = "/root/.cargo/bin/sccache"\ntarget-dir = "/tmp/target"` — paths look like Linux/container defaults; verify against this machine before writing.

## Don't use for

- General Rust language questions or project-level Cargo.toml authoring.
- Replacing rustup itself (rustup is the right install path; rustup-init still ships from `sh.rustup.rs`).

## Prerequisites

- `~/.cargo/env` exists (rustup is already installed) — or fall back to installing rustup via `curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh`.
- Homebrew on PATH for sccache install: `/opt/homebrew/bin/brew` (see `brew-install-on-mac` if missing).
- A writable `~/Library/Caches/` (standard on macOS).

## Procedure

1. **Confirm host context before copying any user-supplied path.** Run `whoami`, `echo $HOME`, `uname -m`. A snippet containing `/root/...` is Linux; a `~/.cargo` path on this Mac is `/Users/<you>/.cargo` (often already a symlink). Never copy a Linux-flavored path into a macOS config without translating it.
2. **Inventory current state:** `du -sh ~/.cargo ~/.rustup ~/Library/Caches/cargo-* ~/.cache/sccache 2>/dev/null` and `ls -la ~/.cargo` (catches the "already a symlink" case).
3. **Pick the install target.** Homebrew for tooling (`brew install sccache`), rustup for the actual Rust toolchain (rustup-managed binaries stay in `~/.cargo/bin` and `~/.rustup`). Don't try to install rustc via Homebrew.
4. **Relocate Cargo state** (if minimizing disk):
   - `mkdir -p ~/Library/Caches/cargo-home ~/Library/Caches/cargo-target ~/.cache/sccache`
   - `rsync -a ~/.cargo/ ~/Library/Caches/cargo-home/` (first-time move only)
   - `rm -rf ~/.cargo && ln -s ~/Library/Caches/cargo-home ~/.cargo`
   - In `~/.zshenv`: `export CARGO_HOME=$HOME/Library/Caches/cargo-home` and the sparse-registry vars. Note `CARGO_HOME` MUST be an env var — Cargo doesn't honor a `[env]`-style move in `config.toml`.
5. **Write `~/.cargo/config.toml`** with the working low-disk shape — `target-dir` in `~/Library/Caches/cargo-target`, sparse `[registries.crates-io]`, `[net] git-fetch-with-cli = true`, and rustflags `-C link-arg=-Wl,-dead_strip` for both Apple targets.
6. **Decide on a build cache backend:**
   - For Rust caching: sccache is the conventional choice, but verify it actually caches against the installed rustc — see Pitfall 1. Don't enable `rustc-wrapper` without that verification.
   - For C/C++/CUDA: sccache's S3/Redis/etc. backends still work even when the rustc backend is broken, but you still need a backend configured if you want them useful.
7. **Verify with a real build, not a config dump.** `cargo new --bin /tmp/probe`, `cargo add serde serde_json`, then `time cargo build --release` cold + after `touch src/main.rs` for warm. The warm number tells you whether incremental hit. For sccache specifically: `sccache -z` → `cargo build` → `sccache -s | grep "Hits rate"` — must show > 0% for the cache to be live. A 0% rate means sccache is silently passthrough.

## Pitfalls

1. **sccache may not cache rustc at all.** Older sccache bottles return "Server sent UnhandledCompile" for rustc ≥ 1.80's argv (split-debuginfo, `--print=sysroot`, etc.) and fall through to the real rustc — build succeeds, stats stay at 0. Symptom: `sccache -s` shows `Hits rate (Rust) 0.00%`. Symptom 2: sccache refuses to run when `CARGO_INCREMENTAL=1`, so enabling the wrapper actively breaks builds until you also set `incremental = false`. Combine the two and the wrapper is worse than nothing — never enable it without first running the verification in step 7. See `references/sccache-compatibility.md` for the version matrix.
2. **`/tmp/target` looks convenient, costs you on reboot.** macOS `/tmp` is wiped on every reboot, so any incremental cache there evaporates. Prefer `~/Library/Caches/cargo-target` — same disk-pressure benefit, but persistent.
3. **`CARGO_TARGET_DIR` and `build.target-dir` are not the same precedence.** Env var wins over config; setting both means the config line is dead code. Pick one source of truth (config.toml preferred — env vars are for things files can't do).
4. **`[env]` table in `config.toml` does not move `CARGO_HOME`.** Cargo reads `CARGO_HOME` only from the process environment. Setting it requires `~/.zshenv` (interactive + non-interactive) or `~/.zprofile` (login only). Use `~/.zshenv` for cross-shell availability.
5. **Don't paste a Linux container's path verbatim.** `/root/.cargo/...` is a Linux root-home convention; macOS root home is `/var/root` and your user home is `/Users/<you>`. When the user pastes `[build] rustc-wrapper = "/root/.cargo/bin/sccache"`, translate to `/Users/sqs/.local/bin/sccache-shim` or wherever the real binary lives, not literal.
6. **`rustc-wrapper` config field requires an absolute path or a name on PATH.** A relative path like `./sccache` is silently ignored by cargo in many versions. Use the full path to the wrapper script.
7. **`target-dir` in config.toml + `CARGO_TARGET_DIR` env var is a footgun.** If you later `export CARGO_TARGET_DIR=/somewhere` in a single session, that wins and the config line stops applying. If you want config.toml to be authoritative, unset the env var entirely.
8. **Stale `build/<crate>-<hash>/out/*` survives `cargo clean -p <crate>`.** When a project's `build.rs` reads an env var declared via `cargo:rerun-if-env-changed`, cargo's fingerprint only changes when that env var's *value* changes — not when the underlying source dir it points at changes (cargo hashes files, not directories). Switching the env var from a relative path to an absolute path can keep the same fingerprint hash and serve a stale generated file from the cache, even after `cargo clean -p <crate>`. When build-script output looks truncated or out of sync with its inputs, wipe both the build-script cache AND the fingerprint cache for that crate: `rm -rf <target-dir>/<triple>/<profile>/build/<crate>-* <target-dir>/<triple>/<profile>/.fingerprint/<crate>-*`. The `.fingerprint/` dir is what cargo consults to decide whether to re-run build.rs.
9. **`cargo build` / `cargo install` fails with `could not execute process .../build-script-build (never executed)` in a shell with 100+ injected env vars (VS Code, Hermes, Git IPC).** Symptom: rustc is invoked, the `build-script-build-<hash>.d` dep-info file is written to `<out-dir>`, but the executable itself is never produced; cargo then ENOENTs on `<out-dir>/build-script-build` (which is normally a hardlink to the executable). The same `cargo build` invocation succeeds when run in a minimal env — proving rustc itself is fine and the issue is interference from one or more inherited env vars (e.g. `VSCODE_INJECTION=1`, `__CFBundleIdentifier=com.microsoft.VSCode`, `CODELLDB_LAUNCH_CONNECT_FILE`, `DYLD_*` traces from VS Code's debugger/IPC). Mitigation: re-run cargo with only the env it actually needs — `env -i HOME=$HOME PATH=/Users/sqs/.rustup/toolchains/stable-aarch64-apple-darwin/bin:/usr/bin:/bin CARGO_HOME=$HOME/Library/Caches/cargo-home CARGO_TARGET_DIR=<path> cargo build` — and the build script's executable appears. Diagnosis recipe when this hits again: (a) `rm -rf <out-dir>` then reproduce with `cargo build -vv` and capture the rustc command line; (b) exec the exact rustc command in isolation under `env -i` — if it writes the binary, cargo-injection is the cause; if it doesn't, the bug is in rustc/cargo itself and worth a `cargo update` / `rustup update stable`. Do NOT spend time on cargo cache, sccache, or `target-dir` moves before verifying with the minimal-env repro.

## Verification

- `cargo --version` resolves, `which cargo` returns `~/Library/Caches/cargo-home/bin/cargo` (the symlink target).
- `du -sh ~/.cargo` returns the symlink size, not the underlying toolchain size; `du -sh ~/Library/Caches/cargo-home` shows the real 200+ MB.
- A throwaway probe project (`cargo new --bin /tmp/probe`, two trivial deps) cold-builds in a few seconds, warm-builds (after `touch src/main.rs`) in well under 1 s — proves incremental is hitting target dir.
- If sccache wrapper is enabled: `sccache -s | grep "Hits rate (Rust)"` non-zero after a second build of unchanged source.
- `~/.cargo` resolves through the symlink; `cargo --version` works from any cwd.

## Things that look correct but fail

- Enabling `rustc-wrapper = "/opt/homebrew/bin/sccache"` (sccache 0.18 direct) → either 0% hits or build failure from the incremental conflict.
- `target-dir = "/tmp/target"` → works, but the cache disappears on reboot, defeating incremental builds.
- Setting `CARGO_HOME` in `~/.cargo/config.toml` under an `[env]` table → silently ignored.
- `cargo install sccache` as a Homebrew alternative → works, but Homebrew bottle is the same upstream; no behavior difference.