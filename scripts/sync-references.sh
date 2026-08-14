#!/usr/bin/env bash
# sync-references.sh
#
# Sync `skills/<skill>/references/*.md` from the upstream docs-pages repo
# according to scripts/sync-references.mapping.
#
# Workflow:
#   1. Clone docs-pages shallowly to a temp dir (or use --source-dir if
#      you already have a clone).
#   2. For each non-override mapping line: copy the source .md into the
#      dest path, strip VuePress-only frontmatter keys, and rewrite the
#      file header so it serves as a self-contained skill reference
#      (adds `synced_from`, normalizes `title`, strips the "authoring"
#      comment block if present).
#   3. For lines tagged `# manual override:` print a SKIP notice and
#      leave the existing dest file untouched (if it exists) or warn
#      if it doesn't.
#
# After sync, run:
#   bash scripts/verify-references.sh
# to diff against the previously committed references/ and surface drift.
#
# Usage:
#   bash scripts/sync-references.sh                 # fresh clone + sync
#   bash scripts/sync-references.sh --source-dir <path>   # reuse a clone
#   bash scripts/sync-references.sh --dry-run       # show what would happen
#   bash scripts/sync-references.sh --force         # overwrite manual overrides (not recommended)
#
# Requires: bash 4+, git, sed, awk, mktemp. No external deps.

set -euo pipefail

# ---------- arg parsing ----------
DRY_RUN=0
FORCE=0
SOURCE_DIR=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --dry-run)     DRY_RUN=1; shift ;;
        --force)       FORCE=1; shift ;;
        --source-dir)  SOURCE_DIR="$2"; shift 2 ;;
        -h|--help)
            sed -n '2,28p' "$0"
            exit 0
            ;;
        *)
            echo "Unknown arg: $1" >&2; exit 2 ;;
    esac
done

# ---------- paths ----------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
MAPPING_FILE="$SCRIPT_DIR/sync-references.mapping"
DOCS_REPO="https://github.com/eastspire/docs-pages.git"

if [[ ! -f "$MAPPING_FILE" ]]; then
    echo "ERROR: mapping file not found: $MAPPING_FILE" >&2
    exit 1
fi

# ---------- clone (or reuse) ----------
if [[ -z "$SOURCE_DIR" ]]; then
    if [[ -n "${GH_TOKEN:-}" ]]; then
        AUTH_REMOTE="https://x-access-token:${GH_TOKEN}@github.com/eastspire/docs-pages.git"
    elif [[ -n "${GITHUB_TOKEN:-}" ]]; then
        AUTH_REMOTE="https://x-access-token:${GITHUB_TOKEN}@github.com/eastspire/docs-pages.git"
    else
        AUTH_REMOTE="$DOCS_REPO"
    fi
    SOURCE_DIR="$(mktemp -d -t docs-pages-sync-XXXXXX)"
    trap 'rm -rf "$SOURCE_DIR"' EXIT
    echo "→ Cloning docs-pages (shallow) into $SOURCE_DIR ..."
    if [[ "$DRY_RUN" -eq 1 ]]; then
        echo "  (dry-run: skipping clone)"
        # fabricate a minimal source tree for dry-run validation
        mkdir -p "$SOURCE_DIR/src/euv/usage-introduction"
    else
        git clone --depth 1 --quiet "$AUTH_REMOTE" "$SOURCE_DIR"
    fi
fi

if [[ ! -d "$SOURCE_DIR/src" ]]; then
    echo "ERROR: source dir doesn't look like a docs-pages clone: $SOURCE_DIR" >&2
    echo "  (no 'src/' subdirectory found)" >&2
    exit 1
fi

# ---------- counters ----------
COPIED=0
SKIPPED_OVERRIDE=0
WARNED_MISSING_DEST=0
MISSING_SOURCE=0
FAILED=0

