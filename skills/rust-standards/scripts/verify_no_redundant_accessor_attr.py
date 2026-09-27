#!/usr/bin/env python3
"""Forbid redundant lombok accessor attributes whose default already generates them.

Background (rust-standards §L, user rule 2026-09-27):
"新增校验 #[get]、#[get_mut] 和 #[set] 不应该存在，默认都是生成的".

`#[derive(Data)]` is `Getter + GetterMut + Setter`, so a field of a derived
struct ALREADY gets its accessor generated. Writing the attribute with no
arguments says nothing the derive did not already do:

    #[derive(Data)]
    pub struct S {
        #[get]          ->  name: String,          // redundant: Data already makes get_name()
        #[get_mut]      ->  count: u32,            // redundant: Data already makes get_mut_count()
        #[set]          ->  flag: bool,            // redundant: Data already makes set_flag()
    }

This is the same class of noise as a redundant `pub` (check 23,
`verify_no_redundant_accessor_pub.py`): a default re-stated at the use site.
That script catches `#[get(pub)]`; this one catches the bare `#[get]` that is
left once the `pub` is removed. The two are complementary rungs of the same
rule, not duplicates.

Deliberately NOT flagged — the attribute carries real information the derive
cannot infer, so removing it would change behaviour:

    #[get(pub(crate))]            // narrows visibility (the §17.14 exposure rule)
    #[get(type(copy))]            // changes the return type
    #[get(pub(crate), type(copy))]  // both of the above
    #[get(skip)] / #[set(skip)]   // opts the field OUT of generation
    #[set(Into)] / #[set(clone)]  // parameter conversion
    #[new(...)] / #[with(...)]    // different macros, different slots

Exemptions:
  - comment lines (a `//` mentioning `#[get]` is documentation, not an attribute)
  - the word appears in any other form: `#[getter]`, `#[getter_mut]`, `#[get_all]`

Read-only. Exits 1 when any redundant bare accessor attribute is present.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

# The three accessor attributes this rule covers. `new` / `with` are NOT here:
# `New` and `With` are separate derives, so `#[new(...)]` is never implied by
# `Data` and always carries meaning.
ACCESSOR_NAMES = ("get", "get_mut", "set")

# A bare accessor attribute with NO argument list: `#[get]`, `#[ set ]`.
# `(?!\s*[(])` is the load-bearing part — any `(...)` means the attribute carries
# options and is therefore not redundant. `get_mut` is tried before `get` so the
# longer name wins (a `get` prefix match would otherwise consume it).
BARE_ACCESSOR_RE = re.compile(
    r"#\[\s*(get_mut|get|set)\s*\](?!\s*[(])"
)

# Guard against longer attribute names that merely start with the same prefix
# (`#[getter]`, `#[get_all]`, `#[setter]`): the name must end at the `]`.
LONG_NAME_RE = re.compile(r"#\[\s*(get_mut|get|set)\s*[A-Za-z_0-9]")

# Derives that generate accessors on their own. A bare `#[get]` only *duplicates*
# generation when the struct actually derives one of these; on a struct that
# derives nothing, `#[get]` would be the only thing creating the accessor and is
# then NOT redundant.
GENERATING_DERIVES = ("Getter", "GetterMut", "Setter", "Data")

# Any `#[derive(...)]` list on the file. Used only as a cheap pre-filter: a file
# with no derive at all cannot contain a redundant accessor attribute.
DERIVE_RE = re.compile(r"#\[\s*derive\s*\(([^)]*)\)\s*\]", re.DOTALL)

SKIP_DIRS = {"target", ".git", "node_modules", ".cargo", "dist", "www"}


def iter_rust_files(root: Path):
    for path in sorted(root.rglob("*.rs")):
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        yield path


def file_generates_accessors(text: str) -> bool:
    """True when any struct in this file derives an accessor-generating macro."""
    return any(
        name in derives
        for derives in DERIVE_RE.findall(text)
        for name in (n.strip() for n in derives.split(","))
        if name in GENERATING_DERIVES
    )


def audit_one(path: Path) -> list[str]:
    """Per-file check, so staged_file_gate.py can diff HEAD vs worktree."""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except (OSError, UnicodeDecodeError):
        return []

    if not file_generates_accessors(text):
        return []

    findings = []
    for line_no, line in enumerate(text.split("\n"), start=1):
        stripped = line.strip()
        # A comment mentioning the attribute is documentation, not an attribute.
        if stripped.startswith("//"):
            continue
        for match in BARE_ACCESSOR_RE.finditer(line):
            # `#[getter]` / `#[get_all]` — a different, longer attribute name.
            if LONG_NAME_RE.match(match.group(0) + ""):
                tail = line[match.end():]
                if re.match(r"\s*[A-Za-z_0-9]", tail):
                    continue
            findings.append(
                f"{path}:{line_no}: redundant bare `#[{match.group(1)}]` — "
                f"`#[derive(Data)]` already generates this accessor; delete the "
                f"attribute (keep it only if it narrows visibility or sets a "
                f"type, e.g. `#[{match.group(1)}(pub(crate))]`)"
            )
    return findings


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: verify_no_redundant_accessor_attr.py <repo_root>", file=sys.stderr)
        return 2
    root = Path(sys.argv[1]).resolve()
    if not root.is_dir():
        print(f"not a directory: {root}", file=sys.stderr)
        return 2

    files = list(iter_rust_files(root))
    violations = []
    for path in files:
        violations.extend(audit_one(path))

    for line in violations:
        print(line)

    print(f"{len(files)} files checked, {len(violations)} violations")
    return 1 if violations else 0


if __name__ == "__main__":
    sys.exit(main())
