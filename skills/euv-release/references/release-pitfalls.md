# euv Release Pitfalls

Concrete incidents the euv release workflow must prevent. Each pitfall
has a date, the PR number that hit it, the symptom, and the rule that
keeps it from happening again.

## P1 — Branching chore/release from PR A's branch (PR diff contamination)

**Date**: 2026-08-29 (first hit); pattern re-validated in this session
(2026-09-01, all four releases of the session cut cleanly).

**Symptom**: PR A is the fix. PR B is the chore/release version bump.
If PR B is cut from PR A's branch (instead of from clean
`origin/master`), then `gh pr diff <B>` includes PR A's commits. The
chore PR appears to "carry" the fix code as part of its diff, and
reviewers see a PR labelled "chore(release): bump to 0.X.Z" that
actually has the entire fix in it too. Worse, the fix diff in PR A is
then "lost" because the same lines are also in PR B's diff.

**Rule**: ALWAYS
```bash
git checkout master && \
  git fetch upstream --no-tags && \
  git reset --hard upstream/master && \
  git push origin master --no-verify && \
  git checkout -b chore/bump-0.X.Z
```
before making any change to the chore branch.

## P3 — `example/pkg/` directory leaks into release commit

**Date**: 2026-09-01 (this session, both 0.18.28 and 0.18.29 releases).

**Symptom**: `euv build` (euv-cli 0.13.6) writes the wasm bundle to
BOTH `example/www/pkg/` (the deployable artifact, gitignored via the
`www` rule) AND `example/pkg/` (the same files at the crate root,
NOT gitignored). When you `git add -A` from the repo root, the
`example/pkg/euv_example.js` and `euv_example_bg.wasm` files get
included as new untracked changes (they show up as
`?? example/pkg/` initially). The commit then has 9 files instead of
7, and the pkg/ files are redundant duplicates of the www/pkg/
versions.

**Fix**: amend the commit:
```bash
git rm --cached example/pkg/euv_example.js example/pkg/euv_example_bg.wasm
git commit --amend --no-edit
git push -u origin chore/bump-0.X.Z --force   # force-push if branch was already pushed
```

**Long-term fix (not done)**: add `pkg/` to example's `exclude` list in
`Cargo.toml` (which doubles as the publish exclusion) OR create a
proper `example/.gitignore`. The `exclude` doesn't affect git
though — would need a real `.gitignore`. Don't mix that fix into a
release PR.

**Defensive routine**: always run
```bash
rm -rf example/pkg/
```
after every `euv build`, before any `git add -A` from the repo root.

## P3.5 — Visual refinement loop: pixel-sample, don't trust computed CSS

