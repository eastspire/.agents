#!/usr/bin/env python3
"""
Verify §13.8 Cargo.toml top-level section header separation (2026-09-27).

§13.8 rule (user 钦定):
  - Every top-level `[section]` header in a `Cargo.toml` MUST be preceded
    by exactly one blank line if it follows non-section content.
  - "Section header" = a `[xxx]` table heading at column 0
    (`[[xxx]]` is an array-of-tables element, NOT counted as a top-level
    section header — it's an element of an existing section, so no blank
    line required).
  - First section header (after `[package]` opening if any) needs no
    preceding blank because the file starts at the header.
  - This rule does NOT apply inside dep blocks — that's §13.7 round 4
    territory and handled by `verify_dep_order.py`.

Why this exists: per `audit-pitfalls §82` (2026-09-27 user observation),
hyperlane root `Cargo.toml` had `[dependencies]` directly after
`tokio-rustls = { ... ] }` (the closing `] }` of a multi-line entry),
and similar 6 violations across 3 repos. CI's `cargo check` / `clippy`
/ `test` all passed because TOML allows it, but visually it merges the
previous section's content with the next section header. The fix is one
blank line per section transition.

Exits 0 if all transitions are blank-separated, 1 if any violations.

Usage:
    python3 verify_section_blanks.py [ROOT]

Default ROOT = current directory.
Excludes `target/`, `~/.cargo/registry/`, `*/tmp/test_*/` (crate-cli
test fixtures).
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def find_cargo_tomls(root: Path) -> list[Path]:
    r = subprocess.run(
        ["find", str(root), "-name", "Cargo.toml", "-not", "-path", "*/target/*"],
        capture_output=True,
        text=True,
    )
    files = []
    for line in r.stdout.strip().splitlines():
        if "/.cargo/registry/" in line or "/tmp/test_" in line:
            continue
        files.append(Path(line))
    return files


def check_file(path: Path) -> list[str]:
    """Return violation descriptions for this file.

    A violation is: a top-level `[section]` header at line N (1-indexed)
    such that line N-1 is non-blank. The first section header of the file
    (line 1 or line 2 with leading [package]) is exempt.
    """
    text = path.read_text()
    lines = text.splitlines()
    violations: list[str] = []

    # Find all top-level section headers
    section_positions: list[tuple[int, str]] = []
    for i, line in enumerate(lines):
        if line.startswith("[") and line.endswith("]") and not line.startswith("[["):
            section_positions.append((i, line))

    if not section_positions:
        return violations

    for idx, (cur_idx, sec) in enumerate(section_positions):
        cur_line_no = cur_idx + 1  # 1-indexed for human display

        # First section: file start, exempt.
        if idx == 0:
            continue

        # Look at the immediately preceding line
        prev_line = lines[cur_idx - 1] if cur_idx > 0 else ""
        if prev_line.strip():
            # No blank line between previous content and this section header
            violations.append(
                f"{path}:{cur_line_no}: section `{sec}` is not separated "
                f"from the previous line (`{prev_line.strip()[:60]}`) "
                f"by a blank line (§13.8)"
            )
    return violations


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    if not root.is_dir():
        print(f"error: {root} is not a directory", file=sys.stderr)
        return 2

    files = find_cargo_tomls(root)
    if not files:
        print(f"No Cargo.toml files found under {root}", file=sys.stderr)
        return 2

    total = 0
    for f in sorted(files):
        for v in check_file(f):
            print(v)
            total += 1

    print(f"\n{len(files)} files checked, {total} violations")
    return 0 if total == 0 else 1


if __name__ == "__main__":
    sys.exit(main())