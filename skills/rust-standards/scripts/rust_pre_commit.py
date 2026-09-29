#!/usr/bin/env python3
"""rust-standards pre-commit + post-coding loop.

The single command an AI / human runs after writing Rust code, before
committing / pushing.  Loops auto-fixers + audit until the entire
pipeline is 0 violations, 0 warnings, 0 fmt diffs.

Phases (each MUST pass before commit; if any fails, loop restarts):

  Phase 1 — Auto-fixers (idempotent, converge to 0 diff)
    1a. fix_dep_order.py --write          (Cargo.toml §13.7 round 4)
    1b. strictify_tests_layout.py         (tests/ §14.4 + §14.5 + §14.7)
    1c. doc_comment_audit.py              (doc-comment Layer 1 + Layer 2)

  Phase 2 — Audit pipeline
    audit_rust_standards.py -- 38 checks; exit non-zero triggers
    Phase 1 re-run + Phase 2 re-run (loop until clean or N iterations).

  Phase 3 — Format idempotence (only after audit clean)
    euv fmt && crate fmt && crate fmt    (euv is no-op for non-euv repos)
    git status --short -- expect empty.

  Phase 4 — clippy 0 warnings
    cargo clippy --all-targets --offline.

  Phase 5 — test compile clean
    cargo test --no-run --all-targets --offline.

Each phase prints a single-line pass / fail status.  Exit 0 only if ALL
phases pass.  Non-zero exit signals which phase + which check failed,
so the caller (human or AI agent) can fix that specific failure.

Usage:
    python3 rust_pre_commit.py [REPO_ROOT]            # full loop
    python3 rust_pre_commit.py [REPO_ROOT] --no-fix   # skip Phase 1
    python3 rust_pre_commit.py [REPO_ROOT] --audit-only
    python3 rust_pre_commit.py [REPO_ROOT] --max-iters 5
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

# Locate scripts relative to this file — `rust_pre_commit.py` lives
# alongside `audit_rust_standards.py` and friends.
SCRIPT_DIR = Path(__file__).resolve().parent

# Auto-fixers — MUST be run BEFORE audit (audit reads post-fix state).
#
# SCOPING (2026-09-27): each fixer is a whole-repo REWRITER by default, so
# every template now carries a `--files` placeholder. `{rs_files}` /
# `{toml_files}` expand to the caller's changed-file list; when the relevant
# list is empty the fixer is SKIPPED rather than run unscoped (an empty
# `--files` with `nargs="*"` means "whole repo" to argparse, which is the
# exact footgun this scoping exists to prevent).
AUTO_FIXERS: list[tuple[str, list[str], str]] = [
    (
        "fix_dep_order",
        [
            "python3", str(SCRIPT_DIR / "fix_dep_order.py"),
            "--write", "{root}", "--files", "{toml_files}",
        ],
        "Cargo.toml §13.7 round 4 dep-block order (write mode)",
    ),
    (
        "strictify_tests_layout",
        [
            "python3", str(SCRIPT_DIR / "strictify_tests_layout.py"),
            "{root}", "--files", "{rs_files}",
        ],
        "tests/ §14.4 / §14.5 / §14.7 layout + comment cleanup",
    ),
    (
        "doc_comment_audit",
        [
            "python3", str(SCRIPT_DIR / "doc_comment_audit.py"),
            "--root", "{root}", "--files", "{rs_files}",
        ],
        "doc-comment Layer 1 (existence) + Layer 2 (# Arguments / # Returns)",
    ),
]


def _run(label: str, argv: list[str], cwd: Path, timeout: int = 300) -> tuple[int, str, str]:
    """Run a subprocess, return (exit_code, stdout, stderr)."""
    try:
        result = subprocess.run(
            argv,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return 124, "", f"timeout after {timeout}s"
    return result.returncode, result.stdout, result.stderr


def _expand(argv: list[str], root: Path) -> list[str]:
    """Replace {root} placeholder with the actual repo path."""
    out = []
    for a in argv:
        if a == "{root}":
            out.append(str(root))
        else:
            out.append(a)
    return out


# ---------------------------------------------------------------------------
# Phase 1 — auto-fixers
# ---------------------------------------------------------------------------


def _git(root: Path, *args: str) -> tuple[int, str]:
    result = subprocess.run(
        ["git", "-C", str(root), *args], capture_output=True, text=True
    )
    return result.returncode, result.stdout


def _changed_paths(root: Path, base: str | None) -> list[str]:
    """Repo-relative paths changed vs `base` (default: origin/HEAD, else HEAD).

    Covers all three ways a change can exist: committed ahead of the base,
    uncommitted worktree edits, and untracked files. Returns [] only when
    there is genuinely nothing to fix.
    """
    if not (root / ".git").exists():
        return []
    diff_base = base
    if diff_base is None:
        for candidate in ("origin/HEAD", "origin/main", "origin/master", "HEAD"):
            code, _ = _git(root, "rev-parse", "--verify", "--quiet", candidate)
            if code == 0:
                diff_base = candidate
                break
        else:
            return []
    paths: set[str] = set()

    # 1. Committed ahead of the base.
    code, out = _git(root, "diff", "--name-only", f"{diff_base}...HEAD")
    if code != 0:
        code, out = _git(root, "diff", "--name-only", diff_base)
    if code == 0:
        paths |= {p for p in out.splitlines() if p.strip()}

    # 2. Uncommitted worktree / index changes. Without this, an edit made
    #    right before running the script (the normal case) is invisible and
    #    the fixers get an empty scope.
    for extra in (["--cached"], []):
        code, out = _git(root, "diff", "--name-only", *extra)
        if code == 0:
            paths |= {p for p in out.splitlines() if p.strip()}

    # 3. Untracked files.
    code, untracked = _git(root, "ls-files", "--others", "--exclude-standard")
    if code == 0:
        paths |= {p for p in untracked.splitlines() if p.strip()}

    return sorted(paths)


def _sandbox_snapshot(root: Path) -> dict[str, int]:
    """Cheap fingerprint of every tracked source file, used to detect
    auto-fixer writes that fall OUTSIDE the caller's change scope."""
    snapshot: dict[str, int] = {}
    for path in root.rglob("*.rs"):
        if "target" in path.parts or ".cargo" in path.parts:
            continue
        try:
            snapshot[str(path)] = path.stat().st_size
        except OSError:
            continue
    return snapshot


