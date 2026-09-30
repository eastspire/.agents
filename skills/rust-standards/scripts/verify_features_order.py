#!/usr/bin/env python3
"""Verify `features = [...]` arrays are sorted per rust-standards §13.7.

Companion to verify_dep_order.py. That script orders dependency ENTRIES
within a `[dependencies]`-style block; this one orders the elements INSIDE
each dependency's `features = [...]` array.

Rule (§13.7, length-first with lexicographic tiebreak):
    * Primary: element length in characters, ascending.
    * Secondary: element text, ASCII lexicographic ascending.

The two keys are the same pair verify_dep_order.py uses for entry order
(`entry_sort_key` returns `(total, key)`), so a features array reads in
exactly the same visual rhythm as the block that contains it.

Scope: dependency features arrays only. `required-features = []` on a
`[[bin]]` target is a different key and is deliberately skipped.

Read-only. Exits non-zero when any array is out of order.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

# `features = [ ... ]` where the key is preceded by whitespace or a
# delimiter, NOT a hyphen — this excludes `required-features`, and also
# avoids matching inside a quoted string value.
FEATURES_RE = re.compile(r"(?<![\w-])features\s*=\s*\[(.*?)\]", re.DOTALL)

# Matches a single element: a quoted string, possibly with a trailing
# comma. A comment inside the array is a hard stop (see below).
ELEMENT_RE = re.compile(r'"([^"]+)"\s*,?')

# Any comment marker inside an array makes auto-handling unsafe: we
# cannot tell whether a comment documents a specific element, and
# re-ordering could silently re-associate it.
COMMENT_RE = re.compile(r"^\s*#|#\s", re.MULTILINE)


def iter_cargo_tomls(root: Path):
    """Yield every Cargo.toml under root, skipping build/vendor dirs."""
    skip = {"target", ".git", "node_modules", ".cargo", "dist", "www"}
    for path in sorted(root.rglob("Cargo.toml")):
        if any(part in skip for part in path.parts):
            continue
        yield path


def parse_features(text: str):
    """Return [(array_start_offset, [elements])] for dependency features arrays.

    Arrays containing comments are skipped entirely — see module docstring.
    """
    found = []
    for match in FEATURES_RE.finditer(text):
        body = match.group(1)
        if COMMENT_RE.search(body):
            continue
        elements = [m.group(1) for m in ELEMENT_RE.finditer(body)]
        if elements:
            found.append((match.start(), elements))
    return found


def sort_key(element: str) -> tuple[int, str]:
    """§13.7 order: length ascending, then lexicographic ascending."""
    return (len(element), element)


def check_file(path: Path) -> list[str]:
    """Return one violation line per out-of-order features array."""
    text = path.read_text(encoding="utf-8", errors="replace")
    violations = []
    for offset, elements in parse_features(text):
        if elements == sorted(elements, key=sort_key):
            continue
        line_no = text.count("\n", 0, offset) + 1
        expected = sorted(elements, key=sort_key)
        violations.append(
            f"{path}:{line_no}: features array not sorted per §13.7 "
            f"(length ascending, then lexicographic): "
            f"got {elements[:4]}... but expected {expected[:4]}..."
        )
    return violations


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: verify_features_order.py <repo_root>", file=sys.stderr)
        return 2
    root = Path(sys.argv[1]).resolve()
    if not root.exists():
        print(f"not a directory: {root}", file=sys.stderr)
        return 2

    manifests = list(iter_cargo_tomls(root))
    if not manifests:
        print("No Cargo.toml files found, nothing to check.", file=sys.stderr)
        return 2

    violations: list[str] = []
    for manifest in manifests:
        violations.extend(check_file(manifest))

    for line in violations:
        print(line)

    print(f"{len(manifests)} files checked, {len(violations)} violations")
    return 1 if violations else 0


if __name__ == "__main__":
    sys.exit(main())
