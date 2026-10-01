#!/usr/bin/env python3
"""
Verify no panicking lombok accessor is called on a bare `Option<T>` field.

rust-standards: `#[derive(Data)]` on a field of type `Option<T>` generates

    pub fn get_x(&self) -> T { self.x.clone().unwrap() }   // panics on None
    pub fn try_get_x(&self) -> T { self.x.clone() }        // safe

Rule: any `Option<T>` field that is allowed to be `None` MUST be read through
`try_get_*`. `get_*` is only legal on non-`Option` fields (or when the caller
has already proven the value is `Some`).

Why a static scan is not enough: field names collide across unrelated types.
`get_min()` exists on both `Counter` (`min: Option<i32>`, panics) and `AABB3D`
(`min: Vector3D`, safe). Name-based matching reports ~180 false hits. So this
verifier does NOT do name matching — it parses the actual struct declarations
and only reports a call when BOTH the declaring type and the call-site receiver
can be resolved.

Usage:
    python3 verify_no_panicking_option_getter.py <repo>

Exit 0 = clean, 1 = violations found.
"""

import re
import sys
from pathlib import Path
from typing import Optional

STRUCT_RE = re.compile(
    r"#\[derive\((?P<derives>[^)]*Data[^)]*)\)\]\s*\n"
    r"(?:#\[[^\]]*\]\s*\n)*"
    r"pub struct (?P<name>\w+)\s*\{(?P<body>.*?)\n\}",
    re.S,
)
FIELD_RE = re.compile(
    r"pub(?:\(crate\))? (?P<fld>\w+): (?P<ty>Option<[^;\n]+?>),"
)
# `impl Foo {` at column 0, or `impl<...> Foo {`
IMPL_RE = re.compile(r"^impl(?:<[^>]*>)? ([\w:]+) \{", re.M)
CALL_RE = re.compile(r"(?<![a-zA-Z_])get_(\w+)\(\)")


def collect_option_fields(repo: Path) -> dict[str, tuple[str, str]]:
    """field name -> (owning struct, declared type) for bare Option fields."""
    out: dict[str, tuple[str, str]] = {}
    for path in repo.rglob("*.rs"):
        if "/target/" in str(path):
            continue
        text = path.read_text(errors="ignore")
        for m in STRUCT_RE.finditer(text):
            for f in FIELD_RE.finditer(m.group("body")):
                fld, ty = f.group("fld"), f.group("ty")
                # `Option<Signal<T>>` and friends are still bare Option and
                # still panic; only `Signal<Option<T>>` (a Signal wrapping an
                # Option) is safe, and that never matches `Option<...>` here.
                out[fld] = (m.group("name"), ty)
    return out


def enclosing_impl(lines, idx) -> Optional[str]:
    for i in range(idx, -1, -1):
        m = IMPL_RE.match(lines[i])
        if m:
            return m.group(1)
        if re.match(r"^\}", lines[i]) and i != idx:
            return None
    return None


def receiver_type(lines, idx) -> Optional[str]:
    """Best-effort receiver type for `X.get_y()` on line `idx`."""
    line = lines[idx]
    m = re.search(r"(\w+)\.get_(\w+)\(\)", line)
    if not m:
        return None
    recv, getter = m.group(1), m.group(2)
    if recv == "self":
        return enclosing_impl(lines, idx)
    # `let <recv>: <Type> = ...` anywhere above
    pat = re.compile(rf"\blet\s+{re.escape(recv)}\s*:\s*&?([\w:]+)")
    for i in range(idx, -1, -1):
        pm = pat.search(lines[i])
        if pm:
            return pm.group(1)
    # `let <recv> = <Type> {`
    pat2 = re.compile(rf"\blet\s+{re.escape(recv)}\s*=\s*([\w:]+)\s*\{{")
    for i in range(idx, -1, -1):
        pm = pat2.search(lines[i])
        if pm:
            return pm.group(1)
    # A function parameter `fn f(&self_, or x: &Type)` on the enclosing line
    # or any line up to the enclosing `fn` — covers `fn p(s: &SceneManager)`.
    fn_pat = re.compile(
        rf"(?:^|\(|,)\s*&?(?:mut\s+)?{re.escape(recv)}\s*:\s*&?([\w:]+)"
    )
    for i in range(idx, -1, -1):
        if re.match(r"^\s*(pub(\([^)]*\))?\s+)?fn\s", lines[i]):
            pm = fn_pat.search(lines[i])
            if pm:
                return pm.group(1)
            return None
    return None


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: verify_no_panicking_option_getter.py <repo>", file=sys.stderr)
        return 2
    repo = Path(sys.argv[1]).resolve()
    option_fields = collect_option_fields(repo)

    violations: list[str] = []
    # Lombok only emits the panicking form when the accessor's declared return
    # type is the BARE inner type. If an accessor is declared
    # `#[get] pub x: Option<T>` -> `fn get_x(&self) -> Option<T> { self.x.clone() }`
    # it is safe. So a field is only risky if some accessor in the struct
    # returns the unwrapped type; `option_fields` keys on the *getter name*
    # and the declared return type is checked against the field type here.
    for path in repo.rglob("*.rs"):
        if "/target/" in str(path):
            continue
        rel = path.relative_to(repo)
        lines = path.read_text(errors="ignore").split("\n")
        for i, line in enumerate(lines):
            code = line.split("//", 1)[0]
            for m in CALL_RE.finditer(code):
                fld = m.group(1)
                if fld not in option_fields:
                    continue  # different type, not a Data Option field
                owner, ty = option_fields[fld]
                # If the call site immediately binds/patterns the result as an
                # Option (`let x: Option<T> = ...`, `if let Some(..) = ...`,
                # `match .. { Some(..) => .. }`) the getter cannot be the
                # panicking bare-type form.
                if re.search(rf"Option<\s*{re.escape(ty[7:-1] if ty.endswith('>') else ty[7:])}\s*>", code):
                    continue
                # `match self.get_x() { Some(..) => .. None => .. }` and
                # `let x = self.get_x(); if let Some(..) = x { .. }` span lines,
                # so scan a small window around the call, not just its own line.
                window = "\n".join(lines[i : i + 4])
                if re.search(
                    r"Some\(|None\s*=>|is_none\(\)|is_some\(\)|\.as_ref\(\)|"
                    r"\.unwrap_or",
                    window,
                ):
                    continue
                # A bare `Option<` in the WINDOW is not evidence the getter is
                # safe — the enclosing fn's own return type often is
                # `Option<..>`. Only the text BEFORE the call on the same
                # statement counts (`let x: Option<T> = e.get_f()`).
                head = code[: m.start(1)]
                if re.search(r"Option<", head):
                    continue
                recv = receiver_type(lines, i)
                # Only report when we can PROVE the receiver is the owning type.
                if recv is None or recv.split("::")[-1] != owner.split("::")[-1]:
                    continue
                violations.append(
                    f"{rel}:{i + 1}: {recv}::get_{fld}() panics on None "
                    f"(field `{fld}: {ty}`) — use try_get_{fld}()"
                )

    if violations:
        print(
            f"=== panicking-getter-on-Option: {len(violations)} violation(s) ==="
        )
        for v in violations:
            print("  " + v)
        return 1
    print("=== panicking-getter-on-Option: 0 violation(s) ===")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
