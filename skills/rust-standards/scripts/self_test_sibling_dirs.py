#!/usr/bin/env python3
"""Self-test for verify_no_sibling_dirs.py (§1.3d, tightened 2026-09-29).

Run:  python3 scripts/self_test_sibling_dirs.py

Exits 0 when the verifier discriminates correctly in both directions, 1
otherwise.  The rule is structural, so a verifier that is silently
permissive is indistinguishable from a correct one by reading it -- only
a fixture with a known answer can tell them apart.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
FIXTURES = HERE / "fixtures" / "sibling-dirs"

EXPECTED_VIOLATING = {
    "renderer": [
        "const.rs", "enum.rs", "fn.rs", "impl.rs", "struct.rs", "trait.rs",
    ],
    "vdom": ["impl.rs", "struct.rs"],
}


def load() -> Any:
    """Import the verifier the same way staged_file_gate.py does."""
    spec = importlib.util.spec_from_file_location(
        "sib", HERE / "verify_no_sibling_dirs.py"
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load verify_no_sibling_dirs.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    module = load()
    failures: list[str] = []

    # --- compliant: 0 findings, exit 0 -------------------------------
    compliant_root = FIXTURES / "compliant"
    if not compliant_root.is_dir():
        failures.append("compliant fixture directory missing")
    for path in sorted(compliant_root.rglob("*.rs")):
        findings = list(module.audit_one(path))
        if findings:
            failures.append(
                f"compliant: {path.relative_to(FIXTURES)} -> {len(findings)} finding(s)"
            )

    # --- violating: every keyword file beside a subdir is reported ---
    for dirname, expected_files in EXPECTED_VIOLATING.items():
        target = FIXTURES / "violating" / dirname
        if not target.is_dir():
            failures.append(f"violating fixture directory missing: {target}")
            continue
        for name in expected_files:
            candidate = target / name
            if not candidate.is_file():
                failures.append(f"violating fixture file missing: {candidate}")
                continue
            findings = list(module.audit_one(candidate))
            if not findings:
                failures.append(f"violating: {name} in {dirname}/ -> 0 findings (expected >=1)")

    # --- explicit leaf cases: keyword file with NO subdir is legal ---
    for name in ("leaf/impl.rs", "leaf/sub.rs"):
        candidate = FIXTURES / "violating" / name
        if candidate.is_file():
            findings = list(module.audit_one(candidate))
            if findings:
                failures.append(f"leaf: {name} -> {len(findings)} finding(s) (expected 0)")

    # --- exit codes ---------------------------------------------------
    import subprocess

    script = str(HERE / "verify_no_sibling_dirs.py")
    ok_rc = subprocess.run(
        [sys.executable, script, str(FIXTURES / "compliant")],
        capture_output=True, text=True,
    )
    if ok_rc.returncode != 0:
        failures.append(f"compliant tree exit {ok_rc.returncode} (expected 0)")

    bad_rc = subprocess.run(
        [sys.executable, script, str(FIXTURES / "violating")],
        capture_output=True, text=True,
    )
    if bad_rc.returncode == 0:
        failures.append("violating tree exit 0 (expected non-zero)")

    if failures:
        print("sibling-dirs self-test: FAIL")
        for item in failures:
            print(f"  - {item}")
        return 1

    print("sibling-dirs self-test: PASS")
    print(
        f"  compliant -> 0 findings, exit 0\n"
        f"  violating -> {len(EXPECTED_VIOLATING)} dirs, "
        f"{sum(len(v) for v in EXPECTED_VIOLATING.values())} keyword files, exit 1\n"
        f"  leaf keyword files beside no sub-directory -> 0 findings (exempt-by-shape)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
