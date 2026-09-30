#!/usr/bin/env python3
"""Self-test for verify_ci_no_bump.py (§17).

Proves both violation classes fire, that the allowlist marker works, and that
the read-only version-extraction pipeline is NOT flagged — that last one is the
false positive that would make this rule unusable, so it is tested explicitly.

Run: python3 scripts/self_test_no_ci_no_bump.py
Exit: 0 = all checks passed, 1 = a check failed.
"""

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
VERIFIER = SCRIPTS / "verify_ci_no_bump.py"
FIXTURES = SCRIPTS / "fixtures" / "ci-no-bump"

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

    print("self_test_no_ci_no_bump: fixtures")
    code, out = run(FIXTURES / "violating")
    check("violating fixture exits 1", code == 1, f"got {code}")
    check("class BUMP caught (cc/crate/cargo)", out.count("BUMP") == 3, out[-200:])
    check("class WRITE caught (sed -i / perl -pi)", out.count("WRITE") == 2, out[-200:])
    check("flags are reported", "--patch" in out and "--minor" in out, out[-200:])
    check(
        "allowlist marker exempts the line below it",
        "allowed.yml" not in out,
        out[-200:],
    )

    code, out = run(FIXTURES / "compliant")
    check("compliant fixture exits 0", code == 0, f"got {code}: {out[-200:]}")
    check("read-only version extraction is allowed", "0" not in out.split("OK:")[-1][:3], out[-200:])
    check("cargo publish is not a violation", "publish" not in out, out[-200:])

    print("self_test_no_ci_no_bump: mutations of the compliant workflow")
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp) / "mutant"
        shutil.copytree(FIXTURES / "compliant", work)
        wf = work / ".github" / "workflows" / "ci.yml"
        original = wf.read_text()

        wf.write_text(original + "      - run: cc bump --major\n")
        code, out = run(work)
        check("mutation 1 (bare cc bump) is caught", code == 1, f"got {code}: {out[-160:]}")
        wf.write_text(original)

        # the allowlist marker must be on the line DIRECTLY above: putting a
        # different step between marker and bump must NOT exempt it
        wf.write_text(
            original + "      # ci-allow-version-write: reason\n"
            "      - run: echo unrelated\n"
            "      - run: crate bump --patch\n"
        )
        code, out = run(work)
        check("mutation 2 (marker not adjacent) still caught", code == 1, f"got {code}: {out[-160:]}")
        wf.write_text(original)

        # a repo that exists but has no .github/workflows is clean
        empty = work / "empty"
        empty.mkdir()
        code, out = run(empty)
        check(
            "repo without .github/workflows is a clean INFO",
            code == 0 and out.startswith("INFO:"),
            f"got {code}: {out[:120]}",
        )

        # a path that does not exist at all IS a usage error
        code, out = run(work / "nowhere")
        check("nonexistent path exits 2", code == 2, f"got {code}")

    if failures:
        print(f"\nself_test_no_ci_no_bump: FAIL ({len(failures)} check(s))")
        for name in failures:
            print(f"  - {name}")
        return 1
    print("\nself_test_no_ci_no_bump: PASS (fixtures + 3 mutations)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
