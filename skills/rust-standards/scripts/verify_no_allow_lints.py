#!/usr/bin/env python3
"""
Verify rust-standards §14 (user rule 14, 2026-09-14): no
`#[allow(...)]` / `#[allow(unused)]` / `#[allow(clippy::xxx)]`
in production code.

Per rust-standards rule 14 (user 原话): "从根源修复 warn,
禁止使用 allow 宏".  clippy / rustc warnings must be fixed at
source, not silenced with attribute macros.

This script complements `audit_rust_standards.py` check 2
(which is git-diff scoped for PR review).  This script scans
the whole tree so a clean baseline doesn't accumulate
`#[allow]`s silently between PRs.

Detection rules:
  - `#[allow]` / `#[allow(...)]` / `#[allow(unused)]` /
    `#[allow(clippy::xxx)]` / `#[allow(non_snake_case)]` etc.
  - `#[expect(...)]` is also banned per the same rule (rare;
    user said `#[expect(...)]` is also forbidden in production
    except for the two documented exception cases).
  - Excluded: `#[allow(dead_code)]` etc. that are *inside*
    `#[cfg(test)] mod tests` blocks (test-only).
  - Excluded: comments.

Exits 0 if clean, 1 if any violation.

Usage:
    python3 verify_no_allow_lints.py [ROOT]
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path


# Match `#[allow(...)]` or `#[expect(...)]` attributes.
ALLOW_OR_EXPECT = re.compile(
    r"^\s*#\[\s*(?:allow|expect)\s*\("
)


def _list_rs_files(root: Path) -> list[Path]:
    r = subprocess.run(
        ["find", str(root), "-name", "*.rs",
         "-not", "-path", "*/target/*",
         "-not", "-path", "*/.cargo/registry/*"],
        capture_output=True, text=True,
    )
    return [Path(line) for line in r.stdout.strip().splitlines() if line]


def _is_inside_cfg_test(lines: list[str], idx: int) -> bool:
    """Return True if `lines[idx]` is inside a `#[cfg(test)] mod tests { ... }`
    block (test-only `#[allow(...)]` is exempt per the rule's
    documented exception)."""
    bracket_depth = 0
    inside_cfg = False
    cfg_enter_depth = -1
    for i, ln in enumerate(lines):
        s = ln.strip()
        if not inside_cfg and "#[cfg(test)]" in s and s.startswith("#["):
            inside_cfg = True
            # Find the line that opens the block
            for j in range(i + 1, min(i + 5, len(lines))):
                if "{" in lines[j]:
                    cfg_enter_depth = bracket_depth + (lines[j].count("{") - lines[j].count("}"))
                    bracket_depth = cfg_enter_depth
                    i = j
                    break
            continue
        if inside_cfg:
            bracket_depth += ln.count("{") - ln.count("}")
            if bracket_depth <= 0:
                inside_cfg = False
            elif i == idx:
                return True
            continue
    return False


def audit_one(path: Path) -> list[str]:
    try:
        text = path.read_text()
    except (OSError, UnicodeDecodeError):
        return []
    lines = text.splitlines()
    violations: list[str] = []
    for i, line in enumerate(lines):
        if not ALLOW_OR_EXPECT.match(line):
            continue
        # Test-only `#[allow]` is exempt per documented exception.
        if _is_inside_cfg_test(lines, i):
            continue
        violations.append(
            f"{path}:{i + 1}: `#[allow(...)]` / `#[expect(...)]` in "
            f"production code (§14) — fix warning at source: "
            f"{line.strip()[:80]!r}"
        )
    return violations


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    if not root.is_dir():
        print(f"error: {root} is not a directory", file=sys.stderr)
        return 2
    total = 0
    files_with_v = 0
    for f in _list_rs_files(root):
        # Skip tests/ — they're scoped separately (R14.7) and
        # `#[allow]` is acceptable in test helpers.
        if "tests" in f.parts:
            continue
        v = audit_one(f)
        if v:
            files_with_v += 1
            total += len(v)
            for line in v:
                print(line)
    print(f"\n=== no-allow-lints: "
          f"{total} violation(s) in {files_with_v} file(s) ===")
    return 0 if total == 0 else 1


if __name__ == "__main__":
    sys.exit(main())