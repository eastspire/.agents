"""Self-test for guard_no_verify.py: owned vs external, plus failure modes.

The rule is ownership, not forking. Fixtures are throwaway git repos with
a synthetic `origin` remote. No network call is involved, so the expected
verdict is decided purely by the owner in the remote URL — a repo whose
origin cannot be read must land on ERROR, which callers treat as ENFORCED.
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Optional

SCRIPT = Path(__file__).resolve().parent / "guard_no_verify.py"

# (label, remote URL, expected verdict)
FIXTURES = [
    # Owned owners — always enforced, fork status irrelevant.
    ("owned org euv-dev", "git@github.com:euv-dev/euv.git", "ENFORCED"),
    ("owned org hyperlane-dev", "https://github.com/hyperlane-dev/hyperlane.git", "ENFORCED"),
    ("owned org crates-dev", "git@github.com:crates-dev/ctares.git", "ENFORCED"),
    ("owned org docs-pages", "git@github.com:docs-pages/docs.git", "ENFORCED"),
    ("owned personal", "git@github.com:eastspire/stripe-pay-sdk.git", "ENFORCED"),
    ("owned personal fork", "git@github.com:eastspire/serde.git", "ENFORCED"),
    ("owned token url", "https://x-access-token:tok@github.com/euv-dev/euv.git", "ENFORCED"),
    # Anything else is external and may be skipped — no fork check. Note
    # eastspire/* stays ENFORCED even when it is a fork: the owner decides.
    ("external fork", "https://github.com/torvalds/linux.git", "EXEMPT"),
    ("external non-fork", "git@github.com:rust-lang/rust.git", "EXEMPT"),
    ("external third party", "https://github.com/serde-rs/serde.git", "EXEMPT"),
    # Unidentifiable — never exempt.
    ("non-github remote", "git@example.com:someone/repo.git", "ERROR"),
    ("no remote", None, "ERROR"),
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


def run(repo: Path) -> tuple:
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--repo", str(repo), "--json"],
        capture_output=True,
        text=True,
        timeout=60,
    )
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError:
        return f"UNPARSEABLE({result.stdout!r} {result.stderr!r})", result.returncode
    return payload["verdict"], result.returncode


def main() -> int:
    failures = []
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        for label, remote, expected in FIXTURES:
            repo = make_repo(tmp, label, remote)
            verdict, rc = run(repo)
            ok = verdict == expected
            print(f"{'PASS' if ok else 'FAIL'}  {label:26} -> {verdict:9} rc={rc}")
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
