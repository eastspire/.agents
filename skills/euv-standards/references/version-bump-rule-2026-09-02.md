# euv crate version bump — end-to-end verified rule (PR #101, 2026-09-02)

> **USE THIS when**: user asks to bump the euv crate version (any kind — patch / minor / release) inside `/root/github/euv-dev/euv` (or a fork clone). The rule below was the **second** rewrite of §17 in `SKILL.md`; the first draft was wrong. This reference is the verified source of truth.

## 1. The rule — bump ONE line, CI does the rest

**Only touch root `Cargo.toml` line 3 (`[package] version`). Do not touch:**

- `Cargo.toml` `[workspace.dependencies]` (lines 22-28) — 6 path-dep `version = "..."` entries
- `core/Cargo.toml`, `ui/Cargo.toml`, `engine/Cargo.toml`, `cli/Cargo.toml`, `macros/Cargo.toml`, `example/Cargo.toml` — each has its own `[package] version`

CI's `sync_workspace_version` job (`.github/workflows/rust.yml`) auto-propagates the root version to all workspace members on the **first `push` to `master` after the squash merge**. PR-side it shows as `skipped` (the `if:` clause only matches `event_name == 'push'`); post-merge it runs successfully.

## 2. End-to-end evidence (PR #101, 2026-09-02)

### PR diff

```
$ git diff origin/master..HEAD --stat
 Cargo.toml                       |  2 +-
 core/src/renderer/render/impl.rs | 102 ++++++++++++++++++++++++++++++---------
 ui/src/style/class/fn.rs         |  20 ++++----
 3 files changed, 89 insertions(+), 35 deletions(-)
```

**The version bump is 1 line change in 1 file.** No member crate touched, no `[workspace.dependencies]` path-dep touched.

### Merge commit

```
9411c9a perf(core): add zero-allocation pre-scan to unwrap_component_owned (0.18.37) (#101)
2f2e4fb chore(release): bump all crates to 0.18.36 (#100)
```

### Post-merge CI run 33590700876 (push to master)

```
setup                       ✅ success
sync_workspace_version      ✅ success    ← CI auto-bumped all 6 member crates + path-dep
tests                       ✅ success
clippy                      ✅ success
check                       ✅ success
build                       ✅ success
publish                     ⏳ in_progress
```

CI's auto-sync commit on master immediately after the merge touched the remaining 7 files (root + 6 member crates, `+14/-14` lines). Final master state: root `0.18.37` and all 6 member crates `0.18.37`.

### Verification

```bash
$ grep -m1 '^version' Cargo.toml
version = "0.18.37"
$ for c in core ui engine cli macros example; do
      printf "%-10s %s\n" "$c" "$(grep -m1 '^version' $c/Cargo.toml)"
  done
core       version = "0.18.37"
ui         version = "0.18.37"
engine     version = "0.18.37"
cli        version = "0.18.37"
macros     version = "0.18.37"
example    version = "0.18.37"
```

## 3. Why the previous rule (bump all 7 places) was wrong

The previous SKILL.md §17 (now superseded) claimed:

> "CI `sync_workspace_version` job only triggers in release-only flow. Daily patch/minor bump PRs don't trigger sync — must locally bump all 7 places, otherwise CI build fails."

This was based on observing `sync_workspace_version` as `skipped` on the PR's own CI run. But that observation was correct AND the conclusion drawn was wrong: the `if:` clause `github.event_name == 'push' && github.ref_name == 'master'` means sync is **skipped on PR**, **runs on master push** — including the push that squash-merge creates. Bumping all 7 in the PR not only duplicates CI's job, it makes the diff noisier and causes merge conflicts with the auto-sync commit.

User feedback (verbatim from chat):

> "升级小版本从记忆读取规则,不是全升级"

## 4. The correct recipe

```bash
cd /root/github/euv-dev/euv
# ONLY this:
sed -i 's/^version = "0.18.36"$/version = "0.18.37"/' Cargo.toml

# Then verify locally:
cargo check -p euv -p euv-core -p euv-engine -p euv-ui -p euv-example --target wasm32-unknown-unknown  # 17s
euv fmt                                                                                                    # workspace clean
wasm-pack build example                                                                                   # 47s; version renders in DOM as v0.18.37

# Then PR — force-push amend if cargo fmt --check at CI rejects a match-arm one-liner.
# Then merge. CI does the rest.
```

## 5. What `sync_workspace_version` actually does

The job script (from `.github/workflows/rust.yml`) reads the root `[package] version`, then for each `Cargo.toml` in workspace members (`core`, `ui`, `engine`, `cli`, `macros`, `example`) sed-replaces their `[package] version` AND each path-dep `version = "..."` in the root `[workspace.dependencies]` block. The job is `if: github.event_name == 'push' && github.ref_name == 'master'`, so:

| Event | `sync_workspace_version` runs? |
|---|---|
| `push` to `master` | ✅ |
| `pull_request` opened/synced/reopened | ❌ skipped (by design — this is what the PR #101 CI display showed) |
| `push` to any non-`master` branch | ❌ skipped |

**Conclusion**: skipping on PR is **not a failure** and **not a sign that the PR needs to bump everything manually**. It's the job's expected wait-for-master behavior.

## 6. When you DO need to bump all 7 places

Only one scenario: **adding a new sub-crate to `members`** for the first time. The new crate's `[package] version` starts at whatever it is in the template, and to keep workspace consistency, the PR that introduces the crate should also bump the root + existing path-deps if they don't already match. After that initial sync, the rule in §1 reverts to "bump root only".

## 7. Related reference files in this skill

- `references/consolidated-pr-workflow.md` — multi-PR consolidation PR flow
- `references/renderer-signal-lifecycle.md` — renderer/signal pattern bank
- (this file) — version-bump rule with end-to-end evidence

## 8. Pitfall: patch tool's lint output for Rust 2024 `let chains`

A side-finding from this session worth noting: the patch tool's embedded `rustfmt` is an OLD version (< 1.85) that does NOT understand Rust 2024 `let chains` syntax. When you patch a file that uses `if let X = ... && let Y = ...`, patch tool's lint step will report:

```
error: let chains are only allowed in Rust 2024 or later
```

even when the file is perfectly valid (CI's rustc 1.98 accepts it). The patch tool's "Pre-existing lint errors — this edit didn't introduce new ones" message is the cue to ignore the lint output and proceed. The actual code is fine; the lint is a tooling-version mismatch.