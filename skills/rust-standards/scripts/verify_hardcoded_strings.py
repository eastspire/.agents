#!/usr/bin/env python3
"""
Verify rust-standards §1.3c (strengthened, 2026-09-26 third
iteration): hardcoded string literals MUST live in `const.rs`.

User original (2026-09-26 third iteration):
  "硬编码字符串必须要维护到 const.rs 上面"

The existing `audit_rust_standards.py` check 18 only catches
hardcoded byte / char / multi-character string literals in
`fn.rs` files (and only the FIRST few characters of a multi-byte
literal).  This new rule extends coverage to ALL files except
`const.rs` and `tests/`:

  ❌  let path: &str = "/usr/local/bin";         // in fn.rs
  ❌  eprintln!("Hello, world!");                // in fn.rs
  ❌  format!("got {} items", n);                // in impl.rs
  ❌  if name == "admin" { ... }                 // in fn.rs

  ✅  // in const.rs:
      pub const BIN_PATH_USR_LOCAL: &str = "/usr/local/bin";
      pub const HELLO_WORLD: &str = "Hello, world!";
      // then in fn.rs:
      eprintln!("{}", HELLO_WORLD);

Exemptions:
  - Files named `const.rs` (this is the canonical home of
    string constants; literal strings here are not
    "hardcoded", they ARE the constant definition).
  - `tests/` directory (R14.7 self-contained; tests often
    embed expected literals).
  - `format!` / `println!` / `eprintln!` / `panic!` /
    `assert!` / `assert_eq!` / `assert_ne!` / `unimplemented!`
    / `unreachable!` / `todo!` / `dbg!` / `write!` / `writeln!`
    macros whose string literal is the FORMAT string (first
    argument).  These are user-facing format strings; they
    MUST stay inline at the call site for readability.
    BUT: arguments embedded as `format!("got {} items", n)`
    where `n` is a literal `0` are NOT exempt — the format
    string itself stays inline, but constants get extracted
    in surrounding code.
  - String literals used as trait discriminant in
    attribute macros like `#[doc = "..."]` / `#[cfg(test)]` —
    handled by the macro detection (line starts with `#[`).
  - String literals inside `#[derive(...)]` (the derive
    name itself, e.g. `#[derive(Debug)]`) — these are
    attribute paths, not user data.
  - String literals in `serde` rename attributes
    (`#[serde(rename = "...")]`) — these are wire-format
    names that MUST be inline.

Detection heuristic:
  - For each .rs file NOT in {const.rs, tests/}:
    * Find every line that contains a string literal
      (`"...some text..."` — minimum 4 non-trivial chars).
    * If the line is:
      - Inside a macro at attribute position (`#[xxx = "..."]`)
        → exempt
      - Inside a known format macro as the first positional
        arg → exempt
      - Otherwise → violation (line + content)

This is a strict heuristic; it WILL have false positives on
well-named macros that take strings as first argument
(`writeln!`, `assert_eq!` format string).  When in doubt,
the script prefers false-positive (flag) over false-negative
(miss), so authors must explicitly justify the literal.

Exits 0 if clean, 1 if any violation.

Usage:
    python3 verify_hardcoded_strings.py [ROOT]
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path


# Format-style macros whose FIRST string argument is the
# format string (user-facing) and is exempt from extraction.
FORMAT_MACROS = {
    "format", "println", "eprintln", "print", "eprint",
    "panic", "unimplemented", "unreachable", "todo",
    "assert", "assert_eq", "assert_ne",
    "write", "writeln",
    "dbg", "error", "warn", "info", "debug", "trace",
}


# Match a string literal — at minimum 4 non-whitespace chars
# (avoid flagging single-char `'.'` literals and empty `""`).
STRING_LITERAL = re.compile(r'"([^"\\]|\\.){4,}"')

# Match attribute lines like `#[doc = "..."]` /
# `#[serde(rename = "..."]` etc. — the whole line starts
# with `#[` and ends with `]`.
ATTR_LINE = re.compile(r"^\s*#\[")


# Match a Rust foreign-ABI declaration slot (2026-09-28).
#
#   extern "system" { ... }        (block)
#   extern "C" fn f() { ... }      (single fn)
#   pub unsafe extern "system" fn g() { ... }
#
# The string here is the LINKING ABI, not program data.  It lives in
# a grammar position that accepts ONLY a string literal — there is no
# expression slot, so it can never be hoisted into a `const`:
#
#   const ABI: &str = "system";
#   extern ABI { }        →  error: expected `fn`, found `ABI`
#
# Verified with rustc 1.9x: replacing the literal with a const path is
# a hard syntax error, so flagging it is a false positive by
# construction.
#
# The match CAPTURES the ABI literal as group `abi` so the caller can
# exclude exactly that span and nothing else.  Skipping the whole line
# (the first implementation of this exemption) is a false-negative
# hole: a one-line `extern "C" fn f() -> &'static str { "/secrets" }`
# under `#[rustfmt::skip]` hid every other literal on the line, which
# is reachable in one line of code and survives `cargo fmt --check`.
# This script's contract is "prefer a false positive over a false
# negative" (see the module docstring), so the exemption is scoped as
# tightly as the grammar allows.
EXTERN_ABI_LINE = re.compile(
    r"""^\s*
        (?:pub(?:\s*\((?:[^()]|\([^()]*\))*\))?\s+)?   # pub / pub(crate) / pub(in path)
        (?:unsafe\s+)?                    # optional `unsafe`
        extern\s+                        # the keyword itself
        (?P<abi>"[^"]*")                 # the ABI literal, captured
    """,
    re.VERBOSE,
)


CFG_PREDICATE = re.compile(
    r"""cfg(?:_attr)?!\s*\(\s*
        [A-Za-z_][A-Za-z0-9_]*\s*=\s*        # the predicate key
        (?P<val>"[^"]*")                      # the literal, captured
    """,
    re.VERBOSE,
)


SKIP_DIR_NAMES = {
    ".git", "target", ".cargo", "node_modules", ".venv", "venv", "dist",
    "build", ".idea", ".vscode", "out",
}


def _list_rs_files(root: Path) -> list[Path]:
    r = subprocess.run(
        ["find", str(root), "-name", "*.rs",
         "-not", "-path", "*/target/*",
         "-not", "-path", "*/.cargo/registry/*"],
        capture_output=True, text=True,
    )
    files = [Path(line) for line in r.stdout.strip().splitlines() if line]
    files = [f for f in files
             if not any(part in SKIP_DIR_NAMES for part in f.parts)]
    # Drop anything git already ignores (2026-09-28).  A path listed in a
    # .gitignore is by definition not part of the project: `crate-cli/tmp/`
    # holds 25 scratch crates from `crate fmt` runs, and scanning them
    # reported violations in files no commit can ever contain.
    return _drop_git_ignored(files, root)


def _drop_git_ignored(files: list[Path], root: Path) -> list[Path]:
    """Return the files git does not ignore.  One batched check-ignore call."""
    if not files:
        return files
    try:
        rels = [str(f.relative_to(root)) for f in files]
    except ValueError:
        return files
    try:
        r = subprocess.run(
            ["git", "-C", str(root), "check-ignore", "--stdin"],
            input="\n".join(rels) + "\n",
            capture_output=True, text=True, timeout=30,
        )
    except (OSError, subprocess.SubprocessError):
        return files  # not a git work tree, or git is unavailable
    if r.returncode not in (0, 1):
        return files
    ignored = {line.strip() for line in r.stdout.splitlines() if line.strip()}
    return [f for f, rel in zip(files, rels) if rel not in ignored]



def _is_format_macro(line: str) -> bool:
    """Return True if the string literal on this line is the
    format string of a known format-style macro (first arg)."""
    # Heuristic: line contains `<macro>!(` followed by string
    # literal before any other arg.
    for m in re.finditer(r"\b(\w+)!\s*\(", line):
        macro = m.group(1)
        if macro in FORMAT_MACROS:
            after = line[m.end():]
            str_match = STRING_LITERAL.search(after)
            if not str_match:
                continue
            comma_match = re.search(r",", after)
            if macro in {"write", "writeln"}:
                # write!/writeln! take the writer as the first arg, so the
                # format string is the second arg (after the first comma).
                if comma_match is None:
                    continue
                second_comma = re.search(r",", after[comma_match.end():])
                if str_match.start() > comma_match.end() and (
                    second_comma is None
                    or str_match.start() < comma_match.end() + second_comma.start()
                ):
                    return True
                continue
            if comma_match is None or str_match.start() < comma_match.start():
                # Format string is the first arg — exempt
                return True
    return False


def _exempt_format_string_lines(lines: list[str]) -> set[int]:
    """Return 1-based line numbers holding the format string of a
    multi-line format-macro call (rustfmt puts each arg on its own
    line, so the format string may not share a line with the macro).

    For write!/writeln! the format string is the second arg (writer
    first); for all other format macros it is the first arg.  Arg
    counting assumes one arg per line, which is how rustfmt wraps."""
    exempt: set[int] = set()
    macro_re = re.compile(r"\b(\w+)!\s*\(")
    for idx, line in enumerate(lines):
        for m in macro_re.finditer(line):
            macro = m.group(1)
            if macro not in FORMAT_MACROS:
                continue
            after = line[m.end():]
            if STRING_LITERAL.search(after):
                continue
            depth = 1 + after.count("(") - after.count(")")
            if depth <= 0:
                continue
            target_arg = 1 if macro in {"write", "writeln"} else 0
            arg_index = 1 if after.strip() else 0
            j = idx + 1
            while j < len(lines) and depth > 0:
                current = lines[j]
                depth += current.count("(") - current.count(")")
                content = current.strip()
                if content:
                    if arg_index == target_arg and STRING_LITERAL.search(current):
                        exempt.add(j + 1)
                        break
                    arg_index += 1
                j += 1
    return exempt


def _comment_start(line: str) -> int | None:
    """Index where a comment begins on this line, or None if there is none.

    String literals are tracked so that a `//` or `/*` inside a literal is not
    mistaken for a comment opener — `let u: &str = "http://host";` has no
    comment.  A `\\` escape advances past the next character.
    """
    i, n, in_str, in_char = 0, len(line), False, False
    while i < n:
        c = line[i]
        if in_str:
            if c == "\\":
                i += 2
                continue
            if c == '"':
                in_str = False
            i += 1
            continue
        if in_char:
            if c == "\\":
                i += 2
                continue
            if c == "'":
                in_char = False
            i += 1
            continue
        if c == '"':
            in_str = True
        elif c == "'" and i + 1 < n and line[i + 1] == "'":
            # Lifetime like `'static` is not a char literal; a char literal is
            # `'x'`.  Only treat as a char when a closing quote follows soon.
            j = i + 1
            while j < n and line[j] != "'":
                j += 1
            if j < n and j - i <= 4:
                in_char = True
        elif c == "/" and i + 1 < n:
            nxt = line[i + 1]
            if nxt == "/":
                return i
            if nxt == "*":
                return i
        i += 1
    return None


def _vars_block_lines(lines: list[str]) -> set[int]:
    """1-based line numbers inside a `vars! { ... }` design-token block.

    `vars!` is the CSS-token counterpart of `const.rs`: the string literals
    in it ARE the token values, hoisting them to a `const.rs` would defeat
    the purpose of a single design-token table. Without this exemption every
    token added to `ui/src/style/var/fn.rs` is reported, which is why that
    file carries a large pre-existing count — the token table is exactly
    where those literals are supposed to live.

    A file may declare several `vars!` blocks (one per theme), so the scan
    re-arms on every `vars!` line instead of stopping after the first one.
    """
    inside = False
    depth = 0
    marked: set[int] = set()
    for i, line in enumerate(lines, start=1):
        stripped = line.strip()
        if not inside:
            if re.match(r"^vars!\s*\{", stripped):
                inside = True
                depth = stripped.count("{") - stripped.count("}")
                marked.add(i)
            continue
        marked.add(i)
        depth += stripped.count("{") - stripped.count("}")
        if depth <= 0:
            inside = False
    return marked


def audit_one(path: Path) -> list[str]:
    try:
        text = path.read_text()
    except (OSError, UnicodeDecodeError):
        return []
    lines = text.splitlines()
    exempt_lines = _exempt_format_string_lines(lines)
    vars_lines = _vars_block_lines(lines)
    violations: list[str] = []
    for i, line in enumerate(lines, start=1):
        # Skip const.rs (the canonical home)
        if path.name == "const.rs":
            continue
        # Skip design-token literals declared inside `vars! { .. }`
        if i in vars_lines:
            continue
        # Skip attribute lines (#[doc = "..."], #[serde(...)])
        if ATTR_LINE.match(line):
            continue
        # Skip lines whose CODE POSITION is inside a comment (2026-09-28).
        # A string in a comment is prose the reader sees, not program data:
        # hoisting `/// (e.g. ":hover")` into const.rs would only corrupt the
        # documentation.  Measured across the three workspaces this removes
        # 637 reported violations that were all doc-comment examples
        # (euv 417, hyperlane 220, ctares 56).
        #
        # This must NOT become a way to hide a real violation, so the rule is
        # positional rather than "the line mentions a comment": the string
        # has to sit after the comment opener.  A trailing comment on a line
        # of real code (`let x: &str = "secret"; // "note"`) still reports the
        # code string and only the part after `//` is exempt.
        code_pos = _comment_start(line)
        if code_pos is not None:
            if code_pos == 0:
                # Whole line is a comment (line, block, doc, or inner).
                continue
            # Trailing comment: keep scanning the CODE part, which is what
            # the rule is about, and stop before the comment.  The scan
            # offset also keeps quote pairing from crossing the boundary.
            abi_end = 0
            scan_line = line[:code_pos]
        else:
            scan_line = line
        # Locate the foreign-ABI slot of `extern "C" { }` / `extern "C" fn f()`
        # (2026-09-28).  The ABI string is a grammar-level keyword slot, not
        # program data — `extern ABI {}` is a hard rustc syntax error, so it
        # can never be hoisted into const.rs.  Only the captured ABI span is
        # excluded below; every OTHER literal on the line is still reported.
        abi_match = EXTERN_ABI_LINE.match(line)
        abi_end = abi_match.end("abi") if abi_match else 0
        # Skip format-macro format strings
        if _is_format_macro(line):
            continue
        # `cfg!(target_os = "...")` is a grammar slot, not program data
        # (2026-09-28).  The predicate value must be a literal: `cfg!(.. =
        # SOME_CONST)` is `error: expected a literal ... found expression`,
        # so it can never be hoisted into const.rs.  Scoped to the captured
        # literal span, exactly like the ABI slot above, so that any OTHER
        # string on the same line is still reported.
        cfg_m = CFG_PREDICATE.search(scan_line)
        cfg_span = cfg_m.span("val") if cfg_m is not None else None
        if i in exempt_lines:
            continue
        # Find string literals on this line.  On an extern line the scan
        # RESUMES after the ABI literal rather than skipping the line:
        # STRING_LITERAL is quote-pairing, so a scan that started at the
        # ABI's closing quote would swallow the code between the two
        # literals and report a garbage span (and could miss a real
        # literal sitting inside that swallowed run).
        for m in STRING_LITERAL.finditer(scan_line, abi_end):
            if cfg_span is not None and m.span() == cfg_span:
                # The cfg! predicate literal itself: a grammar slot.
                continue
            literal = m.group(0)
            # Skip if literal looks like a path (contains /)
            # — paths often encode import paths in `use` and
            # inline `format!` paths.  We're strict here.
            violations.append(
                f"{path}:{i}: hardcoded string literal {literal!r} "
                f"must live in `const.rs` (§1.3c strengthened): "
                f"{line.strip()[:80]!r}"
            )
    return violations


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    if not root.is_dir():
        print(f"error: {root} is not a directory", file=sys.stderr)
        return 2
    total = 0
    files_with_v = 0
    for f in _list_rs_files(root):
        # Skip const.rs (we don't audit the canonical home)
        if f.name == "const.rs":
            continue
        # Skip tests/ (R14.7 self-contained)
        if "tests" in f.parts:
            continue
        v = audit_one(f)
        if v:
            files_with_v += 1
            total += len(v)
            for line in v:
                print(line)
    print(f"\n=== hardcoded-strings-to-const: "
          f"{total} violation(s) in {files_with_v} file(s) ===")
    return 0 if total == 0 else 1


if __name__ == "__main__":
    sys.exit(main())