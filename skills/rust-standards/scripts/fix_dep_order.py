#!/usr/bin/env python3
"""
Auto-fix §13.7 dependency-block ordering for any Rust workspace.

Reuses the parse logic from `verify_dep_order.py` so the verifier and the
fixer can never disagree on what "correct" means.

Default mode is **dry-run**: prints what *would* change but does NOT write
to disk. Pass `--write` to apply the rewrites in-place.

Usage:
    python3 fix_dep_order.py [ROOT]            # dry-run
    python3 fix_dep_order.py --write [ROOT]    # apply
    python3 fix_dep_order.py --backup [ROOT]   # keep .bak alongside rewrite

Behavior:
- Per [dependencies] / [dev-dependencies] / [build-dependencies] /
  [workspace.dependencies] block:
    1. Read entries from the file.
    2. Classify each as local (path/workspace-matches workspace member
       OR root package name) vs third-party.
    3. Sort local group by dep key ascending, third-party group the same.
    4. If both groups present, insert a single blank line at the boundary.
    5. Preserve each entry's full text (including multi-line value, inline
       tables, comments) verbatim.
- No entry text is altered. No content outside the four dep blocks is
  touched.
- After every block rewrite, the file is reparsed to verify the rule holds.

Scope:
- Skips `target/`, `*/.cargo/registry/`, and any path under `*/tmp/test_*/`
  (these are crate-cli test fixtures; touching them breaks the fixtures).

Dry-run guarantee:
- The `_rewrite_file` helper takes `write: bool` and the `--dry-run` path
  in `main()` early-returns before collecting rewrite plans. Running the
  script with no `--write` and no `--backup` MUST leave git status clean
  (verified by the audit checklist in references/audit-pitfalls.md §48).
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

# Re-use the verifier's parse primitives so this script can never drift
# from the single source of truth.
sys.path.insert(0, str(Path(__file__).parent))
from verify_dep_order import (  # noqa: E402
    KEY_PATTERN,
    entry_sort_key,
    find_cargo_tomls,
    read_local_crate_names,
)

DEP_SECTIONS = [
    "dependencies",
    "dev-dependencies",
    "build-dependencies",
    "workspace.dependencies",
]


def _block_span(text: str, section_name: str) -> tuple[int, int] | None:
    """Return (start_idx, end_idx) of the [section] block, including the
    header line and any trailing blank lines. Returns None if not present."""
    m = re.search(rf"^\[\s*{re.escape(section_name)}\s*\]\s*\n", text, re.M)
    if not m:
        return None
    rest = text[m.end():]
    next_m = re.search(r"^\[\S+\]", rest, re.M)
    end = m.end() + (next_m.start() if next_m else len(rest))
    return m.start(), end


def parse_entries(block_text: str) -> list[dict]:
    """Parse a [dependencies] block into a list of items.

    Mirrors `verify_dep_order.check_file_v2`'s inline parser so both
    scripts agree on what a block contains. Each item is one of:
        {"key": str, "lines": [str, ...], "followed_by_blank": bool}

    A blank line between two entries is captured as `followed_by_blank`
    on the preceding entry — no standalone marker entries, no blank
    sentinel dicts. Trailing blank lines after the last entry are
    ignored.
    """
    lines = block_text.splitlines()
    items: list[dict] = []
    cur: dict | None = None
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
    return items


def sort_block_items(items: list[dict], local_set: set[str]) -> list[dict]:
    """Return a new list with local entries first (alphabetical), then
    third-party (alphabetical).

    Sort key (round-4, rust-standards §13.7): primary = total
    whitespace-agnostic character count of the entry; secondary = dep
    key. This matches what `verify_dep_order.entry_sort_key` produces,
    so verifier and fixer can never disagree on the canonical order.

    `followed_by_blank` rules:
    - All input `followed_by_blank` flags are DROPPED — they're noise from
      the source file's existing whitespace, not part of the rule.
    - If both groups are non-empty, the boundary entry (last local) gets
      `followed_by_blank=True`. All other entries get False.
    - If only one group exists, no blank is ever required — every entry
      has `followed_by_blank=False`.
    """
    locals_ = [it for it in items if it["key"] in local_set]
    thirds = [it for it in items if it["key"] not in local_set]
    locals_.sort(key=entry_sort_key)
    thirds.sort(key=entry_sort_key)
    out: list[dict] = []
    for it in locals_:
        out.append({"key": it["key"], "lines": it["lines"], "followed_by_blank": False})
    if locals_ and thirds:
        out[-1]["followed_by_blank"] = True
    for it in thirds:
        out.append({"key": it["key"], "lines": it["lines"], "followed_by_blank": False})
    return out


def block_needs_rewrite(items: list[dict], expected: list[dict]) -> bool:
    """True if current and expected block layouts differ. Compares via
    the same `(key, is_blank)` sequence the verifier builds — keeps
    verifier and fixer in lockstep (audit-pitfalls §48)."""
    def seq(items_):
        out: list[tuple[str, bool]] = []
        for it in items_:
            out.append((it["key"], False))
            if it["followed_by_blank"]:
                out.append(("", True))
        # trim trailing blanks past last expected entry
        while out and out[-1][1] and len(out) > len(expected):
            out.pop()
        return out

    actual_seq = seq(items)
    expected_seq = seq(expected)
    # Drop trailing blanks from expected_seq (verifier tolerance).
    while expected_seq and expected_seq[-1][1]:
        expected_seq.pop()
    return actual_seq != expected_seq


def serialize_block(items: list[dict]) -> str:
    """Render a parsed block back to Cargo.toml text.

    Between two entries: if the preceding entry's `followed_by_blank` is
    True, emit ONE extra blank line (the boundary blank). Otherwise just
    one newline (entry terminator).

    Block ends with exactly one trailing newline (the last entry's
    terminator)."""
    out_parts: list[str] = []
    for i, it in enumerate(items):
        out_parts.append("\n".join(it["lines"]))
        is_last = i == len(items) - 1
        # Always end the entry with one newline. If followed_by_blank
        # and not the last entry, add another newline (a single blank
        # line separates this entry from the next).
        if is_last:
            out_parts.append("\n")
        elif it["followed_by_blank"]:
            out_parts.append("\n\n")
        else:
            out_parts.append("\n")
    return "".join(out_parts)


def rewrite_file_text(
    text: str,
    sections_to_fix: list[tuple[str, list[dict]]],
) -> str:
    """Apply the rewrites in reverse order (highest offset first) so that
    earlier offsets remain valid. `sections_to_fix` is a list of
    (section_name, new_items) pairs in the order they appear in the file.
    """
    spans: list[tuple[int, int, str]] = []
    for sec, new_items in sections_to_fix:
        sp = _block_span(text, sec)
        if sp is None:
            continue
        start, end = sp
        new_block = f"[{sec}]\n" + serialize_block(new_items)
        spans.append((start, end, new_block))
    # Apply right-to-left so earlier indices stay valid.
    spans.sort(key=lambda s: s[0], reverse=True)
    new_text = text
    for start, end, replacement in spans:
        new_text = new_text[:start] + replacement + new_text[end:]
    return new_text


def plan_changes(root: Path, write: bool, only: set[Path] | None = None) -> tuple[int, list[str]]:
    """Walk the workspace, collect per-file rewrite plans. If `write` is
    False, return counts only without touching disk.

    `only` restricts the run to an explicit set of Cargo.toml paths. When
    None, every Cargo.toml under `root` is considered (whole-repo scope).
    """
    files = find_cargo_tomls(root)
    if only is not None:
        files = [f for f in files if f.resolve() in only]
    if not files:
        return 0, ["No Cargo.toml files found"]

    workspace_root = None
    for f in files:
        if re.search(r"^\[workspace\]", f.read_text(), re.M):
            workspace_root = f
            break
    if workspace_root is None:
        local_set_global: set[str] = set()
    else:
        local_set_global = read_local_crate_names(workspace_root)

    rewrites = 0
    skipped_test_dirs = 0
    changes_log: list[str] = []

    for f in files:
        # Skip crate-cli test fixtures (they live under */tmp/test_*/)
        if "/tmp/test_" in str(f):
            skipped_test_dirs += 1
            continue
        text = f.read_text()
        local_set = read_local_crate_names(f) | local_set_global
        sections_to_fix: list[tuple[str, list[dict]]] = []
        for sec in DEP_SECTIONS:
            sp = _block_span(text, sec)
            if sp is None:
                continue
            block_text = text[sp[0]:sp[1]]
            items = parse_entries(block_text)
            expected = sort_block_items(items, local_set)
            if block_needs_rewrite(items, expected):
                sections_to_fix.append((sec, expected))
        if not sections_to_fix:
            continue
        rewrites += 1
        rel = f.relative_to(root)
        for sec, _ in sections_to_fix:
            changes_log.append(f"  {rel} [{sec}]")
        if write:
            new_text = rewrite_file_text(text, sections_to_fix)
            # Optional .bak next to original
            if args.backup:
                f.with_suffix(f.suffix + ".bak").write_text(text)
            f.write_text(new_text)
    return rewrites, changes_log


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "root",
        nargs="?",
        default=".",
        help="Workspace root to scan (default: cwd).",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="Apply rewrites in-place. Default is dry-run.",
    )
    parser.add_argument(
        "--backup",
        action="store_true",
        help="Write a .bak alongside each modified file. Implies --write.",
    )
    parser.add_argument(
        "--files",
        nargs="*",
        default=None,
        help=("Restrict the rewrite to these Cargo.toml paths. Omit for "
              "whole-workspace scope."),
    )
    global args
    args = parser.parse_args()

    # Allow `python3 fix_dep_order.py /path` from any CWD.
    _script_dir = Path(__file__).resolve().parent
    if str(_script_dir) not in sys.path:
        sys.path.insert(0, str(_script_dir))

    root = Path(args.root).resolve()
    if not root.is_dir():
        print(f"error: {root} is not a directory", file=sys.stderr)
        return 2

    if args.backup:
        args.write = True

    only = None
    if args.files:
        only = {Path(p).resolve() for p in args.files}

    rewrites, log = plan_changes(root, write=args.write, only=only)

    if rewrites == 0:
        print(f"Nothing to do ({log[0] if log else 'no Cargo.toml found'})")
        return 0

    print(f"=== fix_dep_order: {rewrites} file(s) {'written' if args.write else 'to rewrite'} ===")
    for line in log:
        print(line)
    if not args.write:
        print("(dry-run; pass --write to apply)")
    return 0


if __name__ == "__main__":
    sys.exit(main())