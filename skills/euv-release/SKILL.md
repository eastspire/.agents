---
name: euv-release
description: Ship an euv release. Two-PR pattern, CI publish, redeploy.
---

# euv Framework Release Workflow

End-to-end playbook for shipping a new euv release (euv-dev/euv) to crates.io, then rebuilding & redeploying euv-example + euv-docs against the new version.

## Architecture in 30 seconds

- euv is a Cargo workspace with 7 crates sharing one version: `euv` (root), `euv-ui`, `euv-core`, `euv-engine`, `euv-macros`, `euv-cli`, `euv-example`. They all bump together — **but the bump is now CI-managed, not local** (see "The new release model" below).
- The repo's `Rust` workflow auto-publishes to crates.io on push to `master` if CI is green and the package version is newer than crates.io's latest. It also auto-tags a GitHub release.
- `euv-docs` uses `euv = "0.18"` (caret), so any 0.18.x resolves automatically — no Cargo.toml edit needed in euv-docs.
- euv-example lives in the same workspace and uses `euv = { workspace = true }` (path dep), so it picks up new code without a crates.io step.
- The repo's `Deploy Pages` workflow rebuilds euv-example with `cargo run -p euv-cli -- build --release --crate-path ./example -- --target web --out-dir www/pkg --out-name euv --no-typescript --no-pack --no-gitignore` and deploys to **https://euv-dev.github.io/euv/**. The `--out-name euv` override changes the JS file from `euv_example.js` (local default) to `euv.js` (Pages artifact).

## The new release model (supersedes the old "two-PR + sed-seven" pattern)

**As of PR #101 (2026-09-02)**: there is **one PR**, not two. The PR's own commit message lists the new version (e.g. `(0.18.37)`), but only the **root `Cargo.toml` `[package] version`** line is touched in the PR diff. CI's `sync_workspace_version` job (`.github/workflows/rust.yml`, gated `if: github.event_name == 'push' && github.ref_name == 'master'`) automatically propagates the root version to all 6 member-crate `Cargo.toml` files and the root `[workspace.dependencies]` path-dep `version` fields on the post-merge push to master.

**Why one PR (not two)**: the previous "two-PR" pattern had PR B as a pure chore-bump that edited all 7 `version = "..."` lines. After the rule change, that work is CI's. The fix PR's title can just embed the new version (`perf(core): add zero-allocation pre-scan to unwrap_component_owned (0.18.37)`), and reviewers see a 1-file diff for the version bump embedded inside the same PR.

**The rule is loaded into `euv-standards` §17 / `references/version-bump-rule-2026-09-02.md`. Always re-read that file before any euv release — it is the verified source of truth.**

**Why branch from clean master**: a previous session got bitten — if a new PR branches from an unmerged PR's branch, `gh pr diff` includes the prior PR's commits. **Always**: `git checkout master && git pull upstream master && git checkout -b <branch>` BEFORE making any change. See `references/release-pitfalls.md` for the full incident.

## Step-by-step: cut a release

### Step 1 — Pre-flight

```bash
# Verify clean tree on master, remote is up to date
cd ~/github/euv-dev/euv
git status --short                    # expect empty
git fetch upstream --no-tags
git checkout master
git reset --hard upstream/master      # force-sync fork to upstream
git push origin master --no-verify     # keep fork in sync (avoids PR-base confusion)
```

### Step 2 — Decide the version bump

