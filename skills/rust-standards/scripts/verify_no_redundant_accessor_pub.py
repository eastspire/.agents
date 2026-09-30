#!/usr/bin/env python3
"""Forbid redundant explicit `pub` inside lombok accessor attributes.

Background (rust-standards §L):
`lombok_macros::Visibility` derives `Default = Public`
(`lombok-macros/src/visibility/enum.rs`). So when NO visibility is
written, the generated accessor is already `pub`. Writing `pub`
explicitly is therefore a no-op that only adds noise:

    #[get(pub)]                 ->  #[get]
    #[get(pub, type(copy))]     ->  #[get(type(copy))]
    #[get(type(copy), pub)]     ->  #[get(type(copy))]
    #[set(pub)]                 ->  #[set]
    #[get_mut(pub)]             ->  #[get_mut]

Only the accessors that deliberately narrow visibility keep a
visibility argument — `pub(crate)`, `pub(super)`, and private. Those
are meaningful and are NOT flagged:

    #[get(pub(crate))]           stays
    #[get(pub(crate), type(copy))]  stays
    #[get_mut(pub(crate))]       stays

Read-only. Exits non-zero when any redundant `pub` is present.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

# Any lombok accessor attribute whose argument list mentions `pub`
# but NOT `pub(` (which would be pub(crate) / pub(super)).
ACCESSOR_RE = re.compile(
    r"#\[(get|set|get_mut|with|new|constructor)\b([^\]]*)\]"
)

# A bare `pub` token: word boundary, not followed by `(`.
REDUNDANT_PUB_RE = re.compile(r"(?<![\w])pub(?![\s]*\()")

# Attributes whose whole argument list is only options, never a
# visibility — e.g. `#[new(skip)]`, `#[with(...)]` have no visibility
# slot at all, so a `pub` there is always wrong.
NEVER_VISIBILITY = {"new", "with", "constructor"}

SKIP_DIRS = {"target", ".git", "node_modules", ".cargo", "dist", "www"}


def iter_rust_files(root: Path):
    for path in sorted(root.rglob("*.rs")):
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        yield path


def check_text(text: str) -> list[tuple[int, str]]:
    """Return [(line_no, offending_attribute)] for redundant pub forms."""
    hits = []
    for line_no, line in enumerate(text.split("\n"), start=1):
        stripped = line.strip()
        # Doc/comment lines cannot carry a real attribute.
        if stripped.startswith("//"):
            continue
        for match in ACCESSOR_RE.finditer(line):
            name, args = match.group(1), match.group(2)
            if name in NEVER_VISIBILITY:
                if REDUNDANT_PUB_RE.search(args):
                    hits.append((line_no, match.group(0)))
                continue
            # `pub(` is pub(crate) / pub(super) — legitimate narrowing.
            if REDUNDANT_PUB_RE.search(args):
                hits.append((line_no, match.group(0)))
    return hits


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: verify_no_redundant_accessor_pub.py <repo_root>", file=sys.stderr)
        return 2
    root = Path(sys.argv[1]).resolve()
    if not root.exists():
        print(f"not a directory: {root}", file=sys.stderr)
        return 2

    files = list(iter_rust_files(root))
    violations = []
    for path in files:
        text = path.read_text(encoding="utf-8", errors="replace")
        for line_no, attr in check_text(text):
            violations.append(
                f"{path}:{line_no}: redundant explicit `pub` in {attr} "
                f"— lombok accessors default to Public; write the attribute "
                f"without `pub`"
            )

    for line in violations:
        print(line)

    print(f"{len(files)} files checked, {len(violations)} violations")
    return 1 if violations else 0


if __name__ == "__main__":
    sys.exit(main())
