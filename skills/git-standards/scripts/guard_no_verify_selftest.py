"""Self-test for guard_no_verify.py: owned vs fork, plus failure modes.

Fixtures are throwaway git repos with a synthetic `origin` remote. The
GitHub query is the only network-dependent step, so a repo whose fork
state cannot be read must land on ENFORCED — that is the property this
test exists to pin.
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Optional

SCRIPT = Path(__file__).resolve().parent / "guard_no_verify.py"

# (label, remote URL, expected verdict, needs GitHub)
FIXTURES = [
    ("owned org, non-fork", "git@github.com:euv-dev/euv.git", "ENFORCED", True),
    ("owned org 2", "https://github.com/crates-dev/ctares.git", "ENFORCED", True),
    ("personal, non-fork", "git@github.com:eastspire/stripe-pay-sdk.git", "ENFORCED", True),
    ("external fork", "https://github.com/eastspire/FrameworkBenchmarks.git", "EXEMPT", True),
    ("external fork 2", "git@github.com:eastspire/web-frameworks.git", "EXEMPT", True),
    ("non-github remote", "git@example.com:someone/repo.git", "ERROR", False),
    ("no remote", None, "ERROR", False),
]


def make_repo(tmp: Path, label: str, remote: Optional[str]) -> Path:
    repo = tmp / label.replace(" ", "_").replace(",", "")
    repo.mkdir(parents=True)
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


def run(repo: Path) -> tuple[str, int]:
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--repo", str(repo), "--json"],
        capture_output=True,
        text=True,
        timeout=90,
    )
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError:
        return f"UNPARSEABLE({result.stdout!r} {result.stderr!r})", result.returncode
    return payload["verdict"], result.returncode


def main() -> int:
    failures: list[str] = []
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        for label, remote, expected, needs_github in FIXTURES:
            repo = make_repo(tmp, label, remote)
            verdict, rc = run(repo)
            ok = verdict == expected
            if not needs_github and verdict != expected:
                ok = False
            print(f"{'PASS' if ok else 'FAIL'}  {label:24} -> {verdict:9} rc={rc}")
            if not ok:
                failures.append(f"{label}: expected {expected}, got {verdict}")

    if failures:
        print("\nFAILURES:")
        for line in failures:
            print(f"  - {line}")
        return 1
    print(f"\nall {len(FIXTURES)} fixtures passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