- patch (`X.Y.Z` → `X.Y.Z+1`): bug fixes, CSS token tweaks, internal refactors, no API surface change
- minor (`X.Y` → `X.Y+1.0`): new components, new public API, new theme tokens that users adopt
- major: breaking changes (rare — euv follows semver but hasn't shipped one yet)

User usually says "升级小版本" — in Chinese context this typically means **patch**. Confirm with the user only if ambiguous. See `references/release-pitfalls.md` for the "patch vs minor" clarification.

**Ask-vs-assume rule** (user-corrected 2026-09-02 via PR #106 → #107): when in doubt about whether a PR warrants a bump, **ask the user** rather than assuming. The "bugfix doesn't bump" shorthand is a default heuristic, not a hard rule — the user is the authority. PR #106 (split inline vs fullscreen rendering paths) was a pure bugfix on PR #104's letterbox, but the user explicitly answered "需要" when asked about bumping. Pattern: deliver the bugfix PR first, then ask "升级小版本了吗?" / "需要 bump 吗?" before cutting the chore PR. Do not auto-include a chore bump in a fix PR.

### Step 3 — Apply the bump (root Cargo.toml, ONE line)

```bash
# Bump ONLY root Cargo.toml line 3 [package] version
sed -i 's/^version = "0.X.Y"$/version = "0.X.Z"/' Cargo.toml
```

Sanity check:

```bash
grep -H '^version' Cargo.toml    # root should report new version
grep 'version = "0.X' Cargo.toml # workspace.dependencies entries should NOT yet be new version (CI does it)
```

**Do NOT** sed-replace the member-crate `Cargo.toml` files (`core/`, `ui/`, `engine/`, `cli/`, `macros/`, `example/`) or the `[workspace.dependencies]` path-dep `version = "..."` entries. Those are CI-managed by `sync_workspace_version`. Pre-bumping them locally is the wrong move — see `euv-standards/references/version-bump-rule-2026-09-02.md` for the full incident and user feedback.

**Before PR, double-check the diff is exactly 1 file**:

```bash
git diff --stat
# Should show Cargo.toml | 2 +- (one line changed) and nothing else version-related.
```

### Step 4 — Build-verify locally before committing

```bash
export PATH=/root/.cargo/bin:$PATH
cargo check -p euv-ui --target wasm32-unknown-unknown   # ~25s clean
cargo check -p euv --target wasm32-unknown-unknown
cargo check -p euv-example --target wasm32-unknown-unknown
```

If any of these fail, the Cargo.toml change broke something. Investigate before committing.

### Step 5 — Commit, push, PR, merge

```bash
git checkout -b perf/<short-description>-0.X.Z      # or chore/.../fix/...; whatever fits the change
# LAST commands before commit: run fmt twice (idempotent check)
export PATH=/root/.cargo/bin:$PATH
euv fmt && cargo fmt --all
euv fmt && cargo fmt --all   # second run: zero diff = idempotent
git add Cargo.toml                                 # ONLY root Cargo.toml
git commit -m "<type>(<scope>): <description> (0.X.Z)

<2-3 sentences explaining what the change does and why it deserves a release.>

The root \`[package] version\` in \`Cargo.toml\` is bumped from 0.X.Y to 0.X.Z.
The \`[workspace.dependencies]\` path-dep entries and the sub-crate
\`package.version\` fields are intentionally left at 0.X.Y — CI's
\`sync_workspace_version\` job (\`.github/workflows/rust.yml\`) propagates
the root version to all workspace members on the master merge commit,
so duplicating the bump here would just churn diffs and conflict with
the CI sync."

git push -u origin perf/<branch>-0.X.Z
gh pr create --repo euv-dev/euv --base master \
  --head eastspire:perf/<branch>-0.X.Z \
  --title "<type>(<scope>): <description> (0.X.Z)" \
  --body-file /tmp/pr-body.md
gh pr merge <N> --repo euv-dev/euv --squash --delete-branch --admin
git fetch upstream --no-tags
git checkout master
git reset --hard upstream/master
git push origin master --no-verify
```

**Bump-as-separate-commit 变体 (PR #171/#172/#173 实测, 2026-09-07)**: 当 fix PR 已经 ship 到 euv-dev/master 在一个独立 branch 上、最后一步是"bump + PR + merge"(用户经常这么要求),**不要**把 fix commit 和 version bump 合到同一个 commit. 用两个 commit:
1. fix commit (已经存在)
2. `chore: bump version to X.Y.Z` commit(单文件 +1/-1)
3. push → `gh pr create` → `gh pr checks N --watch` 等 build/check/clippy/tests 4 项 PASS
4. `gh pr merge N --squash --delete-branch --admin`
5. 验证 master HEAD:`git fetch euv-dev master && git log --oneline euv-dev/master -3` 期望 `[你的 squash] chore: sync all package versions to X.Y.Z`(CI 自动追加)

**Merge race condition (PR #172/#173 实测, 2026-09-07)**: `gh pr merge --admin --squash` 偶发会返回 `fatal: Not possible to fast-forward` 而 GitHub 端实际已合并——通常因为用户从另一个客户端(web UI / mobile / 另一个 gh session)提前点了 merge。**不要**重试(会报"Already merged")。直接 `git fetch euv-dev master && gh pr view N --json state` 确认已 MERGED,然后进入 sync 验证步骤。详见 `references/release-pitfalls.md` "P-new-2026-09-07 gh pr merge not-ff race"。

**Tag 验证必须用 euv-dev 不是 origin (PR #172/#173 实测)**: `release` job push tag 到 `euv-dev/euv`,`origin` (eastspire fork) 永远不会有 release tag。验证 tag:
```bash
git ls-remote --tags euv-dev | grep vX.Y.Z  # ✅ 唯一正确的查询
# git ls-remote --tags origin 永远空,不要用
```

**Merge 后 tag 不是立刻可见 — `release` job 在跑 (PR #172/#173)**: master Rust CI 在合并 push 上包含 `sync_workspace_version` (秒级) + `release` (打 tag,1-3 分钟) + `publish` (crates.io)。sync_workspace_version commit 出现后,tag 还没出。要确认 `vX.Y.Z` 真的存在,需要 `gh run watch $(gh run list --branch master --limit 1 --json databaseId | jq '.[0].databaseId') --exit-status` 等 `release: success`。

### Step 6 — Wait for CI sync + publish jobs

```bash
# Wait for the run that includes the new HEAD
RUN_ID=$(gh run list --branch master --limit 1 --json databaseId | python3 -c "import sys,json;print(json.load(sys.stdin)[0]['databaseId'])")
gh run watch "$RUN_ID" --exit-status
```

The `Rust` workflow on a master push runs three jobs that matter for the bump:

1. `sync_workspace_version` — reads root `[package] version`, sed-replaces the 6 member-crate `[package] version` + the 6 `[workspace.dependencies]` path-dep `version = "..."` entries, commits back to master. **This is the job that makes your 1-line PR a full 7-file version sync.** It runs in seconds.
2. `publish` — installs `cargo-release`, publishes **all 7 crates in dependency order** (`euv-macros` first, then `euv-core`, `euv-engine`, `euv-ui`, `euv`, etc.) to crates.io. Skipped if root version is unchanged.
3. `release` — creates a GitHub release tag like `v0.X.Z`. Skipped if root version is unchanged.

Post-merge CI run sanity check:

```bash
gh run view "$RUN_ID" --repo euv-dev/euv --json jobs | python3 -c "
import json, sys
for j in json.load(sys.stdin)['jobs']:
    print(f\"{j['name']:<28} {j['conclusion']}\")"
# Expect: setup ✅, sync_workspace_version ✅, tests ✅, clippy ✅, check ✅, build ✅, publish ✅, release ✅
```

Then verify the post-merge auto-sync actually landed:

```bash
cd /root/github/euv-dev/euv
git fetch upstream --no-tags
git pull --ff-only upstream master
for c in core ui engine cli macros example; do
  printf "%-10s %s\n" "$c" "$(grep -m1 '^version' $c/Cargo.toml)"
done
# ALL must report the new version (CI propagated it)
```

Verify on crates.io:

```bash
curl -s -H 'User-Agent: hermes-check' https://crates.io/api/v1/crates/euv-ui | \
  python3 -c "import sys,json;print('euv-ui max_stable:', json.load(sys.stdin)['crate']['max_stable_version'])"
```

**Note**: crates.io API can take 30-60 seconds to reflect the publish even after CI reports success. Poll with a 30s delay if the API still shows the old version.

### Step 7 — Rebuild euv-example + redeploy

```bash
# Clean the leaked pkg/ dir from any previous build
rm -rf ~/github/euv-dev/euv/example/pkg/

cd ~/github/euv-dev/euv/example
/root/.cargo/bin/euv build
```

⚠️ **Pitfall**: `euv build` (euv-cli 0.13.6) leaves a `pkg/` dir at the example crate root containing the bundle. This dir is **not** gitignored by the root `.gitignore` (which only covers `target/`, `www/`, `node_modules/`). If you `git add -A` from the repo root without thinking, it leaks into your PR. Always `rm -rf example/pkg/` before `git add`. See `references/release-pitfalls.md`.

### Step 8 — Pick the deployment target

**GitHub Pages** (https://euv-dev.github.io/euv/) is the canonical deployment for euv-example. The `Deploy Pages` workflow triggers automatically after `Rust` workflow completes successfully on master. The Pages build is independent of the local build in Step 7 — it runs on a github runner with `--out-name euv` (produces `euv.js`), so the deployed HTML imports `./pkg/euv.js`, not `./pkg/euv_example.js`. No manual Pages deploy needed.

If the Pages workflow was cancelled by `concurrency: cancel-in-progress: true` (because a sibling PR merged close behind), it auto-retries. To check:

```bash
cd ~/github/euv-dev/euv
gh run list --workflow 'Deploy Pages' --branch master --limit 5
curl -sI --compressed https://euv-dev.github.io/euv/ | grep last-modified
```

**ltpp.vip** is a manual upload path used in this session for snapshot deploys. Use `hyperlane-upload` skill:
1. Upload `euv_example_bg.wasm` → save URL
2. Rewrite `euv_example.js` line `new URL('euv_example_bg.wasm', import.meta.url)` to the ltpp URL → upload rewritten JS → save URL
3. Rewrite `index.html` import `./pkg/euv-example.js` (note the dash) to the rewritten JS URL → upload HTML → that's the entry URL
4. ⚠️ **Note the dash vs underscore**: `euv-example` (Cargo.toml package name with dash) becomes `euv_example.js` after wasm-pack. The generated HTML still references the dash form `./pkg/euv-example.js`. This is a longstanding euv-cli quirk — see `references/euv-cli-build-outputs.md`.

### Step 9 — Headless-browser verify

Per the user's persistent "headless not curl" rule, verify in a real browser:

```python
python3 -c "
import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(
            executable_path='/root/LTPP-MINIMAX/chrome-linux/chrome',
            args=['--no-sandbox','--disable-dev-shm-usage'])
        c = await b.new_context(viewport={'width':1280,'height':900}, color_scheme='dark')
        page = await c.new_page()
        await page.goto('https://euv-dev.github.io/euv/#/modal',
                        wait_until='networkidle', timeout=60000)
        await page.wait_for_selector('.c_app_main', timeout=30000)
        await page.wait_for_timeout(2500)
        await page.locator('button').filter(has_text='Open').first.click(force=True)
        await page.wait_for_timeout(1000)
        info = await page.evaluate('''() => ({
            bg_overlay_var: getComputedStyle(document.querySelector('.c_app_root')).getPropertyValue('--bg-overlay').trim(),
            overlay_bg: getComputedStyle(document.querySelector('.c_modal_overlay')).backgroundColor,
        })''')
        print('DARK:', info)
        await page.screenshot(path='/tmp/verify-dark.png', full_page=False)
        await b.close()

asyncio.run(main())
"
```

Repeat for `color_scheme='light'` to confirm both themes work and `--bg-overlay` resolves correctly.

**For visual refinement (alpha, color, contrast) — go further**: computed CSS only shows the *source* value, not the final blended RGB. Use pixel sampling (PIL.Image.getpixel) to measure actual rendered colors at scrim, modal, and page-bg regions, then verify the **luminance ordering** matches your intent (e.g. modal should be darker than scrim for a "depth" effect). See `references/release-pitfalls.md` P3.5 for the full pattern — this is what unblocks "user says it's still wrong" iterations.

## Fork + branch housekeeping

After both PRs merge, your local fork's master is behind upstream's master. Sync it:

```bash
cd ~/github/euv-dev/euv
git fetch upstream --no-tags
git checkout master
git reset --hard upstream/master
git push origin master --no-verify
```

This keeps the fork's default branch pointing at the same SHA as upstream. The fix-branch and chore-branch were already deleted by `gh pr merge --delete-branch`, but verify:

```bash
git branch -a | grep -v 'master\|upstream\|origin'
# should be empty
```

## Don't do this

- **Don't sed-replace version in all 7 Cargo.toml files.** The previous "two-PR + sed seven files" pattern is **wrong as of 2026-09-02**. Only bump root `Cargo.toml` line 3 — CI's `sync_workspace_version` does the rest. Pre-bumping the member crates and `[workspace.dependencies]` path-dep entries makes the diff noisy and conflicts with the auto-sync commit. See `euv-standards/references/version-bump-rule-2026-09-02.md` for the full incident.
- **Don't open a separate `chore(release): bump all crates` PR.** It's no longer needed; the fix PR's title can embed the new version (`(0.18.37)`).
- **Don't push to `euv-dev/euv:master` directly.** All non-personal repos go through fork + PR. eastspire is admin on `euv-dev/euv` but the user explicitly wants the PR trail for review.
- **Don't merge without PR A's cargo fmt + cargo check passing.** A typo in the root `[package] version` can break `[workspace.dependencies]` resolution. Run it.
- **Don't commit without running `euv fmt` + `cargo fmt --all` immediately before the commit.** See P9 in `references/release-pitfalls.md` — running fmt during dev is not the same as running fmt on the actual tree-state being committed. Last commands before `git commit` MUST be `euv fmt && cargo fmt --all`.
- **Don't bump version on a fmt-only / whitespace-only PR.** If the diff is purely formatting with no API change, do NOT include a `Cargo.toml` version bump — it publishes a no-op version to crates.io and consumes 3-4 min of CI `publish` job time. Let PR #103 be the model: 1 file, whitespace, 0 version change.
- **Don't keep working on local master after the PR merges** when you have uncommitted edits from before the worktree switch. See `release-pitfalls.md` P15 — `git stash` → `git reset --hard upstream/master` → `git stash drop`. Don't `git reset --hard` directly (wipes uncommitted work) and don't `git merge --ff-only upstream/master` if local is ahead (aborts; would need non-ff which creates a duplicate history).
- **Don't try to yank a crates.io version from this VM** without first checking for `CARGO_REGISTRY_TOKEN`. The default environment has none. `cargo yank` errors with `no token found`, and the `crates.io/api/v1/crates/<name>/<version>/yank` PUT endpoint returns `403` even with the available `GH_TOKEN`. See `release-pitfalls.md` P14 for the "skip version" workaround when reverting a release without yank access.
- **Don't stay on the feature branch after `gh pr merge`.** Always follow up the merge with `git checkout master && git fetch upstream master --no-tags && git merge --ff-only upstream/master` before answering any user question about "did you push?" / "did CI run?" / "what version?". See P10 in `references/release-pitfalls.md` for the full incident.
- **Don't run `euv build android` on this VM.** Per memory: Tauri Android build has crashed this VM before. Use the user's local box or CI.
- **Don't touch `docs-pages/pages` (the Vercel HTML build artifact).** It's regenerated on next deploy. Source of truth is `docs-pages/docs` markdown.

## Verification matrix

| What | How |
|------|-----|
| PR diff is 1 file (`Cargo.toml` only) | `gh pr diff <N> --stat` on the release PR |
| `cargo check` clean post-bump | `cargo check -p euv -p euv-core -p euv-engine -p euv-ui -p euv-example --target wasm32-unknown-unknown` |
| CI green | `gh run view <master-run-id> --json jobs` → all `conclusion: success` |
| `sync_workspace_version` actually ran | check the run's jobs list includes `sync_workspace_version` with `success` |
| Member crates all show new version post-merge | `git pull --ff-only upstream master && for c in core ui engine cli macros example; do grep -m1 '^version' $c/Cargo.toml; done` — every line must show `0.X.Z` |
| Crates.io reflects new version | `curl -s -H 'User-Agent: hermes-check' https://crates.io/api/v1/crates/euv-ui` → `max_stable_version` = new version |
| Pages deployed | `curl -sI https://euv-dev.github.io/euv/` → `200`, recent `last-modified` |
| Visual verification | Playwright headless screenshot of `#/modal` in both `dark` and `light` |
| CSS token resolves | Playwright evaluates `getComputedStyle(root).getPropertyValue('--bg-overlay')` and matches expected value |

## Pointers

- `references/release-pitfalls.md` — concrete incidents this workflow prevents (commit-amend mid-PR, pkg/ leaking, PR diff contamination, cargo cache staleness)
- `references/euv-cli-build-outputs.md` — what `euv build` actually emits vs what the Pages workflow emits (dash→underscore quirk, file inventory)
- `references/release-checklist.md` — terse checkbox version of this SKILL.md for copy-paste use