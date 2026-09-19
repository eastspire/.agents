#!/usr/bin/env python3
"""
Verify §13.7 dependency-block ordering for any Rust workspace.

§13.7 rule (round 3, 2026-09-14):
  - [dependencies], [dev-dependencies], [build-dependencies],
    [workspace.dependencies]:
      LOCAL first (alphabetic), single blank line at boundary, then
      THIRD-PARTY (alphabetic).
  - Local detection: dep name appears in [workspace] members OR equals
    the root [package] name.
  - The single blank line at the local/third-party boundary is the ONLY
    blank line allowed inside a dep block. No blanks between local-local
    or third-third entries.

Exits 0 if all blocks are correctly ordered, 1 if any violations found.

Usage:
    python3 verify_dep_order.py [ROOT]

Default ROOT = current directory.
Excludes `target/` and `~/.cargo/registry/`.

Why this exists: the previous round 2 rule (`(len, lex)` everywhere with
blank between every entry) was visually misleading — blanks without
semantic meaning. User correction in 2026-09-14: blanks must appear only
where they carry meaning (a group boundary).
"""
import re
import subprocess
from pathlib import Path


KEY_PATTERN = re.compile(r"^([a-zA-Z0-9_-]+)\s*=")


def find_cargo_tomls(root: Path) -> list[Path]:
    r = subprocess.run(
        ["find", str(root), "-name", "Cargo.toml", "-not", "-path", "*/target/*"],
        capture_output=True,
        text=True,
    )
    files = []
    for line in r.stdout.strip().splitlines():
        if "/.cargo/registry/" in line:
            continue
        files.append(Path(line))
    return files


def read_local_crate_names(path: Path) -> set[str]:
    """A dep is 'local' if its value contains `workspace = true` or
    `path = "..."` referring to another crate in this workspace.
    Returns workspace member package names (any dep pointing to one of
    these via workspace=true or path is local).
    """
    text = path.read_text()
    names: set[str] = set()
    # root [package] name is always local
    m = re.search(r'\[package\].*?name\s*=\s*"([\w-]+)"', text, re.S)
    if m:
        names.add(m.group(1))
    # [workspace] members → look up each member dir's [package] name
    m = re.search(r"members\s*=\s*\[(.*?)\]", text, re.S)
    if m:
        for d in re.findall(r'"(\w+)"', m.group(1)):
            sub = path.parent / d / "Cargo.toml"
            if sub.exists():
                sn = re.search(
                    r'\[package\].*?name\s*=\s*"([\w-]+)"', sub.read_text(), re.S
                )
                if sn:
                    names.add(sn.group(1))
    return names


def parse_block(text: str, section_name: str) -> list[tuple[str, list[str]]]:
    """Parse a [section] block and return list of (key, [lines]) tuples
    for each entry. Blank lines between entries are preserved as boundary
    markers (we don't flatten them out — they need to be checked).

    Returns entries as seqs; the structure of blank lines is recovered
    by interleaving: entries list in order, blanks list of bool.
    """
    m = re.search(rf"^\[\s*{re.escape(section_name)}\s*\]\s*\n", text, re.M)
    if not m:
        return []
    rest = text[m.end():]
    next_m = re.search(r"^\[\S+\]", rest, re.M)
    end = m.end() + (next_m.start() if next_m else len(rest))
    block = text[m.start():end]
    lines = block.splitlines()

    entries: list[tuple[str, list[str]]] = []
    blanks_after: list[bool] = []  # for each entry, whether followed by blank(s)
    cur_key: str | None = None
    cur_lines: list[str] = []
    pending_blank = False

    def flush():
        nonlocal cur_key, cur_lines
        if cur_key is not None:
            entries.append((cur_key, cur_lines))
            blanks_after.append(pending_blank)
        cur_key = None
        cur_lines = []

    for line in lines:
        if not line.strip():
            if cur_key is not None:
                pending_blank = True
            # multiple blanks — capture as one
            continue
        km = KEY_PATTERN.match(line)
        if km:
            flush()
            cur_key = km.group(1)
            cur_lines = [line]
            pending_blank = False
        else:
            cur_lines.append(line)
    flush()
    return entries


def expected_order_with_blank(entries, local_set):
    local = sorted(
        [(k, l) for k, l in entries if k in local_set],
        key=lambda kv: kv[0],
    )
    third = sorted(
        [(k, l) for k, l in entries if k not in local_set],
        key=lambda kv: kv[0],
    )
    if local and third:
        return local + [("", [""])] + third
    return local + third


