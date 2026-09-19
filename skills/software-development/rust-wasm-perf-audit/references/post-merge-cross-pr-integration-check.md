# Cross-PR Integration Check After Sequential Merges (2026-09-11)

> Three class-level pitfalls learned from the 14-PR v0.20.6 perf batch merge at euv. Each PR individually compiled fine, but master HEAD was broken after squash-merging all 14 in sequence. These are reusable for any project running sequential PR batches.

## Pitfall 6 (SKILL.md): Cross-PR Stale References Break Master

**Symptom**: After squash-merging N performance/refactor PRs in sequence, `cargo check --target wasm32-unknown-unknown` on master HEAD fails even though every PR's pre-commit `cargo check` exit 0'd.

**Two recurring patterns**:

1. **删后引用 (deleted-then-referenced)**:
   - PR A removes a const (or fn/struct), saying "the new X replaces it"
   - PR B (in a different PR, separate concern) still has `foo::bar()` calls to the old const/struct that PR A removed
   - Each PR compiles standalone because at the time of PR B's `cargo check`, the const still exists
   - Once PR A merges first → PR B's references become unresolved

2. **类型改动不通知 (type-changed-without-callers-updated)**:
   - PR A changes `struct Field { x: String }` to `Field { x: Cow<'static, str> }`
   - PR B (separate PR) has `let s: String = field.x.clone();` — worked when Field was String, breaks when it's Cow
   - Each PR compiles because they touch disjoint files; combined effect has type errors

**Concrete instance (2026-09-11)**:
- PR #183 (perf) added `core/src/renderer/signal_addrs/` and removed the DOM attribute `data-euv-signal-addrs` and the const `DATA_EUV_SIGNAL_ADDRS` / `CHAR_SIGNAL_ADDRS_SEPARATOR`
- PR #186 (perf) changed `TextNode::content: String` → `Cow<'static, str>`
- Both PRs had `cargo check wasm 5/5 PASS` individually
- After sequential merge: `core/src/renderer/render/impl.rs:1305-1307` referenced the deleted consts (cross-PR stale), `:945` used `.clone()` on `Cow` expecting `String` (cross-PR type mismatch)
- Master HEAD broken until PR #197 ("fix post-merge build breaks") landed

**Rule**: After merging N perf/refactor PRs in sequence, BEFORE opening the next PR, run on master HEAD:
```bash
cargo check -p <each wasm entry crate> --target wasm32-unknown-unknown
```
If any fails, that's a cross-PR integration break — open a "fix post-merge build breaks" PR with the minimal stale-reference fixes. Do NOT skip this check assuming "each PR compiled so master is fine".

## Pitfall 7 (SKILL.md): CI sync_workspace_version May Not Fire

Euv's euv-standards §17 says CI `sync_workspace_version` job auto-propagates root Cargo.toml's `[package] version` to all 6 sub-crate `[package] version` fields + the `[workspace.dependencies]` path-deps on every master push.

**Reality (2026-09-11)**: After 14 squash merges to master, **zero** `chore: sync all package versions to X.Y.Z` commits appeared. Reasons unknown — could be:
- Squash merges don't trigger the push webhook the job depends on
- The job was disabled in a CI config change
- The job's `if:` condition no longer matches squash merges

**Rule**: After merging a batch of PRs (whether squash, rebase, or merge), verify the sync actually ran:
```bash
gh pr list --repo <repo> --state all --limit 30 \
  --jq '.[] | select(.mergedAt != null) | .mergedAt'
git log --oneline --grep='sync all package versions' | head
```
If the last sync is older than your recent merges, **you must open a manual bump PR**: only modify root `Cargo.toml`'s `[package] version` (euv-standards §17 strict rule), let CI propagate. Or if the job is clearly broken, open a follow-up to manually sync all sub crates.

**Don't assume** "if I didn't change the version, no bump is needed" — for a feature/perf batch with N merged PRs, the version SHOULD advance at least patch-level (0.X.Y → 0.X.Y+1). If the last sync is from before your merges, you have an unbumped release.

## Pitfall 8 (SKILL.md): CLI Tools Need Binary Install to Verify

When fixing bugs in user-installed CLI binaries (e.g. `euv-cli`, `cargo`, `npm`), `cargo check -p <cli-crate>` succeeding does NOT mean the fix is verified — the user's `bin/<tool>` is whatever version is in their `$PATH` (often cached at `~/.cargo/bin/`), NOT the source you just edited.

**Concrete instance (2026-09-11)**:
- Source fix: `cli/src/fmt/fn.rs` made `add_indentation` treat block comments as opaque → idempotent
- `cargo check -p euv-cli`: PASS
- `/root/.cargo/bin/euv` (in `PATH`): still euv-cli-0.20.0, **buggy**
- Test: `euv fmt --path .` 4× → 4 different MD5s (still broken!)
- Fix: `cargo install --path cli --root /tmp/euv-install --bin euv --offline`
- Test: `/tmp/euv-install/bin/euv fmt --path .` 4× → 1 MD5 (stable)

**Rule**: For CLI binary fixes, always:
```bash
cargo install --path <cli-crate> --root /tmp/<cli>-install --bin <binary> [--offline]
# Verify with the installed binary, NOT the system one
/tmp/<cli>-install/bin/<binary> ...
```

Document the install path in the PR's verification section so users know they need to `cargo install` to get the fix (until the next release tag publishes the binary).

## Pre-commit gap: missing master-integration check

The existing `rust-wasm-perf-audit` SKILL.md pre-commit sequence covers per-PR hygiene (cargo check 5 wasm targets, euv fmt idempotent, clippy 0) but NOT cross-PR master-integration hygiene. Adding rule 6 above closes this gap.

## Recommended addition to subagent dispatch goals for sequential PR batches

When dispatching subagents to merge a batch of PRs in order, the goal should include:

```text
After each merge, run:
  git fetch origin master
  cargo check -p euv -p euv-core -p euv-engine -p euv-ui -p euv-example --target wasm32-unknown-unknown

If cargo check fails: STOP the batch. Open a separate "fix post-merge build breaks" PR for the stale references. Resume batch only after that PR merges.

After the last merge, run:
  git log --oneline --grep='sync all package versions' | head -3
If the most recent sync_workspace_version commit is older than the merged PRs, open a manual bump PR per euv-standards §17.
```

## Related

- `references/pr-194-scope-leak-from-stale-base.md` — pitfall 5 (PR scope leak from stale base) — combines with pitfall 6 to give a complete "merge N PRs in sequence" protocol
- `references/euv-fmt-non-idempotent-block-comments.md` — pitfall 3 detail (the fmt noise that triggered the workaround discipline)
- euv-standards §17 — the version bump rule that CI sync_workspace_version is supposed to honor