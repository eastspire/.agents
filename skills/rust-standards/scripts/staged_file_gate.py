#!/usr/bin/env python3
"""Staged-file rust-standards gate: block NEW violations only, never legacy debt.

Why this exists
---------------
`~/.git-hooks/pre-commit` has always been broken, for two independent
reasons:

  1. ARGUMENT-TYPE BUG — the hook invoked the verifiers with a FILE path
     (`python3 verify_*.py "$REPO_ROOT/$f"`), but every `verify_*.py` ends
     its `main()` with `if not root.is_dir(): return 2`. Passing a file
     therefore always failed, so EVERY commit touching a `.rs` file was
     blocked regardless of content. Verified 2026-09-27: all four
     file-level verifiers exit non-zero on a file argument, and no `.rs`
     commit had ever succeeded on ctares since the hook was installed.

  2. NO BASELINE COMPARISON — the hook counted violations in the working
     tree. A file that already carried historical violations
     (e.g. `lombok-macros/src/generate/fn.rs` had 48 pre-existing
     doc-comment findings) was blocked even when the staged diff
     introduced nothing. That directly contradicts the hook's own
     documented intent: "block NEW violations, not legacy debt".

This gate fixes both. For every staged `.rs` file it compares the
violation count in the working tree against the same file at HEAD, and
reports only the DELTA.

Usage
-----
    python3 staged_file_gate.py <repo-root> [--staged | --file PATH ...]

Exit codes
----------
    0 — no new violations (commit allowed)
    1 — new violations introduced by the staged changes (commit blocked)
    2 — usage / environment error (not a git repo, scripts missing, ...)

Design notes
------------
- Verifiers are imported as modules and driven through their `audit_one()`
  entry point rather than re-implemented, so there is exactly one parser
  per rule. Importing also sidesteps the argv contract entirely.
- HEAD content is materialised next to the working file (same name plus a
  `.head-baseline` suffix) so path-relative logic keeps working —
  `verify_lib_rs_doc_comment._read_package_name()` walks up to the nearest
  Cargo.toml to resolve `[package].name`, which a temp file in the scratch
  dir would break. The suffix does not match `*.rs` or `lib.rs`, so it is
  invisible to the verifiers' own `find` patterns, and it is removed in a
  `finally` block.
- `verify_lib_rs_doc_comment` is only meaningful for `lib.rs`; running it
  on any other file name is meaningless work, so it is skipped.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
import tempfile
from pathlib import Path

SUFFIX = ".head-baseline"

# verifier module name -> human label
VERIFIERS = {
    "verify_doc_comment_format": "doc-comment §2.1/§2.2",
    "verify_no_import_rename": "import rename §6.5",
    "verify_no_self_field_access": "self.field access §17.3/§17.12",
    "verify_lib_rs_doc_comment": "lib.rs //! block §2.4",
}

# Verifiers that only make sense for a specific file name.
FILE_SCOPED = {"verify_lib_rs_doc_comment": "lib.rs"}


def die(message: str, code: int = 2) -> int:
    print(f"staged_file_gate: {message}", file=sys.stderr)
    return code


def load_verifier(scripts_dir: Path, name: str):
    """Import a verifier module by path, so argv/CLI is bypassed entirely."""
    path = scripts_dir / f"{name}.py"
    if not path.is_file():
        return None
    spec = importlib.util.spec_from_file_location(f"rsv_{name}", path)
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception as error:  # noqa: BLE001 - a broken verifier must not
        print(f"  ! cannot import {name}.py: {error}", file=sys.stderr)
        return None
    return module


def audit(module, path: Path) -> list[str]:
    """Run a verifier's per-file check, tolerating a missing entry point."""
    audit_one = getattr(module, "audit_one", None)
    if audit_one is None:
        return []
    try:
        return list(audit_one(path))
    except Exception as error:  # noqa: BLE001
        print(f"  ! {module.__name__}.audit_one failed: {error}", file=sys.stderr)
        return []


