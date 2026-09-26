#!/usr/bin/env python3
"""
Verify rust-standards §6.1 / §6.3 / §6.4 module-import centralization
for any Rust project.

  §6.1 lib.rs / mod.rs:
      All crate-wide external symbols are re-exported via `pub use`
      (or `pub(crate) use` for crate-only visibility).  The `use`
      group ordering is:
        1. mod xxx;     (no blank lines)
        2. pub use {sub_modules::*}
        3. pub use std::{...} / pub use external_crate::{...}
        4. pub(crate) use
        5. pub(super) use
        6. private use (current crate → std → externals)

  §6.3 sub-files:
      First line MUST be `use super::*;`.  After that, NO
      `use crate::xxx;` / `use std::xxx;` /
      `use super::specific_path;` / `use external_crate::xxx;` may
      appear — all imports flow through lib.rs / mod.rs re-export.

  §6.4:
      Sub-files MUST NOT re-import symbols already re-exported by
      lib.rs / mod.rs.

Exits 0 if clean, 1 if any violation.

Usage:
    python3 verify_module_imports_centralized.py [ROOT]
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path


# Files that are NOT keyword sub-files but are exempt from this rule.
EXEMT_BASENAMES = {"lib.rs", "raw_html.rs", "main.rs", "build.rs"}
BIN_DIR_PATTERN = re.compile(r"/bin/[^/]+\.rs$")

# Keyword sub-files: must have `use super::*;` first; nothing else.
KEYWORD_BASENAMES = {
    "const.rs", "static.rs", "fn.rs", "enum.rs", "struct.rs",
    "trait.rs", "impl.rs", "type.rs", "mod.rs",
}

USE_SUPER_STAR = "use super::*;"

# Forbidden `use` pattern in keyword sub-files (excl. mod.rs) — anything
# other than `use super::*;` is a violation.
USE_FORBIDDEN_KEYWORD = re.compile(
    r"^\s*use\s+(crate::|super::(?!\*)|std::|[a-zA-Z_][a-zA-Z0-9_]*::)"
)
USE_OK = re.compile(r"^\s*use\s+super::\*;")


def _list_rs_files(root: Path) -> list[Path]:
    r = subprocess.run(
        ["find", str(root), "-name", "*.rs",
         "-not", "-path", "*/target/*",
         "-not", "-path", "*/.cargo/registry/*"],
        capture_output=True, text=True,
    )
    return [Path(line) for line in r.stdout.strip().splitlines() if line]


def _is_exempt(path: Path, root: Path) -> bool:
    rel = path.relative_to(root)
    parts = rel.parts
    if "tests" in parts or "examples" in parts:
        return True
    if "target" in parts or ".cargo" in parts:
        return True
    bn = path.name
    if bn in EXEMT_BASENAMES:
        return True
    if BIN_DIR_PATTERN.search(str(rel)):
        return True
    return False


def _first_non_comment_line(text: str) -> tuple[int, str] | None:
    for i, ln in enumerate(text.splitlines(), start=1):
        s = ln.strip()
        if not s:
            continue
        if s.startswith("//"):
            continue
        return i, ln
    return None


def _scan_raw_string_state(lines: list[str]) -> list[bool]:
    """For each line, True if inside a raw-string literal at column 0."""
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
    return inside


def audit_keyword_file(path: Path, text: str, lines: list[str],
                       inside_raw: list[bool]) -> list[str]:
    """Check keyword sub-files (anything except mod.rs): only
    `use super::*;` allowed, and it must be the first non-comment line."""
    basename = path.name
    if basename not in KEYWORD_BASENAMES or basename == "mod.rs":
        return []
    violations: list[str] = []

    # First-line check.
    first = _first_non_comment_line(text)
    if first is not None:
        line_no, line_text = first
        if line_text.strip() != USE_SUPER_STAR:
            violations.append(
                f"{path}:{line_no}: keyword file first line must be "
                f"'{USE_SUPER_STAR}' but is {line_text.strip()!r}"
            )

    # No forbidden use anywhere (already covered by keyword-file-purity
    # check, but keep for self-contained verification).
    for i, line in enumerate(lines):
        if inside_raw[i]:
            continue
        if not USE_FORBIDDEN_KEYWORD.match(line):
            continue
        if USE_OK.match(line):
            continue
        # Skip any `use super::*;` line (allowed anywhere).
        if line.strip() == USE_SUPER_STAR:
            continue
        violations.append(
            f"{path}:{i + 1}: forbidden `use` in keyword sub-file "
            f"(centralize in lib.rs / mod.rs per §6.4): "
            f"{line.strip()[:80]!r}"
        )
    return violations


def audit_lib_rs(path: Path, text: str, lines: list[str]) -> list[str]:
    """lib.rs:  §6.1 std/external imports must be `pub use`, not
    private `use`.  We flag every line like
    `^use std::...;` / `^use external_crate::Sym;` /
    `^use {std::..., external_crate::Sym};` (private).  `pub use` /
    `pub(crate) use` / `pub(super) use` are fine.

    This is a stricter version of the user-pitfall warning.  Per
    §6.1:  "lib.rs 中任何 sub-file 也要用的 std / external crate 符号
    都必须用 pub use".
    """
    violations: list[str] = []
    for i, line in enumerate(lines):
        s = line.strip()
        # Skip non-`use` lines, comments, blank lines.
        if not s or s.startswith("//"):
            continue
        if s.startswith("use "):
            # If the line starts with `pub use` it's fine.
            if s.startswith("pub use "):
                continue
            # If it's `use std::...;` or `use external_crate::...;`,
            # that's a violation.
            if re.match(r"use\s+(std::|[a-zA-Z_][a-zA-Z0-9_]*::)", s):
                # Private use of std / external — must be pub use
                # per §6.1 (only when sub-files might want it).
                violations.append(
                    f"{path}:{i + 1}: private `use` in lib.rs for "
                    f"std/external symbol — should be `pub use` per §6.1 "
                    f"(sub-files inherit via `use super::*;`): "
                    f"{s[:80]!r}"
                )
    return violations


def audit_mod_rs(path: Path, text: str, lines: list[str]) -> list[str]:
    """mod.rs: trailing line must be `use super::*;` (or `pub use super::*;`
    for tests).  No `// xxx` comments.  Three-stage structure:
      1. mod r#xxx;
      2. pub use / pub(crate) use
      3. use super::*;
    """
    violations: list[str] = []
    # No comments rule.
    for i, line in enumerate(lines):
        s = line.strip()
        if s.startswith("//") and not s.startswith("///"):
            violations.append(
                f"{path}:{i + 1}: forbidden `//` comment in `mod.rs` "
                f"(mod.rs is pure structure, §2.5): {s[:60]!r}"
            )
    # Trailing use super::* rule.
    last = None
    for line in lines:
        s = line.strip()
        if s:
            last = s
    if last not in {"use super::*;", "pub use super::*;"}:
        # Per §6.2 last line is the trailing super::* import.
        # Per §2.5 mod.rs has no comments; if last line is a comment,
        # that's a violation flagged above.
        if last is not None:
            violations.append(
                f"{path}:{len(lines)}: mod.rs last non-blank line must be "
                f"`use super::*;` but is {last!r}"
            )
    return violations


def _is_exempt_for_imports(path: Path, root: Path) -> bool:
    """Skip tests/, examples/, target/, .cargo/, build.rs, bin/<name>.rs.
    For this verifier, lib.rs / main.rs are NOT exempt — they are
    the primary target (we audit lib.rs imports for §6.1 compliance)."""
    rel = path.relative_to(root)
    parts = rel.parts
    if "tests" in parts or "examples" in parts:
        return True
    if "target" in parts or ".cargo" in parts:
        return True
    if path.name == "build.rs":
        return True
    if BIN_DIR_PATTERN.search(str(rel)):
        return True
    return False


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    if not root.is_dir():
        print(f"error: {root} is not a directory", file=sys.stderr)
        return 2
    files = _list_rs_files(root)
    total = 0
    files_with_v = 0
    for f in files:
        if _is_exempt_for_imports(f, root):
            continue
        try:
            text = f.read_text()
        except (OSError, UnicodeDecodeError):
            continue
        lines = text.splitlines()
        inside_raw = _scan_raw_string_state(lines)
        bn = f.name
        v: list[str] = []
        if bn in KEYWORD_BASENAMES:
            v += audit_keyword_file(f, text, lines, inside_raw)
        if bn == "lib.rs":
            v += audit_lib_rs(f, text, lines)
        if bn == "mod.rs":
            v += audit_mod_rs(f, text, lines)
        if v:
            files_with_v += 1
            total += len(v)
            for line in v:
                print(line)
    print(f"\n=== module-imports centralized: "
          f"{total} violation(s) in {files_with_v} file(s) ===")
    return 0 if total == 0 else 1


if __name__ == "__main__":
    sys.exit(main())