#!/usr/bin/env python3
"""
Verify §1.3 / §1.3a / §1.3c / §1.4 keyword-file purity + filename
+ relaxed sub-file use rule for any Rust project.

§1.4 (added 2026-09-30, user directive): every `.rs` file under src/ must
be named after a Rust keyword.  A file called `inline.rs` is a violation even
when its contents are correct, because the name itself is what makes the
layout navigable — `fn.rs` says "functions live here" without opening it.

  euv:  cli/src/build/inline.rs existed for months and no hook caught it,
        because `audit_one()` returned `[]` for any basename outside
        KEYWORD_BASENAMES.  A file the rule does not recognise was treated as
        a file the rule does not apply to, so the one case worth reporting
        was the one case silently dropped.  The exemption list below is now
        the ONLY way out.

Per rust-standards (2026-09-26 user tightening + sixth-iteration relaxation):

  • Each file under src/ must be exactly one of the keyword basenames:
        const.rs / static.rs / fn.rs / enum.rs / struct.rs /
        trait.rs / impl.rs / type.rs / mod.rs / macro.rs
    A name outside this set is itself a §1.4 violation (added 2026-09-30),
    not a file the rule ignores.
    Exempt: lib.rs / raw_html.rs / main.rs / bin/<name>.rs / build.rs
    and the whole tests/ tree.

  • Within a keyword file, ONLY declarations matching the file's
    basename may appear at column 0.  Existing rule §1.3a raw-string
    parser is reused.

  • Keyword file's first `use` line, if any, MUST be exactly
    `use super::*;`.  A keyword file MAY also have NO `use` at all
    (2026-09-26 sixth iteration user relaxation: "不是所有文件都必须要
    需要使用 use super::*, 可以不要 use").  This means:
        ✅ File with NO `use`                              — OK
        ✅ File with `use super::*;` (first or anywhere)   — OK
        ❌ File with `use crate::*;` or `use crate::xxx;`  — violation
        ❌ File with `use std::xxx;`                       — violation
        ❌ File with `use external_crate::xxx;`            — violation
        ❌ File with `use super::specific_path;`           — violation

  • Scope: sub-files only (any .rs file other than lib.rs / mod.rs).
    lib.rs goes through §2.4 mandatory //! block rules;
    mod.rs goes through §6.2 three-stage + trailing use super::*;.

Bidirectional fixture (rust-std-fixtures/use-rule/{compliant,violating}):
  compliant/src/sub1/fn.rs — `use super::*;` first           → 0 violations
  compliant/src/sub2/fn.rs — NO use                          → 0 violations
  violating/src/sub2/fn.rs — `use crate::Bar;` etc.         → 4 violations
  violating/src/sub3/fn.rs — `use crate::*;`                → 2 violations
  violating/src/sub4/fn.rs — `use external_crate::Foo;`     → 2 violations
  violating/src/sub5/fn.rs — `use std::collections::HashMap;` → 2 violations
  violating/src/sub6/fn.rs — `use super::r#helper;`         → 2 violations

Real-workspace findings (audit_rust_standards check 23):
  euv:    9 violations  (down from 358 — old rule mandatory,
                          new rule allows skipping use)
  ctares: 16 violations (down from 175 — same reason)

User original (2026-09-26, sixth iteration):
  "不是所有文件都必须要需要使用 use super::*, 可以不要 use, 对于
   lib.rs, mod.rs 之外的 rs 文件, 是不允许出现 use::super::* 和没
   有 use 之外的其他写法的"

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
    # macro.rs holds the `macro_rules!` bodies, which are function-shaped:
    # `macro_rules! name { ... }` and the `pub use name;` re-export. A real
    # `fn`/`struct`/`impl` in the same file is a misplaced declaration.
    "macro.rs":  r"^(pub |pub\(crate\) )?(struct |enum |trait |impl |type )",
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
    # `tmp/` is scratch output: `crate fmt` / integration tests write throwaway
    # projects there (hyperlane and ctares both have a gitignored
    # cli/tmp/test_fmt/test.rs left over from a fmt test run). Those are not
    # part of the crate's source layout and must not be judged by §1.4.
    if "tmp" in parts:
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
    """First non-comment line, IF a use, must be `use super::*;`.

    Per rust-standards §6.3 (2026-09-26 sixth iteration,
    user original): "不是所有文件都必须要需要使用 use super::*,
    可以不要 use, 对于 lib.rs, mod.rs 之外的 rs 文件, 是不允许
    出现 use::super::* 和没有 use 之外的其他写法的".

    Translation: sub-files (not lib.rs / mod.rs) MAY have
    `use super::*;` as their first line OR may have no `use`
    at all.  No other `use` form is allowed.

    So: if first non-comment line is a `use` statement, it
    must be `use super::*;`.  If first non-comment line is
    not a `use` (e.g. is `mod`, `pub`, `fn`, `struct`, etc.
    directly), that's also OK (sub-files CAN skip use).
    """
    first = _first_non_comment_line(text)
    if first is None:
        return []  # empty file — nothing to check
    line_no, line_text = first
    stripped = line_text.strip()
    # If first line is not a `use` statement, file skips use — OK.
    if not stripped.startswith("use "):
        return []
    # First line IS a `use` — must be `use super::*;`.
    if stripped != USE_SUPER_STAR:
        return [
            f"{path}:{line_no}: first `use` line in sub-file MUST be "
            f"'{USE_SUPER_STAR}' (the only allowed form) or omitted; "
            f"got: {stripped!r}"
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
    # §14.1 makes `tests/` the one place a `use crate_name::*;` is
    # *mandatory*: a test module lives outside the crate, so it has no
    # `super::*` chain to inherit. Flagging it here contradicts §14.1
    # directly, and every `tests/mod.rs` in every repo trips it. §6.4 is
    # about src/, where lib.rs already re-exports everything.
    if "tests" in path.parts:
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


def _infer_root(path: Path) -> Path:
    """Best-effort crate root for a file, so `audit_one(path)` can stand alone.

    Walks up from the file to the nearest ancestor whose child directory is
    `src`, which is the shape every crate in every repo here has. Falls back
    to the file's own parent when no such ancestor exists, so the relative
    label degrades to the bare file name instead of raising.
    """
    for candidate in [path.parent, *path.parents]:
        if candidate.name == "src":
            return candidate.parent
    return path.parent


def audit_one(path: Path, root: Path | None = None) -> list[str]:
    """Return all violations for this single file.

    `root` is optional so this entry point matches the signature
    `staged_file_gate.py` calls it with (`audit_one(path)`). When omitted it
    is derived from the path, which is only used to render a repo-relative
    label in the message and to recognise `tests/` / `target/` components —
    both still resolve correctly from an absolute path.
    """
    if root is None:
        root = _infer_root(path)
    if _is_exempt(path, root):
        return []
    basename = path.name
    if basename not in KEYWORD_BASENAMES:
        # §1.4: an unrecognised basename is a violation in its own right.
        # Returning [] here used to make a badly-named file invisible to
        # every check, which is how cli/src/build/inline.rs survived.
        rel = path.relative_to(root)
        keywords = ", ".join(sorted(n[:-3] for n in KEYWORD_BASENAMES))
        return [
            f"{rel}: §1.4: `{basename}` is not a keyword file name; "
            f"move its contents into one of {keywords}"
        ]
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