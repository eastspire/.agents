#!/usr/bin/env python3
"""Verify that .github/workflows/*.yml never writes to a Cargo.toml `version =` line.

RULE (2026-09-26): In CI, the publish job's version-handling step is
strictly forbidden from writing any `version =` line in any Cargo.toml
manifest. Humans decide versions in PRs.

CI is allowed to:
  - call `cc sync` / `crate sync` to realign [workspace.dependencies]
    entries (these only edit reference lines, never `version =`)
  - read a `version =` line via grep/sed to derive a tag (read-only)
  - call `cargo publish` / `cc publish` / `crate publish` (these don't
    modify local Cargo.toml)

Forbidden patterns (any of these = violation):
  - `cc bump` / `crate bump` with any flag
    (--patch/--minor/--major/--alpha/--beta/--rc/--release/--target-version=...)
  - any python3 -c / python3 <<EOF script that calls
    `re.sub` / `write_text` / `replace` targeting a `version =` literal
  - any `sed -i` / `awk ... >` / `perl -pi` rewriting a `version =` literal
  - any `toml.dump` / `toml_edit::DocumentMut` mutation

Why this rule: previously CI auto-bumped a patch on every push to master,
which meant the human's authored version was overridden. The new rule
treats the version field as a human-authored artifact: CI keeps the
workspace structurally consistent (deps refs synced) and never edits the
version field itself.

Usage:
    python3 verify_ci_no_bump.py <repo_root>
    exit 0 = pass
    exit 1 = at least one violation
"""
import re
import sys
from pathlib import Path


# Forbidden: explicit version-bump CLI invocations (any binary name)
BUMP_RE = re.compile(r"\b(?:cc|crate)\s+bump\b")

# Forbidden: any python invocation that rewrites a `version =` literal
# Heuristic: detect python3 -c / python3 << heredocs that contain BOTH
# (a) a write primitive (write_text / Path.write_text / re.sub /
# replace / toml.dump / DocumentMut::set / Item::set) AND
# (b) a literal `version =` (with optional whitespace and any quote
# style — including double-backslash variants that appear when the
# regex was authored inside a bash string literal).
PYTHON_VERSION_WRITE_RE = re.compile(
    r"""python3?\s+-c|python3?\s*<<['"]?['"]?EOF|python3?\s*<<['"]?['"]?PYTHON""",
    re.IGNORECASE,
)
PYTHON_VERSION_WRITE_KEYWORDS = (
    "write_text",
    ".write(",
    "re.sub(",
    ".replace(",
    "toml.dump",
    "DocumentMut",
    "Item::set",
    "Item::as_table_like_mut",
)
# Loose match for `version` followed eventually by `=` and a quote.
# Catches encoding variants like:
#   - `version = "0.1.0"`
#   - `version\s*=\s*"0.1.0"`
#   - `version\\s*=\\s*\\"0.1.0\\"`
# Without trying to be precise about regex escapes. Combined with
# the upstream python-write-keyword requirement (write_text / re.sub
# / etc.) the chance of a false-positive on a python line that just
# mentions "version" + "=" + "some string" but doesn't actually
# rewrite anything is near-zero.
PYTHON_VERSION_LITERAL_RE = re.compile(
    r"version\s*[^\"']*?\s*=\s*[^\"']*?[\"']",
    re.DOTALL,
)

# Forbidden: sed/awk/perl that explicitly rewrites a `version =` line
# to disk. Distinguish from read-only: read-only patterns are
# `$(...)` / `\`...\`` substitution for assignment; writes are
# `sed -i` / `sed ... > file` / `sed ... | tee file` / `perl -pi`.
SED_VERSION_WRITE_RE = re.compile(
    r"""
    \b(?:sed|awk|perl)\b
    [^\n]*
    (?:
        -i              # in-place edit
        | -pi           # perl in-place
        | > \s* [^\s]+  # redirect to a file
        | \| \s* tee    # pipe through tee
    )
    """,
    re.IGNORECASE | re.VERBOSE,
)
SED_VERSION_LITERAL_RE = re.compile(r"\bversion\b", re.IGNORECASE)


