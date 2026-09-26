#!/usr/bin/env python3
"""
Verify §13.7 dependency-block ordering for any Rust workspace.

§13.7 rule (round 4, 2026-09-26):
  - [dependencies], [dev-dependencies], [build-dependencies],
    [workspace.dependencies]:
      LOCAL first, single blank line at boundary, then THIRD-PARTY.
      Within each group, sort by (entry full length, key lex).
      Entry full length = len(re.sub(r"\\s+", "", "<entry-joined>"))
      where entry-joined strips every line and concatenates them
      (whitespace-agnostic so formatter preferences don't shift order).
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

Round history (in §13.7 reference):
  - Round 1 (2026-09-14): (key length, lex).
  - Round 2 (2026-09-14): (key length, lex) for blocks; alphabetic
    for workspace.dependencies; no blank-line grouping.
  - Round 3 (2026-09-14): blank-line separator only at the
    local/third-party boundary; alphabetic inside each group.
  - Round 4 (current, 2026-09-26): user explicitly required
    "完整的长度(含特性等字段)升序,一样的长度按照字典序升序"
    (full entry length ascending, ties broken by lex). Blanks at
    group boundary preserved.
"""
import re
import subprocess
from pathlib import Path


KEY_PATTERN = re.compile(r"^([a-zA-Z0-9_-]+)\s*=")


