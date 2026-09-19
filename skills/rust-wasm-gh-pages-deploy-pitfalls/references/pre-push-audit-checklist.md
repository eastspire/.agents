# Pre-push audit checklist for euv-dev PRs

Mandatory verification steps to run **before** `git push -u origin <branch>` on
any euv example / euv-engine fix. Each step has a one-line rationale
(why the check matters) and the exact command. Catches the 80% of PRs that
would otherwise get bounced in review.

## 1. rust-standards keyword-file compliance

**Why**: `rust-standards` rule 1.1 (every directory holds only one of the
9 keyword-named files: `const.rs` / `static.rs` / `fn.rs` / `enum.rs` /
`struct.rs` / `trait.rs` / `impl.rs` / `type.rs` / `mod.rs`). Adding
`*_fn.rs` or `*_impl.rs` etc. is a real audit failure; reviewers will
revert it.

```bash
python3 /root/.hermes/skills/rust-standards/scripts/audit_rust_standards.py \
  /root/github/euv-dev/euv
```

Expect:
- `PASS: 1. non-keyword prod files` (or only pre-existing entries that
  you didn't introduce — note them in the PR body)
- `PASS: 2-13` all

If you introduced a non-keyword filename, fix BEFORE pushing:

```bash
git mv example/src/page/<page>/hook/<old>_fn.rs example/src/page/<page>/hook/fn.rs
# In mod.rs:
#   -mod <old>_fn;        →  mod r#fn;     (fn is a keyword, raw identifier)
#   +pub(crate) use {r#fn::*, ...};
# Then re-run audit. cargo clippy / build will catch any missed references.
```

Same applies to `*_struct.rs` → `r#struct`, `*_mod.rs` → `r#mod`, etc.

## 2. Clippy + build both profiles

**Why**: clippy catches a wider class of lints than the build, and
release build often fails where dev passes (wasm-opt panic on certain
floating-point patterns is the classic one).

```bash
export PATH=/root/.cargo/bin:$PATH
cd /root/github/euv-dev/euv
cargo clippy -p euv-example --all-targets --offline   # dev, fast
euv build --crate-path ./example \
  -- --target web --out-dir www/pkg --out-name euv \
     --no-typescript --no-pack --no-gitignore           # dev
euv build --release --crate-path ./example \
  -- --target web --out-dir www/pkg --out-name euv \
     --no-typescript --no-pack --no-gitignore           # release (wasm-opt)
```

The `--out-name euv` is critical: it pins the bundle filename to
`euv.js` / `euv_bg.wasm` so `www/index.html`'s import path stays stable
across rebuilds. See `references/wasm-pack-out-name-trap.md` for the
30-minute debugging saga if you skip this.

## 3. euv fmt

**Why**: euv's macro-aware formatter (`euv fmt`) expands `html!` /
`class!` / `vars!` / `var!` / `#[component]` invocations and re-indents
their internals. `cargo fmt` does NOT do this — it'll leave macro
internals untouched. A diff with formatter drift in macros blocks merge.

```bash
euv fmt
git status  # should show no diffs (already clean or just normalized)
```

If `euv fmt` changed files you didn't intend, inspect the diff and
commit it as a separate `style:` commit or include it in the same PR
(reviewers prefer the latter for small drift).

## 4. Commit message English-only + no Chinese

**Why**: GitHub artifacts (commit message subject + body, PR title +
body) are public reviewer-facing text. The user's hard rule
(memory + `git-standards` skill): **English only** in anything that
reaches GitHub. Agent-to-user chat is Chinese; GitHub-bound text is
English.

```bash
# Self-check before commit
git log -1 --format=%B | grep -P "[\p{Han}]" && echo "FAIL: Chinese in commit" || echo "PASS"
grep -P "[\p{Han}]" /tmp/pr-body.md && echo "FAIL: Chinese in PR body" || echo "PASS"
```

If either fails, edit and re-stage.

## 5. Track 2 PR base branch + cross-fork head

**Why**: `euv-dev/*` = Track 2 fork+PR (memory rule). Pushing the
branch to `origin` (which is `eastspire/<repo>` fork, not upstream) and
opening `gh pr create --repo euv-dev/<repo> --head
eastspire:<branch>` produces a cross-fork PR (`isCrossRepository:
true`) — verified working on PR #167.

```bash
git remote -v
# origin    ssh://git@github.com/eastspire/euv.git     (your fork)
# upstream  ssh://git@github.com/euv-dev/euv.git       (the PR target)

# Confirm:
#   - branch is checked out from upstream/master
#   - branch pushed to origin
git branch --show-current
git log upstream/master..HEAD --oneline   # your commits only

# Open PR:
gh pr create --repo euv-dev/euv \
  --head eastspire:fix/<topic>-2026-MM-DD \
  --base master \
  --title "fix(example): <what> + <why>" \
  --body-file /tmp/pr-body.md
```

Verify base branch first: `gh repo view euv-dev/euv --json
defaultBranchRef` → should be `master`. `--base master` against a
`main`-default repo silently targets the wrong branch.

## 6. PR body sections

**Why**: Reviewer scan time. Without clear structure, a 300-line diff
takes 4x longer to review. Template (from `git-standards` skill):

```markdown
## Summary
<2-3 sentence what + why>

## Changes
- file1.rs: <what changed and why>
- file2.rs: <what changed and why>

## Verification
- [ ] `cargo clippy -p euv-example --all-targets` is clean
- [ ] `euv build --release` succeeds
- [ ] `euv fmt` accepts the diff unchanged
- [ ] Manual visual check (if UI change): <link or screenshot>
- [ ] Playwright / headless verification (if behavior change)

## Notes
<side effects, version bump policy, breaking changes>
```

For euv specifically: include a "Why not a version bump?" section when
the change is bug-fix-only — reviewers familiar with the project will
otherwise ask.

## 7. `gh pr create --body-file` not `--body`

**Why**: `gh pr create --body "..."` escapes backticks in inline
strings and renders fenced code blocks as plain text. `--body-file`
preserves verbatim.

```bash
cat <<'EOF' > /tmp/pr-body.md
## Summary
...markdown with `code` blocks and ```fenced``` examples...
EOF
gh pr create --body-file /tmp/pr-body.md ...
```

## 8. After push: watch first CI run, don't auto-merge

**Why**: `euv-dev/euv` has a `sync_workspace_version` job that fires
on `push` to `master` (not on PR event). On a fresh PR, that job will
be `skipping` in `gh pr checks N` — that's normal. The job will
actually run after PR merge, syncing all 14 version fields in one
commit. Don't panic at `skipping`; don't `--admin --squash` to bypass.

```bash
# After PR open:
gh pr checks 167 -R euv-dev/euv --watch
# `sync_workspace_version: skipping` is expected
# `Rust: success` / `wasm: success` is what matters

# DO NOT auto-merge:
#   gh pr merge 167 --auto            ← forbidden
#   enablePullRequestAutoMerge        ← forbidden
# Wait for user to say "merge it" or equivalent.
```

## 9. `git status` cleanliness before push

**Why**: A dirty worktree pushed by accident lands stray files in the
PR diff. Common offenders: `__pycache__/`, `*.pyc`, `.DS_Store`,
`target/`, untracked scratch files in `/tmp/`.

```bash
git status
# Expect: only the files you intend
git diff --stat
# Check: nothing in /tmp, nothing generated
```

## 10. Branch from clean `upstream/master`

**Why**: Opening a feature branch from a previous unmerged PR's head
inherits that PR's commits into your new PR's diff (see
`rust-wasm-gh-pages-deploy-pitfalls` 坑 11). Always:

```bash
git fetch upstream
git checkout master
git reset --hard upstream/master    # ensure local master == upstream HEAD
git checkout -b fix/<topic>-2026-MM-DD
# ...work...
git push -u origin fix/<topic>-2026-MM-DD
```

The exception is stacked/dependent PRs, where the body must declare
"depends on #N" explicitly.

---

## Bundle script

For convenience, run all checks in one go:

```bash
export PATH=/root/.cargo/bin:$PATH
cd /root/github/euv-dev/euv
BRANCH=$(git branch --show-current)
echo "=== audit ==="
python3 /root/.hermes/skills/rust-standards/scripts/audit_rust_standards.py \
  /root/github/euv-dev/euv
echo "=== clippy ==="
cargo clippy -p euv-example --all-targets --offline 2>&1 | tail -5
echo "=== fmt ==="
euv fmt
git status --short
echo "=== branch ==="
echo "current: $BRANCH"
git log upstream/master..HEAD --oneline
echo "=== pre-push status ==="
git status --short
```

If any section fails, stop and fix before `git push`.
