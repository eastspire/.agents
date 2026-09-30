#!/usr/bin/env python3
"""§6.1 / §6.3 / §6.4 — module imports are centralized in lib.rs / mod.rs.

Three sub-rules, each owned by a different file kind:

  lib.rs    a private `use` of a std / external / sibling-crate item must be
            `pub use` instead. A private import cannot be seen by any sub-file,
            so a sub-file that needs the same type has to re-import it, which
            §6.4 forbids. Publishing the import at the crate root is what lets
            `use super::*;` carry the symbol down.

  mod.rs    the strict three-stage layout, no comments and no blank-line
            separators anywhere in the body:
              1. `mod r#xxx;` declarations
              2. `pub use {...};` / `pub(crate) use {...};` re-exports
              3. a single trailing `use super::*;`
            (keyword files are declared with raw identifiers, `mod r#fn;`)

  sub-file  (fn.rs / struct.rs / impl.rs / const.rs / enum.rs / trait.rs /
            type.rs / static.rs) may have NO `use` at all, or exactly
            `use super::*;` — nothing else. Any other import (a long path, a
            specific `super::` path, a glob of an external crate) is a
            violation, because the parent already re-exported everything the
            sub-file is allowed to name.

§6.4 additionally forbids a sub-file from re-importing a symbol the parent
already re-exported; that is covered by the same "only `use super::*;`" rule.

Not reported: comments and blank lines in lib.rs (only mod.rs is comment-free
by the standard), and `#[cfg(test)]` blocks.

Output contract: one violation per line, then a summary line beginning
`=== module-imports centralized:`.

Exit code: 0 = compliant, 1 = violations, 2 = usage error.
"""

import re
import subprocess
import sys
from pathlib import Path

KEYWORD_FILES = {
    "fn.rs", "struct.rs", "impl.rs", "const.rs", "enum.rs", "trait.rs",
    "type.rs", "static.rs", "macro.rs",
}
RUST_KEYWORDS = {
    "fn", "struct", "impl", "const", "enum", "trait", "type", "static",
    "macro", "mod", "let", "match", "move", "ref", "box", "use", "pub", "crate",
    "self", "super", "async", "await", "dyn", "union", "macro_rules",
}

USE = re.compile(r"^\s*((?:pub(?:\([^)]*\))?\s+)?)use\s+(.*?);\s*$")
MOD_DECL = re.compile(r"^\s*(?:pub(?:\([^)]*\))?\s+)?mod\s+(r#)?(\w+)\s*;")
CFG_TEST = re.compile(r"^\s*#\[cfg\(test\)\]")
SUPER_STAR = re.compile(r"^\s*use\s+super\s*::\s*\*\s*;\s*$")


def list_rs_files(root: Path) -> list[Path]:
    result = subprocess.run(
        [
            "find", str(root), "-name", "*.rs",
            "-not", "-path", "*/target/*",
            "-not", "-path", "*/.cargo/registry/*",
        ],
        capture_output=True, text=True,
    )
    return [Path(line) for line in result.stdout.splitlines() if line.strip()]


def _skip_whole_block(lines: list[str], idx: int) -> int:
    j = idx
    while j < len(lines) and "{" not in lines[j]:
        j += 1
    if j >= len(lines):
        return len(lines)
    depth, k = 0, j
    while k < len(lines):
        depth += lines[k].count("{") - lines[k].count("}")
        if depth == 0:
            return k
        k += 1
    return len(lines) - 1


def _is_under_src(path: Path) -> bool:
    return "src" in path.parts


def _is_mod_rs(path: Path) -> bool:
    return path.name == "mod.rs"


def _is_keyword_file(path: Path) -> bool:
    return path.name in KEYWORD_FILES


