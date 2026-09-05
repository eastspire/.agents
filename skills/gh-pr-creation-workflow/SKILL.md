---
name: gh-pr-creation-workflow
description: Three-track GitHub contribution workflow for eastspire — repos under eastspire/* (personal account) AND under docs-pages/* (admin-owned docs org) push straight to master with no PR, while repos under any other organization (euv-dev/*, hyperlane-dev/*, crates-dev/*, third-party forks) go through fork + push branch + PR back to upstream master. Use when deciding whether to open a PR, fork a repo, or push direct; covers the gh CLI commands, remote layout, and the eastspire-admin exception for fork-disabled private repos.
license: MIT
---

# GitHub contribution workflow (eastspire)

Three-track workflow that decides whether a change needs a PR or not, based
solely on **where the repo lives**. Replaces the older "all non-personal repos
need a PR" rule (2026-08-28) and the subsequent "personal + docs-pages only"
specialization (2026-09-05).

## Decision tree (decide in 3 seconds)

```
Where does this repo live?
├─ eastspire/<repo>             → DIRECT PUSH to master, no PR, no fork
├─ docs-pages/<repo>            → DIRECT PUSH to master, no PR (eastspire is admin)
└─ <other-org>/<repo>           → FORK + PR
   ├─ has upstream remote?      → push to fork, gh pr create to org master
   ├─ fork disabled (private)?  → Contents/git-refs API + push branch to upstream + gh pr create
   └─ third-party repo          → standard gh repo fork + PR
```

The split is **per-repo**, not per-change. A 1-line typo follows the same track as a 2000-line refactor.

## Track 1 — Direct-push repos: `eastspire/*` (personal) and `docs-pages/*` (admin)

### Rule

Push straight to `master`. No PR, no fork, no feature branch — even for a 1-line typo or a single rule in `.gitignore`.

### Rationale

You (eastspire) own or admin both of these namespaces. The PR review ceremony would only be you approving yourself. Every other track (fork + PR) exists to get changes in front of a maintainer you don't control — that constraint is absent here. `docs-pages/*` was promoted from "fork + PR" to direct push on 2026-09-05 when the user confirmed that the docs site is also fully self-administered (no external contributors, no upstream oversight). The other three orgs (`euv-dev`, `hyperlane-dev`, `crates-dev`) keep the stricter workflow because they each have an active maintainer outside of eastspire's admin role.

### Standard flow

```bash
cd ~/github/<owner>/<repo>      # owner is eastspire or docs-pages

# 1. Verify the remote is direct (not an org fork you're shadowing)
git remote -v
# expected: origin ssh://git@github.com/<owner>/<repo>.git  (no upstream)

# 2. Make the change, commit, push
git add -A
git -c user.name=eastspire -c user.email=eastspire@users.noreply.github.com commit -m "<type>(<scope>): <subject>"
git push origin master
```

### Applies to

| Repo | Why |
| --- | --- |
| `eastspire/.agents` | skill library — direct push master |
| `eastspire/hyperlane-mcp-upload` | personal Rust project |
| `eastspire/hyperlane-quick-start` | personal hyperlane demo |
| `eastspire/euv` (and any other `eastspire/*` clone) | personal fork used for read-only reference work |
| `docs-pages/docs` | VuePress 2 source — direct push master (2026-09-05) |
| `docs-pages/pages` | Vercel HTML build artifact — **do NOT edit** (auto-regenerated from `docs-pages/docs`); only edit when fixing a build-output mismatch |
| All other `eastspire/*` repos listed under `gh repo list eastspire` | personal account → direct push |

### Pitfalls on this track

- **Don't accidentally clone under `~/github/<other-org>/...` and then push.** That's Track 2 territory even though the local working copy looks the same. Always confirm with `git remote -v` before pushing — the remote owner is the source of truth, not the local directory name.
- **`docs-pages/docs` is private**, so `gh api repos/docs-pages/docs` returns 404 for anonymous probes but git endpoints work fine — don't waste time debugging auth, use SSH.
- **CI workflows in personal/admin repos still need their own secrets.** Direct push doesn't bypass `secrets.CARGO_REGISTRY_TOKEN` etc.; GitHub Actions is per-repo regardless of who owns it.
- **Branch protection off by default.** `eastspire/*` and `docs-pages/*` repos typically have no `required_pull_request_reviews`, so direct push lands without a status check. If you need a CI gate, add one via `gh api -X PUT .../branches/master/protection` — but that's the repo owner's call.

## Track 2 — Organization and third-party repos (fork + PR)

### Rule

Always work through a fork. Branch from `upstream/master` (or `upstream/<base>`), push the branch to `origin` (your fork), then `gh pr create` targeting the org's default branch.

### Standard flow

```bash
# 1. Make sure you have a fork under eastspire
gh repo fork <org>/<repo> --remote   # adds upstream + origin if missing
cd ~/github/eastspire/<repo>          # or wherever the fork is checked out
git remote -v
# expected:
#   origin    ssh://git@github.com/eastspire/<repo>.git
#   upstream  https://github.com/<org>/<repo>.git

# 2. Branch from a CLEAN upstream master (see pitfall below)
git fetch upstream
git checkout master
git pull upstream master       # ensure local master == upstream master HEAD
git checkout -b <branch-name>

# 3. Commit + push to fork
git add -A
git -c user.name=eastspire -c user.email=eastspire@users.noreply.github.com commit -m "<type>(<scope>): <subject>"
git push -u origin <branch-name>

# 4. Open PR back to org master
gh pr create \
  --repo <org>/<repo> \
  --head eastspire:<branch-name> \
  --base master \
  --title "<type>(<scope>): <subject>" \
  --body-file /tmp/pr-body.md
```

### Per-repo base branch

Most org repos use `master` (`euv-dev/euv`, `hyperlane-dev/hyperlane`, `crates-dev/...`). Some use `main`. Always verify with `gh repo view <org>/<repo> --json defaultBranchRef` before opening the PR — `--base master` against a repo whose default is `main` will silently target the wrong branch.

### Applies to

| Repo pattern | Notes |
| --- | --- |
| `euv-dev/*` | `eastspire` is org admin but treat as upstream |
| `hyperlane-dev/*` | same |
| `crates-dev/*` | same |
| Any third-party repo (e.g. `the-benchmarker/web-frameworks`) | standard fork + PR |
| `eastspire/euv` (etc. when used as read-only reference) | push to personal fork only; PRs to `euv-dev/euv` go through `eastspire/euv` fork |
| ~~`docs-pages/*`~~ | **Moved to Track 1 (direct push) on 2026-09-05.** `docs-pages/docs` is VuePress markdown that eastspire admins end-to-end; `docs-pages/pages` is Vercel HTML build output and should not be edited anyway. |

> **Why docs-pages moved**: the user's mental model is "personal admin namespace + docs admin namespace" both being self-service. The other three orgs each have a non-eastspire maintainer who actually reviews PRs, so the fork-and-PR ceremony still serves a purpose there. `docs-pages` has no such maintainer — eastspire is the entire team — so the ceremony is pure overhead.

### Exception: fork-disabled private repos (`euv-dev/euv-docs` if it ever becomes private)

If a Track 2 repo becomes private AND has fork disabled (the only public-by-default case is no exception needed — you just fork), use the Contents/git-refs API workaround:

```bash
# Use the Contents API or git refs API to create/update the branch directly on upstream
gh api -X PUT repos/<org>/<repo>/contents/<path> \
  -H "Accept: application/vnd.github+json" \
  -f message="<commit message>" \
  -f branch=<branch-name> \
  -f content=<base64-encoded-content> \
  -f sha=<blob-sha-if-updating>

# Then push the branch with git if larger changes
git push origin <branch-name>     # where origin = <org>/<repo> via admin SSH

# Finally open the PR as normal — the branch already exists on upstream
gh pr create --repo <org>/<repo> --head <branch-name> --base master \
  --title "..." --body-file /tmp/pr-body.md
```

Note: `docs-pages/docs` used to live here as the canonical "private + fork-disabled + admin" case, but it was promoted to Track 1 (direct push) on 2026-09-05, so this exception now only applies to hypothetical future Track-2 repos.

## The three tracks compared

| Step | Direct-push `eastspire/*` / `docs-pages/*` | Org + third-party `<other>/<repo>` |
| --- | --- | --- |
| Clone / create | `gh repo create` or direct clone | `gh repo fork` |
| Remote layout | `origin` only | `origin` (fork) + `upstream` |
| Branch | stay on `master` | new feature branch off upstream `master` |
| Commit | direct | direct (same) |
| Push | `git push origin master` | `git push -u origin <branch>` |
| PR | **none** | `gh pr create --repo <org>/<repo>` |
| Review | self | maintainer |

## Verifying which track you're on

When in doubt:

```bash
git remote -v
# origin is ssh://git@github.com/<owner>/<repo>.git
# If <owner> in {eastspire, docs-pages} → Track 1 (direct push master)
# If <owner> is anything else → Track 2 (you already cloned upstream; check for fork)
```

```bash
# Programmatic check, useful in scripts
gh repo view <owner>/<repo> --json owner,nameWithOwner,defaultBranchRef
# owner.login ∈ {"eastspire", "docs-pages"} → Track 1, push directly
# owner.login == anything else → Track 2, fork + PR
```

```bash
# If origin points to an org repo, look for an eastspire fork
gh repo view <owner>/<repo> --json parent
# parent.nameWithOwner == "eastspire/<repo>" → you're on a fork, proceed Track 2
# parent == null → you're on upstream itself, fork first
```

## PR body style (applies to Track 2 only — Track 1 has no PR)

- **English** for all GitHub-visible text: PR title, PR body, commit message, code comments. `rust-standards` §2.7 codifies this; the rule applies regardless of the user's chat language.
- **Conventional commit subject**: `<type>(<scope>): <subject>`, type ∈ {feat, fix, refactor, perf, docs, test, build, ci, chore, style}
- **Three-section body**: `## Summary` / `## Verification` / `## Notes`
- **Always `--body-file`** instead of `--body "..."` — gh escapes backticks in inline strings, breaking code blocks
- **Search before opening**: `gh pr list --search "..." --repo <org>/<repo>` — avoid duplicate PRs

## Pitfalls

1. **Don't confuse "personal repo I forked for reference" with "Track 2 PR target".** `eastspire/euv` is a personal fork of `euv-dev/euv`. Pushing to `eastspire/euv` is Track 1 (personal repo, direct push). PRs from `eastspire/euv` go TO `euv-dev/euv` — that's a Track 2 PR. The repo you push to and the repo you PR from are different decisions.
2. **Always start a new feature branch from clean `upstream/master`**. Opening a branch from an unmerged PR's branch makes `gh pr diff` include that PR's commits in your new PR's diff. Recipe: `git checkout master && git pull upstream master && git checkout -b <new>`. Stack/dependent PRs (where one PR is intentionally the base of another) are the only exception — call it out in the PR body.
3. **The `gh pr create --head` value must be `eastspire:<branch>`** (owner-prefixed) when the head fork is under `eastspire`. Plain `<branch>` only works if there's no fork (i.e. you're pushing to upstream directly, rare).
4. **CI workflows in fork repos can't deploy Pages / push to crates.io** — they don't have the upstream's secrets. Gate deploy jobs with `if: github.repository == '<org>/<repo>'` or only run them on `push` events (PRs from forks have read-only tokens by design).
5. **Fork dispatch can't run `actions/deploy-pages@v4`** even on harmless `workflow_dispatch` triggers — the fork has no Pages deploy key. Same `if:` guard fixes it.
6. **Forgetting `gh repo fork --remote`** on an existing clone leaves you without an `upstream` remote and you'll accidentally push your branch straight into the upstream `master`. Verify with `git remote -v` immediately after fork.
7. **`fork` from `eastspire/*` to `eastspire/*` errors** ("Cannot fork a repository you own"). If you need a "fork" of your own repo for some reason, clone it under a different name — but you almost never need this.
8. **Use `--body-file` not `--body "..."`** — gh escapes backticks in inline strings and your fenced code blocks come out as plain text. `cat <<'EOF' > /tmp/pr-body.md` then `--body-file /tmp/pr-body.md`.
9. **Don't open PRs from a dirty worktree** — uncommitted `.pyc`, `__pycache__/`, or scratch files will land in the diff. Run `git status` before `git add -A`.
10. **`eastspire/*` forks used as upstream references** (`eastspire/euv`, `eastspire/serde`, `eastspire/clap`, etc. from `gh repo list eastspire`) are **Track 1** for pushing — but Track 2 for PRs. Push to the personal fork freely; open PRs from the fork back to the original (`euv-dev/euv`, `tokio-rs/serde`, `clap-rs/clap`).
11. **`docs-pages/*` was promoted from Track 2 to Track 1 on 2026-09-05** — don't reflexively reach for the "fork + PR" or "Contents API" flow when touching a docs-pages repo. Verify the track first with `git remote -v`. `docs-pages/pages` is still a Vercel build artifact and should not be edited directly — but it's now "Track 1, push directly" rather than "Track 2 with API workaround".
12. **`gh pr view N` stdout is often empty** with restricted-scope GH_TOKEN. Use `gh pr view N --json ...` or `gh api repos/<org>/<repo>/pulls/N` for reliable reads.
13. **`gh pr edit --title` silently fails** when token lacks `read:org` (GraphQL path). For renaming PRs, use REST: `curl -X PATCH -H "Authorization: token ***" https://api.github.com/repos/<org>/<repo>/pulls/<N> -d @payload.json`.
14. **`gh pr create --head owner:branch` fails with "Head ref must be a branch" / "Not all refs are readable"** when the head repo isn't registered as a fork in GitHub's graph — `gh repo create` makes an independent repo, NOT a fork, and the `parent` metadata is never set retroactively even after `git remote add upstream && git push upstream master`. Verify with `gh repo view <you>/<repo> --json parent`; if `parent == null` you need to delete + re-fork cleanly. See `github/github-repo-management` §11.2 (Independent repo vs fork), §11.3 (-N collision cleanup), §11.1 (`delete_repo` scope).

## Supersede flow (Track 2 only)

Already opened a PR but the scope grew? Don't open a second one — supersede:

```bash
gh pr close <N> --comment "Superseded by upcoming PR that bundles X+Y into one review."
git add <new-files>
git commit --amend --no-edit
git push --force origin <branch>           # --force (lease fails post-amend)
gh pr create --base master --head <branch> --title "..." --body-file /tmp/pr-body.md
```

Add `## Supersedes #N` to the new PR body. New PR number will increment.

## Append-to-existing-PR flow (Track 2 only, "在已有 PR 里更新")

User says: "直接在已有开的 PR 里更新代码就行" / "fix goes into PR #N" /
"append the fix to the open PR". Don't open a new PR, don't supersede — **commit
on top of the existing PR's head branch**:

```bash
# 1. Find the PR's head branch
gh pr view <N> --repo <org>/<repo> --json headRefName,headSha
# → headRefName: "perf/document-fragment-batch-append"

# 2. Checkout that branch (do NOT create a new branch)
git fetch origin <head-branch>
git checkout <head-branch>
git pull origin <head-branch> --rebase  # sync to remote head

# 3. Make all changes (fix + version bump etc.) and commit on top
git add <files>
git -c user.name=eastspire -c user.email=eastspire@users.noreply.github.com \
  commit -m "<type>(<scope>): <subject>

<body explains why, not what>"
git push origin <head-branch>   # no --force needed, just new commit on top

# 4. PR auto-updates; CI re-runs
gh pr checks <N> --repo <org>/<repo>
```

**When to use this** vs supersede vs new PR:

|| User intent | Action |
| --- | --- |
| "在已有 PR 里追加" / "fix goes into PR #N" / "在那个 PR 里更新一下" | **Append** (this section) |
| "scope 变了, supercede" / "合并这个, 重开一个" | Supersede (section above) |
| "开新 PR" / "单独发一个" | New PR (Track 2 standard flow) |
| 模糊 | Ask one clarifying question via `clarify`, don't guess |

**Anti-patterns caught in 2026-09 PR #146 + #147 incident** (closed #147 after
opening, then cherry-picked to #146 — wasted a close + new PR cycle):

- Created `fix/merge-class-cssref-drop` branch on top of `upstream/master`,
  opened PR #147, THEN realized user wanted fix in PR #146 → close #147, then
  cherry-pick to `perf/document-fragment-batch-append`. **Could have skipped
  the close by checking first** whether a fix-relevant PR was already open.
- `gh pr close --delete-branch` silently skips `--delete-branch` for fork-PRs
  (`! Skipped deleting the remote branch of a pull request from fork`); manual
  `git push origin --delete <branch>` is required after.

**Diagnostic**: before opening any new PR, **always**:

```bash
gh pr list --repo <org>/<repo> --state open --author @me --json number,title,headRefName,state
```

If a fix-relevant PR is already open → append. Otherwise → new PR.

## Commit message style (both tracks)

- English subject + body (per `rust-standards` §2.7 — applies to ALL GitHub-visible text)
- Conventional commit format: `<type>(<scope>): <subject>`
- Body explains the why, not the what