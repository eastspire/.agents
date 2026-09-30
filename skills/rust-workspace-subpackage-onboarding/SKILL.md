---
name: rust-workspace-subpackage-onboarding
description: "Add or remove a Rust workspace subpackage. Add: onboard an upstream crate as a local workspace member, then normalize through dep unification, [workspace.dependencies] sort, and [package] field inheritance. Remove: dependency-pre-flight + reference sweep + git rm + verify the workspace still builds, as a single chore commit."
version: 0.1.0
author: Hermes Agent (curator)
license: MIT
platforms: [macos, linux, windows]
metadata:
  hermes:
    tags: [rust, cargo, workspace, subpackage, crate, integrate]
    category: software-development
    related: [github]
---

# Onboard an upstream crate as a Rust workspace subpackage

Use when the user wants an existing upstream library to live **inside** an existing Cargo workspace as a local sibling crate, rather than being pulled in as an external dependency from crates.io. The end state: a `path = "./DIR"` dep declared in the workspace root, the directory containing a real `Cargo.toml` from the upstream, and the workspace able to build/test it with no registry round-trip.

This is NOT vendoring — the cloned directory IS the subpackage, and it remains a git repository with its own `.git` (don't strip it). It's also NOT a fork in the legal sense; nothing in the upstream is rewritten during onboarding. Edits, if any, come later as a separate step.

## When to use

- User says "clone http-foo into this project as a subpackage `foo`" (or `request`, `constant`, `compress`, etc.).
- User wants to consolidate several sibling crates from one author/org into a single workspace for shared versioning, release, and CI.
- The target project is a Cargo workspace (has root `Cargo.toml` with `[workspace]` and a `members` array).

## Don't use for

- Adding an external dep to a single crate (`cargo add` or edit that crate's `[dependencies]`) — that's a one-line change, not onboarding.
- Vendoring source into `vendor/` — that's a different mechanism (`cargo vendor`) used for offline builds.
- Replacing the workspace's `Cargo.toml` entirely — that's a workspace restructure, not onboarding.

## Prerequisites

- Confirm the target project is a Cargo workspace: the root `Cargo.toml` must contain `[workspace]` with a `members = [...]` array. `cargo metadata --no-deps --format-version 1 | jq '.workspace_members'` is the canonical check.
- Confirm the target subdirectory name does not collide: `ls WORKSPACE_ROOT/DIR` should be absent.
- Git credentials that can `git clone` the upstream — HTTPS works for public repos without any auth setup; SSH requires the user's key in `~/.ssh/config` for `github.com`.
- `cargo` is installed and resolves on the existing workspace (it should — the workspace already builds).

## Procedure

1. **Decide the directory name.** Match one of these conventions (in order of preference):
   - The upstream repo's basename minus a common prefix. Example: `crates-dev/http-request` → `request/` when a sibling `crates-dev/http-constant` will land at `constant/`. The shared prefix carries no meaning inside the workspace.
   - The upstream repo's full basename (`http-request` → `http-request/`) when the prefix carries meaning, e.g. when two siblings would collide under a shared stripped name.
   - Ask the user if unsure — they often have a strong preference and renaming later means editing every `path =` reference.
   - When unclear, the safest default is the upstream repo basename. Don't strip a prefix silently.

2. **Pre-flight the upstream repo.** Before cloning, fetch its manifest to confirm it's real, see its default branch, and grab the version to use in `workspace.dependencies`:
   ```bash
   UA='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15'
   curl -sSL -A "$UA" "https://raw.githubusercontent.com/OWNER/REPO/master/Cargo.toml" | head -20
   # fall back to /main/ if 404
   ```
   Record: crate name, version, edition. The default branch is `master` for many Rust crates (notably the `crates-dev/*` namespace); try `master` first, `main` second.

3. **Clone into the workspace root.** The subpackage is a top-level directory, NOT nested under `crates/`, `packages/`, or similar — Rust workspace convention puts each member at the root alongside existing siblings like `core/` and `cli/`. From inside the workspace root:
   ```bash
   cd WORKSPACE_ROOT
   git clone --depth 1 https://github.com/OWNER/REPO.git DIR
   ```
   `--depth 1` is appropriate here: the subpackage is sourced from upstream, not developed in-place. If the user plans to push commits back to a fork from this clone, drop `--depth 1` so all branches and tags are local.

4. **Add the directory to `[workspace] members`.** Edit the root `Cargo.toml`, in the order the existing members are organized (most workspaces group by logical layer, not alphabet — preserve that order):
   ```toml
   [workspace]
   members = [
       "core",
       "macros",
       "type",
       "cli",
       "DIR",   # NEW
   ]
   ```

5. **Add a `workspace.dependencies` entry** with the version captured in step 2:
   ```toml
   [workspace.dependencies]
   CRATE_NAME = { path = "DIR", version = "X.Y.Z" }
   ```
   The `path` makes it a local subpackage; the `version` is required by Cargo's workspace-dependency schema and is used when the subpackage is later published or consumed by external crates.

6. **Verify, don't trust.** Run `cargo metadata --no-deps --format-version 1` and confirm the new subpackage appears in `workspace_members`. Parse with:
   ```bash
   cargo metadata --no-deps --format-version 1 | python3 -c "
   import json, sys
   d = json.load(sys.stdin)
   for m in d['workspace_members']:
       print(m)
   "
   ```
   The new member must show up as `path+file://.../DIR#CRATE_NAME@VERSION`. If it doesn't, the `[workspace] members` line is wrong (typo, missing entry, or the `Cargo.toml` inside `DIR` is malformed — `cargo metadata` will surface the latter as a stderr error).

7. **Stop and confirm with the user.** Do NOT automatically:
   - Add `workspace = true` references to other workspace crates' `[dependencies]` (that's a usage decision, not an onboarding step).
   - Rewrite the subpackage's own `Cargo.toml` to inherit from `[workspace.package]` (a cleanup, not onboarding).
   - Commit anything (the user often wants to review the diff before staging).
   - Run `cargo build`/`cargo test` across the whole workspace — that can take 10+ minutes on a fresh project with many deps, and the user may not be ready to download the registry index.

## Pitfalls

- **Don't assume `main` is the default branch.** Older Rust crates (notably `crates-dev/*`) use `master`. Try `master` first when fetching via `raw.githubusercontent.com` — a 404 on `main` is normal, not an error.
- **Subpackages must be top-level directories, not nested.** Convention is `WORKSPACE_ROOT/DIR/Cargo.toml`, not `WORKSPACE_ROOT/crates/DIR/Cargo.toml`. The nested form requires also configuring `[workspace] members = ["crates/*"]` (glob) and breaks existing members that use bare relative paths. Don't introduce nested layout unless the workspace already uses it.
- **Don't invent the `version =` value.** Read it from the upstream's own `Cargo.toml`. If you guess, `cargo publish` later will reject the workspace dependency for being out of sync with the on-disk crate.
- **Don't add `[profile.dev]` / `[profile.release]` to the workspace root just because the subpackage has them.** Subpackages that weren't workspace-adapted carry their own profile tables; cargo emits a warning ("profiles for the non root package will be ignored") but the build succeeds. The warning is informational, not an error — don't proactively "fix" it during onboarding. If the user asks for dependency unification (see Stage 2 below), deleting the subpackage's profile table is part of that work.
- **HTTPS clones need no GitHub auth.** Public repos clone fine with `https://github.com/...` URLs even without `gh auth login` or `~/.ssh/config`. Don't reach for SSH first; it adds an auth dependency. Switch to SSH only if the user pastes a `git@github.com:` URL or asks for it.
- **Skip the `git fetch --all --tags` step from mass-clone workflows.** This is local-integration, not mirror-cloning. `--depth 1` is appropriate; bringing all branches into a workspace subpackage creates noise in `git branch` lists and is rarely wanted.
- **Never edit the subpackage's `Cargo.toml` during onboarding.** Even "harmless" edits (changing `version`, adding `edition.workspace = true`) silently break the assumption that this directory equals the upstream. Do edits in a separate, explicit step the user has approved.
- **Don't auto-commit.** Onboarding produces a dirty working tree (`Cargo.toml` modified + a new directory + the subpackage's own `.git`). The user almost always wants to review the diff and possibly split it into "add subpackage" and "wire into existing crates" commits. Leave the tree dirty and report.
- **Don't use `web_extract` for `raw.githubusercontent.com`.** It returns "Blocked: private network" for githubusercontent on this machine — a known false positive (curl gets the same URL fine). Use `curl -sSL` with a Safari User-Agent instead. See `references/raw-github-fetch.md` for the exact incantation.