def _sandbox_drift(before: dict[str, int], after: dict[str, int], scope: set[str]) -> list[str]:
    """Files whose size changed but that are NOT in `scope`."""
    drift: list[str] = []
    for path, size in after.items():
        if before.get(path) == size:
            continue
        if str(Path(path).resolve()) in scope:
            continue
        drift.append(path)
    return sorted(drift)


# ---------------------------------------------------------------------------
# Phase 1 — auto-fixers
# ---------------------------------------------------------------------------


def phase_fixers(
    root: Path, skip: bool, scope: list[str] | None
) -> tuple[bool, list[str], list[str]]:
    """Run all auto-fixers in order, each scoped to `scope`.

    Returns (all_ok, [failure_labels], [out_of_scope_drift_files]).

    Scope matters: all three fixers are whole-repo REWRITERS by default.
    `doc_comment_audit.py` in particular inserts doc comments into every
    tracked .rs file lacking them — running it unscoped on a repo with
    legacy debt rewrote 84 files / +7165 lines in one invocation
    (2026-09-27, ctares). With a scope, only the caller's own change is
    touched.
    """
    failures: list[str] = []
    drift: list[str] = []
    if skip:
        print("  Phase 1 [SKIP] auto-fixers (--no-fix)")
        return True, failures, drift

    rs_scope = [f for f in scope or [] if f.endswith(".rs")]
    toml_scope = [f for f in scope or [] if f.endswith("Cargo.toml")]

    if scope == []:
        # Scope computed, nothing changed -> nothing to fix. Running the
        # fixers here would mean a whole-repo sweep, which is exactly the
        # 7165-line rewrite this scoping was added to stop.
        print("  Phase 1 [SKIP] auto-fixers (no changed .rs / Cargo.toml in scope)")
        return True, failures, drift
    scope_note = "scoped" if scope else "WHOLE-REPO (--no-scope)"

    for label, template, desc in AUTO_FIXERS:
        argv_template = list(template)
        if "{rs_files}" in argv_template:
            argv_template[argv_template.index("{rs_files}")] = " ".join(rs_scope)
        if "{toml_files}" in argv_template:
            argv_template[argv_template.index("{toml_files}")] = " ".join(toml_scope)
        argv = _expand(argv_template, root)
        # A scoped fixer with an empty file list must not fall back to
        # whole-repo: drop the flag entirely and skip the run instead.
        if scope and not (rs_scope or toml_scope):
            continue
        if "{rs_files}" in template and not rs_scope:
            continue
        if "{toml_files}" in template and not toml_scope:
            continue

        before = _sandbox_snapshot(root)
        t0 = time.monotonic()
        rc, stdout, stderr = _run(label, argv, root, timeout=120)
        dt = time.monotonic() - t0
        if rc != 0:
            failures.append(label)
            print(f"  Phase 1 [{label:24s}] FAIL  rc={rc}  ({dt:.1f}s)")
            if stderr:
                print(f"    stderr: {stderr.strip()[:200]}")
        else:
            after = _sandbox_snapshot(root)
            scope_resolved = {
                str((root / f).resolve()) for f in (scope or [])
            }
            drift.extend(_sandbox_drift(before, after, scope_resolved))
            print(f"  Phase 1 [{label:24s}] PASS  ({dt:.1f}s)  {desc} [{scope_note}]")
    return not failures, failures, drift


