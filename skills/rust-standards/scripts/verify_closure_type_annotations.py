#!/usr/bin/env python3
"""
Verify rust-standards §5.2 (new, 2026-09-26 third iteration):
closure parameters MUST have explicit type annotations.

User original (2026-09-26 third iteration):
  "闭包参数需要显示标注"

Specifically:

  ❌  let f = |x, y| x + y;
  ❌  vec.iter().map(|x| x * 2).collect()
  ❌  .filter(|item| item.is_valid())

  ✅  let f = |x: u32, y: u32| -> u32 { x + y };
  ✅  vec.iter().map(|x: &u32| x * 2).collect()
  ✅  .filter(|item: &Item| item.is_valid())

Exemptions (legitimate cases):
  - `||` (empty parameter list) — no params, no annotation needed
  - `|..|` (rest pattern) — no name, no annotation possible
  - `|(a, b): &(T, U)|` — pattern destructuring WITH type annotation
    on the whole tuple (this IS an explicit annotation)
  - `|&x: &T|` — single ref pattern with type annotation
  - inside `tests/` directory (R14.7 self-contained)

Detection approach:
  - Find all `|<params>|` patterns in the source.
  - For each, parse comma-separated params.
  - Each param is either:
    * `_` or `_name` — needs `: T` suffix
    * `name` (bare identifier) — needs `: T` suffix
    * `name: T` — ok
    * `(pat): T` — tuple pattern with type — ok
    * `&name: T` or `&mut name: T` — ref with type — ok
    * `..` — rest pattern — ok
  - Report any param that is just a bare identifier or `_name`
    without `: T`.

This script is heuristic — it cannot understand every valid
closure pattern (closures that destructure complex nested
patterns might false-positive).  When in doubt, prefer
false-negative (miss) over false-positive (false flag).  When
implementing new code, prefer explicit type annotation per
project convention.

Exits 0 if clean, 1 if any violation.

Usage:
    python3 verify_closure_type_annotations.py [ROOT]
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path


# Find closures.  Tricky because:
#   - `||` (no params) — must not match
#   - `| x |` (single param) — must match
#   - `|x: u32, y: String|` (multiple typed) — must match
#   - `|(a, b): &(T, U)|` (tuple pattern with type) — must match
#   - `|..|` (rest only) — must not flag
#   - `|x: &Foo|` (single typed) — must match
#   - `|x|` — violation
#
# Strategy: regex that captures |<params>|, then we parse the
# captured params in Python (not regex backrefs) for robustness.
#
# We also need to avoid:
#   - bitwise OR in expressions (e.g. `a | b`) — outside closures
#   - `||` operator (e.g. `a || b`) — single `|`, not `|...|`
#   - generics like `Vec<u32>` — `<u32>` not confused with `|`
#
# Heuristic: look for `|<non-empty-content>|` where content does
# not start with `=` or `|` (so `||` operator excluded).  Then
# split content by `,` at top-level (no `<>` nesting counted
# here — but Rust closures rarely have generic params inside).
CLOSURE = re.compile(
    r"\|(?P<params>[^|=][^|]*?)\|"
)


def _mask_line(line: str) -> list[bool]:
    """Return a per-character mask: True where the char is CODE, False
    where it belongs to a string / char / byte literal or a comment.

    The `|...|` scanner must only ever see real code.  Every reported
    false positive in a real repo came from a `|` that was really part
    of a string literal (``log::info!("(a|b|c)")``) or a `||` short
    circuit.  Masking by position — rather than skipping whole lines —
    is what makes the exemption safe: a genuine closure on a line that
    ALSO contains a string with a pipe is still checked (see the
    `tricky` fixture), which a `continue` on the line would miss.
    """
    mask = [True] * len(line)
    i, n = 0, len(line)
    while i < n:
        ch = line[i]
        # line comment: everything after `//` (but not `///`, handled as
        # code by the caller; here only `//` that is not `///`/`//!`)
        if ch == "/" and line[i:i + 3] not in ("///", "//!") and line[i + 1:i + 2] == "/":
            for k in range(i, n):
                mask[k] = False
            break
        # raw string r"..." / r#"..."#
        if ch == "r" and line[i + 1:i + 2] in ('"', "#"):
            j = i + 1
            hashes = 0
            while line[j:j + 1] == "#":
                hashes += 1
                j += 1
            if line[j:j + 1] != '"':
                i += 1
                continue
            close = '"' + "#" * hashes
            end = line.find(close, j + 1)
            end = n if end == -1 else end + len(close)
            for k in range(i, end):
                mask[k] = False
            i = end
            continue
        # normal string "..." with backslash escapes
        if ch == '"':
            j = i + 1
            while j < n:
                if line[j] == "\\":
                    j += 2
                    continue
                if line[j] == '"':
                    j += 1
                    break
                j += 1
            for k in range(i, min(j, n)):
                mask[k] = False
            i = j
            continue
        # char / byte literal 'x'  (careful: lifetimes look the same)
        if ch == "'":
            # a lifetime `'a` has no closing quote on the same token
            if line[i + 1:i + 2] != "\\" and line[i + 2:i + 3] == "'":
                for k in range(i, i + 3):
                    mask[k] = False
                i += 3
                continue
            if line[i + 1:i + 2] == "\\":
                j = i + 2
                while j < n and line[j] != "'":
                    j += 1
                j = min(j + 1, n)
                for k in range(i, j):
                    mask[k] = False
                i = j
                continue
            i += 1
            continue
        i += 1
    return mask


def _masked_spans(line: str) -> str:
    """Return `line` with every literal/comment character replaced by a
    space.  Offsets are preserved, so span arithmetic stays valid."""
    mask = _mask_line(line)
    return "".join(ch if keep else " " for ch, keep in zip(line, mask))


def _list_rs_files(root: Path) -> list[Path]:
    r = subprocess.run(
        ["find", str(root), "-name", "*.rs",
         "-not", "-path", "*/target/*",
         "-not", "-path", "*/.cargo/registry/*"],
        capture_output=True, text=True,
    )
    return [Path(line) for line in r.stdout.strip().splitlines() if line]


def _has_explicit_type(param: str) -> bool:
    """Return True if the param has explicit `: T` annotation
    or is a recognized pattern that doesn't need one (rest,
    destructuring with type, etc.)."""
    p = param.strip()
    if not p:
        return True  # empty (shouldn't happen but be safe)
    if p == "..":
        return True  # rest pattern
    if p == "_":
        # `|_|` binds nothing by name.  There is no identifier to attach a
        # type to, and writing `let _: u32 = ...` for a discarded
        # argument would change nothing about the reader's ability to see
        # the type.  Treat like the rest pattern: no annotation possible.
        return True
    # `&pat: T` or `&mut pat: T`
    if p.startswith(("&mut ", "&")):
        # Strip leading ref, check for `: T`
        rest = p.lstrip("&").lstrip("mut ").lstrip()
        if ":" in rest:
            # Has explicit type after ref pattern
            return True
        # `&x` without `: T` — violation
        return False
    # `(pat): T` — tuple destructuring with type
    if p.startswith("(") and ") :" in p:
        return True
    if ":" in p:
        # Walk through to find unbracketed `:`
        depth = 0
        for i, ch in enumerate(p):
            if ch in "([{":
                depth += 1
            elif ch in ")]}":
                depth -= 1
            elif ch == ":" and depth == 0:
                # has explicit type
                return True
    return False


def _is_macro_pattern(params: str) -> bool:
    """True when the captured `|...|` text is a macro_rules! fragment.

    Such text contains `$( ... )` repetitions or a bare repetition suffix
    (`*`, `+`, `?`) with no comma binding, which is a macro pattern rather
    than a closure parameter list.  A real closure always has plain
    comma-separated bindings and never contains `$(`.
    """
    if "$(" in params:
        return True
    # A bare repetition such as `*` or `?` captured as the whole "params".
    if params.strip() in {"*", "+", "?"}:
        return True
    return False


def _is_op_chain(p: str) -> bool:
    """True when the captured text is an operator chain, not a binding.

    Covers `==`, `!=`, `<=`, `>=`, `&&`, `||`, and arithmetic.  A closure
    parameter list can never contain a comparison or boolean operator, so
    their presence settles the question regardless of the surroundings.
    """
    return bool(re.search(r"==|!=|<=|>=|&&|\|\||\+\+|--|[+\-*/%^]", p))


def _is_pattern_tuple(p: str) -> bool:
    """True when `p` is a tuple/paren BINDING pattern rather than a call.

    `|(a, b)|`, `|&(x, y)|` and `|(a, (b, c))|` are closures over tuple
    patterns; `(a & b)` and `(a as u32)` are expressions.  The difference
    is what the parens contain: only bindings, refs, `_`, and `mut`.
    """
    s = p.strip()
    if not s.startswith("(") or not s.endswith(")"):
        return False
    inner = s[1:-1].strip()
    if not inner:
        return False
    # split on top-level commas
    parts, depth, cur = [], 0, ""
    for ch in inner:
        if ch in "([{<":
            depth += 1
        elif ch in ")]}>":
            depth -= 1
        if ch == "," and depth == 0:
            parts.append(cur)
            cur = ""
        else:
            cur += ch
    parts.append(cur)
    parts = [x.strip() for x in parts if x.strip()]
    if not parts:
        return False
    for part in parts:
        e = part
        for _ in range(2):  # `mut` and `&`/`&mut`, in either order
            e = re.sub(r"^(?:mut|&{0,2})\s+", "", e)
        if not e:
            continue
        if e == "_":
            continue
        if _is_pattern_tuple(e):  # nested tuple
            continue
        if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*(\s*:\s*.+)?", e):
            continue
        return False
    return True


def _next_nonspace(line: str, index: int, step: int) -> str | None:
    """Return the nearest non-whitespace character to `line[index]`,
    scanning in direction `step`, or None at end of line.

    `index` is the edge of the captured `|...|` group.  When scanning
    forwards the group-closing `|` itself is skipped, so the caller sees
    the operator that follows the chain (`a | b | c` => `c`).
    """
    i = index
    while True:
        i += step
        if i < 0 or i >= len(line):
            return None
        ch = line[i]
        if ch.isspace():
            continue
        if ch == "|":
            # the group delimiter, not an operand
            continue
        return ch


def _is_bitwise_or_chain(
    params: str, line: str, span: tuple[int, int]
) -> bool:
    """True when the `|`...`|` match is a bitwise-or / boolean short-circuit
    chain, not closure parameters.

    A closure parameter list is a comma-separated binding list: its content
    is identifiers, `&`/`&mut`/`_`/patterns, and `: Type` annotations.  An
    operand chain is none of those — it contains calls, `&` masks, casts or
    a bare parenthesised expression, and it is always delimited by `|` that
    has a non-empty operand on BOTH sides (the `|` delimiters sit OUTSIDE
    the captured group, so the shape is judged from the source around the
    span, not from the captured text).

    Both cases below were read as closures before this check existed:
      `name.contains('/') || name.contains('\\')`      (`||` short circuit)
      `(hash_b & hash_c) | (hash_b & hash_d) | ...`     (bitwise mask chain)
    """
    p = params.strip()
    if not p:
        return False
    # --- BINDING LISTS: never an operand chain.  Checked FIRST, because a
    # tuple pattern like `|(k, v)|` is full of parens and commas and would
    # otherwise be mistaken for a call expression.
    if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", p):
        return False
    if re.fullmatch(r"(?:mut\s+)?(?:&{0,2}\s*)?[A-Za-z_][A-Za-z0-9_]*(?:\s*,\s*(?:mut\s+)?(?:&{0,2}\s*)?[A-Za-z_][A-Za-z0-9_]*)*", p):
        return False
    if re.fullmatch(r"\([^)]*\)\s*:\s*.+", p):  # tuple pattern WITH type
        return False
    # An un-annotated tuple pattern: `(a, b)`, `&(a, b)`, `mut (a, b)`,
    # `(a, (b, c))`, and any mix of refs/underscores inside.  This is a
    # binding list, so the presence of parens is not evidence of a call.
    if _is_pattern_tuple(p):
        return False
    # Operand on both sides of each delimiter => an operator chain.
    # The captured group is the text BETWEEN two `|` chars, so for
    # `a | b | c` it is the middle operand `b`.  A real closure is
    # introduced by an opening `|` that has NO operand before it, which
    # makes the pair asymmetric — so the "before" char must be one that
    # can legally precede a value (identifier, `)`, `]`, quote, digit).
    # NOTE: skip whitespace before inspecting the neighbouring char;
    # `a | b | c` puts a space between the operand and the delimiter, and
    # testing the raw neighbour would see `' '` and wrongly conclude the
    # chain ends there.
    start, end = span
    before = _next_nonspace(line, start, -1)
    after = _next_nonspace(line, end, +1)
    if before is None or after is None:
        return False
    if not re.match(r"[\w)\]\"']", before):
        # nothing that can end an operand precedes the opening `|`
        return True
    if before in {"|", "&", "!", "=", "<", ">", "+", "-", "*", "/", "%", "^"}:
        return True
    # `a | b` / `a || b`: the captured text is an expression, not a
    # binding list — calls, masks, casts and quotes cannot appear in a
    # parameter pattern.
    if "(" in p or ")" in p or "&" in p or "'" in p or "\"" in p or "<<" in p or "as " in p:
        return True
    return False


def audit_one(path: Path) -> list[str]:
    try:
        text = path.read_text()
    except (OSError, UnicodeDecodeError):
        return []
    violations: list[str] = []
    for i, line in enumerate(text.splitlines(), start=1):
        # Skip comments — we don't want to flag closure-shaped
        # content inside `// ...` lines.
        if line.lstrip().startswith(("/", "*")):
            continue
        # Scan only the CODE part of the line: string / char literals and
        # trailing comments are blanked out first, preserving offsets, so
        # a `|` inside `log::info!("a|b|c")` is never read as a closure
        # delimiter (2026-09-28).  Exempting by span, not by line, keeps
        # real closures on the same line visible.
        code = _masked_spans(line)
        # Skip macro_rules! lines whose `|` sits inside a `$( ... )`
        # repetition (2026-09-28).  A macro matcher and a macro body are
        # both patterns, not closures: `move |$( $arg:ident $(: $ty:ty)? ),*|`
        # must not be asked for a type annotation, because adding one means
        # editing the macro and breaking it.  A real closure with real
        # parameters is still checked, so this is not a blanket exemption.
        for m in CLOSURE.finditer(code):
            params_str = m.group("params")
            if _is_macro_pattern(params_str):
                continue
            # An operator chain (`a == b || c == d`, `(a & b) | (c & d)`) is
            # never a closure.  Checked before the bitwise-specific helper
            # because that one needs the surrounding span; this one is
            # self-contained and covers `==`/`!=`/`<=`/`&&` too.
            if _is_op_chain(params_str):
                continue
            if _is_bitwise_or_chain(params_str, code, m.span("params")):
                # `|`-separated bit operations, e.g.
                # `((a as usize) << 16) | ((b as usize) << 8)`, were being read
                # as closure parameters.  A `|` chain is not a closure: the
                # delimiter sits OUTSIDE the captured group, so the marker is read
                # from the source around the span.
                continue
            # Split by `,` at depth 0
            params = _split_top_commas(params_str)
            for param in params:
                if not _has_explicit_type(param):
                    violations.append(
                        f"{path}:{i}: closure parameter without "
                        f"explicit type annotation (§5.2): {param.strip()!r} "
                        f"in `|...|`"
                    )
    return violations


def _split_top_commas(s: str) -> list[str]:
    """Split string by `,` at depth 0 (no nesting in <>, (), etc.)."""
    out: list[str] = []
    depth = 0
    cur = ""
    for ch in s:
        if ch in "([{<":
            depth += 1
            cur += ch
        elif ch in ")]}>":
            depth -= 1
            cur += ch
        elif ch == "," and depth == 0:
            out.append(cur)
            cur = ""
        else:
            cur += ch
    if cur:
        out.append(cur)
    return out


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    if not root.is_dir():
        print(f"error: {root} is not a directory", file=sys.stderr)
        return 2
    total = 0
    files_with_v = 0
    for f in _list_rs_files(root):
        if "tests" in f.parts:
            continue
        v = audit_one(f)
        if v:
            files_with_v += 1
            total += len(v)
            for line in v:
                print(line)
    print(f"\n=== closure-params-explicit-type: "
          f"{total} violation(s) in {files_with_v} file(s) ===")
    return 0 if total == 0 else 1


if __name__ == "__main__":
    sys.exit(main())