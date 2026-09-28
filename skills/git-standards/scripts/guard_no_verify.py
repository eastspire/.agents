#!/usr/bin/env python3
"""Classify whether a repository may bypass its pre-commit hook.

The rule is ownership, not forking. A repo under one of the owned owners
(the personal account plus the four owned orgs) must never skip the
pre-commit gate. Anything else is external — upstream code the user does
not own — and follows upstream conventions, so the hook may be skipped.

Only the origin remote is consulted; no network call is involved, so a
missing token, an unreachable API or a rate limit can never change the
verdict. A repo whose origin cannot be parsed is reported ERROR, which
callers must treat as ENFORCED.

Exit codes:
    0  ENFORCED  owned project, the hook must run
    1  EXEMPT    external repo, the hook may be skipped
    2  ERROR     could not classify; callers must treat this as ENFORCED
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from typing import Optional

OWNED_OWNERS = frozenset(
    {
        "eastspire",
        "hyperlane-dev",
        "euv-dev",
        "crates-dev",
        "docs-pages",
    }
)

# Remote URL shapes that identify a GitHub repo, e.g.
#   git@github.com:euv-dev/euv.git
#   https://github.com/euv-dev/euv.git
#   https://x-access-token:<tok>@github.com/euv-dev/euv.git
GITHUB_REMOTE = re.compile(
    r"github\.com[:/]+(?P<owner>[A-Za-z0-9_.-]+)/(?P<repo>[A-Za-z0-9_.-]+?)(?:\.git)?/?$"
)

ENFORCED = "ENFORCED"
EXEMPT = "EXEMPT"
ERROR = "ERROR"


def run_git(repo: str, *args: str) -> Optional[str]:
    """Run a git command in `repo`, returning stripped stdout or None."""
    try:
        result = subprocess.run(
            ["git", "-C", repo, *args],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def parse_origin(repo: str) -> Optional[tuple]:
    """Return (owner, repo) parsed from the first GitHub remote."""
    remotes = run_git(repo, "remote", "-v")
    if not remotes:
        return None
    # Prefer origin, then any remote in declaration order.
    lines = [line for line in remotes.splitlines() if "fetch" in line]
    lines.sort(key=lambda line: 0 if line.startswith("origin") else 1)
    for line in lines:
        parts = line.split()
        url = parts[1] if len(parts) > 1 else ""
        match = GITHUB_REMOTE.search(url)
        if match:
            return match.group("owner"), match.group("repo")
    return None


def classify(repo: str) -> tuple:
    """Return (verdict, reason) for `repo`.

    The rule is ownership, not forking: a repo under one of the owned
    owners is always enforced; anything else is external and may be
    skipped. No network call is needed, so a missing token or an
    unreachable API can never change the verdict.
    """
    origin = parse_origin(repo)
    if origin is None:
        return (
            ERROR,
            "cannot parse a GitHub origin remote; treating as owned "
            "(an unidentifiable repo is never exempt)",
        )
    owner, name = origin
    full_name = f"{owner}/{name}"

    if owner.lower() in OWNED_OWNERS:
        return (
            ENFORCED,
            f"{full_name} is under owned owner '{owner}'; "
            "the pre-commit hook must run and --no-verify is forbidden",
        )
    return (
        EXEMPT,
        f"{full_name} is external (owner '{owner}' is not one of the owned "
        "owners); upstream conventions apply and the hook may be skipped",
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Classify whether a repo may bypass its pre-commit hook."
    )
    parser.add_argument("--repo", default=".", help="repository path (default: .)")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    args = parser.parse_args()

    verdict, reason = classify(args.repo)

    if args.json:
        print(json.dumps({"verdict": verdict, "reason": reason}))
    else:
        print(f"VERDICT: {verdict}")
        print(f"  {reason}")

    if verdict == EXEMPT:
        return 1
    if verdict == ERROR:
        # Distinct from ENFORCED so callers can log it, but the documented
        # instruction is to treat it as ENFORCED.
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
