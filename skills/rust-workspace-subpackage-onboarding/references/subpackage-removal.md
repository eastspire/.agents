# Subpackage removal (deleting a workspace member)

The symmetric inverse of the onboarding procedure in `../SKILL.md`. Use when the user says "delete X from this workspace", "drop X subdir", or "remove X from the monorepo". The end state: working tree is back to N-1 members, every reference to `X` outside `X/` is gone, `cargo check --workspace` is green, one `chore:` commit on master.

## When to use

- Removing a member from an existing Cargo workspace (whether it was added by an earlier onboarding, a `git subtree add`, or was always a workspace member).
- Removing a member whose upstream is dead (e.g. `crates-dev/X` returned 404), leaving only the local copy.
- Removing a member that is being migrated to a path-only dev-dep or `cargo install`-style external dep.

## Don't use for

- Stripping just `.git/` / `.github/` / per-subpackage `.gitignore` while keeping the crate directory — that's the "onboarding cleanup" step in the umbrella SKILL.md, not removal.
- Renaming a member directory — that's a `git mv` + path rewrites in `[workspace.dependencies]`, a different task.
- Yanking from crates.io — `cargo yank` is a registry operation, not a workspace edit.

## Pre-flight: dependency check

Before deleting, **verify no other workspace member depends on `X`** (regular dep, dev-dep, build-dep, or target-dependency — all four count). A grep isn't enough; cargo's resolver catches path-indirect refs that grep misses (e.g. `[dev-dependencies] X` from a member that lives in `#[cfg(test)]` only).

Use `cargo metadata`:

```bash
cargo metadata --no-deps --format-version=1 | python3 -c "
import json, sys
d = json.load(sys.stdin)
target = 'YOUR_CRATE_NAME'
for pkg in d['packages']:
    if pkg['name'] == target:
        continue
    deps = pkg.get('dependencies', [])
    refs = [d for d in deps if d['name'] == target]
    if refs:
        kind = refs[0].get('kind', 'normal')
        print(f'{pkg[\"name\"]} -> {target}  ({kind})')
"
```

If anything prints, the deletion will break that member's compile. Either keep the dep (and skip removal of `X`), or refactor the dependent first.

## Pre-flight: upstream status (decommissioning a dead subtree)

When removing a member that came from a `git subtree add` whose upstream is dead, **don't reverse-subtree-split** as a "preserve upstream" gesture — that pushes to a 404 remote and orphans the branch on every reader's clone. The forward delete (this procedure) is sufficient. Subtree history is already preserved in the parent repo's commit graph (the original `merge: import X from OWNER/X@master` commit is the audit trail); no separate ref is needed.

## Pre-flight: reference sweep candidates

Beyond `Cargo.toml` and the directory itself, `X` typically appears in:

| Location | Why | Fix |
|---|---|---|
| `[workspace].members` array | cargo won't compile without it | remove the entry, keep the order of remaining members |
| `README.md` layout diagram | docs get stale fast | remove the `, DIR/` line, keep alignment with adjacent entries |
| `README.md` test/build examples | example commands that mention `-p X` | remove the line |
| `README.md` crates.io/docs.rs badge table | per-crate row | remove the row |
| `README.md` upstream-origin table | row that names X's source repo | remove the row |
| `.github/workflows/release.yml` `PACKAGES=( ... X ... )` array | published binaries list | remove from list (only if X was actually published — most workspaces have only one binary) |
| Workspace-root `.gitignore` | subcrate-specific patterns | audit — if a pattern like `/target` was added BECAUSE of X's quirks, drop it; keep generic patterns |
| Cron/skill-sync tooling that scans workspace dirs (e.g. `OPT_OUT` for "tiny config repo") | leftover references in metadata tooling | drop the entry |

**Don't skip** the badge / upstream-table rows — they 404 on docs.rs and crates.io after the workspace commits the removal, and stale docs are user-visible.

## Procedure

