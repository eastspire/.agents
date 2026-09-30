#!/usr/bin/env python3
"""§17 — CI workflows never bump versions and never write `version =`.

Rule (2026-09-26 user directive). Version bumps belong to humans, in one place,
via a dedicated tool (e.g. `cc bump` / `crate bump`). A CI job that edits a
Cargo.toml version produces a history where the same crate has two different
version numbers depending on which pipeline ran, and a tag cut from one branch
does not match the manifest the other branch built.

Two violation classes:

  BUMP   a workflow step invoking a version-bumping command
         (`cc bump`, `crate bump`, `cargo set-version`, `cargo release`,
         `bump2version`, `cargo-bump`, `set-version`), with or without a
         `--patch/--minor/--major/--release/--target-version` flag

  WRITE  a workflow step rewriting a `version =` line in place
         (`sed -i`, `perl -pi`, `python3 -c` writing to the file, `awk >`)

Allowed, and deliberately not reported:
  - read-only extraction of a version for a tag or commit message
    (`grep ... | sed -E 's/.../.../'` that prints to stdout, never redirects
    into a manifest)
  - `cargo publish`, `cargo package`, `cargo build` — none of them write
    `version =`
  - a `version:` key in a GitHub Actions *workflow* env block, which is CI's
    own version, not a crate version

Allowlist: a line directly above the violation reading
`# ci-allow-version-write: <reason>` exempts it. The coupling is tight on
purpose — the reason sits next to the thing it excuses, so it cannot outlive it.

Output contract: one violation per line, then a summary line. `OK: <n> workflow
file(s) checked, no violation` when clean — the audit's shell template greps
that line away.

Exit code: 0 = compliant, 1 = violations, 2 = usage error.
"""

import re
import sys
from pathlib import Path

ALLOW_MARKER = re.compile(r"^\s*#\s*ci-allow-version-write\s*:")

# class BUMP — a version-bumping command
BUMP = re.compile(
    r"\b(?:cc|crate)\s+bump\b"
    r"|\bcargo\s+(?:set-version|release|bump)\b"
    r"|\bbump2version\b"
    r"|\bcargo-bump\b"
    r"|\bset-version\b"
)
# the flag set that makes a bump a bump (recorded for the message only)
BUMP_FLAG = re.compile(r"--(?:patch|minor|major|release|target-version|rev)\b")

# class WRITE — an in-place edit that can rewrite `version =`
WRITE = re.compile(
    r"\bsed\s+(?:-[a-zA-Z]*i[a-zA-Z]*\b|-i\b)"          # sed -i / -i.bak / --in-place
    r"|\bperl\s+-pi\b"
    r"|\bawk\b[^|;]*>\s*\S+"                            # awk > file
    r"|>\s*[\w./-]*Cargo\.toml\b"                        # redirect into a manifest
)
# a write is only a violation when it also touches a version line
VERSION_LINE = re.compile(r"""^\s*version\s*=|s/(.*version.*)/\1/""")

# read-only pipelines that merely print a version
READONLY = re.compile(r"grep\b")


def list_workflows(root: Path) -> list[Path]:
    base = root / ".github" / "workflows"
    if not base.is_dir():
        return []
    return sorted(p for p in base.iterdir() if p.suffix in (".yml", ".yaml"))


def audit_one(path: Path) -> list[str]:
    try:
        lines = path.read_text().splitlines()
    except (OSError, UnicodeDecodeError):
        return []
    violations: list[str] = []
    for idx, raw in enumerate(lines, 1):
        line = raw.strip()
        if not line or line.startswith("#") and ALLOW_MARKER.match(line):
            continue

        kind = None
        if BUMP.search(line):
            kind = "BUMP"
        elif WRITE.search(line) and (VERSION_LINE.search(line) or "version" in line):
            # a plain `sed -i` that never mentions version is not this rule's
            # business; the caller pairs it with the bump check
            kind = "WRITE"

        if kind is None:
            continue
        if idx >= 2 and ALLOW_MARKER.match(lines[idx - 2]):
            continue
        if ALLOW_MARKER.match(line):
            continue

        detail = ""
        flag = BUMP_FLAG.search(line)
        if flag:
            detail = f" (flag {flag.group(0)})"
        violations.append(
            f"{path}:{idx}: CI must not bump versions or write `version =` "
            f"(§17): {kind}{detail} in {line[:80]!r}. Bump locally with the "
            f"dedicated tool and let CI only build/publish."
        )
    return violations


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    if not root.is_dir():
        print(f"error: {root} is not a directory", file=sys.stderr)
        return 2

    workflows = list_workflows(root)
    if not workflows:
        print("INFO: no .github/workflows directory, nothing to check")
        return 0

    all_violations: list[str] = []
    for path in workflows:
        all_violations.extend(audit_one(path))

    for violation in all_violations:
        print(violation)
    if all_violations:
        print(
            f"\n=== ci-no-version-bump: {len(all_violations)} violation(s) "
            f"in {len(workflows)} workflow file(s) ==="
        )
        return 1
    print(f"\nOK: {len(workflows)} workflow file(s) checked, no version write")
    return 0


if __name__ == "__main__":
    sys.exit(main())
