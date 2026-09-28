#!/usr/bin/env python3
"""
§1.3d verifier: a Rust code file MUST NOT live at the same level as directories.

Rule (2026-09-28 user directive, verbatim: "如果 rust 代码文件同级有目录,
需要报错提示代码文件不能和目录在同一级,注意 lib.rs main.rs build.rs
mod.rs 这些除外"):

    A directory that holds at least one sub-directory MUST NOT also hold
    `.rs` code files, except for the four module-entry files:

        lib.rs   — crate root entry
        main.rs  — bin entry
        build.rs — cargo build script (lives at crate root by convention)
        mod.rs   — module entry, its job IS to declare sub-modules

    Everything else (`const.rs` / `fn.rs` / `impl.rs` / `struct.rs` /
    `enum.rs` / `trait.rs` / `type.rs` / `static.rs`, plus any non-keyword
    file such as `inline.rs`) is a violation when a sub-directory sits
    beside it.

Why:
  A keyword file is a *leaf* of the module tree: `mod r#fn;` in `mod.rs`
  resolves to `<dir>/fn.rs` and nothing else.  Once `<dir>/` also owns
  sub-modules, the directory stops being a leaf and the reader has to
  decide whether `foo.rs` belongs to the parent scope or is a namespace
  peer of `foo/` — two conventions for one level of the tree.  The four
  entry files are exempt because their entire purpose is to be the
  parent of sub-modules.

Detection:
  Walk the tree.  For every directory:
    code_files = [*.rs] minus {lib.rs, main.rs, build.rs, mod.rs}
    sub_dirs   = visible sub-directories, excluding SKIP_DIR_NAMES
  If both are non-empty -> ONE violation for that directory, naming every
  offending file and every sibling sub-directory.

Skipped entirely (never scanned, never reported):
  - directory names in SKIP_DIR_NAMES (target / .git / node_modules / ...)
  - dot-directories (`.github`, `.cargo`, ...)
  - anything git already ignores (a path listed in .gitignore is not part
    of the project: `crate-cli/tmp/` holds scratch crates whose layout no
    commit can ever contain)

Exit code: 0 = compliant, 1 = violations found, 2 = usage error.

Usage:
    python3 verify_no_sibling_dirs.py [ROOT]
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


# Module-entry files: the ONLY `.rs` files allowed beside sub-directories.
EXEMPT_FILE_NAMES = frozenset({"lib.rs", "main.rs", "build.rs", "mod.rs"})

SKIP_DIR_NAMES = {
    ".git", "target", ".cargo", "node_modules", ".venv", "venv", "dist",
    "build", ".idea", ".vscode", "out", "__pycache__",
}

MAX_LISTED = 8


def _visible_sub_dirs(directory: Path, entries: list[str]) -> list[str]:
    """Sub-directory names of `directory` that count as module children."""
    names: list[str] = []
    for entry in sorted(entries):
        if not (directory / entry).is_dir():
            continue
        if entry in SKIP_DIR_NAMES or entry.startswith("."):
            continue
        names.append(entry)
    return names


def audit_one_dir(directory: Path) -> list[str]:
    """Return violations for a single directory (empty list = compliant)."""
    try:
        entries = sorted(os.listdir(directory))
    except (OSError, PermissionError):
        return []
    sub_dirs = _visible_sub_dirs(directory, entries)
    if not sub_dirs:
        return []
    code_files = sorted(
        entry
        for entry in entries
        if entry.endswith(".rs")
        and entry not in EXEMPT_FILE_NAMES
        and (directory / entry).is_file()
    )
    if not code_files:
        return []

    files_label = _label(code_files)
    dirs_label = _label(sub_dirs)
    return [
        f"{directory}: code file(s) {files_label} cannot share a level with "
        f"sub-directory(ies) {dirs_label} (§1.3d); move each file into its "
        f"own sub-module directory (e.g. `{code_files[0][: -len('.rs')]}/"
        f"{code_files[0]}`) — only lib.rs / main.rs / build.rs / mod.rs "
        f"are allowed beside directories"
    ]


def _label(names: list[str]) -> str:
    shown = ", ".join(names[:MAX_LISTED])
    if len(names) > MAX_LISTED:
        shown += f", ... (+{len(names) - MAX_LISTED} more)"
    return f"[{shown}]"


def _dirs_to_check(root: Path) -> list[Path]:
    """Every candidate directory under root, git-ignored ones dropped."""
    candidates: list[Path] = []
    for dirpath, dirnames, _ in os.walk(root, followlinks=False):
        dirnames[:] = sorted(
            name
            for name in dirnames
            if name not in SKIP_DIR_NAMES and not name.startswith(".")
        )
        candidates.append(Path(dirpath))
    return _drop_git_ignored(candidates, root)


def _drop_git_ignored(dirs: list[Path], root: Path) -> list[Path]:
    """Return only the directories git does not ignore (one batched call).

    A path listed in .gitignore is not part of the project: `crate-cli/tmp/`
    holds scratch crates from local runs, and reporting them yields findings
    no commit can ever contain.
    """
    if not dirs:
        return dirs
    try:
        rels = [str(d.relative_to(root)) + "/" for d in dirs]
    except ValueError:
        return dirs
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "check-ignore", "--stdin"],
            input="\n".join(rels) + "\n",
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError):
        return dirs
    if result.returncode not in (0, 1):
        return dirs
    ignored = {line.strip().rstrip("/") for line in result.stdout.splitlines() if line.strip()}
    kept = []
    for directory, rel in zip(dirs, rels):
        rel = rel.rstrip("/")
        if rel in ignored or any(rel.startswith(f"{parent}/") for parent in ignored):
            continue
        kept.append(directory)
    return kept


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    if not root.is_dir():
        print(f"error: {root} is not a directory", file=sys.stderr)
        return 2
    violations: list[str] = []
    hit_dirs = 0
    for directory in _dirs_to_check(root):
        found = audit_one_dir(directory)
        if found:
            hit_dirs += 1
            violations.extend(found)
    for violation in violations:
        print(violation)
    print(
        f"\n=== no-sibling-dirs (§1.3d): {len(violations)} violation(s) "
        f"in {hit_dirs} dir(s) ==="
    )
    return 1 if violations else 0


if __name__ == "__main__":
    sys.exit(main())
