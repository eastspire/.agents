---
name: rust-workspace-release
description: 'Use when releasing multi-crate Rust workspaces via crate-cli (`crate` binary).'
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos]
metadata:
  hermes:
    tags: [Rust, Cargo, Release, crates.io, CI/CD]
    related_skills: [rust-standards, github-actions-deploy-pipelines]
---

# Rust workspace release (crate-cli / `crate`)

## When to Use

- Bumping versions across a Rust workspace (single crate, virtual workspace,
  or root-package monorepo), syncing `[workspace.dependencies]` pins, or
  publishing members to crates.io — use the `crate` commands below instead
  of hand-rolled toml/sed scripts.
- Editing the release CI (bump/sync/publish/release jobs) of hyperlane, euv,
  ctares, or any workspace that adopts the same pipeline.
- Not for one-off crate downloads/queries (that is `rust-crate-use`) or
  dependency-ordering style rules (that is `rust-standards`).

Release lifecycle for the user's multi-crate Rust workspaces (hyperlane,
euv, ctares). The tool is **crate-cli** (package `crate-cli`, lib
`crate_cli`, binary `crate`) living in the ctares repo (`crates-dev/ctares`,
local `~/code/ctares/crate-cli` — members sit at the repo root, NOT under
`crates/`). The release-ci session that exposed the binary rename
also flipped the package name from `crates-cli` to `crate-cli` so the
crate can be published (the underscore-and-dash-normalization on crates.io
made the previous name a perpetual collision with willothy's `crates_cli`).

## The three commands

- `crate bump [--patch|--minor|--major | --target-version=X.Y.Z]` — bumps
  versions for the whole repo. Handles all three architectures: single
  crate (non-monorepo), virtual workspace (all members), and workspace
  with a root package (root + members). After bumping it realigns every
  local dependency's `version = "..."` reference (member manifests AND
  `[workspace.dependencies]` root entries) to the new version. Members
  using `version.workspace = true` are bumped by updating
  `[workspace.package].version` once.

  **`--patch` on a heterogeneous workspace (no `[workspace.package].version` set) auto-enters mode 3**: each member independently +1 patch, preserving each member's `major.minor`. So `color-output@10.1.6` and `crate-cli@0.2.8` become `color-output@10.1.7` and `crate-cli@0.2.9` in a single pass, and the root `Cargo.toml` gains `[workspace.package].version = "<max-after-bump>"` (the highest bumped version). The dep-ref cascade (rewriting `[workspace.dependencies]` path-member `version = "..."`) runs in the same commit — verify the post-bump diff has BOTH the `[package].version` bumps AND the dep-ref rewrites before committing. To promote to a unified workspace version (every member `version.workspace = true`), follow the bump with a hand conversion of each member's `version = "X.Y.Z"` line, then `crate sync`; without the sync the workspace fails to resolve until the dep-refs match the promoted root version.
- `crate sync` — rewrites `[workspace.dependencies]` local path entries
  to the workspace root version and renames dep aliases to the member's
  real `[package].name`. Idempotent (no write when already aligned).
  Also aligns the root package's own `path = "."` self-entry when one
  exists. **Heterogeneous workspaces** (no `[workspace.package].version`
  and no root `[package]`, e.g. ctares where every member has its own
  version): sync aligns each local entry to THAT member's own version
  instead of erroring on the missing root version. A member with
  `version.workspace = true` in a workspace with no shared version is an
  error (nothing to inherit).

  **`crate sync` is the only `crate` command that NEVER writes to a
  `version =` line.** It edits dependency-reference entries (path-alias
  renames, version-equality of `[workspace.dependencies]` paths, per-
  member sibling dep version pins) but every `version =` value in every
  manifest is left exactly as the human wrote it. Verified by diffing
  pre/post runs on ctares — sync produces a no-op diff whenever the
  workspace is already internally consistent. This is the property that
  makes the "CI only syncs" pattern safe to run on every push.
