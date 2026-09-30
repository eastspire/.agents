#!/usr/bin/env python3
"""Self-test for verify_module_imports_centralized.py (§6.1 / §6.3 / §6.4).

Three independent sub-rules, so three independent groups of checks. The one that
matters most is the compliant side: a sub-file with NO `use` at all is
explicitly allowed by the 2026-09-26 relaxation, and an over-eager verifier that
flags it would push every file back toward a mandatory import.

Run: python3 scripts/self_test_no_module_imports_centralized.py
Exit: 0 = all checks passed, 1 = a check failed.
"""

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
VERIFIER = SCRIPTS / "verify_module_imports_centralized.py"
FIXTURES = SCRIPTS / "fixtures" / "module-imports-centralized"

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

    print("self_test_no_module_imports_centralized: fixtures")
    code, out = run(FIXTURES / "violating")
    check("violating fixture exits 1", code == 1, f"got {code}")
    check("§6.1 private use in lib.rs caught", "cannot reach any sub-file" in out, out[-200:])
    check("§6.1 does not flag `use self::`", "use self::inner::Helper" not in out, out[-200:])
    check("§6.2 comment in mod.rs caught", "comment in a mod.rs body" in out, out[-200:])
    check("§6.2 blank line inside the mod block caught", "blank line inside the `mod` block" in out, out[-200:])
    check("§6.2 stage order caught", "must precede stage 2" in out, out[-200:])
    check("§6.2 non-pub re-export caught", "must be `pub use`" in out, out[-200:])
    check("§6.3/§6.4 sub-file import caught", "may only import `use super::*;`" in out, out[-200:])

    code, out = run(FIXTURES / "compliant")
    check("compliant fixture exits 0", code == 0, f"got {code}: {out[-240:]}")
    check("a sub-file with no use is allowed", "0 violation(s)" in out, out[-240:])

    print("self_test_no_module_imports_centralized: mutations of the compliant crate")
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp) / "mutant"
        shutil.copytree(FIXTURES / "compliant", work)

        lib = work / "src" / "lib.rs"
        original = lib.read_text()
        lib.write_text(original.replace("pub use std::collections::HashMap;", "use std::collections::HashMap;"))
        code, out = run(work)
        check("mutation 1 (pub use -> use) is caught", code == 1, f"got {code}: {out[-160:]}")
        lib.write_text(original)

        sub = work / "src" / "render" / "fn.rs"
        original_sub = sub.read_text()
        sub.write_text(original_sub.replace("use super::*;", "use super::*;\nuse std::fmt::Debug;"))
        code, out = run(work)
        check("mutation 2 (extra import in sub-file) is caught", code == 1, f"got {code}: {out[-160:]}")
        sub.write_text(original_sub)

        mod = work / "src" / "inner" / "mod.rs"
        original_mod = mod.read_text()
        # splitting the mod block is the §6.2 blank-line violation
        mod.write_text(original_mod.replace("mod r#struct;\nmod r#fn;", "mod r#struct;\n\nmod r#fn;"))
        code, out = run(work)
        check("mutation 3 (mod block split by a blank line) is caught", code == 1, f"got {code}: {out[-160:]}")
        mod.write_text(original_mod)
        mod.write_text(original_mod + "\n// a late comment\n")
        code, out = run(work)
        check("mutation 4 (comment in mod.rs) is caught", code == 1, f"got {code}: {out[-160:]}")

        code, out = run(work / "nope")
        check("nonexistent path exits 2", code == 2, f"got {code}")

    if failures:
        print(f"\nself_test_no_module_imports_centralized: FAIL ({len(failures)} check(s))")
        for name in failures:
            print(f"  - {name}")
        return 1
    print("\nself_test_no_module_imports_centralized: PASS (fixtures + 5 mutations)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
