# GitHub Fetch Under Heavy Throttling / GFW

Field notes for downloading GitHub repos on networks where HTTPS to github.com / raw.githubusercontent.com / codeload.github.com is heavily throttled or partially blocked, but `api.github.com` and SSH `git@github.com:22` work normally.

## Symptoms

- `curl https://codeload.github.com/.../tar.gz` returns `HTTP/2 stream CANCEL` (exit 92) or `Recv failure: Connection reset` after a few MB.
- `git clone git@github.com:owner/repo.git` succeeds on SSH handshake (~10s) but `index-pack` crawls at 20–40 KiB/s and stalls on medium/large repos.
- `wget https://codeload.github.com/.../tar.gz` is the only thing that completes, but very slowly (~1–2 MB/min on a 50–200MB tarball).
- Tarball gzip stream may be truncated at the end — `tar -tzf` exits mid-listing when the connection dies.

## Why This Happens

- The host can reach `api.github.com` and `git@github.com:22` but is rate-limited or has HTTP/2 multiplexing issues to `codeload.github.com` and `raw.githubusercontent.com`.
- `curl` aborts on the first stream error; `wget` retries the partial byte range indefinitely.
- The throttling is per-connection, not per-host — a parallel `wget` doesn't speed things up.

## Reliable Recipe

### Download a tarball when SSH is too slow

```bash
# Use wget with aggressive retry. curl will not survive repeated HTTP/2 stream resets.
wget --tries=infinite --waitretry=3 --read-timeout=60 \
     -O /tmp/repo.tar.gz \
     https://codeload.github.com/<owner>/<repo>/tar.gz/refs/heads/<branch>

# Verify the tarball ends cleanly before extracting
tar -tzf /tmp/repo.tar.gz > /tmp/listing.txt 2>&1
tail -5 /tmp/listing.txt
# If the listing is short and ends mid-entry, the gzip tail was truncated — re-download.
```

Plan for ~30–45 minutes for a 50MB tarball on a heavily throttled host.

### Read a single file when raw.githubusercontent.com is blocked

```bash
# raw.githubusercontent.com may be blocked even when api.github.com works.
# Use the contents API + base64 decode:
curl -sS -m 10 \
  "https://api.github.com/repos/<owner>/<repo>/contents/<path-to-file>" \
  | python3 -c "
import sys, json, base64
r = json.load(sys.stdin)
print(base64.b64decode(r['content']).decode('utf-8'))
"
```

### Listing a directory

```bash
curl -sS -m 10 "https://api.github.com/repos/<owner>/<repo>/contents/<dir>" \
  | python3 -c "
import sys, json
r = json.load(sys.stdin)
for i in r:
    print(f'{i[\"type\"]:5s} {i[\"size\"]:>10d}  {i[\"name\"]}')
"
```

### Don't trust `tar` listing count alone — re-extract and recount

A truncated gzip may still list N entries before bailing, but the last few files in the listing may not exist in the extracted tree. After `tar -xzf`, sanity-check with:

```bash
find . -type f | wc -l
# vs.
tar -tzf /tmp/repo.tar.gz 2>/dev/null | grep -v '/$' | wc -l
```

If they differ, the tail of the tarball is corrupt — re-download. Do NOT attempt to push a partial repo as a PR; the missing files will surface as a misleading diff.

## Implications for PR Workflows

- A downloaded tarball is **not a git repo** — no `.git/` directory, no commit history, no branches. You cannot `git push` from it. To PR changes:
  1. Re-clone with SSH if network allows: `git clone git@github.com:<owner>/<repo>.git`
  2. Or `git init` + `git remote add` to your fork, but be aware: you have no upstream history until you `git fetch` it, and any changes you make on top of the tarball will appear as the entire file set in the diff if you don't layer them on the fetched history properly.
- Treat any "I'll just download the tarball and edit" plan as **incomplete** until the git history is reconstructed. Don't claim the work is ready to push until that step succeeds.

## Don't Try

- `ghproxy.com` / `mirror.ghproxy.com` / `gh-proxy.com` / `hub.fastgit.xyz` / `github.akams.cn` / `ghps.cc` — these mirrors are dead, return 404, or are blocked on hosts that already throttle github.com directly.
- `https://ghfast.top/<github-url>` — **still alive** (as of Aug 2026) for fast GitHub release/asset downloads when `codeload.github.com` is dead slow. Works for `https://ghfast.top/https://github.com/<owner>/<repo>/releases/download/<tag>/<asset>`. Returned 200 + 13 MB at full link speed when `codeload.github.com` was capped at 33 KB/s. Don't trust `git clone` through it — it's a release-asset proxy, not a git-protocol bridge.
- `https://ghproxy.net/<github-url>` — also still alive as a release-asset proxy, slightly slower than ghfast.top in spot tests. Same caveat.
- Parallel curl/wget — throttling is per-connection, so N parallel downloads ≈ 1× speed with N× resource use.
- Resuming with `curl -C -` — codeload does not honor Range well for the redirect path, so resume usually restarts.

## Pushing to GitHub from a throttled host

For `git push` specifically (not clone):

- **HTTPS push via `x-access-token:<token>@github.com/...` may stall indefinitely** even when `gh api` calls work in seconds. The smart-HTTP protocol's push endpoint is more sensitive to throttling than the REST API endpoints. Symptom: TCP/TLS handshake completes in seconds, then no progress for minutes.
- **SSH push to the same repo is fast**, even when SSH clone is slow. Observed: `git push https://...` stuck after 90s with 0 bytes transferred; switching the remote URL to `git@github.com:<o>/<r>.git` and re-pushing completed in < 30s for a ~90-commit fork with ~800 files. Oddly asymmetric — but reliable.
- Workflow: when push hangs over HTTPS, `git remote set-url origin git@github.com:<owner>/<repo>.git` and retry.

For one-file or few-file changes where you can't push at all (slow clone + slow push), use the Contents API directly — see `github-api-file-upload.md`.