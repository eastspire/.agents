# Contents API workflow — no local clone required

When the local working tree is empty or stale, and SSH clone is slow / unreliable (e.g. 466-file repo under GFW throttling: ~28 min observed), **skip git entirely and use the REST Contents API**. For ≤10 file changes on a private repo, this is faster than a full clone.

## When to use this over `github-tree-api-multi-file-commit`

- ≤10 file changes (delete a directory + edit a few config files)
- Don't need atomic single-commit history (each PUT/DELETE creates its own commit, which is fine for PR review purposes)
- Working tree is missing or stale and SSH clone is slow

## When NOT to use

- Many files (≥10) and atomic commit matters → use tree/commit/ref API
- You already have a clean local clone → use git directly (much faster)

## The 3-step flow

```python
import urllib.request, json, os, base64
TOKEN = os.popen('grep -oP \'export GH_TOKEN="\\K[^"]+\' /root/.bashrc.d/gh_token.sh').read().strip()
H = {'Authorization': f'token {TOKEN}',
     'Accept': 'application/vnd.github+json',
     'User-Agent': 'hermes-cli'}
```

### 1. Create branch via git refs API

```python
master_sha = '...'  # from GET /repos/.../git/refs/heads/master
branch_name = 'chore/<descr>-YYYY-MM-DD'
req = urllib.request.Request(
    'https://api.github.com/repos/OWNER/REPO/git/refs',
    data=json.dumps({
        'ref': f'refs/heads/{branch_name}',
        'sha': master_sha,
    }).encode(),
    method='POST', headers=H)
with urllib.request.urlopen(req, timeout=30) as resp:
    print(json.loads(resp.read())['ref'])  # "refs/heads/<branch_name>"
```

### 2a. Modify file (PUT)

```python
path = 'src/.vuepress/sidebar.js'
new_content = '''...'''

# Need current sha
req = urllib.request.Request(
    f'https://api.github.com/repos/OWNER/REPO/contents/{path}?ref={branch_name}',
    headers=H)
with urllib.request.urlopen(req, timeout=30) as resp:
    current = json.loads(resp.read())

# PUT the change
req = urllib.request.Request(
    f'https://api.github.com/repos/OWNER/REPO/contents/{path}',
    data=json.dumps({
        'message': 'docs: <summary>',
        'branch': branch_name,
        'sha': current['sha'],
        'content': base64.b64encode(new_content.encode()).decode(),
    }).encode(),
    method='PUT', headers=H)
with urllib.request.urlopen(req, timeout=30) as resp:
    print(json.loads(resp.read())['commit']['sha'])
```

### 2b. Delete file (DELETE)

```python
path = 'src/development-standards/README.md'

# Need current sha (same fetch as above)
req = urllib.request.Request(
    f'https://api.github.com/repos/OWNER/REPO/contents/{path}?ref={branch_name}',
    headers=H)
with urllib.request.urlopen(req, timeout=30) as resp:
    current = json.loads(resp.read())

req = urllib.request.Request(
    f'https://api.github.com/repos/OWNER/REPO/contents/{path}',
    data=json.dumps({
        'message': 'docs: remove <descr>',
        'branch': branch_name,
        'sha': current['sha'],
    }).encode(),
    method='DELETE', headers=H)
with urllib.request.urlopen(req, timeout=30) as resp:
    print(json.loads(resp.read())['commit']['sha'])
```

### 3. Open PR

```bash
GH_TOKEN=$TOKEN gh pr create \
  --repo OWNER/REPO \
  --base master \
  --head <branch_name> \
  --title "docs: <summary>" \
  --body-file /tmp/pr-body.md
```

## Performance notes (verified 2026-08-27)

For a 466-file `docs-pages/docs` repo with 5 modifications:

| Step | Time |
| --- | --- |
| Branch creation (1 API call) | ~1s |
| Per-file fetch + PUT or DELETE (5 files) | ~3-15s each (PUT faster, DELETE similar) |
| Total file ops | ~30-60s |
| gh pr create | ~5s |
| **Total wall-clock** | **~2-3 min** |

vs. SSH clone + edit + push + PR: ~30+ min on GFW-throttled hosts.

## Pitfalls

1. **`?ref=` default trap** — `GET /contents?ref=` defaults to detached HEAD, not the default branch. Always pass `?ref={branch}` explicitly when fetching the file's `sha` for the PUT/DELETE.
2. **Rate limiting** — Contents API counts each PUT/DELETE as one request. For ≤10 changes per minute you're fine. For batch >20, switch to tree/commit API.
3. **Each PUT/DELETE creates its own commit** — if you want one atomic commit, use the tree/commit/ref API instead (see `github-tree-api-multi-file-commit`). For doc edits, atomic commits usually don't matter — reviewers see a clean PR with N well-described commits.
4. **No `force=true` available** — Contents API does sequential commits, each building on the previous. No race risk.
5. **404 on GET means dir was already deleted** — if you're verifying after deletion, a 404 on `GET .../contents/<path>` is the expected success signal, not an error.

## Quick "is the change live?" verification

```python
# After all PUTs/DELETEs, fetch the tree listing to confirm
import urllib.request, json
req = urllib.request.Request(
    f'https://api.github.com/repos/OWNER/REPO/git/trees/{branch_name}?recursive=1',
    headers=H)
with urllib.request.urlopen(req, timeout=30) as resp:
    tree = json.loads(resp.read())
paths = sorted(e['path'] for e in tree['tree'] if e['type'] == 'blob')
# check no dev-standards paths remain
assert not any(p.startswith('src/development-standards/') for p in paths)
```

Then check commits on the branch:

```python
req = urllib.request.Request(
    f'https://api.github.com/repos/OWNER/REPO/commits?sha={branch_name}&per_page=20',
    headers=H)
with urllib.request.urlopen(req, timeout=30) as resp:
    for c in json.loads(resp.read()):
        print(c['sha'][:8], c['commit']['message'].splitlines()[0])
```