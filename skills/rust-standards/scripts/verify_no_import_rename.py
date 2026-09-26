#!/usr/bin/env python3
"""§6.5 verifier: `use ... as ...` import renaming is forbidden.

Rule (2026-09-26 user directive):
  - Type imports must NOT be renamed with `as` in `use` statements.
  - When names conflict, do NOT alias the import; instead qualify at the
    usage site with the shortest distinguishable namespace
    (e.g. write `task::Context` at the call site, not
    `use std::task::Context as TaskContext;`).

Detection:
  - Track `use` statements, including grouped multi-line blocks
    (`use std::{ fmt::{self, Write as FmtWrite} };`).
  - Any `as <ident>` inside a `use` statement is a violation,
    regardless of visibility (`use` / `pub use` / `pub(crate) use`).

Exit code: 0 = compliant, 1 = violations found, 2 = usage error.
"""

import re
import subprocess
import sys
from pathlib import Path

USE_START = re.compile(r"^\s*(?:pub(?:\([^)]*\))?\s+)?use\s")
AS_RENAME = re.compile(r"\bas\s+[A-Za-z_][A-Za-z0-9_]*")


def list_rs_files(root: Path) -> list[Path]:
    result = subprocess.run(
        [
            "find",
            str(root),
            "-name",
            "*.rs",
            "-not",
            "-path",
            "*/target/*",
            "-not",
            "-path",
            "*/.cargo/registry/*",
        ],
        capture_output=True,
        text=True,
    )
    return [Path(line) for line in result.stdout.splitlines() if line.strip()]


def audit_one(path: Path) -> list[str]:
    try:
        text = path.read_text()
    except (OSError, UnicodeDecodeError):
        return []
    violations: list[str] = []
    in_use = False
    for number, line in enumerate(text.splitlines(), start=1):
        stripped: str = line.strip()
        if not in_use:
            if not USE_START.match(line):
                continue
            if stripped.startswith("//"):
                continue
            in_use = True
        if in_use:
            match = AS_RENAME.search(line)
            if match and not stripped.startswith("//"):
                violations.append(
                    f"{path}:{number}: import rename via `as` forbidden; "
                    f"qualify at usage site instead (§6.5): {stripped!r}"
                )
            if ";" in line:
                in_use = False
    return violations


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    if not root.is_dir():
        print(f"error: {root} is not a directory", file=sys.stderr)
        return 2
    all_violations: list[str] = []
    file_count = 0
    for path in list_rs_files(root):
        violations = audit_one(path)
        if violations:
            file_count += 1
            all_violations.extend(violations)
    for violation in all_violations:
        print(violation)
    print(f"\n=== no-import-rename: {len(all_violations)} violation(s) in {file_count} file(s) ===")
    return 1 if all_violations else 0


if __name__ == "__main__":
    sys.exit(main())
