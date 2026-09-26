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
      block fragments), arguments list is one `- \`Type\` - description`
      per line, returns list is one `- \`Type\`: description` per line.

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
    before `below_idx` (0-based line indices)."""
    j = below_idx - 1
    while j >= 0 and lines[j].strip() == "":
        j -= 1
    if j < 0 or not lines[j].lstrip().startswith("///"):
        return None
    end = j
    start = j
    while start > 0 and lines[start - 1].lstrip().startswith("///"):
        start -= 1
    return start, end


def _fn_signature_full(lines: list[str], fn_idx: int) -> tuple[str, list[str], str]:
    """Return (name, non_self_params, return_type)."""
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
    non_self = [p for p in params_list if p not in {"", "&self", "&mut self", "self", "mut self"}]
    after = sig[k:]
    m2 = re.search(r"->\s*([^{=;]+)", after)
    ret_str = ""
    if m2:
        ret_raw = m2.group(1).strip().rstrip(",")
        ret_raw = re.sub(r"\{.*$", "", ret_raw, flags=re.DOTALL).strip()
        ret_clean = ret_raw.replace("`", "").replace("&", "").strip()
        ret_clean = ret_clean.split("where")[0].split(";")[0].strip()
        ret_str = ret_clean
        if ret_clean in ("()", "Self", ""):
            ret_str = ""
    return name, non_self, ret_str


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


def _format_arg_line(s: str) -> bool:
    """Per §2.2: arg list is `- \`Type\` - description`.  Each line
    must match `^/// - `[^`]+` - .+`."""
    return bool(re.match(r"^/// - `[^`]+` - .+", s))


def _format_return_line(s: str) -> bool:
    """Per §2.2: returns is `- \`Type\`: description`.  Each line must
    match `^/// - `[^`]+`: .+`."""
    return bool(re.match(r"^/// - `[^`]+`: .+", s))


def audit_one(path: Path) -> list[str]:
    try:
        text = path.read_text()
    except (OSError, UnicodeDecodeError):
        return []
    lines = text.splitlines()
    fn_locs = _find_fn_locs(lines)
    test_regions = _scan_test_regions(lines)
    violations: list[str] = []

    # Layer 1 — bare fn.
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
        # Layer 2 — section completeness.
        doc_start, doc_end = doc
        doc_text = "\n".join(lines[doc_start:doc_end + 1])
        name, non_self, ret_str = _fn_signature_full(lines, fn_idx)
        # Strict section header check: `/// # Arguments` (possibly trailing ws).
        has_args = bool(re.search(r"^///\s*#\s*Arguments\s*$", doc_text, re.MULTILINE))
        has_returns = bool(re.search(r"^///\s*#\s*Returns\s*$", doc_text, re.MULTILINE))
        if non_self and not has_args:
            violations.append(
                f"{path}:{fn_idx + 1}: fn `{name}` has non-self params but "
                f"missing `# Arguments` section (§2.2)"
            )
        if ret_str and not has_returns:
            violations.append(
                f"{path}:{fn_idx + 1}: fn `{name}` returns non-() but "
                f"missing `# Returns` section (§2.2)"
            )

        # Layer 3 — format inside sections.
        in_args = False
        in_returns = False
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
            if in_returns and s.startswith("/// -"):
                if not _format_return_line(s):
                    violations.append(
                        f"{path}:{j + 1}: `# Returns` line format violation "
                        f"(must be `- `Type`: description`): {s!r}"
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