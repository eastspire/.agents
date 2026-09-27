#!/usr/bin/env python3
"""Classify whether a repository may bypass its pre-commit hook.

Owned projects — anything under the user's personal account or one of the
four owned orgs — must never skip the pre-commit gate. The single exemption
is a fork of an external project the user does not author, because that
codebase and its conventions belong to someone else.

The classifier is deliberately asymmetric: anything it cannot positively
identify as an external fork is reported ENFORCED, so a missing token, an
unreachable API or an unparseable origin never silently grants an escape
hatch.

Exit codes:
    0  ENFORCED  owned project, the hook must run
    1  EXEMPT    external fork, the hook may be skipped
    2  ERROR     could not classify; callers must treat this as ENFORCED
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys

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


def run_git(repo: str, *args: str) -> str | None:
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


def parse_origin(repo: str) -> tuple[str, str] | None:
    """Return (owner, repo) parsed from the first GitHub remote."""
    remotes = run_git(repo, "remote", "-v")
    if not remotes:
        return None
    # Prefer origin, then any remote in declaration order.
    lines = [line for line in remotes.splitlines() if "fetch" in line]
    lines.sort(key=lambda line: 0 if line.startswith("origin") else 1)
    for line in lines:
        url = line.split()[1] if len(line.split()) > 1 else ""
        match = GITHUB_REMOTE.search(url)
        if match:
            return match.group("owner"), match.group("repo")
    return None


def query_fork_state(owner: str, repo: str) -> tuple[bool | None, str | None]:
    """Ask GitHub whether the repo is a fork; return (is_fork, parent).

    Returns (None, None) when the API cannot be reached or the token lacks
    scope — the caller must treat that as "not proven to be a fork".
    """
    payload = run_git_api(owner, repo)
    if payload is None:
        return None, None
    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        return None, None
    if not isinstance(data, dict) or "fork" not in data:
        return None, None
    is_fork = data.get("fork")
    # The gh --jq projection renders a missing parent as the string "none",
    # not as null or an object, so normalise both shapes here.
    parent = data.get("parent")
    if not isinstance(parent, str):
        parent = None
    if parent in (None, "", "none"):
        parent = None
    return (bool(is_fork) if isinstance(is_fork, bool) else None), parent


def run_git_api(owner: str, repo: str) -> str | None:
    """Fetch repos/<owner>/<repo> through the gh CLI, or None on failure."""
    try:
        result = subprocess.run(
            [
                "gh",
                "api",
                f"repos/{owner}/{repo}",
                "--jq",
                "{fork, parent: (.parent.full_name // \"none\")}",
            ],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None


def classify(repo: str) -> tuple[str, str]:
    """Return (verdict, reason) for `repo`."""
    origin = parse_origin(repo)
    if origin is None:
        return (
            ERROR,
            "cannot parse a GitHub origin remote; treating as owned "
            "(no exemption is granted on uncertainty)",
        )
    owner, name = origin
    full_name = f"{owner}/{name}"

    if owner.lower() in OWNED_OWNERS:
        is_fork, parent = query_fork_state(owner, name)
        if is_fork is True and parent and parent.split("/")[0].lower() not in OWNED_OWNERS:
            return (
                EXEMPT,
                f"{full_name} is a fork of external project {parent}; "
                "upstream conventions apply, hook may be skipped",
            )
        if is_fork is None:
            return (
                ENFORCED,
                f"{full_name} is under owned owner '{owner}' and the fork "
                "field could not be read; an owned repo is enforced by default",
            )
        return (
            ENFORCED,
            f"{full_name} is an owned, non-fork project under '{owner}'; "
            "the pre-commit hook must run",
        )

    # Outside the owned owners: only a positively-identified external fork is
    # exempt. Everything else — including repos the user merely contributes
    # to — stays enforced.
    is_fork, parent = query_fork_state(owner, name)
    if is_fork is True and parent and parent.split("/")[0].lower() not in OWNED_OWNERS:
        return (
            EXEMPT,
            f"{full_name} is a fork of external project {parent}; "
            "upstream conventions apply, hook may be skipped",
        )
    if is_fork is None:
        return (
            ENFORCED,
            f"{full_name} is not under an owned owner and its fork state is "
            "unknown; enforced by default, never exempt on uncertainty",
        )
    return (
        ENFORCED,
        f"{full_name} is not a fork and not under an owned owner; "
        "the pre-commit hook must run",
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