## Verification

- `ls WORKSPACE_ROOT/DIR/Cargo.toml` exists.
- `cargo metadata --no-deps --format-version 1` lists the new subpackage as `path+file://.../DIR#CRATE_NAME@VERSION`.
- `grep -E '"DIR"' WORKSPACE_ROOT/Cargo.toml` finds it in the `members` array.
- `grep -E 'CRATE_NAME = \{ path' WORKSPACE_ROOT/Cargo.toml` finds the `workspace.dependencies` entry.
- The subpackage's own `.git/` is present (`ls -d DIR/.git`) — confirms the clone succeeded, not just an empty directory.

## Common follow-ups (do NOT do these automatically — flag to the user)

- Add `CRATE_NAME = { workspace = true }` to the `[dependencies]` of existing workspace crates that need to consume the new subpackage. Suggest candidate crates based on naming and imports; let the user decide.
- Delete the subpackage's local `[profile.dev]` / `[profile.release]` tables so the workspace root's profiles apply. Resolves cargo's "profiles for the non root package will be ignored" warning.
- Stage and commit the changes. Suggest a commit message convention like `chore: onboard CRATE_NAME as workspace subpackage`.

## Scope of "子包" / "subpackage" in this user's vocabulary

When this user says "子包", they mean **only the crates newly onboarded in the current task**, not every workspace member. Pre-existing workspace members (`core`, `macros`, `type`, `cli` in hyperlane) are out of scope unless the user names them. When a request like "delete the .gitignore of all subpackages" arrives, **ask which set** — touching pre-existing crates can change build behavior or git tracking the user didn't intend.