def check_file(path: Path, local_set: set[str]) -> int:
    """Return count of violations found in this file."""
    text = path.read_text()
    sections = [
        "dependencies",
        "dev-dependencies",
        "build-dependencies",
        "workspace.dependencies",
    ]
    count = 0
    for sec in sections:
        entries = parse_block(text, sec)
        if not entries:
            continue
        expected = expected_order_with_blank(entries, local_set)
        # Build actual ordered list (with blank as "" marker)
        actual = []
        pending_blank = False
        for i, (k, ls) in enumerate(entries):
            if pending_blank:
                actual.append(("", [""]))
                pending_blank = False
            actual.append((k, ls))
            # Look at the source between this entry and the next
            # (we approximate by checking if there was a blank)
            # The blanks_after flag is set if any blank line was seen
            # while parsing this entry
        # Simpler: rebuild actual = entries with their blanks
        actual = []
        for i, (k, ls) in enumerate(entries):
            actual.append((k, ls))
            # Check if there's a blank between this entry and next:
            # In the original parse, the parser captured blanks via pending_blank
            # before seeing the next key. We need to recover that here.
        # Re-parse to also capture per-entry trailing blank
        ...

    return count


def check_file_v2(path: Path, local_set: set[str]) -> list[str]:
    """Return list of violation descriptions for this file."""
    text = path.read_text()
    violations = []
    for sec in ["dependencies", "dev-dependencies", "build-dependencies", "workspace.dependencies"]:
        m = re.search(rf"^\[\s*{re.escape(sec)}\s*\]\s*\n", text, re.M)
        if not m:
            continue
        rest = text[m.end():]
        next_m = re.search(r"^\[\S+\]", rest, re.M)
        end = m.end() + (next_m.start() if next_m else len(rest))
        block_text = text[m.start():end]

        # Parse entries + record whether each is followed by a blank line
        lines = block_text.splitlines()
        items: list[dict] = []  # each = {"key": str, "lines": [...], "followed_by_blank": bool}
        cur = None
        seen_blank_after = False
        for line in lines:
            if not line.strip():
                if cur is not None:
                    cur["followed_by_blank"] = True
                continue
            km = KEY_PATTERN.match(line)
            if km:
                if cur is not None:
                    items.append(cur)
                cur = {"key": km.group(1), "lines": [line], "followed_by_blank": False}
            else:
                if cur is not None:
                    cur["lines"].append(line)
        if cur is not None:
            items.append(cur)

        if not items:
            continue

        # Build actual sequence with blank markers
        actual_seq: list[tuple[str, bool]] = []  # (key_or_empty, is_blank)
        for it in items:
            actual_seq.append((it["key"], False))
            if it["followed_by_blank"]:
                actual_seq.append(("", True))

        # Build expected sequence
        local = sorted([it for it in items if it["key"] in local_set], key=lambda x: x["key"])
        third = sorted([it for it in items if it["key"] not in local_set], key=lambda x: x["key"])
        expected_seq: list[tuple[str, bool]] = []
        for it in local:
            expected_seq.append((it["key"], False))
        if local and third:
            expected_seq.append(("", True))
        for it in third:
            expected_seq.append((it["key"], False))

        # Trim trailing blanks on both sides for comparison tolerance
        while actual_seq and actual_seq[-1][1]:
            actual_seq.pop()
        while expected_seq and expected_seq[-1][1]:
            expected_seq.pop()

        if actual_seq != expected_seq:
            actual_repr = [k if k else "(blank)" for k, _ in actual_seq]
            expected_repr = [k if k else "(blank)" for k, _ in expected_seq]
            violations.append(
                f"{path} [{sec}] (rule: §13.7 local-vs-third)\n"
                f"  actual:   {actual_repr}\n"
                f"  expected: {expected_repr}"
            )
        return violations


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    if not root.is_dir():
        print(f"error: {root} is not a directory", file=__import__("sys").stderr)
        return 2

    files = find_cargo_tomls(root)
    if not files:
        print(f"No Cargo.toml files found under {root}", file=__import__("sys").stderr)
        return 2

    # Local crate names are workspace-wide. Find the workspace root
    # (the Cargo.toml that contains [workspace]) and use its member set.
    workspace_root = None
    for f in files:
        text = f.read_text()
        if re.search(r"^\[workspace\]", text, re.M):
            workspace_root = f
            break
    if workspace_root is None:
        # No workspace — assume each crate is its own root
        local_set_global: set[str] = set()
    else:
        local_set_global = read_local_crate_names(workspace_root)

    total_violations = 0
    for f in files:
        # Sub-crates may also be standalone (publish = false). Use the
        # workspace-wide local set so e.g. example's [dependencies] sees
        # euv / euv-engine / euv-ui as local.
        local_set_for_file = read_local_crate_names(f) | local_set_global
        for v in check_file_v2(f, local_set_for_file):
            print(v)
            total_violations += 1

    print(f"\n{len(files)} files checked, {total_violations} violations")
    return 0 if total_violations == 0 else 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
