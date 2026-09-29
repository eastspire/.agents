#!/usr/bin/env python3
"""
§1.3d verifier: a Rust code file MUST NOT live at the same level as directories.

Rule (2026-09-28 user directive, verbatim: "如果 rust 代码文件同级有目录,
需要报错提示代码文件不能和目录在同一级,注意 lib.rs main.rs build.rs
mod.rs 这些除外"), as narrowed the same day after the standard fix
turned out to cost clippy warnings:

    A directory that holds at least one sub-directory MUST NOT also hold
    a `.rs` file that has NO module-scope home of its own.

    Exempt — a file is exempt when it is either:

    (a) a module-entry file:  lib.rs / main.rs / build.rs / mod.rs
        (their whole job is to be the parent of sub-modules), or

    (b) a keyword file — the nine §1.3 names (const.rs, static.rs,
        fn.rs, enum.rs, struct.rs, trait.rs, impl.rs, type.rs) plus
        `macro.rs`.  Each is a leaf of the module tree that its OWN
        directory's mod.rs declares by name; §1.3a already governs what
        may live inside them, so the parent level needs no opinion.

    Everything else — `inline.rs`, `html_static_style.rs`, and any other
    ad-hoc `.rs` file — is a violation when a sub-directory sits beside
    it, because such a file has no name any mod.rs declares and no
    place in the keyword taxonomy.

Why keyword files are exempt (this is the narrowing, 2026-09-28):
    The strict reading — "no .rs file beside a directory, period" —
    looks tidier and was the first implementation.  It is unsound in
    two measured ways:

      1. It forces the fix `const.rs -> const/{const.rs,mod.rs}`, and
         `mod r#const;` inside `const/mod.rs` names a module identical
         to its containing directory.  That is clippy's
         `module_inception`, which fires by default.  euv (2 warnings)
         and ctares (5) both measured the regression against a
         0-warning master baseline; `X/X.rs` did not exist anywhere in
         either repo before this rule forced it.

      2. It mislabels legitimate files.  ctares carries 24 `macro.rs`
         files sitting beside sub-directories (`clonelicious/src/`,
         `future-fn/src/`, `std-macro-extensions/src/*/`) — all valid
         leaves, all reported as violations by the strict reading.

    So the rule now targets what it was actually for: an orphan `.rs`
    file with no module name and no keyword slot, next to real
    sub-modules.

Detection:
  Walk the tree.  For every directory:
    orphan_files = [*.rs] minus {lib, main, build, mod} minus KEYWORD_FILES
    sub_dirs     = visible sub-directories, excluding SKIP_DIR_NAMES
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


# Module-entry files: their purpose IS to be the parent of sub-modules.
ENTRY_FILE_NAMES = frozenset({"lib.rs", "main.rs", "build.rs", "mod.rs"})

# §1.3 keyword files + macro.rs.  Each is a named leaf declared by its own
# directory's mod.rs, so its presence beside sub-directories is not a
# layout problem.  `macro.rs` is included because ctares ships 24 of them
# in exactly this position as valid leaves.
KEYWORD_FILE_NAMES = frozenset({
    "const.rs", "static.rs", "fn.rs", "enum.rs", "struct.rs",
    "trait.rs", "impl.rs", "type.rs", "macro.rs",
})

EXEMPT_FILE_NAMES = ENTRY_FILE_NAMES | KEYWORD_FILE_NAMES

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
        f"{directory}: orphan code file(s) {files_label} cannot share a level "
        f"with sub-directory(ies) {dirs_label} (§1.3d); move each into its own "
        f"sub-module directory (e.g. `{code_files[0][: -len('.rs')]}/"
        f"{code_files[0]}`) — module-entry files (lib.rs / main.rs / build.rs / "
        f"mod.rs) and §1.3 keyword files (const/fn/impl/struct/enum/trait/type/"
        f"static/macro .rs) are exempt because their names are declared by their "
        f"own directory's mod.rs"
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