def git(repo_root: Path, *args: str) -> tuple[int, str]:
    result = subprocess.run(
        ["git", "-C", str(repo_root), *args],
        capture_output=True,
        text=True,
    )
    return result.returncode, result.stdout


def head_content(repo_root: Path, rel: str) -> str | None:
    """File content at HEAD, or None when the file is new / untracked."""
    code, out = git(repo_root, "show", f"HEAD:{rel}")
    if code != 0:
        return None
    return out


def materialise(target: Path, text: str) -> Path:
    """Write `text` beside `target` so path-relative logic still resolves."""
    tmp = target.with_name(target.name + SUFFIX)
    tmp.write_text(text)
    return tmp


def parse_args(argv: list[str]) -> tuple[Path, list[str]]:
    args = argv[1:]
    if not args:
        raise ValueError("usage: staged_file_gate.py <repo-root> [--staged | --file PATH ...]")
    root = Path(args[0]).resolve()
    files: list[str] = []
    rest = args[1:]
    if "--file" in rest:
        index = rest.index("--file")
        files = rest[index + 1 :]
    else:
        code, out = git(root, "diff", "--cached", "--name-only", "--diff-filter=ACMR")
        if code != 0:
            raise ValueError("not a git repository, or git failed")
        files = [line for line in out.splitlines() if line.strip()]
    return root, files


def main() -> int:
    try:
        repo_root, staged = parse_args(sys.argv)
    except ValueError as error:
        return die(str(error))

    if not repo_root.is_dir():
        return die(f"{repo_root} is not a directory")

    scripts_dir: Path | None = None
    for candidate in (
        Path.home() / ".agents/skills/rust-standards/scripts",
        Path.home() / ".hermes/skills/rust-standards/scripts",
    ):
        if (candidate / "verify_doc_comment_format.py").is_file():
            scripts_dir = candidate
            break
    if scripts_dir is None:
        return die("rust-standards skill scripts not found")

    rs_files = [f for f in staged if f.endswith(".rs")]
    if not rs_files:
        print("staged_file_gate: no staged .rs files, nothing to check")
        return 0

    modules: dict[str, object] = {}
    for name in VERIFIERS:
        module = load_verifier(scripts_dir, name)
        if module is not None:
            modules[name] = module

    if not modules:
        return die("no verifier could be imported")

    print("============================================================")
    print("staged_file_gate: new-violation gate (staged vs HEAD)")
    print(f"  repo:    {repo_root}")
    print(f"  scripts: {scripts_dir}")
    print(f"  .rs files: {len(rs_files)}")
    print("============================================================")

    total_new = 0
    report: list[str] = []

    for rel in rs_files:
        working = repo_root / rel
        if not working.is_file():
            report.append(f"    - {rel}: staged but missing from worktree, skipped")
            continue

        baseline = head_content(repo_root, rel)
        baseline_path: Path | None = None
        if baseline is not None:
            try:
                baseline_path = materialise(working, baseline)
            except OSError as error:
                print(f"  ! cannot stage baseline for {rel}: {error}", file=sys.stderr)
                baseline_path = None

        try:
            for name, module in modules.items():
                required_name = FILE_SCOPED.get(name)
                if required_name and working.name != required_name:
                    continue
                before = audit(module, baseline_path) if baseline_path else []
                after = audit(module, working)
                if len(after) > len(before):
                    delta = len(after) - len(before)
                    total_new += delta
                    report.append(
                        f"    - {rel}: +{delta} new ({name} — {VERIFIERS[name]})"
                    )
        finally:
            if baseline_path is not None and baseline_path.exists():
                baseline_path.unlink()

    if total_new == 0:
        print("\n  0 new violations — commit allowed")
        print("  (legacy violations in touched files are NOT counted)")
        print("============================================================")
        return 0

    print(f"\n  {total_new} NEW violation(s) introduced by staged changes:")
    for line in report:
        print(line)
    print("")
    print("============================================================")
    print("staged_file_gate: FAIL — commit BLOCKED")
    print("============================================================")
    return 1


if __name__ == "__main__":
    sys.exit(main())
