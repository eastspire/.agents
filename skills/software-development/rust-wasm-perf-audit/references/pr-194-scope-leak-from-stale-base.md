# Lesson: PR scope leak from stale fork base (euv PR #194, 2026-09-11)

> Captured 2026-09-11. The fix-PR opened fine, the audit after-the-fact caught the leak, fix-PR was rebase-revised and CI re-ran. Records the exact mechanism so future batches don't repeat.

## TL;DR

When you fork a branch for a new PR, **your starting point matters**. If the branch you fork from was itself branched off a stale master (or you accidentally fetch into the wrong base), the new branch inherits commits that already landed on master via a different PR. Without an explicit `git diff origin/master --stat` check, the leak only surfaces after you've pushed and opened the PR.

## Incident

### Setup

- master @ `b108fa10` (after PR #181 bump to 0.21.1)
- PR #180 (CHAR_SPACE &str const restore, opened by an earlier subagent) sat OPEN on a separate branch `perf/char-space-str-const`
- The 12-PR perf batch ran in parallel-ish (sequentially dispatched but each subagent had its own `git checkout origin/perf/<x>` flow)
- After PR #178-#193 merged (master b108fa10 includes everything), PR #180 was also merged into master (as `chore: bump version to 0.21.1 (#181)` and the actual CHAR_SPACE commits became part of master state via `git log`)
- The `bin/euv` installed in `/root/.cargo/bin/euv` was the pre-fix euv-cli-0.20.0 binary

### What went wrong

The fix-euv-fmt-bug subagent dispatched with the workflow step "checkout clean origin/master". But the local checkout had a stale `fix/euv-fmt-non-idempotent-block-comments` branch pointing to a base that included **PR #180's commits** (because the branch was created earlier when PR #180 was still OPEN, then master merged PR #180 but the local branch's parent didn't rebase).

Subagent proceeded to:
1. Implement the fix in cli/src/fmt/fn.rs (correct)
2. Add regression tests in cli/tests/fmt/fn.rs (correct)
3. Run euv fmt → "1 file changed" → saw `core/src/vdom/attribute/const.rs` and `core/src/vdom/attribute/impl.rs` get modified by euv fmt → these came from PR #180's CHAR_SPACE const restoration that wasn't yet on the branch's "current master" reference but WAS in the branch's parent commits
4. Committed everything as one PR
5. Pushed and opened PR #194

### Discovery

User asked me (orchestrator) to verify PR scope. I ran:

```bash
git diff origin/master origin/fix/euv-fmt-non-idempotent-block-comments --stat
# Result: 4 files
#   cli/src/fmt/fn.rs                | 101 +++++++  (correct - the fix)
#   cli/tests/fmt/fn.rs              |  57 +++++  (correct - regression test)
#   core/src/vdom/attribute/const.rs |   3 ++  (WRONG - PR #180 content)
#   core/src/vdom/attribute/impl.rs  |  12 ++-- (WRONG - PR #180 content)
```

The 2 core/ files were not part of the fix. They were inherited from the stale base.

### Fix

Cherry-pick the cli-only commit onto a fresh branch from current master:

```bash
git checkout origin/master
git checkout -b fix/euv-fmt-non-idempotent-block-comments-clean origin/master
git cherry-pick <cli-fix-commit-sha>
git push origin fix/euv-fmt-non-idempotent-block-comments-clean --force-with-lease
# ... but we kept the same branch name, so:
git branch -D fix/euv-fmt-non-idempotent-block-comments
git push origin :fix/euv-fmt-non-idempotent-block-comments
git push origin fix/euv-fmt-non-idempotent-block-comments-clean:fix/euv-fmt-non-idempotent-block-comments
# (or just use the simpler: rebase the existing branch, then force-push)
```

Actual method used: cherry-pick onto a fresh branch from origin/master, then rename + force-push to overwrite the remote. Result: PR #194 diff dropped from 4 files (156 lines) to 2 files (147 lines), only `cli/`. CI re-ran, all 5 checks still passed.

## Rule (now embedded in SKILL.md §5)

**Before opening any PR, run:**

```bash
git fetch origin master
git diff origin/master <your-branch> --stat
```

If the file list is wider than the PR's intended scope, you have a stale-base leak. Fix by:

- `git rebase -i origin/master` and drop the unrelated commits, OR
- `git cherry-pick <good-commit-sha>` onto a fresh branch from origin/master

The pattern: **"scope check" before "scope commit"**. Don't trust subagents to remember this — make it the 5th item in the pre-commit list.

## Why subagents miss this

Subagents work in a tight local-checkout loop:
1. Read code → make change → run pre-commit → push → open PR
2. The "did I inherit someone else's work?" question doesn't have a natural prompt
3. `euv fmt` reformatting unrelated files is the first signal, but if the subagent interprets it as "fmt noise" and reverts the wrong files, the leak persists silently

## Verification by rebuild (related lesson)

When the fix is to a CLI binary (like `euv fmt`), **just running the locally-installed `/root/.cargo/bin/euv` does NOT verify the fix**. The installed binary is from a previous `cargo install` or from the cargo cache (euv-cli-0.20.0 etc.). You need:

```bash
cargo install --path <crate> --root /tmp/<x>-install --bin <bin-name> --offline
# or build directly:
cargo build --release --bin <bin-name>
# Then run with the new binary, NOT /root/.cargo/bin/<bin-name>
```

In our session, PR #194's fix binary was at `/tmp/euv-install/bin/euv`. Verification used that path, not the system one.

## Cross-references

- Parent skill: `../SKILL.md` §5 "PR 范围检查" (newly added)
- Related: `lessons-from-12-pr-batch-2026-09-11.md` §"Orchestrator MUST independently verify subagent claims before declaring '✅ done'"
- Related: `euv-fmt-non-idempotent-block-comments.md` (the bug being fixed)