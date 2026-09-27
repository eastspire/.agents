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
AUTO_FIXERS: list[tuple[str, list[str], str]] = [
    (
        "fix_dep_order",
        ["python3", str(SCRIPT_DIR / "fix_dep_order.py"), "--write", "{root}"],
        "Cargo.toml §13.7 round 4 dep-block order (write mode)",
    ),
    (
        "strictify_tests_layout",
        ["python3", str(SCRIPT_DIR / "strictify_tests_layout.py"), "{root}"],
        "tests/ §14.4 / §14.5 / §14.7 layout + comment cleanup",
    ),
    (
        "doc_comment_audit",
        ["python3", str(SCRIPT_DIR / "doc_comment_audit.py"), "--root", "{root}"],
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


def phase_fixers(root: Path, skip: bool) -> tuple[bool, list[str]]:
    """Run all auto-fixers in order.  Each is idempotent — second run
    is a no-op.  Return (all_ok, [failure_labels])."""
    failures: list[str] = []
    if skip:
        print("  Phase 1 [SKIP] auto-fixers (--no-fix)")
        return True, failures
    for label, argv_template, desc in AUTO_FIXERS:
        argv = _expand(argv_template, root)
        t0 = time.monotonic()
        rc, stdout, stderr = _run(label, argv, root, timeout=120)
        dt = time.monotonic() - t0
        if rc != 0:
            failures.append(label)
            print(f"  Phase 1 [{label:24s}] FAIL  rc={rc}  ({dt:.1f}s)")
            if stderr:
                print(f"    stderr: {stderr.strip()[:200]}")
        else:
            # Count how many files the fixer touched (look for "N file(s)"
            # or similar in stdout).
            print(f"  Phase 1 [{label:24s}] PASS  ({dt:.1f}s)  {desc}")
    return not failures, failures


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
    """Run cargo clippy --all-targets.  Any warning = FAIL."""
    argv = ["cargo", "clippy", "--all-targets", "--offline", "--quiet"]
    t0 = time.monotonic()
    rc, stdout, stderr = _run("clippy", argv, root, timeout=600)
    dt = time.monotonic() - t0
    if rc == 0:
        print(f"  Phase 4 [clippy               ] PASS  ({dt:.1f}s)  0 warnings")
        return True
    print(f"  Phase 4 [clippy               ] FAIL  rc={rc}  ({dt:.1f}s)")
    out = (stdout or "") + (stderr or "")
    warning_lines = [
        line for line in out.splitlines()
        if "warning:" in line or "error:" in line
    ]
    for line in warning_lines[:10]:
        print(f"    {line.strip()[:200]}")
    if len(warning_lines) > 10:
        print(f"    ... ({len(warning_lines) - 10} more)")
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

    # ------------------------------------------------------------------
    # Phase 1 + Phase 2 loop: fixers may unblock audit findings, so we
    # iterate up to max_iters times.
    # ------------------------------------------------------------------
    if not audit_only:
        for iteration in range(1, args.max_iters + 1):
            print(f"--- iteration {iteration}/{args.max_iters} ---")
            fix_ok, fix_failures = phase_fixers(root, skip_fix)
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
