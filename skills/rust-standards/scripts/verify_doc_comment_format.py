#!/usr/bin/env python3
"""
Verify rust-standards §2.2 doc-comment format compliance for any Rust
project (read-only checker).

Reuses parser logic from doc_comment_audit.py but is a pure verifier
(no fixing).  Audits:

  Layer 1 — Existence
      Every non-#[test] fn / `impl` block in src-adjacent code must
      carry at least one `///` line above it.  Test fns are exempt.

  Layer 2 — Completeness (per §2.2 template)
      Every fn with non-self parameters OR a non-()/Self return type
      must carry the corresponding `# Arguments` / `# Returns` section
      in its `///` block.

  Layer 3 — Format
      Doc comments on fn items MUST follow the §2.2 template:
        /// Brief description.
        ///
        /// Extended explanation if needed.
        ///
        /// # Arguments
        ///
        /// - `Type` - description
        /// - `Name: Constraint` - description
        ///
        /// # Returns
        ///
        /// - `Type`: description
        ///
        /// # Panics
        ///
        /// explanation
      Specifically: each section header is preceded by `///` (no `///`
      block fragments), arguments list is one `- `Type` - description`
      per line, returns list is one `- `Type`: description` per line.

  Layer 4 — Signature type match (2026-09-26 user strengthening, "需要
      针对文档注释加强校验").  For `# Arguments`, each list item's
      backtick-quoted type MUST equal the corresponding parameter's
      type-in-signature (the type literal appearing in `fn foo(p: T)`,
      including leading `&` and inline `` ` ``).  For `# Returns`, the
      single backtick-quoted type MUST equal the return type signature.
      This prevents the historical drift where authors wrote
      `- `Argument` - description` when the signature was actually
      `- `InternalAttribute` - description`.  The brief description
      lines (prose) preceding the sections must be English (the rule
      was always implicit per §2.7); this is not separately checked
      here because prose-language detection is outside the verifier's
      scope, but the structural requirement (prose lines MUST precede
      the first `#` section header) IS enforced: a doc block whose
      first non-blank `///` line is `/// # Arguments` (no prose
      before) is flagged.

Exits 0 if clean, 1 if any violation.  Lists one violation per line.

Usage:
    python3 verify_doc_comment_format.py [ROOT]
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path


# Match `fn name` declarations (with optional visibility/qualifiers).
_FN_PATTERN = re.compile(
    r"^(\s*)((?:pub(?:\([^)]*\))?\s+|async\s+|const\s+|unsafe\s+)*)"
    r"fn\s+([A-Za-z_][A-Za-z0-9_]*)\s*[<(]"
)


def _list_rs_files(root: Path) -> list[Path]:
    """Find every .rs file under root via `find` so we don't depend
    on the cwd being a git repo."""
    r = subprocess.run(
        ["find", str(root), "-name", "*.rs",
         "-not", "-path", "*/target/*",
         "-not", "-path", "*/.cargo/registry/*"],
        capture_output=True, text=True,
    )
    return [Path(line) for line in r.stdout.strip().splitlines() if line]


def _scan_test_regions(lines: list[str]) -> set[int]:
    """Return line indices (0-based) that lie inside `#[cfg(test)]`
    blocks or follow `#[test]` attributes.  Test fns are exempt."""
    inside_cfg_test: set[int] = set()
    in_cfg = False
    bracket_depth = 0
    for i, ln in enumerate(lines):
        s = ln.strip()
        if not in_cfg and "#[cfg(test)]" in ln and ln.lstrip().startswith("#["):
            in_cfg = True
            bracket_depth = ln.count("{") - ln.count("}")
            continue
        if in_cfg:
            bracket_depth += ln.count("{") - ln.count("}")
            if bracket_depth <= 0:
                in_cfg = False
            else:
                inside_cfg_test.add(i)
            continue
        if s in {"#[test]", "#[wasm_bindgen_test]", "#[tokio::test]"} or "tokio::test" in s:
            for j in range(i + 1, min(i + 5, len(lines))):
                t = lines[j].strip()
                if t == "" or t.startswith("#["):
                    continue
                inside_cfg_test.add(j)
                break
    return inside_cfg_test


def _find_fn_locs(lines: list[str]) -> list[int]:
    out: list[int] = []
    for i, ln in enumerate(lines):
        if ln.lstrip().startswith("//"):
            continue
        if _FN_PATTERN.match(ln):
            out.append(i)
    return out


def _extract_doc_block(lines: list[str], below_idx: int) -> tuple[int, int] | None:
    """Return (start, end) inclusive for the `///` block ending just
    before `below_idx` (0-based line indices).

    Attribute lines (`#[...]`) between the doc block and the fn are
    skipped, since idiomatic Rust places doc comments above attributes.
    """
    j = below_idx - 1
    while j >= 0 and (
        lines[j].strip() == "" or lines[j].lstrip().startswith("#[")
    ):
        j -= 1
    if j < 0 or not lines[j].lstrip().startswith("///"):
        return None
    end = j
    start = j
    while start > 0 and lines[start - 1].lstrip().startswith("///"):
        start -= 1
    return start, end


def _split_top_commas(params_str: str) -> list[str]:
    depth = 0
    parts: list[str] = []
    last = 0
    for i, ch in enumerate(params_str):
        if ch in "([{<":
            depth += 1
        elif ch in ")]}>":
            depth -= 1
        elif ch == "," and depth == 0:
            parts.append(params_str[last:i])
            last = i + 1
    parts.append(params_str[last:])
    return parts


def _fn_signature_types(lines: list[str], fn_idx: int) -> tuple[str, list[str], str]:
    """Return (name, raw_param_types, raw_return_type).

    `raw_param_types` is the list of bare-type strings for every
    non-self parameter, exactly as written in the signature
    (whitespace-trimmed, but `&` and `` ` `` preserved).  This is
    what Layer 4 matches against the doc-comment's backtick-quoted
    type literal.

    `raw_return_type` is the bare return-type string for non-()/
    Self/no-return cases, with `&` and `` ` `` preserved.
    """
    ln = lines[fn_idx]
    m = _FN_PATTERN.match(ln)
    if not m:
        return "", [], ""
    name = m.group(3)
    name_pos = ln.find(name) + len(name)
    paren_start = ln.find("(", name_pos)
    if paren_start == -1:
        return name, [], ""
    sig_lines = [ln]
    depth = 1
    k = paren_start + 1
    while k < len(ln) and depth > 0:
        ch = ln[k]
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        k += 1
    if depth != 0:
        more = 1
        while depth > 0 and fn_idx + more < len(lines):
            sig_lines.append(lines[fn_idx + more])
            for ch in lines[fn_idx + more]:
                if ch == "(":
                    depth += 1
                elif ch == ")":
                    depth -= 1
            more += 1
    sig = "\n".join(sig_lines)
    after_name = sig.find(name) + len(name)
    paren_start2 = -1
    depth_gen = 0
    for k in range(after_name, len(sig)):
        ch = sig[k]
        if ch == "<" and depth_gen == 0:
            depth_gen += 1
        elif ch == ">" and depth_gen > 0:
            depth_gen -= 1
        if ch == "(" and depth_gen == 0:
            paren_start2 = k
            break
    if paren_start2 == -1:
        return name, [], ""
    depth = 1
    k = paren_start2 + 1
    while k < len(sig) and depth > 0:
        ch = sig[k]
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        k += 1
    params_str = sig[paren_start2 + 1:k - 1]
    params_list = [p.strip() for p in _split_top_commas(params_str)]
    raw_types: list[str] = []
    for p in params_list:
        if p in {"", "&self", "&mut self", "self", "mut self"}:
            continue
        colon = p.find(":")
        if colon == -1:
            raw_types.append(p.strip())
        else:
            raw_types.append(p[colon + 1:].strip())
    after = sig[k:]
    m2 = re.search(r"->\s*([^{=;]+)", after)
    ret_str = ""
    if m2:
        ret_raw = m2.group(1).strip().rstrip(",")
        ret_raw = re.sub(r"\{.*$", "", ret_raw, flags=re.DOTALL).strip()
        ret_clean = ret_raw.split("where")[0].split(";")[0].strip()
        ret_str = ret_clean
        if ret_clean in ("()", "Self", ""):
            ret_str = ""
    return name, raw_types, ret_str


def _fn_signature_full_legacy(lines: list[str], fn_idx: int) -> tuple[str, list[str], str]:
    """Legacy wrapper kept for Layers 1/2/3 — strips `&` / `` ` `` /
    whitespace from types.  Layer 4 uses `_fn_signature_types`
    directly instead so it can compare against the raw signature."""
    name, raw_types, ret_str = _fn_signature_types(lines, fn_idx)
    norm_types = [t.replace("`", "").replace("&", "").strip() for t in raw_types]
    ret_norm = ret_str.replace("`", "").replace("&", "").strip()
    if ret_norm in ("()", "Self", ""):
        ret_norm = ""
    return name, norm_types, ret_norm


def _format_arg_line(s: str) -> bool:
    """Per §2.2: arg list is `- `Type` - description`.  Each line
    must match `^/// - `[^`]+` - .+`."""
    return bool(re.match(r"^/// - `[^`]+` - .+", s))


def _format_return_line(s: str) -> bool:
    """Per §2.2 (2026-09-26 user strengthening): returns list is
    either `- `Type` - description` (dash form, per user's `eq`
    example, where the separator is ` - ` after the type) or
    `- `Type`: description` (colon form, per user's
    `try_get_internal_attribute` example, where the separator is
    `: ` after the type — no space between the closing backtick
    and the colon).  Both separators are accepted.  Each line must
    match `^/// - `[^`]+` ?(-|:) .+`."""
    return bool(re.match(r"^/// - `[^`]+` ?(-|:) .+", s))


def _has_prose_before_first_section(doc_text: str) -> bool:
    """Layer 4 sub-check (2026-09-26 user strengthening): the doc
    block must contain at least one English-prose `///` line BEFORE
    the first `/// # Arguments` (or other `/// #`) section header.
    A doc block that opens with `/// # Arguments` and no prose
    before it fails this check.

    Prose = a `///` line that is neither empty nor a section
    header (`# XXX`).
    """
    for raw in doc_text.splitlines():
        s = raw.strip()
        if s.startswith("/// #"):
            return False
        if s.startswith("///") and s not in {"///", "///!"}:
            return True
    return False


def audit_one(path: Path) -> list[str]:
    try:
        text = path.read_text()
    except (OSError, UnicodeDecodeError):
        return []
    lines = text.splitlines()
    fn_locs = _find_fn_locs(lines)
    test_regions = _scan_test_regions(lines)
    violations: list[str] = []

    for fn_idx in fn_locs:
        if fn_idx in test_regions:
            continue
        doc = _extract_doc_block(lines, fn_idx)
        if doc is None:
            name = (_FN_PATTERN.match(lines[fn_idx]) or [None, None, None, None])[3] or "?"
            violations.append(
                f"{path}:{fn_idx + 1}: fn `{name}` missing `///` doc comment (§2.1)"
            )
            continue
        doc_start, doc_end = doc
        doc_text = "\n".join(lines[doc_start:doc_end + 1])
        name, raw_param_types, raw_ret_type = _fn_signature_types(lines, fn_idx)
        _, norm_param_types, norm_ret_type = _fn_signature_full_legacy(lines, fn_idx)

        has_args = bool(re.search(r"^\s*///\s*#\s*Arguments\s*$", doc_text, re.MULTILINE))
        has_returns = bool(re.search(r"^\s*///\s*#\s*Returns\s*$", doc_text, re.MULTILINE))

        # Layer 2 — section completeness (presence checks).
        if norm_param_types and not has_args:
            violations.append(
                f"{path}:{fn_idx + 1}: fn `{name}` has non-self params but "
                f"missing `# Arguments` section (§2.2)"
            )
        if norm_ret_type and not has_returns:
            violations.append(
                f"{path}:{fn_idx + 1}: fn `{name}` returns non-() but "
                f"missing `# Returns` section (§2.2)"
            )

        # Layer 3 — format inside sections.
        # Layer 4 — signature type match (drives off the same scan).
        in_args = False
        in_returns = False
        seen_arg_types: list[str] = []
        for j in range(doc_start, doc_end + 1):
            s = lines[j].strip()
            if s.startswith("/// # Arguments"):
                in_args, in_returns = True, False
                continue
            if s.startswith("/// # Returns"):
                in_args, in_returns = False, True
                continue
            if s.startswith("/// #"):
                in_args, in_returns = False, False
                continue
            if in_args and s.startswith("/// -"):
                if not _format_arg_line(s):
                    violations.append(
                        f"{path}:{j + 1}: `# Arguments` line format violation "
                        f"(must be `- `Type` - description`): {s!r}"
                    )
                    continue
                # Layer 4 — extract backtick-quoted type from this
                # `- `Type` - description` line and compare against
                # the raw signature type for the corresponding
                # parameter.
                m_t = re.match(r"^/// - `([^`]+)` - ", s)
                if m_t:
                    doc_type = m_t.group(1).strip()
                    seen_arg_types.append(doc_type)
            if in_returns and s.startswith("/// -"):
                if not _format_return_line(s):
                    violations.append(
                        f"{path}:{j + 1}: `# Returns` line format violation "
                        f"(must be `- `Type` - description` or `- `Type`: description`): {s!r}"
                    )
                    continue
                # Layer 4 — extract backtick-quoted return type and
                # compare against the raw signature return type.
                # Match either separator: `- `T` - desc` or
                # `- `T`: desc` (note: colon form has NO space
                # between the closing backtick and the colon).
                m_t = re.match(r"^/// - `([^`]+)` ?(-|:) ", s)
                if m_t and raw_ret_type:
                    doc_type = m_t.group(1).strip()
                    sig_type = raw_ret_type.strip()
                    if doc_type != sig_type:
                        violations.append(
                            f"{path}:{j + 1}: `# Returns` type literal "
                            f"`{doc_type}` does not match fn signature return "
                            f"type `{sig_type}` (§2.2 Layer 4)"
                        )

        # Layer 4 (cont.) — every seen arg type must appear in the
        # raw signature param types (set comparison; order-insensitive
        # since the signature is the source of truth, not the doc).
        if seen_arg_types:
            sig_type_set = {t.strip() for t in raw_param_types}
            for doc_type in seen_arg_types:
                if doc_type not in sig_type_set:
                    violations.append(
                        f"{path}:{fn_idx + 1}: fn `{name}` `# Arguments` type "
                        f"literal `{doc_type}` does not match any parameter "
                        f"type in the signature `{raw_param_types}` "
                        f"(§2.2 Layer 4)"
                    )
            # Also flag missing args: every distinct signature type
            # must appear at least once in the doc block (set
            # semantics — `fn f(a: u32, b: u32)` requires only one
            # `- `u32` - ...` line in the doc, not two).
            sig_type_seen = {t for t in seen_arg_types if t in sig_type_set}
            missing = sig_type_set - sig_type_seen
            if missing:
                violations.append(
                    f"{path}:{fn_idx + 1}: fn `{name}` `# Arguments` does not "
                    f"cover all signature types; missing: {sorted(missing)} "
                    f"(signature has `{raw_param_types}`, doc has "
                    f"`{seen_arg_types}`) (§2.2 Layer 4)"
                )

        # Layer 4 sub-check — prose before first section.
        if has_args or has_returns:
            if not _has_prose_before_first_section(doc_text):
                violations.append(
                    f"{path}:{fn_idx + 1}: fn `{name}` doc comment has no "
                    f"prose `///` line before first `#` section header; "
                    f"brief description must precede `# Arguments` / "
                    f"`# Returns` (§2.2)"
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
        # Skip tests entirely (R14.5 forbids comments in tests).
        if "tests" in f.parts:
            continue
        v = audit_one(f)
        if v:
            files_with_v += 1
            total += len(v)
            for line in v:
                print(line)
    print(f"\n=== doc-comment format: "
          f"{total} violation(s) in {files_with_v} file(s) ===")
    return 0 if total == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
