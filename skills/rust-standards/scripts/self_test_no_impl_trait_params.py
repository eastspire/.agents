#!/usr/bin/env python3
"""Self-test for verify_no_impl_trait_params.py (§9.2).

A verifier that has never been shown a violation is not evidence of anything.
This runs the real script against real fixtures and then MUTATES the compliant
fixture to prove each guard actually fires — a verifier that silently stopped
detecting would otherwise pass the happy path forever.

Run: python3 scripts/self_test_no_impl_trait_params.py
Exit: 0 = all checks passed, 1 = a check failed.
"""

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
VERIFIER = SCRIPTS / "verify_no_impl_trait_params.py"
FIXTURES = SCRIPTS / "fixtures" / "impl-trait-params"

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
    if not FIXTURES.is_dir():
        print(f"FAIL: fixtures missing: {FIXTURES}")
        return 1

    print("self_test_no_impl_trait_params: fixtures")
    code, out = run(FIXTURES / "violating")
    check("violating fixture exits 1", code == 1, f"got {code}")
    check("violating fixture reports 3 hits", "3 violation(s)" in out, out[-200:])
    check(
        "cites all three violating fns",
        all(f":{ln}:" in out for ln in (7, 12, 17)),
        out[-200:],
    )

    code, out = run(FIXTURES / "compliant")
    check("compliant fixture exits 0", code == 0, f"got {code}")
    check("compliant fixture reports 0", "0 violation(s)" in out, out[-200:])

    print("self_test_no_impl_trait_params: mutations of the compliant fixture")
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp) / "mutant"
        shutil.copytree(FIXTURES / "compliant", work)

        # 1. add a parameter-position impl Trait
        target = work / "generic_params.rs"
        original = target.read_text()
        target.write_text(
            original + "\n/// added by self-test\npub fn bad(v: impl Display) -> String {\n    format!(\"{v}\")\n}\n"
        )
        code, out = run(work)
        check("mutation 1 (param impl Trait) is caught", code == 1, f"got {code}: {out[-160:]}")
        target.write_text(original)

        # 2. a raw string whose body contains the word — must NOT be flagged,
        #    and must not desynchronise the rest of the file
        target.write_text(
            original
            + '\n/// ```\n/// let pattern = r"impl Trait";\n/// ```\npub fn later(v: impl Display) -> String { format!("{v}") }\n'
        )
        code, out = run(work)
        check(
            "mutation 2 (raw string + real violation) flags exactly 1",
            code == 1 and "1 violation(s)" in out,
            out[-200:],
        )
        target.write_text(original)

        # 3. return-position only — must stay silent (guards against a blanket sweep)
        target.write_text(original + "\npub fn ok() -> impl Iterator<Item = u8> { core::iter::empty() }\n")
        code, out = run(work)
        check("mutation 3 (return impl Trait only) stays clean", code == 0, f"got {code}: {out[-160:]}")
        target.write_text(original)

        # 4. usage error path
        code, _ = run(work / "does_not_exist")
        check("missing directory exits 2", code == 2, f"got {code}")

    if failures:
        print(f"\nself_test_no_impl_trait_params: FAIL ({len(failures)} check(s))")
        for name in failures:
            print(f"  - {name}")
        return 1
    print("\nself_test_no_impl_trait_params: PASS (fixtures + 4 mutations)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