- `crate publish` — publishes in `[workspace.members]` declaration order,
  which must be publish-topological (dependency before dependent). Skips
  members with `publish = false`. Resolves `version.workspace = true`.
  When a root package exists it is appended last, UNLESS members depend
  on it — then it is inserted at its topological position (after its
  deps, before its dependents).

### `crate bump` bump-type vs. `--target-version` (CI conditional)

When a CI workflow controls the release target (e.g. a `workflow_dispatch`
input or a tag like `release-vX.Y.Z`), the naive `crate bump --patch` flow
will keep nudging master a step further on every push, and `crate publish`
succeeds against crates.io only because the tag and the prior published
version get reconciled — but local `Cargo.toml` is left with stale
trailing versions on every master run. The `--target-version=X.Y.Z`
flag makes `crate bump` a conditional instead:

```
crate bump --target-version=X.Y.Z        # --patch/--minor/--major ignored
  target == current   ->  patch +1   (so the same patch is re-released)
  target != current   ->  overwrite Cargo.toml with target verbatim
  malformed target    ->  exit non-zero with "target version" error
```

The same rule applies per-member in a virtual workspace. When the flag is
absent, `crate bump` keeps the legacy `--patch|--minor|--major|...`
behavior verbatim. Wire the workflow to pass the desired release target
rather than chaining an unconditional `--patch`.

## CI integration pattern (proven green on hyperlane + euv)

The publish job owns version management; check/tests/clippy/build just gate:

```yaml
- name: Install crate-cli
  run: |
    for i in 1 2 3 4 5 6 7 8; do
      if cargo install --git https://github.com/crates-dev/ctares.git crate-cli; then break; fi
    done
# dev-driven version flow (euv): sync only
- run: crate sync
# CI-driven release flow: pass the target version explicitly so master
# pushes don't nudge the patch on every run.
- run: |
    crate bump --target-version="${{ inputs.release_version }}"
    crate sync
    git diff --quiet Cargo.toml || { git add Cargo.toml; git commit -m "chore: bump version"; git push; }
- run: |
    echo "${{ secrets.CARGO_REGISTRY_TOKEN }}" | cargo login
    crate publish
```

Alternative when CI runs in the ctares repo itself: `cargo build --release -p
crate-cli` then call `./target/release/crate ...` — no install step at all.

The legacy auto-bump on every master push (`cc bump --patch` unconditionally,
no `--target-version`) still works for projects that explicitly want
"every green master push = a new patch release". Switch to
`--target-version` when the workflow controls the release target itself.

### Maintainer-driven release via `workflow_dispatch`

When the project moves from "every green push is a release" to
"releases are a maintainer decision", the workflow becomes
dispatch-driven:

```yaml
on:
  push:
    branches: [master]
  pull_request:
    branches: [master]
  workflow_dispatch:
    inputs:
      target-version:
        description: 'Target version (X.Y.Z) for `crate bump --target-version`.'
        required: true
        type: string
```

The publish job's `if:` becomes `github.event_name == 'workflow_dispatch'`
(no longer depends on `push`), and the bump step reads
`${{ inputs.target-version }}`. The `target-version` field MUST be
validated as semver at the workflow layer (a fast-fail grep), because
`crate bump --target-version` only rejects malformed targets deep inside
the run — a clear "::error::" up front saves a full CI cycle on typos.

Idempotence: running dispatch twice with the same target leaves the
repo unchanged after the first run — `current == target` does patch+1
once, then the next run finds `current = target + 1` so the rule
doesn't fire. This is the property that makes the dispatch pattern
safe to retry after a transient failure (network, runner lost,
CARGO_REGISTRY_TOKEN missing, etc.) without duplicating the release.

#### `workflow_dispatch` trap: all-downstream-jobs condition still gates on push/PR

When the workflow used to be `push`-only with `publish` gated to
`github.event_name == 'push' && github.ref_name == 'master'`, the
test/clippy/build jobs usually look like:

```yaml
jobs:
  tests:
    needs: setup
    if: always() && (github.event_name == 'pull_request' || (github.event_name == 'push' && needs.setup.result == 'success'))
```

