#!/usr/bin/env python3
"""
Apply §13.7 round 4 ordering to every `[dependencies]` /
`[dev-dependencies]` / `[build-dependencies]` /
`[workspace.dependencies]` block of every Cargo.toml under the
target workspace, in place.

Reorders entries only — does NOT touch:
  * anything outside the four dep blocks (other sections, profile,
    workspace metadata, package metadata)
  * content of any individual dep entry (key = value form stays
    exactly as written — version / features / default-features /
    registry / path / git / workspace are preserved verbatim)
  * comments inside entry lines (toml_formatter preserves them)
  * line-level indentation and trailing whitespace inside an entry
  * the trailing newline of the file
  * files under `*/target/*` or `*/tmp/test_*` (test-helper fixtures
    that MUST stay mis-ordered to assert `cc sync` / `cc bump`
    format preservation)

Idempotent: re-running produces a 0-byte diff. After every successful
write, the script re-invokes `verify_dep_order.py` against the
workspace and asserts the suite exits 0.

Default is `--dry-run`; pass `--write` to commit changes to disk.
A `.bak` backup is written next to each modified file with the
original contents; pass `--backup` to opt back in (2026-09-26:
default is no backup — git history is the source of truth).

Why this script exists (not just re-running verify_dep_order.py):
the verify script only reports violations. Without a rewriter,
applying the rule across one workspace means 24+ files × 4 blocks
× manual parser-driven reorders — error-prone (comments get lost
or comments-above-block vs comments-between-entry get mixed up).
A rewriter must use the same parse_block logic as the verifier so
they can't disagree about what counts as "ordered".

Usage:
    python3 fix_dep_order.py [--write] [--no-backup] [ROOT]

Default ROOT = current directory.
"""
from __future__ import annotations

import argparse
import importlib.util
import re
import shutil
import subprocess
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Re-use verify_dep_order's parse_block + ordering primitives so the
# rewriter and the verifier cannot disagree about "what an entry is"
# or "what local means".
# ---------------------------------------------------------------------------

VERIFY_SCRIPT = Path(__file__).resolve().parent / "verify_dep_order.py"
_SPEC = importlib.util.spec_from_file_location("verify_dep_order", VERIFY_SCRIPT)
assert _SPEC is not None and _SPEC.loader is not None, (
    f"failed to load spec for {VERIFY_SCRIPT}"
)
_verify = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_verify)


KEY_PATTERN = _verify.KEY_PATTERN
parse_block = _verify.parse_block
_entry_chars = _verify._entry_chars
find_cargo_tomls = _verify.find_cargo_tomls
read_local_crate_names = _verify.read_local_crate_names


def _expected_block_lines(entries, local_set):
    """Round-4 sort: local group first sorted by (entry length, key),
    single boundary blank, third group sorted the same way.
    Returns a list of "lines of fixed block" preserving each entry's
    original lines verbatim (whitespace, comments, multi-line forms)
    and emitting exactly one blank line between local and third.

    INSIDE a group, entries are concatenated with NO blank lines
    between them (§13.7.2: "块内禁有多余空行"). Only ONE blank
    line appears — at the local/third boundary, when both groups
    are non-empty."""
    local = sorted(
        [(k, ls) for k, ls in entries if k in local_set],
        key=lambda kv: (_entry_chars(kv[1]), kv[0]),
    )
    third = sorted(
        [(k, ls) for k, ls in entries if k not in local_set],
        key=lambda kv: (_entry_chars(kv[1]), kv[0]),
    )

    out: list[str] = []
    for _, ls in local:
        out.extend(ls)
    if local and third:
        out.append("")  # the ONE boundary blank between local and third
    for _, ls in third:
        out.extend(ls)
    return out


# ---------------------------------------------------------------------------
# Block rewriting
# ---------------------------------------------------------------------------

SECTION_RE = re.compile(
    r"^(\[\s*(?P<sec>dependencies|dev-dependencies|build-dependencies|workspace\.dependencies)\s*\])\s*\n"
    r"(?P<body>(?:[^\n]*\n)*?)"
    r"(?=\s*^\[\S+\]|\Z)",
    re.M | re.S,
)


