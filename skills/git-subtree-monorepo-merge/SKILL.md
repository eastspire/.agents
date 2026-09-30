---
name: git-subtree-monorepo-merge
description: Merge N repos into one monorepo via git subtree.
when_to_use: merge N git repos into one monorepo / subtree add multiple crates / consolidate repos preserving history / monorepo from upstream fleet / fork fleet into one workspace / git subtree pull to consolidate
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [GitHub, Git, Monorepo, Subtree]
    related_skills: [github-pr-workflow, github-repo-management]
---

# Git Subtree Monorepo Merge

Consolidate N related repositories (crates, services, libraries, plugins) into a single monorepo where each becomes `subdir/<name>/`. Use `git subtree add` so upstream history stays reachable — `git subtree pull` later syncs new upstream commits.

## When to use this vs other approaches

| Approach | History | Future sync | Best for |
|---|---|---|---|
| `git subtree add` (this skill) | preserved | `git subtree pull` | Long-lived monorepo, regular upstream sync expected |
| `git merge` of N clones | preserved (messy) | manual | Repos share a common ancestor (rare) |
| Copy files only | lost | impossible | Throwaway aggregation only |
| Submodules | preserved | `git submodule update` | When each subdir must stay a real working repo |

For a Cargo workspace / npm workspaces / polyglot monorepo where subdirs are NOT separately published — subtree.

## Procedure

### Phase 1 — Recon (don't skip)

1. Confirm token works: `curl -s -H "Authorization: token ***" https://api.github.com/user | jq -r .login`. If `GH_TOKEN` is empty, get one from `gh auth token` or `git credential fill` — see Token discovery at end.
2. Verify target org/user exists with a valid token. Empty-token requests return 401 for ALL paths, masking 404; never use 401 to conclude "org doesn't exist."
3. List target repos: `GET /orgs/<ORG>/repos?per_page=100&type=all` (private + public).
4. Scan name collisions on the OWNER where the new repo will live:
   - `GET /user/repos?per_page=100` (paginate) — your existing repo names.
   - For each candidate monorepo name, check: not in your repo list, not already a user/org on GitHub (`/users/<name>` + `/orgs/<name>` both 404).
   - Owner-scoped repo name (`<owner>/<name>`) is a SEPARATE namespace from `<name>` user/org — existing `/users/<name>` does NOT block `<owner>/<name>`.

### Phase 2 — Clone upstream repos

`git clone --quiet <url>` per repo. Branch fallback: each upstream may use `master` or `main`; detect from `default_branch` field in the API response, not by hardcoding.

Run clones in parallel via `concurrent.futures.ThreadPoolExecutor(max_workers=4)` in Python (urllib + subprocess). 4 workers is the sweet spot — beyond that, GitHub rate-limits; below that, you waste wall time on a fleet of 20+ repos.

```python
from concurrent.futures import ThreadPoolExecutor, as_completed
import subprocess
results = []
with ThreadPoolExecutor(max_workers=4) as ex:
    futs = {ex.submit(clone_one, repo): repo for repo in repos}
    for f in as_completed(futs):
        results.append(f.result())
```

For each repo, try upstream URL first, fall back to your personal fork if upstream is unreachable.

### Phase 3 — Decide delivery mode BEFORE you touch the remote

Pick ONE and stick to it — mixing is bad hygiene:

| Mode | When | Git history on master |
|---|---|---|
| Force-push | Personal scratch repo, no review needed | Each subtree commit visible (1688 commits for a 21-crate fleet) |
| Feature branch + PR + squash-merge | Org repo, want audit trail, want PR numbers in master log | 1 squash commit per PR, references (#N) in commit message |

Default to PR-flow unless the user explicitly says otherwise — preserves history, leaves a reviewable record, matches open-source convention.

### Phase 4 — Create the monorepo

```bash
# Always set default_branch explicitly. auto_init defaults to "main".
curl -s -X POST -H "Authorization: token $GH_TOKEN" https://api.github.com/orgs/<OWNER>/repos \
  -d '{"name":"<name>","description":"...","private":false,"auto_init":true,"default_branch":"master","license_template":"mit"}'
```

`auto_init: true` trap: omitting `default_branch` creates the repo with `main` even when your project convention is `master`. After this, `/contents/<file>` API queries default to `main` and return 404 because your real content is on `master`. Fix with a follow-up `PATCH /repos/<owner>/<name> -d '{"default_branch":"master"}'` and `DELETE /repos/<owner>/<name>/git/refs/heads/main` to drop the empty main ref.

### Phase 5 — Subtree merge

Order matters: write `Cargo.toml` / `package.json` / `pyproject.toml` workspace manifest BEFORE the first `subtree add`. After `subtree add` completes, commit the manifest as a SEPARATE commit — don't try to commit during the subtree-add loop because the working tree state from the first `subtree add` resets uncommitted changes:

```bash
git clone <monorepo-url> repo && cd repo
git checkout <default_branch>
git config user.email "..." && git config user.name "..."

# 1) Write workspace manifest at the root (UNCOMMITTED — that's fine)
cat > Cargo.toml <<'EOF'
[workspace]
resolver = "2"
members = ["crates/<name1>", "crates/<name2>", ...]
EOF

# 2) Add each subtree (these will commit themselves; your uncommitted manifest stays in working tree)
for repo in "${REPOS[@]}"; do
    git remote add "${repo}-src" "/path/to/clone/${repo}"
    git fetch --quiet "${repo}-src" "${repo}-branch"
    git subtree add --prefix="subdir/${repo}" "${repo}-src" "${repo}-branch" \
        -m "merge: import ${repo} from <ORG>/${repo}@${repo}-branch"
    git remote remove "${repo}-src"
done

# 3) Now commit the manifest that survived the subtree-add storm
git add Cargo.toml README.md LICENSE
git commit -m "chore: add workspace manifest and README"

git push -u origin master
```

### Phase 6 — If using PR-flow delivery

```bash
# 1. Force-push master to an empty commit (your previous content is now on a tag)
git tag archive/import-bundle <old-master-HEAD>      # safety net
git checkout master
git update-ref refs/heads/master <empty-commit-sha> # create with: git commit-tree $(git mktree < /dev/null) -m "chore: initialize"
git push origin master --force                       # now master is empty on remote

# 2. Recreate the import work as a feature branch from the tag
git branch import/all-crates archive/import-bundle
git checkout import/all-crates
# Merge master in so head and base share history (PRs require shared ancestor)
git merge master --no-ff --allow-unrelated-histories \
    -m "merge: bring workspace base into import branch"
git push origin import/all-crates --force

# 3. Open the PR
curl -X POST -H "Authorization: token $GH_TOKEN" \
  https://api.github.com/repos/<OWNER>/<name>/pulls \
  -d '{"title":"feat: import all N crates via git subtree","head":"import/all-crates","base":"master","body":"..."}'

# 4. Squash-merge
curl -X PUT -H "Authorization: token $GH_TOKEN" \
  https://api.github.com/repos/<OWNER>/<name>/pulls/<N>/merge \
  -d '{"commit_title":"feat: import all N crates (#N)","commit_message":"...","sha":"<head-sha>","merge_method":"squash"}'
```

PR 422 "branch has no history in common with master": caused by force-pushing master to an empty orphan while keeping the import branch from the old tree. Fix: `git merge master --no-ff --allow-unrelated-histories` on the import branch before pushing it. GitHub's PR API refuses unrelated-history pushes by default.

Do NOT use `git rebase` here — subtree commits touch thousands of files and rebase will conflict on every Cargo.toml/package.json in working tree. Merge with `--allow-unrelated-histories` is the right tool.

### Phase 7 — Cleanup of old repos

```bash
# Try DELETE — may return 403 due to classic-PAT glitch on recently-created repos
curl -X DELETE -H "Authorization: token $GH_TOKEN" \
  https://api.github.com/repos/<OLD_OWNER>/<OLD_NAME>

# Fallback if 403: archive with a redirect message
curl -X PATCH -H "Authorization: token $GH_TOKEN" \
  https://api.github.com/repos/<OLD_OWNER>/<OLD_NAME> \
  -d '{"archived":true,"description":"[ARCHIVED] Moved to https://github.com/<NEW_OWNER>/<NEW_NAME>"}'
```

The 403 is a GitHub-side glitch where classic PATs sometimes can't DELETE repos they just created via API, even with `admin: true` permission and `repo` scope. Browser DELETE in repo Settings → Danger Zone works because that path uses session auth, not PAT. Document the archive state in the redirect description so anyone hitting the old URL knows where to go.

## Token discovery

`GH_TOKEN` is often empty in Hermes background agents (non-interactive shell, rc files not sourced). Don't assume env is set:

```python
import os, subprocess
TOKEN = os.environ.get('GH_TOKEN') or os.environ.get('GITHUB_TOKEN')
if not TOKEN:
    # ask git's credential helper rather than scraping shell rc files
    out = subprocess.run(['git', 'credential', 'fill'],
                         input='protocol=https\nhost=github.com\n\n',
                         capture_output=True, text=True)
    TOKEN = dict(l.split('=', 1) for l in out.stdout.splitlines() if '=' in l).get('password')
if not TOKEN:
    raise SystemExit('no GitHub token: export GH_TOKEN or configure a git credential helper')
```

Distinguish these failure modes — never use 401/403 to conclude "org/repo doesn't exist":
- 401 (Bad credentials) — token is missing/empty/invalid; affects ALL endpoints
- 403 (Must have admin rights) — token valid but lacks scope OR GitHub DELETE glitch
- 403 with `x-ratelimit-remaining: 0` — rate limit, wait 60s
- 404 (Not Found) — resource genuinely doesn't exist (only meaningful with valid token)

## Verification checklist (always run after delivery)

- GET `/repos/<OWNER>/<name>` returns `archived: false`, correct `default_branch`
- GET `/repos/<OWNER>/<name>/contents/<workspace-manifest>` decodes successfully, lists all N subdirs
- GET `/repos/<OWNER>/<name>/contents/subdir/<name>` for each subdir is a directory (not 404)
- Sample `subdir/<name>/Cargo.toml` (or `package.json` / `pyproject.toml`) has correct package metadata
- GET `/repos/<OWNER>/<name>/commits?per_page=5` shows expected top commits
- PR (if PR-flow): `state: closed, merged: true, merge_commit_sha: <non-null>`
- All old/placeholder repos are either archived or deleted; redirect description present

## Anti-patterns

- Don't `git subtree add --squash` for fleet consolidation. Squash drops upstream history, defeats the whole point of subtree. `--squash` is only useful for one-off cherry-picks.
- Don't loop `git subtree add` then `git push` per crate. Single bulk push at the end is faster and gives a clean remote state.
- Don't write the workspace manifest INSIDE the subtree-add loop. `git subtree add` can reset the working tree; commit the manifest once at the end.
- Don't force-push the import branch to base without merging base in first — you'll get PR 422.
- Don't reuse `default_branch` from a personal repo for an org repo — POST creates with `main` regardless. Always set explicitly.
- Don't skip the verification checklist — local `git log` shows commits, but only the API check confirms the remote actually has the expected tree under the right default branch.