Switching `publish` to dispatch-driven is the easy half. The easy half
**silently breaks the dispatch run** — `tests`, `clippy`, `check`,
`build` all evaluate to `false` (neither push nor pull_request) and
GitHub Actions treats `'skipped'` as `not 'success'`, so every
downstream job is skipped too. The whole dispatch run reports as
"all skipped" with no error message. Verified on ctares `rust.yml`
after the trigger conversion.

Fix every downstream condition to include the dispatch arm:

```yaml
if: always() && (github.event_name == 'pull_request' || (github.event_name == 'push' && needs.setup.result == 'success') || github.event_name == 'workflow_dispatch')
```

`always()` is still required — without it, when the upstream `setup`
job is itself skipped on dispatch (e.g. some workflows add an early
`if: github.event_name == 'push'` guard) the `&&` short-circuits to
false and the gate is never entered. Smoke-test trigger changes on
the PR that introduces them: `gh pr checks <N>` showing the new job
as `skipped` instead of `in_progress` means the `if:` is wrong.

### Sync-only pattern (CI never bumps, never publishes from auto-run)

For repositories where **only humans decide versions** (the user authors
`version =` lines in their PR and expects CI to keep references
internally consistent but never nudge the version on its own), the
workflow drops `crate bump` entirely and runs `crate sync` as the only
manifest edit:

```yaml
# ctares pattern: human-set versions, CI never modifies version =
- name: Sync workspace dependency references
  id: sync_refs
  run: |
    set -e
    ./target/release/crate sync
    if git diff --quiet Cargo.toml; then
      echo "sync_changed=false" >> $GITHUB_OUTPUT
    else
      git config user.name "github-actions[bot]"
      git config user.email "github-actions[bot]@users.noreply.github.com"
      git add -A
      git commit -m "chore: sync workspace member dependency refs"
      git pull --no-rebase origin master
      git push origin HEAD:master
    fi
```

Three properties make this safe to run on every push:

1. `crate sync` never writes a `version =` line, so a clean run leaves
   the author's version untouched.
2. `git diff --quiet Cargo.toml || commit` skips the commit when the
   workspace is already consistent — no churn, no bot commits on green.
3. The commit message names the operation ("sync") rather than the
   version ("bump"), so log readers can distinguish human-driven
   version changes from CI's reference fixes.

If the workflow previously exposed `bumped_version` / `bumped_tag` as
job outputs, rename them to `synced_version` / `synced_tag` and update
every `needs.publish.outputs.bumped_*` reference in the `release` job.
`crate sync` doesn't write either output — the rename is manual. The
version reported in `synced_version` is whatever humans wrote in their
PR, **not** a CI decision: the publish/release jobs downstream receive
that authored version and ship it.

When `publish` and `release` still run on `push master` in this pattern,
they ship whatever version the PR author set — which is the intended
behavior under the "CI never bumps" rule. To make release an explicit
maintainer step, combine with the `workflow_dispatch` block above.

#### Non-workspace-member manifests (e.g. euv-docs/Cargo.toml)

`crate sync` cannot reach a Cargo.toml that is **not** a workspace
member (e.g. euv's `docs/Cargo.toml` which is excluded from
`[workspace.members]`). The natural temptation is to inline a small
shell script that mirrors root's `version =` into the out-of-tree
manifest — `sed -i ...`, `python3 -c "re.sub(...)"`, etc. Under the
`verify_ci_no_bump.py` rule (no `version =` writes), this is exactly
the case that needs an `# ci-allow-version-write: <reason>` marker.

Two paths when the user wants to enforce "CI never writes
`version =`":

- **(preferred) Drop the mirror script; docs version becomes
  human-maintained.** `docs/Cargo.toml` is updated in the same PR that
  bumps the root version. Add a checklist note to the PR template so
  authors don't forget. Trade-off: one more thing humans must
  remember; benefit: zero CI magic, all `version =` lines are
  hand-written and auditable in PR diff.
