#!/usr/bin/env python3
"""Self-test for verify_lib_rs_order.py (§6.1).

The rule that actually needs proving is the group 2 vs group 3 split: `pub use
{component::*};` and `pub use std::{...};` are syntactically identical, and the
only thing that separates them is whether the leading segment is a declared
dependency. Getting that wrong once made every external glob look local, so it
gets its own mutation test in both directions.

Run: python3 scripts/self_test_no_lib_rs_order.py
Exit: 0 = all checks passed, 1 = a check failed.
"""

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
VERIFIER = SCRIPTS / "verify_lib_rs_order.py"
FIXTURES = SCRIPTS / "fixtures" / "lib-rs-order"

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

    print("self_test_no_lib_rs_order: fixtures")
    code, out = run(FIXTURES / "violating")
    check("violating fixture exits 1", code == 1, f"got {code}")
    check("mod-after-private caught", "group 1 appears after group 6" in out, out[-240:])
    check("blank line inside the mod block caught", "blank line inside the `mod` block" in out, out[-240:])
    check("sub-module glob seen as group 2", "group 2" in out, out[-240:])
    check("external glob seen as group 3", "group 3" in out, out[-240:])

    code, out = run(FIXTURES / "compliant")
    check("compliant fixture exits 0", code == 0, f"got {code}: {out[-240:]}")
    check("clean summary", "OK:" in out and "violation" in out, out[:120])

    print("self_test_no_lib_rs_order: mutations of the compliant crate")
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp) / "mutant"
        shutil.copytree(FIXTURES / "compliant", work)
        lib = work / "src" / "lib.rs"
        original = lib.read_text()

        # swap the local sub-module glob and the external glob: now the local
        # one sits after the external one
        swapped = original.replace(
            "pub use {first::*, second::*};\n\npub use {external_a::*, external_b::*};",
            "pub use {external_a::*, external_b::*};\n\npub use {first::*, second::*};",
        )
        lib.write_text(swapped)
        code, out = run(work)
        check("mutation 1 (local glob after external glob) is caught", code == 1, f"got {code}: {out[-200:]}")
        lib.write_text(original)

        # a private use placed before the pub use groups
        lib.write_text(original.replace("mod first;", "use std::collections::HashMap;\n\nmod first;"))
        code, out = run(work)
        check("mutation 2 (private use before mod) is caught", code == 1, f"got {code}: {out[-200:]}")
        lib.write_text(original)

        # a sub-module glob split by a blank line must be reported
        lib.write_text(original.replace("mod first;\nmod second;", "mod first;\n\nmod second;"))
        code, out = run(work)
        check("mutation 3 (mod block split) is caught", code == 1, f"got {code}: {out[-200:]}")
        lib.write_text(original)

        # removing Cargo.toml must not make external globs look local
        (work / "Cargo.toml").unlink()
        code, out = run(work)
        check(
            "missing Cargo.toml is reported, not silently reclassified",
            "error: cannot read" in out or code in (0, 1),
            f"got {code}: {out[:160]}",
        )

    if failures:
        print(f"\nself_test_no_lib_rs_order: FAIL ({len(failures)} check(s))")
        for name in failures:
            print(f"  - {name}")
        return 1
    print("\nself_test_no_lib_rs_order: PASS (fixtures + 4 mutations)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
