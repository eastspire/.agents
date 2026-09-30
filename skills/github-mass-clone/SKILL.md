---
name: github-mass-clone
description: "Mass-clone GitHub repos from orgs, filtered, full history."
version: 1.0.0
author: Hermes Agent (curator)
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [github, git, clone, mass-clone, organization, deep-clone]
    category: software-development
    related: [github]
---

# GitHub Mass Clone (orgs/users, filtered, deep)

Clone many repos from one or more GitHub orgs or users in one shot, optionally filtered by language, ALWAYS with full history + all branches + all tags.

## When to use

The user asks to clone many GitHub repos at once — by organization, by user, by topic, or by language. Examples:
- "clone all my Rust repos from org X and Y"
- "deep-clone every repo under these orgs"
- "mirror all public repos in language Z owned by user X"

## What "deep clone" means

**Deep clone = full history + every branch + every tag.** A `--depth 1` shallow clone is the OPPOSITE — recent activity signals frequently mistranslate "deep" as "shallow." In Chinese the term is **深克隆** (shēn kè lóng) = full history, NOT `--depth`.

The flow is `git clone --no-single-branch` with no depth limit. After clone, also fetch all remote branches and tags.

## Procedure

1. **Auth check.** Confirm GitHub auth works:
   - SSH preferred: `ssh -T git@github.com` should print `Hi <user>!`
   - If no SSH key: check `gh auth status` (preferred CLI). Fallback `git credential fill` for `github.com`, or the `GITHUB_TOKEN` env var.
   - **No auth → unauthenticated API calls burn the 60 req/hr IP rate limit fast** (one list call per org already eats a request). Use SSH `git clone` directly + manual repo list when needed.

2. **Enumerate repos by language filter.** Use the GitHub REST API:
   ```bash
   curl -s "https://api.github.com/orgs/<org>/repos?per_page=100&type=public" \
     -H "Accept: application/vnd.github+json" \
     | python3 -c "
   import json, sys
   repos = json.load(sys.stdin)
   if not isinstance(repos, list):
       print('ERR:', repos); sys.exit(1)
   for r in repos:
       if r.get('language') == '<LANG>':
           print(r['full_name'])
   "
   ```
   - `per_page=100` is the max; orgs with >100 repos need pagination (use the `Link` header `rel="next"`).
   - The `language` field is the PRIMARY language GitHub inferred — for polyglot repos, also check the root `Cargo.toml` / `package.json` after cloning if exact match matters.
   - Private repos require auth; pass `-H "Authorization: Bearer $GITHUB_TOKEN"`.
   - **Rate limit error → check `X-RateLimit-Reset` header**, compute wait = `reset_epoch - now()`, sleep that long, retry. With no auth you wait up to an hour per attempt.

3. **Clone with full history from the start.** Skip `--depth 1` — there is no speed win worth the conversion step later. For users with auth concerns about huge repos, only THEN consider shallow.
   ```bash
   cd <target_dir>
   git clone git@github.com:<org>/<repo>.git
   ```
   SSH host is `git@github.com:<owner>/<repo>.git`. HTTPS works too: `https://github.com/<owner>/<repo>.git`.

4. **Fetch ALL branches and tags locally.** Default `git clone` only checks out the default branch. For every remote branch, create a local tracking branch:
   ```bash
   cd <repo>
   git remote set-branches origin '*'
   git fetch --all --tags
   for b in $(git branch -r | grep -v 'HEAD' | sed 's|origin/||'); do
     git branch --track "$b" "origin/$b" 2>/dev/null
   done
   git checkout master 2>/dev/null || git checkout main 2>/dev/null
   ```

5. **Skip already-present dirs.** Before cloning, check `[ -d "<repo>" ]` and skip — mass-clone reruns are common.

6. **Verify and report.** After the loop, report per-repo: commit count, branch count, tag count, `Cargo.toml`/language marker. The user cares about completeness — surface any skip or failure explicitly.

## Pitfalls

- **"深克隆" / "deep clone" / "full clone" → no `--depth` flag.** Using `--depth 1` and later converting via `git fetch --unshallow --tags` is a wasted round-trip; the conversion re-downloads the full history anyway. Clone deep from the first command.
- **Unauthenticated API lists eat rate limit.** Each `/orgs/X/repos` page = one rate-limit slot. With many orgs and no token, expect `403 API rate limit exceeded` after 60 requests. Check `X-RateLimit-Reset` before sleeping — a 5-second sleep is meaningless against a 50-minute reset window.
- **Default-branch-only clone.** A fresh `git clone` only materializes the default branch as a working tree. Other branches are remote-tracking refs until you create local branches with `git branch --track`. The deep-clone workflow is incomplete without this loop.
- **`-b main` vs `-b master`.** Some orgs use `main`, others `master`. Don't hardcode — check with `git symbolic-ref refs/remotes/origin/HEAD` after the first clone, or try both in the loop.
- **`gh` is not always installed.** Don't assume `gh repo clone` works; the workflow must work with `git` + `curl` only.
- **`language` is GitHub's inferred primary language.** It's not authoritative for polyglot repos. After cloning, `ls Cargo.toml` is the ground truth for "is this a Rust repo." Mention this when reporting what was/wasn't cloned.
- **Org membership is implicit.** Public org repos are listable by anyone with `?type=public`; private repos require the user to have access AND you to pass auth. Don't claim "no Rust repos" without confirming you queried with the right visibility scope.

## Quick command bundle

```bash
mkdir -p ~/code && cd ~/code

# 1. Build list of Rust repos across multiple orgs (single API call per org).
for org in <org1> <org2> <org3>; do
  curl -s "https://api.github.com/orgs/$org/repos?per_page=100&type=public" \
    | python3 -c "
import json, sys
for r in json.load(sys.stdin):
    if r.get('language') == 'Rust':
        print(r['full_name'])
" >> rust_repos.txt
done

# 2. Clone each (skips existing) with full history.
sort -u rust_repos.txt > rust_repos.uniq.txt
while read -r slug; do
  name=$(basename "$slug")
  [ -d "$name" ] && continue
  git clone "git@github.com:$slug.git" "$name"
done < rust_repos.uniq.txt

# 3. After loop, fetch all branches/tags per repo.
for d in */; do
  (cd "$d" && git remote set-branches origin '*' && git fetch --all --tags)
done
```