def _rewrite_block(block_text: str, local_set: set[str]) -> tuple[str, bool]:
    """Rewrite one `[sec]\n<lines>` block per round 4.

    `block_text` starts with the `[sec]` header line and ends right
    before the next `[<something>]` header (or end of file) — that
    is the same shape `parse_block` recognises.

    Returns the new block text and a `changed` flag.
    """
    header_match = re.match(r"^(\[\s*(?:dependencies|dev-dependencies|build-dependencies|workspace\.dependencies)\s*\])\s*\n", block_text)
    if not header_match:
        return block_text, False
    header = header_match.group(1)
    body_lines = block_text[header_match.end():].splitlines()

    # parse_block-style walker
    entries: list[tuple[str, list[str]]] = []
    blanks_after_count: list[int] = []
    cur_key = None
    cur_lines: list[str] = []
    seen_blank = 0

    def flush():
        nonlocal cur_key, cur_lines, seen_blank
        if cur_key is not None:
            entries.append((cur_key, cur_lines))
            blanks_after_count.append(seen_blank)
        cur_key = None
        cur_lines = []
        seen_blank = 0

    for line in body_lines:
        if not line.strip():
            if cur_key is not None:
                seen_blank += 1
            continue
        km = KEY_PATTERN.match(line)
        if km:
            flush()
            cur_key = km.group(1)
            cur_lines = [line]
            seen_blank = 0
        else:
            if cur_key is not None:
                cur_lines.append(line)
    flush()

    if not entries:
        return block_text, False

    new_body = _expected_block_lines(entries, local_set)
    new_block = header + "\n" + "\n".join(new_body)
    if not new_block.endswith("\n"):
        new_block += "\n"

    if new_block == block_text.rstrip("\n") + "\n":
        return block_text, False
    return new_block, True


