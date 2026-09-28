"""Self-test for guard_no_verify.py against the live GitHub API.

Ownership is resolved by asking GitHub, so these fixtures are throwaway git
repos whose `origin` names a repo that really does (or really does not)
belong to the account gh is authenticated as. Running against the live API
is the point: a mocked enumeration would not catch a wrong endpoint.

Fixtures are chosen from real repositories, so the expected verdict is
derived from GitHub's own answer:

  * a repo the account owns            -> ENFORCED
  * a repo under one of its orgs       -> ENFORCED
  * a repo the account does not own    -> EXEMPT
  * a repo name that does not exist    -> EXEMPT
  * an unparseable or absent remote     -> ERROR (treated as ENFORCED)

The ERROR fixtures are the important ones: an unanswerable question must
never become a free pass.
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import List, Optional, Tuple

SCRIPT = Path(__file__).resolve().parent / "guard_no_verify.py"

# Fixtures that do not depend on what the account happens to own.
FIXTURES: List[Tuple[str, Optional[str], str]] = [
    # External — the account neither owns these nor belongs to their orgs.
    ("external: rust-lang", "git@github.com:rust-lang/rust.git", "EXEMPT"),
    ("external: serde-rs", "https://github.com/serde-rs/serde.git", "EXEMPT"),
    ("external: torvalds", "https://github.com/torvalds/linux.git", "EXEMPT"),
    # A repo name under the account that does not exist: GitHub reports no
    # such repository, so the account does not own it.
    ("absent repo name", "git@github.com:eastspire/__no_such_repo_9f2c.git", "EXEMPT"),
    # Unparseable / absent remote -> ERROR, which callers treat as ENFORCED.
    ("non-github remote", "git@example.com:someone/repo.git", "ERROR"),
    ("no remote", None, "ERROR"),
]


def gh_json(endpoint: str, jq: str) -> Optional[str]:
    """Query the gh CLI, returning stdout or None."""
    try:
        result = subprocess.run(
            ["gh", "api", endpoint, "--jq", jq],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    return result.stdout


def live_owned_fixtures() -> List[Tuple[str, Optional[str], str]]:
    """Build ENFORCED fixtures from repos the account actually owns."""
    account = (gh_json("user", ".login") or "").strip()
    if not account:
        return []

    out: List[Tuple[str, Optional[str], str]] = []

    personal = gh_json(
        f"users/{account}/repos?per_page=100&affiliation=owner", ".[] | .name"
    )
    if personal:
        names = [n.strip() for n in personal.splitlines() if n.strip()]
        for name in names[:2]:
            out.append(
                (
                    f"owned personal: {name}",
                    f"git@github.com:{account}/{name}.git",
                    "ENFORCED",
                )
            )

    orgs_out = gh_json("/user/orgs", ".[].login") or ""
    orgs = [o.strip() for o in orgs_out.splitlines() if o.strip()]
    for org in orgs:
        repos_out = gh_json(f"orgs/{org}/repos?per_page=100", ".[] | .name") or ""
        names = [n.strip() for n in repos_out.splitlines() if n.strip()]
        if names:
            out.append(
                (
                    f"owned org: {org}/{names[0]}",
                    f"git@github.com:{org}/{names[0]}.git",
                    "ENFORCED",
                )
            )
    return out


def make_repo(tmp: Path, label: str, remote: Optional[str]) -> Path:
    """Create a throwaway git repo with the given origin remote."""
    repo = tmp / label.replace(" ", "_").replace("/", "_").replace(",", "")
    repo.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    subprocess.run(
        ["git", "-C", str(repo), "config", "user.email", "t@t.vip"], check=True
    )
    subprocess.run(["git", "-C", str(repo), "config", "user.name", "t"], check=True)
    if remote:
        subprocess.run(
            ["git", "-C", str(repo), "remote", "add", "origin", remote], check=True
        )
    return repo


def run(repo: Path) -> Tuple[str, int]:
    """Invoke the classifier and return (verdict, exit code)."""
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--repo", str(repo), "--json"],
        capture_output=True,
        text=True,
        timeout=120,
    )
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError:
        return f"UNPARSEABLE({result.stdout!r} {result.stderr!r})", result.returncode
    return payload["verdict"], result.returncode


def main() -> int:
    """Run every fixture and report failures."""
    owned = live_owned_fixtures()
    fixtures = owned + FIXTURES
    failures = []

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        for label, remote, expected in fixtures:
            repo = make_repo(tmp, label, remote)
            verdict, rc = run(repo)
            ok = verdict == expected
            print(f"{'PASS' if ok else 'FAIL'}  {label:34} -> {verdict:9} rc={rc}")
            if not ok:
                failures.append(f"{label}: expected {expected}, got {verdict}")

    if not owned:
        print("\nWARNING: gh unavailable, so no ENFORCED fixture was exercised")

    if failures:
        print("\nFAILURES:")
        for line in failures:
            print(f"  - {line}")
        return 1
    print(f"\nall {len(fixtures)} fixtures passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
