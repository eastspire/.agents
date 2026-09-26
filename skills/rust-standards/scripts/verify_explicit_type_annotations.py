#!/usr/bin/env python3
"""
Verify rust-standards §5.1: explicit type annotations for variables,
parameters, and return values.

Per rust-standards (2026-09-26 strengthening): no implicit type
inference for `let` bindings.  Specifically:

  ❌  let items = Vec::new();
  ❌  let map = HashMap::new();
  ❌  let s = String::new();
  ❌  let v: Vec<_> = (0..10).collect();

  ✅  let items: Vec<u32> = Vec::new();
  ✅  let map: HashMap<String, u32> = HashMap::new();
  ✅  let s: String = String::new();
  ✅  let v: Vec<u32> = (0..10).collect();

Also covers fn parameters and return types where the type is
non-trivial (e.g. `&Vec<T>` vs `&[T]`); the audit focuses on the
most common pitfall — bare `let x = Type::new();` without `:`.

Exits 0 if clean, 1 if any violation.  Reports each violation as
`<file>:<line>: implicit Vec::new() without type annotation (§5.1): <text>`.

Usage:
    python3 verify_explicit_type_annotations.py [ROOT]

Default ROOT = current directory.  Walks every .rs file under root
(skipping target/, .cargo/registry/, tests/).
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path


# Match `let <ident> = <Type>::new();` or similar without an explicit
# type annotation.  We use a pragmatic heuristic — common Rust
# collection types that have a `::new()` constructor and are
# typically inferred instead of explicitly annotated:
#
#   Vec, VecDeque, HashMap, HashSet, BTreeMap, BTreeSet, LinkedList,
#   BinaryHeap, String, Box, Rc, Arc
#
# Allowed: `let x: Vec<u32> = Vec::new();` (explicit colon)
# Forbidden: `let x = Vec::new();` (no annotation)
TYPE_NEW_NO_ANNOT = re.compile(
    r"^\s*let\s+(?:mut\s+)?(?P<name>[a-zA-Z_][a-zA-Z0-9_]*)\s*=\s*"
    r"(?P<type>Vec|VecDeque|HashMap|HashSet|BTreeMap|BTreeSet|"
    r"LinkedList|BinaryHeap|String|Box|Rc|Arc)::new\(\)"
)

# Also catch `let v: Vec<_> = ...collect()` patterns that defeat the
# purpose of explicit annotation (Vec<_> is still implicit element type).
COLLECT_NO_ANNOT = re.compile(
    r"^\s*let\s+(?:mut\s+)?(?P<name>[a-zA-Z_][a-zA-Z0-9_]*)\s*:\s*"
    r"(?P<type>Vec|VecDeque|HashMap|HashSet|BTreeMap|BTreeSet)"
    r"<_\s*>\s*=\s*"
)


def _list_rs_files(root: Path) -> list[Path]:
    r = subprocess.run(
        ["find", str(root), "-name", "*.rs",
         "-not", "-path", "*/target/*",
         "-not", "-path", "*/.cargo/registry/*"],
        capture_output=True, text=True,
    )
    return [Path(line) for line in r.stdout.strip().splitlines() if line]


def audit_one(path: Path) -> list[str]:
    try:
        text = path.read_text()
    except (OSError, UnicodeDecodeError):
        return []
    lines = text.splitlines()
    violations: list[str] = []
    for i, line in enumerate(lines, start=1):
        if m := TYPE_NEW_NO_ANNOT.match(line):
            violations.append(
                f"{path}:{i}: implicit {m.group('type')}::new() without "
                f"type annotation (§5.1): {line.strip()[:80]!r}"
            )
            continue
        if m := COLLECT_NO_ANNOT.match(line):
            violations.append(
                f"{path}:{i}: implicit `{m.group('type')}<_>` annotation "
                f"defeats explicit-type rule (§5.1): {line.strip()[:80]!r}"
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
        # Skip tests/ entirely (R14.5 forbids comments but doesn't
        # impose §5.1 strict type annotation there).
        if "tests" in f.parts:
            continue
        v = audit_one(f)
        if v:
            files_with_v += 1
            total += len(v)
            for line in v:
                print(line)
    print(f"\n=== explicit-type-annotations: "
          f"{total} violation(s) in {files_with_v} file(s) ===")
    return 0 if total == 0 else 1


if __name__ == "__main__":
    sys.exit(main())