def find_python_writes(text: str) -> list[tuple[int, str]]:
    """Find python invocations that look like they rewrite a version line."""
    hits: list[tuple[int, str]] = []
    for i, line in enumerate(text.splitlines(), start=1):
        if "python" not in line.lower():
            continue
        if not PYTHON_VERSION_WRITE_RE.search(line):
            continue
        # Look ahead up to ~2000 chars (block size for python -c) for
        # both a write primitive and a `version =` literal.
        tail = text[text.find(line):][:2000]
        if not PYTHON_VERSION_LITERAL_RE.search(tail):
            continue
        if not any(kw in tail for kw in PYTHON_VERSION_WRITE_KEYWORDS):
            continue
        hits.append((i, line.strip()[:140]))
    return hits


def check_file(path: Path) -> list[str]:
    violations: list[str] = []
    text = path.read_text()
    lines = text.splitlines()

    # Allowlist: a line containing the marker
    # `# ci-allow-version-write: <reason>` opts the line out of the
    # sed / awk / perl / python checks. Use sparingly — every
    # allowlist should have a documented reason (e.g. "docs mirror",
    # "non-workspace-member sync"). `cc bump` / `crate bump` cannot be
    # allowlisted.
    ALLOW_MARKER_RE = re.compile(
        r"#\s*ci-allow-version-write\s*:\s*\S", re.IGNORECASE
    )

    for i, line in enumerate(lines, start=1):
        stripped = line.lstrip()
        if stripped.startswith("#"):
            continue
        if BUMP_RE.search(line):
            violations.append(
                f"{path}:{i}: forbidden CI bump invocation: {line.strip()!r}"
            )
        # For sed/awk/perl/python writes, allow if a `# ci-allow-version-write:`
        # comment appears within the immediately preceding 3 lines. Tighter
        # window = allowlist must be tightly coupled to the violation, no
        # scattered allow-markers above.
        is_violation = (
            SED_VERSION_WRITE_RE.search(line)
            and SED_VERSION_LITERAL_RE.search(line)
        )
        # Allow if the immediately preceding line carries the allow
        # marker. Same tight-coupling rule as python above.
        if is_violation and i >= 2 and ALLOW_MARKER_RE.search(lines[i - 2]):
            is_violation = False
        if is_violation:
            violations.append(
                f"{path}:{i}: forbidden sed/awk/perl rewriting version = "
                f"to disk: {line.strip()!r}"
            )

    for lineno, snippet in find_python_writes(text):
        # Walk back exactly 1 line (the comment immediately above the
        # python invocation). Tight-coupling rule: the allow marker
        # must be on the line just above the violation, not scattered
        # earlier in the file.
        if lineno >= 2 and ALLOW_MARKER_RE.search(lines[lineno - 2]):
            continue
        violations.append(
            f"{path}:{lineno}: python in CI rewrites a version = line: "
            f"{snippet!r}"
        )

    return violations


def main(repo_root: str) -> int:
    root = Path(repo_root)
    workflows = sorted((root / ".github" / "workflows").glob("*.yml"))
    if not workflows:
        print(f"INFO: no .github/workflows/*.yml under {root}")
        return 0

    all_violations: list[str] = []
    for wf in workflows:
        all_violations.extend(check_file(wf))

    if all_violations:
        print(f"FAIL: {len(all_violations)} violation(s) across "
              f"{len(workflows)} workflow file(s):")
        for v in all_violations:
            print(f"  {v}")
        print()
        print("Rule: CI must not write any `version =` line in any "
              "Cargo.toml. Only `cc sync` / `crate sync` is allowed "
              "(it edits only [workspace.dependencies] reference "
              "lines, never `version =`). Humans set versions in PRs; "
              "CI keeps references consistent.")
        return 1

    print(f"OK: {len(workflows)} workflow file(s) — no forbidden "
          f"version-write operations.")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: verify_ci_no_bump.py <repo_root>", file=sys.stderr)
        sys.exit(2)
    sys.exit(main(sys.argv[1]))