def _workspace_member_names(path: Path) -> set[str]:
    """Crate names of every sibling in the same workspace.

    §6.1 group 6 explicitly allows a private `use current_crate::*;` when the
    current crate is a workspace member, so glob-importing a sibling privately
    is the documented spelling, not a violation.

    The walk must find the manifest that actually declares `[workspace]`, not
    merely the first Cargo.toml above the file: a member crate has its own and
    would otherwise stop the search before the root is ever reached.
    """
    names: set[str] = set()
    for parent in path.parents:
        candidate = parent / "Cargo.toml"
        if not candidate.is_file():
            continue
        try:
            text = candidate.read_text()
        except (OSError, UnicodeDecodeError) as exc:
            print(f"error: cannot read {candidate}: {exc}", file=sys.stderr)
            continue
        if "[workspace]" not in text:
            continue  # a member manifest — keep walking up
        for entry in _workspace_members(text):
            member_dir = parent / entry
            # A member is named by its [package].name, which is not always the
            # directory's last segment (euv/engine is the `euv-engine` crate).
            # Record both so either spelling is recognised.
            names.add(Path(entry).name)
            declared = _package_name(member_dir / "Cargo.toml")
            if declared:
                names.add(declared)
        # the workspace root's OWN [package] name is a sibling too — a root
        # package is not listed in `members` but every member depends on it.
        root_name = _package_name(candidate)
        if root_name:
            names.add(root_name)
        names.add(parent.name)
        return names
    return names


def _package_name(manifest_path: Path) -> str:
    try:
        manifest_text = manifest_path.read_text()
    except (OSError, UnicodeDecodeError):
        return ""
    in_package = False
    for raw in manifest_text.splitlines():
        line = raw.strip()
        if line.startswith("["):
            in_package = line == "[package]"
            continue
        if not in_package or not line or line.startswith("#"):
            continue
        if line.startswith("name"):
            _, _, value = line.partition("=")
            return value.strip().strip('"').strip("'")
    return ""


def _workspace_members(manifest_text: str) -> list[str]:
    """Every `members` entry, including a multi-line TOML array.

    A line-based split mangles `members = [\n  "core",\n  "engine",\n]` into
    a first element of `["core`, so the array is collected as raw text between
    the brackets instead.
    """
    match = re.search(r"^\s*members\s*=\s*\[(.*?)\]", manifest_text, re.S | re.M)
    if match is None:
        return []
    return re.findall(r"[\"`]([^\"`]+)[\"`]", match.group(1))


def audit_lib_rs(path: Path, lines: list[str]) -> list[str]:
    """Private `use` of a non-local item must be `pub use` (§6.1)."""
    violations = []
    siblings = _workspace_member_names(path)
    for idx, raw in enumerate(lines, 1):
        m = USE.match(raw)
        if m is None:
            continue
        visibility, body = m.group(1).strip(), m.group(2).strip()
        if visibility:  # pub / pub(crate) — already published
            continue
        first = body.split("::", 1)[0].strip().strip("{}").strip()
        # `use self::` / `use super::` / `use crate::` are local to this module
        if first in ("self", "super", "crate"):
            continue
        # §6.1 group 6: a private glob of a workspace member is the documented
        # spelling, not a violation.
        if first in siblings:
            continue
        violations.append(
            f"{path}:{idx}: private `use {body}` in lib.rs cannot reach any "
            f"sub-file (§6.1); publish it as `pub use {body};` so sub-files get "
            f"it through `use super::*;`"
        )
    return violations