Examples seen in this user's projects:

- `hyperlane` workspace: pre-existing members are `core/macros/type/cli`. New subpackages = `request/constant/compress`. The two sets have different `.gitignore` rules (`cli` has `/tmp`, `macros` has `**target`) — only delete from the new set unless told otherwise.

## Stripping artifacts that no longer apply after onboarding

Subpackages cloned from upstream carry files that assume a single-crate repository layout. In monorepo mode these become dead weight or actively wrong. Items the user has asked to remove in this workflow:

- **`.git/` directory of each subpackage.** The subpackage is now part of the parent repo; its independent git history is irrelevant. Removing `.git` also prevents accidentally treating the directory as a nested git repo. Use `rm -rf DIR/.git` per subpackage.
- **`.github/workflows/*.yml` of each subpackage.** These CI scripts run `cargo publish`, create GitHub Releases, and tag from the subpackage's own version — they assume the subpackage IS the repository. In monorepo mode they will misfire (wrong auth context, publishing from wrong directory, version detection via `toml get Cargo.toml package.name` returning the right name but workflow running against monorepo metadata). Delete the entire `DIR/.github/` tree.
- **`.gitignore` of each subpackage** if its rules are fully covered by the workspace root's `.gitignore`. Audit before deleting — if a subpackage has rules NOT covered at root (e.g. `cli` had `/tmp`, `macros` had `**target`), keep them.
- **README badges and links pointing to the upstream organization.** When the subpackage is moved into the user's org (e.g. `crates-dev/http-xxx` → `hyperlane-dev/http-xxx`), the badge URLs 404 because the new org doesn't host those crates. Two fixes: (a) rewrite URLs to point at the new org's monorepo location, or (b) delete the badge lines. **Do not silently rewrite** — the user has to choose.

### Don't strip these

- **LICENSE file's `Copyright (c) <YEAR> <ORG>` line.** This is copyright attribution, not a URL. Changing it has legal implications and the user has explicitly drawn the line at "address/organization" changes. Even when other artifacts are migrated to the new org, the LICENSE copyright line stays until the user says otherwise.
- **`description` / `keywords` / `categories` in `[package]`.** These are per-crate metadata, not workspace metadata. Don't move them to `[workspace.package]`. See "Package field inheritance" below.

## Stage 2: unify all dependencies through `[workspace.dependencies]`

