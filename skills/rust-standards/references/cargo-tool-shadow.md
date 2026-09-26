# `~/.cargo/bin/<name>` shadows rustc/cargo `PATH`-spawned tools

This file gives the diagnostic + repair procedure when every `cargo build` /
`cargo clippy --fix` simultaneously fails on the workspace while producing
only `*.d` dep-info files in `target/debug/build/<crate>-<hash>/`.

## Symptoms

All failing at the same stage:

```
Compiling <crate> v<X.Y.Z>
error: failed to run custom build command for `<crate> v<X.Y.Z>`

Caused by:
  could not execute process `.../target/debug/build/<crate>-<hash>/build-script-build` (never executed)

Caused by:
  No such file or directory (os error 2)
```

Inside `.../target/debug/build/<crate>-<hash>/` you'll see one file:

```
build_script_build-<hash>.d          # rustc's dep-info; emit=dep-info
```

…and **no** `build_script_build-<hash>` (no executable). Every workspace
member fails the same way on its first `build.rs`. Procedural-macros (whose
codegen cargo invokes by absolute path) often compile fine.

## Mechanism (one paragraph)

`rustc` on Apple targets resolves the linker by **PATH lookup of the bare
tool name `cc`** (no absolute path is passed). If `~/.cargo/bin` precedes
`/usr/bin` on `PATH` — which is the default after `rustup` setup — any
binary in `~/.cargo/bin/` whose name collides with a system or rust toolchain
binary takes its place at link time. The shadowed binary either exits 0
without producing output (typical: an old CLI renamed in source but never
deleted, prints help and exits), or produces the wrong artifacts. Rustc
considers the link "successful", the build script `.exe` is never written,
and the next cargo step fails with `No such file or directory`.

The same trap fires for any tool rustc/cargo `PATH`-spawn by bare name:
`cc`, `c++`, `make`, `as`, `ld`, `ar`, `cargo` (for cargo subcommands invoked
from build scripts), `git` (build scripts that run `git rev-parse`), `bash`
(rare but possible). Cargo's own invocation of rustc uses
`/Users/sqs/.rustup/toolchains/.../bin/rustc` (an absolute path), so the
shadow only hits the *child* processes rustc spawns.

## Diagnostic recipe (4 commands, ~30 s)

```bash
# 1. Reproduce minimally — single crate, one job, no cache ambiguity.
rm -rf <repo>/target/debug/build/<crate>-* 2>/dev/null
RUSTC_LOG=info cargo build -p <one-affected-crate> -j 1 \
  2> /tmp/rustc.log 1>/tmp/cargo.log

# 2. Find the link command. The trailing 30+ lines after "preparing Executable"
#    show the full link argv. The first executable named (no path) is the
#    suspicious tool.
grep -A 1 "preparing Executable" /tmp/rustc.log | tail

# 3. The wrong tool's output (if the shadow is a CLI that prints help on
#    no-args) shows up immediately after. rustc forwards the stdout/stderr
#    of the linker and prints them as "linker stdout:" / "linker stderr:".
grep -E "linker stderr|linker stdout" -A 20 /tmp/rustc.log | head -50

# 4. Confirm which `cc` (or other tool) wins on PATH WITH cargo-home/bin first,
#    matching what cargo gives to rustc.
PATH="$HOME/.cargo/bin:$PATH" which cc
# Expect: /usr/bin/cc
# If it returns anything inside ~/.cargo/bin → that's the shadow culprit.
```

If steps 2–4 confirm the diagnosis, move to repair.

## Repair procedure

For the `cc` shadow (most common after `cc → crate` rename):

```bash
# Option A — relocate (recommended; you can restore it later under an alias
# name like `cc-crate-cli` if you actually want it on PATH).
mv ~/.cargo/bin/cc /tmp/cc-stale-by-$(date +%s)

# Option B — rename in place, preserving the slot.
mv ~/.cargo/bin/cc ~/.cargo/bin/cc-crate-cli       # alias kept for direct use

# Verify:
test -x ~/.cargo/bin/cc && echo "still present — re-check shadow list" \
  || echo "shadow cleared"

PATH="$HOME/.cargo/bin:$PATH" which cc             # must print /usr/bin/cc
```

For other shadows, apply the same pattern but substitute the colliding name.
**Never** `chmod 0` the file — it still resolves first in PATH and cargo
will see it as an unrunnable file rather than the system tool, producing a
*different* (worse) error.

After the shadow is gone, `cargo clean && cargo build` should succeed in
under a minute on warm cache. If it doesn't, re-check (re-grep for any
of the colliding names listed above).

## Pre-commit check

Run `scripts/check_cargo_bin_shadow.sh $HOME/.cargo/bin` before any commit
that touches `~/.cargo/bin/` (e.g., after running `cargo install <pkg>` or
after a bin rename). The script enumerates colliding names and exits 0
when none of them resolve into `~/.cargo/bin` via PATH lookup. Add it to
the rule-13 quick-check workflow.

## Common false-positives to check before repair

| Symptom | Real cause | Quick check |
|---|---|---|
| Same error but only on a single crate | actual missing dep / typo | `cargo build -p <crate> -v` |
| Same error reproduces on CI too | system tool genuinely missing | `which cc && which c++` (in CI env) |
| `cargo clean` makes it pass for ~1 build | stale build-script cache | manually `rm -rf target/debug/build` |
| `.d` file present + exit code from rustc | rustc itself crashing mid-link | `RUSTC_LOG=info` full log → look for non-linker error lines |

If the table row matches, **do not** assume shadow — fix the real problem
first.
