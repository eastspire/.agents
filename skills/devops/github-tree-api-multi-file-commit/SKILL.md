---
name: github-tree-api-multi-file-commit
description: >-
  Use the GitHub Git Database API (Trees + Commits + Refs) to commit multiple
  file changes in a single commit on a fork, then open a PR — instead of
  making N separate PUT /contents/{path} calls. This is the robust path when
  (a) you need to update several files atomically with one PR, or (b) you
  have no local clone and are working purely over the REST API. Triggers
  include "open PR on a fork via API", "multi-file commit via API",
  "tree API + commit + ref", "update N files in one PR without cloning",
  "GitHub API only no git", "create branch + commit + PR with curl/gh api".
  Avoid when you already have a local clone — use the gh pr create flow from
  the gh-pr-creation-workflow skill instead, which is much faster.
---

# GitHub Tree API Multi-File Commit Pattern

Use the Git Database API to make **N file changes in one commit on a fork**, without cloning locally. The naive `PUT /repos/{owner}/{repo}/contents/{path}` flow breaks down with N>=2 because:

- Each PUT needs the file's current `sha` from `GET .../contents?ref={branch}`
- N parallel PUTs can race on the same branch ref (422 "Update is not a fast forward")
- The `?ref=` default falls back to detached HEAD, not default branch (see existing memory)

The tree/commit/ref pattern sidesteps all of this.

## When to use

- Updating **2+ files** atomically on a fork
- You **don't have a local clone** (or it's faster not to clone — e.g. multi-repo batch work)
- You need **one commit, one PR** (not N commits)
- You've been burned by `PUT /contents` 422s or sha mismatches

## When NOT to use

- You have a local clone → just `git checkout -b`, edit, commit, push, `gh pr create` (see `gh-pr-creation-workflow` skill)
- Single file change → `PUT /contents` is simpler
- 1 file but it's large (>100MB) → use git directly, not API

## The 5-step flow (cross-fork, no clone)

All endpoints use `POST`. Auth via `${GH_TOKEN}` header.

### 1. Get base_tree + base_commit_sha

```bash
gh api -X GET "repos/{owner}/{repo}/git/ref/heads/{base_branch}" --jq '.object.sha,.object.url'
# returns base_commit_sha; append /git/trees/{sha} to get base_tree_sha
gh api -X GET "repos/{owner}/{repo}/git/commits/{base_commit_sha}" --jq '.tree.sha'
```

If the fork's `{base_branch}` is missing entirely (e.g. CODE-RUN/SSH where upstream is private or default branch differs), first create the fork's branch as a copy of upstream's:

```bash
gh api -X POST "repos/{upstream_owner}/{upstream_repo}/git/refs" \
  -f ref="refs/heads/{base_branch}" -f sha="{upstream_base_commit_sha}"
# wait, that's upstream. For fork:
gh api -X POST "repos/{fork_owner}/{fork_repo}/git/refs" \
  -f ref="refs/heads/{base_branch}" -f sha="{fork_base_commit_sha}"
```

### 2. Build the new tree

`POST /repos/{owner}/{repo}/git/trees` with `base_tree` + `tree` array:

```json
{
  "base_tree": "<base_tree_sha from step 1>",
  "tree": [
    {
      "path": "sh/bin_up.sh",
      "mode": "100755",
      "type": "blob",
      "content": "<full new file content, raw string, NOT base64>"
    },
    {
      "path": "sh/bin_build.sh",
      "mode": "100755",
      "type": "blob",
      "content": "<...>"
    }
  ]
}
```

Returns `sha` = new_tree_sha.

**Critical**: `content` is **raw UTF-8 string**, not base64. `mode` `"100755"` for executable, `"100644"` for normal. If the original file is 755, keep it 755 — losing execute bit is a silent regression.

### 3. Create commit

`POST /repos/{owner}/{repo}/git/commits`:

```json
{
  "message": "chore: scrub personal info from sh/*.sh headers\n\n- Remove Author/Email/QQ/Copyright header comments\n- Remove commented-out old scp commands (192.168.x LAN IPs)\n- Preserve deploy main body verbatim\n- sh -n syntax-checked all modified files",
  "tree": "<new_tree_sha>",
  "parents": ["<base_commit_sha>"]
}
```

Returns `sha` = new_commit_sha.

### 4. Update or create ref

If the branch **already exists** in the fork (you re-running after a failed attempt, or doing iterative work):

```bash
gh api -X PATCH "repos/{owner}/{repo}/git/refs/heads/{branch_name}" \
  -f sha="{new_commit_sha}" -f force=true
```

