#!/usr/bin/env python3
"""Self-test for verify_no_panicking_borrow.py.

A verifier that never fails proves nothing, so this checks both directions:

  1. The compliant fixture tree reports 0 violations and exits 0.
  2. The violating fixture tree reports >0 violations and exits 1.
  3. Mutation testing: three independent breakages of the verifier are each
     injected, and each must change an outcome. If a mutation is NOT caught,
     the verifier has a code path that does not affect its result and the
     fixtures do not pin it.

Exit 0 = self-test passed, 1 = self-test failed.
"""

import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
VERIFIER = HERE / "verify_no_panicking_borrow.py"
FIXTURES = HERE / "fixtures" / "refcell-borrow"


def run(tree: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["python3", str(VERIFIER), str(FIXTURES / tree)],
        capture_output=True,
        text=True,
    )


def main() -> int:
    failures: list[str] = []

    compliant = run("compliant")
    if compliant.returncode != 0:
        failures.append(
            f"compliant tree should exit 0, got {compliant.returncode}:\n"
            f"{compliant.stdout}"
        )

    violating = run("violating")
    if violating.returncode != 1:
        failures.append(
            f"violating tree should exit 1, got {violating.returncode}:\n"
            f"{violating.stdout}"
        )

    original = VERIFIER.read_text()
    mutations = [
        (
            "re-entrancy pattern neutralised",
            "REENTRANT = re.compile(",
            'REENTRANT = re.compile(r"ZZZ_NEVER_ZZZ") or re.compile(',
            "violating",
            0,
        ),
        (
            "guard scope tracking disabled",
            "if depth < d]:",
            "if False]:",
            "compliant",
            1,
        ),
        (
            "guard-binding pattern neutralised",
            "GUARD_BIND = re.compile(",
            'GUARD_BIND = re.compile(r"ZZZ") or re.compile(',
            "violating",
            0,
        ),
    ]
    for label, anchor, replacement, tree, expected in mutations:
        if anchor not in original:
            failures.append(f"mutation anchor missing: {label!r} ({anchor!r})")
            continue
        try:
            VERIFIER.write_text(original.replace(anchor, replacement, 1))
            result = run(tree)
            if result.returncode != expected:
                failures.append(
                    f"mutation NOT caught: {label} "
                    f"(tree={tree} expected exit {expected}, "
                    f"got {result.returncode})"
                )
        finally:
            VERIFIER.write_text(original)

    for failure in failures:
        print(f"FAIL: {failure}")
    if failures:
        print(f"\nself_test_no_panicking_borrow: {len(failures)} failure(s)")
        return 1
    print("self_test_no_panicking_borrow: PASS (fixtures + 3 mutations)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
