---
name: gh-pr-creation-workflow
description: GitHub contribution workflow for eastspire-owned namespaces (eastspire/* + hyperlane-dev/* + euv-dev/* + crates-dev/* + docs-pages/*). **Decide the change type first, the namespace second: docs / config / comment-only changes commit straight to the default branch with no PR; only changes to executable code branch, push, open a PR, and delete the branch after merge.** Third-party repos where eastspire is not admin still go through `gh repo fork` + PR. Use when deciding whether to push directly, branch, fork, or open a PR; covers the gh CLI commands, remote layout, the mechanical `classify_change.py` classifier, branch deletion (including the repo-level `delete_branch_on_merge=true` prerequisite), and the eastspire-admin exception for fork-disabled private repos.
license: MIT
---

# GitHub contribution workflow (eastspire)

Two dimensions decide every contribution: **what changed** (docs / config /
comments vs. executable code) and **where the repo lives** (eastspire-owned vs.
third-party). The first decides *whether* you open a PR, the second decides
*how* the branch reaches the repo. Run them in that order.

This replaced the 3-track scheme (2026-08-28 → 2026-09-25) where `eastspire/*`
and `docs-pages/*` direct-pushed to master with no PR while everything else
fork-firsted (2026-09-25: all source-side contributions through one PR cycle), and
it further replaces the 2026-09-27 per-repo split, where every change in every
namespace went through a PR and a `README.md` typo fix cost a full PR cycle.
**Now the type of change decides.**

## Decision tree (decide in 3 seconds)

**Check the change type FIRST, then the namespace.** The type decides *whether*
you open a PR; the namespace decides *how* you get the branch there (push to
upstream vs. fork). Getting the order wrong means either a pointless PR for a
typo fix, or an unreviewed code change shipped to `master`.

```
STEP 1 — What does the diff change?            (run classify_change.py)
├─ docs / config only, or every changed line is
│  a comment / docstring / blank line          → DIRECT_PUSH, no PR. STOP.
│  (SKILL.md, README.md, *.yml, Cargo.toml, /// in a .rs file, …)
├─ mixed docs+code, or anything binary,
│  generated, or a lockfile                    → NEEDS_PR. Go to STEP 2.
└─ any changed line of executable code         → NEEDS_PR. Go to STEP 2.

STEP 2 — Where does the repo live?             (decides the mechanics only)
├─ eastspire/*                       (personal)           ─┐
├─ hyperlane-dev/*                   (eastspire admin)     │
├─ euv-dev/*                         (eastspire admin)     ├─→ BRANCH + PUSH-TO-UPSTREAM + PR + --delete-branch
├─ crates-dev/*                      (eastspire admin)     │   (this skill, main flow)
└─ docs-pages/*                      (eastspire admin)    ─┘
└─ third-party / no admin role       (e.g. tokio-rs/*, clap-rs/*)
   ├─ forking enabled on upstream    → gh repo fork + push to fork + PR (legacy Track 2)
   └─ forking disabled + private     → Contents/git-refs API + branch on upstream + PR
```

The mechanical classifier, so step 1 is a command and not a judgement call:

```bash
python3 ~/.agents/skills/git-standards/scripts/classify_change.py
# VERDICT: DIRECT_PUSH → commit on the default branch, stop
# VERDICT: NEEDS_PR    → continue below
```

Until 2026-09-27 the split was **per-repo** — "a 1-line typo follows the same
flow as a 2000-line refactor". That is now wrong: the user's rule is
**「对于修改文档和修改配置的改动请直接提交不要创建 pr，只有对于代码造成了改动才需要
创建 pr，pr 合并之后分支需要删除」** plus **「修改代码的注释也是直接提交不需要创建
pr」**. A comment-only or config change goes direct **in every namespace**,
including `euv-dev/*` and `crates-dev/*` — not only in `eastspire/.agents`.
Full rule and boundary table: `git-standards` §3.3a.

The one remaining per-repo carve-out: **personal forks under `eastspire/*` of
third-party repos** (`eastspire/serde`, `eastspire/euv` mirror, etc.) — those
still mirror their upstream through `gh repo fork` and use the legacy Track 2
flow when contributing back, because direct push to the third party isn't
permitted.

## Direct-push route (docs / config / comments — no PR)

When step 1 returns DIRECT_PUSH, there is no branch, no PR and no review. Skip
straight to committing on the default branch:

```bash
git fetch origin && git checkout <default-branch> && git pull --ff-only origin <default-branch>
git add <only-your-files>          # stage precisely, no -A
git commit -m "<type>(<scope>): <subject>" -m "<body wrapped 72, English>"
git push origin <default-branch>   # direct, no PR
```

Applies in **every** namespace — `eastspire/*`, `euv-dev/*`, `hyperlane-dev/*`,
`crates-dev/*`, `docs-pages/*`. `.agents` (the skill library) is the everyday
example, not a special case.

No branch means no `--delete-branch` step: nothing was created, so nothing has
to be cleaned up. If branch protection rejects the push, that repo does not
accept direct commits — fall back to the full PR flow and say so rather than
retrying with an admin token.

## Universal flow for eastspire-owned repos

Every repo under `eastspire/*`, `hyperlane-dev/*`, `euv-dev/*`,
`crates-dev/*`, or `docs-pages/*` follows the same six steps. No fork, no
`upstream` remote, no `--head owner:branch` gymnastics — push the branch
straight to the upstream repo and open the PR from there.

### 1. Verify write permission + remote layout

```bash
git remote -v
# expected: origin ssh://git@github.com/<owner>/<repo>.git  (single remote)

gh api repos/<owner>/<repo>/collaborators/eastspire/permission --jq .permission
# expected: admin / maintain / write
# If 'read' or 'none' — STOP. The repo is NOT in eastspire's admin scope.
```

### 2. Sync local default branch from upstream

```bash
git fetch origin
git checkout <default-branch>   # usually master, sometimes main
git pull --ff-only origin <default-branch>
git log -1 --oneline            # confirm HEAD == origin/<default>
```

### 3. Branch off the clean default

```bash
# Branch-name convention: <type>/<scope>-<slug>-YYYY-MM-DD
# examples:
#   feat/render-batch-append-2026-09-25
#   fix/login-redirect-bug-2026-09-25
#   chore/bump-version-0-25-14-2026-09-25
git checkout -b <branch>
```

**Critical**: always branch from the freshly-fetched default branch, NOT from
another open PR's head branch. PRs opened off an unmerged base inherit that
PR's commits in the diff (the 2026-09 PR #146/#147 incident). Stack/dependent
PRs are the only exception — call it out in the PR body.

### 4. Make the change + commit (Conventional Commits, English only)

```bash
git add <files>
git -c user.name=eastspire -c user.email=eastspire@users.noreply.github.com \
    commit -m "<type>(<scope>): <subject>

<body explains why, not what, wrapped at 72 chars>"
```

Type ∈ {`feat`, `fix`, `refactor`, `perf`, `docs`, `test`, `build`, `ci`,
`chore`, `style`, `revert`}. Body and subject must be English
(`rust-standards` §2.7 — applies to ALL GitHub-visible text). Don't use
Chinese characters in commit subjects, PR titles, or PR bodies.

### 5. Push the branch straight to upstream + open PR

```bash
git push -u origin <branch>

gh pr create \
  --repo <owner>/<repo> \
  --base <default-branch> \
  --head <branch> \
  --title "<type>(<scope>): <subject>" \
  --body-file /tmp/pr-body.md
```

Note `--head <branch>` (NOT `--head eastspire:<branch>`) — there's no fork,
so the head ref is unqualified. The PR's head URL will be
`https://github.com/<owner>/<repo>/tree/<branch>`.

### 6. Monitor CI → stop at green → wait for merge → clean up

```bash
gh pr checks --watch                 # wait for green
```

**STOP at green.** Never run `gh pr merge --auto` or
`enablePullRequestAutoMerge` unless the user has typed an explicit
"merge it" / "go ahead" for THIS PR in the current session. The user
owns merge decisions — see `github-pr-workflow` §6 for the full rule.

When the user approves merge, prefer:

```bash
gh pr merge <N> --repo <owner>/<repo> --squash --delete-branch --body-file /tmp/pr-body.md
```

`--delete-branch` deletes the head branch on the upstream repo the moment
the squash commit lands. Combined with `delete_branch_on_merge=true` at the
repo level (see *Repo settings* below), this guarantees no stale branches
accumulate.

Then locally:

```bash
git fetch origin <default-branch>
git checkout <default-branch>
git reset --hard origin/<default-branch>
git branch -d <branch>            # local branch gone
git log -1 --oneline              # confirm HEAD == origin/<default>
```

The `git reset --hard origin/<default>` step is good hygiene before opening
the next PR — for this flow (direct push to upstream, no fork) the local
default branch IS upstream's HEAD already, but resetting makes that explicit.

## Repo settings (one-time per repo)

Auto-delete on merge requires the repo setting
`delete_branch_on_merge=true`. Run this once per eastspire-owned repo (it
survives across PRs):

```bash
gh api -X PATCH repos/<owner>/<repo> \
  -f delete_branch_on_merge=true
```

Default branch can also be queried from the API to drive the
`--base <default-branch>` argument:

```bash
gh repo view <owner>/<repo> --json defaultBranchRef --jq .defaultBranchRef.name
```

Verified 2026-09-25 across the eastspire-owned set: `euv-dev/euv`,
`euv-dev/euv-app`, all 12 `hyperlane-dev/*` repos, all 16 `crates-dev/*`
repos, `docs-pages/docs`, `docs-pages/pages`, and non-fork `eastspire/*`
repos — all had `delete_branch_on_merge=null` at audit time and have been
flipped to `true` via batch `gh api -X PATCH`.

## Applies to (full list)

| Namespace | Notes |
| --- | --- |
| `eastspire/*` non-fork (personal) | `.agents`, `LTPP`, `LTPP-APP-Flutter`, `LTPP-CODE`, `LTPP-CODE-RUN`, `LTPP-SSH`, `eastspire`, `eastspire/dsh-plugin-longmem`, `eastspire/certbot-letencrypt-txy-ssl`, `eastspire/dioxus-study`, `eastspire/hyperlane-playground-android-app`, `eastspire/kimi-mc`, `eastspire/LeetcodeAndAcwingRank`, `eastspire/HTML-PDF`, `eastspire/OjJudgeTestdataCreat`, `eastspire/post-blog-user-crawler`, `eastspire/public`, `eastspire/rust-get-proxy-request`, `eastspire/rust-tools`, `eastspire/sqs-douyin-collection-download`, `eastspire/sun-yuchen-skill`, `eastspire/tauri-app`, `eastspire/VUE-EXE`, `eastspire/vue-wasm`, `eastspire/water-surface`, `eastspire/web-server-pressure-measurement`, `eastspire/zeng-ying-skill` |
| `euv-dev/*` | `euv-dev/euv`, `euv-dev/euv-app`, `euv-dev/euv-docs` (and any future repos) |
| `hyperlane-dev/*` | `hyperlane`, `hyperlane-log`, `hyperlane-time`, `hyperlane-quick-start`, `hyperlane-broadcast`, `hyperlane-utils`, `hyperlane-plugin-websocket`, `hyperlane-macros`, `hyperlane-ai`, `hyperlane-cli`, `hyperlane-mcp-upload` (11 repos at audit) |
| `crates-dev/*` | 16 repos (color-output, bin-encode-decode, std-macro-extensions, china_identification_card, compare-version, lombok-macros, tcplane, tcp-request, file-operation, recoverable-thread-pool, recoverable-spawn, clonelicious, future-fn, etc.) |
| `docs-pages/*` | `docs-pages/docs` (VuePress source, private), `docs-pages/pages` (Vercel HTML build output — only edit when fixing a build-output mismatch; otherwise edit `docs-pages/docs` and let the auto-deploy regenerate) |

## Exception: personal forks under `eastspire/*` of third-party repos

`eastspire/*` repos with `fork: true` (e.g. `eastspire/serde`,
`eastspire/clap`, `eastspire/euv`, `eastspire/rust-by-example-cn`) are
**third-party mirrors**, not eastspire source. They:

- Stay as read-only references (push to them freely, no PR needed).
- For PRs back to the third party (`tokio-rs/serde`, `clap-rs/clap`,
  `euv-dev/euv`, etc.) → use the **legacy Track 2 fork-first flow**:
  `gh repo fork <third>/<repo> --remote` (idempotent if already forked),
  push the branch to the fork, `gh pr create --repo <third>/<repo>
  --head eastspire:<branch>`.

Reason: direct push to a third party requires admin on the third party,
which eastspire doesn't have. The fork exists precisely to bridge that
permission gap.

```bash
# Legacy Track 2 — for eastspire/<repo> → <third-party>/<repo>
gh repo fork <third-party>/<repo> --remote          # idempotent
cd ~/github/eastspire/<repo>
git fetch upstream
git checkout <default-branch> && git pull --ff-only upstream <default-branch>
git checkout -b <branch>
# ... commit ...
git push -u origin <branch>
gh pr create --repo <third-party>/<repo> \
  --head eastspire:<branch> --base <default-branch> \
  --title "..." --body-file /tmp/pr-body.md
gh pr merge <N> --repo <third-party>/<repo> --squash --delete-branch
```

## Exception: fork-disabled private repos

If an eastspire-owned repo ever becomes private AND has fork disabled
(private repo + forking disabled is rare; verified rare on this host),
use the Contents API + git refs API to create the branch directly on
upstream without cloning:

```bash
# 1. Create the branch on upstream via git refs
BASE_SHA=$(gh api repos/<owner>/<repo>/git/refs/heads/<default-branch> --jq .object.sha)
gh api -X POST repos/<owner>/<repo>/git/refs \
  -f ref="refs/heads/<branch>" -f sha="$BASE_SHA"

# 2. Upload file changes via Contents API (one PUT per file)
gh api -X PUT repos/<owner>/<repo>/contents/<path> \
  -f message="<commit msg>" -f branch=<branch> \
  -f content=<base64> -f sha=<blob-sha-if-updating>

# 3. Open PR
gh pr create --repo <owner>/<repo> --head <branch> --base <default-branch>
```

This is needed only when `git clone` would be too slow AND forking is
disabled. None of the eastspire-owned repos currently require this —
public clones work fine.

## PR body style (applies to ALL flows)

- **English** for all GitHub-visible text: PR title, PR body, commit
  message, code comments. `rust-standards` §2.7 codifies this; the rule
  applies regardless of the user's chat language.
- **Conventional commit subject**: `<type>(<scope>): <subject>`, type ∈
  {feat, fix, refactor, perf, docs, test, build, ci, chore, style,
  revert}
- **Three-section body**: `## Summary` / `## Verification` / `## Notes`
- **Always `--body-file`** instead of `--body "..."` — gh escapes
  backticks in inline strings, breaking code blocks.
- **Search before opening**: `gh pr list --search "..." --repo <o>/<r>`
  to avoid duplicate PRs.

## Pitfalls

1. **Don't confuse personal fork vs source.** `eastspire/euv` is a
   personal fork of `euv-dev/euv`. Pushing to `eastspire/euv` is
   direct-to-upstream (it's an eastspire-owned repo, no PR needed if
   you don't intend to ship the change anywhere else). If you DO want
   to upstream the change to `euv-dev/euv`, use the **legacy Track 2
   fork-first flow** documented in *Exception: personal forks under
   `eastspire/*`* above. The repo you push to and the repo you PR from
   are different decisions.
2. **Always start a new feature branch from clean origin/<default>.**
   Opening a branch from another open PR's branch makes `gh pr diff`
   include that PR's commits in your new PR's diff. Recipe:
   `git fetch origin && git checkout <default> && git pull --ff-only origin <default> && git checkout -b <new>`.
   Stack/dependent PRs (where one PR is intentionally the base of
   another) are the only exception — call it out in the PR body.
3. **`gh pr create --head <branch>` is unqualified** for direct-push
   upstream flow. Adding `--head eastspire:<branch>` only works for
   legacy Track 2 PRs (fork under eastspire targeting a third party).
   For this skill's main flow, plain `--head <branch>` is correct.
4. **CI workflows in fork repos can't deploy Pages / push to crates.io**
   — applies to **legacy Track 2 fork-first flow** (personal fork
   pushing to third-party upstream). The fork's `secrets.*` is empty
   for security reasons. Gate deploy jobs with
   `if: github.repository == '<org>/<repo>'` or only run them on
   `push` events (PRs from forks have read-only tokens by design).
   For this skill's main flow (direct push to eastspire-owned
   upstream), all repo secrets are available in CI as usual.
5. **`actions/deploy-pages@v4` on `workflow_dispatch` from fork**
   silently no-ops — the fork has no Pages deploy key. Applies to
   legacy Track 2 only. Same `if:` guard fixes it. For main flow
   direct push, Actions deploys normally.
6. **After PR merge, run cleanup locally:**
   ```bash
   git fetch origin <default> && git checkout <default> && \
   git reset --hard origin/<default> && git branch -d <merged-branch>
   ```
   - **Pitfall(squash merge 后 `git branch -d` 会 refuse,必须 `-D`)**:squash merge 把所有分支 commits 压缩成一个新 SHA(不是任何源 commit 的祖先),所以源分支的 tip 不在 master 的 ancestry 里。`git branch -d` 会报 "the branch 'X' is not fully merged" 并 refuse 删除;`git branch -D` 强制删除(因为 squash 之后这些 commits 实际已经被 squash 进 master,只是 SHA 不连续)。**预防**:对自己 PR 走 squash merge 的场景,直接用 `-D`;merge commit / rebase merge 的场景下 `-d` 才能工作(commits 是祖先)。验证:`git branch -D <branch>` 后 `git branch -a` 不再列出该分支 = 清理成功。
   The `reset --hard origin/<default>` ensures your local default
   branch tracks the new merge commit. euv PR #233/#234/#235/#236 chain
   (2026-09-14) had the legacy Track 2 equivalent of this race —
   local `master` was "ahead of origin/master" but actually at the old
   fork master. For direct-push flow this is mostly a no-op
   (local == origin), but doing it explicitly after every merge keeps
   the next `git checkout -b` from a clean base.
7. **`gh pr close --delete-branch` silently skips `--delete-branch`
   for legacy Track 2 fork-PRs** (`! Skipped deleting the remote
   branch of a pull request from fork`). Manual
   `git push origin --delete <branch>` is required after. For main
   flow direct-push PRs, `--delete-branch` works as documented.
8. **Use `--body-file` not `--body "..."`** — gh escapes backticks in inline strings and your fenced code blocks come out as plain text. `cat <<'EOF' > /tmp/pr-body.md` then `--body-file /tmp/pr-body.md`.
9. **Don't open PRs from a dirty worktree** — uncommitted `.pyc`, `__pycache__/`, or scratch files will land in the diff. Run `git status` before `git add -A`.
10. **`eastspire/*` forks used as upstream references**
    (`eastspire/euv`, `eastspire/serde`, `eastspire/clap`, etc. from
    `gh repo list eastspire`) are **eastspire-owned** for the purposes
    of `git push` (no PR needed to push to them). For PRs back to the
    original third party (`euv-dev/euv`, `tokio-rs/serde`,
    `clap-rs/clap`), use the **legacy Track 2 fork-first flow**
    documented in *Exception: personal forks under `eastspire/*`*
    above.
11. **`docs-pages/*` is main-flow for code (no special-case)** — direct
    push to upstream + PR + `--delete-branch`, same as `euv-dev` and
    `hyperlane-dev`. The old 2026-09-05 "direct push master, no PR"
    shortcut is retired **for code changes**. Docs and config changes in
    `docs-pages/*` are now direct-push like everywhere else (per the
    change-type rule, not per-org), and `docs-pages/pages` (Vercel build
    output) still should not be edited directly — edit `docs-pages/docs`
    (VuePress source) and let the auto-deploy regenerate.
12. **`gh pr view N` stdout is often empty** with restricted-scope GH_TOKEN. Use `gh pr view N --json ...` or `gh api repos/<org>/<repo>/pulls/N` for reliable reads.
13. **`gh pr edit --title` silently fails** when token lacks `read:org` (GraphQL path). For renaming PRs, use REST: `curl -X PATCH -H "Authorization: token ***" https://api.github.com/repos/<org>/<repo>/pulls/<N> -d @payload.json`.
14. **`gh pr create --head owner:branch` fails with "Head ref must be a branch" / "Not all refs are readable"** when the head repo isn't registered as a fork in GitHub's graph — `gh repo create` makes an independent repo, NOT a fork, and the `parent` metadata is never set retroactively even after `git remote add upstream && git push upstream master`. Verify with `gh repo view <you>/<repo> --json parent`; if `parent == null` you need to delete + re-fork cleanly. See `github/github-repo-management` §11.2 (Independent repo vs fork), §11.3 (-N collision cleanup), §11.1 (`delete_repo` scope).
14a. **`gh pr create` returns "No commits between euv-dev:master and eastspire:fix/branch" even though `git diff upstream/master..HEAD --stat` clearly shows a diff.** Symptom: the GraphQL compare endpoint sees the head branch as effectively at the same SHA as the base (timing? cache? graph consistency lag?). The branch is correctly pushed, `gh api repos/<org>/<repo>/compare/<base>...<head>` returns `ahead_by: 1, behind_by: 0`, but `gh pr create` still fails. **Fix**: skip `gh pr create` entirely and POST to the REST endpoint directly:
    ```python
    import json, urllib.request, os
    body = open("/tmp/pr-body.md").read()
    data = json.dumps({
        "title": "<type>(<scope>): <subject>",
        "head": "eastspire:fix/branch",
        "base": "master",
        "body": body,
    }).encode()
    req = urllib.request.Request(
        "https://api.github.com/repos/<org>/<repo>/pulls", method="POST", data=data)
    req.add_header("Authorization", f"token {os.environ['GH_TOKEN']}")
    req.add_header("Accept", "application/vnd.github+json")
    resp = urllib.request.urlopen(req)
    pr = json.loads(resp.read())
    print(pr["html_url"])  # https://github.com/<org>/<repo>/pull/<N>
    ```
    Set `GH_TOKEN` via `source /root/.bashrc.d/gh_token.sh && export GH_TOKEN` before running. Returns the PR URL directly. Common cause: the head branch wasn't pushed to the fork (`origin`) — verify with `git ls-remote <your-remote> <branch>` first. If empty, push to fork then retry — `gh pr create` from `upstream` direct URL without fork coordination is the trigger.
15. **`--delete-branch` on `gh pr merge` requires `delete_branch_on_merge=true` AT THE REPO LEVEL** — verify with
    `gh repo view <o>/<r> --json deleteBranchOnMerge` before relying
    on auto-delete. If unset, set it via
    `gh api -X PATCH repos/<o>/<r> -f delete_branch_on_merge=true`.
    The CLI flag `--delete-branch` is a no-op (with a warning) if the
    repo setting is off. As of 2026-09-25 all eastspire-owned repos
    have this flipped to `true` via batch `gh api -X PATCH`.

15a. **"合并之前的 PR，新开一个" — user-owned merge cadence, not an
    agent decision.** When the user says "之前的 PR 先合并，新开一个
    PR 修复" / "merge the previous PR and open a new one", the
    sequence is:

    1. Merge all currently-open PRs the user mentioned — use
       `gh pr merge <N> --squash --delete-branch --body-file /tmp/merge-comment.md`
       (the `--body-file` keeps the squash commit descriptive). Stop
       at green before merging if any CI is still pending.
    2. After merge, reset the local default branch:
       `git fetch origin <default> && git checkout <default> && git reset --hard origin/<default> && git branch -D <merged-branch>`.
       Use `-D` not `-d` after squash merge (pitfall 6 above).
    3. Verify the branch is gone on remote too: `git ls-remote origin <branch>` should return empty.
    4. Only THEN open the new PR, on a fresh branch off clean
       `origin/<default>`. Don't reuse the old branch — its SHA may
       have been rewritten by squash.

    If the new PR is a follow-up to the merged work and the user wants
    a version bump, bump the workspace `version` in the same PR per
    the per-project bump convention (e.g. ctares root only, hyperlane
    root only, euv root only — child crates use `version.workspace =
    true` and pick up the bump automatically). Don't ship a version
    bump on its own commit after the merge; combine the bump with the
    follow-up changes so the bump has a clear "this is the new
    release" PR.

## Multi-repo verifier-evolution cleanup ("rule changed, old PRs are all stale")

When a project-level verifier rule tightens (e.g. rust-standards §13.7 evolved from round-3 alphabetic-only to round-4 entry-length sort), **every open PR that was opened against the old rule is now FAILING the new verifier**, even if its title claims it's compliant. This pattern appears as "N open PRs across M repos, all broken by the same rule tightening". Cleanup sequence:

### 1. Audit by verifier, not by title

Trust the verifier output, NOT the PR title. A PR titled "alphabetize workspace dependencies" may have actually used entry-length sort; a PR titled "round-4 sort" may have used the old key-length sort. Run the verifier against each PR's branch (use worktree, NOT the main checkout — see pitfall below) and group:

- **Survivors** — verifier reports 0 violations. Keep these.
- **Stale** — verifier reports ≥1 violations. Will need supersession.

```bash
# For each (repo, branch) pair:
TMP="/tmp/verifier-audit-$(date +%s)"
mkdir -p "$TMP"
git -C /Users/sqs/code/<repo> worktree add --force "$TMP/<repo>-<branch>" <branch>
python3 <verifier-script> "$TMP/<repo>-<branch>"   # exit 0 = survivor
# cleanup
git -C /Users/sqs/code/<repo> worktree remove --force "$TMP/<repo>-<branch>"
```

### 2. Close stale PRs with `--delete-branch` + explanatory comment

```bash
for repo_pr in "<repo> <pr-number>"; do
  read -r repo pr <<< "$repo_pr"
  gh pr close "$pr" --repo "$repo" --delete-branch --comment "Closing: superseded by round-N verifier update. This branch passes round-(N-1) but fails round-N. The surviving PR carries the canonical order. See <reference-link> for the rule evolution."
done
```

`--delete-branch` deletes the head branch on the upstream repo (works for direct-push main flow; silently skipped for legacy Track 2 fork-PRs — see pitfall 7).

### 3. Cleaning-up verification — `--delete-branch` is not exhaustive

`gh pr close --delete-branch` does **not** clean up:

- **Local refs** in the main worktree: `git -C /Users/sqs/code/<repo> branch -D <branch>` after every close.
- **Orphan remote branches** (branches pushed but never attached to a PR, e.g. from a closed supersession that was force-pushed without reopening): verify with `git -C /Users/sqs/code/<repo> ls-remote origin <branch>` and delete with `git -C /Users/sqs/code/<repo> push origin --delete <branch>`.

```bash
# After closing all stale PRs in a repo, audit remote branches:
for repo in <repos>; do
  echo "===== $repo ====="
  for branch in $(git -C /Users/sqs/code/$repo branch -a | grep 'remotes/origin/' | awk '{print $1}' | sed 's|remotes/origin/||'); do
    # check if branch has any open PR
    has_pr=$(gh api "repos/$repo/pulls?head=$branch&state=open" --jq 'length')
    if [ "$has_pr" = "0" ]; then
      # check if branch has any commits ahead of master
      ahead=$(gh api "repos/$repo/compare/master...$branch" --jq '.ahead_by // 0' 2>/dev/null)
      if [ "$ahead" != "0" ] && [ -n "$ahead" ]; then
        echo "  orphan: $branch (ahead of master by $ahead commits)"
      fi
    fi
  done
done
```

Then delete confirmed orphans:

```bash
git -C /Users/sqs/code/<repo> push origin --delete <orphan-branch>
```

### 4. Pitfall — verifier-state vs checkout-state

Running `<verifier-script> <repo_dir>` against the user's main checkout dir gives you the verifier output for **whatever branch that checkout is currently on**, NOT the branch you intend to verify. If your main checkout is on `master` and you want to verify a feature branch:

```bash
# WRONG: verifier reads main checkout's branch (master), not the feature branch
python3 verify_dep_order.py /Users/sqs/code/euv

# RIGHT: detached worktree at the feature branch, verifier against the worktree
git -C /Users/sqs/code/euv worktree add --force /tmp/euv-feature feature-branch
python3 verify_dep_order.py /tmp/euv-feature
git -C /Users/sqs/code/euv worktree remove --force /tmp/euv-feature
```

The worktree pattern is essential for batch verification — for each branch, create a worktree, verify, clean up. Verifying 7 PRs across 3 repos without worktrees would require `git checkout` round-trips that leave the main checkout on a stale branch mid-task.

### 5. Master fix surface

If the verifier-evolved rule also uncovers violations on `master` itself (because the old PRs were the only line of defense), the **survivor PRs must be the canonical fix path**: when each survivor PR merges, its commits bring master into compliance. Verify that each survivor PR's diff vs master actually contains the fix to master's violations:

```bash
git -C /Users/sqs/code/<repo> log --oneline master..<survivor-branch>
gh api "repos/<repo>/compare/master...<survivor-branch>" --jq '.files[].filename'
```

If a master violation is **not** covered by any survivor PR, it's a separate scope — open a new PR for it rather than amending a survivor.

### When this applies

- Verifier rule tightened and old PRs are now stale (most common)
- Linter / formatter version bump made old PRs non-conformant
- New mandatory CI check (e.g. security scanner, SBOM) added that old PRs lack
- Any scenario where "the rule changed, N old PRs no longer fit"

This is distinct from single-PR supersession (scope grew → amend + force-push). The key difference: here the old PRs were correct under the OLD rule but are stale under the NEW rule; force-pushing the same commits doesn't help because the rule itself moved.

## Supersede flow

Already opened a PR but the scope grew? Don't open a second one — supersede:

```bash
gh pr close <N> --comment "Superseded by upcoming PR that bundles X+Y."
git add <new-files>
git commit --amend --no-edit
git push --force origin <branch>           # --force (lease fails post-amend)
gh pr create --base <default> --head <branch> --title "..." --body-file /tmp/pr-body.md
```

Add `## Supersedes #N` to the new PR body. New PR number will increment.
For legacy Track 2 (fork-first), the `git push --force origin <branch>`
targets your fork — same command shape, different remote.

## Append-to-existing-PR flow ("在已有 PR 里更新")

User says "直接在已有开的 PR 里更新代码就行" / "fix goes into PR #N" /
"append the fix to the open PR". Don't open a new PR, don't supersede —
**commit on top of the existing PR's head branch**:

```bash
# 1. Find the PR's head branch
gh pr view <N> --repo <owner>/<repo> --json headRefName,headSha
# → headRefName: "feat/render-batch-append-2026-09-25"

# 2. Checkout that branch (do NOT create a new branch)
git fetch origin <head-branch>
git checkout <head-branch>
git pull origin <head-branch> --rebase   # sync to remote head

# 3. Make all changes (fix + version bump etc.) and commit on top
git add <files>
git -c user.name=eastspire -c user.email=eastspire@users.noreply.github.com \
  commit -m "<type>(<scope>): <subject>

<body explains why, not what>"
git push origin <head-branch>            # no --force needed, new commit on top

# 4. PR auto-updates; CI re-runs
gh pr checks <N> --repo <owner>/<repo>
```

For legacy Track 2 (fork-first), `origin` in steps 2/3/5 is the fork
(`eastspire/<repo>`) and the `gh pr view` / `gh pr checks` `--repo` arg
is the third-party upstream (`<org>/<repo>`). All else identical.

**When to use this** vs supersede vs new PR:

| User intent | Action |
| --- | --- |
| "在已有 PR 里追加" / "fix goes into PR #N" / "在那个 PR 里更新一下" | **Append** (this section) |
| "scope 变了, supercede" / "合并这个, 重开一个" | Supersede (section above) |
| "开新 PR" / "单独发一个" | New PR (main flow) |
| 模糊 | Ask one clarifying question via `clarify`, don't guess |

**Anti-patterns caught in 2026-09 PR #146 + #147 incident** (closed #147
after opening, then cherry-picked to #146 — wasted a close + new PR cycle):

- Created `fix/merge-class-cssref-drop` branch on top of `upstream/master`,
  opened PR #147, THEN realized user wanted fix in PR #146 → close #147,
  then cherry-pick to `perf/document-fragment-batch-append`. **Could have
  skipped the close by checking first** whether a fix-relevant PR was
  already open.
- `gh pr close --delete-branch` silently skips `--delete-branch` for
  legacy Track 2 fork-PRs (`! Skipped deleting the remote branch of a
  pull request from fork`); manual `git push origin --delete <branch>`
  is required after. For main flow, `--delete-branch` works.

**Diagnostic**: before opening any new PR, **always**:

```bash
gh pr list --repo <owner>/<repo> --state open --author @me --json number,title,headRefName,state
```

If a fix-relevant PR is already open → append. Otherwise → new PR.

16. **Local default branch ahead of `origin/<default>` after a
    non-fast-forwarded sequence (rare with main flow, possible with
    Track 2 legacy).** Symptom: your local clone's `<default>` has
    commits `origin/<default>` doesn't (e.g. an unmerged clippy-clean
    or version-bump commit that you merged locally first to keep CI
    green, but haven't pushed as a PR yet). The main-flow recipe
    "branch from clean `origin/<default>`" hides this case — if you
    only do `git checkout <default> && git pull origin <default> && git
    checkout -b feat/foo` you'll land on a default whose tip is NOT
    `origin/<default>`'s tip, and the diff against origin will include
    those local-only commits. Two clean fixes:

    ```bash
    # A) Cherry-pick the single commit you want to ship (preserves commit hash + message)
    git checkout -b feat/foo origin/<default>
    git cherry-pick <local-only-commit-sha>          # resolve any conflicts
    git push -u origin feat/foo
    gh pr create --repo <owner>/<repo> --head feat/foo ...

    # B) Rebase the local-only commits onto origin/<default> first
    git checkout <default>
    git rebase origin/<default>                     # rewrites local-only commits on top
    git checkout -b feat/foo                         # now local <default> == origin
    # then amend/append and push as normal
    ```

    **Conflict scope rule during cherry-pick / rebase**: if the origin
    version of a file lacks a section that your local-only commit
    added (e.g. Cargo.toml `[profile.dev]` block from a local-only
    clippy-clean commit, when origin has none yet), the conflict
    resolver should **drop that section from the PR** — it belongs to a
    separate scope (clippy-clean PR, version-bump PR) and mixing scopes
    dilutes review. The 4-file PR (#31 on `euv-dev/euv-docs`,
    2026-09-18) reproduced this exactly: cherry-pick of `41c6deb`
    (CLI) had a Cargo.toml conflict because `41c6deb` was committed on
    top of `d5a8443` (profile config), and origin didn't yet have
    either. Resolution kept `[[bin]]` (CLI scope) and dropped
    `[profile.dev]/[profile.release]` (clippy-clean scope, separate
    PR).

    Verification before `gh pr create` — confirm the PR diff contains
    ONLY the intended scope:

    ```bash
    git fetch origin
    git diff --stat origin/<default>..HEAD           # exactly the files you intend
    git diff origin/<default>..HEAD | grep -E '^[+-]' | grep -v '^+++' | grep -v '^---' | wc -l
    # If line count matches your expected diff scope, you're clean.
    ```

17. **Reply to an inline review comment via REST, not `gh pr comment`.**
    `gh pr comment <N>` posts a top-level PR conversation comment —
    useful for a final summary, but reviewers expect replies on each
    review-thread comment to land as **a reply in that thread**, with
    the original diff hunk still visible. Get the comment ID from
    `gh api repos/<o>/<r>/pulls/<N>/comments --jq '.[] | "\(.id) \(.path):\(.line)"'`,
    then POST to `repos/<o>/<r>/pulls/<N>/comments/<id>/replies`:

    ```bash
    gh api -X POST repos/hyperlane-dev/hyperlane/pulls/35/comments/4113690104/replies \
        -f body="Done — moved the thread_local into static.rs per the convention."
    ```

    `--jq .id` returns the new reply ID. Common pattern: open the
    `gh pr view N --comments` list (or the same REST endpoint) to find
    the IDs before replying. Don't batch: each `gh pr comment` call
    creates a separate conversation entry, which fragments the thread
    and confuses reviewers.

18. **`git push --force-with-lease` fails with `stale info` after a
    rebase/cherry-pick in a fresh worktree.** Symptom: the rebase
    produced a new commit SHA on the branch, but the reflog / local
    tracking info still references the pre-rebase SHA, so the lease
    check thinks the remote was modified by someone else and refuses.
    **Fix** (in order):

    ```bash
    # Refresh the lease baseline from origin (the rebased branch is
    # gone from origin, so this resolves to the missing-ref state, but
    # then the second push works):
    git fetch origin <branch>
    git push --force-with-lease origin <branch>   # may still fail

    # Fallback — plain --force when no one else could have updated the
    # branch between the rebase and this push (single-writer scenario):
    git push --force origin <branch>
    ```

    Verify with `git ls-remote origin <branch>` — should match the
    local SHA after the successful push. Don't use `--force-with-lease`
    blindly after every rebase; the lease guarantees nothing for a
    single-writer branch, and the failure costs you an extra fetch.

## Commit message style (all flows)

- English subject + body (per `rust-standards` §2.7 — applies to ALL GitHub-visible text)
- Conventional commit format: `<type>(<scope>): <subject>`
- Body explains the why, not the what