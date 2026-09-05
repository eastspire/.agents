---
name: github-pr-workflow
description: "GitHub PR lifecycle: branch, commit, open, CI, merge. NEVER auto-merge — agent must wait for the user to merge when downstream work depends on it. Includes fork-first path for no-write targets and tarball-to-PR recovery when only api.github.com works."
version: 1.5.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [GitHub, Pull-Requests, CI/CD, Git, Automation, Merge]
    related_skills: [github-auth, github-code-review]
---

# GitHub Pull Request Workflow

Complete guide for managing the PR lifecycle. Each section shows the `gh` way first, then the `git` + `curl` fallback for machines without `gh`.

## When to Use This Skill

Use this skill whenever the outcome is a PR — feature work, bugfix, docs update, refactor. Load it even for "just push this fix" requests, since the user may have a no-direct-push rule that makes the PR step mandatory (not optional). Quick decision tree:

- **You already have a local repo with `origin` set and write permission on it** → straight PR workflow.
- **You only have a tarball/working tree (no `.git/`), or you only have read access to the target repo** → see `## Tarball-Only and Read-Only Sources` below BEFORE doing anything.
- **The user said "禁止直接 push" / "no direct push" / "always via PR"** → treat as hard constraint, not a soft preference; do not push to the base branch even if you have write permission.
- **A green PR is ready to merge, or downstream work depends on it** → STOP. Post the "ready to merge" template and wait for the user to press the merge button. Never run `gh pr merge --auto` or `enablePullRequestAutoMerge`. See [Section 6](#6-merging).

## Prerequisites

- Authenticated with GitHub (see `github-auth` skill)
- Inside a git repository with a GitHub remote, OR following the tarball fallback below

### Quick Auth Detection

```bash
# Determine which method to use throughout this workflow
if command -v gh &>/dev/null && gh auth status &>/dev/null; then
  AUTH="gh"
else
  AUTH="git"
  # Ensure we have a token for API calls
  if [ -z "$GITHUB_TOKEN" ]; then
    if _hermes_env="${HERMES_HOME:-$HOME/.hermes}/.env"; [ -f "$_hermes_env" ] && grep -q "^GITHUB_TOKEN=" "$_hermes_env"; then
      GITHUB_TOKEN=$(grep "^GITHUB_TOKEN=" "$_hermes_env" | head -1 | cut -d= -f2 | tr -d '\n\r')
    elif grep -q "github.com" ~/.git-credentials 2>/dev/null; then
      GITHUB_TOKEN=$(uv run python "${HERMES_HOME:-$HOME/.hermes}/skills/github/github-auth/scripts/git-credential-token.py")
    fi
  fi
fi
echo "Using: $AUTH"
```

### Extracting Owner/Repo from the Git Remote

Many `curl` commands need `owner/repo`. Extract it from the git remote:

```bash
# Works for both HTTPS and SSH remote URLs
REMOTE_URL=$(git remote get-url origin)
OWNER_REPO=$(echo "$REMOTE_URL" | sed -E 's|.*github\.com[:/]||; s|\.git$||')
OWNER=$(echo "$OWNER_REPO" | cut -d/ -f1)
REPO=$(echo "$OWNER_REPO" | cut -d/ -f2)
echo "Owner: $OWNER, Repo: $REPO"
```

---

## 1. Branch Creation

This part is pure `git` — identical either way:

```bash
# Make sure you're up to date
git fetch origin
git checkout main && git pull origin main

# Create and switch to a new branch
git checkout -b feat/add-user-authentication
```

Branch naming conventions:
- `feat/description` — new features
- `fix/description` — bug fixes
- `refactor/description` — code restructuring
- `docs/description` — documentation
- `ci/description` — CI/CD changes

## 2. Making Commits

Use the agent's file tools (`write_file`, `patch`) to make changes, then commit:

```bash
# Stage specific files
git add src/auth.py src/models/user.py tests/test_auth.py

# Commit with a conventional commit message
git commit -m "feat: add JWT-based user authentication

- Add login/register endpoints
- Add User model with password hashing
- Add auth middleware for protected routes
- Add unit tests for auth flow"
```

Commit message format (Conventional Commits):
```
type(scope): short description

Longer explanation if needed. Wrap at 72 characters.
```

Types: `feat`, `fix`, `refactor`, `docs`, `test`, `ci`, `chore`, `perf`

## 3. Pushing and Creating a PR

### Push the Branch (same either way)

```bash
git push -u origin HEAD
```

### Create the PR

**With gh:**

```bash
gh pr create \
  --title "feat: add JWT-based user authentication" \
  --body "## Summary
- Adds login and register API endpoints
- JWT token generation and validation

## Test Plan
- [ ] Unit tests pass

Closes #42"
```

Options: `--draft`, `--reviewer user1,user2`, `--label "enhancement"`, `--base develop`

### With git + curl:

```bash
BRANCH=$(git branch --show-current)

curl -s -X POST \
  -H "Authorization: token $GITHUB_TOKEN" \
  -H "Accept: application/vnd.github.v3+json" \
  https://api.github.com/repos/$OWNER/$REPO/pulls \
  -d "{
    \"title\": \"feat: add JWT-based user authentication\",
    \"body\": \"## Summary\nAdds login and register API endpoints.\n\nCloses #42\",
    \"head\": \"$BRANCH\",
    \"base\": \"main\"
  }"
```

The response JSON includes the PR `number` — save it for later commands.

### Language for GitHub artifacts (English only)

All text shipped to GitHub must be English: PR title, PR body, commit message
(subject + body), issue title/body, PR review comments, branch name (use ASCII).
Agent-to-user chat replies stay in the user's preferred language; the rule is
about *artifacts a reviewer or contributor will read*, not about the agent's
conversational replies. Self-check before `gh pr create`:

```bash
grep -P "[\p{Han}]" /tmp/pr-body.md && echo "FAIL: Chinese chars in PR body" && exit 1
git log -1 --format=%B | grep -P "[\p{Han}]" && echo "FAIL: Chinese chars in commit message" && exit 1
```

### Editing a PR body after creation

`gh pr edit --body-file` goes through GraphQL and requires `read:org` scope on
the token; most fork PATs (the `notifications, repo, workflow` set common on
this host) will hit HTTP 422 instead of updating. Workaround via REST, which
only needs `repo`:

```bash
gh api -X PATCH repos/$OWNER/$REPO/pulls/$PR_NUMBER \
  -f body="$(cat /tmp/pr-body.md)"
```

PR title is updated the same way (`-f title=...`). **Commit message already
pushed to GitHub cannot be force-edited** — that requires a `git commit
--amend` plus force-with-lease push, or a rebase. So the commit-message
English rule has to be checked *before* the commit lands, not after.

### Writing the commit message before `git commit`

Conventional Commits format with English-only body:

```bash
git commit -m "speed(euv_playground): use s/thin release profile instead of z+lto+codegen-units=1

The playground build was configuring Cargo.toml with the slowest
combination for both dev and release profiles:

  opt-level = \"z\"
  lto = true
  codegen-units = 1
  incremental = false
  debug = false

wasm-pack build --release then runs wasm-opt -Oz on the output,
so cargo-side z+lto+1 is redundant work and dominates build time
without measurable size benefit.

Replaces with profiles that match cargo's default-but-constrained
shape:

  [profile.dev]      opt-level = 0, debug = true, incremental = true, codegen-units = 256
  [profile.release]  opt-level = \"s\", lto = \"thin\", codegen-units = 16, debug = false, strip = \"symbols\""
```

Wrap body lines at 72 chars, lead verb forms (`Replaces with...`, `Drops ...`),
no trailing period.

To create as a draft, add `"draft": true` to the JSON body.

### Creating a PR From a Tarball (no local git history)

If you only have a downloaded tarball or working tree — no `.git/` directory — you cannot `git push` because there is no branch, no remote, and no commit graph. The fix is to re-create the history before pushing:

```bash
# 1. Get a real git repo by either re-cloning or init-from-tarball
# Option A: clone if network permits
git clone https://github.com/<owner>/<repo>.git ./repo
# Option B: init from an existing tarball (only when clone is impossible)
cd ./repo
# IMPORTANT: tarball doesn't carry history — do NOT claim to preserve upstream history
git init && git remote add origin git@github.com:<your-fork>/<repo>.git
# Pull the actual history from origin to populate .git/, then layer your changes on top
git fetch origin
git checkout -b feat/my-change origin/main  # or: git pull origin main --allow-unrelated-histories
# Restore your tarball changes on top of the fetched history
# ...then add, commit, push, PR
```

Once you have a real `git` repo with the base branch checked out, continue with the normal `git push -u origin HEAD` flow above.

### Eastspire-Owned Orgs — Skip the Fork Decision (2026-09-05 revision)

When the target repo belongs to an org where the user (`eastspire`) has admin/maintain permission, the workflow depends on the org:

| Org | Workflow | Why |
| --- | --- | --- |
| `eastspire/*` (personal) | **Direct push to master, no fork, no PR** | Self-account; PR review would be self-approval |
| `docs-pages/*` | **Direct push to master, no fork, no PR** (2026-09-05) | eastspire is the entire admin team; no external reviewers |
| `euv-dev/*` | Branch + push direct (upstream) + open PR | eastspire is admin, but each repo has a non-eastspire maintainer |
| `hyperlane-dev/*` | same as `euv-dev/*` | same |
| `crates-dev/*` | same as `euv-dev/*` | same |
| Third-party (e.g. `tokio-rs/serde`) | `gh repo fork` + branch + push to fork + open PR | eastspire has no admin role |

```bash
# 1. (optional but cheap) verify track via remote + owner
git remote -v
# origin ssh://git@github.com/<owner>/<repo>.git
# If <owner> in {eastspire, docs-pages} → Track 1 (push master)
# If <owner> in {euv-dev, hyperlane-dev, crates-dev} → Track 2 (branch + push + PR)
# Else → Track 2 via gh repo fork

# Optional: API permission check for Track 2
PERM=$(gh api repos/<owner>/<repo>/collaborators/eastspire/permission --jq .permission 2>/dev/null)
case "$PERM" in
  admin|maintain|write) echo "✓ $PERM — direct branch push OK (Track 2)" ;;
  *)                   echo "⚠ $PERM — fall back to gh repo fork path" ;;
esac

# 2a. Track 1 — personal + docs-pages
git add -A
git -c user.name=eastspire -c user.email=eastspire@users.noreply.github.com commit -m "..."
git push origin master

# 2b. Track 2 — eastspire-owned org with active maintainer OR third-party
git checkout -b <scope>/<descr>-YYYY-MM-DD origin/master
# ... make changes, git commit ...
git push -u origin <branch>
gh pr create --base master --head <branch> --title "..." --body-file /tmp/pr-body.md
```

Why this matters: `gh repo fork` on a user-owned repo fails with `cannot be forked. A single user account cannot own both a parent and fork` (verified on `eastspire/.agents`). For the three maintainer-orgs (`hyperlane-dev`, `crates-dev`, `euv-dev`), forking either errors out or produces a meaningless same-account fork — so always push the branch direct to upstream and open the PR from there. For `docs-pages/*` specifically, **don't open a PR at all** as of 2026-09-05; the user confirmed the docs site is fully self-administered and the PR ceremony is pure overhead.

For the full decision tree see `gh-pr-creation-workflow`. For the historical context of `docs-pages` having a Contents-API workaround (pre-2026-09-05), see the older revisions of this file or `gh-pr-creation-workflow` §"Exception". The exception is no longer needed.

### Cross-Org / No-Write Permission (the "fork first" path)

You cannot push to a branch on a repo you lack write permission to — typical when the user account has push rights only to their own fork, not to the upstream organization. Steps:

```bash
# 1. Fork the upstream repo to the user's account (UI button OR API)
gh repo fork <owner>/<repo> --clone   # with gh
# or via API: POST /repos/<owner>/<repo>/forks
# 2. Add upstream as a separate remote so you can sync later
git remote add upstream https://github.com/<owner>/<repo>.git
# 3. Push the branch to YOUR fork, NOT upstream
git push -u origin HEAD
# 4. Open the PR against the upstream base
gh pr create --base main --head <user>:<branch>
# or: POST /pulls with head="<user>:<branch>", base="main"
```

Stop and ask the user if you don't know whether they have push rights to the target repo. Trying to push and failing wastes a turn on the same diagnostic.

### Fork Disabled — Direct Branch Push (when you already have write access)

Some orgs disable forks entirely (`POST /repos/<o>/<r>/forks` returns 403 "forking is disabled"). When the user's account is admin/owner of the upstream, the fork path is moot anyway — skip it and push straight to the upstream:

```bash
# Confirm your permission level BEFORE pushing
gh api repos/<owner>/<repo>/collaborators/<user>/permission --jq .permission
# Expected: "admin" / "maintain" / "write". Anything else means you can't push here.

# Create a new branch on the upstream directly (ref-based, no clone needed)
MASTER_SHA=$(gh api repos/<owner>/<repo>/commits/<base-branch> --jq .sha)
gh api -X POST repos/<owner>/<repo>/git/refs \
  -f ref="refs/heads/<branch>" \
  -f sha="$MASTER_SHA"

# Now upload your file changes to that branch via the Contents API
# (see references/github-api-file-upload.md — this is how you avoid clone stalls)
# ...

# Open the PR with the upstream branch as head
gh pr create --repo <owner>/<repo> --head <branch> --base <base-branch>
```

This is the right path when:
- The target repo is private (forks of private repos are still blocked on free orgs) **or** the org has "forking is disabled" in settings
- The user's account has admin/maintain/write on the upstream
- The tarball would be too slow to clone (`codeload.github.com` 1–2 MB/min on a 200MB repo = 100+ minutes; SSH `index-pack` at 24 KiB/s = even worse)

See `references/github-api-file-upload.md` for the Contents API recipe that makes this work without `git clone`.

## 4. Monitoring CI Status

### Check CI Status

**With gh:**

```bash
# One-shot check
gh pr checks

# Watch until all checks finish (polls every 10s)
gh pr checks --watch
```

**With git + curl:**

```bash
# Get the latest commit SHA on the current branch
SHA=$(git rev-parse HEAD)

# Query the combined status
curl -s \
  -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/repos/$OWNER/$REPO/commits/$SHA/status \
  | python -c "
import sys, json
data = json.load(sys.stdin)
print(f\"Overall: {data['state']}\")
for s in data.get('statuses', []):
    print(f\"  {s['context']}: {s['state']} - {s.get('description', '')}\")"

# Also check GitHub Actions check runs (separate endpoint)
curl -s \
  -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/repos/$OWNER/$REPO/commits/$SHA/check-runs \
  | python -c "
import sys, json
data = json.load(sys.stdin)
for cr in data.get('check_runs', []):
    print(f\"  {cr['name']}: {cr['status']} / {cr['conclusion'] or 'pending'}\")"
```

### Poll Until Complete (git + curl)

```bash
# Simple polling loop — check every 30 seconds, up to 10 minutes
SHA=$(git rev-parse HEAD)
for i in $(seq 1 20); do
  STATUS=$(curl -s \
    -H "Authorization: token $GITHUB_TOKEN" \
    https://api.github.com/repos/$OWNER/$REPO/commits/$SHA/status \
    | python -c "import sys,json; print(json.load(sys.stdin)['state'])")
  echo "Check $i: $STATUS"
  if [ "$STATUS" = "success" ] || [ "$STATUS" = "failure" ] || [ "$STATUS" = "error" ]; then
    break
  fi
  sleep 30
done
```

## 5. Auto-Fixing CI Failures

When CI fails, diagnose and fix. This loop works with either auth method.

### Step 1: Get Failure Details

**With gh:**

```bash
# List recent workflow runs on this branch
gh run list --branch $(git branch --show-current) --limit 5

# View failed logs
gh run view <RUN_ID> --log-failed
```

**With git + curl:**

```bash
BRANCH=$(git branch --show-current)

# List workflow runs on this branch
curl -s \
  -H "Authorization: token $GITHUB_TOKEN" \
  "https://api.github.com/repos/$OWNER/$REPO/actions/runs?branch=$BRANCH&per_page=5" \
  | python -c "
import sys, json
runs = json.load(sys.stdin)['workflow_runs']
for r in runs:
    print(f\"Run {r['id']}: {r['name']} - {r['conclusion'] or r['status']}\")"

# Get failed job logs (download as zip, extract, read)
RUN_ID=<run_id>
curl -s -L \
  -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/repos/$OWNER/$REPO/actions/runs/$RUN_ID/logs \
  -o /tmp/ci-logs.zip
cd /tmp && unzip -o ci-logs.zip -d ci-logs && cat ci-logs/*.txt
```

### Step 2: Fix and Push

After identifying the issue, use file tools (`patch`, `write_file`) to fix it:

```bash
git add <fixed_files>
git commit -m "fix: resolve CI failure in <check_name>"
git push
```

### Step 3: Verify

Re-check CI status using the commands from Section 4 above.

### Auto-Fix Loop Pattern

When asked to auto-fix CI, follow this loop:

1. Check CI status → identify failures
2. Read failure logs → understand the error
3. Use `read_file` + `patch`/`write_file` → fix the code
4. `git add . && git commit -m "fix: ..." && git push`
5. Wait for CI → re-check status
6. Repeat if still failing (up to 3 attempts, then ask the user)

## 6. Merging

> **⛔ Auto-merge is OFF by default. NEVER run `gh pr merge --auto`, `enablePullRequestAutoMerge`, or any other path that merges without explicit per-PR approval, unless the user has typed a clear "merge it" / "go ahead" instruction for THAT specific PR in the current session.**
>
> The user owns merge decisions. Auto-merge removes that gate and can race ahead of CI, force-push a reviewer's expectations, or merge a PR the user wanted to amend. See [Pitfall: Auto-merging PRs](#pitfall-auto-merging-prs) for the full rule and the "wait-for-merge" workflow.

**The agent's job ends at "PR is green and ready"** — preparing the squash, deleting the source branch afterwards, syncing the local base branch, etc., are all things to do **after** the user confirms merge. Do not pre-merge.

When the user gives an explicit "merge it" / "go ahead and merge" instruction, then — and only then — use the commands below.

**With gh** (only when the user has explicitly asked for the merge):

```bash
# Squash merge + delete branch (cleanest for feature branches)
gh pr merge --squash --delete-branch

# Plain merge commit (preserve history)
gh pr merge --merge --delete-branch

# Rebase merge
gh pr merge --rebase --delete-branch
```

**With git + curl** (only when the user has explicitly asked for the merge):

```bash
PR_NUMBER=<number>

# Merge the PR via API (squash)
curl -s -X PUT \
  -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/repos/$OWNER/$REPO/pulls/$PR_NUMBER/merge \
  -d "{ \
    \"merge_method\": \"squash\", \
    \"commit_title\": \"feat: add user authentication (#$PR_NUMBER)\" \
  }"

# Delete the remote branch after merge
BRANCH=$(git branch --show-current)
git push origin --delete $BRANCH

# Switch back to main locally
git checkout main && git pull origin main
git branch -d $BRANCH
```

Merge methods: `"merge"` (merge commit), `"squash"`, `"rebase"`

### Pitfall: Auto-Merging PRs

**Treat `gh pr merge --auto` / `enablePullRequestAutoMerge` as forbidden
unless the user has typed a "merge it" / "go ahead" instruction for the
specific PR you're about to open.** Auto-merge removes the gate and can
race ahead of CI, force-push a reviewer's expectations, or merge a PR the
user wanted to amend.

The classic failure mode is **downstream work depending on the merge**:

1. Agent opens PR #42 with `feat: add v2 API endpoint`.
2. Agent then starts working on PR #43 that *uses* the v2 endpoint — pulling from `master`, hitting a `use of undeclared crate` error.
3. Agent either (a) silently gives up on PR #43, (b) rebases PR #43 onto PR #42's branch and bundles them, or (c) force-merges PR #42 via `--auto` to "unstick" itself.
4. None of those is what the user wanted. They wanted a review window between #42 and #43.

**Correct sequence when a PR is "ready but not merged"** and downstream work needs it:

1. `gh pr checks <N>` → all green.
2. Post a single-line summary to the user: *"PR #42 is green (CI: ✓). Ready to merge — say the word and I'll clean up the source branch, or I can start PR #43 on a fresh base now and rebase it once #42 lands."*
3. **Stop and wait.** Do not run `gh pr merge` of any flavor.
4. If the user replies "merge it" / "go ahead" → run the merge block above.
5. If the user replies "start #43 anyway" → proceed with the new branch off the current base; remember to rebase or merge `master` into it once #42 lands.

### User-Opted-In `--auto` Workflow (when the repo allows it)

Some repos — verified 2026-08-30 on `euv-dev/euv-docs`, `eastspire/euv-docs`,
plus all the user's `euv-dev/*` projects — have `allow_auto_merge=true`
set as a long-standing repo preference (see memory entry
"代码工作流 / PR 提交流程"). When this is set:

- `gh pr create --auto --squash --delete-branch` will queue the PR to
  auto-merge as soon as required status checks pass, and delete the
  source branch once it lands.
- This is the user's *preferred* workflow for routine CI fixes where
  there's no human review expected and the change is straightforward
  (rename a branch reference, bump a dep, fix a typo).
- **Always verify the repo has `allow_auto_merge=true` before using
  `--auto`** — `gh repo view $REPO --json allowAutoMerge` (or via
  REST `gh api repos/$REPO --jq .allow_auto_merge`). If the repo does
  NOT allow it, `--auto` is silently a no-op and the PR sits open
  waiting for manual merge — confusing to the user.
- For higher-stakes PRs (cross-cutting refactors, anything that
  touches public APIs, anything breaking ABI/behavior), default to the
  "stop at green, wait for user" flow regardless of `--auto`. A 60-second
  pause beats a 60-minute revert.

Enable on a repo:

```bash
gh api -X PATCH repos/$OWNER/$REPO -f allow_auto_merge=true
gh api -X PATCH repos/$OWNER/$REPO -f delete_branch_on_merge=true
```

### Reporting "ready to merge" to the user

Use this template when stopping at green:

```text
PR #<N> ready to merge: <title>
  • Branch: <branch> → <base>
  • CI: <gh pr checks summary>
  • Files: +<add>/-<del> across <N> files
  • Reviewers: <list, or "none requested yet">
Awaiting your "go ahead" before merging.
```

Do **not** post "merged #42" until the user has approved and the merge API call has returned 200 OK with a non-null `merged: true` in the response body.

## 7. Complete Workflow Example

```bash
# 1. Start from clean main
git checkout main && git pull origin main

# 2. Branch
git checkout -b fix/login-redirect-bug

# 3. (Agent makes code changes with file tools)

# 4. Commit
git add src/auth/login.py tests/test_login.py
git commit -m "fix: correct redirect URL after login

Preserves the ?next= parameter instead of always redirecting to /dashboard."

# 5. Push
git push -u origin HEAD

# 6. Create PR (picks gh or curl based on what's available)
# ... (see Section 3)

# 7. Monitor CI (see Section 4)

# 8. Stop at green and report to the user (see Section 6 — NEVER auto-merge)
```

## 7a. Multi-PR Workflow — When a PR blocks the next one

When the agent is working through a sequence of PRs (PR #N+1 depends on PR #N being merged), do NOT auto-merge #N to "unstick" #N+1. The default is:

1. Open PR #N with full diff + CI green.
2. Report: "PR #N is green. Ready to merge. Awaiting your go-ahead before I start PR #N+1, which depends on #N landing."
3. **Wait for the user to merge #N themselves** (or give explicit "merge it" instruction).
4. Once #N is merged, `git fetch origin && git rebase origin/master` on the local base, then proceed with #N+1.

If the user prefers a tighter loop ("just merge them all in sequence and report at the end"), they will say so explicitly — capture that as an exception in the response and still report between merges, just batched. Do **not** infer "tighten up" from silence.

## Useful PR Commands Reference

| Action | gh | git + curl |
|--------|-----|-----------|
| List my PRs | `gh pr list --author @me` | `curl -s -H "Authorization: token $GITHUB_TOKEN" "https://api.github.com/repos/$OWNER/$REPO/pulls?state=open"` |
| View PR diff | `gh pr diff` | `git diff main...HEAD` (local) or `curl -H "Accept: application/vnd.github.diff" ...` |
| Add comment | `gh pr comment N --body "..."` | `curl -X POST .../issues/N/comments -d '{"body":"..."}'` |
| Request review | `gh pr edit N --add-reviewer user` | `curl -X POST .../pulls/N/requested_reviewers -d '{"reviewers":["user"]}'` |
| Close PR | `gh pr close N` | `curl -X PATCH .../pulls/N -d '{"state":"closed"}'` |
| Check out someone's PR | `gh pr checkout N` | `git fetch origin pull/N/head:pr-N && git checkout pr-N` |

## Pitfalls

- **Editing the build product, not the source.** Before you open a PR that touches `*.html`, check whether the repo is a Vercel/Netlify/Cloudflare Pages auto-deploy target. `package.json` referencing `vuepress build src` / `next build && next export` / `hugo` / `mkdocs build`, plus commit messages matching `Deploy from @<sha>`, are the giveaways. Those HTML files get overwritten on every deploy — your diff will vanish. Always edit the source repo (markdown / source files), not the rendered output. See `references/build-product-vs-source-repo.md` for the full diagnostic.
- **Pushing to a repo you only have read access to.** `git push` returns 403 with "Permission denied". Always check `gh repo view <owner>/<repo> --json viewerPermission` (or `GET /repos/<owner>/<repo>` `permissions.pull`) before pushing; if you only have `read`, the fork-first path is the only option.
- **Trying to fork a repo where forking is disabled.** Many orgs turn this off in settings, and private repos often can't be forked on free orgs. `POST /repos/<o>/<r>/forks` returns 403 with "forking is disabled". If the user is admin/owner of the upstream, skip the fork entirely and push to a new branch on the upstream directly — see the "Fork Disabled" recipe below.
- **Trying to PR from a tarball-only working tree.** `git push` fails with "not a git repository" or "no upstream branch". A tarball has no commit graph — re-clone (preferred) or `git init` + `git fetch origin` first.
- **Treating the user's "no direct push" rule as soft.** If they said "禁止直接 push" / "always via PR", that is the policy. Do not push to base/main even when you have write access — branch, commit, push branch, open PR.
- **`git push` over HTTPS hangs even when SSH works.** On GFW-throttled hosts, HTTPS `github.com` smart-HTTP can stall indefinitely on push (handshake succeeds, then nothing). **SSH push to the same repo is fast** — odd but observed. If `git push https://...` is stuck, switch the remote to SSH: `git remote set-url origin git@github.com:<o>/<r>.git` and retry.
- **codeload.github.com single-connection bandwidth is heavily throttled on GFW-blocked hosts.** A 50–200MB tarball can take 30–45 min at 1–2 MB/min. If `wget`/`curl` keeps getting `HTTP/2 stream CANCEL` or `Recv failure`, retry with `wget --tries=infinite --waitretry=3 --read-timeout=60` instead of `curl` (single-connection retries less aggressively). SSH `git clone` to the same host is usually *slower* than HTTPS tarball under throttling (24 KiB/s observed), so prefer the tarball.
- **GitHub rate limits Contents API hard.** Single-file `PUT /repos/<o>/<r>/contents/<path>` counts as one request; bulk edits of N files can hit the 5000/hour limit on personal tokens. For multi-file doc sync, batch into a single commit if the API allows, or pace your calls. See `references/github-api-file-upload.md`.
- **Pushing without checking the base branch.** `git push -u origin HEAD` defaults to whatever upstream says; on a freshly forked repo that may be `master`, not `main`. Verify with `git symbolic-ref refs/remotes/origin/HEAD` before opening the PR, and pass `--base` explicitly when creating the PR.
- **Using `gh` for `gh api` when only `gh auth login` works for HTTPS but SSH keys are also configured.** Pick one mode and stay in it — mixing auth modes mid-workflow leaks credentials into shell history or kills the agent's auth on rotation.
- **Reporting "PR opened" without checking the response.** `gh pr create` returns the PR URL on success and exits non-zero on failure (e.g., "no history in common with base"). Always read the actual output, not the exit code, before claiming success.
- **Auto-merging a PR because the next task depends on it.** Default state is "stop at green, wait for the user to press the merge button". Never run `gh pr merge --auto`, `gh pr merge --squash`, or `enablePullRequestAutoMerge` unless the user has *just now* typed something like "merge it" / "go ahead" / "approve and merge". When the next task needs a PR to land first, post a "PR #N ready to merge, awaiting your go-ahead" report and stop — do not unstick yourself by force-merging or rebasing the next branch onto the still-open one. Full rule in [Section 6 § Pitfall: Auto-Merging PRs](#6-merging) and [Section 7a](#7a-multi-pr-workflow--when-a-pr-blocks-the-next-one).
- **`gh auth status` reports "not logged in" even though the user has `GH_TOKEN` working in their own terminal.** The token is set in `~/.bashrc` / `~/.profile` and the agent's `terminal()` runs a non-login, non-interactive shell that doesn't source those files. Don't waste a turn re-asking the user to set up auth — instead source the profile and re-run, or stash a wrapper like `/tmp/with-gh-env.sh` that does `source ~/.bashrc ~/.profile; exec "$@"`. Full recipe (detection probe + wrapper + why not to fix the global env) lives in the `github-auth` skill under "Pitfall: `GH_TOKEN` set in `~/.bashrc` / `~/.profile` but invisible to `gh`".
- **`gh api /repos/<o>/<r>/branches` only returns protected/default branches.** Default `/branches` endpoint omits regular feature/chore branches and silently hides the branches you actually came to inspect. Always use `/git/refs/heads` to enumerate ALL branch heads:
  ```bash
  gh api repos/<owner>/<repo>/git/refs/heads \
    | python3 -c "import sys,json; d=json.load(sys.stdin); [print(b['ref']) for b in d]"
  ```
  This matters when the user asks you to "delete all non-master branches" or audit a repo — using `/branches` will report a false "only master exists" and you'll miss everything you should have deleted. Confirmed 2026-08-29 on `euv-dev/euv`: `/branches` returned only `master`, but `/git/refs/heads` revealed `chore/bump-0-17-1-2026-08-29` and `fix/macros-publish-dev-dep-2026-08-27` that had to be deleted.
- **"Source repo" vs "fork" branch cleanup — fork is NOT in scope.** When the user says "clean up branches under org X" they mean the *source* repos under that org (`X/<repo>`), not your personal fork (`<user>/<repo>`). Forks live in the user's personal namespace and have their own branch lifecycle. Before `git push <remote> --delete <branch>`, run `git remote -v` to confirm which remote is the source of truth: typically `origin` = fork, `upstream` = source. Verified 2026-08-29: I deleted a `chore/bump-deps-*` branch on `eastspire/euv-docs` thinking it was the source, but the actual source was `euv-dev/euv-docs` (no such branch there) and the fork had inherited it from a prior PR. Cross-check the target org on GitHub (`gh api repos/<owner>/<repo>`) before deleting.
- **Personal/admin repos: push directly to master, never via PR.** As of 2026-09-05 the rule covers both `eastspire/*` (personal) AND `docs-pages/*` (admin-owned docs). `gh repo fork <personal-repo>` fails with "cannot be forked. A single user account cannot own both a parent and fork". For these repos, always commit + `git push origin master` directly (after a quick `git fetch origin && git reset --hard origin/master` to make sure your local `master` matches the remote). If your edits were on a different local branch with other sessions' working-tree noise mixed in, use `git stash push -m "wip-not-mine"` → `git checkout master` → `git reset --hard origin/master` → `git cherry-pick <only-your-sha>` → `git push origin master` → `git branch -D <branch>` → `git stash pop`. Cherry-pick conflicts: use `git show <sha>:<file> > /tmp/v && cp /tmp/v <file> && git add` to take your version verbatim. For `euv-dev`/`hyperlane-dev`/`crates-dev`/third-party, this pitfall does NOT apply — those still need branch + PR.

## Related References

- `references/gfw-throttled-github-fetch.md` — when `codeload.github.com` and `raw.githubusercontent.com` are heavily throttled or blocked but `api.github.com` and `git@github.com` work. Covers `wget` retry recipe, `api.github.com/contents` + base64 fallback for reading raw files, and why tarballs are NOT git repos (implications for PR workflows).
- `references/build-product-vs-source-repo.md` — when the repo you're about to edit is a Vercel/Netlify/Cloudflare Pages auto-deploy target. Why editing the rendered HTML is wasted work, how to identify the source repo, and what to do instead.
- `references/github-api-file-upload.md` — Contents API (`PUT /repos/<o>/<r>/contents/<path>`) recipe for uploading file changes without `git clone`. Used when the repo is too large to clone in the time budget, or forking is disabled and you must push straight to the upstream.

---

## Build Product vs Source Repository

A category of repos you should NOT push to without first checking what they are: **auto-deployed documentation sites**. The pattern:

```
<org>/<docs-source-repo>     (private, often) — VuePress/Docusaurus/Hugo/MkDocs sources
                                     ↓ yarn build / npm run build / hugo / mkdocs build
                                     ↓ output → <build-output-dir>
                                     ↓ Vercel/Netlify/Cloudflare Pages auto-commit
<org>/<build-product-repo>   (often public, named like "...-pages", "site", "www") — static HTML + assets
```

The build product repo has `*.html` only — no markdown sources, no `package.json`, no `_config.yml`. It exists because the hosting platform needs a public, history-tracked place to push rendered artifacts.

### How to detect a build-product repo (cheap heuristics)

1. `GET https://api.github.com/repos/<o>/<r>/contents` — if the listing is `*.html` / `assets/` / `sitemap.xml` / `robots.txt` / `404.html` and **zero** markdown sources / `package.json` / build configs, it's almost certainly the output side.
2. `GET /repos/<o>/<r>/commits` — commit messages matching `Deploy from @<sha>` (Vercel), `Deploy <id>` (Netlify), or `pages build` (Cloudflare Pages) are deployment-bot signatures.
3. If the repo has a private sibling in the same org (e.g., `docs-pages/docs` private + `docs-pages/pages` public), the private one is almost certainly the source — fetch its `package.json` / `.vuepress/` / `_config.yml` to confirm.

### Why "just edit the HTML" is the wrong move

- The next auto-deploy will overwrite your HTML changes with the freshly built output.
- Your reviewer sees a 50,000-character HTML diff with shiki highlight spans and inline CSS — high signal-to-noise ratio, hard to review.
- The source repo (where humans actually edit) goes out of sync with the public site the moment your PR merges.

### What to do instead

- Identify the **source repo** (the private sibling, or the repo with `package.json` / `*.md` / `_config.yml`).
- Open your PR against the **source** repo, in the markdown / config file that the build pipeline consumes.
- After merge, the auto-deploy will produce the HTML — your changes appear on the live site without you touching the HTML repo.

### Edge cases

- The source repo is private and you only have read access on it: same Contents-API-without-clone recipe applies (next section). You don't need clone access if the repo is small enough to PUT file-by-file.
- The repo really is single-repo (no source sibling) but still auto-deployed: it must be a static site generator with `*.md` IN the same repo as the build output. Look for `vuepress build src` in scripts — the `src/` directory is the source, the rest is generated.
- The repo is hand-maintained HTML with no auto-deploy (an old GitHub Pages setup): treat it like a normal repo and edit the HTML.