When the user says "全部统一到根 toml" / "所有依赖都用 workspace" / "子包 deps 都用跟 toml", they want **every** dependency declared by every subpackage moved to the root `[workspace.dependencies]` table, with each subpackage's `[dependencies]` / `[dev-dependencies]` reduced to `{ workspace = true }` lines. This applies to external crates.io deps, not just intra-workspace paths.

### Procedure

1. **Inventory every dep across all subpackages.** Use a Python pass with `tomllib` (stdlib in 3.11+) to collect `{name: [(subpkg, section, spec_dict), ...]}`. Don't eyeball it — same crate in 5 places with 3 different feature sets is normal and easy to miss.
2. **Collapse duplicates to one canonical workspace entry.** For each crate, pick the *most general* spec (most features, broadest scope). Workspace `features = [...]` set the *union*, not the intersection, so picking the biggest set keeps every consumer working. Record all per-subpackage overrides you'll need to keep.
3. **Write the consolidated `[workspace.dependencies]` table.** Apply the user's two-group sort (see `references/workspace-deps-sort.md` for the exact rule and audit script): intra-workspace `path = "..."` entries first, then externals, both groups sorted by **full line length ascending with ties broken by lexical order**. The "length" the user means is `len("name = value")` — including the ` = ` and the entire RHS, not just the key. Shortest line first; within equal length, alphabetically by name. Validate the result with the audit script in the reference before committing.
4. **Rewrite every subpackage's `Cargo.toml`**: every dep line becomes `name = { workspace = true }`. Delete the subpackage's own `[profile.dev]` / `[profile.release]` tables — the workspace root's profiles now apply, which both fixes the "profiles for non root package" warning and removes drift.
5. **Verify**: `cargo metadata --no-deps --format-version 1` succeeds and lists all members. Then `cargo check --workspace --offline` for real compile validation.
6. **Audit**: parse every subpackage's manifest and confirm every dep is `dict(workspace=True)`. A leftover string spec or `version = "..."` is a regression.

### Pitfalls (Stage 2)

- **Same crate, different features across subpackages → pick the broadest in workspace.dependencies.** When `tokio` appears with `features = ["full"]` in three places and `features = ["macros", "rt-multi-thread"]` in a fourth (e.g. `request/dev-dependencies`), the workspace entry must use `features = ["full"]` so cargo's feature union covers all callers. The narrower caller will over-include, which costs compile time but doesn't break functionality. If the over-inclusion matters (binary size, conflicting features), the narrower caller can override:
  ```toml
  tokio = { workspace = true, default-features = false, features = ["macros", "rt-multi-thread"] }
  ```
  Don't write the override speculatively — wait for the user to say it matters.
