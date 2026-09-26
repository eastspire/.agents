#!/usr/bin/env python3
"""
Verify rust-standards §2.4: every `lib.rs` MUST have a leading
`//!` doc comment block with the canonical structure:

  //! <package_name>
  //!
  //! <content>

Per references/02-documentation.md §2.4 (2026-09-26 user
iteration strengthening): "lib.rs 唯一注释在文件开头,格式如下:

  //! Crates name
  //!
  //! Description"

User original (2026-09-26, fifth iteration): "对于 lib.rs 必须
要检查是否存在 //! 注释,注释第一行 //! 后是包名后面是一行 //!
再后面才是内容".

Bidirectional fixture (rust-std-fixtures/lib-rs-doc/{compliant,violating}):
  compliant/crates/foo/src/lib.rs    — minimal `//! foo\n//!\n//! ...`         → 0 violations
  compliant/crates/baz/src/lib.rs    — minimal `//! baz\n//!\n//! X` (1-char desc) → 0 violations
  compliant/crates/qux/src/lib.rs    — multi-line description                                → 0 violations
  compliant/crates/quux/src/lib.rs   — extra blank lines between //! block and code            → 0 violations
  violating/crates/foo/src/lib.rs    — missing //! block entirely                             → 1 violation
  violating/crates/bar/src/lib.rs    — //! + content but missing //! separator                 → 1 violation
  violating/crates/baz/src/lib.rs    — //! text "WRONG_NAME" doesn't match [package].name      → 1 violation
  violating/crates/qux/src/lib.rs    — blank line between //! and content (no //! separator)   → 1 violation
  violating/crates/quux/src/lib.rs   — //! + separator but no third //! description line       → 1 violation

Real-workspace findings (audit_rust_standards check 36):
  euv:    5 violations — name mismatch in core/example/cli/macros/lib.rs,
                        docs/src/lib.rs has NO //! block at all.

Validation:
  1. File must START with `//!` (no leading whitespace, no
     leading `use` / `mod` / `pub` / `extern` etc.).
  2. The first `//!` line text after `//!` (and any leading
     whitespace) MUST equal the package name (taken from
     the closest Cargo.toml's `[package].name` field).
  3. The second `//!` line MUST be EMPTY (just `//!` with
     no trailing content) — this is the canonical separator
     between the package-name heading and the description.
  4. After the empty `//!` line, content follows.  The verifier
     does NOT enforce specific content (project-specific
     description), only that the structure is present.

Exemptions (these files are NOT lib.rs but follow the same
naming pattern at top of their crate):
  - `macros/src/lib.rs` — proc-macro crate, often has a
    minimal `//!` block.  Same rule applies (mandatory).
  - `euv-docs/src/lib.rs` — markdown utility crate.  Same
    rule applies.
  - Bin entry files (`src/bin/<name>.rs`, `<name>/main.rs`):
    NOT audited by this script — only `lib.rs`.

Exits 0 if clean, 1 if any violation.

Usage:
    python3 verify_lib_rs_doc_comment.py [ROOT]
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path


# Match `//! <text>` lines.  Capture group 1 = text after `//!`
INNER_DOC = re.compile(r"^//!\s*(?P<text>.*?)\s*$")


def _list_lib_rs_files(root: Path) -> list[Path]:
    """Find every lib.rs file under root via `find`."""
    r = subprocess.run(
        ["find", str(root), "-name", "lib.rs",
         "-not", "-path", "*/target/*",
         "-not", "-path", "*/.cargo/registry/*"],
        capture_output=True, text=True,
    )
    return [Path(line) for line in r.stdout.strip().splitlines() if line]


def _read_package_name(lib_rs: Path) -> str | None:
    """Walk up the path to find the closest Cargo.toml and read
    [package].name.  Returns None if not found / not parseable."""
    # The crate containing lib.rs is the directory parent of src/.
    # Cargo.toml is at the crate root.
    cur = lib_rs.parent
    while cur != cur.parent:
        cargo = cur / "Cargo.toml"
        if cargo.is_file():
            text = cargo.read_text()
            m = re.search(
                r'^\[\s*package\s*\][^\[]*?'
                r'^\s*name\s*=\s*"(?P<name>[^"]+)"',
                text, re.MULTILINE | re.DOTALL,
            )
            if m:
                return m.group("name")
            return None
        cur = cur.parent
    return None


def audit_one(path: Path) -> list[str]:
    try:
        text = path.read_text()
    except (OSError, UnicodeDecodeError):
        return []
    lines = text.splitlines()
    if not lines:
        return [
            f"{path}:1: lib.rs is empty — must start with `//! <package_name>` doc block (§2.4)"
        ]

    violations: list[str] = []
    pkg_name = _read_package_name(path)
    if pkg_name is None:
        violations.append(
            f"{path}: (could not read [package].name from nearest Cargo.toml — skipping structural check; please verify manually)"
        )
        # Still proceed to check structure, but we can't compare against pkg name.

    # 1. First non-blank line MUST be `//!`.
    i = 0
    while i < len(lines) and not lines[i].strip():
        i += 1
    if i >= len(lines):
        return [
            f"{path}:1: lib.rs has only blank lines — must start with `//! <package_name>` doc block (§2.4)"
        ]
    first = lines[i]
    m1 = INNER_DOC.match(first)
    if not m1:
        violations.append(
            f"{path}:{i + 1}: lib.rs first non-blank line MUST be `//!` "
            f"doc comment, got: {first.strip()[:80]!r} (§2.4)"
        )
        return violations  # No point checking further

    # 2. First `//!` line text must equal the package name.
    first_text = m1.group("text").strip()
    if pkg_name is not None and first_text != pkg_name:
        violations.append(
            f"{path}:{i + 1}: lib.rs first `//!` line text MUST equal "
            f"package name {pkg_name!r}, got: {first_text!r} (§2.4)"
        )

    # 3. Next `//!` line MUST be empty (just `//!`).
    j = i + 1
    if j >= len(lines):
        violations.append(
            f"{path}:{j + 1}: lib.rs must have a second `//!` empty line "
            f"after package name, got EOF (§2.4)"
        )
        return violations
    second = lines[j]
    m2 = INNER_DOC.match(second)
    if not m2:
        violations.append(
            f"{path}:{j + 1}: lib.rs second `//!` line expected (separator), "
            f"got: {second.strip()[:80]!r} (§2.4)"
        )
        return violations
    second_text = m2.group("text").strip()
    if second_text != "":
        violations.append(
            f"{path}:{j + 1}: lib.rs second `//!` line MUST be empty "
            f"(just `//!`), got content: {second_text!r} (§2.4)"
        )

    # 4. After the empty separator, at least one more `//!` line
    #    is required (the description).  This is the "再后面才是内容"
    #    part of the user's instruction.
    k = j + 1
    # Skip any blank lines
    while k < len(lines) and not lines[k].strip():
        k += 1
    if k >= len(lines):
        violations.append(
            f"{path}:{k + 1}: lib.rs third `//!` line expected (description "
            f"content), got EOF (§2.4)"
        )
        return violations
    third = lines[k]
    m3 = INNER_DOC.match(third)
    if not m3:
        violations.append(
            f"{path}:{k + 1}: lib.rs third `//!` line expected (description), "
            f"got: {third.strip()[:80]!r} (§2.4)"
        )
    # Content text is allowed to be anything; user just requires
    # the structural presence.

    return violations


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    if not root.is_dir():
        print(f"error: {root} is not a directory", file=sys.stderr)
        return 2
    files = _list_lib_rs_files(root)
    total = 0
    files_with_v = 0
    for f in files:
        v = audit_one(f)
        if v:
            files_with_v += 1
            total += len(v)
            for line in v:
                print(line)
    print(f"\n=== lib.rs-doct-comment: "
          f"{total} violation(s) in {files_with_v} file(s) ===")
    return 0 if total == 0 else 1


if __name__ == "__main__":
    sys.exit(main())