- **(allowed) Keep the mirror, accept the allowlist marker.** The
  marker `# ci-allow-version-write: docs mirror, non-workspace-member`
  on the line immediately above the rewrite satisfies the verifier
  and keeps the auto-sync. Trade-off: the comment above the rewrite
  is the only comment of the "no comments in CI" exception; if the
  user later says "remove all comments", this becomes the obvious
  place to drop the mirror script.

Do not pick the third option ("rename docs to be a workspace member")
without consulting the user — adding it to `[workspace.members]`
makes `crate sync` see it, but also pulls docs into `crate bump` /
`crate publish` (which now bump / ship docs too), which is a
meaningful behavior change beyond the user's stated rule.

**Correction (2026-09-26 euv case)**: when the non-member manifest's
`*.workspace = true` inheritance is broken (`failed to find a workspace
root`), and the non-member's deps are `version = "0"` (path-only, no
framework pin), the cleanest fix IS to add it to `[workspace.members]`
and drop any per-non-member CI publish branch. The "behavior change
beyond the rule" framing is wrong here — `crate publish` shipping docs
is exactly what the user wants; the per-non-member branch was always
a workaround. Before applying this fix, verify the manifest's
dependencies don't pin to a specific upstream framework version
(e.g. `euv = "0.18"` for CSS stability) — if they do, adding to
members breaks the pin via sync cascade. If deps are `version = "0"`
or path-only, the fix is safe.

#### Keep CI workflows free of explanatory comments

When modifying the sync step or any other CI step, **do not add
explaining comments inside `.github/workflows/*.yml`**. The CI file is
read by GitHub Actions and the maintainer — not by an LLM trying to
understand intent. Adding `# CI never bumps Cargo.toml versions...`,
`# heterogeneous workspaces rewrite...`, `# docs mirror,
non-workspace-member` etc. clutters the file, drifts out of date as
the script evolves, and forces the next reviewer to figure out which
comment was current-as-of-when. The explanatory text belongs in this
skill (or commit message / PR description), not in the workflow.

This rule covers both:

- "Explainer" comments above a step (the kind an LLM naturally writes
  to justify why the step exists): delete them all.
- Allowlist markers like `# ci-allow-version-write: docs mirror`. If
  the rule above is enforced strictly, the marker is not needed — and
  where the marker IS needed (a genuine non-member cargo manifest
  mirror), prefer removing the rewrite entirely and moving the
  responsibility to the PR author (next section).

When a comment is unavoidable because the YAML construct is opaque
(e.g. the `setext` heading trap in some linters, or a workaround for
a runner quirk), keep it to one sentence.

**Stale names in workflow comments are the worst version of this rule.**
A binary rename (`cc` → `crate`), a flag rename (`--patch` →
`--target-version`), or a member rename (`crates-cli` → `crate-cli`)
often leaves a parenthetical like `(the `cc` tool)` or a clause like
`(handled by crates-cli)` inside an otherwise-cosmetic comment block —
the comment survives because nothing references it for correctness,
but it actively misleads readers until someone deletes it. The fix
is the same as the general rule: delete the whole comment. Do not
"fix" the stale name in place (e.g. `(the `crate` tool)`), because
the comment was never load-bearing in the first place — keeping any
version of it is a commitment to keeping it current. If a `grep -rn
'\bcc\b'` over `.github/workflows/` returns any matches, treat them
as both a rename miss AND a comment-hygiene miss in the same pass.

### Audit gate: `verify_ci_no_bump.py`

The rule "CI never bumps" is enforced by a verifier, not by prompt
recitation. The verifier lives at
`scripts/verify_ci_no_bump.py` in `rust-standards`, is wired into
`audit_rust_standards.py` as check 22, and returns:

- exit 0 — every `.github/workflows/*.yml` in the repo either calls only
  `crate sync` / `crate publish` or uses `# ci-allow-version-write: <reason>`
  on the line immediately above any read-write sed/perl/python invocation
- exit 1 — at least one workflow step calls `crate bump` / `cc bump` (any
  flag combo), or rewrites a `version =` line via `sed -i` /
  `perl -pi` / `python3 -c` / `awk > file` without an adjacent allowlist