- **`serde = "1.0.229"` (no features) becomes `serde = { workspace = true }` where workspace has `features = ["derive"]` → over-includes `derive`.** This is the same feature-union gotcha. Acceptable when only `request` is affected; problematic when it bloats a `no_std` or wasm crate. Check downstream effects before claiming the change is "equivalent".
- **`write_file` over an existing Cargo.toml is refused unless you've fully `read_file`d it in this session.** Patches via `patch` tool don't satisfy the read-before-write guard for whole-file rewrites. When you need to rewrite a manifest, `read_file` it first (every page if it's large), then `write_file`. `patch` is fine for surgical edits and skips this guard.
- **Don't keep `[profile.dev]` / `[profile.release]` in subpackages "just in case".** They are silently ignored (cargo warns) and create the appearance of per-crate customization that isn't real. Delete them as part of unification; if a crate truly needs different profile settings later, that's a separate discussion.
- **`--offline` is required for verification when the registry index isn't warm.** A first-time `cargo check` after onboarding may try to download hundreds of crates and exceed reasonable timeouts. Run `cargo fetch` once to populate the cache, then `cargo check --workspace --offline` for verification.
- **The "is_local" classification for `[workspace.dependencies]` is by *presence of `path` field*, not by "value starts with `{`".** Many externals use inline tables too (`{ version = ..., features = [...] }`). A naive `value.startswith("{")` check puts externals into the intra-workspace group. Inspect the parsed dict for a `"path"` key, or do the classification by inspecting the rendered value's tokens.
- **`search_files` is unreliable for verifying toml key changes.** When you patch a toml file and want to confirm `pattern: "repository"` no longer matches in `request/Cargo.toml`, the search can return zero hits even when the file still contains the string. The pattern is matched by ripgrep, which is line-anchored and supports regex, but the tool's output wrapper can lose counts when the same match appears across many files in a glob. Don't trust a zero-count to mean "absent". For toml audit, parse with `tomllib` and confirm the parsed dict instead:
  ```python
  import tomllib
  t = tomllib.loads(Path("sub/Cargo.toml").read_text())
  assert "repository" not in t["package"]
  ```
  This is the source of truth.
- **`exclude.workspace = true` works in cargo ≥ 1.78 and IS honored at `cargo package`/`cargo publish` time.** The earlier belief that cargo silently ignores it was based on `cargo metadata` output — but `cargo metadata` does not surface `exclude` at all, so absence there is not evidence. Correct verification is to actually run `cargo package -p foo --list --allow-dirty --no-verify` and confirm the resulting `.crate` excludes what `[workspace.package].exclude` declares. Earlier versions of this skill said otherwise — that was wrong. Use `exclude.workspace = true` in subpackages and aggregate the canonical list at `[workspace.package].exclude` only.

## Stage 3: package-field inheritance via `[workspace.package]`

When the user says "字段除了 description keywords categories 其他的全部使用 workspace" / "all package fields except description/keywords/categories should use workspace", they want a specific `[package]` rewrite:

- **Keep literal** (per-crate): `name`, `version`, `description`, `keywords`, `categories`, `exclude`.
- **Inherit from `[workspace.package]`** (`.workspace = true`): `readme`, `edition`, `authors`, `license`, `repository`.

This is layered on top of Stage 2: dependencies are already all `{ workspace = true }`, and now `[package]` metadata follows the same pattern for the inheritable fields.

### Why this stage is opt-in, not automatic

- **`version` is almost always per-crate.** Newly-onboarded subpackages carry their own upstream versions (e.g. `http-request@8.91.128`, `http-constant@5.6.15`, `http-compress@3.0.28`) that are unrelated to the workspace root's version (`21.3.6`). Unifying `version.workspace = true` overwrites those with the workspace version — semver-collisions, broken publish artifacts, and lost upstream identity. **Ask the user before unifying `version`.** If they confirm they want a single shared version across the workspace, then `version.workspace = true` is correct; otherwise leave per-crate.
- **`name` is *never* inheritable.** Each crate in a workspace has its own package name. Cargo errors on `name.workspace = true`.
- **`exclude` is also *never* inheritable.** Cargo's `package.exclude` does not support `.workspace = true`. Keep it literal.
- **`description`, `keywords`, `categories` are inheritable in principle but the user has explicitly excluded them.** Cargo's `[workspace.package]` *does* support these as workspace values, but the user keeps them per-crate — likely because each subpackage's description/categories genuinely differ. Don't override their preference to "tidy up further".

### Procedure

1. **Confirm root `[workspace.package]` has every inheritable field defined.** For the user's standard set, the root must define `readme`, `edition`, `authors`, `license`, `repository`. Missing any one means the inherited value will be a TOML error. Add to root if missing.
2. **For each subpackage, rewrite `[package]` in this exact field order** (preserves readability and matches the user's house style):
   ```toml
   [package]
   name = "<literal>"
   version = "<literal>"
   readme.workspace = true
   edition.workspace = true
   authors.workspace = true
   license.workspace = true
   repository.workspace = true
   description = """<literal>"""
   keywords = ["<literal>"]
   categories = ["<literal>"]
   exclude = ["<literal>"]
   ```
4. **Use `write_file`, not `patch`.** Rewriting `[package]` in place via `patch` works but tends to leave the field order messy after multiple prior edits. Whole-file rewrite with `read_file` first (to satisfy the guard) is cleaner. Preserve all other sections (`[dependencies]`, `[dev-dependencies]`, `[[bin]]`, `[lib]`, profile tables) byte-for-byte.
5. **Verify**: `cargo check --workspace --offline` must succeed, and a Python audit must confirm every inheritable field in every subpackage is `dict(workspace=True)`.

### Pitfalls (Stage 3)

- **`version.workspace = true` written INSIDE an inline table fails to parse.** Forms that fail:
  ```toml
  CRATE = { path = "X", version.workspace = true }       # in [workspace.dependencies]
  CRATE = { version.workspace = true }                    # anywhere inline
  ```
  Error: `invalid type: map, expected a string ... in 'version'`. The dot-key form must be a top-level key under the section. Correct forms:
  ```toml
  # in [workspace.dependencies]
  CRATE = { path = "X" }
  CRATE.version.workspace = true      # separate dot-key on its own line

  # in [package]
  version.workspace = true            # separate dot-key under [package]
  ```
  Symptom in a workflow context: `cargo publish -p foo` aborts with the parse error before it ever talks to crates.io. Symptom in `cargo check`: the same parse error blocks the whole workspace.
- **When subpackages adopt `version.workspace = true`, `[workspace.dependencies]` entries must drop their hardcoded `version = "X.Y.Z"` field too.** If `[workspace.dependencies]` still says `http-compress = { path = "compress", version = "3.0.28" }` while `compress/Cargo.toml` resolves to `21.3.6` via inheritance, cargo errors with `failed to select a version for the requirement http-compress = "^3.0.28", candidate versions found which didn't match: 21.3.6`. Either:
  - Drop the `version` field entirely from the path entry: `http-compress = { path = "compress" }` (cargo reads the version from the subpackage's own manifest), OR
  - Mirror the workspace inheritance pattern: `http-compress = { path = "compress" }` followed by `http-compress.version.workspace = true` on the next line.
  Pick the first — it's shorter, and when versions are unified the field becomes redundant anyway.
- **Don't unify `version` without asking first.** Newly-onboarded subpackages carry their own upstream versions (e.g. `http-request@8.91.128`) that are unrelated to the workspace root's version (`21.3.6`). Unifying overwrites them. If the user confirms they want shared versioning across the whole workspace, proceed; otherwise leave per-crate. The version can be unified later in a single explicit commit that the user reviews as a deliberate "all packages bumped to 22.0.0" change.
- **`#![edition = "2024"]` inner attribute does NOT override the edition for an integration test crate.** A standalone `tests/<name>.rs` is compiled as its own crate, and the edition is decided by `package.edition` (or `[[test]] edition`). Putting `#![edition = "2024"]` at the top of the file fails with `cannot find attribute 'edition' in this scope`, leaving the file on Rust 2015 and breaking `async fn` / `async move` with E0670. Symptom: cargo's lint complains before the real compile errors do. The right fix is in `Cargo.toml`:
  ```toml
  [package]
  edition.workspace = true        # OK if workspace.package.edition is set

  [[test]]
  name = "integration_foo"
  # edition = "2024"             # deprecated in newer cargo; usually unnecessary
  ```
  If `package.edition` is inherited from `workspace.package` correctly, standalone integration tests get the right edition automatically — no per-test override needed.

### Exclude aggregation: just use `[workspace.package].exclude`

Subpackages should declare `exclude.workspace = true`. The canonical list lives at the root:

```toml
[workspace.package]
exclude = ["target", "Cargo.lock", "sh", ".github", "logs", "img", "**/*.log", "debug", "tmp"]
```

To recompute after adding or removing a subpackage, run a Python pass with `tomllib` over every subpackage, take the union, sort alphabetically, and write back. A drift check that fails CI is worth adding once the list is stable.

**Note**: `cargo package` always includes `Cargo.toml.orig`, `.cargo_vcs_info.json`, and (when present) `Cargo.lock` in the `.crate`, regardless of `exclude`. That's hardcoded cargo behavior — it is not a bug in `exclude` and adding more entries to the list won't suppress them. Use `[package] include = [...]` (positive list) if you need to suppress them; otherwise accept them.

## Related files

- `references/raw-github-fetch.md` — the curl incantation for fetching upstream `Cargo.toml` when `web_extract` falsely blocks githubusercontent, including the master-then-main fallback.
- `references/workspace-deps-sort.md` — the user's exact sorting rule for `[workspace.dependencies]` (intra-workspace first, then externals, full line length ascending, ties by lexical) plus the audit script that validates it.
- `references/monorepo-publish-workflow.md` — deriving publish order from `cargo metadata`, the workflow shape that publishes N crates in topological order, and the GitHub Actions YAML gotchas (especially: don't put `|` at the start of a line inside a `NOTES="..."` literal).
- `references/subpackage-removal.md` — the symmetric inverse of this skill: deleting a workspace member, including the dependency-pre-flight check, reference sweep table, and the verify pipeline.
