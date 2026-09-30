#!/usr/bin/env python3
"""Forbid bare, argument-less lombok accessor attributes.

Background (rust-standards §17.14.1):
each lombok derive macro already emits its accessor for every field,
with no per-field attribute required. `Data` derives all three
(`lombok-macros/src/generate/fn.rs` calls
`inner_lombok_data(input, true, true, true)`), and `Getter` /
`GetterMut` / `Setter` each emit their own single accessor. So a bare
attribute adds nothing:

    #[derive(Data)]            #[derive(Data)]
    pub struct S {             pub struct S {
        #[get]        <-- drop     b: i32,
        b: i32,      <-- keep }
    }

Only the attribute whose accessor the derive set does NOT already
provide is load-bearing, and those stay:

    #[derive(Getter)]          struct with #[set]  -> set is required
    pub struct S { b: i32 }

    #[derive(Data)]            struct with #[set(skip)]  -> skip is config
    pub struct S {             pub struct S {
        b: i32,                     #[set(skip)]
    }                               b: i32,
                                }

Attributes carrying arguments (`type(copy)`, `skip`, ...) are never
touched — their arguments configure generation and are not redundant.

Read-only. Exits non-zero when any redundant bare attribute is present.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

# Which accessor kinds each derive macro provides for free.
PROVIDES: dict[str, set[str]] = {
    "Data": {"get", "get_mut", "set"},
    "Getter": {"get"},
    "GetterMut": {"get_mut"},
    "Setter": {"set"},
}

SKIP_DIRS = {"target", ".git", "node_modules", ".cargo", "dist", "www"}

# Bare accessor attribute: no parentheses at all.
BARE_RE = re.compile(r"#\[(get|get_mut|set)\]")

# Item declarations (braced or tuple structs, enums, unions).
ITEM_RE = re.compile(r"\b(?:struct|enum|union)\s+(\w+)")

DERIVE_RE = re.compile(r"#\[derive\(([^)]*)\)\]")
ATTR_RE = re.compile(r"#\[[^\]]*\]")

# Anything that ends the attribute run that may precede an item.
STOP_RE = re.compile(r"\b(?:fn|impl|trait|mod|use|static|const|type|macro)\b")


def strip_comments(text: str) -> str:
    """Blank out comments and string/char literal bodies, preserving offsets.

    Offset preservation matters: violations are reported at the original
    line/column. Comment stripping is what keeps prose like
    "This struct defines ..." or a doc-comment showing `#[set]` from being
    parsed as code.
    """
    out: list[str] = []
    i = 0
    n = len(text)
    while i < n:
        c = text[i]
        two = text[i : i + 2]
        if two == "//":
            while i < n and text[i] != "\n":
                out.append(" ")
                i += 1
        elif two == "/*":
            depth = 1
            out.append("  ")
            i += 2
            while i < n and depth:
                if text[i : i + 2] == "/*":
                    depth += 1
                    out.append("  ")
                    i += 2
                elif text[i : i + 2] == "*/":
                    depth -= 1
                    out.append("  ")
                    i += 2
                else:
                    out.append("\n" if text[i] == "\n" else " ")
                    i += 1
        elif c in "rb" and re.match(r"r(#*)\"", text[i:]):
            m = re.match(r"r(#*)\"", text[i:])
            assert m
            hashes = m.group(1)
            end = text.find('"' + hashes, i + m.end())
            end = n if end == -1 else end + 1 + len(hashes)
            for ch in text[i:end]:
                out.append("\n" if ch == "\n" else " ")
            i = end
        elif c == '"':
            out.append(" ")
            i += 1
            while i < n and text[i] != '"':
                if text[i] == "\\":
                    out.append(" ")
                    i += 1
                    if i < n:
                        out.append("\n" if text[i] == "\n" else " ")
                        i += 1
                    continue
                out.append("\n" if text[i] == "\n" else " ")
                i += 1
            if i < n:
                out.append(" ")
                i += 1
        elif c == "'" and re.match(r"'(?:\\.|[^\\'])'", text[i:]):
            m = re.match(r"'(?:\\.|[^\\'])'", text[i:])
            assert m
            for ch in m.group(0):
                out.append("\n" if ch == "\n" else " ")
            i += m.end()
        else:
            out.append(c)
            i += 1
    return "".join(out)


def find_body(text: str, after: int) -> tuple[int, int] | None:
    """Return the (start, end) span of an item body, or None if unit.

    Skips a generic parameter list first, so const-generic braces like
    `Foo<{ N }>` do not confuse brace matching.
    """
    i = after
    n = len(text)
    while i < n and text[i].isspace():
        i += 1
    depth = 0
    while i < n:
        c = text[i]
        if c == "<":
            depth += 1
        elif c == ">":
            depth -= 1
        elif depth == 0 and c in "{(":
            break
        elif depth == 0 and c == ";":
            return None
        elif depth == 0 and c == "\n" and text[i + 1 : i + 2] == "\n":
            return None
        i += 1
    if i >= n or text[i] not in "{(":
        return None

    opener = text[i]
    closer = {"{": "}", "(": ")"}[opener]
    body_start = i
    depth = 0
    while i < n:
        if text[i] == opener:
            depth += 1
        elif text[i] == closer:
            depth -= 1
            if depth == 0:
                return (body_start, i + 1)
        i += 1
    return None


def derives_for_item(text: str, item_start: int) -> set[str]:
    """Collect derive names attached to the item starting at item_start.

    Walks left from the declaration over the run of attributes and
    whitespace. Stops at the first thing that is not an attribute, so
    an unrelated attribute between two derives does not truncate the run.
    """
    derives: set[str] = set()
    pos = item_start
    while pos > 0:
        j = pos
        # Skip whitespace, then the visibility keyword (`pub`, `pub(crate)`),
        # so the walk lands on the attribute run in front of the item.
        while j > 0 and text[j - 1].isspace():
            j -= 1
        vis = re.search(r"(?:pub(?:\s*\([^)]*\))?|(?:priv|async|const|unsafe|default)\b)\s*$",
                        text[:j])
        if vis:
            j = vis.start()
            while j > 0 and text[j - 1].isspace():
                j -= 1
        if j <= 0:
            break
        if text[j - 1] != "]":
            break
        end = j
        # Walk back to the matching `[`. A naive backward scan stops on the
        # first `]`, which is the inner closer of a `#[derive(...)]` token
        # containing a nested list. Track depth so the outer `[` is found.
        depth = 0
        while j > 0:
            j -= 1
            ch = text[j]
            if ch == "]":
                depth += 1
            elif ch == "[":
                depth -= 1
                if depth == 0:
                    break
        if j <= 0 or text[j] != "[":
            break
        # `text[j:end]` starts at `[`; the `#` sits just before it. Keep it
        # so the slice is the complete `#[...]` attribute token.
        attr = text[j - 1 : end] if j > 0 and text[j - 1] == "#" else text[j:end]
        if not attr.startswith("#["):
            break
        m = DERIVE_RE.fullmatch(attr)
        if m:
            for part in m.group(1).split(","):
                name = part.strip()
                if name:
                    derives.add(name)
        pos = j
    return derives


def check_text(text: str) -> list[tuple[int, str, str]]:
    """Return [(line_no, attribute, item_name)] for redundant bare accessors."""
    code = strip_comments(text)
    items = []
    for m in ITEM_RE.finditer(code):
        body = find_body(code, m.end())
        if body is None:
            continue
        start, end = body
        items.append((m.start(), m.group(1), start, end))

    hits: list[tuple[int, str, str]] = []
    for am in BARE_RE.finditer(code):
        kind = am.group(1)
        owner = None
        for decl_start, name, start, end in items:
            if start <= am.start() < end:
                owner = (decl_start, name)
                break
        if owner is None:
            # Not inside a struct/enum body (e.g. an impl or a macro
            # invocation). Too ambiguous to judge — leave it alone.
            continue
        decl_start, name = owner
        provided: set[str] = set()
        for d in derives_for_item(code, decl_start):
            provided |= PROVIDES.get(d, set())
        if not provided:
            # No recognised accessor-providing derive; stay conservative.
            continue
        if kind in provided:
            hits.append((code.count("\n", 0, am.start()) + 1, am.group(0), name))
    return hits

def iter_rust_files(root: Path):
    for path in sorted(root.rglob("*.rs")):
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        yield path


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: verify_no_redundant_bare_accessor.py <repo_root>", file=sys.stderr)
        return 2
    root = Path(sys.argv[1]).resolve()
    if not root.exists():
        print(f"not a directory: {root}", file=sys.stderr)
        return 2

    files = list(iter_rust_files(root))
    violations = []
    for path in files:
        text = path.read_text(encoding="utf-8", errors="replace")
        for line_no, attr, item in check_text(text):
            violations.append(
                f"{path}:{line_no}: redundant bare {attr} on `{item}` — the derive "
                f"already generates this accessor; delete the attribute"
            )

    for line in violations:
        print(line)

    print(f"{len(files)} files checked, {len(violations)} violations")
    return 1 if violations else 0


if __name__ == "__main__":
    sys.exit(main())
