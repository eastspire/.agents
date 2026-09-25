#!/usr/bin/env bash
# Verify R14.7: tests/<sub>/fn.rs may contain ONLY `use super::*;` as a top-level use.
# All other imports (wasm_bindgen_test, std::xxx, web_sys::xxx) must be re-exported
# by the parent tests/mod.rs via `pub use`.
#
# Usage: bash verify_test_imports_centralized.sh <repo_root>
# Exit 0 if all test fn.rs files comply; non-zero with list of violations otherwise.

set -u

if [ $# -lt 1 ]; then
    echo "Usage: $0 <repo_root>"
    exit 2
fi

REPO_ROOT="$1"

# Sanity: skip when there are no tests/ subfolders at all (clean repo).
# Otherwise the script silently passes — desirable for repos with no Rust tests.
shopt -s nullglob
matches=( "$REPO_ROOT"/tests/*/fn.rs )
shopt -u nullglob
if [ ${#matches[@]} -eq 0 ]; then
    echo "OK: 0 tests/<sub>/fn.rs files (R14.7 not applicable)"
    exit 0
fi

violations=0
checked=0

# Single-quoted pattern: only `use super::*;` is allowed on the top-level use line.
# The escape `\*` is for grep's regex (KEEP that one), NOT for bash (no shell glob).
for f in "${matches[@]}"; do
    checked=$((checked + 1))
    # Strip every line that is exactly `use super::*;` — anything left is a violation.
    # Use grep -nF (fixed string) for the `use super::*;` filter to avoid regex pitfalls.
    bad=$(grep -n '^use ' -- "$f" | grep -v -F 'use super::*;' || true)
    if [ -n "$bad" ]; then
        echo "VIOLATION: $f has non-super use lines:"
        echo "$bad" | sed 's/^/    /'
        violations=$((violations + 1))
    fi
done

if [ "$violations" -gt 0 ]; then
    echo ""
    echo "FAIL: ${violations} file(s) violate R14.7 (test fn.rs may only have use super::*;)"
    echo "Move those 'use' lines into tests/mod.rs as 'pub use std::xxx;' / 'pub use wasm_bindgen_test::wasm_bindgen_test;' etc."
    exit 1
fi

echo "OK: $checked tests/<sub>/fn.rs file(s) all have only 'use super::*;' (R14.7)"
exit 0
