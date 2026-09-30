#!/usr/bin/env python3
"""Self-test for verify_no_test_comments.py (§14.5).

Proves the verifier fires on every banned comment form and stays silent on the
look-alike that matters most — a `//` inside a string literal.

Run: python3 scripts/self_test_no_test_comments.py
Exit: 0 = all checks passed, 1 = a check failed.
"""

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
VERIFIER = SCRIPTS / "verify_no_test_comments.py"
FIXTURES = SCRIPTS / "fixtures" / "test-comments"

failures: list[str] = []


def run(target: Path) -> tuple[int, str]:
    proc = subprocess.run(
        [sys.executable, str(VERIFIER), str(target)],
        capture_output=True, text=True,
    )
    return proc.returncode, proc.stdout


def check(name: str, condition: bool, detail: str = "") -> None:
    if condition:
        print(f"  ok   {name}")
    else:
        print(f"  FAIL {name}{(' — ' + detail) if detail else ''}")
        failures.append(name)


def main() -> int:
    if not VERIFIER.exists():
        print(f"FAIL: verifier missing: {VERIFIER}")
        return 1

    print("self_test_no_test_comments: fixtures")
    code, out = run(FIXTURES / "violating")
    check("violating fixture exits 1", code == 1, f"got {code}")
    for form, label in (
        ("//!", "inner doc comment"),
        ("// ", "line comment"),
        ("///", "doc comment"),
        ("/*", "block comment"),
    ):
        check(f"flags {label}", form in out, out[-160:])

    code, out = run(FIXTURES / "compliant")
    check("compliant fixture exits 0", code == 0, f"got {code}: {out[-160:]}")
    check(
        "// inside a string is not a comment",
        "0 violation(s)" in out,
        out[-160:],
    )

    print("self_test_no_test_comments: mutations of the compliant fixture")
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp) / "mutant"
        shutil.copytree(FIXTURES / "compliant", work)
        target = work / "tests" / "clean_test.rs"
        original = target.read_text()

        target.write_text(original + "\n#[test]\nfn added() {\n    // comment\n    assert!(true);\n}\n")
        code, out = run(work)
        check("mutation 1 (line comment) is caught", code == 1, f"got {code}: {out[-160:]}")
        target.write_text(original)

        # a comment in a PRODUCTION file must not be reported by this rule
        prod = work / "lib.rs"
        prod.write_text("//! production docs are fine\npub fn helper() {}\n")
        code, out = run(work)
        check("mutation 2 (production file) stays clean", code == 0, f"got {code}: {out[-160:]}")
        prod.unlink()

        code, _ = run(work / "nope")
        check("missing directory exits 2", code == 2, f"got {code}")

    if failures:
        print(f"\nself_test_no_test_comments: FAIL ({len(failures)} check(s))")
        for name in failures:
            print(f"  - {name}")
        return 1
    print("\nself_test_no_test_comments: PASS (fixtures + 3 mutations)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