**Why the allowlist window is exactly 1 line**: the marker must be
visibly coupled to the violation (`# ci-allow-version-write: <reason>`
on the line just above the rewriting call). A wider window (e.g. 3-6
lines) lets an unrelated `echo` or `sed` blur the connection, and
reviews stop noticing the override. Implementation detail at
`rust-standards/references/audit-pitfalls.md §49.2`.

**Before claiming "CI never bumps" for a repo**, run:

```bash
python3 ~/.agents/skills/rust-standards/scripts/verify_ci_no_bump.py <repo>
```

If exit 1, either (a) rewrite the offending step to call `crate sync`
instead, or (b) add the allowlist marker on the line immediately above
with a documented reason (e.g. "docs mirror, non-workspace-member" for
the euv-docs `Cargo.toml` reflection pattern).

### `cc` ↔ `crate` binary name across repos

The release-ci rename flipped crate-cli's package from `crates-cli`
(bin `cc`) to `crate-cli` (bin `crate`), so **a workflow written
before the rename** still calls `cc sync` / `cc bump`, and **a workflow
written after** calls `crate sync` / `crate bump`. Both work today
(`~/.cargo/bin/cc` is from `crate-cli v0.2.5`; the latest crates.io
release installs `crate`), but a single repo may have a partially
migrated workflow with one step calling `cc` and another calling
`crate`. The verifier matches both with `\b(?:cc|crate)\s+bump\b`,
so partial migration is correctly flagged. Fix: pick one binary name
per workflow (prefer `crate` going forward) and replace all calls in
the same `patch` pass — `sed -i '' 's/\bcc bump\b/crate bump/g;
s/\bcc sync\b/crate sync/g; s/\bcc publish\b/crate publish/g' .github/workflows/rust.yml`
on macOS, equivalent `sed -i` on Linux.

### Renaming a step output — exact grep recipe

When converting `crate bump` → `crate sync` and renaming the step output
from `bumped_version`/`bumped_tag` to `synced_version`/`synced_tag`,
the rename cascades silently if missed. The mechanical fix is one
`grep -rl` + `sed -i` over `.github/workflows/`:

```bash
# 1. find every reference
grep -rn 'bumped_version\|bumped_tag\|bump_sync' .github/workflows/
# 2. rename in place (GNU sed shown; macOS uses -i '')
sed -i 's/bumped_version/synced_version/g; s/bumped_tag/synced_tag/g; s/bump_sync/sync_refs/g' \
  .github/workflows/rust.yml
# 3. verify no remnants
grep -rn 'bumped_\|bump_sync' .github/workflows/   # must be empty
# 4. verify YAML still parses
python3 -c "import yaml; yaml.safe_load(open('.github/workflows/rust.yml'))"
# 5. audit gate
python3 ~/.agents/skills/rust-standards/scripts/verify_ci_no_bump.py .
```

The audit step at the end is non-optional — it is the only check that
confirms the workflow no longer contains a `cc bump` / `crate bump`
call hidden behind a renamed-but-not-removed step.

### User-applies-a-rule-across-repos workflow

When the user states a rule and asks for it applied to "all repos" or
"the other repos too", the standard move is:

1. Verify the rule has an executable verifier (or write one — see
   `rust-standards` "新增 audit check 的硬性流程"). A rule without a
   verifier decays into a vibe.
2. Run the verifier across every named repo. Capture pass/fail
   per-repo. **Do not** claim the rule is in force until exit 0 on
   each.
3. For each failing repo, decide between (a) fix in place, or (b)
   allowlist with a documented reason, or (c) flag back to the user
   for a decision. Don't auto-rewrite code under (c).
4. State the per-repo outcome in the report so the user can sanity-
   check that no repo was silently skipped.

For the "CI sync-only" rule specifically: ctares, hyperlane, and euv
are the three known consumers. If a new repo (e.g. a fourth
eastspire-owned crate-cli consumer) appears, run the verifier before
deciding whether the rule already covers it.

## Pitfalls

