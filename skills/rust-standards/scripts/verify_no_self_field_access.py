#!/usr/bin/env python3
"""§17.3 / §17.12 verifier: direct `self.field` access is forbidden.

Rule (2026-09-26 user directive):
  "禁止通过self直接操作字段,使用Data宏的get和set"

All field reads/writes in production code MUST go through the
lombok-`Data`-generated (or hand-written per §17.11) accessors
`get_<field>` / `get_<field>_ref` / `get_<field>_mut` / `set_<field>`.

LEGAL `self.field` positions (§17.12, scanned as exemptions):
  1. Hand-written accessor bodies: fns named `get_*` / `set_*` /
     `try_get_*` (the accessor implementation itself).
  2. `impl Debug for ...` / `impl Display for ...` blocks (§17.3:
     Debug / Display 实现内部允许).
  3. `#[cfg(test)]` blocks and the `tests/` directory.

Everything else — business methods, builders, trait impls other than
Debug/Display, `default()`, `drop()` — MUST use accessors.

Detection:
  - `self.<ident>` NOT followed by `(` (method calls are accessors by
    definition and are never flagged).  The `Pin<&mut Self>` idiom
    `let this = self.get_mut();` rebinds self, so `this.<ident>` is
    flagged the same way.
  - `self::<path>` (module path) is not field access; skipped.
  - Tuple-field access `self.0` is not covered (known limitation).

Exit code: 0 = compliant, 1 = violations, 2 = usage error.
"""

import re
import subprocess
import sys
from pathlib import Path

FIELD_ACCESS = re.compile(r"\b(?:self|this)\.([a-z_][a-z0-9_]*)\b(?!\s*\()")
FN_START = re.compile(
    r"^\s*(?:pub(?:\([^)]*\))?\s+)?(?:async\s+)?(?:unsafe\s+)?fn\s+([a-z_][a-z0-9_]*)"
)
TRAIT_IMPL_OK = re.compile(r"^\s*impl(?:<[^>]*>)?\s+(?:\w+::)*(Debug|Display)\s+for\s")
ACCESSOR_FN = re.compile(r"^(get|set|try_get)_[a-z0-9_]+$|^new$")
CFG_TEST = re.compile(r"^\s*#\[cfg\(test\)\]")


def list_rs_files(root: Path) -> list[Path]:
    result = subprocess.run(
        [
            "find",
            str(root),
            "-name",
            "*.rs",
            "-not",
            "-path",
            "*/target/*",
            "-not",
            "-path",
            "*/.cargo/registry/*",
        ],
        capture_output=True,
        text=True,
    )
    return [Path(line) for line in result.stdout.splitlines() if line.strip()]


def _brace_delta(line: str) -> int:
    return line.count("{") - line.count("}")


def _exempt_ranges(lines: list[str]) -> list[tuple[int, int]]:
    """Return 0-based inclusive (start, end) ranges where self.field is
    legal: accessor fn bodies, Debug/Display impl blocks, cfg(test)
    items."""
    ranges: list[tuple[int, int]] = []
    idx = 0
    total = len(lines)
    while idx < total:
        line = lines[idx]
        if CFG_TEST.match(line):
            j = idx
            while j < total and "{" not in lines[j]:
                j += 1
            if j < total:
                depth = 0
                k = j
                while k < total:
                    depth += _brace_delta(lines[k])
                    if depth == 0:
                        break
                    k += 1
                ranges.append((idx, min(k, total - 1)))
                idx = k + 1
                continue
        trait_match = TRAIT_IMPL_OK.match(line)
        fn_match = FN_START.match(line)
        is_accessor = fn_match is not None and ACCESSOR_FN.match(
            fn_match.group(1)
        )
        if trait_match or is_accessor:
            j = idx
            while j < total and "{" not in lines[j]:
                j += 1
            if j < total:
                depth = 0
                k = j
                while k < total:
                    depth += _brace_delta(lines[k])
                    if depth == 0:
                        break
                    k += 1
                ranges.append((idx, min(k, total - 1)))
                idx = k + 1
                continue
        idx += 1
    return ranges


def audit_one(path: Path) -> list[str]:
    try:
        text = path.read_text()
    except (OSError, UnicodeDecodeError):
        return []
    if "tests" in path.parts:
        return []
    lines = text.splitlines()
    exempt = _exempt_ranges(lines)
    violations: list[str] = []
    range_idx = 0
    for number, line in enumerate(lines):
        while range_idx < len(exempt) and number > exempt[range_idx][1]:
            range_idx += 1
        if range_idx < len(exempt) and exempt[range_idx][0] <= number <= exempt[range_idx][1]:
            continue
        stripped = line.strip()
        if stripped.startswith("//"):
            continue
        for match in FIELD_ACCESS.finditer(line):
            violations.append(
                f"{path}:{number + 1}: direct `self.{match.group(1)}` field "
                f"access forbidden; use Data-macro accessor "
                f"(§17.3 / §17.12): {stripped[:80]!r}"
            )
    return violations


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    if not root.is_dir():
        print(f"error: {root} is not a directory", file=sys.stderr)
        return 2
    all_violations: list[str] = []
    file_count = 0
    for path in list_rs_files(root):
        violations = audit_one(path)
        if violations:
            file_count += 1
            all_violations.extend(violations)
    for violation in all_violations:
        print(violation)
    print(
        f"\n=== no-self-field-access: {len(all_violations)} violation(s) "
        f"in {file_count} file(s) ==="
    )
    return 1 if all_violations else 0


if __name__ == "__main__":
    sys.exit(main())