# ---------------------------------------------------------------------------
# Phase 2 — audit pipeline
# ---------------------------------------------------------------------------


def phase_audit(root: Path) -> tuple[bool, str]:
    """Run audit_rust_standards.py.  Return (ok, summary)."""
    argv = ["python3", str(SCRIPT_DIR / "audit_rust_standards.py"), str(root)]
    t0 = time.monotonic()
    rc, stdout, stderr = _run("audit", argv, root, timeout=300)
    dt = time.monotonic() - t0
    # The audit script prints '=== SUMMARY: X/Y PASS ===' on stdout.
    summary = ""
    for line in stdout.splitlines():
        if "SUMMARY" in line:
            summary = line.strip()
            break
    if rc == 0:
        print(f"  Phase 2 [audit                ] PASS  ({dt:.1f}s)  {summary}")
        return True, summary
    print(f"  Phase 2 [audit                ] FAIL  rc={rc}  ({dt:.1f}s)  {summary}")
    # Print the FAIL lines for context (max 10)
    fail_lines = [
        line for line in stdout.splitlines()
        if line.startswith("FAIL: ") or line.startswith("  ")
    ]
    for line in fail_lines[:10]:
        print(f"    {line}")
    if len(fail_lines) > 10:
        print(f"    ... ({len(fail_lines) - 10} more)")
    return False, summary


# ---------------------------------------------------------------------------
# Phase 3 — format idempotence
# ---------------------------------------------------------------------------


def phase_fmt(root: Path) -> bool:
    """Run `euv fmt && crate fmt && crate fmt` and check the SECOND
    crate fmt run is a no-op (idempotence check).

    Notes:
      - euv fmt is only meaningful for euv workspaces; for other repos
        it just exits non-zero (tool not found).  We tolerate that with
        a fallback to just `crate fmt`.
      - We do NOT gate on `git status --short` — Cargo.lock may be
        created by cargo clippy/test build (Phase 4 / 5), and that
        is unrelated to fmt.  The idempotence check is the right
        signal: if running `crate fmt` twice produces any diff in
        the second run, formatter is broken.
    """
    has_euv_fmt = shutil.which("euv") is not None
    cmds: list[list[str]] = []
    if has_euv_fmt:
        cmds.append(["euv", "fmt"])
    # Two write passes (some files need 2 passes to fully converge due
    # to re-ordering), then --check to verify idempotence.
    cmds.extend([
        ["crate", "fmt"],
        ["crate", "fmt"],
        ["crate", "fmt", "--check"],
    ])
    t0 = time.monotonic()
    for cmd in cmds:
        rc, stdout, stderr = _run("fmt", cmd, root, timeout=120)
        if rc != 0:
            # `crate fmt --check` is the idempotence sentinel — it
            # exits non-zero ONLY when fmt would still produce diff.
            if cmd[-1] == "--check":
                dt = time.monotonic() - t0
                print(f"  Phase 3 [fmt                  ] FAIL  fmt not idempotent  ({dt:.1f}s)")
                print(f"    (Hint: run `crate fmt` manually and review the diff — this usually")
                print(f"     means rustfmt changed behavior, see SKILL.md §13 pitfall.)")
                # Show what changed
                rc2, out2, _ = _run(
                    "fmt-show",
                    ["git", "diff", "--stat"],
                    root,
                    timeout=10,
                )
                if rc2 == 0 and out2.strip():
                    for line in out2.strip().splitlines()[:10]:
                        print(f"    {line}")
                return False
            # Real failure
            dt = time.monotonic() - t0
            print(f"  Phase 3 [fmt                  ] FAIL  {' '.join(cmd)} rc={rc}  ({dt:.1f}s)")
            if stderr:
                print(f"    stderr: {stderr.strip()[:300]}")
            return False
    dt = time.monotonic() - t0
    print(f"  Phase 3 [fmt                  ] PASS  ({dt:.1f}s)  idempotent")
    return True