If the branch is **new**:

```bash
gh api -X POST "repos/{owner}/{repo}/git/refs" \
  -f ref="refs/heads/{branch_name}" -f sha="{new_commit_sha}"
```

`force=true` is safe here because we're force-updating **a feature branch we own** to point to our new commit. **NEVER** force-update master/main (covered in memory).

### 5. Open PR

```bash
gh pr create \
  --repo {upstream_owner}/{upstream_repo} \
  --head {fork_owner}:{branch_name} \
  --base {base_branch} \
  --title "chore: scrub personal info from sh/*.sh headers" \
  --body "## Summary
Removed Author/Email/QQ/Copyright header comments and LAN-IP comment blocks from sh/bin_*.sh. Deploy body unchanged.

## Changes
- \`sh/bin_up.sh\`: replaced 6-line author header with 2-line generic comment
- \`sh/bin_build.sh\`: same
- Syntax-checked with \`sh -n\`, mode 755 preserved

## Verification
- \`sh -n sh/bin_up.sh\` passes
- \`sh -n sh/bin_build.sh\` passes
- diff shows only -N/+M in header region, body identical

🤖 Generated with [Hermes](https://github.com/eastspire/hermes-agent)"
```

## Pitfalls (hit these in 2026-08-16 LTPP family PRs)

1. **`?ref=` default trap** — `GET /contents?ref=` defaults to detached HEAD, not default branch. Always pass `?ref={branch}` explicitly when fetching `sha` for `PUT /contents` (already in memory). For the tree/commit flow, you don't fetch file shas — you embed content directly — so this pitfall is sidestepped.

2. **`PUT /contents` race on same branch** — 2 parallel PUTs on the same branch can 422 because the second PUT sees a different ref head. Tree/commit API is atomic by design.

3. **`content` field is raw, not base64** — the Git Database tree API `content` is UTF-8 string. Don't base64-encode.

4. **Don't lose file mode** — if you `PUT /contents` you preserve mode automatically; in the tree API you must specify `"mode": "100755"` explicitly. Forgetting defaults to `100644`, which breaks `sh` scripts that need execute bit.

5. **Branch name clash on retry** — if the branch already exists, `POST /git/refs` returns 422. Use `PATCH /git/refs/heads/{name}` with `force=true` to update it (safe for feature branches, **never** for master/main).

6. **Empty commit on no-op tree** — if all files' content is unchanged, the new tree sha == base tree sha, and GitHub may reject creating a no-op commit. Verify content actually differs.

7. **`force=true` on `PATCH /git/refs`** — only safe on **feature branches you own**. **Never** force-push master/main. Already in memory.

## Worked example: comments-only privacy scrub (the LTPP family pattern)

For "only modify comment headers, don't change deploy body" requests:

1. Read the **original file verbatim** — `GET /repos/.../contents/sh/bin_up.sh?ref=main` (or master).
2. Replace only the **top comment block** (everything between `#!/bin/bash` and the first non-comment line, or the first executable command). Common patterns to scrub:
   - `@Author: ...` / `@Date:` / `@LastEditors:` / `@FilePath:` / `@Description: ...`
   - Inline `# Author:` / `# Email:` / `# QQ:` / `# Copyright (c) YYYY by NAME`
   - Commented-out old commands leaking internal IPs (e.g. `192.168.x.x`)
3. **Body of the script stays byte-identical** (the `scp`, `webman`, `gtl` etc. lines).
4. Submit via tree API (not `PUT /contents` × N).
5. Verify in PR diff that **body lines are zero-diff** — only the header comment block changed.

**Don't simplify hardcoded deploy values in the body** unless the user explicitly says so — they may have intentionally inlined the production server IP / Windows SSH key path / port. Grep-friendly does not equal leakage; only headers + commented-out lines count as "comments".

## Verification checklist (post-PR)

- `gh pr diff {pr_number} --repo {owner}/{repo}` — eyeball that only header lines changed
- `git show {new_commit_sha}:sh/bin_up.sh | sh -n` — syntax check (if you can clone)
- `gh api /repos/{owner}/{repo}/contents/sh/bin_up.sh?ref={branch}` — verify mode is `100755`
- `gh pr view {pr_number} --json files,additions,deletions` — sanity check totals

## When local clone IS available, just use it

The tree API flow is for the **no-clone, multi-repo batch** case. If you're working in a single repo with a local clone, `git checkout -b` + `git commit` + `git push -u origin` + `gh pr create` is faster and less error-prone. See `gh-pr-creation-workflow` skill.
