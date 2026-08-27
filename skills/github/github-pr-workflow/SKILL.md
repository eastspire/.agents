---
name: github-pr-workflow
description: "GitHub PR lifecycle: branch, commit, open, CI, merge. Includes fork-first path for no-write targets and tarball-to-PR recovery when only api.github.com works."
version: 1.2.0
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

### Eastspire-Owned Orgs — Skip the Fork Decision

When the target repo belongs to an org where the user (`eastspire`) has admin/maintain permission, **always push directly to a new branch on the upstream** — do not even try `gh repo fork`. The 4 orgs this applies to (verified 2026-08):

- `hyperlane-dev/*` — hyperlane framework
- `crates-dev/*` — Rust crates release
- `euv-dev/*` — euv framework
- `docs-pages/*` — docs (note: fork disabled on most private repos here, but Contents/git-refs API + direct branch push still works)

```bash
# 1. (optional but cheap) verify permission before pushing — 1 API call
PERM=$(gh api repos/<owner>/<repo>/collaborators/eastspire/permission --jq .permission 2>/dev/null)
case "$PERM" in
  admin|maintain|write) echo "✓ $PERM — direct push OK" ;;
  *)                   echo "⚠ $PERM — switch to fork-first path below" ;;
esac

# 2. Branch + commit + push straight to upstream
git checkout -b <scope>/<descr>-YYYY-MM-DD origin/master
# ... make changes, git commit ...
git push -u origin <branch>

# 3. Open PR
gh pr create --base master --head <branch> --title "..." --body-file /tmp/pr-body.md
```

Why this matters: `gh repo fork` on a user-owned repo fails with `cannot be forked. A single user account cannot own both a parent and fork` (verified on `eastspire/.agents`). For other eastspire-owned orgs (`hyperlane-dev`, `crates-dev`, `euv-dev`, `docs-pages`), forking either errors out or produces a meaningless same-account fork. Always check the org first; if it's one of these four, skip fork entirely.

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

**With gh:**

```bash
# Squash merge + delete branch (cleanest for feature branches)
gh pr merge --squash --delete-branch

# Enable auto-merge (merges when all checks pass)
gh pr merge --auto --squash --delete-branch
```

**With git + curl:**

```bash
PR_NUMBER=<number>

# Merge the PR via API (squash)
curl -s -X PUT \
  -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/repos/$OWNER/$REPO/pulls/$PR_NUMBER/merge \
  -d "{
    \"merge_method\": \"squash\",
    \"commit_title\": \"feat: add user authentication (#$PR_NUMBER)\"
  }"

# Delete the remote branch after merge
BRANCH=$(git branch --show-current)
git push origin --delete $BRANCH

# Switch back to main locally
git checkout main && git pull origin main
git branch -d $BRANCH
```

Merge methods: `"merge"` (merge commit), `"squash"`, `"rebase"`

### Enable Auto-Merge (curl)

```bash
# Auto-merge requires the repo to have it enabled in settings.
# This uses the GraphQL API since REST doesn't support auto-merge.
PR_NODE_ID=$(curl -s \
  -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/repos/$OWNER/$REPO/pulls/$PR_NUMBER \
  | python -c "import sys,json; print(json.load(sys.stdin)['node_id'])")

curl -s -X POST \
  -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/graphql \
  -d "{\"query\": \"mutation { enablePullRequestAutoMerge(input: {pullRequestId: \\\"$PR_NODE_ID\\\", mergeMethod: SQUASH}) { clientMutationId } }\"}"
```

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

# 8. Merge when green (see Section 6)
```

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