# ---------------------------------------------------------------------------
# Phase 4 — clippy 0 warnings
# ---------------------------------------------------------------------------


def phase_clippy(root: Path) -> bool:
    """Run cargo clippy --all-targets.  Any warning = FAIL.

    The exit code is NOT a warning signal: `cargo clippy` exits 0 with
    any number of `warning:` diagnostics (warnings are not errors unless
    `-D warnings` is passed, which no project in this workspace does).
    A previous version gated on `rc == 0` alone and printed a hardcoded
    "0 warnings" — it reported PASS for any repo with clippy warnings,
    which is how euv (2) and ctares (5) shipped `module_inception`
    warnings while every gate stayed green.  Count the diagnostics.
    """
    argv = ["cargo", "clippy", "--all-targets", "--offline", "--quiet"]
    t0 = time.monotonic()
    rc, stdout, stderr = _run("clippy", argv, root, timeout=600)
    dt = time.monotonic() - t0
    out = (stdout or "") + (stderr or "")
    # `warning: <text>` at column 0 starts a diagnostic; the indented
    # `= note:` / `= help:` continuation lines and the `--> file:line`
    # pointer must not be counted, or one warning inflates to several.
    warning_lines = [
        line for line in out.splitlines()
        if line.startswith("warning:") or line.startswith("error:")
    ]
    count = len(warning_lines)
    if rc == 0 and count == 0:
        print(f"  Phase 4 [clippy               ] PASS  ({dt:.1f}s)  0 warnings")
        return True
    reason = f"rc={rc}" if rc != 0 else f"{count} warning(s)"
    print(f"  Phase 4 [clippy               ] FAIL  ({dt:.1f}s)  {reason}")
    for line in warning_lines[:10]:
        print(f"    {line.strip()[:200]}")
    if count > 10:
        print(f"    ... ({count - 10} more)")
    print(f"    (Hint: rust-standards rule 14 forbids `#[allow]` — fix at source.)")
    return False


# ---------------------------------------------------------------------------
# Phase 5 — test compile clean
# ---------------------------------------------------------------------------


def phase_test_compile(root: Path) -> bool:
    """Run cargo test --no-run --all-targets to confirm test code compiles."""
    argv = ["cargo", "test", "--no-run", "--all-targets", "--offline", "--quiet"]
    t0 = time.monotonic()
    rc, stdout, stderr = _run("test", argv, root, timeout=600)
    dt = time.monotonic() - t0
    if rc == 0:
        print(f"  Phase 5 [test compile         ] PASS  ({dt:.1f}s)")
        return True
    print(f"  Phase 5 [test compile         ] FAIL  rc={rc}  ({dt:.1f}s)")
    out = (stdout or "") + (stderr or "")
    for line in out.splitlines()[:15]:
        if line.strip():
            print(f"    {line.strip()[:200]}")
    return False


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------


