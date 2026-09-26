#!/usr/bin/env python3
"""
Verify §9.2 fn parameter style: no `impl Trait` in fn parameters,
must use generic params + `where T: Trait` clause.

Per rust-standards §9.2:

  fn parse<T: FromStr>(input: T) -> Result<T, Error>     ❌ inline bound
  fn parse<T>(input: T) -> Result<T, Error>             ✅ generic + where
  where T: FromStr,

  fn f(x: impl AsRef<str>) -> ...                        ❌ impl param
  fn f<T>(x: T) -> ... where T: AsRef<str>               ✅

We scan every non-tests .rs file for fn signatures containing `impl
<Ident>` at parameter position.  Detection is column-0 / indented
declaration of `fn` or inside `impl` blocks (method receivers like
`&self` / `&mut self` are skipped).

Exit 0 if no violation, 1 with list of violations otherwise.

Usage:
    python3 verify_no_impl_trait_params.py [ROOT]
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path


# Match `impl <Ident>` at the start of a parameter token.  This is a
# pragmatic heuristic — we look for the substring `impl ` followed by an
# identifier, bounded to a parameter position (after `(` / `,` / start
# of line inside `impl` block / `fn` declaration).
# Detection strategy: find every `fn ...` declaration, then scan only
# inside its parameter list for `impl <Ident>` tokens.
FN_DECL = re.compile(
    r"^\s*((?:pub(?:\([^)]*\))?\s+|async\s+|const\s+|unsafe\s+|"
    r"(?:pub(?:\([^)]*\))?\s+)?(?:async|const|unsafe)\s+)*)"
    r"fn\s+[A-Za-z_][A-z0-9_]*\b",
    re.MULTILINE,
)
IMPL_PARAM = re.compile(r"\bimpl\s+([A-Z][A-Za-z0-9_]*)\b")


def _list_rs_files(root: Path) -> list[Path]:
    r = subprocess.run(
        ["find", str(root), "-name", "*.rs",
         "-not", "-path", "*/target/*",
         "-not", "-path", "*/.cargo/registry/*"],
        capture_output=True, text=True,
    )
    out: list[Path] = []
    for line in r.stdout.strip().splitlines():
        if line:
            out.append(Path(line))
    return out


def _iter_param_spans(text: str) -> list[tuple[int, int, int]]:
    """Return (line, col_start, col_end) ranges for every fn signature's
    parameter list.  Pragmatic:  balance parens after `fn <name>`."""
    spans: list[tuple[int, int, int]] = []
    for m in FN_DECL.finditer(text):
        # Find opening `(` from `m.end()`
        i = m.end()
        # Skip return-type generics if any (rare but possible: `fn f<T>(...)`).
        # The angle brackets here are tricky.  We look for the first `(` that
        # has matching `)` after it and is NOT inside `<...>`.
        depth_gen = 0
        while i < len(text):
            ch = text[i]
            if ch == "<":
                depth_gen += 1
            elif ch == ">":
                depth_gen -= 1
            elif ch == "(" and depth_gen == 0:
                break
            i += 1
        if i >= len(text) or text[i] != "(":
            continue
        # Find matching `)`.
        start_paren = i
        depth = 1
        j = i + 1
        while j < len(text) and depth > 0:
            ch = text[j]
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
            j += 1
        if depth != 0:
            continue
        # Convert char offsets to line/col for nicer output.
        line = text.count("\n", 0, start_paren) + 1
        spans.append((line, start_paren, j))
    return spans


def _line_of_offset(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def audit_one(path: Path) -> list[str]:
    try:
        text = path.read_text()
    except (OSError, UnicodeDecodeError):
        return []
    violations: list[str] = []
    for line, p_start, p_end in _iter_param_spans(text):
        # Get the parameter-list substring.
        # Note: spans could span multiple lines; we'll search it as text.
        param_text = text[p_start:p_end + 1]
        for m in IMPL_PARAM.finditer(param_text):
            abs_offset = p_start + m.start()
            ln = _line_of_offset(text, abs_offset)
            violations.append(
                f"{path}:{ln}: `impl {m.group(1)}` in fn parameter — "
                f"move to generic + where clause (§9.2)"
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
        # Skip tests/, build.rs, examples/ — impl Trait is conventional in tests.
        parts = f.parts
        if "tests" in parts or "examples" in parts or "target" in parts:
            continue
        if f.name == "build.rs":
            continue
        v = audit_one(f)
        if v:
            files_with_v += 1
            total += len(v)
            for line in v:
                print(line)
    print(f"\n=== no-impl-trait-fn-params: "
          f"{total} violation(s) in {files_with_v} file(s) ===")
    return 0 if total == 0 else 1


if __name__ == "__main__":
    sys.exit(main())