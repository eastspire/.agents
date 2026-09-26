#!/usr/bin/env python3
"""
Verify rust-standards §1.3c (strengthened, 2026-09-26 third
iteration): hardcoded string literals MUST live in `const.rs`.

User original (2026-09-26 third iteration):
  "硬编码字符串必须要维护到 const.rs 上面"

The existing `audit_rust_standards.py` check 18 only catches
hardcoded byte / char / multi-character string literals in
`fn.rs` files (and only the FIRST few characters of a multi-byte
literal).  This new rule extends coverage to ALL files except
`const.rs` and `tests/`:

  ❌  let path: &str = "/usr/local/bin";         // in fn.rs
  ❌  eprintln!("Hello, world!");                // in fn.rs
  ❌  format!("got {} items", n);                // in impl.rs
  ❌  if name == "admin" { ... }                 // in fn.rs

  ✅  // in const.rs:
      pub const BIN_PATH_USR_LOCAL: &str = "/usr/local/bin";
      pub const HELLO_WORLD: &str = "Hello, world!";
      // then in fn.rs:
      eprintln!("{}", HELLO_WORLD);

Exemptions:
  - Files named `const.rs` (this is the canonical home of
    string constants; literal strings here are not
    "hardcoded", they ARE the constant definition).
  - `tests/` directory (R14.7 self-contained; tests often
    embed expected literals).
  - `format!` / `println!` / `eprintln!` / `panic!` /
    `assert!` / `assert_eq!` / `assert_ne!` / `unimplemented!`
    / `unreachable!` / `todo!` / `dbg!` / `write!` / `writeln!`
    macros whose string literal is the FORMAT string (first
    argument).  These are user-facing format strings; they
    MUST stay inline at the call site for readability.
    BUT: arguments embedded as `format!("got {} items", n)`
    where `n` is a literal `0` are NOT exempt — the format
    string itself stays inline, but constants get extracted
    in surrounding code.
  - String literals used as trait discriminant in
    attribute macros like `#[doc = "..."]` / `#[cfg(test)]` —
    handled by the macro detection (line starts with `#[`).
  - String literals inside `#[derive(...)]` (the derive
    name itself, e.g. `#[derive(Debug)]`) — these are
    attribute paths, not user data.
  - String literals in `serde` rename attributes
    (`#[serde(rename = "...")]`) — these are wire-format
    names that MUST be inline.

Detection heuristic:
  - For each .rs file NOT in {const.rs, tests/}:
    * Find every line that contains a string literal
      (`"...some text..."` — minimum 4 non-trivial chars).
    * If the line is:
      - Inside a macro at attribute position (`#[xxx = "..."]`)
        → exempt
      - Inside a known format macro as the first positional
        arg → exempt
      - Otherwise → violation (line + content)

This is a strict heuristic; it WILL have false positives on
well-named macros that take strings as first argument
(`writeln!`, `assert_eq!` format string).  When in doubt,
the script prefers false-positive (flag) over false-negative
(miss), so authors must explicitly justify the literal.

Exits 0 if clean, 1 if any violation.

Usage:
    python3 verify_hardcoded_strings.py [ROOT]
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path


# Format-style macros whose FIRST string argument is the
# format string (user-facing) and is exempt from extraction.
FORMAT_MACROS = {
    "format", "println", "eprintln", "print", "eprint",
    "panic", "unimplemented", "unreachable", "todo",
    "assert", "assert_eq", "assert_ne",
    "write", "writeln",
    "dbg", "error", "warn", "info", "debug", "trace",
}


# Match a string literal — at minimum 4 non-whitespace chars
# (avoid flagging single-char `'.'` literals and empty `""`).
STRING_LITERAL = re.compile(r'"([^"\\]|\\.){4,}"')

# Match attribute lines like `#[doc = "..."]` /
# `#[serde(rename = "...")]` etc. — the whole line starts
# with `#[` and ends with `]`.
ATTR_LINE = re.compile(r"^\s*#\[")


def _list_rs_files(root: Path) -> list[Path]:
    r = subprocess.run(
        ["find", str(root), "-name", "*.rs",
         "-not", "-path", "*/target/*",
         "-not", "-path", "*/.cargo/registry/*"],
        capture_output=True, text=True,
    )
    return [Path(line) for line in r.stdout.strip().splitlines() if line]


def _is_format_macro(line: str) -> bool:
    """Return True if the string literal on this line is the
    format string of a known format-style macro (first arg)."""
    # Heuristic: line contains `<macro>!(` followed by string
    # literal before any other arg.
    for m in re.finditer(r"\b(\w+)!\s*\(", line):
        macro = m.group(1)
        if macro in FORMAT_MACROS:
            after = line[m.end():]
            str_match = STRING_LITERAL.search(after)
            if not str_match:
                continue
            comma_match = re.search(r",", after)
            if macro in {"write", "writeln"}:
                # write!/writeln! take the writer as the first arg, so the
                # format string is the second arg (after the first comma).
                if comma_match is None:
                    continue
                second_comma = re.search(r",", after[comma_match.end():])
                if str_match.start() > comma_match.end() and (
                    second_comma is None
                    or str_match.start() < comma_match.end() + second_comma.start()
                ):
                    return True
                continue
            if comma_match is None or str_match.start() < comma_match.start():
                # Format string is the first arg — exempt
                return True
    return False


def _exempt_format_string_lines(lines: list[str]) -> set[int]:
    """Return 1-based line numbers holding the format string of a
    multi-line format-macro call (rustfmt puts each arg on its own
    line, so the format string may not share a line with the macro).

    For write!/writeln! the format string is the second arg (writer
    first); for all other format macros it is the first arg.  Arg
    counting assumes one arg per line, which is how rustfmt wraps."""
    exempt: set[int] = set()
    macro_re = re.compile(r"\b(\w+)!\s*\(")
    for idx, line in enumerate(lines):
        for m in macro_re.finditer(line):
            macro = m.group(1)
            if macro not in FORMAT_MACROS:
                continue
            after = line[m.end():]
            if STRING_LITERAL.search(after):
                continue
            depth = 1 + after.count("(") - after.count(")")
            if depth <= 0:
                continue
            target_arg = 1 if macro in {"write", "writeln"} else 0
            arg_index = 1 if after.strip() else 0
            j = idx + 1
            while j < len(lines) and depth > 0:
                current = lines[j]
                depth += current.count("(") - current.count(")")
                content = current.strip()
                if content:
                    if arg_index == target_arg and STRING_LITERAL.search(current):
                        exempt.add(j + 1)
                        break
                    arg_index += 1
                j += 1
    return exempt


def audit_one(path: Path) -> list[str]:
    try:
        text = path.read_text()
    except (OSError, UnicodeDecodeError):
        return []
    lines = text.splitlines()
    exempt_lines = _exempt_format_string_lines(lines)
    violations: list[str] = []
    for i, line in enumerate(lines, start=1):
        # Skip const.rs (the canonical home)
        if path.name == "const.rs":
            continue
        # Skip attribute lines (#[doc = "..."], #[serde(...)])
        if ATTR_LINE.match(line):
            continue
        # Skip format-macro format strings
        if _is_format_macro(line):
            continue
        if i in exempt_lines:
            continue
        # Find string literals on this line
        for m in STRING_LITERAL.finditer(line):
            literal = m.group(0)
            # Skip if literal looks like a path (contains /)
            # — paths often encode import paths in `use` and
            # inline `format!` paths.  We're strict here.
            violations.append(
                f"{path}:{i}: hardcoded string literal {literal!r} "
                f"must live in `const.rs` (§1.3c strengthened): "
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
        # Skip const.rs (we don't audit the canonical home)
        if f.name == "const.rs":
            continue
        # Skip tests/ (R14.7 self-contained)
        if "tests" in f.parts:
            continue
        v = audit_one(f)
        if v:
            files_with_v += 1
            total += len(v)
            for line in v:
                print(line)
    print(f"\n=== hardcoded-strings-to-const: "
          f"{total} violation(s) in {files_with_v} file(s) ===")
    return 0 if total == 0 else 1


if __name__ == "__main__":
    sys.exit(main())