def find_cargo_tomls(root: Path) -> list[Path]:
    # Note: -not -path '*/tmp/*' was historically used to skip build
    # artifacts, but it also excludes /tmp fixture roots during testing.
    # Drop it; the cargo registry filter below already handles real
    # artifact noise.
    #
    # Two extra filters exist for the cc / hyperlane-cli / crate-cli
    # test-helper convention: each binary crate lays out its integration
    # tests under `<crate>/tmp/test_<scenario>/`, and each synthesised
    # Cargo.toml is deliberately mis-ordered — its job is to assert
    # that `cc sync` / `cc bump` do NOT destroy comments, format, or
    # blank lines, so they MUST stay mis-ordered in the fixture. Those
    # fixtures are not part of the production workspace and must not be
    # touched by `--fix` mode either (see fix_dep_order.py).
    r = subprocess.run(
        [
            "find", str(root), "-name", "Cargo.toml",
            "-not", "-path", "*/target/*",
            "-not", "-path", "*/tmp/test_*",
        ],
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
    # member entries may be paths ("crates/foo") or globs ("crates/*"), not
    # bare names — capture the full quoted string and resolve relative dirs.
    m = re.search(r"members\s*=\s*\[(.*?)\]", text, re.S)
    if m:
        for d in re.findall(r'"([^"]+)"', m.group(1)):
            if any(c in d for c in "*?["):
                candidates = sorted(path.parent.glob(d))
            else:
                candidates = [path.parent / d]
            for cand in candidates:
                sub = cand / "Cargo.toml"
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


def _entry_chars(raw_lines):
    """§13.7 round-4 entry length: strip every line, concatenate,
    remove whitespace, return len. Whitespace-agnostic."""
    joined = " ".join(line.strip() for line in raw_lines if line.strip())
    return len(re.sub(r"\s+", "", joined))


def expected_order_with_blank(entries, local_set):
    """Round 4 sort key: (entry full length, key lex). Group split
    preserved from round 3 — local first, then a single boundary
    blank, then third-party."""
    local = sorted(
        [(k, l) for k, l in entries if k in local_set],
        key=lambda kv: (_entry_chars(kv[1]), kv[0]),
    )
    third = sorted(
        [(k, l) for k, l in entries if k not in local_set],
        key=lambda kv: (_entry_chars(kv[1]), kv[0]),
    )
    if local and third:
        return local + [("", [""])] + third
    return local + third


def check_file_v2(path: Path, local_set: set[str]) -> list[str]:
    """Round 4 (2026-09-26):
      * inner order — local vs third-party groups, each sorted by
        entry full length + lex; one boundary blank between groups.
      * cross-section blank — exactly 1 blank line between any dep
        block's last entry and the next non-dep `[section]` (e.g.
        `[patch.crates-io]`, `[profile.dev]`, `[lib]`, `[[bin]]`).
      * EOF blank — TOML files must end with exactly 1 blank line
        (trailing 2 `\\n`: last entry newline + one separator
        newline). Same visual rhythm as cross-section blank, but
        applied at file boundary.
    """
    text = path.read_text()
    violations = []
    sections = [
        "dependencies",
        "dev-dependencies",
        "build-dependencies",
        "workspace.dependencies",
    ]
    for sec in sections:
        # One match per dep section: anchored on `^` so we ignore
        # `key = "[dependencies]"` style string content.
        m = re.search(rf"^\[\s*{re.escape(sec)}\s*\]\s*\n", text, re.M)
        if not m:
            continue
        # Find end of the dep block — up to (but not including) the
        # next `[<section>]` header line, or EOF.
        rest = text[m.end():]
        next_m = re.search(r"^\[\S+\]", rest, re.M)
        block_end = m.end() + (next_m.start() if next_m else len(rest))
        block_text = text[m.start():block_end]

        lines = block_text.splitlines()
        items: list[dict] = []
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

        # ---- Inner ordering rule: local vs third-party ----
        # Build actual sequence (with blank markers)
        actual_seq: list[tuple[str, bool]] = []
        for it in items:
            actual_seq.append((it["key"], False))
            if it["followed_by_blank"]:
                actual_seq.append(("", True))

        # Build expected sequence (round 4: sort by entry length + lex)
        local = sorted(
            [it for it in items if it["key"] in local_set],
            key=lambda x: (_entry_chars(x["lines"]), x["key"]),
        )
        third = sorted(
            [it for it in items if it["key"] not in local_set],
            key=lambda x: (_entry_chars(x["lines"]), x["key"]),
        )
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
                f"{path} [{sec}] (rule: §13.7 round 4 local/length/lex)\n"
                f"  actual:   {actual_repr}\n"
                f"  expected: {expected_repr}"
            )

        # ---- Cross-section rule: dep block ends → next section ----
        # The dep block's last byte in `text` is `block_end - 1`. The
        # NEXT char `text[block_end]` is the start of the next
        # `[section]` header (or EOF).
        #   * If `block_end == len(text)` — dep block is the file's
        #     last content → cross-section check skipped here; the
        #     file-level EOF rule below still applies.
        #   * Otherwise: count consecutive `\n` immediately before the
        #     next header. After `text[block_end-1] == "\n"` (block's
        #     own trailing newline), we expect one MORE `\n` for a
        #     single blank line → 2 leading `\n`. Anything else is
        #     wrong: 1 means zero blank lines, 3+ means extra blanks.
        if block_end < len(text):
            j = block_end - 1
            blanks = 0
            while j >= 0 and text[j] == "\n":
                blanks += 1
                j -= 1
            gap = blanks - 1  # subtract the dep block's own trailing `\n`
            if gap != 1:
                violations.append(
                    f"{path} [{sec}] (rule: §13.7 round 4 cross-section blank)\n"
                    f"  gap between this dep block and the next `[section]` "
                    f"is {gap} blank line(s); must be exactly 1"
                )

    # ---- File-level EOF rule (§13.7.2b): TOML files end with the
    # last entry's newline ONLY — trailing exactly 1 `\n`. Round 4
    # correction (2026-09-26): the previous "trailing 2 `\n` = 1 blank
    # line" rule was rejected by user ("末尾都是两个空行,只需要一个").
    # The single trailing `\n` matches `cargo new` / `rustfmt` /
    # standard Unix file convention. Compute *after* the dep-loop so
    # violations get a single file-level entry, not one per dep
    # section.
    trailing = 0
    if text:
        j = len(text) - 1
        while j >= 0 and text[j] == "\n":
            trailing += 1
            j -= 1
    if trailing != 1 and text:
        # NOTE: empty `text` (len == 0) is treated as PASS — a 0-byte
        # file has no trailing newline and arguably nothing to "end",
        # unlike a 0-trailing-newline non-empty file which is missing
        # the last entry's terminator (POSIX violation).
        violations.append(
            f"{path} (rule: §13.7 round 4 EOF trailing)\n"
            f"  file ends with {trailing} trailing `\\n`; must be exactly "
            f"1 (standard Unix line-terminator style)"
        )

    # ---- Mid-file 3+ blank lines (§13.7.2c): anywhere in the file
    # (outside a dep block — inside is handled by inner-order/cross-
    # section/EOF rules), 3+ consecutive `\n` characters denote 2+
    # blank lines, violating the single rhythm. Detect by a single
    # regex scan, attach line numbers so the user can jump to them
    # in their editor. Catches `key = "x"\n\n\n\n[next_section]`
    # between non-dep sections (e.g. `[profile.dev]` → `[profile.
    # release]`) which §13.7.2a doesn't audit.
    for m in re.finditer(r"\n\n\n+", text):
        newlines_in_match = m.group(0).count("\n")
        # m.start() offset in text → 1-indexed line of the FIRST `\n`
        # in the run.
        line_no = text[:m.start()].count("\n") + 1
        violations.append(
            f"{path}:{line_no} (rule: §13.7 round 4 multi-blank-run)\n"
            f"  {newlines_in_match} consecutive `\\n` → {newlines_in_match - 1} "
            f"blank line(s) here; must collapse to exactly 1 blank line"
        )

    return violations


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    if not root.is_dir():
        print(f"error: {root} is not a directory", file=__import__("sys").stderr)
        return 2

    files = find_cargo_tomls(root)
    if not files:
        # No Cargo.toml = nothing to verify, treat as a pass (exit 0)
        # so audit wrappers don't flag this as a violation.  Print a
        # status line so audit can filter it out if needed.
        print(f"OK: 0 Cargo.toml files (R13.7 not applicable)")
        return 0

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
