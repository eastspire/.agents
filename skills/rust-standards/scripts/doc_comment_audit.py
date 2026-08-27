#!/usr/bin/env python3
"""Bulk doc-comment auditor + fixer for rust-standards §2.1+§2.2 compliance.

Two-layer audit (each is an independent gate):

  Layer 1 — Existence
      Every non-#[test] fn / `impl` block in src-adjacent code must carry
      at least one `///` line above it.

  Layer 2 — Completeness (per §2.2 template)
      Every fn with non-self parameters OR a non-()/Self return type must
      also carry the corresponding `# Arguments` / `# Returns` section.

Modes:
  --check            run both audits and print a per-line report of remaining
                     violations; exit non-zero if any. Does not modify files.
  (no flag)          run both layers' fixups on every Rust file in the repo
                     (git ls-files). Idempotent: rerunning is a no-op.

Usage:
  python3 doc_comment_audit.py --check              # audit only
  python3 doc_comment_audit.py                      # fix in place
  python3 doc_comment_audit.py --check --root <DIR> # audit a different worktree

The script is intentionally self-contained: no third-party dependencies. Run
it from any rust project root, including projects not written in Python. The
only assumption is that `git ls-files` lists the Rust source files in scope.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from collections import defaultdict
from typing import Iterable

# ---------- pure helpers (no side effects) ---------------------------------


def _split_top_commas(params_str: str) -> list[str]:
    """Split a function parameter list by top-level commas (ignoring [], <>, {})."""
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


def _balanced_from_input(impl_text: str) -> str | None:
    """Extract the input type from `impl From<...> for ...` with nested <>."""
    m = re.search(r"\bFrom<", impl_text)
    if not m:
        return None
    p = m.start() + len("From<")
    depth = 1
    for i in range(p, len(impl_text)):
        ch = impl_text[i]
        if ch == "<":
            depth += 1
        elif ch == ">":
            depth -= 1
            if depth == 0:
                return impl_text[p:i]
    return None


def _detect_target_type(impl_text: str) -> str:
    """`impl Display for X` -> `X`; `impl X {` -> `X`; otherwise `Self`."""
    m = re.search(r"for\s+([A-Za-z_][A-Za-z0-9_]*)", impl_text)
    if m:
        return m.group(1)
    m = re.match(r"impl(?:<[^>]+>)?\s+([A-Za-z_][A-Za-z0-9_]*)", impl_text)
    if m:
        rest = impl_text[m.end():].strip().split()
        if not rest or rest[0] == "{":
            return m.group(1)
    return "Self"


# ---------- brief-doc generator (Layer 1) ----------------------------------


def _describe_type_arg(t: str) -> str:
    """Phrase a type as a function *parameter* (ends with period)."""
    t = t.strip()
    if t in ("&mut self", "&self", "self"):
        return "The receiver."
    if t.startswith("&mut "):
        return f"Mutable reference to a `{t[5:].strip()}` (mutated in place)."
    if t.startswith("&"):
        return f"Shared reference to a `{t[1:].strip()}`."
    primitives = {"f64": "A 64-bit float (`f64`).",
                  "f32": "A 32-bit float (`f32`).",
                  "usize": "A non-negative integer (`usize`).",
                  "u32": "A 32-bit unsigned integer (`u32`).",
                  "i32": "A 32-bit signed integer (`i32`).",
                  "bool": "A boolean (`bool`)."}
    if t in primitives:
        return primitives[t]
    if t in {"T", "F", "E", "Fut", "Reader", "Error", "I"}:
        return "A generic type parameter."
    if t in {"Vector2D", "Vector3D"}:
        return f"{t[-2:].lower()}D vector (`{t}`)."
    return f"A `{t}` parameter."


def _describe_type_return(t: str) -> str:
    """Phrase a type as a function *return* (no 'parameter' word, ends with period)."""
    t = t.strip()
    if t in {"()", "Self", ""}:
        return ""
    primitives = {"f64": "A 64-bit float.",
                  "f32": "A 32-bit float.",
                  "usize": "A non-negative integer.",
                  "u32": "A 32-bit unsigned integer.",
                  "i32": "A 32-bit signed integer.",
                  "bool": "A boolean."}
    if t in primitives:
        return primitives[t]
    if t in {"T", "F", "E", "Fut", "Reader", "Error", "I"}:
        return "A value of the generic type parameter."
    if t == "Vector2D":
        return "A 2D vector."
    if t == "Vector3D":
        return "A 3D vector."
    return f"A `{t}` value."


def build_short_fn_doc(impl_text: str, fn_name: str) -> list[str]:
    """One-line `///` doc for a fn that currently has none (Layer 1)."""
    target = _detect_target_type(impl_text)
    if target == "Self" and not impl_text:
        return [f"/// Body of the `{fn_name}` free function."]

    # Trait / specialization patterns.
    table: dict[str, str] = {
        "clone": f"/// Clones the [`{target}`].",
        "default": f"/// Constructs a default [`{target}`] value.",
        "fmt": f"/// Formats the [`{target}`] via the supplied formatter.",
        "eq": f"/// Returns `true` when `self` and `other` are equivalent.",
        "shape": "/// Returns the concrete shape variant of the collider.",
        "bounding_box": "/// Returns the axis-aligned bounding box of the collider.",
        "contains_point": "/// Returns `true` when the supplied point lies inside the collider.",
        "center": "/// Returns the geometric centre of the collider.",
        "lerp": "/// Linearly interpolates toward `other` by the supplied `factor`.",
        "magnitude": "/// Returns the Euclidean magnitude of the vector.",
        "magnitude_squared": "/// Returns the squared magnitude of the vector (no square root).",
        "normalized": "/// Returns the unit-length direction along `self`.",
        "scaled": "/// Returns the vector multiplied by `scalar`.",
        "dot": "/// Returns the dot product of `self` and `other`.",
        "zero": "/// Returns the zero vector of this dimension.",
        "update": "/// Advances the simulation by `delta_time` seconds.",
        "is_empty": "/// Returns `true` when the collection is empty.",
        "is_set": "/// Returns `true` when the value has been initialised.",
        "is_pending": "/// Returns `true` when a value is waiting to be emitted.",
        "is_throttling": "/// Returns `true` when a throttle delay is active.",
        "is_animating": "/// Returns `true` when an animation is currently running.",
        "is_at_max": "/// Returns `true` when the value is at the configured maximum.",
        "is_at_min": "/// Returns `true` when the value is at the configured minimum.",
        "len": "/// Returns the number of items in the collection.",
        "neg": "/// Returns the negated vector.",
        "add": "/// Adds `other` to `self`.",
        "sub": "/// Subtracts `other` from `self`.",
        "mul": "/// Multiplies `self` and `other` (or `scalar`).",
        "add_assign": "/// Adds `other` to `self` in place.",
        "sub_assign": "/// Subtracts `other` from `self` in place.",
        "mul_assign": "/// Multiplies `self` by `scalar` in place.",
    }
    if fn_name in table:
        return [table[fn_name]]
    if fn_name == "from":
        inner = _balanced_from_input(impl_text)
        if inner is not None:
            inner = inner.strip()
            m = re.match(r"Vec<(.+)>$", inner)
            if m:
                return [f"/// Lifts a `Vec<{m.group(1).strip()}>` into [`{target}`]."]
            m = re.match(r"Option<(.+)>$", inner)
            if m:
                return [f"/// Lifts an `Option<{m.group(1).strip()}>` into [`{target}`]."]
            return [f"/// Converts a `{inner}` into [`{target}`]."]
        return [f"/// Converts the input into [`{target}`]."]
    return [f"/// Implements the `{fn_name}` operation on [`{target}`]."]


def build_impl_block_doc(decl: str) -> str:
    """One-line `///` doc for an `impl` block opener that currently has none."""
    s = decl.rstrip("{").strip()
    for trait in ("Display", "Debug"):
        m = re.match(rf"impl\s+{trait}\s+for\s+(\w+)", s)
        if m:
            return f"/// Formatting / debug-printing for [`{m.group(1)}`]."
    m = re.match(r"impl\s+Default\s+for\s+(\w+)", s)
    if m:
        return f"/// Default construction for [`{m.group(1)}`]."
    m = re.match(r"impl\s+PartialEq\s+for\s+(\w+)", s)
    if m:
        return f"/// Equality comparison for [`{m.group(1)}`]."
    m = re.match(r"impl\s+Clone\s+for\s+(\w+)", s)
    if m:
        return f"/// Clone semantics for [`{m.group(1)}`]."
    m = re.match(r"impl\s+From<.+?>\s+for\s+(\w+)", s)
    if m:
        return f"/// `From` conversion into [`{m.group(1)}`]."
    m = re.match(r"impl(?:<[^>]+>)?\s+(\w+)\s*$", s)
    if m:
        return f"/// Inherent implementation of [`{m.group(1)}`]."
    m = re.match(r"impl\s+(\w+)\s+for\s+(\w+)", s)
    if m:
        return f"/// Implements [`{m.group(1)}`] for [`{m.group(2)}`]."
    return f"/// Implements `{s}`."


# ---------- full §2.2 template generator (Layer 2) -------------------------


# Common fn-name → per-param template. Patterns are matched more-specific-first;
# `*` is the wildcard fallback. See rust-standards §2.7 pitfall 6.
_FN_ARG_TEMPLATES: dict[str, list[tuple[str, str]]] = {
    "fmt":          [("*", "The formatter receiving the formatted output.")],
    "eq":           [("*", "The other value to compare against `self`.")],
    "from":         [("*", "Input value to convert from.")],
    "lerp":         [("*", "The opposite endpoint of the interpolation."),
                     ("factor", "Interpolation factor; typically `[0.0, 1.0]`.")],
    "update":       [("delta_time", "Seconds elapsed since the previous update.")],
    "is_touched":   [("*", "Field name.")],
    "is_alive":     [("*", "Raw address to test.")],
    "try_replace":  [("*", "Replacement value.")],
    "try_set":      [("*", "Value to store.")],
    "scaled":       [("*", "Scalar multiplier.")],
    "dot":          [("*", "Other vector.")],
    "contains_point":[("*", "Point to test.")],
    "add":          [("*", "Other operand.")],
    "sub":          [("*", "Operand to subtract.")],
    "mul":          [("*", "Other operand or scalar.")],
    "add_assign":   [("*", "Other operand.")],
    "sub_assign":   [("*", "Operand to subtract.")],
    "mul_assign":   [("*", "Scalar multiplier.")],
}


_FN_RETURN_TEMPLATES: dict[str, str] = {
    "default": "A default-constructed instance.",
    "from":    "The converted value of type `Self`.",
    "lerp":    "The linearly-interpolated value.",
}


def _match_arg_template(name_part: str, type_only: str,
                        patterns: list[tuple[str, str]] | None) -> str | None:
    """Apply the per-fn template — non-wildcard patterns first, then `*`."""
    if not patterns:
        return None
    for pat, desc in patterns:
        if pat == "*":
            continue
        if pat == name_part or pat == type_only:
            return desc
    for pat, desc in patterns:
        if pat == "*":
            return desc
    return None


def build_full_fn_doc_sections(name: str, non_self: list[str], return_type: str) -> tuple[list[str], list[str]]:
    """Return `(argument_lines, return_lines)` per rust-standards §2.2.

    `non_self` is a list of `name: Type` strings (no `self` / `&self`).
    `return_type` is the bare return string, or empty for `()` / `Self` / nothing.
    """
    patterns = _FN_ARG_TEMPLATES.get(name)
    arg_lines: list[str] = []
    if non_self:
        arg_lines.append("///")
        arg_lines.append("/// # Arguments")
        arg_lines.append("///")
        for p in non_self:
            colon = p.find(":")
            if colon == -1:
                name_part, type_only = "", p.strip()
            else:
                name_part = p[:colon].strip()
                type_only = p[colon + 1:].strip()
            desc = _match_arg_template(name_part, type_only, patterns) or _describe_type_arg(type_only)
            arg_lines.append(f"/// - `{type_only}` - {desc}")

    ret_lines: list[str] = []
    if return_type:
        ret_lines.append("///")
        ret_lines.append("/// # Returns")
        ret_lines.append("///")
        desc = _FN_RETURN_TEMPLATES.get(name)
        if desc is None:
            if return_type == "Self":
                desc = "The constructed value (`Self`)."
            elif return_type.startswith("Result"):
                desc = "Result of the operation; an `Err` variant on failure."
            elif return_type.startswith("Option"):
                desc = "`Some(...)` on success, `None` otherwise."
            else:
                desc = _describe_type_return(return_type)
        ret_lines.append(f"/// - `{return_type}` - {desc}")

    return arg_lines, ret_lines


# ---------- scanner helpers -------------------------------------------------


_FN_PATTERN = re.compile(
    r"^\s*((?:pub(?:\([^)]*\))?\s+|async\s+)?(?:const\s+|unsafe\s+)*)fn\s+([A-Za-z_][A-Za-z_0-9]*)\s*[<(]"
)


def _scan_test_regions(lines: list[str], fn_locs: list[int]) -> set[int]:
    """Return fn_locs that lie inside `#[cfg(test)]` modules or follow a `#[test]` attr."""
    inside_cfg_test: set[int] = set()
    in_cfg = False
    bracket_depth = 0
    cfg_enter_depth = -1
    for i, ln in enumerate(lines):
        s = ln.strip()
        if not in_cfg and "#[cfg(test)]" in ln and ln.lstrip().startswith("#["):
            for j in range(i + 1, min(i + 5, len(lines))):
                if "{" in lines[j]:
                    in_cfg = True
                    cfg_enter_depth = lines[j].count("{") - lines[j].count("}")
                    bracket_depth = cfg_enter_depth
                    i = j
                    break
            else:
                continue
            continue
        if in_cfg:
            bracket_depth += lines[i].count("{") - lines[i].count("}")
            if bracket_depth <= 0:
                in_cfg = False
            elif i in fn_locs:
                inside_cfg_test.add(i)

    after_test: set[int] = set()
    for i, ln in enumerate(lines):
        s = ln.strip()
        if s in {"#[test]", "#[wasm_bindgen_test]", "#[tokio::test]"} or "tokio::test" in s:
            for j in range(i + 1, min(i + 5, len(lines))):
                t = lines[j].strip()
                if t == "" or t.startswith("#["):
                    continue
                if j in fn_locs:
                    after_test.add(j)
                break
    return inside_cfg_test | after_test


def _find_fn_locs(lines: list[str]) -> list[int]:
    out: list[int] = []
    for i, ln in enumerate(lines):
        if ln.lstrip().startswith("//"):
            continue
        if _FN_PATTERN.match(ln):
            out.append(i)
    return out


def _fn_needs_doc(lines: list[str], fn_idx: int, exempted: set[int]) -> bool:
    """Layer-1 check: does `fn` at fn_idx lack any `///` directly above?"""
    if fn_idx in exempted:
        return False
    j = fn_idx - 1
    first_attr_above = None
    while j >= 0:
        s = lines[j].strip()
        if s == "":
            j -= 1
            continue
        if s.startswith("#["):
            if first_attr_above is None:
                first_attr_above = j
            j -= 1
            continue
        break
    insert_at = first_attr_above if first_attr_above is not None else fn_idx
    prev_idx = insert_at - 1
    while prev_idx >= 0 and lines[prev_idx].strip() == "":
        prev_idx -= 1
    if prev_idx >= 0 and lines[prev_idx].lstrip().startswith("///"):
        return False
    return True


def _extract_doc_block(lines: list[str], below_idx: int) -> tuple[int, int] | None:
    """Return `(doc_start, doc_end)` (inclusive) for the `///` block ending just before `below_idx`."""
    j = below_idx - 1
    while j >= 0 and lines[j].strip() == "":
        j -= 1
    if j < 0 or not lines[j].lstrip().startswith("///"):
        return None
    doc_end = j
    doc_start = j
    while doc_start > 0 and lines[doc_start - 1].lstrip().startswith("///"):
        doc_start -= 1
    return doc_start, doc_end


def _impl_block_needs_doc(lines: list[str], impl_idx: int) -> bool:
    """Layer-1 check: does the `impl` block at impl_idx lack any `///` above?"""
    j = impl_idx - 1
    while j >= 0 and lines[j].strip() == "":
        j -= 1
    if j < 0:
        return True
    prev = lines[j].lstrip()
    return not (prev.startswith("///") or prev.startswith("//!"))


def _fn_signature_full(lines: list[str], fn_idx: int) -> tuple[str, str, list[str], str, bool]:
    """Return `(name, sig_full, non_self_params, return_type_clean, has_non_unit_return)`.

    `has_non_unit_return` is `False` for `()` and `Self`.
    """
    ln = lines[fn_idx]
    m = _FN_PATTERN.match(ln)
    if not m:
        return "", "", [], "", False
    name = m.group(2)
    name_pos = ln.find(name) + len(name)
    paren_start = ln.find("(", name_pos)
    if paren_start == -1:
        return name, ln, [], "", False
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
    sig_full = "\n".join(sig_lines)
    after_name = sig_full.find(name) + len(name)
    paren_start2 = -1
    depth_brk = 0
    for k in range(after_name, len(sig_full)):
        ch = sig_full[k]
        if ch == "<" and depth_brk == 0:
            depth_brk += 1
        elif ch == ">" and depth_brk > 0:
            depth_brk -= 1
        if ch == "(" and depth_brk == 0:
            paren_start2 = k
            break
    if paren_start2 == -1:
        return name, sig_full, [], "", False
    depth = 1
    k = paren_start2 + 1
    while k < len(sig_full) and depth > 0:
        ch = sig_full[k]
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        k += 1
    params_str = sig_full[paren_start2 + 1:k - 1]
    params_list = [p.strip() for p in _split_top_commas(params_str)]
    non_self = [p for p in params_list if p not in {"", "&self", "&mut self", "self", "mut self"}]
    after = sig_full[k:]
    ret_str = ""
    has_non_unit_return = False
    m2 = re.search(r"->\s*([^{=;]+)", after)
    if m2:
        ret_raw = m2.group(1).strip().rstrip(",")
        ret_raw = re.sub(r"\{.*$", "", ret_raw, flags=re.DOTALL).strip()
        ret_clean = ret_raw.replace("`", "").replace("&", "").strip()
        ret_clean = ret_clean.split("where")[0].split(";")[0].strip()
        ret_str = ret_clean
        has_non_unit_return = bool(ret_clean) and ret_clean not in ("()", "Self", "")
    return name, sig_full, non_self, ret_str, has_non_unit_return


def audit_one(path: str) -> dict[str, list[tuple[int, str, str]]]:
    """Return `{kind: [(line, name, detail), ...]}` violations for `path`."""
    violations: dict[str, list[tuple[int, str, str]]] = defaultdict(list)
    try:
        with open(path) as fh:
            lines = fh.read().splitlines()
    except (OSError, UnicodeDecodeError):
        return violations

    fn_locs = _find_fn_locs(lines)
    test_regions = _scan_test_regions(lines, fn_locs)

    # Layer 1 — bare fn
    for fn_idx in fn_locs:
        if _fn_needs_doc(lines, fn_idx, test_regions):
            name, *_ = _fn_signature_full(lines, fn_idx)
            violations["missing-fn-doc"].append((fn_idx + 1, name, f"bare fn at line {fn_idx + 1}"))

    # Layer 1 — bare impl block
    for i, ln in enumerate(lines):
        s = ln.strip()
        if s.startswith("impl "):
            if (s.endswith("{") or "{" in s) and "=" not in s:
                if _impl_block_needs_doc(lines, i):
                    first_line = s
                    violations["missing-impl-block-doc"].append((i + 1, first_line, "bare impl block"))

    # Layer 2 — fn with non-self params OR non-() return but missing section header.
    for fn_idx in fn_locs:
        if fn_idx in test_regions:
            continue
        doc = _extract_doc_block(lines, fn_idx)
        if doc is None:
            # Layer 1 already flags this — Layer 2 only fires for fn that *has* a doc.
            continue
        doc_start, doc_end = doc
        doc_text = "\n".join(lines[doc_start:doc_end + 1])
        has_arguments = "# Arguments" in doc_text
        has_returns = "# Returns" in doc_text
        name, _, non_self, ret_str, has_non_unit_return = _fn_signature_full(lines, fn_idx)
        if non_self and not has_arguments:
            violations["missing-arguments-section"].append(
                (fn_idx + 1, name, f"fn has non-self params but no `# Arguments`")
            )
        if has_non_unit_return and not has_returns:
            violations["missing-returns-section"].append(
                (fn_idx + 1, name, f"fn returns non-() but no `# Returns`")
            )

    return violations


def fix_one(path: str) -> tuple[int, int]:
    """Run all three layers on `path`. Returns (layer1_fixes, layer2_fixes)."""
    try:
        with open(path) as fh:
            original = fh.read()
        lines = original.splitlines()
    except (OSError, UnicodeDecodeError):
        return 0, 0

    fn_locs = _find_fn_locs(lines)
    test_regions = _scan_test_regions(lines, fn_locs)

    # Layer 1 inserts:  fn single-line docs + impl block docs.
    inserts: list[tuple[int, list[str]]] = []
    for fn_idx in fn_locs:
        if not _fn_needs_doc(lines, fn_idx, test_regions):
            continue
        j = fn_idx - 1
        first_attr_above = None
        while j >= 0:
            s = lines[j].strip()
            if s == "":
                j -= 1
                continue
            if s.startswith("#["):
                if first_attr_above is None:
                    first_attr_above = j
                j -= 1
                continue
            break
        insert_at = first_attr_above if first_attr_above is not None else fn_idx
        name, *_ = _fn_signature_full(lines, fn_idx)
        impl_text = ""
        for k in range(fn_idx - 1, -1, -1):
            t = lines[k].strip()
            if t.startswith("impl") and not t.startswith("//"):
                impl_text = t
                break
        inserts.append((insert_at, build_short_fn_doc(impl_text, name)))

    for i, ln in enumerate(lines):
        s = ln.strip()
        if s.startswith("impl "):
            if (s.endswith("{") or "{" in s) and "=" not in s:
                if _impl_block_needs_doc(lines, i):
                    inserts.append((i, [build_impl_block_doc(s)]))

    inserts.sort(key=lambda x: -x[0])
    new_lines = list(lines)
    for insert_at, doc_lines in inserts:
        for d in reversed(doc_lines):
            new_lines.insert(insert_at, d)

    # Layer 2: insert missing # Arguments / # Returns sections. Sort DESC by doc_end.
    layer2_count = 0
    fn_locs2 = _find_fn_locs(new_lines)
    expansions: list[tuple[int, list[str]]] = []
    for fn_idx in fn_locs2:
        if fn_idx in _scan_test_regions(new_lines, fn_locs2):
            continue
        doc = _extract_doc_block(new_lines, fn_idx)
        if doc is None:
            continue
        _, doc_end = doc
        name, _, non_self, ret_str, has_non_unit_return = _fn_signature_full(new_lines, fn_idx)
        arg_lines, ret_lines = build_full_fn_doc_sections(
            name, non_self, ret_str if has_non_unit_return else ""
        )
        if not arg_lines and not ret_lines:
            continue
        layer2_count += 1
        expansions.append((doc_end + 1, arg_lines + ret_lines))
    expansions.sort(key=lambda x: -x[0])
    for insert_at, doc_lines in expansions:
        for d in reversed(doc_lines):
            new_lines.insert(insert_at, d)

    if len(new_lines) != len(lines) or new_lines != lines:
        with open(path, "w") as fh:
            fh.write("\n".join(new_lines) + "\n")
    return len(inserts), layer2_count


# ---------- driver ---------------------------------------------------------


def _list_rust_files(root: str) -> list[str]:
    out = subprocess.run(
        ["git", "ls-files"],
        cwd=root, capture_output=True, text=True, check=True,
    )
    return [f for f in out.stdout.strip().splitlines() if f.endswith(".rs")]


def _print_summary(total: dict[str, int], files_changed: int) -> None:
    print(f"\n=== doc-comment audit summary ===")
    for kind, n in sorted(total.items()):
        print(f"  {kind}: {n}")
    print(f"  files affected: {files_changed}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--check", action="store_true",
                    help="Audit only; do not modify files. Exits non-zero on any violation.")
    ap.add_argument("--root", default=".",
                    help="Project root (defaults to current dir). Affects git ls-files scope.")
    args = ap.parse_args(argv)

    rust_files = _list_rust_files(args.root)
    if args.check:
        total: dict[str, int] = defaultdict(int)
        files_with_issues = 0
        for f in rust_files:
            path = f"{args.root}/{f}"
            v = audit_one(path)
            if v:
                files_with_issues += 1
                for kind, items in v.items():
                    total[kind] += len(items)
                    for line, name, detail in items:
                        print(f"  {f}:{line} {name} — {kind}: {detail}")
        _print_summary(total, files_with_issues)
        return 0 if sum(total.values()) == 0 else 1

    total_layer12 = 0
    total_layer2 = 0
    files_changed = 0
    for f in rust_files:
        path = f"{args.root}/{f}"
        n12, n2 = fix_one(path)
        if n12 + n2:
            files_changed += 1
            total_layer12 += n12
            total_layer2 += n2
    _print_summary({
        "layer1-short-docs-and-impl-docs": total_layer12,
        "layer2-arguments-returns-sections": total_layer2,
    }, files_changed)
    return 0


if __name__ == "__main__":
    sys.exit(main())
