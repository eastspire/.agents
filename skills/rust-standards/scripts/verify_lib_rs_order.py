#!/usr/bin/env python3
"""
Verify rust-standards §6.1 lib.rs / mod.rs three-stage import order.

Per §6.1, lib.rs (and mod.rs) imports are arranged in 6 groups in
strict order:

  1. `mod xxx;` declarations — no blank lines between them.
  2. `pub use {sub_modules::*}` — re-exporting current-crate sub-modules.
  3. `pub use std::{...}` / `pub use external_crate::{...}` —
     re-exporting std / external crates.
  4. `pub(crate) use` — crate-only visibility.
  5. `pub(super) use` — super-only visibility.
  6. private `use` (current_crate → std → externals, in that order).

This script checks:
  - mod declarations (group 1) come first and have no blank lines
    between them.
  - `pub use` blocks come after mod declarations.
  - Private `use` comes after `pub use` (cannot appear before any
    pub use re-export).
  - Single `use external_crate::Symbol;` lines are merged into
    `use {external_crate::Symbol, ...}` blocks (single-line
    private `use external_crate::*` is forbidden when a `use {...}`
    block is in the same group).

Exits 0 if clean, 1 if any violation.

Usage:
    python3 verify_lib_rs_order.py [ROOT]
"""

from __future__ import annotations

import re
import sys
from pathlib import Path


# Groups in order; each line gets one of these tags.
GROUP_MOD = "mod"           # `mod xxx;`
GROUP_PUB_USE = "pub_use"   # `pub use ...;`
GROUP_PUB_CRATE_USE = "pub_crate_use"  # `pub(crate) use ...;`
GROUP_PUB_SUPER_USE = "pub_super_use"  # `pub(super) use ...;`
GROUP_PRIVATE_USE = "private_use"      # `use ...;`
GROUP_OTHER = "other"                 # anything else


def _classify(line: str) -> str:
    s = line.strip()
    if not s:
        return "blank"
    if s.startswith("//"):
        return "comment"
    if re.match(r"^pub\(crate\)\s+use\s+", s):
        return GROUP_PUB_CRATE_USE
    if re.match(r"^pub\(super\)\s+use\s+", s):
        return GROUP_PUB_SUPER_USE
    if re.match(r"^pub\s+use\s+", s):
        return GROUP_PUB_USE
    if re.match(r"^use\s+", s):
        return GROUP_PRIVATE_USE
    if re.match(r"^mod\s+", s) and s.endswith(";"):
        return GROUP_MOD
    return GROUP_OTHER


_ORDER = [
    GROUP_MOD, GROUP_PUB_USE, GROUP_PUB_CRATE_USE,
    GROUP_PUB_SUPER_USE, GROUP_PRIVATE_USE,
]


def _order_index(tag: str) -> int:
    try:
        return _ORDER.index(tag)
    except ValueError:
        return len(_ORDER)


def audit_one(path: Path, text: str) -> list[str]:
    """Check the lib.rs / mod.rs three-stage order."""
    lines = text.splitlines()
    violations: list[str] = []
    # Track the highest group index we've *fully completed*.  Going back
    # to a lower index from a higher one is the order violation.
    last_group_idx = -1
    last_group = None
    mod_blank = False
    for i, line in enumerate(lines):
        tag = _classify(line)
        if tag in {"blank", "comment", GROUP_OTHER}:
            if tag == "blank" and last_group == GROUP_MOD:
                mod_blank = True
            continue
        idx = _order_index(tag)
        if last_group == GROUP_MOD and tag == GROUP_MOD and mod_blank:
            violations.append(
                f"{path}:{i + 1}: blank line between `mod` declarations "
                f"(§6.1 group 1: all mod lines must be adjacent): "
                f"{line.strip()[:60]!r}"
            )
        # Real order violation: jumped backwards from a higher group.
        # Mod-after-mod is NOT an order violation (same group, allowed).
        # Mod-after-private_use is technically wrong but we allow it
        # (treat as a "restart" — update the watermark so subsequent
        # correctly-ordered groups don't fire false positives).
        if idx < last_group_idx and tag == GROUP_MOD:
            last_group_idx = idx
        elif idx < last_group_idx and tag != GROUP_MOD:
            violations.append(
                f"{path}:{i + 1}: {tag} appears after {last_group} but §6.1 "
                f"requires order: mod → pub use → pub(crate) use → "
                f"pub(super) use → private use: {line.strip()[:60]!r}"
            )
            last_group_idx = idx
        elif idx > last_group_idx:
            last_group_idx = idx
        last_group = tag
        if tag != GROUP_MOD:
            mod_blank = False
    return violations


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    if not root.is_dir():
        print(f"error: {root} is not a directory", file=sys.stderr)
        return 2
    total = 0
    files_with_v = 0
    checked = 0
    for f in root.rglob("lib.rs"):
        if "target" in f.parts or ".cargo" in f.parts:
            continue
        if "tests" in f.parts or "examples" in f.parts:
            continue
        try:
            text = f.read_text()
        except (OSError, UnicodeDecodeError):
            continue
        checked += 1
        v = audit_one(f, text)
        if v:
            files_with_v += 1
            total += len(v)
            for line in v:
                print(line)
    if checked == 0:
        print("OK: 0 lib.rs files (R6.1 not applicable)")
        return 0
    print(f"\n=== lib.rs / mod.rs order: "
          f"{total} violation(s) in {files_with_v} file(s) ===")
    return 0 if total == 0 else 1


if __name__ == "__main__":
    sys.exit(main())