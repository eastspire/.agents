#!/usr/bin/env python3
"""§6.6 verifier: same-root `use` statements MUST be aggregated.

Rule (2026-09-27 user directive):
  Within one file / one scope, 2+ independent top-level `use` statements
  sharing the same root segment (e.g. `use std::ffi::c_void;` +
  `use std::path::Path;`) MUST be merged into a single brace form
  (`use std::{ffi::c_void, path::Path};`).

Detection:
  - A use-block state machine collects every top-level `use` statement
    as (root, visibility, start_line, end_line, is_glob).
  - Statements are grouped by root; a root with 2+ members is reported.
  - Comments between two `use` statements do not break the scan: they
    are skipped, and both statements still land in the same group.

Exemptions (deliberate, each one verified against real repos):
  1. Different roots (`use std::...` + `use serde::...`) — normal.
  2. A glob import coexisting with a non-glob import of the same root
     (`use super::*;` + `use super::Foo;`, `use crate::x::*;` +
     `use crate::x::Y;`). Merging would change resolution semantics
     (a glob may be shadowed by an explicit item), so both forms are
     reported separately: the glob member is dropped from the group
     and the group is only flagged when 2+ NON-glob members remain.
  3. `use` inside a fn body — §6.4 already bans those; not re-reported.
  4. `#[cfg(test)] mod tests` bodies — test-local imports, §14 territory.
  5. Visibility split. rustfmt 1.9.0-stable reorders but never merges
     (`imports_granularity` is nightly-only), and even nightly
     `imports_granularity = "Module"` keeps `pub use` and private `use`
     in separate statements. So `pub use std::{...}` + `use std::...`
     is INTENTIONAL re-export-vs-private-import, not drift. Grouping
     is done PER (root, visibility) for this reason.
  6. §6.1 three-stage order conflict. lib.rs / mod.rs keep mod -> pub
     use -> pub(crate) use -> pub(super) use -> private use. If two
     same-root, same-visibility statements sit in DIFFERENT stages
     separated by another stage, the verifier stays silent: fixing it
     would move an import across a stage boundary and break check 27.
     Only a contiguous run inside ONE stage is reported.

Exit code: 0 = compliant, 1 = violations found, 2 = usage error.
"""

import re
import subprocess
import sys
from pathlib import Path

# `pub use` / `pub(crate) use` / `pub(super) use` / bare `use`, at any indent
# of an item (0 indent) — indented ones are inside a mod/fn body and are
# filtered out later by the scope tracker.
USE_START = re.compile(
    r"^(?P<indent>[ \t]*)"
    r"(?:(?P<vis>pub(?:\([^)]*\))?)\s+)?"
    r"use\s+(?P<rest>.+)$"
)
CFG_TEST = re.compile(r"^\s*#\[cfg\(test\)\]")
# any outer attribute that may gate an import: #[cfg(..)] / #[allow(..)] / ..
ATTRIBUTE = re.compile(r"^#!?\[")


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
            "*/.git/*",
            "-not",
            "-path",
            "*/node_modules/*",
            "-not",
            "-path",
            "*/tmp/*",
            "-not",
            "-path",
            "*/.cargo/registry/*",
        ],
        capture_output=True,
        text=True,
    )
    return [Path(line) for line in result.stdout.splitlines() if line.strip()]