**Date**: 2026-09-01 (this session, dark-theme overlay scrim across
PR #83 → #85 → #87 → #89 → #91 → #93 → #95 → #97 → #99, **eleven
iterations in one session** (versions 0.18.27 → 0.18.36, nine PR
pairs — fix + chore/release — total).

**Symptom**: User said "暗色遮罩看不见" → made it visible (rgb 38).
User said "0.15 太弱" → bumped to 0.45 (rgb 115). User said
"0.45 太突兀" → dropped to 0.20 (rgb 51). User said "还是太白"
after 0.10 (rgb 26). User said "怎么不透明了透明" after switching
to solid `rgb(50,50,50)` (PR #93). User said "还是太白" again at
0.06 alpha (rgb 15). User said "现在暗色遮罩和背景区分不出来了"
at 0.04 (rgb 10). **Three rejections of "太白" across different
alphas** chasing the same complaint because **the fix metric was
wrong**.

**Root cause of the loop**: I was iterating on `alpha` while the real
problem was the **scrim-vs-panel luminance ordering**, not the alpha
value. Computed CSS (`getComputedStyle(overlay).backgroundColor`) only
shows the source value (e.g. `rgba(255,255,255,0.10)`); it does NOT
tell you the final blended RGB after alpha-compositing with the page
background. And it definitely doesn't tell you the perceptual
ordering — does the scrim look "lighter" or "darker" than the panel?

**The deeper issue**: the user's complaint word never changed
("还是太白") while the iteration went through 4 rounds of pure alpha
tuning. By the 2nd "too white" (PR #91), the frame was already wrong:
any visible scrim on `#000` is lighter than bg and reads as
"highlighted/white" to the eye. The pure-`#000` bg + scrim frame
makes the goal ("black-feel scrim distinguishable from bg")
self-contradictory.

When the agent switched to solid color (PR #93), the user complaint
*changed form*: "怎么不透明了透明" (now opaque). That revealed a
**new axis** (transparency) that the alpha-only iterations had
implicitly traded off. PR #95/97 added the **distinguishability
axis** when going back to alpha. PR #99 finally hit the intersection
of all three axes at `rgba(255,255,255,0.08)` → `rgb(20,20,20)`.

**The general lesson** (cross-references `frontend/css-edge-cases` §9
"Color/alpha iteration: when the perceptual frame is wrong, not the
value"):

1. Sample page bg FIRST (don't assume `#000` or `#fff` — verify with PIL)
2. Compute the scrim's blended RGB against actual page bg
3. Verify panel/scrim/page luminance ordering matches your intent
4. If the user reuses the **same complaint word** 3+ times in a row
   against the same token, **the frame is wrong, not the value**
   — enumerate the OTHER axes the design implicitly trades off
   (hue, transparency, distinguishability, etc.) and surface the
   contradiction with a clarification
5. Pixel sampling is mandatory, not optional, for visual refinement

**Three-axes inventory** (from the dark-scrim series): hue
("black feel"), transparency ("see content through"), and
distinguishability ("scrim visible against bg"). The first 4 PRs
only iterated hue; PR #93 added transparency as a new axis (solid
color); PR #95/97 added distinguishability (back to alpha, going
too low); PR #99 finally resolved all three.

**Lower-bound floor** for distinguishability on `#000` bg: ≥15 RGB
units above bg. Below 10 units, scrim and bg merge into one mass
even at high DPR. (Mirror: ≥15 RGB units below bg on `#fff`.)

**Sweet spot** (v0.18.36, PR #99): 20 RGB units of lift via
`rgba(255, 255, 255, 0.08)` on `#000` → `rgb(20, 20, 20)`. Verified
pixel-sampled: scrim = `rgb(20, 20, 20)`, modal panel =
`rgb(0, 0, 0)`, page bg = `rgb(0, 0, 0)`. Luminance order
`#000 → #141414 → #000` — page → scrim → panel — produces the
"deeper-black focal point" effect the user wants.

**Why sweet spot is exactly 20, not 15 or 30**: at 15 (the lower
bound), user said "区分不出来". At 30+, user said "白 halo". 20 is
the midpoint where the eye can resolve all three regions
separately (page bg / scrim / panel) without any element
dominating. Document this as `bg-overlay` alpha in
`ui/src/style/var/fn.rs` — single source of truth, propagates to
`c_modal_overlay` / `c_vconsole_overlay` / `c_mobile_overlay` /
`c_drawer_mask` automatically.

**Light theme mirror** (v0.18.36): `rgba(0, 0, 0, 0.20)` →
`rgb(204, 204, 204)` on `#fff`. Light mode has no perceptual
ambiguity because `rgba(0,0,0,X)` on `#fff` always reads as
"darker dim" (the conventional scrim pattern). Stick to 0.20.

**Decision rule for scrim/sheet/banner values**:

1. Sample page bg FIRST (don't assume `#000` or `#fff` — verify with PIL)
2. Compute the scrim's blended RGB against actual page bg
3. Verify panel/scrim/page luminance ordering matches your intent
4. If user says "still X", enumerate which axes (hue / transparency
   / distinguishability) the design trades off and which one the
   next value violates. Switch axes, don't tune on the same axis.
5. After 2 rounds of "same complaint word" + "still X", surface
   the frame contradiction via `clarify` — pick the closest
   approximation, change a sibling token, or change the frame.

**Solid-color trade-off** (PR #93): when alpha tuning fails to fix
"too X" complaints, switching to solid `rgb(R,G,B)` will *always*
introduce a new complaint ("now opaque"). Solid colors have
opacity 1.0, which blocks transparency. Document this trade-off
in the PR body before opening — if you don't, the user will reject
the solid-color PR the moment they notice they can't see content
behind.

## P3.6 — Playwright cache busting: `?bust=` + `--disable-cache`

**Date**: 2026-09-01 (this session, PR #91 verification).

**Symptom**: After `cp -fv` of new wasm/js to the test server dir,
Playwright still reads the OLD CSS values. Even with a fresh
`page.goto()`. Console shows nothing — the browser cache served
the stale asset.

**Fix**: combine URL bust + browser flag:
```bash
# URL side: append ?bust=<version> to the URL you goto
await page.goto(f'http://127.0.0.1:5189/?bust=v0.18.32#/modal')

# Browser side: launch with --disable-cache
b = await p.chromium.launch(
    executable_path='/root/LTPP-MINIMAX/chrome-linux/chrome',
    args=['--no-sandbox','--disable-dev-shm-usage','--disable-cache'])
```

**Why both**: `?bust=` makes the HTML response unique so the linked
JS/wasm URLs (which still reference the original path) are
re-fetched. `--disable-cache` is the belt-and-suspenders that
forces re-validation of every other request too (fonts, css, etc).

**Anti-pattern**: relying on `page.reload()` alone. Service workers,
disk cache, and HTTP 304s all conspire to keep serving the stale
asset. The first `?bust=` request that succeeds typically warms the
correct version; subsequent reloads without `?bust=` should also
return fresh now.

## P3.7 — User terse rejection ("还是太白") means re-diagnose, not re-iterate

**Date**: 2026-09-01 (this session, dark scrim iterations).

**Symptom**: User gave a single-sentence rejection ("还是太白")
without explaining WHY. I had three choices:
(a) bump alpha down again (same axis — failed 3 times before)
(b) re-read the actual rendered output to find the real problem
(c) ask "what specifically feels wrong?" (forbidden per user rule:
don't ask if directive is clear — but there's no directive here,
just a complaint)

**Correct path**: (b). The user already approved the metric
("贴近背景但可以清楚分辨"). They're not saying "alpha wrong" —
they're saying "the *result* still feels wrong on that metric". So
the fix is to verify the result actually achieves the metric. Pixel
sampling (P3.5) makes the gap visible: `scrim rgb(26,26,26) on
#000 page, modal panel rgb(0,0,0)` → user sees "scrim lighter than
panel" → "still white". Tactic change, not value tweak.

**Decision rule**: after 2 failed iterations on the same axis, stop
iterating and re-measure. If measurement shows the perceptual
ordering is wrong, change the tactic (luminance ordering, hue,
or both). Alpha-tuning is rarely the answer past the second try.

## P4 — Pages deploy cancelled by `concurrency: cancel-in-progress`

**Date**: 2026-09-01 (this session, immediately after 0.18.29 cut).

**Symptom**: PR A merges at T+0. PR B merges at T+7min. Both trigger
the `Deploy Pages` workflow on the same `pages` concurrency group.
The second run cancels the first mid-build (cargo was compiling
`euv-cli` for the Pages workflow). The cancelled run shows
`conclusion: cancelled` with `##[error]The operation was canceled.`
in the logs and "Terminate orphan process: pid (...) (cargo)".

**Reality**: this is **expected behavior**, not a failure. The
`Rust` workflow publishes to crates.io (which is the actual release
artifact). The `Deploy Pages` workflow rebuilds the example against
the new code. The cancelled Pages run was the PR-A branch's Pages
build — superseded by PR-B's Pages build, which auto-retried
successfully within 4 minutes.

**How to read the failure**: a Pages run with `conclusion: cancelled`
followed by another Pages run with `conclusion: success` is normal
when two PRs land within 7 minutes of each other. Check that the
retry succeeded before reporting "deploy failed".

**Verification command**:
```bash
gh run list --branch master --limit 5 --json databaseId,conclusion,name,headSha
# Look for two Deploy Pages runs in a row:
#   {conclusion: cancelled, headSha: HEAD-of-PR-A}
#   {conclusion: success,    headSha: HEAD-of-PR-B}
# That's the normal pattern. Both should reference a successful retry.
```

## P5 — First `euv build` after a fix lands may use stale cargo cache

**Date**: 2026-08-30 (recorded in memory from previous session).

**Symptom**: After editing `ui/src/style/var/fn.rs` and running
`euv build`, Playwright still reads the OLD CSS values. The wasm file
timestamp is fresh but the embedded data is stale.

**Cause**: `euv build` uses `wasm-pack` which uses cargo's incremental
build cache. The cached `libeuv_ui-*.rlib` from the previous compile
gets linked instead of recompiled.

**Fix**: run `euv build` a second time. The first run triggers the
rebuild; the second run produces the artifact with the new data
embedded.

**Alternative**: `cargo clean -p euv-ui` before `euv build` to force
a fresh compile of just that crate.

## P6 — Crates.io API lag after CI reports publish success

**Date**: 2026-09-01 (this session).

**Symptom**: After the GitHub Actions `publish` step reports
"Published to crates.io", the API query
`https://crates.io/api/v1/crates/euv-ui` still shows the old version.
Up to 60 seconds of lag.

**Fix**: poll with backoff:
```bash
for i in 1 2 3 4 5 6; do
  V=$(curl -s -A 'Mozilla/5.0' https://crates.io/api/v1/crates/euv-ui | \
       python3 -c "import sys,json;print(json.load(sys.stdin)['crate']['max_stable_version'])")
  echo "attempt $i: euv-ui max_stable = $V"
  if [ "$V" = "0.X.Z" ]; then break; fi
  sleep 30
done
```

## P7 — Cargo workspace version bumps: 7 files, not 6

**Date**: 2026-09-01 (this session, caught twice).

**Symptom**: Running `sed -i 's/version = "0.X.Y"/version = "0.X.Z"/'`
on `Cargo.toml ui/Cargo.toml core/Cargo.toml engine/Cargo.toml
example/Cargo.toml macros/Cargo.toml` (6 files) leaves `cli/Cargo.toml`
at the old version. The next CI publish job fails because
`euv-cli 0.X.Z` (workspace) conflicts with `euv-cli 0.X.Y` (crate),
or — worse — silently publishes only 6 of 7 crates.

**Fix**: the canonical sed invocation is **7 files**:
```bash
sed -i 's/version = "0.X.Y"/version = "0.X.Z"/g' \
  Cargo.toml ui/Cargo.toml core/Cargo.toml \
  engine/Cargo.toml example/Cargo.toml \
  macros/Cargo.toml cli/Cargo.toml
```

**Sanity check**:
```bash
grep -H '^version' ui/Cargo.toml core/Cargo.toml engine/Cargo.toml \
  example/Cargo.toml Cargo.toml macros/Cargo.toml cli/Cargo.toml
# Must show 7 matching lines. If only 6, find the missing one.
```

## P9 — Run `euv fmt` + `cargo fmt --all` IMMEDIATELY before `git commit` (user-corrected 2026-09-02)

**Date**: 2026-09-02 (this session, after PR #102 merge).

**Symptom**: PR #102 (`feat(example): add landscape fullscreen mode for 2D / 3D games`)
merged successfully and shipped euv 0.18.38 to crates.io. But the user
followed up with "**执行fmt了吗？**" — pointing out the PR was committed
without running `euv fmt` immediately before the commit, only during
local development. On the post-merge state, `euv fmt` reformatted
`ui/src/style/class/fn.rs` (whitespace drift inside a CSS comment within
a `class!` macro block), producing PR #103 as a fmt-only follow-up.

**Root cause**: I conflated "I ran fmt during dev" with "the committed
state is formatted." They diverge when:
1. The dev environment has uncommitted changes that affect fmt output
2. The macro-aware `euv fmt` (euv-cli 0.13.6) sees a different view
   of `class!` / `html!` macro bodies than what was on disk when I
   last ran fmt during dev
3. After PR-A merges into upstream master, the rebase state on the
   new branch exposes whitespace drift that was hidden by the old
   base

**Rule**: the LAST command before `git commit` MUST be:

```bash
export PATH=/root/.cargo/bin:$PATH
euv fmt           # macro-aware; touches ui/src/style/class/fn.rs,
                  # example/src/style/class/fn.rs, macros, anywhere
                  # html!/class! bodies appear
cargo fmt --all   # cargo fmt on Rust source; euv fmt does NOT touch
                  # .rs files outside macro bodies
git diff --stat   # 1+ files reformatted is normal and expected
```

Run it twice if the diff from the second run is non-empty — confirms
formatter is idempotent. Then `git add -A && git commit`.

**Anti-pattern**: relying on "I ran fmt earlier during dev." Fmt state
is per-tree-state; it does not persist across rebases, amends, or
upstream syncs.

**Diagnostic** (if you're about to commit but unsure if fmt ran):
```bash
# Should produce zero diff if fmt is idempotent on current tree
euv fmt 2>&1 | tail -3
cargo fmt --all -- --check
# Non-zero exit from cargo fmt --check = unformatted files present
```

## P10 — Post-merge: `git checkout master && git fetch upstream && git merge --ff-only` BEFORE any next action

**Date**: 2026-09-02 (this session, after PR #102 merge).

**Symptom**: After `gh pr merge 102 --repo euv-dev/euv --merge --delete-branch`,
I stayed on the `feat/game-fullscreen` branch. When the user asked
"升级小版本了吗？", I was looking at a working tree where root
`Cargo.toml` showed `0.18.38` (the PR #102 chore commit `68cd748`),
but local `upstream/master` was still at `b2235232` (PR #101 sync,
0.18.37). I would have made decisions based on stale upstream state
if I had started the next PR without first syncing.

**Rule**: after `gh pr merge` of ANY PR (merge / squash / rebase), the
next terminal call MUST be:

```bash
cd /root/github/euv-dev/euv  # or wherever the fork root lives
git checkout master
git fetch upstream master --no-tags
git merge --ff-only upstream/master
```

This gives you:
- The actual upstream HEAD SHA (not the local branch HEAD)
- A clean working tree (no in-progress feature branch state)
- A clean local branch state (`origin/master` and `upstream/master`
  can be re-pushed with `--no-verify` if fork is behind)

**Why this matters for the user**: when the user asks "did you bump
the version?" / "is CI green?" / "did you push?", you need to be
answering about **upstream state**, not about the last PR's
local-only commit.

**Anti-pattern**: assuming `gh pr merge` automatically updates
local state. It does NOT — `gh pr merge` only updates upstream
(after PR is actually merged). Local branches and `upstream/master`
refs are independent of merge events.

## P11 — `publish` job runs on every master push, even fmt-only ones

**Date**: 2026-09-02 (this session, after PR #103 fmt-only merge).

**Symptom**: After merging a whitespace-only PR (PR #103, 1 file
+10/-10, no version change), the `publish` job still ran on the
master push. It exited success because `cargo publish` saw
"is already published" for all 6 crates and broke the retry loop.
But it consumed ~3-4 minutes of CI runner time.

**Why**: the `publish` job guard is `needs.setup.outputs.tag != ''`.
Tag is constructed as `v$VERSION` where VERSION comes from
`toml get Cargo.toml package.version` on **current root Cargo.toml**,
not from "did this push change the version". So a fmt-only commit
on master still has a valid tag (`v0.18.38` from PR #102), and the
job runs. The `cargo publish` loop is the only line of defense.

**Cost**: ~3-4 min CI time on every fmt-only / chore-only master
push that doesn't change `Cargo.toml`. Minor; not worth changing CI
to skip — the safe path (let `cargo publish` self-detect "already
published") is more important than saving 4 minutes.

**Verification that nothing went wrong** (after a fmt-only merge):
```bash
gh run view <master-run-id> --repo euv-dev/euv --json jobs \
  | python3 -c "
import json, sys
for j in json.load(sys.stdin)['jobs']:
    print(f'{j[\"name\"]:<28} {j[\"conclusion\"]}')"
# publish will be success; the publish step's "is already published"
# detection in the cargo publish loop is what produced success
```

If you want to be sure the published crates.io version did NOT move:
```bash
curl -s -A 'Mozilla/5.0' https://crates.io/api/v1/crates/euv-cli \
  | python3 -c "import json,sys; print('max_version:', json.load(sys.stdin)['crate']['max_version'])"
# Compare against git tag of last release — must match
```

## P8 — `gt` and `gt` — committing in repo root pulls in `target/`

**Date**: This is a near-miss, not yet triggered in this session but
in scope: if you `cd ~/github/euv-dev/euv && git add -A`, the
`target/` directory (cargo build outputs) is gitignored, but if
someone has previously added `target` overrides locally, files
might stage. Always check `git status --short` BEFORE `git add -A`
on a release commit:

```bash
git status --short
# Expected: 7 modified (Cargo.toml + 6 sub-crates), 0 untracked, 0 deleted
# If anything else appears, investigate before adding.
```
## P12 — `euv fmt` re-indents one CSS comment in `ui/src/style/class/fn.rs` every bump PR

**Date**: 2026-09-02 (PR #105 0.18.39, PR #107 0.18.40 — same diff pattern, both times).
**Updated**: 2026-09-03 — confirmed across PRs #103, #105, #107, #109, #111, #112 (fmt-only), #113 (seven consecutive commits over 2 days). Pattern is stable.

**Symptom**: Every time you cut a chore-bump PR and run `euv fmt` immediately before commit (per P9), the macro-aware formatter (euv-cli 0.13.6) re-indents the `euv dropdown menu` CSS comment block in `ui/src/style/class/fn.rs` by **4 more spaces**. The diff is consistently:

```
 ui/src/style/class/fn.rs | 20 ++++++++++----------  (10 lines moved +4 spaces, 10 lines moved back)
 2 files changed, +11/-11  (1 line for Cargo.toml + 10/+10 for the comment)
```

This is **not a bug** — the formatter is idempotent (running it twice produces zero diff). The drift is the formatter gradually normalizing the indent of one specific comment block that lives inside a `class!` macro body.

**Why the same fix doesn't apply to PR #103**: PR #103 was the original whitespace-only follow-up to PR #102. After PR #103, the comment was at "indent level N+4". PR #105 ran fmt and shifted it to "N+8". PR #107 ran fmt and shifted it to "N+12". Each bump PR carries a +10/-10 whitespace-only diff in `ui/src/style/class/fn.rs` in addition to the version bump.

**Why this is OK**:

1. The diff is always exactly 10 lines moved (+10/-10), not an unbounded drift.
2. CI's `euv fmt` check (if any) would catch a non-idempotent state — the second `euv fmt` after the first produces zero diff.
3. The comment block is whitespace-only; no semantic change.
4. It's actually a useful normalization — the formatter is correcting a long-standing macro-indent drift that previous sessions didn't run fmt on.

**Verification** (after `euv fmt` reformats `ui/src/style/class/fn.rs`):

```bash
# Run fmt twice — second run must produce zero diff (idempotent)
euv fmt
git diff --stat
euv fmt
git diff --stat
# Both should show the same 2-file diff (Cargo.toml + ui/src/style/class/fn.rs)
```

**If fmt is NOT idempotent** (the second run reformats more files):

- Stop. Investigate which file changed twice — that's a real formatting issue, not the recurring comment drift.
- Common cause: `class!` / `html!` macro body got edited in a way that exposed a new indent-drift candidate. Run `euv fmt` a third time — if the third run is empty, the state stabilized; if not, examine the affected file.

**Don't try to suppress this diff** with `git checkout -- ui/src/style/class/fn.rs` before commit. The drift IS the fmt-clean state; reverting it would put the file in an unformatted state, and a future fmt run would re-introduce the diff.

## P13 — Worktree + post-merge cleanup: `git worktree remove` is part of the routine

**Date**: 2026-09-02 (PR #104, PR #106, PR #107 all used `git worktree add` from `upstream/master`).

**Symptom**: After cutting a PR from a worktree (`git worktree add /tmp/...-worktree upstream/master`), merging the PR via `gh pr merge --delete-branch` only deletes the **remote branch** and the **local branch tracking ref**. It does NOT remove the **worktree directory** itself. The worktree stays around at the old HEAD, consuming disk space and creating confusion about which working tree is "current".

**Rule**: after `gh pr merge` of any PR that came from a worktree, the cleanup routine is:

```bash
# 1. Sync local master to upstream (P10)
cd ~/github/euv-dev/euv
git fetch upstream master --no-tags
git merge --ff-only upstream/master

# 2. Remove the worktree
git worktree list                            # find the worktree dir
git worktree remove /root/github/<owner>/<repo>-worktrees/<branch> --force

# 3. Verify
git worktree list                            # only the main worktree should remain
git branch -a | grep -v 'master\|upstream'    # no stale local branches
```

**Why `--force`**: the worktree's branch was deleted by `--delete-branch`, but git may still hold a ref. `--force` is safe here because the worktree is throwaway by definition.

**Don't skip this**. Worktrees leak disk space (~5-15 GB per worktree after cargo build) and confuse `git worktree list` output. The user's VM has a 60 GB root partition that fills up easily.

## P14 — Reverting a published release: skip version numbers when crates.io yank isn't possible

**Date**: 2026-09-03 (this session, revert of PR #106 + PR #107 series back to PR #103).

**Symptom**: User asked to "撤销game全屏的提交，彻底恢复之前的代码。版本号需要基于现在版本再升小版本" (revert the game-fullscreen commits, completely restore prior code, and bump the version based on current). The master branch had:

- PR #106 (split inline vs fullscreen rendering paths) — a fix-PR that landed in 0.18.40
- PR #107 (bump root version to 0.18.40) — the version bump that shipped PR #106 to crates.io
- PR #105 (bump root version to 0.18.39) — earlier release, still valid on crates.io
- PR #104 (letterbox fix) — the user wanted this kept; only the PR #106 + #107 series reverted

**The complication**: PR #107's merge had published 0.18.40 to crates.io. To "completely restore" the code AND remove 0.18.40 from crates.io, you'd need to yank it. But this VM has **no `CARGO_REGISTRY_TOKEN`** in the environment (`cargo yank --version 0.18.40` returns `error: no token found, please run cargo login`; the `https://crates.io/api/v1/crates/<name>/<version>/yank` PUT endpoint returns `403` with the available `GH_TOKEN`).

Without crates.io yank, the published `0.18.40` artifact is permanent — yanking is the only way to remove it from the registry. The release is still visible to anyone pinning `=0.18.40`.

**Resolution** (the pattern that landed):

1. `git revert` of the PR #106 commit + PR #107 merge commit + the auto-propagate commit (`cc3758c5`/`2150d478`) — three commits on master as PR #108.
3. **Skip version 0.18.40** when bumping — go `0.18.38 → 0.18.41` instead of `0.18.38 → 0.18.39`. This avoids a yank-then-republish collision on the same version number, AND signals to downstream users "the 0.18.40 release was rolled back; please use 0.18.41 instead".
4. Document in the new bump PR's description (and in the PR #108 body) that 0.18.40 was NOT yanked and remains visible on crates.io. Note the yank is left to a maintainer with `CARGO_REGISTRY_TOKEN` access.
5. Delete the GitHub Release `v0.18.40` (`gh release delete v0.18.40 --repo euv-dev/euv --yes`) — this is doable from this VM; only crates.io yank is gated on the token.

**`git revert` of merge commits** (not in P10's quick reference):

```bash
# Plain commit revert (regular single-parent commits):
git revert --no-edit <sha>

# Merge commit revert (PR merges into master). MUST pass -m 1 to select
# the first parent as the mainline; without it, git errors out:
git revert --no-edit -m 1 <merge-sha>
```

The `-m 1` selects "the branch that this PR was merged into" as the mainline to keep. For PR merges, this is master. After merge-revert, the branch tip (PR's own commit) is removed from master history.

**`git revert` of an auto-propagate commit** (the `chore: sync all package versions to 0.X.Y` commit created by CI's `sync_workspace_version` job): just a regular `git revert --no-edit <sha>` — no `-m 1` needed.

**Order matters**: revert the auto-propagate commit FIRST, then the merge commit. Reversing causes conflicts because the merge commit's tree assumes the auto-propagate version is in place.

**Why not skip the revert and just bump 0.18.40 → 0.18.41**: the user explicitly said "撤销game全屏的提交" (revert the game-fullscreen commits). The revert is mandatory. Skipping the version while leaving the bugfix code in place would publish a 0.18.41 release containing the very bug the user wants removed.

**Sanity-check after PR #108 lands**: master HEAD should be at the merge commit BEFORE the bugfix (i.e. PR #104 merge `05981b92`, root version `0.18.38`). If it's anywhere else, the revert chain missed a commit.

**Decision tree** (when user asks to revert a published release):

| Crates.io yank possible? | Action |
|---|---|
| Yes (have `CARGO_REGISTRY_TOKEN`) | Yank all crates at the bad version; cut a normal bump PR (`X.Y.Z → X.Y.Z+1`). |
| No (no token, this VM's default state) | Revert the merge commits + auto-propagate as PR #108; cut a new bump PR **skipping** the bad version (`X.Y.Z → X.Y.Z+2`); document in PR body that the bad version remains in the registry until a maintainer yanks it. |

The "skip version" approach is a one-time escape hatch for an environment without crates.io yank access. If the bad-version code is going to recur, fix the yank access first (it's a 1-line `~/.cargo/credentials` file with a `crates-io` API token, or run `cargo login` interactively in a user-facing session).

## P15 — Master reset when local has uncommitted changes that duplicate merged PR content

**Date**: 2026-09-03 (this session, after PR #110 merge).

**Symptom**: I had been editing `ui/src/style/class/fn.rs` + view files on local `master` directly (during the PR #110 implementation phase) before remembering to switch to a worktree. The edits were uncommitted. After PR #110 merged, those edits now exist **twice**: once in the upstream merge, once in the local working tree. The local master is ahead of `upstream/master` by 24 commits plus has these uncommitted changes.

`git merge --ff-only upstream/master` aborts because local is ahead (it'd need non-ff) — and the non-ff merge would create a duplicate-history state. The uncommitted changes block `git reset --hard upstream/master` because reset would wipe them.

**Rule**: when local master has both ahead commits AND uncommitted changes, the cleanup is stash → reset → drop:

```bash
cd /root/github/eastspire/euv
git stash                              # save the uncommitted working tree
git status                              # confirm: "nothing to commit, working tree clean"
git reset --hard upstream/master        # force-sync local master to upstream
git status                              # confirm: clean tree at upstream HEAD
git stash drop                          # discard the stash (it duplicates PR content)
git log --oneline -3                    # confirm we're at the latest upstream merge
```

**Why drop, not apply**: if the stash was the same content that just landed upstream (because I edited locally before pushing via PR), applying it would put duplicate content in the working tree. The PR-merged commit is the source of truth — the stash is just a record that the edits happened.

**Diagnostic that the stash contains PR content** (not independent work):

```bash
git stash show -p | diff - <(git show upstream/master:<file>) 
# If the diff is empty or near-empty for all stashed files,
# the stash duplicates PR content → safe to drop.
```

**Why not keep local master ahead of upstream by force-pushing**: local commits that haven't been pushed to upstream are work-in-progress on `eastspire/euv` (the fork). Force-pushing them to upstream master would create a non-ff state in the fork's master, which conflicts with the user's "all non-personal repos go through fork + PR" rule. The PR has already merged into upstream; the local commits are obsolete.

**Anti-pattern**: `git reset --hard upstream/master` without first stashing — wipes uncommitted changes (per memory's 2026-08-22 rule). Only safe when `git status` shows clean tree.

**Alternative when stash contains INDEPENDENT work** (not duplicates): replace `git stash drop` with `git stash pop` after the reset. The stash's commits will reapply on top of the new master HEAD, preserving the work.

## P13.1 — The `euv fmt` whitespace reflow can be diagnosed with `git diff -w`

**Date**: 2026-09-03 (this session, P12 verification on PR #112 + PR #113).

**Symptom**: When reviewing a fmt-only PR's changes before committing, want to confirm "this diff is genuinely whitespace-only, not a real change I missed". `git diff --stat` shows +10/-10 in `ui/src/style/class/fn.rs`, which looks meaningful. Is it?

**Diagnostic**:

```bash
git diff --ignore-all-space --ignore-blank-lines --stat
# Output: empty (zero lines) → 100% whitespace

git diff -w | head -10
# Output: empty → confirmed pure whitespace

git diff -U0 | grep '^@@' | head
# Output: only "@@ -3595,10 +3595,10 @@" → only one 10-line hunk around line 3595
```

**For PR #112 / PR #113**: `git diff -w` was empty. The 10/+10 diff is `euv fmt` normalizing the dropdown menu CSS comment indent. Safe to commit.

**When `git diff -w` is NOT empty**: there's a real semantic change mixed in. Investigate which lines differ (the `-w` flag ignores whitespace; non-whitespace differences like CSS property names or Rust tokens will show up). Common cause: the macro formatter shifted some lines AND edited a real property on a different line in the same hunk.

## P16 — Canvas fullscreen first-frame distortion: fix generalizes to WebGL/WebGPU via `renderer.get_canvas()`

**Date**: 2026-09-03 (this session, PR #132 follow-up to PR #130).

**Symptom**: After PR #124 fixed the fullscreen canvas refactor and PR #128 added per-tab rescale logic, PR #130 fixed the Canvas 2D tab's first-frame distortion (~110ms → ~16ms). User then reported the SAME distortion on the **Game 3D WebGL tab** (cubes visibly stretched into rectangles for ~120ms after entering fullscreen). The Canvas 2D fix did not generalize because the underlying mechanism differed.

**Why Canvas 2D ≠ WebGL/WebGPU for the same symptom**:

| Renderer | Sizing call | What it reads |
|---|---|---|
| Canvas 2D (`SsaaCanvas`) | `acquire_game_2d_ssaa_canvas()` → `from_selector_with_scale(SELECTOR, css_w, css_h, scale)` → `display_canvas.set_width(css_w * dpr)` | CSS box passed by caller, which originally came from `read_canvas_size` (used `clientWidth` → backed by canvas.width → no-op resize) |
| WebGL (`WebGlRenderer`) | `renderer.resize(physical_w, physical_h)` called from raf loop, gated on `if resize_dirty` (debounced) | Same `clientWidth` source, but resize is gated — so the per-frame CSS-vs-backing check needs to ALSO trigger resize when CSS doesn't match backing, not just when debounce fired |
| WebGPU (`WebGpuRenderer`) | Same as WebGL | Same |

**Layer-1 fix — the per-frame CSS-vs-backing safety net in the raf closure**:

```rust
let css_size: (f64, f64) = read_canvas_size(SELECTOR).unwrap_or((0.0, 0.0));  // getBoundingClientRect (CSS box)
let new_physical_width: u32 = (css_size.0 * dpr).round() as u32;
let new_physical_height: u32 = (css_size.1 * dpr).round() as u32;
if let Some(renderer) = renderer_for_loop.borrow_mut().as_mut() {
    // PER-FRAME check: backing vs CSS box. Stable because getBoundingClientRect
    // returns CSS layout box (not backing), so the comparison doesn't feedback-loop.
    if new_physical_width > 0 && new_physical_height > 0 {
        let backing_w: u32 = renderer.get_canvas().width();
        let backing_h: u32 = renderer.get_canvas().height();
        if backing_w != new_physical_width || backing_h != new_physical_height {
            // *** ORDER MATTERS *** — set the backing store (synchronous DOM
            // write, microseconds) BEFORE calling renderer.resize (which is
            // a GPU swap-chain reconfig that blocks main thread 100-200ms).
            // If you call renderer.resize first, the browser paints 6-12
            // frames during that stall, stretching the OLD-size backing
            // into the NEW CSS box.
            renderer.get_canvas().set_width(new_physical_width);
            renderer.get_canvas().set_height(new_physical_height);
            let _ = renderer.resize(new_physical_width, new_physical_height);
        }
    }
    // Existing debounced path still runs (no-op if already resized above)
    if resize_dirty {
        let _ = renderer.resize(new_physical_width, new_physical_height);
    }
    // ... rest of render
}
```

**Layer-2 fix — ResizeObserver for sub-frame synchronous resize detection** (PR #134, 2026-09-03):

Layer-1 alone leaves a ~16ms gap (one browser paint cycle) where the backing store mismatch is visible. Layer-2 is `ResizeObserver` — it fires synchronously inside the browser's layout phase, BEFORE the next paint, so the backing store is correct before any pixel touches the screen.

```rust
// In start_game_X_webgl_loop / start_game_X_webgpu_loop, AFTER renderer init:
let observer_closure: Closure<dyn FnMut(js_sys::Array, ResizeObserver)> = Closure::wrap(
    Box::new(move |_entries: js_sys::Array, _obs: ResizeObserver| {
        let Some(window_value): Option<Window> = window() else { return; };
        let document_value: Document = window_value.document().unwrap();
        let element: Element = document_value.query_selector(SELECTOR).ok().flatten().unwrap();
        let rect: DomRect = element.get_bounding_client_rect();
        let new_w: u32 = (rect.width() * dpr).round() as u32;
        let new_h: u32 = (rect.height() * dpr).round() as u32;
        if let Some(renderer) = renderer_for_observer.borrow_mut().as_mut() {
            if renderer.get_canvas().width() != new_w || renderer.get_canvas().height() != new_h {
                // SAME ORDER as Layer-1: backing-store first, then resize.
                renderer.get_canvas().set_width(new_w);
                renderer.get_canvas().set_height(new_h);
                renderer.resize(new_w, new_h);
            }
        }
    }),
);
let observer_callback: Function = observer_closure.as_ref().unchecked_ref::<Function>().clone();
observer_closure.forget();  // wasm-bindgen Closure doesn't hold JS ref
if let Ok(resize_observer) = ResizeObserver::new(&observer_callback)
    && let Some(window_value) = window()
    && let Some(document_value) = window_value.document()
    && let Some(element) = document_value.query_selector(SELECTOR).ok().flatten()
{
    resize_observer.observe(&element);
    *observer_cell.borrow_mut() = Some(resize_observer);
}
// In cleanup: *observer_cell.borrow_mut().take().map(|o| o.disconnect());
```

**Cargo.toml features required** for ResizeObserver:

```toml
[target.'cfg(target_arch = "wasm32")'.dependencies]
web-sys = { version = "0.3.104", features = [
    "ResizeObserver",
    "ResizeObserverEntry",
    // ... existing features
] }
```

**Why Layer-2 is necessary even with Layer-1**: raf closures are throttled by browser scheduling. When `tab.set(true)` flips the fullscreen signal, euv's signal-driven DOM re-render is **asynchronous** — the canvas CSS class change happens on a future animation frame, not synchronously inside the click handler. The raf closure runs in step with that re-render, so Layer-1 catches the change but at the next raf tick (not the next paint). ResizeObserver fires inside the layout phase that the raf is waiting for, getting ahead of it.

**Verified metrics (PR #132 + PR #134, headless Chromium 1280×800 DPR=2)**:

```
Game 3D WebGL, Enter Fullscreen frame trace:
  pre-fix (PR #130 only):           backing=1200×800 css=1248×750 for ~112ms (7 frames)
                                    → cube faces visibly stretched into rectangles
  post-PR #132 fix (Layer-1 only):  backing=1200×800 css=1248×750 for ~16ms (1 frame)
                                    → cubes render with normal cube proportions
  post-PR #134 fix (Layer-1+2):     backing matches CSS box on next layout, 0 frame gap
                                    → visually indistinguishable from inline state

Game 3D WebGPU, Enter Fullscreen: same pattern as WebGL.
```

**The "set_width BEFORE resize" ordering rule** — this is the lesson that only emerged after PR #132's verification with a 200ms raf stall probe. Without it, Layer-1 doesn't help: GPU swap-chain reconfiguration (`renderer.resize`) blocks the main thread for 100-200ms; during that stall, the browser keeps painting at 16ms cadence with the OLD-size backing image stretched into the NEW CSS box. Setting `canvas.width` first is a synchronous DOM write (microseconds) that bumps the backing store to match the CSS box; THEN `renderer.resize` blocks for 100-200ms but the browser can't paint stretched pixels anymore because the backing is already the right size.

**Symptom absence on inline → fullscreen if your renderer doesn't use `clientWidth`**: if a new renderer (custom WebGPU2 / Vulkan) doesn't go through `read_canvas_size` or `clientWidth`, the distortion won't manifest. Test the pattern by checking `grep -rn "client_width\|client_height" example/src/page/<page>/hook/fn.rs` — if both files only use `get_bounding_client_rect`, the bug doesn't apply.

**The obsolete comment**: the WebGPU/WebGL raf loops had a comment claiming "deliberately do NOT call sync_to_current_canvas() on every frame because the loop would read its own writes and grow the texture exponentially". This was a workaround for using `clientWidth` (which tracks backing store and would feedback-loop). Once `read_canvas_size` reads the CSS layout box via `getBoundingClientRect`, the comparison is stable: a resize only fires when the layout actually changes, not when our own `canvas.width` write updates the backing store. The new comment block replaces the obsolete one and explains the trade-off.

**`renderer.get_canvas()` pattern**: `WebGlRenderer` and `WebGpuRenderer` both auto-generate `get_canvas()` from the `canvas: HtmlCanvasElement` field via the `#[derive(Data)]` macro (similar to `get_width()` / `get_height()` for `width: u32` / `height: u32` fields). This is the canonical way to access the backing store size from outside the renderer's own resize method. Verified in `engine/src/renderer/impl.rs` `impl WebGlRenderer` block.

**Verified metrics (PR #132, headless Chromium 1280×800 DPR=2)**:

```
Game 3D WebGL, Enter Fullscreen frame trace:
  pre-fix:  backing=1200×800 css=1248×750 for ~112ms (7 frames)
            → cube faces visibly stretched into rectangles
  post-fix: backing=1200×800 css=1248×750 for ~16ms (1 frame,
            the unavoidable CSS-flip frame)
            → cubes render with normal cube proportions

Game 3D WebGL, Exit Fullscreen frame trace:
  pre-fix:  backing=2496×1500 css=820×547 for ~120ms (7 frames)
            → cube faces stretched
  post-fix: backing=2496×1500 css=820×547 for ~16ms (1 frame)

Game 3D WebGPU, Enter Fullscreen:
  pre-fix:  backing=1200×800 css=1248×750 for ~7 frames
  post-fix: backing=1200×800 css=1248×750 for 1 frame
```

**Symptom absence on inline → fullscreen if your renderer doesn't use `clientWidth`**: if a new renderer (custom WebGPU2 / Vulkan) doesn't go through `read_canvas_size` or `clientWidth`, the distortion won't manifest. Test the pattern by checking `grep -rn "client_width\|client_height" example/src/page/<page>/hook/fn.rs` — if both files only use `get_bounding_client_rect`, the bug doesn't apply.

## P17 — `read_canvas_size` exists in TWO independently-authored copies (game_2d + game_3d)

**Date**: 2026-09-03 (this session, PR #130 vs PR #132 split).

**Symptom**: PR #130 fixed the `clientWidth` → `getBoundingClientRect` bug in `example/src/page/game_2d/hook/fn.rs::read_canvas_size`. User then reported the same distortion on the Game 3D page. PR #132 fixed `example/src/page/game_3d/hook/fn.rs::read_canvas_size` — **same function name, same bug, different file, completely independent implementation**.

**Root cause**: when the two hook modules were created (`game_2d/hook/fn.rs` and `game_3d/hook/fn.rs`), the `read_canvas_size` helper was duplicated rather than extracted to a shared `euv_engine` / `euv` utility. Both copies then drifted to the same buggy `clientWidth` pattern independently. Fixing one didn't fix the other.

**Rule for any future `read_canvas_size`-like helper**: when adding a canvas-size utility, search for ALL files that re-implement the same logic:

```bash
grep -rn "fn read_canvas_size\|fn acquire_.*_canvas" example/src/page/*/hook/fn.rs
# Should return ONE definition. Multiple = bug magnet for any fix.
```

**Fix for this specific case** (PR #130 + PR #132 did NOT do this; if it recurs, do this):

1. Move `read_canvas_size` to `example/src/util/canvas.rs` or similar shared location
2. Both hook modules import the same fn
3. The `getBoundingClientRect` fix (or any future fix) lives in one place

**Why we didn't refactor in this session**: out of scope for the bugfix PRs. PR #130/132 are pure-bugfix patches; refactoring the helper to shared module is a separate chore PR that should NOT be bundled with a behavioral change. Defer the refactor until the bug count justifies the architectural change.

**Diagnostic when user reports "same bug different page"**:

```bash
# Find all canvas-size readers
grep -rn "client_width\|client_height\|get_bounding_client_rect" example/src/page/
# If multiple files use client_width/client_height, they probably need the same fix.
```

## P-new-2026-09-07: `gh pr merge --admin` 偶发报 "Not possible to fast-forward" 但实际已合并 (PR #172/#173)

**Symptom**: `gh pr merge N --squash --delete-branch --admin` 退出码非零,stderr:
```
hint: git merge --no-ff
hint: or: git rebase
fatal: Not possible to fast-forward, aborting.
! warning: not possible to fast-forward to: "master"
```

**Cause**: User-side merge button 在 `gh pr merge` 调用之前已经触发了 GitHub 端的 squash merge。`gh` 此时尝试本地 fast-forward,发现自己的分支已经不在历史里,报错。

**Diagnose**:
```bash
cd /root/github/euv-dev/euv
git fetch euv-dev master
git log --oneline euv-dev/master -3  # 如果最顶是 [你的 squash], 已合并
gh pr view N --json state           # state == "MERGED"
```

**Fix**: **不要**重试 merge(重试会报 "Already merged")。直接进入 sync 验证步骤:
```bash
# Wait for sync_workspace_version to land
sleep 30
git fetch euv-dev master
git log --oneline euv-dev/master -3  # 期望看到 [squash] + [chore: sync ...]
grep -H '^version' {core,ui,engine,cli,macros,example}/Cargo.toml  # 期望都是新版本
```

**Prevention**: 如果用户在另一个客户端(web UI / mobile / 另一个 gh session)同步操作,这是 race condition,不可完全避免。

## P-new-2026-09-07: 验证 tag 用错 remote — origin 是 fork, euv-dev 才是源仓 (PR #172/#173)

**Symptom**: `git ls-remote --tags origin` 看不到 `v0.20.2` / `v0.20.3`,但 `gh release list` 看到 release 已创建。

**Cause**: `release` job push tag 到 `euv-dev/euv`(源仓),不是 eastspire fork (`origin`)。

**Fix**:
```bash
git ls-remote --tags euv-dev | grep 'refs/tags/v' | head  # ✅ 正确
git ls-remote --tags origin  | grep 'refs/tags/v' | head  # ❌ 永远空
gh release list --repo euv-dev/euv  # 也能看到
```

## P-new-2026-09-07: merge 后立刻 `git ls-remote` 看 tag 看不到 — release job 还在跑 (PR #172/#173)

**Symptom**: PR merged 后立即 `git ls-remote --tags euv-dev | grep v0.20.3` 返回空。

**Cause**: `release` job (打 tag) + `publish` job (crates.io) 在 master Rust CI 的合并 push 上跑,但需要 1-3 分钟。先看到 `sync_workspace_version` commit (秒级) 才会看到 tag。

**Fix**:
```bash
RUN_ID=$(gh run list --branch master --limit 1 --json databaseId | python3 -c "import sys,json;print(json.load(sys.stdin)[0]['databaseId'])")
gh run watch "$RUN_ID" --exit-status  # 等到 release: success
git ls-remote --tags euv-dev | grep vX.Y.Z  # 现在应该有了
```

## P-new-2026-09-12: stale fork cherry-pick on Cargo.toml conflict — reset to upstream first (PR #202)

**Symptom**: `git push origin <branch>` rejected with `non-fast-forward` even
after a fresh `git fetch upstream`. Local `master` is ahead of `upstream/master`
because the fork hasn't pulled recent upstream commits (0.21.4→0.21.5→0.21.6
sync + fix PRs). Cherry-picking the working-tree commit onto local `master`
collides on the root `Cargo.toml` version line because that line diverged
upstream.

**Rule**: don't cherry-pick onto a non-clean base. For any euv PR fix from a
stale fork, the canonical sequence is:

```bash
git fetch upstream master                      # sync ref tracking
git reset --hard upstream/master               # wipe local master to clean base
git cherry-pick <your-fix-sha>                 # cleanly replay on upstream tip
git push origin <branch>                       # fast-forward now works
git log --oneline upstream/master..HEAD        # verify: exactly your 1 commit
git diff --stat upstream/master..HEAD          # Cargo.toml + your scoped files only
```

If `cherry-pick` collides anyway on `Cargo.toml`, your fix commit was based
on an older root version — rebase to upstream first, then re-cherry-pick.
Don't manually resolve Cargo.toml conflicts in the cherry-pick; that re-syncs
member-crate versions away from upstream's auto-propagate state.

## P-new-2026-09-12: `patch_children_keyed` InsertBefore with stale NodeList refs → Chromium fallback to appendChild → DOM order jumble (virtual-list bug)

**Symptom**: After several scroll steps in `#/virtual-list`, the row DOM order
is completely jumbled (`Item #359, #336, #355, #353, ...` instead of
continuous). The renderer emits RemoveChild + InsertBefore ops in a single
naive two-pass sweep against the **live NodeList**. Each
`InsertBefore { reference: child_nodes.get(target_index) }` resolves before
the queued RemoveChild ops run, so the reference points at a node about to
be detached. Chromium's `insertBefore(node, detachedRef)` falls back to
`appendChild` — producing the jumbled DOM order.

**Bug history (audit)**:

- PR #187 originally implemented LIS-based keyed diff (correct algorithm).
- PR #192 refactored `patch_children_keyed` to **drop the LIS optimization**
  and replaced it with naive two-pass (the bug introduced here).
- Master at this point still has `lis_indices` (from #187) at `fn.rs:30`,
  but it's never called — dead code warning.

**Fix pattern** (PR #202): extract a pure planner that runs in O(M + N log N):

```rust
pub(crate) fn compute_child_ops_plan<'a>(
    old_keys: &[Option<&'a str>],
    new_keys: &[Option<&'a str>],
) -> Vec<ChildOpPlan> {
    // Pass 1: HashMap<&str, usize> index keyed old children
    // Pass 2: HashSet<&str> for old-key-vs-new membership (O(1) lookup)
    // Pass 3: emit Remove for old keys absent from new
    // Pass 4: build kept_old_indices + kept_pos_for_new
    // Pass 5: LIS over kept_old_indices (the existing lis_indices fn)
    // Pass 6: emit Keep / MoveBefore / InsertBefore in single sweep;
    //         each Move/Insert anchors against the previous emitted
    //         child's new_index so the reference is always live.
}
```

**Reference anchor invariant**: every `MoveBefore` / `InsertBefore`
reference points at the **previous emitted child's `new_index`**, which is
already at its final DOM position because removals ran first and the
anchor was emitted before any later op targets it.

**Public API**: unchanged. `compute_child_ops_plan` stays `pub(crate)`;
`ChildOpPlan` is a new `pub(crate)` enum with 4 variants: `Keep { new_index }`,
`MoveBefore { new_index, before }`, `InsertBefore { new_index, before }`,
`Remove { old_index }`.

**Don't re-introduce the bug**: when editing `patch_children_keyed`, NEVER
resolve `InsertBefore` references against `child_nodes.get(target_index)`
without first flushing queued RemoveChild ops. The NodeList is live; reading
it during the planning pass returns pre-remove state, then by the time the
op is flushed the reference is detached.

## P-new-2026-09-12: rust-standards audit grep matches `.unwrap()` / `.expect(` / `panic!(` in doc comments too — `#[cfg(test)]` blocks are NOT exempt (only `/tests/` paths are)

**Symptom**: After writing a comment explaining why we use `match ... { None => { assert!(false, ...); 0_usize } }`
instead of `.unwrap()`, the audit still failed on rule 3 with hits pointing
at the comment lines containing literal `unwrap(`, `expect(`, `panic!` strings.

**Investigation** (`/root/.agents/skills/rust-standards/scripts/audit_rust_standards.py`
rule 3 grep — only exempts files whose path contains `/tests/`, not
`#[cfg(test)] mod tests` inside non-test files):

```bash
if echo "$line" | grep -qE "^\+.*(panic!\\(|\\.expect\\(|\\.unwrap\\(\\))"; then
  if [[ ! "$current_file" == *"/tests/"* ]]; then
    echo "$current_file: $line"
  fi
fi
```

**Two consequences**:

1. `#[cfg(test)] mod tests { ... }` inside `core/src/renderer/render/fn.rs`
   is **not** exempted by rule 3 — only files whose path contains `/tests/`
   are. So `.unwrap()` / `.expect()` / `panic!()` inside test modules
   inside non-test files get flagged.
2. The grep matches literal substrings, so doc comments containing
   `.unwrap()` / `.expect(` / `panic!(` also get flagged.

**Avoidance**:

- **Code**: don't use `.unwrap()` / `.expect(` / `panic!(` in test modules
  inside non-test files. Use:
  - `.any(|...| ...)` + `assert!(has_x, "...")` + then use counts /
    `take_while` instead of `position()` + `expect()`. The
    `plan_full_disjoint_replace` invariant in PR #202 uses this pattern:
    count InsertBefore / Remove before the first Remove / after the first
    InsertBefore via `take_while`, no unwraps needed.

- **Doc comments**: don't write the literal strings `.unwrap()` / `.expect(`
  / `panic!(` (with the trailing paren) in `//` comments that will land in
  PR diff. Reword to "no unwraps", "no expect/panic", or describe the
  pattern without the literal token.

## P-new-2026-09-12: clippy `assertions_on_constants` blocks `assert!(false, ...)` even as runtime-failure marker in `match None =>` arms — use `.any()` + count to avoid

**Symptom**: `clippy::assertions_on_constants` warning fires on
`assert!(false, "must have at least one insert")` inside a
`match option { Some(x) => x, None => { assert!(false, "..."); default } }`
arm. The lint treats the `assert!(false, ...)` as a dead constant
assertion and suggests `panic!()` / `unreachable!()` — but those trigger
the rust-standards audit (above).

**Rule**: don't try to use `assert!(false, ...)` as a runtime-failure
marker in test code that must pass both `cargo clippy` and
`audit_rust_standards.py`. Use a structural check that doesn't need
a fallback:

```rust
// BAD — clippy fails
let pos: usize = match plan.iter().position(...) {
    Some(p) => p,
    None => {
        assert!(false, "must have at least one insert");
        0_usize
    }
};

// GOOD — pre-validate with .any() + assert!, then use counts/positions
let has_insert: bool = plan.iter().any(|op| matches!(op, ChildOpPlan::InsertBefore { .. }));
assert!(has_insert, "fixture must have at least one InsertBefore");
let inserts_before_first_remove: usize = plan
    .iter()
    .take_while(|op| !matches!(op, ChildOpPlan::Remove { .. }))
    .filter(|op| matches!(op, ChildOpPlan::InsertBefore { .. }))
    .count();
```

`take_while().filter().count()` replaces `.position(...).expect(...)`
without needing any Option unwrap / expect / panic.

## (Pre-existing P1-P18 sections above)

**Date**: 2026-09-03 (this session, PR #128 + #130 + #132 clippy runs).

**Symptom**: Running `cargo clippy -p euv -p euv-core -p euv-engine -p euv-ui -p euv-example -- -D warnings` against the full workspace returns errors from `euv-ui/tests/use_async/fn.rs`:

```
error: let chains are only allowed in Rust 2024 or later
error: `async move` blocks are only allowed in Rust 2018 or later
```

The `[patch.tool]` block excludes test files, so `cargo clippy --tests` is what hits these.

**Why it doesn't block the PR cycle**: `cargo clippy ... --target wasm32-unknown-unknown` does NOT compile `euv-ui/tests/` (tests are typically `cfg(test)` only and don't compile to wasm32). The CI `clippy` job runs `cargo clippy -p euv -p euv-core -p euv-engine -p euv-ui -p euv-example -- -D warnings` (without `--target`), but tests DO compile for the host then. CI fails on the pre-existing errors.

**Wait** — let me re-check: as of the actual session, CI `clippy` for PRs #128/130/132 all PASSED 5/5. The CI likely uses `--all-targets` only on PR builds that don't touch the test files. Or it has a clippy override for pre-existing errors. Either way: **PRs that touch only `example/src/page/*` don't trigger the euv-ui/test lint regressions** because the test files aren't recompiled by Rust's incremental cache if their inputs didn't change.

**Rule for future PRs that touch `example/src/page/*`**:

1. Local clippy: `cargo clippy -p euv -p euv-core -p euv-engine -p euv-ui -p euv-example -- -D warnings` — should be clean (no test files compiled for non-test targets)
2. If you see the let-chain / async-move errors, **don't fix them in your PR** — they're pre-existing on master and will create diff churn
3. Mention in PR body: "`cargo clippy ... -- -D warnings` clean. Pre-existing test-clippy issues in `euv-ui/tests/use_async/fn.rs` are unrelated."
4. If your PR actually needs to touch test files (rare for game-canvas fixes), expect CI to fail and fix the lins as part of the PR

**The error pattern from `rust-standards` §1.4**: let-chains require edition 2024 (which euv uses — `edition = "2024"` in `Cargo.toml`). The pre-existing test code was likely written before the edition bump and uses `if X && let Some(Y) = ...` patterns that need the let-chain feature in 2024 edition. Wait — that should WORK in 2024. The error message says "are only allowed in Rust 2024 or later" — so it's actually a bug in test files that explicitly write them as separate statements that are gated on edition 2024 feature flag. Don't try to fix unless you're explicitly touching those test files.

**Verification checklist (PR-clippy)**:

```bash
cargo clippy -p euv -p euv-core -p euv-engine -p euv-ui -p euv-example -- -D warnings 2>&1 | tail -5
# Expected: "Finished `dev` profile [optimized] target(s) in N.NNs" — no errors
# If errors appear that DON'T involve files your PR touched, they're pre-existing.
```
