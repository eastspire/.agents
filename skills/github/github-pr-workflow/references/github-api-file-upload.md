# GitHub Contents API: File Upload Without Cloning

## Why this recipe exists

When one of the following is true:

- `git clone` over HTTPS to the target repo stalls (GFW throttling; can be 30+ min on a 100MB repo, hours on bigger).
- `git clone` over SSH hits `index-pack` at 20–40 KiB/s and won't finish in any reasonable time.
- The org has **forking disabled** (`POST /repos/<o>/<r>/forks` returns 403) AND you only need to change a handful of files.
- The target repo is **private** and your account has admin/maintain but no local clone bandwidth.

…you can upload file changes directly via the Contents API. No `git clone`, no `git push`. Each `PUT` writes one file as one commit on the branch you specify.

## What you need

1. A GitHub token with `repo` scope (or `contents:write` for fine-grained). `gh auth status` should already be passing for the target user.
2. The base branch SHA (so you can `git/refs` to create a feature branch).
3. The current blob SHA of every file you're replacing (so Contents API knows what to update; missing it = "you need to fetch first").

## Recipe

### Step 1 — get the base branch SHA + the file blob SHAs

```bash
BASE_SHA=$(gh api repos/<owner>/<repo>/commits/<base-branch> --jq .sha)

# For every file you'll change, fetch its current blob SHA:
gh api repos/<owner>/<repo>/contents/<path-to-file>?ref=<base-branch> \
  --jq '{name: .name, sha: .sha, size: .size}'
# Save the .sha field — Contents PUT needs it as `sha`.
```

### Step 2 — create the feature branch (ref-based, no clone needed)

```bash
gh api -X POST repos/<owner>/<repo>/git/refs \
  -f "ref=refs/heads/<branch-name>" \
  -f "sha=$BASE_SHA"
```

Verify:

```bash
gh api repos/<owner>/<repo>/branches/<branch-name> --jq '.name + " sha=" + .commit.sha'
# Expected: <branch-name> sha=<base-sha>
```

### Step 3 — PUT each modified file

For each file:

```bash
# Build the JSON payload — content must be base64
python3 - <<PYEOF
import base64, json, subprocess

path = "<path/to/file.ext>"
new_text = open("<local-path-to-modified-file>", encoding="utf-8").read()
original_blob_sha = "<sha-from-step-1>"

payload = {
    "message": "docs(<scope>): <short summary>\n\n<longer description if needed>",
    "content": base64.b64encode(new_text.encode()).decode(),
    "branch": "<branch-name>",
    "sha": original_blob_sha,   # required for updates; omit for new files
}
print(json.dumps(payload))
PYEOF
```

Then call:

```bash
gh api -X PUT repos/<owner>/<repo>/contents/<path-to-file> \
  --input /tmp/payload-<N>.json
```

Response includes the new blob SHA and the commit SHA. Each file becomes its own commit on the branch. (For multi-file doc syncs, you can also use the Git Data API `POST /repos/<o>/<r>/git/trees` to batch into a single commit — see "Batched uploads" below.)

### Step 4 — open the PR

```bash
gh pr create \
  --repo <owner>/<repo> \
  --head <branch-name> \
  --base <base-branch> \
  --title "<title>" \
  --body-file /tmp/pr-body.md
```

If the user has admin/maintain on the repo (you should have already verified this), this works directly without forking.

## Pitfalls

- **The token format matters.** Use the token as the auth header value directly. Do NOT embed it in the request URL — GitHub logs URLs and you'll leak the token.
  ```bash
  # OK
  curl -H "Authorization: Bearer $GITHUB_TOKEN" ...
  # DO NOT
  curl "https://x-access-token:$GITHUB_TOKEN@github.com/..."  # leaks to shell history and git remote URL
  ```
- **Missing `sha` on update = 422 "sha is required for updating an existing file"**. Fetch it via `GET /repos/<o>/<r>/contents/<path>` first.
- **`sha` mismatch = 409 "does not match the expected value"**. Someone else committed between your fetch and your PUT. Refetch the SHA and retry.
- **Branch ref POST fails with 422 "Reference already exists"**. The branch name is taken. Use a different name, or pass the existing SHA.
- **PR creation fails with "no history in common with base"**. Your branch's HEAD has no ancestor commit relationship with the base branch. The Contents-API recipe doesn't create an orphan — every PUT writes a commit whose parent is the previous HEAD on the branch, so history is naturally linear. If you see this error, you probably tried to use `git replace --graft` on a local clone instead. Stop and use Contents API.
- **Rate limit**. Contents API calls count against the per-hour REST rate limit (5000/hr for authenticated users, 60/hr for unauth). For multi-file syncs of dozens of files, pace yourself. See "Batched uploads" for a workaround.
- **Private repos: the API works fine, but `gh api` may report `Missing required scopes: read:org` for *forking* even though contents reads/writes succeed.** Don't conflate the two — fork is a separate permission from contents-write.

## Batched uploads (single commit, many files)

When you have N files to change and want them in one commit (cleaner PR, no rate-limit pressure), use the Git Data API:

```bash
# 1. Get the base tree SHA
BASE_TREE=$(gh api repos/<owner>/<repo>/git/trees/<base-sha> --jq .sha)

# 2. Build a new tree with all your changes
#    (each entry references a blob you upload via POST /repos/<o>/<r>/git/blobs)
TREE_PAYLOAD=$(python3 - <<PYEOF
import base64, json

entries = []
for path, local_path in [
    ("src/euv/cli/install.md",     "/local/install.md"),
    ("src/euv/usage-introduction/engine.md", "/local/engine.md"),
]:
    text = open(local_path, encoding="utf-8").read()
    entries.append({
        "path": path,
        "mode": "100644",
        "type": "blob",
        "content": text,            # Git Data API blobs accept UTF-8 content directly
    })
print(json.dumps({"base_tree": "$BASE_TREE", "tree": entries}))
PYEOF
)

NEW_TREE_SHA=$(gh api -X POST repos/<owner>/<repo>/git/trees \
  --input <(echo "$TREE_PAYLOAD") --jq .sha)

# 3. Create a commit pointing at the new tree, parent = base commit
NEW_COMMIT_SHA=$(gh api -X POST repos/<owner>/<repo>/git/commits \
  -f "message=docs(euv): <your message>" \
  -f "tree=$NEW_TREE_SHA" \
  -f "parents[]=$BASE_SHA" --jq .sha)

# 4. Move the branch ref to the new commit
gh api -X PATCH repos/<owner>/<repo>/git/refs/heads/<branch-name> \
  -f "sha=$NEW_COMMIT_SHA"

# 5. Now open the PR as usual
```

This is one commit, N files, one rate-limit cost (for the tree POST — blobs in trees inline `content` so no separate blob upload needed).

## When NOT to use this recipe

- You have a clean `git clone` of the repo already. Use normal `git add/commit/push` — much faster for > 5 files.
- You need to review diffs locally before pushing (`git diff`, `git log -p`). Contents API commits in one shot.
- The target repo is huge AND you need to make dozens of changes. At that point, the network cost of `git fetch` is amortized across all your local commits, and you save round-trips by working in a local clone.

## One-liner: read a file with Contents API (no clone, no raw.githubusercontent.com)

When `raw.githubusercontent.com` is blocked but `api.github.com` works:

```bash
gh api repos/<owner>/<repo>/contents/<path> --jq .content | base64 -d
```

This is the read-side counterpart of the PUT recipe above. Useful for inspecting a file before editing it without paying the full clone cost.