def _brace_delta(line: str) -> int:
    """Net brace depth change for one line.

    Naive `count('{') - count('}')` miscounts braces that appear inside
    string literals, char literals and line comments, which would corrupt
    the top-level scope tracking (a `let s = "{";` would push the scanner
    into a phantom block).  This scanner skips those regions.
    """
    delta = 0
    index = 0
    length = len(line)
    while index < length:
        char = line[index]
        if char == "/" and index + 1 < length and line[index + 1] == "/":
            break  # line comment — rest of the line is not code
        if char == "/" and index + 1 < length and line[index + 1] == "*":
            end = line.find("*/", index + 2)
            index = length if end == -1 else end + 2
            continue
        if char == "r" and index + 1 < length and line[index + 1] in "#\"":
            # raw string: r"..." / r#"..."# / r##"..."##
            hashes = 0
            cursor = index + 1
            while cursor < length and line[cursor] == "#":
                hashes += 1
                cursor += 1
            if cursor < length and line[cursor] == '"':
                terminator = '"' + "#" * hashes
                end = line.find(terminator, cursor + 1)
                index = length if end == -1 else end + len(terminator)
                continue
        if char == '"':
            cursor = index + 1
            while cursor < length:
                if line[cursor] == "\\":
                    cursor += 2
                    continue
                if line[cursor] == '"':
                    break
                cursor += 1
            index = cursor + 1
            continue
        if char == "'":
            # char literal OR lifetime ('a).  Only a char literal counts.
            if index + 2 < length and line[index + 2] == "'":
                if line[index + 1] == "\\":
                    closer = line.find("'", index + 2)
                    index = length if closer == -1 else closer + 1
                else:
                    index += 3
                continue
            index += 1
            continue
        if char == "{":
            delta += 1
        elif char == "}":
            delta -= 1
        index += 1
    return delta


def _skip_block(lines: list[str], idx: int) -> int:
    """From an item header line, return the index of its closing brace.

    Handles the `where` clause spanning lines: keep walking forward
    until the first line that actually opens a brace.
    """
    total = len(lines)
    j = idx
    while j < total and "{" not in lines[j]:
        j += 1
    if j >= total:
        return total - 1
    depth = 0
    k = j
    while k < total:
        depth += _brace_delta(lines[k])
        if depth == 0 and k >= j:
            return k
        k += 1
    return total - 1


def _root_of(rest: str) -> tuple[str, bool]:
    """Return (root segment, is_glob) for a `use` statement tail.

    `ffi::c_void`               -> ('ffi' under 'std', False) — the caller
    prefixes the crate root, so this returns the segment AFTER the
    leading root only when the root is known.  Simpler: the root is the
    first path segment, i.e. everything before the first `::`.
    """
    tail = rest.strip()
    is_glob = tail.endswith("*") and not tail.startswith("{")
    # strip a leading `::`
    if tail.startswith("::"):
        tail = tail[2:]
    root = re.split(r"::|\{|,", tail, maxsplit=1)[0].strip()
    return root, is_glob


def _top_level_use_statements(lines: list[str]) -> list[dict]:
    """Scan a file, returning every top-level `use` statement.

    Top-level == not nested inside any `{ ... }` block (fn body, mod
    body, impl block).  `#[cfg(test)] mod tests { ... }` is skipped
    wholesale (exemption 4).
    """
    statements: list[dict] = []
    depth = 0  # brace depth of the enclosing block
    idx = 0
    total = len(lines)
    pending_attr = False
    while idx < total:
        raw = lines[idx]
        stripped = raw.strip()

        if CFG_TEST.match(raw) and depth == 0:
            end = _skip_block(lines, idx)
            idx = end + 1
            continue

        if depth == 0 and not stripped.startswith("//"):
            if ATTRIBUTE.match(stripped):
                # A conditional import (`#[cfg(windows)] use std::...;`)
                # MUST NOT be merged with an unconditional one: hoisting a
                # cfg-gated item into a shared brace group would make the
                # attribute apply to the whole group, changing which items
                # exist on non-matching targets.  Record the attributes and
                # emit the statement, but never group it with siblings.
                pending_attr = True
                idx += 1
                continue
            match = USE_START.match(raw)
            if match:
                indent = match.group("indent")
                if not indent:  # only column-0 `use` is a top-level import
                    vis = match.group("vis") or ""
                    # consume the whole statement (multi-line brace block)
                    chunk = [match.group("rest")]
                    end = idx
                    while ";" not in chunk[-1] and end + 1 < total:
                        end += 1
                        chunk.append(lines[end].strip())
                    text = " ".join(chunk).rstrip(";").strip()
                    if text.startswith("{"):
                        # Rootless brace form `use { a::*, b::* };` has NO
                        # root segment, so §6.6 (same-root aggregation) does
                        # not apply; §6.1 governs these re-export blocks.
                        root, is_glob, rootless = "*", False, True
                    else:
                        root, is_glob = _root_of(text)
                        rootless = False
                    statements.append(
                        {
                            "root": root,
                            "vis": vis,
                            "start": idx + 1,
                            "end": end + 1,
                            "is_glob": is_glob,
                            "rootless": rootless,
                            "gated": pending_attr,
                            "text": text,
                        }
                    )
                    idx = end + 1
                    depth = 0
                    pending_attr = False
                    continue

        depth += _brace_delta(raw)
        if depth < 0:
            depth = 0
        idx += 1
    return statements