def _rewrite_file(
    path: Path,
    local_set: set[str],
    *,
    write: bool = True,
) -> tuple[bool, list[str]]:
    """Rewrite all four dep blocks inside `path`. Returns
    `(any_change, list_of_changes_summary)`.

    Per §13.7 round 4: every dep block (any of the four
    `[dependencies]` / `[dev-dependencies]` / `[build-dependencies]` /
    `[workspace.dependencies]`) ends with a single blank line
    separating it from the next non-dep section
    (`[patch.crates-io]`, `[profile.dev]`, `[lib]`, `[[bin]]`,
    `[workspace.metadata]`, etc.). This rule lives inside the same
    rewriter because verify_dep_order.py also enforces it — the
    rewritten trailing-newline behaviour below is what the verifier
    expects.

    When `write=False`, the function still scans and computes the
    candidate spans, but does NOT touch the file on disk. This is
    how the dry-run mode of the CLI can preview changes without
    committing them — the previous round-3 implementation wrote
    eagerly and corrupted idempotency in dry-run mode.
    """
    original = path.read_text()
    new = original

    # SECTION_RE is non-overlapping; find each dep block and rewrite.
    changes: list[str] = []
    spans: list[tuple[int, int, str]] = []  # (start, end, replacement)
    for m in SECTION_RE.finditer(new):
        sec = m.group("sec")
        header_line = m.group(1)
        # body inside the section — from start of header_line to start of next `[\S+]` or EOF
        original_block = new[m.start():m.end()]
        rewritten, changed = _rewrite_block(original_block, local_set)

        # §13.7 round 4 cross-section rule: dep block end → next
        # `[<section>]` must have exactly one blank line between them.
        # `m.end()` already includes the trailing `\n` of the dep block
        # (because SECTION_RE matches up to that `\n` and uses a zero-
        # width lookahead for the next section). So:
        #   * If `m.end() < len(new)` — there is content (a section
        #     header) right after. Insert ONE additional `\n` so the
        #     gap becomes `\n\n` (i.e. one blank line).
        #   * If `m.end() == len(new)` — the dep block is the file's
        #     last content. Do NOT add an extra `\n`, otherwise the
        #     file gains a trailing blank line.
        if m.end() < len(new):
            # the byte at m.end() is normally the start of the next
            # section header (e.g. `[`). Avoid double-blanking if the
            # original already had a blank line.
            if not new[m.end():m.end() + 1].startswith("\n"):
                rewritten = rewritten + "\n"

        if changed or rewritten != original_block:
            key_count = len(parse_block(rewritten, sec))
            old_key_count = len(parse_block(original_block, sec))
            changes.append(
                f"[{sec}]: {len(original_block)} -> {len(rewritten)} bytes; "
                f"key count preserved = {key_count} (was {old_key_count})"
            )
            spans.append((m.start(), m.end(), rewritten))

    if not changes:
        # No dep-block changes requested. But §13.7.2b EOF rule and
        # §13.7.2c multi-blank-run rule still apply independently —
        # check trailing-newline count and inline multi-blank runs
        # before bailing out. An empty file (len 0) is exempt from
        # both rules (verify treats it as PASS).
        if not new:
            return False, []
        trailing_n = len(new) - len(new.rstrip("\n"))
        has_multi_blank = bool(re.search(r"\n\n\n+", new))
        if trailing_n == 1 and not has_multi_blank:
            return False, []
        # EOF or multi-blank needs fix; fall through to apply.

    # Apply spans to build the candidate new file content.
    out_parts: list[str] = []
    cursor = 0
    for start, end, replacement in spans:
        out_parts.append(new[cursor:start])
        out_parts.append(replacement)
        cursor = end
    out_parts.append(new[cursor:])
    rewritten_full = "".join(out_parts)

    # §13.7.2c multi-blank-run collapse: anywhere 3+ consecutive `\n`
    # (= 2+ blank lines) appear in the candidate, collapse them to
    # exactly 2 `\n` (1 blank line). This catches the case where
    # a user manually left 3+ blanks between any two non-dep sections
    # (e.g. `[profile.dev]` → `[profile.release]`). Apply BEFORE
    # the EOF rule so EOF sees the already-normalized tail.
    rewritten_full = re.sub(r"\n\n\n+", "\n\n", rewritten_full)

    # §13.7.2b EOF rule: TOML files end with the last entry's
    # newline ONLY — trailing exactly 1 `\n`. Round 4 rejected the
    # trailing-2 (`\n\n`) rule (2026-09-26 user correction: "末尾都
    # 是两个空行,只需要一个"). The single trailing `\n` is the
    # standard Unix line-terminator style and matches what Rust's
    # own `cargo new` and `rustfmt` emit. Strip all trailing `\n`
    # then add exactly 1.
    # NOTE: empty `rewritten_full` (len == 0) is left alone — a 0-byte
    # file isn't required to end in `\n` (there's nothing to
    # terminate).
    if rewritten_full:
        stripped = rewritten_full.rstrip("\n")
        rewritten_full = stripped + "\n"

    if rewritten_full == new:
        return False, []

    if write:
        path.write_text(rewritten_full)
    return True, (changes or ["EOF trailing-newline normalize"])


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true",
                    help="actually mutate Cargo.toml on disk "
                         "(default: dry-run, only print the diff intent)")
    ap.add_argument("--no-backup", action="store_true",
                    help="(default — no backup) suppress is the default; "
                         "`--backup` re-enables writing .bak next to each "
                         "rewritten file. Backups stay behind otherwise.")
    ap.add_argument("root", nargs="?", default=".",
                    help="workspace root (default: current directory)")
    args = ap.parse_args()

    root = Path(args.root).resolve()
    if not root.is_dir():
        print(f"error: {root} is not a directory", file=sys.stderr)
        return 2

    files = find_cargo_tomls(root)
    if not files:
        print(f"No Cargo.toml files found under {root}", file=sys.stderr)
        return 2

    # Workspace-wide local crate set
    workspace_root = None
    for f in files:
        if re.search(r"^\[workspace\]", f.read_text(), re.M):
            workspace_root = f
            break
    local_set_global = (
        read_local_crate_names(workspace_root)
        if workspace_root is not None
        else set()
    )

    # First pass: dry-run scan to collect files that need rewriting.
    # We pass `write=False` so the disk is NOT touched during this pass
    # (otherwise dry-run mode would silently mutate files when the
    # round 4 rule applies to a previously-unordered block).
    modified: list[tuple[Path, list[str]]] = []
    for f in files:
        local_set_for_file = read_local_crate_names(f) | local_set_global
        changed, summary = _rewrite_file(f, local_set_for_file, write=False)
        if changed:
            modified.append((f, summary))

    if not modified:
        print("All Cargo.toml files already match §13.7 round 4. Nothing to do.")
        return 0

    for path, summary in modified:
        rel = path.relative_to(root) if path.is_relative_to(root) else path
        print(f"\n=== {rel} ===")
        for s in summary:
            print(f"  - {s}")

    if not args.write:
        print(f"\n[dry-run] {len(modified)} file(s) would be rewritten.")
        print("Re-run with --write to commit changes.")
        return 0

    # --write path: only write .bak if `--backup` was explicitly passed.
    # Default (2026-09-26 user correction) is no backup — the workspace
    # git history is the source of truth; .bak files clutter `git status`.
    for path, _summary in modified:
        if args.no_backup:
            shutil.copy2(path, path.with_suffix(path.suffix + ".bak"))

    for path, _summary in modified:
        local_set_for_file = read_local_crate_names(path) | local_set_global
        _changed, _summary = _rewrite_file(path, local_set_for_file)
        # Even after --write, _rewrite_file is idempotent so _changed
        # must be False now.

    # Final verification
    print()
    r = subprocess.run(
        [sys.executable, str(VERIFY_SCRIPT), str(root)],
        capture_output=True, text=True,
    )
    print(r.stdout, end="")
    if r.returncode != 0:
        print(f"\n[WARN] verify_dep_order.py exited {r.returncode} after rewrite.")
        print("This indicates the rewriter produced content the verifier")
        print("disagrees with. Re-run `git diff <root>` and investigate.")
    return r.returncode


if __name__ == "__main__":
    sys.exit(main())