def main() -> int:
    ap = argparse.ArgumentParser(description=(__doc__ or "").split("\n\n")[0])
    ap.add_argument(
        "repo",
        nargs="?",
        default=".",
        help="Path to Rust repo root (default: current dir)",
    )
    ap.add_argument(
        "--no-fix",
        action="store_true",
        help="Skip Phase 1 auto-fixers (audit-only mode)",
    )
    ap.add_argument(
        "--audit-only",
        action="store_true",
        help="Run only Phase 2 (audit); skip fixers, fmt, clippy, test",
    )
    ap.add_argument(
        "--max-iters",
        type=int,
        default=3,
        help="Max iterations of Phase 1 -> Phase 2 loop (default: 3)",
    )
    ap.add_argument(
        "--base",
        default=None,
        help=("Git ref the change scope is computed against "
              "(default: origin/HEAD, else origin/main / origin/master / HEAD)."),
    )
    ap.add_argument(
        "--no-scope",
        action="store_true",
        help=("Run auto-fixers over the WHOLE repo (legacy behaviour). The "
              "auto-fixers are rewriters; use only when a full sweep is wanted."),
    )
    args = ap.parse_args()

    root = Path(args.repo).resolve()
    if not root.is_dir():
        print(f"error: {root} is not a directory", file=sys.stderr)
        return 2
    # Sanity: must be a Rust repo with Cargo.toml
    if not (root / "Cargo.toml").exists():
        print(f"error: {root} has no Cargo.toml — not a Rust repo", file=sys.stderr)
        return 2

    print(f"rust_pre_commit.py — repo: {root}")
    print(f"  scripts dir: {SCRIPT_DIR}")
    print()

    overall_ok = True
    audit_only = args.audit_only
    skip_fix = args.no_fix

    # Change scope for the auto-fixers.
    #
    #   None            -> scope deliberately disabled (--no-scope): whole-repo.
    #   non-empty list  -> only these files may be rewritten.
    #   empty list      -> scope was COMPUTED but nothing changed, so the
    #                      fixers have nothing to do. This is NOT a licence to
    #                      sweep the repo.
    scope: list[str] | None
    if args.no_scope:
        scope = None
        print("scope: WHOLE-REPO (--no-scope) — fixers may rewrite any file")
    else:
        scope = _changed_paths(root, args.base)
        if scope:
            rs_n = len([f for f in scope if f.endswith(".rs")])
            toml_n = len([f for f in scope if f.endswith("Cargo.toml")])
            base_label = args.base or "auto"
            print(f"scope: {len(scope)} changed file(s) vs {base_label} "
                  f"({rs_n} .rs, {toml_n} Cargo.toml)")
        else:
            print("scope: no changes detected — auto-fixers will be SKIPPED")
            print("       (pass --no-scope to force a whole-repo sweep)")
    print()

    # ------------------------------------------------------------------
    # Phase 1 + Phase 2 loop: fixers may unblock audit findings, so we
    # iterate up to max_iters times.
    # ------------------------------------------------------------------
    if not audit_only:
        all_drift: list[str] = []
        for iteration in range(1, args.max_iters + 1):
            print(f"--- iteration {iteration}/{args.max_iters} ---")
            fix_ok, fix_failures, drift = phase_fixers(root, skip_fix, scope)
            all_drift.extend(drift)
            if not fix_ok:
                print(f"\nFAIL: Phase 1 fixer(s) failed: {', '.join(fix_failures)}")
                print(f"  These are script bugs, not code issues — investigate manually.")
                overall_ok = False
                break

            audit_ok, _ = phase_audit(root)
            if audit_ok:
                break
            if iteration == args.max_iters:
                print(f"\nFAIL: Phase 2 audit still has violations after {args.max_iters} fix iterations.")
                print(f"  Fix remaining violations manually — see FAIL: lines above.")
                overall_ok = False
                break
            print(f"  -> audit has violations; re-running auto-fixers (iteration {iteration + 1})")
            print()
        if all_drift:
            unique = sorted(set(all_drift))
            print(f"  WARNING: auto-fixers modified {len(unique)} file(s) OUTSIDE the change scope:")
            for path in unique[:10]:
                print(f"    - {path}")
            if len(unique) > 10:
                print(f"    ... ({len(unique) - 10} more)")
            print("  Review with `git diff`; revert anything unrelated to your change.")
            print()
        print()
    else:
        # audit-only mode: still run audit, just skip fixers / fmt / clippy / test
        print("--- audit-only mode: skipping fixers / fmt / clippy / test ---")
        audit_ok, _ = phase_audit(root)
        if not audit_ok:
            overall_ok = False
        print()

    # ------------------------------------------------------------------
    # Phase 3 — fmt idempotence
    # ------------------------------------------------------------------
    if not audit_only and overall_ok:
        if not phase_fmt(root):
            overall_ok = False
    elif not audit_only and not overall_ok:
        # Skip fmt if audit already failed — focus the user on the audit
        print("  Phase 3 [fmt                  ] SKIP  (audit failed; fix audit first)")

    # ------------------------------------------------------------------
    # Phase 4 — clippy
    # ------------------------------------------------------------------
    if not audit_only and overall_ok:
        if not phase_clippy(root):
            overall_ok = False
    elif not audit_only and not overall_ok:
        print("  Phase 4 [clippy               ] SKIP  (audit failed; fix audit first)")

    # ------------------------------------------------------------------
    # Phase 5 — test compile
    # ------------------------------------------------------------------
    if not audit_only and overall_ok:
        if not phase_test_compile(root):
            overall_ok = False
    elif not audit_only and not overall_ok:
        print("  Phase 5 [test compile         ] SKIP  (audit failed; fix audit first)")

    print()
    if overall_ok:
        print("=" * 60)
        print("PASS — all phases clean.  Safe to commit / push.")
        print("=" * 60)
        return 0
    print("=" * 60)
    print("FAIL — see phase output above for what to fix.")
    print("=" * 60)
    return 1


if __name__ == "__main__":
    sys.exit(main())
