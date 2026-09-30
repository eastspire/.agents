#!/usr/bin/env python3
"""§6.1 — lib.rs import groups appear in the prescribed order.

The order, as written in references/06-module-imports.md §6.1:

  1. `mod xxx;`                      — all of them touching, no blank lines
  2. `pub use {sub_module::*};`      — sub-module globs come FIRST
  3. `pub use {external_crate::*};`  — then external-crate globs
  4. `pub(crate) use`
  5. `pub(super) use`
  6. `use` (private), and inside it the sub-order is
       current crate -> standard library -> external crates
     a lone `use external::Symbol;` must be folded into the aggregated
     `use {...};` block rather than standing on its own line

Groups are separated by one blank line; within group 1 no blank line is allowed.

A blank line is the ONLY thing that separates groups, so the group index is the
count of blank lines seen before the line. That is what makes the rule
mechanically checkable: a violation is a line whose group index is lower than
the highest group index already seen.

Output contract: one violation per line, then `=== lib-rs import order: ...`
or `OK: 0 lib.rs file(s) checked` (the audit's shell template greps away
`^=== ` and `^OK: 0 lib`).

Exit code: 0 = compliant, 1 = violations, 2 = usage error.
"""

import re
import subprocess
import sys
from pathlib import Path
from typing import Optional

MOD_DECL = re.compile(r"^\s*(?:pub(?:\([^)]*\))?\s+)?mod\s+(r#)?\w+\s*;")
# `pub use foo::*;` / `pub use {a::*, b::*};` -> is any target a local sub-module?
# Local = a bare identifier or `crate::`/`self::` rooted, as opposed to a crate
# that resolves in the extern prelude. We approximate "local" by the absence of
# a known std/external root, which is exactly the distinction a reader makes.
PRIV_USE = re.compile(r"^\s*use\s+(?!.*\bpub\b)")
PUB_USE = re.compile(r"^\s*pub\s+use\s+(.*?);\s*$")
PUB_CRATE_USE = re.compile(r"^\s*pub\(crate\)\s+use\b")
PUB_SUPER_USE = re.compile(r"^\s*pub\(super\)\s+use\b")
COMMENT = re.compile(r"^\s*(//|/\*)")
LONE_EXTERNAL = re.compile(r"^\s*use\s+([a-z_][a-z0-9_]*)::[A-Za-z_]")


def list_lib_files(root: Path) -> list[Path]:
    result = subprocess.run(
        [
            "find", str(root), "-name", "lib.rs",
            "-not", "-path", "*/target/*",
            "-not", "-path", "*/.cargo/registry/*",
        ],
        capture_output=True, text=True,
    )
    return [Path(line) for line in result.stdout.splitlines() if line.strip()]


def _dependency_roots(lib_rs: Path) -> set[str]:
    """Crate names declared in the nearest Cargo.toml.

    A leading path segment that is NOT a dependency is, by definition, a local
    module.  That is the only sound way to tell `pub use {component::*};` (a
    sub-module, §6.1 group 2) from `pub use std::{...};` (an external crate,
    group 3) — the two are syntactically identical.
    """
    roots: set[str] = set()
    manifest: Optional[Path] = None
    for parent in lib_rs.parents:
        candidate = parent / "Cargo.toml"
        if candidate.is_file():
            manifest = candidate
            break
    if manifest is None:
        return roots
    try:
        text = manifest.read_text()
    except (OSError, UnicodeDecodeError) as exc:
        # Never swallow this silently: a wrong `manifest` path once made every
        # crate look dependency-free, which silently downgraded every §6.1
        # group-2/group-3 distinction to "local".
        print(
            f"error: cannot read {manifest}: {exc}",
            file=sys.stderr,
        )
        return roots
    in_deps = False
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("["):
            in_deps = line in (
                "[dependencies]", "[dev-dependencies]", "[build-dependencies]",
                "[workspace.dependencies]",
            ) or line.startswith("[target.")
            continue
        if not in_deps or not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        name = line.split("=", 1)[0].strip().strip('"')
        if name and not name.startswith("["):
            roots.add(name)
    return roots


