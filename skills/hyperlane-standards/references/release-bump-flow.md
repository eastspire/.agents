# Release Bump Flow (hyperlane monorepo)

Cycle for bumping the shared version of all 5 crates in the monorepo.
Modeled on euv §17 + the 2026-09-13 PR #220 sync regression lesson.

## The invariant

**5 crates, 1 version number.** All `Cargo.toml` files in the workspace
should resolve to the same `<X.Y.Z>`. A `git show master:Cargo.toml | grep
'^version'` must match `git show master:core/Cargo.toml | grep '^version'`
etc. for all 5 crates, after the `sync_workspace_version` job has run.

## Manual flow (what a developer does)

```bash
cd /root/github/hyperlane-dev/hyperlane
NEW_VER="21.3.7"
OLD_VER="21.3.6"

# 1. edit ONLY the root Cargo.toml
sed -i "s/^version = \"$OLD_VER\"$/version = \"$NEW_VER\"/" Cargo.toml

# 2. verify diff is exactly 1 file, +1/-1
git diff --stat
# expected:  Cargo.toml | 2 +-
git diff
# expected:  exactly one line in the version field

# 3. commit
git add Cargo.toml
git commit -m "chore: bump version to $NEW_VER"

# 4. push branch, open PR against hyperlane-dev/hyperlane
git push -u origin chore/bump-$NEW_VER
```

## What you must NOT do

- ❌ `sed -i "s/version = \"$OLD_VER\"/version = \"$NEW_VER\"/" */Cargo.toml`
- ❌ Edit `core/Cargo.toml` / `macros/Cargo.toml` / `type/Cargo.toml` /
  `cli/Cargo.toml` version field manually
- ❌ Edit `[workspace.dependencies]` path-dep `version` field manually
- ❌ Edit any non-root `Cargo.toml` in the same PR

Doing any of these produces a 5+ file diff that the maintainer will reject
because:

1. The CI sync job will overwrite those edits anyway.
2. They suggest the developer doesn't understand §17.
3. PR review at euv confirmed this is a hard reject signal.

## What the CI does (master merge only)

When a PR with a version bump is merged to master:

1. `setup` job reads root Cargo.toml version via `toml get`.
2. `sync_workspace_version` job triggers (`if: github.event_name == 'push'
   && github.ref_name == 'master'`).
3. The job:
   - Lists workspace members via
     `toml get Cargo.toml workspace.members --raw | tr -d '[]"' | sed 's/,/\n/g'`
   - For each member's `[package].name`, runs `sed -i` to update its
     `[package].version` field.
   - Also runs `sed -i` to update each `[workspace.dependencies.<name>]`
     `version = "..."` field, in both inline-table and sub-table forms.
   - Finally updates the root `[package].version` itself (idempotent).
   - Runs `cargo generate-lockfile` to refresh the lockfile.
   - Commits as `eastspire <root@ltpp.vip>` with message
     `chore: sync all package versions to X.Y.Z` and pushes to master.
4. The 6 follow-up jobs (check / tests / clippy / build / publish / release)
   run again on the new HEAD, with the synced versions in place.

## Sync regression handling

If after merge the auto `chore: sync all package versions to X.Y.Z` commit
**does not appear** on master (e.g. CI sync job silently used stale root
Cargo.toml content, or token scope issue), recover with:

```bash
cd /root/github/hyperlane-dev/hyperlane
NEW_VER="21.3.7"
OLD_VER="21.3.6"

# Force-sync all 5 crates + root workspace.dependencies path-deps
for sub in core macros type cli; do
  sed -i "s/^version = \"$OLD_VER\"$/version = \"$NEW_VER\"/" "$sub/Cargo.toml"
done
sed -i "s/^version = \"$OLD_VER\"$/version = \"$NEW_VER\"/" Cargo.toml

# workspace.dependencies path-dep pins
sed -i -E "s|^(${NAME}-(core|macros|type|cli)[[:space:]]*=[[:space:]]*\{.*version[[:space:]]*=[[:space:]]*\")([^\"]+)(\".*)|\1${NEW_VER}\4|" Cargo.toml

git add -A
git commit -m "chore: sync all package versions to $NEW_VER (fix sync regression)"
git push origin master
```

Expected diff stat: `5 files changed, 5 insertions(+), 5 deletions(-)`.

## Patch vs minor/major bump

| Bump type | `Cargo.toml` version field | CI behavior |
| --- | --- | --- |
| patch | e.g. `21.3.6` → `21.3.7` | sync_workspace_version propagates cleanly |
| minor | e.g. `21.3.6` → `21.4.0` | local `cargo check` may fail on path-dep version mismatch (e.g. macros' `hyperlane-core = "^21.3.6"` is now out-of-range for the new `21.4.0`). Locally sed all 5 crates + workspace.dependencies to verify; CI will redo it on master push. |
| major | e.g. `21.3.6` → `22.0.0` | same as minor |

For minor/major, the PR compile job is expected to FAIL locally -- this is
by design (the path-dep ranges are pinned to the old range and need
sync_workspace_version to bump them). Don't waste cycles trying to fix
local compile; commit just the root `Cargo.toml` bump, let CI sync do the
rest, and verify on the auto-commit that lands.

## Real-world PRs to study

- PR #171: patch bump 0.20.0 → 0.20.1, clean single-commit flow.
- PR #220: patch bump with the `cargo publish` curl-35 post-verify false-alarm
  pitfall. See euv-standards `references/minor-bump-ci-red-by-design.md` for
  the full story (also applies to hyperlane post-monorepo).
- euv PR #196/197: sync_workspace_version wrote the wrong version because
  it read stale root content -- recovery flow shown above.