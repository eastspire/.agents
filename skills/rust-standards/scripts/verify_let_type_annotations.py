#!/usr/bin/env python3
"""
Verify rust-standards §5.1: ALL `let` bindings MUST have explicit
type annotations (rule 6 / 2026-09-26 third iteration).

User original (2026-09-26 third iteration):
  "let 的类型必须要显示标注 (包含 let _ = )"

This is a strengthening of `verify_explicit_type_annotations.py`
(check 31) which only catches collection constructors without
type annotation.  The new rule is far broader: NO `let` binding
may omit its type.  Specifically:

  ❌  let x = 5;
  ❌  let s = "hello";
  ❌  let v = vec![1, 2, 3];
  ❌  let _ = fs::remove_dir_all(&temp_dir).await;   // user explicit
  ❌  let opt = some_fn();

  ✅  let x: u32 = 5;
  ✅  let s: &str = "hello";
  ✅  let v: Vec<u32> = vec![1, 2, 3];
  ✅  let _: Result<()> = fs::remove_dir_all(&temp_dir).await;
  ✅  let opt: Option<u32> = some_fn();

Exemptions (legitimate cases where type inference is the spec):
  - `let <pat>: binding = (Some::<T>::None | None::<T>)` — explicit
    generic annotation, no need for `:` re-statement.
  - `if let Some(x) = ...` / `while let Some(x) = ...` patterns —
    these are pattern bindings, not `let` statements.
  - Inside `tests/` directory (R14.7 self-contained).
  - `let _ = ...` is **also** banned per user explicit; we
    require `let _: T = ...`.  Rationale: `let _ = expr;`
    hides the return type from the reader and is a frequent
    source of silently dropped Result errors.  Even on discard,
    the type carries signal (the reader knows what shape is
    being discarded).

This script is the broader successor to
`verify_explicit_type_annotations.py` (check 31).  Check 31
remains as a subset-style "collection constructors specifically"
check; this script (check 33) is the comprehensive form.

Exits 0 if clean, 1 if any violation.

Usage:
    python3 verify_let_type_annotations.py [ROOT]
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path


# Match `let <pat> = <expr>;` where `<pat>` does NOT contain `:`
# (no type annotation).  Pattern captures the binding name.
#
# We must distinguish:
#   let x = ...;           ← violation (no type)
#   let x: u32 = ...;      ← ok (has type)
#   let mut x = ...;       ← violation
#   let mut x: u32 = ...;  ← ok
#   let _ = ...;           ← violation (per user explicit)
#   let _: T = ...;        ← ok
#   let (a, b) = ...;      ← violation (no type) — but tuple
#                             destructuring is uncommon; treat as
#                             violation so users add `: (T, U)`
#   if let Some(x) = ...;  ← NOT a `let` statement (it's a
#                             pattern guard in if/while); regex
#                             must not match.
#
# Regex: starts with `let `, followed by binding name (with optional
# `mut`), then either `: ` (type annotation present) or ` = `
# (no annotation — violation).
LET_NO_ANNOT = re.compile(
    r"^\s*let\s+(?:mut\s+)?"
    r"(?P<pat>(?:\([^)]*\))?(?:_[a-zA-Z0-9_]*|[a-zA-Z_][a-zA-Z0-9_]*)"
    r"(?:\s*:\s*[^=]+?)?)"  # optional `: type` (non-greedy, must not consume `=`)
    r"\s*=\s*"                # the `=` after binding
)


def _list_rs_files(root: Path) -> list[Path]:
    r = subprocess.run(
        ["find", str(root), "-name", "*.rs",
         "-not", "-path", "*/target/*",
         "-not", "-path", "*/.cargo/registry/*"],
        capture_output=True, text=True,
    )
    return [Path(line) for line in r.stdout.strip().splitlines() if line]


def _has_type_annotation(pat: str) -> bool:
    """Return True if the binding pattern already has `:` type
    annotation (e.g. `x: u32`, `_: Result<()>`).  `:` inside
    generics like `Option::<u32>` doesn't count; we look for
    `:` followed by space and a type-like character."""
    # Strip the leading optional `mut ` already matched by
    # LET_NO_ANNOT's prefix (we get the post-mut pat).
    if ":" in pat:
        # Find `:` not inside angle brackets (rough heuristic)
        depth = 0
        for i, ch in enumerate(pat):
            if ch == "<":
                depth += 1
            elif ch == ">":
                depth -= 1
            elif ch == ":" and depth == 0:
                # Has explicit type annotation
                rest = pat[i + 1:].lstrip()
                if rest and not rest.startswith("="):
                    return True
                # colon but no real type? treat as no annotation
                return False
    return False


def audit_one(path: Path) -> list[str]:
    try:
        text = path.read_text()
    except (OSError, UnicodeDecodeError):
        return []
    violations: list[str] = []
    for i, line in enumerate(text.splitlines(), start=1):
        # Skip `if let` / `while let` pattern guards
        stripped = line.lstrip()
        if stripped.startswith(("if let ", "while let ", "} else if let ")):
            continue
        # Skip let-chains (Rust 2024 `if let X = ... && let Y = ...`)
        if "&&" in stripped and stripped.startswith("let "):
            continue
        m = LET_NO_ANNOT.match(line)
        if not m:
            continue
        pat = m.group("pat").strip()
        if _has_type_annotation(pat):
            continue
        violations.append(
            f"{path}:{i}: `let` binding without explicit type annotation "
            f"per §5.1: {line.strip()[:80]!r}"
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
        if "tests" in f.parts:
            continue
        v = audit_one(f)
        if v:
            files_with_v += 1
            total += len(v)
            for line in v:
                print(line)
    print(f"\n=== let-bindings-explicit-type: "
          f"{total} violation(s) in {files_with_v} file(s) ===")
    return 0 if total == 0 else 1


if __name__ == "__main__":
    sys.exit(main())