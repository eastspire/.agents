#!/usr/bin/env python3
"""Classify whether a repository may bypass the pre-commit hook.

Ownership is resolved by asking GitHub, not by a hardcoded owner list, so
every repo the user owns is covered — including any org created after this
script was written. Two sets are enumerated:

  * every repository under the authenticated account (`/user/repos`)
  * every repository under every org the account belongs to (`/user/orgs`
    then `orgs/<org>/repos`)

A repo is ENFORCED when it appears in either set, and EXEMPT only when
GitHub positively reports it as belonging to nobody the user owns. Anything
unresolvable — no auth, API down, rate limited, remote that is not GitHub —
is ERROR, which the caller must treat as ENFORCED. The failure direction is
deliberate: an unanswerable question must never become a free pass.

Exit codes:
    0  ENFORCED  the repo is the user's, the hook must run
    1  EXEMPT    GitHub confirms the repo is not the user's
    2  ERROR     could not resolve ownership; callers treat this as ENFORCED
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from typing import List, Optional, Tuple

GITHUB_REMOTE = re.compile(
    r"github\.com[:/]+(?P<owner>[A-Za-z0-9_.-]+)/(?P<repo>[A-Za-z0-9_.-]+?)(?:\.git)?/?$"
)

ENFORCED = "ENFORCED"
EXEMPT = "EXEMPT"
ERROR = "ERROR"

# A hook must not hang a commit; each gh call is bounded.
GH_TIMEOUT = 25


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


def parse_origin(repo: str) -> Optional[Tuple[str, str]]:
    """Return (owner, repo) parsed from the first GitHub remote."""
    remotes = run_git(repo, "remote", "-v")
    if not remotes:
        return None
    lines = [line for line in remotes.splitlines() if "fetch" in line]
    lines.sort(key=lambda line: 0 if line.startswith("origin") else 1)
    for line in lines:
        parts = line.split()
        url = parts[1] if len(parts) > 1 else ""
        match = GITHUB_REMOTE.search(url)
        if match:
            return match.group("owner"), match.group("repo")
    return None


def gh_api(endpoint: str, jq: str) -> Optional[str]:
    """Call the gh CLI, returning stdout, or None if the call failed."""
    try:
        result = subprocess.run(
            ["gh", "api", endpoint, "--jq", jq],
            capture_output=True,
            text=True,
            timeout=GH_TIMEOUT,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    return result.stdout


def gh_account() -> Optional[str]:
    """The account gh is authenticated as, or None."""
    out = gh_api("user", ".login")
    return out.strip() if out and out.strip() else None


def gh_owned_repos(account: str) -> Optional[List[str]]:
    """Every repo name the account owns directly, or None on failure."""
    out = gh_api(f"users/{account}/repos?per_page=100&affiliation=owner", ".[] | .name")
    if out is None:
        return None
    return [line.strip() for line in out.splitlines() if line.strip()]


def gh_owned_orgs(account: str) -> Optional[List[str]]:
    """Every org the account belongs to, or None on failure.

    `/user/orgs` is used rather than `/users/<account>/orgs` because the
    latter lists only orgs with public membership, which silently omits
    private ones.
    """
    out = gh_api("/user/orgs", ".[].login")
    if out is None:
        return None
    return [line.strip() for line in out.splitlines() if line.strip()]


def gh_org_repos(org: str) -> Optional[List[str]]:
    """Every repo name under `org`, or None on failure."""
    out = gh_api(f"orgs/{org}/repos?per_page=100", ".[].name")
    if out is None:
        return None
    return [line.strip() for line in out.splitlines() if line.strip()]


def classify(repo: str) -> Tuple[str, str]:
    """Return (verdict, reason) for `repo`."""
    origin = parse_origin(repo)
    if origin is None:
        return (
            ERROR,
            "cannot parse a GitHub origin remote; treating as owned "
            "(an unidentifiable repo is never exempt)",
        )
    owner, name = origin
    full_name = f"{owner}/{name}"

    account = gh_account()
    if account is None:
        return (
            ERROR,
            "gh is not authenticated, so ownership cannot be resolved; "
            "treating as owned",
        )

    # The account's own repositories.
    if owner.lower() == account.lower():
        personal = gh_owned_repos(account)
        if personal is None:
            return (ERROR, "could not list personal repositories; treating as owned")
        if name in personal:
            return (
                ENFORCED,
                f"{full_name} is a repository owned by {account}; "
                "the pre-commit hook must run",
            )
        return (
            EXEMPT,
            f"GitHub reports {account} owns no repository named {name} "
            "(deleted, renamed, or transferred); hook may be skipped",
        )

    # Repositories under any organization the account belongs to.
    orgs = gh_owned_orgs(account)
    if orgs is None:
        return (
            ERROR,
            "could not list the account's organizations; treating as owned",
        )
    if owner.lower() in {org.lower() for org in orgs}:
        repos = gh_org_repos(owner)
        if repos is None:
            return (ERROR, f"could not list repositories under {owner}; treating as owned")
        if name in repos:
            return (
                ENFORCED,
                f"{full_name} is a repository under your organization {owner}; "
                "the pre-commit hook must run",
            )
        return (
            EXEMPT,
            f"GitHub reports organization {owner} has no repository named "
            f"{name}; hook may be skipped",
        )

    return (
        EXEMPT,
        f"{full_name} is not yours: {account} neither belongs to {owner} "
        "nor owns it; hook may be skipped",
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