- **`version.workspace = true` in a non-member Cargo.toml fails with
  `failed to find a workspace root`.** Cargo's inheritance syntax
  (`version.workspace`, `edition.workspace`, `readme.workspace`,
  `repository.workspace`, `*.workspace`) requires the manifest to be
  inside a workspace — either as a `[workspace.members]` entry or as
  the root. A manifest excluded via `[workspace].exclude = ["docs"]`
  cannot inherit; cargo reports `failed to find a workspace root` and
  aborts before any other manifest action (including `cargo fmt --check`,
  which calls `cargo metadata` first). Three fix paths: (a) inline the
  values (`version = "0.26.5"` etc.) — costs you re-syncing on every
  bump; (b) declare the manifest as its own single-member workspace
  (`[workspace] members = ["."]` + matching `[workspace.package]`) —
  pointless duplication; (c) add it to the parent workspace's
  `[workspace].members` and remove from `exclude` — cleanest when the
  manifest's deps don't pin to a specific upstream framework version.
  See the "Non-workspace-member manifests" section above for which path
  fits which scenario.
- **`crate sync` rewrites stale `[workspace.dependencies]` path-dep
  versions in the same commit as your intended change.** When you run
  `crate sync` to align member manifests with the root version, the
  tool also rewrites every `version = "..."` field in the root
  `[workspace.dependencies]` block to match `[workspace.package].version`.
  If your PR is meant to touch only one file (e.g. `docs/Cargo.toml`),
  `crate sync` will silently expand the diff to include root
  `Cargo.toml` lines that were already stale from a prior partial
  bump. **Mitigation**: before running sync as part of a focused fix,
  check `git diff` first — if root `[workspace.dependencies]` paths
  show stale versions, treat those as a separate concern (or include
  them in the PR with a clear commit message naming the second change).
  After running sync, `git checkout -- <file>` to drop unrelated
  rewrites, or commit them together as "chore: sync workspace
  deps" with a follow-up explanation.
- **crates-cli ↔ crates_cli name collision.** Originally the package was
  `crates-cli` (binary `cc`). crates.io normalizes `-` and `_` for name
  ownership but `cargo install` needs the exact package name, and
  `crates-cli` collided with the existing unrelated `crates_cli` crate —
  so it could NEVER be published and `cargo install crates-cli` fails with
  "could not find crates-cli in registry". The release-ci session renamed
  the package to `crate-cli` (binary `crate`) to fix that, and from this
  point forward the install line is `cargo install --git
  https://github.com/crates-dev/ctares.git crate-cli` (and `crate bump`,
  not `cc`). Before naming any new publishable crate, check
  `curl -s -o /dev/null -w "%{http_code}" -A "Mozilla/5.0" https://crates.io/api/v1/crates/<name>`
  — 200 means taken.
- **An unconditional `crate bump --patch` on master keeps stepping the
  published patch with every green push.** With no `--target-version`
  flag in the workflow, `crate bump --patch` always rewrites
  `Cargo.toml` to `0.2.7 → 0.2.8`, commits, then `crate publish` ships
  0.2.8 to crates.io even when there is no meaningful change since the
  last release — useful only for "every green push = new patch" repos.
  When the workflow itself owns the release target (workflow_dispatch
  input, tag-driven release, manual promotion), pass
  `--target-version=X.Y.Z` so master pushes no-op without the input.
  `current == target` still does patch +1 by design so the user can
  re-publish the same tag without the publish job refusing a duplicate.
- **Mark unpublishable members `publish = false`** in their `[package]` —
  `crate publish` then skips them automatically and `cargo publish` is
  blocked at the source. Applies to the crate-cli package itself and to
  example/playground crates.