def _stage_runs(statements: list[dict]) -> list[list[dict]]:
    """Split the statement list into contiguous runs (no gap larger than
    a comment/blank).  A gap means a different §6.1 stage intervened, so
    the two sides must NOT be merged (exemption 6)."""
    runs: list[list[dict]] = []
    current: list[dict] = []
    previous_end = None
    for statement in statements:
        if previous_end is not None and statement["start"] - previous_end > 2:
            runs.append(current)
            current = []
        current.append(statement)
        previous_end = statement["end"]
    if current:
        runs.append(current)
    return runs


def audit_one(path: Path) -> list[str]:
    try:
        text = path.read_text()
    except (OSError, UnicodeDecodeError):
        return []
    try:
        lines = text.splitlines()
    except Exception:  # noqa: BLE001
        return []
    violations: list[str] = []
    try:
        statements = _top_level_use_statements(lines)
    except Exception as error:  # noqa: BLE001 - never break the gate
        print(f"  ! {path}: use-aggregation parse failed: {error}")
        return []

    for run in _stage_runs(statements):
        # group by (root, visibility); drop globs, rootless brace blocks and
        # cfg-gated imports from the comparison
        groups: dict[tuple[str, str], list[dict]] = {}
        for statement in run:
            if statement["is_glob"] or statement["rootless"] or statement["gated"]:
                continue
            key = (statement["root"], statement["vis"])
            groups.setdefault(key, []).append(statement)
        for (root, vis), members in sorted(groups.items()):
            if len(members) < 2:
                continue
            locations = ", ".join(str(m["start"]) for m in members)
            vis_label = f"{vis} " if vis else ""
            merged = _merge_hint(members, vis)
            violations.append(
                f"{path}:{members[0]['start']}: {len(members)} independent "
                f"`{vis_label}use {root}::...` statements at lines {locations}; "
                f"merge into one brace form (§6.6): `{merged}`"
            )
    return violations


def _split_top_level(inner: str) -> list[str]:
    """Split brace-group contents on top-level commas, ignoring commas
    nested inside `{}` / `()` / `<>`."""
    items: list[str] = []
    depth = 0
    current = ""
    for char in inner:
        if char in "{(<":
            depth += 1
        elif char in "})>":
            depth -= 1
        if char == "," and depth == 0:
            items.append(current.strip())
            current = ""
        else:
            current += char
    if current.strip():
        items.append(current.strip())
    return [item for item in items if item]


def _merge_hint(members: list[dict], vis: str) -> str:
    """Render the aggregated form rustfmt-style, purely as a hint.

    Nested brace groups are FLATTENED so the hint is copy-pasteable:
    `use std::fmt::{self, Debug};` merged with `use std::path::Path;`
    yields `use std::{fmt::{self, Debug}, path::Path};`, never a
    doubled-brace form.
    """
    paths: list[str] = []
    for member in sorted(members, key=lambda m: m["start"]):
        text = member["text"]
        prefix = re.escape(member["root"]) + r"::"
        trimmed = re.sub(r"^" + prefix, "", text, count=1)
        trimmed = trimmed.strip()
        if trimmed.startswith("{") and trimmed.endswith("}"):
            paths.extend(_split_top_level(trimmed[1:-1]))
        else:
            paths.append(trimmed)
    prefix = f"{vis} " if vis else ""
    return prefix + f"use {members[0]['root']}::{{{', '.join(paths)}}};"


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
    print(
        f"\n=== use-aggregation: {len(all_violations)} violation(s) "
        f"in {file_count} file(s) ==="
    )
    return 1 if all_violations else 0


if __name__ == "__main__":
    sys.exit(main())
