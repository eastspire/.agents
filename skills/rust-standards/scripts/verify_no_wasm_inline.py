#!/usr/bin/env python3
"""
Verify rust-standards §12: WASM projects (cargo crate-type contains
"cdylib") MUST NOT have `#[inline]` / `#[inline(always)]` /
`#[inline(never)]` attributes.

Per rust-standards rule 12 (user 原话, 2026-09-26): "WASM 项目
禁止所有 inline 注解".  WASM codegen handles inlining itself; manual
inline annotations force the wasm-opt pipeline to skip functions,
which makes the final binary 10-50% larger without measurable
speedup.

This script detects:
  1. `[lib] crate-type = ["cdylib", ...]` in any Cargo.toml — declares
     the crate as a WASM build.
  2. Any `#[inline]` / `#[inline(always)]` / `#[inline(never)]` in
     the corresponding src/ tree → violation.

Per crate, only audits the src/ trees of crates that have cdylib
in crate-type.  Pure rust crates are ignored.

Exits 0 if clean, 1 if any violation.

Usage:
    python3 verify_no_wasm_inline.py [ROOT]
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path


CDYLIB_RE = re.compile(r'crate-type\s*=\s*\[?\s*["\']cdylib["\']')
INLINE_ATTR = re.compile(r"^\s*#\[\s*inline(?:\s*\([^\)]*\))?\s*\]")


def _list_rs_files(root: Path) -> list[Path]:
    r = subprocess.run(
        ["find", str(root), "-name", "*.rs",
         "-not", "-path", "*/target/*",
         "-not", "-path", "*/.cargo/registry/*"],
        capture_output=True, text=True,
    )
    return [Path(line) for line in r.stdout.strip().splitlines() if line]


def _is_cdylib_crate(cargo_toml: Path) -> bool:
    try:
        text = cargo_toml.read_text()
    except (OSError, UnicodeDecodeError):
        return False
    return bool(CDYLIB_RE.search(text))


def _find_cdylib_crates(root: Path) -> list[Path]:
    """Return directories of all cdylib crates under root."""
    out: list[Path] = []
    for cargo in root.rglob("Cargo.toml"):
        # Skip target/ and .cargo/registry/ subtrees
        parts = cargo.parts
        if any(p in ("target", "registry") for p in parts):
            continue
        if _is_cdylib_crate(cargo):
            out.append(cargo.parent)
    return out


def audit_one(path: Path) -> list[str]:
    try:
        text = path.read_text()
    except (OSError, UnicodeDecodeError):
        return []
    violations: list[str] = []
    for i, line in enumerate(text.splitlines(), start=1):
        if INLINE_ATTR.match(line):
            violations.append(
                f"{path}:{i}: `#[inline(...)]` in WASM crate (§12): "
                f"{line.strip()[:80]!r}"
            )
    return violations


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    if not root.is_dir():
        print(f"error: {root} is not a directory", file=sys.stderr)
        return 2
    crates = _find_cdylib_crates(root)
    if not crates:
        print("=== no-wasm-inline: 0 cdylib crates; rule §12 not applicable ===")
        return 0
    total = 0
    files_with_v = 0
    for crate_dir in crates:
        for rs in _list_rs_files(crate_dir):
            v = audit_one(rs)
            if v:
                files_with_v += 1
                total += len(v)
                for line in v:
                    print(line)
    print(f"\n=== no-wasm-inline: "
          f"{total} violation(s) in {files_with_v} file(s) "
          f"across {len(crates)} cdylib crate(s) ===")
    return 0 if total == 0 else 1


if __name__ == "__main__":
    sys.exit(main())