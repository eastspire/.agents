#!/usr/bin/env python3
"""
Verify rust-standards §5.2 (new, 2026-09-26 third iteration):
closure parameters MUST have explicit type annotations.

User original (2026-09-26 third iteration):
  "闭包参数需要显示标注"

Specifically:

  ❌  let f = |x, y| x + y;
  ❌  vec.iter().map(|x| x * 2).collect()
  ❌  .filter(|item| item.is_valid())

  ✅  let f = |x: u32, y: u32| -> u32 { x + y };
  ✅  vec.iter().map(|x: &u32| x * 2).collect()
  ✅  .filter(|item: &Item| item.is_valid())

Exemptions (legitimate cases):
  - `||` (empty parameter list) — no params, no annotation needed
  - `|..|` (rest pattern) — no name, no annotation possible
  - `|(a, b): &(T, U)|` — pattern destructuring WITH type annotation
    on the whole tuple (this IS an explicit annotation)
  - `|&x: &T|` — single ref pattern with type annotation
  - inside `tests/` directory (R14.7 self-contained)

Detection approach:
  - Find all `|<params>|` patterns in the source.
  - For each, parse comma-separated params.
  - Each param is either:
    * `_` or `_name` — needs `: T` suffix
    * `name` (bare identifier) — needs `: T` suffix
    * `name: T` — ok
    * `(pat): T` — tuple pattern with type — ok
    * `&name: T` or `&mut name: T` — ref with type — ok
    * `..` — rest pattern — ok
  - Report any param that is just a bare identifier or `_name`
    without `: T`.

This script is heuristic — it cannot understand every valid
closure pattern (closures that destructure complex nested
patterns might false-positive).  When in doubt, prefer
false-negative (miss) over false-positive (false flag).  When
implementing new code, prefer explicit type annotation per
project convention.

Exits 0 if clean, 1 if any violation.

Usage:
    python3 verify_closure_type_annotations.py [ROOT]
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path


# Find closures.  Tricky because:
#   - `||` (no params) — must not match
#   - `| x |` (single param) — must match
#   - `|x: u32, y: String|` (multiple typed) — must match
#   - `|(a, b): &(T, U)|` (tuple pattern with type) — must match
#   - `|..|` (rest only) — must not flag
#   - `|x: &Foo|` (single typed) — must match
#   - `|x|` — violation
#
# Strategy: regex that captures |<params>|, then we parse the
# captured params in Python (not regex backrefs) for robustness.
#
# We also need to avoid:
#   - bitwise OR in expressions (e.g. `a | b`) — outside closures
#   - `||` operator (e.g. `a || b`) — single `|`, not `|...|`
#   - generics like `Vec<u32>` — `<u32>` not confused with `|`
#
# Heuristic: look for `|<non-empty-content>|` where content does
# not start with `=` or `|` (so `||` operator excluded).  Then
# split content by `,` at top-level (no `<>` nesting counted
# here — but Rust closures rarely have generic params inside).
CLOSURE = re.compile(
    r"\|(?P<params>[^|=][^|]*?)\|"
)


def _list_rs_files(root: Path) -> list[Path]:
    r = subprocess.run(
        ["find", str(root), "-name", "*.rs",
         "-not", "-path", "*/target/*",
         "-not", "-path", "*/.cargo/registry/*"],
        capture_output=True, text=True,
    )
    return [Path(line) for line in r.stdout.strip().splitlines() if line]


def _has_explicit_type(param: str) -> bool:
    """Return True if the param has explicit `: T` annotation
    or is a recognized pattern that doesn't need one (rest,
    destructuring with type, etc.)."""
    p = param.strip()
    if not p:
        return True  # empty (shouldn't happen but be safe)
    if p == "..":
        return True  # rest pattern
    # `&pat: T` or `&mut pat: T`
    if p.startswith(("&mut ", "&")):
        # Strip leading ref, check for `: T`
        rest = p.lstrip("&").lstrip("mut ").lstrip()
        if ":" in rest:
            # Has explicit type after ref pattern
            return True
        # `&x` without `: T` — violation
        return False
    # `(pat): T` — tuple destructuring with type
    if p.startswith("(") and ") :" in p:
        return True
    if ":" in p:
        # Walk through to find unbracketed `:`
        depth = 0
        for i, ch in enumerate(p):
            if ch in "([{":
                depth += 1
            elif ch in ")]}":
                depth -= 1
            elif ch == ":" and depth == 0:
                # has explicit type
                return True
    return False


def audit_one(path: Path) -> list[str]:
    try:
        text = path.read_text()
    except (OSError, UnicodeDecodeError):
        return []
    violations: list[str] = []
    for i, line in enumerate(text.splitlines(), start=1):
        # Skip comments — we don't want to flag closure-shaped
        # content inside `// ...` lines.
        if line.lstrip().startswith(("/", "*")):
            continue
        for m in CLOSURE.finditer(line):
            params_str = m.group("params")
            # Split by `,` at depth 0
            params = _split_top_commas(params_str)
            for param in params:
                if not _has_explicit_type(param):
                    violations.append(
                        f"{path}:{i}: closure parameter without "
                        f"explicit type annotation (§5.2): {param.strip()!r} "
                        f"in `|...|`"
                    )
    return violations


def _split_top_commas(s: str) -> list[str]:
    """Split string by `,` at depth 0 (no nesting in <>, (), etc.)."""
    out: list[str] = []
    depth = 0
    cur = ""
    for ch in s:
        if ch in "([{<":
            depth += 1
            cur += ch
        elif ch in ")]}>":
            depth -= 1
            cur += ch
        elif ch == "," and depth == 0:
            out.append(cur)
            cur = ""
        else:
            cur += ch
    if cur:
        out.append(cur)
    return out


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    if not root.is_dir():
        print(f"error: {root} is not a directory", file=sys.stderr)
        return 2
    total = 0
    files_with_v = 0
    for f in _list_rs_files(root):
        if "tests" in f.parts:
            continue
        v = audit_one(f)
        if v:
            files_with_v += 1
            total += len(v)
            for line in v:
                print(line)
    print(f"\n=== closure-params-explicit-type: "
          f"{total} violation(s) in {files_with_v} file(s) ===")
    return 0 if total == 0 else 1


if __name__ == "__main__":
    sys.exit(main())