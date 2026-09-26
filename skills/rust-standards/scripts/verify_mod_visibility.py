#!/usr/bin/env python3
"""
Verify rust-standards §1 / §6.2: mod.rs `mod xxx;` must have NO
visibility prefix.

Per rust-standards (2026-09-26 user iteration):  in any `mod.rs`,
`mod r#xxx;` declarations MUST be bare — no `pub mod r#xxx;`,
no `pub(crate) mod r#xxx;`, no `pub(super) mod r#xxx;`.  The
visibility of items inside the module is controlled at the
declaration site of the item itself, not on the mod line.  `mod`
in mod.rs is always crate-internal (private to the module's
parent namespace), and visibility widening happens via `pub use`
in mod.rs's "middle stage" or via `pub`/`pub(crate)` on each
sub-module's items.

Rationale:
  - `mod r#xxx;` in mod.rs makes the module visible to the
    parent module's namespace (so `use super::*` in sub-files
    can resolve symbols).  Adding `pub`/`pub(crate)`/`pub(super)`
    on top of this is redundant — `mod` alone is the correct
    visibility for this layer.
  - Historically `pub(crate) mod r#xxx;` was sometimes used to
    keep sibling files visible across `crate::submodule::*`
    imports, but this is a workaround for missing
    `use super::*;` chains — the modern fix is always
    `mod r#xxx;` + sub-file first line `use super::*;`.

Exits 0 if clean, 1 if any violation.

Usage:
    python3 verify_mod_visibility.py [ROOT]
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path


# Match mod declarations in mod.rs:
#   - forbidden prefixes: `pub `, `pub(crate) `, `pub(super) `
#   - mod.rs only (per rule)
#   - we look at column-0 / indented mod declarations
MOD_DECL = re.compile(
    r"^(?P<vis>(?:pub(?:\([^)]*\))?\s+)?)mod\s+"
)


def _list_rs_files(root: Path) -> list[Path]:
    r = subprocess.run(
        ["find", str(root), "-name", "*.rs",
         "-not", "-path", "*/target/*",
         "-not", "-path", "*/.cargo/registry/*"],
        capture_output=True, text=True,
    )
    return [Path(line) for line in r.stdout.strip().splitlines() if line]


def _scan_raw_string_state(lines: list[str]) -> list[bool]:
    """For each line, True if inside a raw-string literal at column 0."""
    inside = [False] * len(lines)
    in_raw = False
    delim = ""
    for i, line in enumerate(lines):
        if in_raw:
            inside[i] = True
            close_marker = '"' + delim
            if close_marker in line:
                in_raw = False
                delim = ""
            continue
        m = re.search(r"r(#+)\"", line)
        if m:
            delim = m.group(1)
            rest = line[m.end():]
            close_marker = '"' + delim
            cpos = rest.find(close_marker)
            if cpos == -1:
                in_raw = True
                inside[i] = True
    return inside


def audit_one(path: Path) -> list[str]:
    """Per rust-standards: in mod.rs, `mod xxx;` MUST be bare."""
    basename = path.name
    if basename != "mod.rs":
        return []
    try:
        text = path.read_text()
    except (OSError, UnicodeDecodeError):
        return []
    lines = text.splitlines()
    inside_raw = _scan_raw_string_state(lines)
    violations: list[str] = []
    for i, line in enumerate(lines):
        if inside_raw[i]:
            continue
        m = MOD_DECL.match(line)
        if not m:
            continue
        vis = m.group("vis").strip()
        if vis == "":
            continue  # bare `mod` is the only allowed form
        violations.append(
            f"{path}:{i + 1}: `mod` declaration in mod.rs must be bare "
            f"(no visibility prefix); found `{vis}`: {line.strip()[:80]!r}"
        )
    return violations


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    if not root.is_dir():
        print(f"error: {root} is not a directory", file=sys.stderr)
        return 2
    files = _list_rs_files(root)
    total = 0
    files_with_v = 0
    for f in files:
        v = audit_one(f)
        if v:
            files_with_v += 1
            total += len(v)
            for line in v:
                print(line)
    print(f"\n=== mod.rs mod visibility (no `pub` prefix): "
          f"{total} violation(s) in {files_with_v} file(s) ===")
    return 0 if total == 0 else 1


if __name__ == "__main__":
    sys.exit(main())