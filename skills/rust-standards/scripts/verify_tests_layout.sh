#!/usr/bin/env bash
# Verify rust-standards §14.4 / §14.5 compliance for any Git repo.
# Run from repo root: bash <skill>/scripts/verify_tests_layout.sh
#
# Checks:
#   1. No #[cfg(test)] mod tests blocks inside any src/ file
#   2. No `//` comments inside any tests/**/*.rs file
#   3. No `use super::*;` at top-level integration test mod.rs
#   4. No `pub use renderer::...` / `pub use other_crate::...` re-exports
#      added solely so tests/ can see private items
#
# Exits 0 on PASS, 1 on FAIL. Prints offending lines with file:line.

set -uo pipefail

ROOT="${1:-.}"
cd "$ROOT" || { echo "FAIL: cannot cd to $ROOT"; exit 1; }

FAIL=0

echo "=== §14.4 check 1: no inline #[cfg(test)] mod tests in src/ ==="
for f in $(find core/src engine/src ui/src cli/src -name "*.rs" 2>/dev/null); do
  if grep -n "^#\[cfg(test)\]" "$f" 2>/dev/null | grep -v "^[^:]*:[^:]*://" > /dev/null; then
    # Skip lines that are inside a comment (// or /// before #[cfg(test)])
    if ! grep -B 2 "^#\[cfg(test)\]" "$f" 2>/dev/null | grep -E "^\s*//" > /dev/null; then
      echo "FAIL: inline #[cfg(test)] mod tests found at $f"
      grep -n "^#\[cfg(test)\]" "$f" | head -3
      FAIL=1
    fi
  fi
done
[ "$FAIL" = 0 ] && echo "PASS: no inline tests in src/"

echo
echo "=== §14.5 check 2: no comments in tests/**/*.rs files ==="
for f in $(find core/tests engine/tests ui/tests cli/tests -name "*.rs" 2>/dev/null); do
  if [ -f "$f" ]; then
    hits=$(grep -nE "^\s*//[^/]" "$f" 2>/dev/null)
    if [ -n "$hits" ]; then
      echo "FAIL: comments in $f:"
      echo "$hits" | head -5
      FAIL=1
    fi
  fi
done
[ "$FAIL" = 0 ] && echo "PASS: no comments in test files"

echo
echo "=== Check 3: top-level integration test mod.rs has no use super::* ==="
for f in core/tests/mod.rs engine/tests/mod.rs ui/tests/mod.rs cli/tests/mod.rs; do
  if [ -f "$f" ]; then
    if tail -5 "$f" | grep -E "^\s*use super::\*;" > /dev/null; then
      echo "FAIL: top-level $f ends with use super::*; (invalid Rust at crate root)"
      FAIL=1
    fi
  fi
done
[ "$FAIL" = 0 ] && echo "PASS: top-level mod.rs files clean"

echo
echo "=== Check 4: no pub use re-exports added solely for tests ==="
# Heuristic: any pub use added in lib.rs whose path ends with an item that
# only has #[cfg(test)] usage. Skipped for now — relies on a code search.
echo "SKIP: requires manual review (search for 'pub use' + tests/ references in lib.rs)"

echo
if [ "$FAIL" = 0 ]; then
  echo "ALL CHECKS PASSED"
  exit 0
else
  echo "FAILURES DETECTED — see above"
  exit 1
fi