- **`[workspace.members]` order IS the publish order.** A member listed
  before its local dependency makes `crate publish` error out ("invalid
  publish order"). Reorder members topologically; for a facade root
  package the order is: leaf deps first, facade after its deps,
  facade's dependents after it.
- **Path-only dev-dependencies do not constrain publish order.**
  `cargo publish` strips dev-deps from the published manifest and skips
  the registry check for `{ path = "../" }`-only entries — a member may
  dev-dep on a crate that publishes after it (e.g. macros dev-dep on
  the facade). Dev-deps WITH a `version` field do constrain (they are
  registry-checked at publish). The tool implements exactly this
  distinction; preserve it.
- **Crates outside `[workspace.members]` are invisible to the tool.**
  A non-member crate (e.g. `docs/` excluded from the workspace) gets
  no bump, no sync, no publish — keep thin per-manifest steps in CI for
  it: `sed` its `version` to the workspace version, then
  `cargo publish --manifest-path <dir>/Cargo.toml --allow-dirty --no-verify`
  with a bounded retry loop that treats "already uploaded/published" as
  success.
- **Verify a publish run against the crates.io API, not the exit code.**
  After CI publish, check each crate:
  `curl -s -A "Mozilla/5.0" https://crates.io/api/v1/crates/<name>` →
  `newest_version`. CI-side, poll the version endpoint until HTTP 200
  before declaring `published=true`.
- **The bump-commit push races concurrent merges.** A publish run that
  checks out SHA X, bumps, commits, and pushes to master dies with
  `! [rejected] HEAD -> master (fetch first)` when another PR merged
  meanwhile. Put `git pull --rebase origin master` between the bump commit
  and the push (no `-X theirs` — conflicts on hand-maintained versions
  should fail loudly). Rapid successive PR merges make one of the triggered
  runs lose this race; the loser retries on its next trigger.
- **Moving members between dirs breaks CI greps and docs.** After a layout
  move (e.g. `crates/<name>/` → `<name>/`), grep `.github/workflows/` for
  hardcoded `<old-dir>/<name>/Cargo.toml` paths and update the README layout
  section — both silently keep pointing at the old layout.
- **A green local `cargo check` does not prove CI green.** CI resolves the
  LATEST published deps; the local `Cargo.lock` may pin older ones. When a
  published dependency's API changed, reproduce locally with
  `cargo update -p <dep>` before fixing.
- **A user edit that breaks CI gets fixed with evidence, not silently
  reverted.** When a hand-edited workflow step fails in a real run, show the
  failure log, state the hard constraint, and apply the working variant —
  do not quietly restore the old form without explanation.
- **Converting a push-triggered workflow to `workflow_dispatch` requires
  extending every downstream job's `if:` to include the new trigger.**
  Switching only the `publish` job to `github.event_name == 'workflow_dispatch'`
  is the visible half of the change; the downstream `tests` / `clippy` /
  `check` / `build` jobs almost always still gate on `pull_request ||
  push`, which silently evaluates to `false` on a dispatch run. Result
  is "all skipped" with no error — `gh pr checks` for the run shows
  every job as `skipped`. See the workflow_dispatch trap section above.
- **When the user pulls back on a CLI change, default to workflow-only.**
  A repeated reversal across turns on the same task (e.g. "use the new
  flag" → "revert that, only edit CI") means the user has decided the
  tool's public surface should not change for this need. Stop modifying
  `crate-cli` source; solve the version/sync/release concern in the
  workflow file alone. Touching the tool again after a second reversal
  costs trust on top of the work — the next session will inherit the
  rule that this kind of task is "CI only".
- **Renaming a step output cascades silently across `needs.*.outputs.*`
  references.** A bump step exposes `bumped_version` / `bumped_tag` in
  its `outputs:` block; the `publish` and `release` jobs both read those
  via `needs.bump.outputs.bumped_version` and `needs.publish.outputs.bumped_tag`.
  Renaming the outputs to `synced_version` / `synced_tag` without
  updating every reader makes the reader-side `${{ ... }}` interpolate
  to an empty string — the `if:` condition `... != ''` evaluates to
  false and the downstream job silently never runs. Grep the workflow
  for the old output name and rename every reference in one pass
  before opening the PR.

## Local pre-flight for publish-order changes

Validate `cc` ordering against a real workspace without publishing: build a
tiny scratch crate that depends on crates-cli by `path`, call
`resolve_publish_order` on the target repo's `Cargo.toml`, and print the
resolved order + `publish` flags. Run with `CARGO_NET_OFFLINE=true` to avoid
registry stalls.