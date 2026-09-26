#!/usr/bin/env bash
# check_cargo_bin_shadow.sh — detect *unexpected* binaries in a cargo bin dir
# whose name shadows a tool rustc/cargo PATH-spawns by bare name.
#
# Legitimate rustup-managed proxies (`cargo`, `rustc`, `cargo-clippy`, …) in
# $CARGO_BIN_DIR are the expected contents and are exempt from this check.
# What this script catches: stray extras that look like real tools, e.g. an
# old `cc` binary left behind after a `cc → crate` rename, or a misnamed
# installer script dropped in `cargo install` style.
#
# Usage:
#   bash check_cargo_bin_shadow.sh [CARGO_BIN_DIR]
#       default: $HOME/.cargo/bin
#
# Exit codes:
#   0 — clean (no unexpected shadows)
#   1 — at least one unexpected shadow; printed in form
#         `<bin> -> <full path> (would shadow <tool>)`
#
# Run this from a pre-commit hook or right after `cargo install <pkg>` —
# catches the trap before a `cargo build` is run.

set -euo pipefail

CARGO_BIN_DIR="${1:-$HOME/.cargo/bin}"

# Tool names rustc/cargo PATH-spawn by bare name during a build.
TOOLS=(cc c++ make as ld ar cargo git bash)

# Bins that legitimately live in a rustup-managed `~/.cargo/bin/` because
# `rustup` installs symlinks there. Aliases for the same tool (e.g. `cargo`
# and `cargo-clippy`) both point at `rustup` and are normal. Anything in
# this list is exempt from the shadow check.
RUSTUP_MANAGED_BINS=(
  cargo
  cargo-clippy
  cargo-fmt
  cargo-miri
  clippy-driver
  rls
  rust-analyzer
  rust-gdb
  rust-gdbgui
  rust-lldb
  rustc
  rustdoc
  rustfmt
)

if [[ ! -d "$CARGO_BIN_DIR" ]]; then
  echo "no such directory: $CARGO_BIN_DIR" >&2
  exit 1
fi

# For each candidate bin in the dir: is it the canonical rustup proxy, or
# is it an unexpected file? Two signals exempt it:
#   1. Name is in RUSTUP_MANAGED_BINS.
#   2. File is a symlink whose target resolves to `rustup`.
is_rustup_managed() {
  local f="$1"
  local base
  base="$(basename "$f")"

  for ok in "${RUSTUP_MANAGED_BINS[@]}"; do
    if [[ "$base" == "$ok" ]]; then
      return 0
    fi
  done

  if [[ -L "$f" ]]; then
    local target
    target="$(readlink "$f")"
    case "$target" in
      rustup|*/rustup) return 0 ;;
    esac
    # Two-level symlinks (`cargo -> rustup` where `rustup` itself is a
    # symlink to the actual binary).
    if [[ -L "$CARGO_BIN_DIR/$target" ]]; then
      target="$(readlink "$CARGO_BIN_DIR/$target")"
      case "$target" in
        rustup|*/rustup) return 0 ;;
      esac
    fi
  fi

  return 1
}

has_shadow=0
for tool in "${TOOLS[@]}"; do
  # PATH-lookup as cargo would see it: CARGO_BIN_DIR precedes system dirs.
  bin_path="$(PATH="$CARGO_BIN_DIR:$PATH" command -v "$tool" || true)"
  if [[ -z "$bin_path" ]]; then
    continue
  fi

  # If the resolution points OUTSIDE CARGO_BIN_DIR, this tool is not
  # shadowed from this bin dir.
  case "$bin_path" in
    "$CARGO_BIN_DIR"/*) ;;
    *) continue ;;
  esac

  # Exempt rustup-managed proxies.
  if is_rustup_managed "$bin_path"; then
    continue
  fi

  # Exempt non-executable entries (degenerate but not an active shadow).
  if [[ ! -x "$bin_path" ]]; then
    continue
  fi

  # Real, runnable, non-rustup-managed bin in CARGO_BIN_DIR with a tool name.
  # This is the trap.
  echo "$bin_path  (would shadow system $tool)"
  has_shadow=1
done

if [[ "$has_shadow" -eq 1 ]]; then
  echo
  echo "Unexpected shadow in $CARGO_BIN_DIR — see references/cargo-tool-shadow.md" >&2
  exit 1
fi

echo "OK: no unexpected shadow in $CARGO_BIN_DIR (tools: ${TOOLS[*]})"
exit 0
