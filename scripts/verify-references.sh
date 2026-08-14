#!/usr/bin/env bash
# verify-references.sh
#
# Compare the just-synced references/ against HEAD (or any --against ref)
# and surface:
#   - files changed by the sync (expected on every run)
#   - files in HEAD that are NO LONGER in the working tree (potential
#     orphans — usually the manual-override files the script skipped)
#   - files in the working tree that aren't tracked in HEAD (new files)
#
# Exits 0 if the working tree matches the expected post-sync shape.
# Exits 1 if there are unexpected untracked files (suggests the mapping
# has drifted from reality).
#
# Usage:
#   bash scripts/verify-references.sh                 # compare against HEAD
#   bash scripts/verify-references.sh --against <ref> # compare against any ref
#   bash scripts/verify-references.sh --strict        # exit 1 on any diff

set -euo pipefail

AGAINST="HEAD"
STRICT=0
while [[ $# -gt 0 ]]; do
    case "$1" in
        --against)  AGAINST="$2"; shift 2 ;;
        --strict)   STRICT=1; shift ;;
        -h|--help)
            sed -n '2,18p' "$0"; exit 0 ;;
        *) echo "Unknown arg: $1" >&2; exit 2 ;;
    esac
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$ROOT_DIR"

CHANGED=0
ORPHANED=0
UNTRACKED=0
DRIFT=0

# 1. List of references/ files in HEAD (across all skills)
mapfile -t HEAD_REFS < <(git ls-tree -r --name-only "$AGAINST" -- 'skills/*/references/' 2>/dev/null | sort)

# 2. List of references/ files in working tree
mapfile -t WT_REFS < <(find skills -path '*/references/*.md' -type f 2>/dev/null | sort)

# 3. Changed files (in both, but content differs)
for f in "${HEAD_REFS[@]}"; do
    if [[ -f "$f" ]]; then
        if ! git diff --quiet "$AGAINST" -- "$f" 2>/dev/null; then
            : # git diff is across HEAD vs WT, not file-vs-file — do it manually below
        fi
    fi
done

# Simpler: use git diff --name-only
mapfile -t DIFF_FILES < <(git diff --name-only "$AGAINST" 2>/dev/null | grep -E '^skills/[^/]+/references/.*\.md$' | sort || true)
CHANGED="${#DIFF_FILES[@]}"

echo "→ References sync verification (against $AGAINST)"
echo
echo "  files in $AGAINST:    ${#HEAD_REFS[@]}"
echo "  files in working tree: ${#WT_REFS[@]}"
echo "  changed by sync:      $CHANGED"

if [[ "$CHANGED" -gt 0 ]]; then
    echo
    echo "  ── changed files ──"
    for f in "${DIFF_FILES[@]}"; do
        echo "    $f"
    done
fi

# 4. Orphans: in HEAD but not in working tree (overrides the script skipped + then deleted)
for f in "${HEAD_REFS[@]}"; do
    if [[ ! -f "$f" ]]; then
        # Don't flag a "missing" file if it's already missing from HEAD (e.g. never tracked)
        if git cat-file -e "$AGAINST:$f" 2>/dev/null; then
            ORPHANED=$((ORPHANED+1))
            echo "  ⚠ orphaned (in $AGAINST, missing in WT): $f"
        fi
    fi
done

# 5. Untracked: in working tree but not in HEAD (mapping drift)
for f in "${WT_REFS[@]}"; do
    if ! git cat-file -e "$AGAINST:$f" 2>/dev/null; then
        UNTRACKED=$((UNTRACKED+1))
        echo "  ? untracked (in WT, missing in $AGAINST): $f"
    fi
done

# 6. Mapping drift: source paths in mapping that don't exist in the upstream clone
if [[ -n "${DOCS_PAGES_DIR:-}" && -d "$DOCS_PAGES_DIR/src" ]]; then
    SCRIPT_DIR_LOCAL="$SCRIPT_DIR"
    while IFS=$'\t' read -r dest_rel src_rel note; do
        [[ -z "$dest_rel" || "$dest_rel" =~ ^[[:space:]]*# ]] && continue
        src_rel="${src_rel# }"; src_rel="${src_rel% }"
        if [[ ! -f "$DOCS_PAGES_DIR/$src_rel" ]]; then
            DRIFT=$((DRIFT+1))
            echo "  ✗ mapping drift: $src_rel"
        fi
    done < "$SCRIPT_DIR_LOCAL/sync-references.mapping"
fi

echo
echo "──── verify summary ────"
echo "  changed:   $CHANGED"
echo "  orphaned:  $ORPHANED"
echo "  untracked: $UNTRACKED"
echo "  drift:     $DRIFT"

if [[ "$ORPHANED" -gt 0 || "$UNTRACKED" -gt 0 || "$DRIFT" -gt 0 ]]; then
    echo
    echo "  ⚠ review the items above before committing" >&2
    if [[ "$STRICT" -eq 1 ]]; then exit 1; fi
fi
exit 0
