#!/usr/bin/env python3
"""
Verify §1.3 / §1.3a / §1.3c keyword-file purity + first-line `use super::*;`
for any Rust project.

Per rust-standards (2026-09-26 user tightening):

  • Each file under src/ must be exactly one of the 9 keyword basenames:
        const.rs / static.rs / fn.rs / enum.rs / struct.rs /
        trait.rs / impl.rs / type.rs / mod.rs
    Exempt: lib.rs / raw_html.rs / main.rs / bin/<name>.rs / build.rs
    and the whole tests/ tree.

  • Keyword files (any of the 9 above, except mod.rs) MUST open with
    `use super::*;` as the first non-comment line.  The previous
    exemption allowing direct `///` doc comments on enum.rs / struct.rs
    / type.rs is RETIRED.

  • Within a keyword file, ONLY declarations matching the file's
    basename may appear at column 0.  Existing rule §1.3a raw-string
    parser is reused.

  • Keyword files MUST NOT contain `use crate::xxx;`,
    `use super::specific_path;`, `use std::xxx;`,
    `use external_crate::xxx;` outside the leading
    `use super::*;`.  All imports are centralized in lib.rs /
    mod.rs.

Exit 0 if clean, exit 1 if any violation found (each violation on its
own line: <file>:<line>: <reason>).

Usage:
    python3 verify_keyword_file_purity.py [ROOT]

Default ROOT = current directory.  Excludes target/, .cargo/registry/,
and the standard cargo convention paths (lib.rs / main.rs / build.rs /
bin/<name>.rs).
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

# 9 keyword basenames + their forbidden-decl regex (column-0).
# Reuse the rule from audit_rust_standards.py check 16.
FORBIDDEN_DECLS: dict[str, str] = {
    "const.rs":  r"^(pub |pub\(crate\) )?(fn |struct |enum |trait |impl |type )",
    "static.rs": r"^(pub |pub\(crate\) )?(fn |struct |enum |trait |impl |type )",
    "fn.rs":     r"^(pub |pub\(crate\) )?(struct |enum |trait |impl |type )",
    "enum.rs":   r"^(pub |pub\(crate\) )?(struct |fn |impl |trait |type )",
    "struct.rs": r"^(pub |pub\(crate\) )?(enum |fn |impl |trait |type )",
    "trait.rs":  r"^(pub |pub\(crate\) )?(struct |enum |fn |impl |type )",
    "impl.rs":   r"^(pub |pub\(crate\) )?(struct |enum |fn |trait |type )",
    "type.rs":   r"^(pub |pub\(crate\) )?(struct |enum |fn |impl |trait )",
    # mod.rs is the only keyword file that itself contains sub-module
    # declarations — `mod r#xxx;` is allowed (and required).  No
    # `pub struct` / `pub fn` / etc. at column 0 in mod.rs.
    "mod.rs":    r"^(pub |pub\(crate\) )?(struct |enum |fn |trait |impl |type |const |static )",
}

KEYWORD_BASENAMES = set(FORBIDDEN_DECLS.keys())

# Cargo convention paths that are exempt from this rule.
EXEMPT_BASENAMES = {"lib.rs", "raw_html.rs", "main.rs", "build.rs"}

# Module path basenames exempt (bin/<name>.rs where <name> is anything).
BIN_DIR_PATTERN = re.compile(r"/bin/[^/]+\.rs$")

# Header pattern: optional `use super::*;` first non-comment line.
USE_SUPER_STAR = "use super::*;"

# Strict `use` patterns forbidden anywhere outside the leading
# `use super::*;` line.  We scan whole file and skip the leading
# super::* line — anything else `use <path>::...;` is violation.
# - `crate::...;` — long path to crate root, must use `pub use` in lib.rs
# - `super::specific_path;` (super:: NOT followed by *) — explicit import
# - `std::...;` — std symbols already re-exported by lib.rs `pub use std::...`
# - `external_crate::Sym;` — same: must be `pub use external_crate::...` in lib.rs
USE_FORBIDDEN = re.compile(
    r"^\s*use\s+(crate::|super::(?![*])|std::|[a-zA-Z_][a-zA-Z0-9_]*::)"
)


def _list_rs_files(root: Path) -> list[Path]:
    """Find every .rs file under root, skipping cargo noise."""
    r = subprocess.run(
        ["find", str(root), "-name", "*.rs",
         "-not", "-path", "*/target/*",
         "-not", "-path", "*/.cargo/registry/*"],
        capture_output=True, text=True,
    )
    out: list[Path] = []
    for line in r.stdout.strip().splitlines():
        if not line:
            continue
        out.append(Path(line))
    return out


def _is_exempt(path: Path, root: Path) -> bool:
    """Skip lib.rs / main.rs / build.rs / bin/<name>.rs / tests/."""
    rel = path.relative_to(root)
    parts = rel.parts
    if "tests" in parts:
        return True
    if "target" in parts or ".cargo" in parts:
        return True
    bn = path.name
    if bn in EXEMPT_BASENAMES:
        return True
    if BIN_DIR_PATTERN.search(str(rel)):
        return True
    return False


def _first_non_comment_line(text: str) -> tuple[int, str] | None:
    """Return (line_no, line_text) of first line that is not blank
    and not a `//!` / `///` / `// xxx` comment.  1-indexed."""
    for i, ln in enumerate(text.splitlines(), start=1):
        s = ln.strip()
        if not s:
            continue
        if s.startswith("//"):
            continue
        return i, ln
    return None


def _scan_raw_string_state(lines: list[str]) -> list[bool]:
    """For each line, return True if it is *inside* a raw-string literal
    at column 0.  Required because raw_string contents can legitimately
    contain keywords like `struct` or `fn` as text."""
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
            else:
                # Same-line raw string; tail is still 'in' until close_marker
                if cpos + len(close_marker) < len(rest):
                    inside[i] = False
                else:
                    inside[i] = False
    return inside


def _check_forbidden_decl(
    path: Path, basename: str, lines: list[str], inside_raw: list[bool],
) -> list[str]:
    """Check no column-0 decl of the wrong type lives in this keyword
    file.  Returns list of violation strings."""
    forbidden = FORBIDDEN_DECLS[basename]
    violations: list[str] = []
    rx = re.compile(forbidden)
    for i, line in enumerate(lines):
        if inside_raw[i]:
            continue
        if rx.match(line):
            violations.append(
                f"{path}:{i + 1}: forbidden decl in {basename} file: "
                f"{line[:80]!r}"
            )
    return violations


def _check_first_line_super(path: Path, text: str) -> list[str]:
    """First non-comment line must be `use super::*;`."""
    first = _first_non_comment_line(text)
    if first is None:
        return []  # empty file — nothing to check
    line_no, line_text = first
    if line_text.strip() != USE_SUPER_STAR:
        return [
            f"{path}:{line_no}: first non-comment line must be "
            f"'{USE_SUPER_STAR}' but is {line_text.strip()!r}"
        ]
    return []


def _check_use_centralized(
    path: Path, text: str, lines: list[str], inside_raw: list[bool],
) -> list[str]:
    """No `use crate::xxx;` / `use std::xxx;` /
    `use super::specific_path;` / `use external_crate::xxx;` outside the
    leading `use super::*;`.  Imports centralized in lib.rs / mod.rs
    (rust-standards §6.4)."""
    violations: list[str] = []
    first = _first_non_comment_line(text)
    if first is None:
        return []
    leading_line_no = first[0]
    for i, line in enumerate(lines, start=1):
        if inside_raw[i - 1]:
            continue
        if not USE_FORBIDDEN.match(line):
            continue
        # Skip the leading `use super::*;` (it's the only allowed one).
        if i == leading_line_no and line.strip() == USE_SUPER_STAR:
            continue
        # Skip any `use super::*;` line (rare but allowed anywhere).
        if line.strip() == USE_SUPER_STAR:
            continue
        # Skip `pub use ...` re-exports (mod.rs only — already filtered out).
        # Other keyword files should never have `pub use` either.
        violations.append(
            f"{path}:{i}: forbidden `use` in keyword file "
            f"(centralize in lib.rs / mod.rs per §6.4): {line.strip()[:80]!r}"
        )
    return violations


def audit_one(path: Path, root: Path) -> list[str]:
    """Return all violations for this single file."""
    if _is_exempt(path, root):
        return []
    basename = path.name
    if basename not in KEYWORD_BASENAMES:
        return []
    try:
        text = path.read_text()
    except (OSError, UnicodeDecodeError):
        return []
    lines = text.splitlines()
    inside_raw = _scan_raw_string_state(lines)
    out: list[str] = []
    out += _check_first_line_super(path, text)
    out += _check_forbidden_decl(path, basename, lines, inside_raw)
    out += _check_use_centralized(path, text, lines, inside_raw)
    return out


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    if not root.is_dir():
        print(f"error: {root} is not a directory", file=sys.stderr)
        return 2
    files = _list_rs_files(root)
    total_violations = 0
    files_with_violations = 0
    for f in files:
        v = audit_one(f, root)
        if v:
            files_with_violations += 1
            total_violations += len(v)
            for line in v:
                print(line)
    print(f"\n=== keyword-file purity: "
          f"{total_violations} violation(s) in {files_with_violations} file(s) ===")
    return 0 if total_violations == 0 else 1


if __name__ == "__main__":
    sys.exit(main())