1. **Drop `X` from `[workspace].members`.** Edit root `Cargo.toml`, preserve the existing order of remaining members (most workspaces group by logical layer, not alphabet). Cargo errors on a missing member reference and on a member that isn't a directory, so a clean diff matters.
2. **`git rm -r X/`.** This stages the directory removal and its subtree. Don't `rm -rf` first — `git rm` keeps the index consistent and gives a clean staged diff. After this step, `git status` shows 1 modified file (root Cargo.toml) + N `D  X/...` lines.
3. **Sweep the reference candidates table above.** Use `grep -rn X` filtered to known extensions (`.toml`, `.rs`, `.yml`, `.yaml`, `.sh`, `.md`, `.gitignore`, etc.). Anything that lights up outside `X/` is a stale reference and must be edited. The grep miss rate for nested workspaces (members referencing each other via `path = "../X"`) is ~zero for this task — the dependency check pre-flight catches what grep misses.
4. **`cargo fmt --all`** (not `--check`). The `members` array edit and any reference sweep may have shifted formatting; run in-place to match the user's "everything compiles, everything formatted" baseline.
5. **Verify, in this order:**
   - `cargo fmt --all -- --check` (idempotent — should print nothing)
   - `cargo check --workspace --all-features` (no errors, no "package not found" complaints about X)
   - `cargo build --workspace --all-features` (compiles fully)
   - `cargo test --workspace --all-features` (existing tests still pass)
   - `cargo clippy --workspace --all-targets -- -D warnings` (no new warnings from neighboring crates — deleted crates shouldn't add warnings but the index shift can sometimes surface previously-suppressed ones)
6. **Verify zero reference residue.** `grep -rn X` after the staged changes should light up only the diff itself (the deleted files inside `X/` are not "outside `X/`" since they're gone). A second sweep with `--include='*.toml' --include='*.rs' --include='*.yml' --include='*.yaml' --include='*.md' .` should be empty.
7. **Commit and push.** One atomic `chore:` commit is appropriate — this is a 1-file deletion + 1-content sweep, not a feature that needs a PR review. Before staging, **inspect `git status --short` for any unrelated modifications** (untouched files showing ` M`) — those are pre-existing worktree edits that got pulled into the index when you ran `git add -A`. Either revert them first (`git checkout -- FILE`) or split them into their own commit. Batching an unrelated content edit into a `chore: remove X` commit makes the PR/commit body wording lie, and `git bisect` later can't tell which change did what. After the local commit, the push may need `git pull --no-rebase origin master` if the remote has diverged (this is the common case for ctares-style monorepos with active CI). The user preference is merge, never rebase.

### Commit message shape

```
chore: remove <name> subdir from workspace

<one-paragraph why: e.g. "subtree merge from OWNER/<name>@master,
upstream crate no longer exists" or "moved to standalone repo at URL">

- drop "<name>" from [workspace].members in root Cargo.toml
- remove <N> stale <name> mentions from README (layout diagram, ...)
- git rm -r <name>/ (N files: Cargo.toml, Cargo.lock, ...)
```

Body explains *why* the removal is safe (which test of the dependency check passed). Don't restate the file list — that's already in `git show --stat`.

## Pitfalls

- **`git rm -r` BEFORE updating `[workspace.members]` fails cargo immediately** — the workspace tries to read `X/Cargo.toml`, gets ENOENT, errors on every subsequent `cargo` command until `[workspace].members` is also dropped. Two ways out: (a) update root Cargo.toml first (recommended — the diff is easier to review), or (b) `git rm` first and commit only after both edits land. Don't break the build between edits.
- **Don't delete the directory with `rm -rf` instead of `git rm -r`.** Plain rm removes files but leaves the index entries; `git status` shows ~80 lines of "D" records with no `.git` changes, and a later `git checkout -- X/` resurrects the deleted files. `git rm` updates both files and index atomically.
- **`cargo metadata --no-deps` does NOT include transitive deps in the `dependencies` array per package.** It only lists each package's direct deps. That's what you want for the local dependency check. If you see a transitive ref to X via a third-party crate, that's not a workspace concern — the third-party crate provides its own version of X at lock-time. The `cargo metadata` check is for *workspace member → X* edges only.
- **`cargo package -p X` still works after the workspace delete** as long as the directory exists — it doesn't require membership. But the published `.crate` won't be in any release notes (workspaces don't publish subcrates individually; they publish the whole workspace with the root version). If the user wants to preserve a one-time final release of X before deleting, that's `[workspace] members` removal → bump version → `cargo publish -p X` → `git subtree split -P X ...` → THEN this procedure. Different order; not the default.
- **`document-to-action-items` automation in `.github/workflows/` or similar tooling that scans `--workspace` output may have cached references.** Audit workflow files for `members:` / `for crate in $(ls) do` patterns that loop over directory listings — those pick up stale hits between commits.
- **`crates.io` registry: removing the local copy of X does NOT yank X from crates.io.** If X was published, it stays published and pinnable for years via the Cargo.lock that already has it. If the user wants to yank, it's a separate `cargo yank` step. If they don't, fine — but say so in the PR/notes so reviewers don't assume registry cleanup happened.
- **Skill-sync tooling that auto-scans workspace dirs.** `daily_skill_sync.py` in this machine's `~/.hermes/scripts/` has an `OPT_OUT` dict named after projects; if X is in there, drop the entry in the same commit as the workspace removal. Otherwise the cron job will keep scanning a deleted path every day and report noise in the next plan.
- **Local-only deletion is sometimes correct.** If the user says "delete gtl-config locally and on all remotes", `git rm` + local rm is right; **"push" means push the deletion commit, not push to the deleted remotes** (the deletes are noops once the remote is already 404). Don't try to invoke `gh repo delete` on a 404 — the call returns "Not Found" and the audit log shows a wasted API hit. **Verify the remote is gone FIRST** (the `cross-platform-git-mirror` skill has the canonical 3-platform probe pattern), then proceed with local-only work.