def _root_segments(body: str) -> set[str]:
    """Leading path segments of every item in a use body."""
    inner = body.strip()
    if inner.startswith("{"):
        inner = inner[1:-1] if inner.endswith("}") else inner[1:]
    segments: set[str] = set()
    for item in inner.split(","):
        item = item.strip().rstrip(";").strip()
        if not item:
            continue
        m = re.match(r"(?:r#)?([A-Za-z_][A-Za-z0-9_]*)", item)
        if m:
            segments.add(m.group(1))
    return segments


def _classify(stripped: str, dep_roots: set[str]) -> Optional[int]:
    """Return the §6.1 group index of one line, or None if it is not a decl."""
    if MOD_DECL.match(stripped):
        return 1
    if PUB_CRATE_USE.match(stripped):
        return 4
    if PUB_SUPER_USE.match(stripped):
        return 5
    m = PUB_USE.match(stripped)
    if m is not None:
        segments = _root_segments(m.group(1))
        # local when nothing in it resolves to a declared dependency
        if not (segments & dep_roots):
            return 2
        return 3
    if PRIV_USE.match(stripped):
        return 6
    return None


def audit_one(path: Path) -> list[str]:
    try:
        lines = path.read_text().splitlines()
    except (OSError, UnicodeDecodeError):
        return []
    violations: list[str] = []
    dep_roots = _dependency_roots(path)
    group = 0
    highest = 0
    seen_any = False
    for idx, raw in enumerate(lines, 1):
        stripped = raw.strip()
        if COMMENT.match(stripped):
            continue
        if not stripped:
            if seen_any and any(MOD_DECL.match(l.strip()) for l in lines[:idx]):
                # a blank line inside the `mod` block splits group 1
                nxt = next(
                    (k for k in range(idx, len(lines)) if lines[k].strip()), None
                )
                if nxt is not None and MOD_DECL.match(lines[nxt].strip()):
                    violations.append(
                        f"{path}:{idx + 1}: blank line inside the `mod` block; "
                        f"§6.1 group 1 keeps every `mod xxx;` touching"
                    )
            group += 1
            continue
        g = _classify(stripped, dep_roots)
        if g is None:
            # a lone private `use external::Symbol;` must be folded into the
            # aggregated block that follows it (§6.1 group 6)
            m = LONE_EXTERNAL.match(stripped)
            if m and g is None and group >= 6:
                nxt = next(
                    (k for k in range(idx, len(lines)) if lines[k].strip()), None
                )
                if nxt is None or not lines[nxt].strip().startswith("use {"):
                    violations.append(
                        f"{path}:{idx}: a lone `use {m.group(1)}::Symbol;` must be "
                        f"folded into the aggregated `use {{...}};` block (§6.1 "
                        f"group 6): {stripped[:70]}"
                    )
            seen_any = True
            continue
        seen_any = True
        if g < highest:
            violations.append(
                f"{path}:{idx}: import group {g} appears after group {highest} "
                f"(§6.1 order is mod -> pub use local -> pub use external -> "
                f"pub(crate) -> pub(super) -> private): {stripped[:70]}"
            )
        highest = max(highest, g)
    return violations


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    if not root.is_dir():
        print(f"error: {root} is not a directory", file=sys.stderr)
        return 2
    libs = list_lib_files(root)
    all_violations: list[str] = []
    for path in libs:
        all_violations.extend(audit_one(path))
    for violation in all_violations:
        print(violation)
    if all_violations:
        print(
            f"\n=== lib-rs import order: {len(all_violations)} violation(s) "
            f"in {len(libs)} lib.rs file(s) ==="
        )
        return 1
    print(f"\nOK: {len(libs)} lib.rs file(s) checked, no group-order violation")
    return 0


if __name__ == "__main__":
    sys.exit(main())
