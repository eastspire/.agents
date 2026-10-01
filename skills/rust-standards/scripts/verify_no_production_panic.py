#!/usr/bin/env python3
"""
Verify that production code contains no `panic!` / `.expect(` / `.unwrap()`
(R11.4, audit check 3).

Why this exists
---------------
`audit_rust_standards.py` check 3 implements this rule as an inline shell
pipeline over `git diff origin/master HEAD`, which means it only ever sees
lines the branch *adds*. Two consequences, both observed on euv:

  1. The pre-commit hook could not run it at all — `staged_file_gate.py`
     drives per-file verifiers through their `audit_one()` entry point, and
     this rule had no such script. So a rule the audit enforced and the
     hook did not is a rule that does not hold at commit time, which is
     exactly how `cli/src/build/inline.rs` survived.
  2. A `+` line that is only a comment was reported as a violation, so
     prose describing a *removed* panic ("the old `x().expect(..)` could
     panic") counted as a live panic. The audit script now skips comment
     lines; this script does the same at file level, by construction.

Per audit-pitfalls #41, `try_X().unwrap()` in a `get_X` wrapper is an
upstream idiom: the panic-on-missing contract is part of that wrapper's
documented API, so it is exempt. Per #42, `macros/` conventionally panics
in macro internals to surface user errors through compiler diagnostics.

Test code is exempt everywhere: `tests/`, `#[cfg(test)] mod`, and
`#[test]` / `#[wasm_bindgen_test]` bodies are where a panic is the
assertion.

Usage:
    python3 verify_no_production_panic.py [ROOT]
    python3 verify_no_production_panic.py [ROOT] --file PATH   # gate mode

Exit 0 if clean, 1 if any violation, 2 on usage error.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

PANIC = re.compile(r"(?<![A-Za-z0-9_])(?:panic!\s*\(|\.expect\s*\(|\.unwrap\s*\()")

# audit-pitfalls #41: the get_X wrapper idiom.
TRY_UNWRAP = re.compile(
    r"(?:try_|[Ss]elf::try_)[A-Za-z0-9_]*\s*\(.*\)\s*\.unwrap\s*\(\s*\)"
    r"|(?:try_|[Ss]elf::try_)[A-Za-z0-9_]*\s*\(.*\)\s*\.await\s*\.unwrap\s*\(\s*\)"
    r"|Regex::new\s*\(.*\)\s*\.expect\s*\("
)

EXEMPT_DIRS = {"target", ".cargo", "node_modules"}


def _is_comment(line: str) -> bool:
    stripped = line.lstrip()
    return stripped.startswith(("//", "/*", "*", "*/"))


def _inside_test_scope(lines: list[str], index: int) -> bool:
    """True when `lines[index]` sits inside a `#[cfg(test)]` / test fn."""
    depth = 0
    in_test_mod = False
    in_test_fn = False
    for i in range(0, index + 1):
        line = lines[i]
        stripped = line.strip()
        if re.match(r"#\[(cfg\(test\)|test|wasm_bindgen_test|bench)\]", stripped):
            # the attribute governs the item that follows
            if in_test_mod or in_test_fn:
                continue
            nxt = lines[i + 1] if i + 1 < len(lines) else ""
            if re.match(r"\s*(pub\s+)?(async\s+)?fn\b", nxt) or re.match(r"\s*(pub\s+)?mod\b", nxt):
                if re.match(r"\s*(pub\s+)?mod\b", nxt):
                    in_test_mod = True
                else:
                    in_test_fn = True
        if re.match(r"(pub\s+)?(async\s+)?fn\b", stripped) and in_test_fn:
            pass
        depth += line.count("{") - line.count("}")
        if in_test_mod and depth <= 0 and i > 0:
            in_test_mod = False
    return in_test_mod or in_test_fn


def _exempt_path(path: Path, root: Path) -> bool:
    parts = path.relative_to(root).parts
    if "tests" in parts:
        return True
    if any(part in EXEMPT_DIRS for part in parts):
        return True
    if "tmp" in parts:
        return True
    if "macros" in parts:
        return True
    return False


def audit_one(path: Path, root: Path | None = None) -> list[str]:
    if root is None:
        root = _infer_root(path)
    if _exempt_path(path, root):
        return []
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return []
    out: list[str] = []
    lines = text.split("\n")
    for index, line in enumerate(lines):
        if _is_comment(line):
            continue
        if not PANIC.search(line):
            continue
        if TRY_UNWRAP.search(line):
            continue
        if _inside_test_scope(lines, index):
            continue
        out.append(f"{path.relative_to(root)}:{index + 1}: {line.strip()[:100]}")
    return out


def _infer_root(path: Path) -> Path:
    for candidate in [path.parent, *path.parents]:
        if candidate.name == "src":
            return candidate.parent
    return path.parent


def main() -> int:
    args = sys.argv[1:]
    if not args:
        print("error: usage: verify_no_production_panic.py [ROOT] [--file PATH]", file=sys.stderr)
        return 2
    if "--file" in args:
        root = Path(args[0]).resolve()
        path = Path(args[args.index("--file") + 1]).resolve()
        found = audit_one(path, root)
        for line in found:
            print(line)
        return 1 if found else 0
    root = Path(args[0]).resolve()
    if not root.is_dir():
        print(f"error: {root} is not a directory", file=sys.stderr)
        return 2
    total: list[str] = []
    for path in sorted(root.rglob("*.rs")):
        if any(part in EXEMPT_DIRS for part in path.parts):
            continue
        total += audit_one(path, root)
    for line in total[:20]:
        print(line)
    print(f"=== production panic/expect/unwrap (R11.4): {len(total)} violation(s) ===")
    return 1 if total else 0


if __name__ == "__main__":
    raise SystemExit(main())
