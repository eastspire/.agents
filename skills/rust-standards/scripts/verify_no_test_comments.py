#!/usr/bin/env python3
"""
Verify rust-standards §14.5: NO comments in any test file.

Per §14.5 (2026-09-12 user clarification, 2026-09-26 strengthening):

  Tests have ZERO comments.  This applies to:
    - file-level //! headers
    - per-fn /// doc comments
    - fn-body inline // comments
    - any line whose first non-whitespace characters are `//`, `///`,
      or `//!`

  Test fn name = documentation; assertion messages express the
  expected behavior.  NO EXCEPTIONS.

Per round 3 (audit-pitfalls §37) all three forms (`//`, `///`, `//!`)
are banned.  The previous regex `^\\s*//[^/]` accidentally excluded
`///` — this verifier catches all three explicitly.

Exits 0 if clean, 1 if any violation.  Reports each violation as
`<file>:<line>: <text>`.

Usage:
    python3 verify_no_test_comments.py [ROOT]

Default ROOT = current directory.  Recursively walks every `tests/**/*.rs`
under ROOT.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path


# Match any line that is a comment (after optional leading whitespace):
#   - //  (regular inline / line comment)
#   - /// (outer doc comment)
#   - //! (inner doc comment)
# The previous regex ^\\s*//[^/] missed `///` because the second `/`
# matched the `[^/]` exclusion.  This new regex catches all three.
COMMENT_LINE = re.compile(r"^\s*(//|///|//!)")


def _list_test_files(root: Path) -> list[Path]:
    """Find every tests/**/*.rs file under root, including the loose
    root tests/<file>.rs files.  Skip target/ and .cargo/."""
    r = subprocess.run(
        ["find", str(root), "-path", "*/tests/*", "-name", "*.rs",
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
    violations: list[str] = []
    for i, line in enumerate(text.splitlines(), start=1):
        if COMMENT_LINE.match(line):
            violations.append(
                f"{path}:{i}: forbidden comment in test file (§14.5): "
                f"{line.strip()[:80]!r}"
            )
    return violations


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    if not root.is_dir():
        print(f"error: {root} is not a directory", file=sys.stderr)
        return 2
    files = _list_test_files(root)
    total = 0
    files_with_v = 0
    for f in files:
        v = audit_one(f)
        if v:
            files_with_v += 1
            total += len(v)
            for line in v:
                print(line)
    print(f"\n=== no-comments-in-tests: "
          f"{total} violation(s) in {files_with_v} file(s) ===")
    return 0 if total == 0 else 1


if __name__ == "__main__":
    sys.exit(main())