def audit_mod_rs(path: Path, lines: list[str]) -> list[str]:
    """Strict three-stage layout, no comments, no blank separators (§6.2)."""
    violations = []
    stage = 1
    seen_stage2 = False
    for idx, raw in enumerate(lines, 1):
        stripped = raw.strip()
        if not stripped:
            # §6.2 / templates/mod-rs.md: blank lines SEPARATE the three stages
            # (that is what the canonical template looks like). What is
            # forbidden is a blank line INSIDE one stage — two `mod` lines
            # split by a blank line, or two re-exports split by one.
            prev = next(
                (l.strip() for l in reversed(lines[:idx]) if l.strip()), ""
            )
            prev_is_mod = bool(MOD_DECL.match(prev))
            nxt = next(
                (l.strip() for l in lines[idx:] if l.strip()), ""
            )
            next_is_mod = bool(MOD_DECL.match(nxt))
            if prev_is_mod and next_is_mod:
                violations.append(
                    f"{path}:{idx}: blank line inside the `mod` block; §6.2 "
                    f"stage 1 keeps every `mod xxx;` touching (blank lines "
                    f"belong BETWEEN the three stages, not within one)"
                )
            continue
        if stripped.startswith("//"):
            if stripped.startswith("///") and idx == 1:
                continue  # the crate-level doc block is a mod.rs header
            violations.append(
                f"{path}:{idx}: comment in a mod.rs body is forbidden (§6.2); "
                f"the file carries only `mod` / `pub use` / `use super::*;`"
            )
            continue
        if stage == 0 and (USE.match(stripped) or MOD_DECL.match(stripped)):
            stage = 1
        m = MOD_DECL.match(stripped)
        if m is not None:
            name = m.group(2)
            if name in RUST_KEYWORDS and not m.group(1):
                violations.append(
                    f"{path}:{idx}: `mod {name};` must be a raw identifier "
                    f"(§6.2): write `mod r#{name};`"
                )
            if seen_stage2:
                violations.append(
                    f"{path}:{idx}: `mod` declaration after a re-export stage; "
                    f"stage 1 (mod) must precede stage 2 (pub use) (§6.2)"
                )
            continue
        m = USE.match(stripped)
        if m is None:
            continue
        if SUPER_STAR.match(stripped):
            continue
        if m.group(1).strip():  # pub use / pub(crate) use
            seen_stage2 = True
            continue
        violations.append(
            f"{path}:{idx}: a re-export in a mod.rs must be `pub use` or "
            f"`pub(crate) use` (§6.2); found `{stripped[:70]}`"
        )
    return violations


def audit_sub_file(path: Path, lines: list[str]) -> list[str]:
    """Only `use super::*;` is allowed, and only once (§6.3 / §6.4)."""
    violations = []
    idx, total = 0, len(lines)
    while idx < total:
        if CFG_TEST.match(lines[idx]):
            idx = _skip_whole_block(lines, idx) + 1
            continue
        m = USE.match(lines[idx])
        if m is None:
            idx += 1
            continue
        if SUPER_STAR.match(lines[idx]):
            idx += 1
            continue
        violations.append(
            f"{path}:{idx + 1}: a keyword sub-file may only import "
            f"`use super::*;` (§6.3/§6.4) — the parent already re-exported "
            f"everything nameable here; found `{lines[idx].strip()[:70]}`"
        )
        idx += 1
    return violations


def audit_one(path: Path) -> list[str]:
    try:
        lines = path.read_text().splitlines()
    except (OSError, UnicodeDecodeError):
        return []
    if "tests" in path.parts or not _is_under_src(path):
        return []
    if _is_mod_rs(path):
        return audit_mod_rs(path, lines)
    if path.name == "lib.rs":
        return audit_lib_rs(path, lines)
    if _is_keyword_file(path):
        return audit_sub_file(path, lines)
    return []


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    if not root.is_dir():
        print(f"error: {root} is not a directory", file=sys.stderr)
        return 2
    all_violations: list[str] = []
    file_count = 0
    for path in list_rs_files(root):
        found = audit_one(path)
        if found:
            file_count += 1
            all_violations.extend(found)
    for violation in all_violations:
        print(violation)
    if not all_violations:
        print("\n=== module-imports centralized: 0 violation(s) in 0 file(s) ===")
        return 0
    print(
        f"\n=== module-imports centralized: {len(all_violations)} violation(s) "
        f"in {file_count} file(s) ==="
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
