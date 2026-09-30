#!/usr/bin/env python3
"""§14.5 — no comments in test files.

Rule (2026-09-26 user tightening, round-3 clarification):

    no `//`, no `///`, no `//!` anywhere in a test file

A test reads as executable specification.  Comments in test files restate what
the code already says, and a stale comment in a test is worse than no comment at
all: it survives refactors of the code and keeps asserting something untrue.

Scope: every `.rs` file under a `tests/` directory, plus any file that IS a test
module (`#[cfg(test)]` block contents are handled by the caller's own scan of
production files — here we only take path-based ownership).

Deliberately NOT reported:
  - comments in production files (this rule is about test files only)
  - `#[cfg(test)]` blocks inside production files — the audit's check 14 owns
    those, so scanning them here would double-report

Output contract: one violation per line, then a summary line beginning
`=== no-comments-in-test-files:`.

Exit code: 0 = compliant, 1 = violations, 2 = usage error.
"""

import re
import subprocess
import sys
from pathlib import Path

LINE_COMMENT = re.compile(r"^\s*//")
# `//` appearing after code on the same line is still a comment.
TRAILING_COMMENT = re.compile(r"//")


def list_test_files(root: Path) -> list[Path]:
    result = subprocess.run(
        [
            "find", str(root), "-name", "*.rs",
            "-path", "*/tests/*",
            "-not", "-path", "*/target/*",
            "-not", "-path", "*/.cargo/registry/*",
        ],
        capture_output=True, text=True,
    )
    return [Path(line) for line in result.stdout.splitlines() if line.strip()]


def audit_one(path: Path) -> list[str]:
    try:
        lines = path.read_text().splitlines()
    except (OSError, UnicodeDecodeError):
        return []
    violations: list[str] = []
    in_block = False
    for idx, raw in enumerate(lines, 1):
        stripped = raw.strip()
        if in_block:
            if "*/" in stripped:
                in_block = False
                end = stripped.index("*/") + 2
                # code after the block close on the same line may still hold a comment
                if "//" in stripped[end:]:
                    violations.append(
                        f"{path}:{idx}: comment in a test file is forbidden (§14.5) "
                        f"(//, /// and //! are all banned): {stripped[:90]!r}"
                    )
                continue
            violations.append(
                f"{path}:{idx}: comment in a test file is forbidden (§14.5) "
                f"(//, /// and //! are all banned): {stripped[:90]!r}"
            )
            continue
        if stripped.startswith("/*"):
            if "*/" not in stripped[2:]:
                in_block = True
                violations.append(
                    f"{path}:{idx}: comment in a test file is forbidden (§14.5) "
                    f"(//, /// and //! are all banned): {stripped[:90]!r}"
                )
                continue
            after = stripped[stripped.index("*/") + 2:]
            if "//" in after:
                violations.append(
                    f"{path}:{idx}: comment in a test file is forbidden (§14.5) "
                    f"(//, /// and //! are all banned): {stripped[:90]!r}"
                )
            continue
        if LINE_COMMENT.match(raw) or ("//" in raw and not _in_string(raw, raw.index("//"))):
            violations.append(
                f"{path}:{idx}: comment in a test file is forbidden (§14.5) "
                f"(//, /// and //! are all banned): {stripped[:90]!r}"
            )
    return violations


def _in_string(line: str, idx: int) -> bool:
    """True when the `//` at idx sits inside a string or char literal."""
    prefix = line[:idx]
    # odd number of unescaped quotes before it => we are inside a string
    count = 0
    i = 0
    while i < len(prefix):
        ch = prefix[i]
        if ch == "\\":
            i += 2
            continue
        if ch in "\"'":
            j = i + 1
            while j < len(prefix) and prefix[j] != ch:
                if prefix[j] == "\\":
                    j += 1
                j += 1
            if j >= len(prefix):
                count += 1  # unterminated -> we are inside it
                break
            i = j
        i += 1
    return count % 2 == 1


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    if not root.is_dir():
        print(f"error: {root} is not a directory", file=sys.stderr)
        return 2
    all_violations: list[str] = []
    file_count = 0
    for path in list_test_files(root):
        found = audit_one(path)
        if found:
            file_count += 1
            all_violations.extend(found)
    for violation in all_violations:
        print(violation)
    if not all_violations:
        print(f"\n=== no-comments-in-test-files: 0 violation(s) in 0 file(s) ===")
        return 0
    print(
        f"\n=== no-comments-in-test-files: {len(all_violations)} violation(s) "
        f"in {file_count} file(s) ==="
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