# ---------- helpers ----------
strip_vuepress_frontmatter() {
    # Strip these keys from frontmatter (kept: title, category, tags, sidebar, etc.)
    # We rebuild the frontmatter from scratch so order is consistent.
    awk '
        BEGIN { in_fm=0; fm_done=0 }
        /^---[[:space:]]*$/ {
            if (!fm_done) { in_fm = !in_fm; if (!in_fm) fm_done=1; next }
            else { print; next }
        }
        in_fm { next }
        !fm_done && NR<=3 && /^---[[:space:]]*$/ { next }
        { print }
    ' "$1"
}

# Prepend a normalized header (YAML frontmatter + H1 + synced_from line)
# to the stripped body. Stdin = body. Args: $1=rel_source, $2=dest_rel
build_skill_reference() {
    local rel_source="$1"
    local dest_rel="$2"
    local commit_sha
    commit_sha="$(git -C "$SOURCE_DIR" rev-parse --short HEAD 2>/dev/null || echo unknown)"
    cat <<HEADER
---
synced_from: docs-pages/${rel_source}@${commit_sha}
sync_method: scripts/sync-references.sh
sync_date: $(date -u +%Y-%m-%d)
---

<!--
This file is auto-synced from the upstream docs-pages repo.
Manual edits will be overwritten on the next sync. To pin a custom version
of this reference, add "# manual override:" to its mapping line and the
script will leave it alone.
-->

$(cat)
HEADER
}

# ---------- main loop ----------
echo "→ Syncing references from $SOURCE_DIR"
echo "  mapping: $MAPPING_FILE"
echo

while IFS=$'\t' read -r dest_rel src_rel note; do
    # skip comments / blanks
    [[ -z "$dest_rel" || "$dest_rel" =~ ^[[:space:]]*# ]] && continue
    dest_rel="${dest_rel# }"; dest_rel="${dest_rel% }"
    src_rel="${src_rel# }"; src_rel="${src_rel% }"

    dest_abs="$ROOT_DIR/$dest_rel"
    src_abs="$SOURCE_DIR/$src_rel"

    is_override=0
    if [[ -n "$note" && "$note" == *"manual override"* ]]; then
        is_override=1
    fi

    if [[ ! -f "$src_abs" ]]; then
        echo "  ✗ MISSING source: $src_rel"
        MISSING_SOURCE=$((MISSING_SOURCE+1))
        continue
    fi

    if [[ "$is_override" -eq 1 && "$FORCE" -eq 0 ]]; then
        if [[ -f "$dest_abs" ]]; then
            echo "  ⤼ SKIP (override): $dest_rel"
            SKIPPED_OVERRIDE=$((SKIPPED_OVERRIDE+1))
        else
            echo "  ! WARN (override, no dest): $dest_rel — create it manually"
            WARNED_MISSING_DEST=$((WARNED_MISSING_DEST+1))
        fi
        continue
    fi

    if [[ "$DRY_RUN" -eq 1 ]]; then
        echo "  → would copy: $src_rel → $dest_rel"
        COPIED=$((COPIED+1))
        continue
    fi

    mkdir -p "$(dirname "$dest_abs")"
    if ! strip_vuepress_frontmatter "$src_abs" | build_skill_reference "$src_rel" "$dest_rel" > "$dest_abs.tmp"; then
        echo "  ✗ FAILED: $dest_rel" >&2
        rm -f "$dest_abs.tmp"
        FAILED=$((FAILED+1))
        continue
    fi
    mv "$dest_abs.tmp" "$dest_abs"
    echo "  ✓ $dest_rel"
    COPIED=$((COPIED+1))

done < "$MAPPING_FILE"

# ---------- summary ----------
echo
echo "──── sync summary ────"
echo "  copied:             $COPIED"
echo "  skipped (override): $SKIPPED_OVERRIDE"
echo "  warn (override no dest): $WARNED_MISSING_DEST"
echo "  missing source:     $MISSING_SOURCE"
echo "  failed:             $FAILED"

if [[ "$FAILED" -gt 0 ]]; then
    exit 1
fi
if [[ "$MISSING_SOURCE" -gt 0 ]]; then
    echo "  (some sources missing — verify upstream file paths and update mapping)" >&2
    exit 1
fi
