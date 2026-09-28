---
name: github-cross-platform-mirror
description: "Push-triggered GitHub Actions mirror to gitee and gitcode."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [macos, linux]
tags: [github, gitee, gitcode, mirror, sync, actions]
metadata:
  hermes:
    tags: [github, gitee, gitcode, mirror, sync, actions]
    related_skills: [github-repo-management, github-actions-deploy-pipelines]
---

# GitHub → gitee/gitcode cross-platform mirror

Set up automatic push from a set of GitHub repos to gitee.com and gitcode.com whenever GitHub receives a commit. The mirror runs entirely on GitHub's own runners (so the user's local network to those platforms does not matter), and uses the user's API tokens for gitee/gitcode stored as GitHub Actions secrets.

## When to use

- "Mirror my GitHub repos to gitee and gitcode" / "sync my GitHub repos to Chinese git platforms" / "set up automatic push to gitee" / "配置 github 触发同步到 gitee/gitcode".
- User has multiple GitHub repos under one or more orgs (or personal namespace) that all need the same workflow.
- User wants a `push`-triggered GitHub Actions workflow — NOT cron-based (cron leaves a window of staleness; push is instant).

## What this skill does NOT cover

- Cron-based or pull-based mirror (use gitee/gitcode's own built-in mirror UI for that — it's free but 5-minute delayed).
- Bidirectional sync (push from gitee/gitcode back to GitHub). Only one-way: GitHub → gitee/gitcode.
- Non-gitee, non-gitcode targets. The auth URL formats are platform-specific.

## Outcome

After this skill runs, every `git push` to any branch of every mirrored GitHub repo will trigger a `git push 'refs/heads/*:refs/heads/*' '+refs/tags/*:refs/tags/*' --force` to the same-named repo under `eastspire` (or whatever the target namespace is) on both gitee and gitcode. End state verifiable by matching default-branch HEAD SHAs across all three platforms.

## Procedure

### 1. Discover repos across namespaces

Enumerate every GitHub repo the user owns across the namespaces that need mirroring. Use `/user/repos?visibility=all&affiliation=owner` — NOT `/users/{login}/repos`, which only returns public repos and silently misses private ones.

Filter out forks and archived repos before listing. The user will probably want to mirror owned non-fork non-archived only.

```python
import subprocess, json, os
GH_TOKEN = os.environ["GH_TOKEN"]  # export it, or get it from `gh auth token` — never hardcode
all_repos = []
for page in range(1, 6):
    r = subprocess.run([
        "curl", "-sS", "-H", f"Authorization: Bearer {GH_TOKEN}",
        f"https://api.github.com/user/repos?per_page=100&page={page}&visibility=all&affiliation=owner"
    ], capture_output=True, text=True, timeout=20)
    arr = json.loads(r.stdout)
    if not arr: break
    all_repos.extend(arr)
    if len(arr) < 100: break
target = [r for r in all_repos if not r['fork'] and not r['archived']]
```

For org-owned repos (`hyperlane-dev/*`, `euv-dev/*`, etc.), fetch each org separately with `/orgs/{org}/repos?type=member`.

**New repos are created private by default** — GitHub, and both mirrors, unless the user asks for
public in that turn. `github-repo-management` §2 owns that rule; this skill only has to make sure
the mirrors don't turn a private source into a public one.

### 2. Probe each target on gitee and gitcode

For every repo name from step 1, check whether it already exists on each platform. The HTTP status alone is enough — `200` means it exists, `404` means it doesn't.

```python
GITEE   = "<gitee_token>"
GITCODE = "<gitcode_token>"
for name in repo_names:
    g = curl -sS -o /dev/null -w "%{http_code}" \
        f"https://gitee.com/api/v5/repos/{target_ns}/{name}?access_token={GITEE}"
    c = curl -sS -o /dev/null -w "%{http_code}" \
        f"https://gitcode.com/api/v5/repos/{target_ns}/{name}?access_token={GITCODE}"
```

### 3. Create missing repos on gitee and gitcode via API

For each name missing on either platform, POST a create. **gitee and gitcode have different auth conventions for POST** (see platform quirks below):

**Visibility is inherited from the GitHub source, never hardcoded.** A private GitHub repo must
get private mirrors — creating a public mirror of a private source leaks it. Read `private` off
the GitHub repo object and pass it straight through:

```python
src = requests.get(f"https://api.github.com/repos/{owner}/{name}",
                   headers={"Authorization": f"Bearer {GH_TOKEN}"}).json()
priv = bool(src["private"])

# gitee: token in URL query, JSON body
requests.post("https://gitee.com/api/v5/user/repos",
    params={"access_token": GITEE},
    json={"name": name, "private": priv, "auto_init": False})

# gitcode: token in `private-token` HEADER, JSON body without token
requests.post("https://gitcode.com/api/v5/user/repos",
    headers={"private-token": GITCODE},
    json={"name": name, "private": priv, "auto_init": False})
```

New GitHub repos themselves default to private (`github-repo-management` §2) — so the common case
is `priv = True` on both mirrors. Use `auto_init: False` so the first mirror push does not collide
with a default-branch ref the platform added. Verify all 200/201, then confirm the visibility
actually landed (`GET /repos/{ns}/{name}` → `private` matches) — the create endpoint silently
ignores `private` for some accounts and defaults the mirror to public.

### 4. Push initial mirror from a local bare clone (one-shot catch-up)

This step is independent of the GitHub workflow — it pulls from GitHub and pushes once to gitee and gitcode so they have all the existing history. Run this BEFORE deploying the workflow so the first workflow trigger has nothing to do (just confirms parity).

```bash
mkdir -p "$WORKDIR/clones" && cd "$WORKDIR/clones"   # $WORKDIR is any scratch dir you control, e.g. under your home
git clone --bare "https://x-access-token:${GH_TOKEN}@github.com/${owner}/${name}.git" name.git

# gitee: token-embedded URL, https://<user>:<token>@gitee.com/...
git -C name.git push 'refs/heads/*:refs/heads/*' '+refs/tags/*:refs/tags/*' --force \
    "https://eastspire:${GITEE}@gitee.com/eastspire/${name}.git"

# gitcode: token-embedded URL uses oauth2: prefix, NOT a username
git -C name.git push 'refs/heads/*:refs/heads/*' '+refs/tags/*:refs/tags/*' --force \
    "https://oauth2:${GITCODE}@gitcode.com/eastspire/${name}.git"
```

macOS has no GNU `timeout` — wrap every clone/push with the Python wrapper at `scripts/timeout.py`:

```bash
scripts/timeout.py 900 git clone --bare ...   # 15-min timeout for big repos
```

**Big-repo clone tuning**: a 250 MB GitHub repo can take 8–15 minutes on a flaky link. Default 3-minute timeout is too tight. Use 900 seconds. If `git clone` still hangs with no progress, kill it and retry — network blips look identical to "still downloading".

### 5. Validate three-way HEAD parity

For every repo, fetch `commits?per_page=1` (GitHub) and `/commits?per_page=1` (gitee, gitcode) and compare the top SHA. They MUST match before deploying the workflow — otherwise the workflow's first push will be a no-op for the SHA-mismatched side and you will not know.

```python
def top_sha(platform, name): ...
```

A common false-negative: the mirror side looks "different" because its `default_branch` is set to an old feature branch (e.g. `feat/init-plugin-skeleton`), not `master`. The gitcode `default_branch` is whatever the first push landed on; if you push from a repo whose HEAD points to a non-master branch first, the platform's default branch becomes that branch. After the push, PATCH the platform's `default_branch` field:

```python
requests.patch(f"https://gitcode.com/api/v5/repos/{ns}/{name}",
    headers={"private-token": GITCODE},
    json={"default_branch": default_branch})
```

gitee accepts `default_branch` via PUT with the token in the URL query string.

### 6. Deploy the GitHub Actions workflow to every target repo

For every repo, do two API calls:

**(a) Set two repo secrets** (`GITEE_TOKEN`, `GITCODE_TOKEN`). GitHub requires the value to be **libsodium sealed-box encrypted** with the repo's public key. The full recipe is in `references/secret-encryption.py`; the gist:

```python
import requests, base64
from nacl import public
key = requests.get(f"https://api.github.com/repos/{owner}/{repo}/actions/secrets/public-key",
                   headers={"Authorization": f"Bearer {GH_TOKEN}"}).json()
pk = public.PublicKey(base64.b64decode(key['key']))
sealed = public.SealedBox(pk).encrypt(token_value.encode())
requests.put(f"https://api.github.com/repos/{owner}/{repo}/actions/secrets/{SECRET_NAME}",
    headers={"Authorization": f"Bearer {GH_TOKEN}", "Content-Type": "application/json"},
    json={"encrypted_value": base64.b64encode(sealed).decode(), "key_id": key['key_id']})
```

If `pynacl` is missing, `pip3 install pynacl` (macOS Xcode-shipped Python already has pip).

**(b) Write the workflow file** `.github/workflows/mirror.yml` via the Contents API:

```python
import base64, requests
content_b64 = base64.b64encode(WORKFLOW_YAML.encode()).decode()
body = {"message": "ci: add mirror sync workflow for gitee/gitcode",
        "content": content_b64, "branch": "master"}
# If file already exists, include its current sha to update
existing = requests.get(f"https://api.github.com/repos/{owner}/{repo}/contents/{path}?ref=master",
                        headers={"Authorization": f"Bearer {GH_TOKEN}"})
if existing.ok:
    body["sha"] = existing.json()["sha"]
requests.put(f"https://api.github.com/repos/{owner}/{repo}/contents/{path}",
    headers={"Authorization": f"Bearer {GH_TOKEN}", "Content-Type": "application/json"},
    json=body)
```

The exact YAML to write is in `templates/mirror.yml` — do NOT add a custom branch filter, the
`branches: ['**']` form (single-quoted YAML string) is intentional and works. The file is called
**`mirror.yml`, not `mirror-sync.yml`** — this is the canonical name used by `euv`, `hyperlane`
and `ctares`, and a new repo gets it at that path by default (see `github-repo-management` §2).

### 7. Verify the first workflow run

For one pilot repo, wait ~30s after the workflow file commit lands, then poll `actions/runs?per_page=3` and look for the workflow. Filter by `name == "Mirror"` (or whatever you named it). Read the run logs to confirm both `Push to Gitee` and `Push to GitCode` steps succeeded. Then re-run the three-way SHA parity check from step 5 — if it still matches, the platform is mirroring correctly.

**Only then** batch-deploy to the remaining N-1 repos.

## Platform auth URL formats (the easy-to-get-wrong part)

| Platform | Repo-exists probe | Create-repo auth | Push URL | Create auth header |
|---|---|---|---|---|
| **gitee** | `?access_token=TOKEN` query | same, JSON body | `https://USER:TOKEN@gitee.com/USER/REPO.git` | none (token in URL/body) |
| **gitcode** | `?access_token=TOKEN` query | **`private-token: TOKEN` HEADER**, body has no token | `https://oauth2:TOKEN@gitcode.com/USER/REPO.git` | `private-token: TOKEN` |

Two consequences worth memorizing:

1. **gitcode POST does NOT accept `access_token` in the body or URL** — the API will return `400 UN_KNOW: Invalid header parameter: private-token, required`. Pass the token in the `private-token` header and the body without it.
2. **gitcode push URL uses `oauth2:TOKEN`, not `USER:TOKEN`** — `USER:TOKEN` works on gitee but gitcode requires the literal `oauth2` username.

Git's credential helper is the portable way to read a token: `git credential fill` asks the
configured helper for a host and returns the username/password pair, so the same code works on
any machine regardless of where its credential file or keychain lives. Ask per-host and keep the
tokens separate — the github.com, gitee.com and gitcode.com entries are different credentials:

```python
def token_for(host):
    out = subprocess.run(['git', 'credential', 'fill'],
                         input=f'protocol=https\nhost={host}\n\n',
                         capture_output=True, text=True)
    return dict(l.split('=', 1) for l in out.stdout.splitlines() if '=' in l).get('password')

gh_pat = token_for('github.com')   # returns None when the helper has no entry for that host
```

If you grab the wrong one (e.g. use a gitcode token against the GitHub API), calls return 401 with no
useful body — symptom is a `GH_TOKEN` that actually holds the other platform's token.

## Workflow file (the only known-good shape)

The full YAML is in `templates/mirror.yml`. Key choices and why:

- `on.push.branches: ['**']` — push on ANY branch, not just master. Tag pushes also trigger.
- `permissions: contents: read` — no write token is needed; writes go via the user-supplied PAT-style secrets.
- `fetch-depth: 0, fetch-tags: true` — required so refs/tags have anything to push.
- **Explicit refspecs, not `--mirror`:** `git push <remote> 'refs/heads/*:refs/heads/*' '+refs/tags/*:refs/tags/*' --force`.
  `git push --mirror` also pushes refs/remotes/* and refs/pull/*, which gitee rejects with
  `deny updating a hidden ref`. The explicit refspecs are what makes first push land cleanly.
- **Retry with exponential backoff, 8 attempts:** `max_retries=8`, `delay=$((2 ** attempt))`
  (2s, 4s, 8s … capped by the attempt count), `timeout-minutes: 30` on the job. Chinese git
  platforms throttle and reset connections under load; a single-shot push fails intermittently
  for reasons unrelated to credentials.
- **Real failure, not a swallowed warning.** After the last attempt the step exits 1. A mirror
  that silently reports success while diverging from GitHub is worse than a red run — this is
  the user's explicit standing rule ("用户不要静默成功"). Do NOT downgrade this to `|| exit 0`.
- **Both platforms fail independently** — GitCode runs even if Gitee failed (separate steps,
  not a matrix), so one outage does not hide the other.
- `actions/checkout@v4` — works as of mid-2026. v3 is deprecated.

## Verification checklist (use after every batch)

After deploying to N repos, run this audit script. Anything not matching needs investigation before declaring done.

```python
# Pull from each platform's commits?per_page=1, compare top SHAs.
# Tolerate transient timeouts with 5 retries and 1.5s sleep.
```

Save the result as `mirror-audit.json` so the user can diff runs over time.

## Deleting mirrored repos

When the GitHub source repo goes away (deleted upstream, renamed, or the user has folded the crate into a monorepo under a new name), the corresponding gitee/gitcode mirrors become orphans and should be deleted in the same turn. The agent can fully automate this on gitee/gitcode; GitHub itself often needs manual deletion because the user's PAT lacks `delete_repo` scope.

```bash
# gitee: DELETE /repos/{ns}/{name}?access_token=TOKEN
curl -X DELETE -o /dev/null -w "%{http_code}" \
    "https://gitee.com/api/v5/repos/${NS}/${name}?access_token=${GITEE}"
# 204 No Content = success

# gitcode: DELETE /repos/{ns}/{name}?access_token=TOKEN (token also goes in private-token header)
curl -X DELETE -H "private-token: ${GITCODE}" -o /dev/null -w "%{http_code}" \
    "https://gitcode.com/api/v5/repos/${NS}/${name}?access_token=${GITCODE}"
# 204 No Content = success
```

After the DELETE, probe with the same `?access_token=TOKEN` GET — `404` confirms the repo is gone. Batch in one script (don't loop interactively). The mirror namespace is NOT always the source org: for `crates-dev/*` mirrors set up via this skill, the namespace is `eastspire/<old-name>` (the user's personal namespace), not `crates-dev/<old-name>` — probe both before deleting.

GitHub-side: `DELETE /repos/{owner}/{repo}` with the standard `repo` scope returns 403 with `Must have admin rights to Repository`. That 403 means the PAT lacks the separate `delete_repo` scope (response header `x-accepted-oauth-scopes: delete_repo`). The agent cannot fix this — tell the user to either (a) regenerate the PAT at https://github.com/settings/tokens with `delete_repo` checked, or (b) delete in the web UI at Settings → Danger Zone. Don't fabricate a workaround; the deletion is irreversible so user-managed execution is correct.

## Pitfalls

- **`/users/{login}/repos` returns only public repos even with auth.** Use `/user/repos?affiliation=owner&visibility=all` (with `?type=member` for org views) — verified gap between the two (27 public vs 34 owned including private).
- **gitee `.`-prefixed repo names fail first attempt, succeed on retry.** The first POST returns an error about `.` not allowed at start; retrying the same payload returns `id`. It is a transient gitee API bug, not a content issue. Always retry once before reporting "name rejected".
- **macOS has no GNU `timeout`.** `bash: timeout: command not found` even though brew has `coreutils` with `gtimeout`. Use the `scripts/timeout.py` wrapper, not `pip install timeout` (does not exist).
- **`git push --mirror` is not usable here.** It pushes refs/remotes/* and refs/pull/* too, which
  gitee rejects with `deny updating a hidden ref`. Use the explicit refspecs
  `'refs/heads/*:refs/heads/*' '+refs/tags/*:refs/tags/*' --force` (what `templates/mirror.yml`
  does). This is a workflow-shape problem, not a platform transient — re-dispatching won't fix it.
- **gitcode push URL must use `oauth2:` prefix, not the user.** Using `eastspire:$GITCODE` fails with auth error.
- **GitHub Actions runner cannot push back to itself.** Once the workflow pushes to gitee/gitcode, those pushes do NOT trigger another GitHub Actions run. No infinite loop risk.
- **Default-branch mismatch looks like "push failed" but is not.** If gitcode's `default_branch` is `feat/x` instead of `master`, the platform's `/commits?per_page=1` returns the feature branch tip — different from GitHub master tip — and the user will conclude push didn't work. The push did work; fix the default branch via `PATCH /repos/{}/{ }` with `{"default_branch": "master"}` and re-check.
- **PyNaCl encryption requires the repo's CURRENT public key.** Each repo has its own keypair. Use `/repos/{owner}/{repo}/actions/secrets/public-key` once per repo, never cache across repos.
- **Auth-token confusion in the git credential helper causes silent 401s.** The stored entries cover
  github.com, gitee.com and gitcode.com. Ask the helper per-host and use the one matching the API you
  are calling.
- **Adding `pull_request` trigger to a `push`-triggered workflow breaks existing CI if other jobs `needs: <push-only-job>`.** Not relevant to this skill's pure-mirror workflow (no `needs:` chains), but worth flagging if the user later extends with CI steps.
- **The GitHub Contents API rejects `auto_init: true` repos for the workflow path.** `auto_init: false` for the create step (so first push can land on master cleanly); if you let gitee/gitcode init with README, the first mirror push deletes their default branch's commit and replaces with yours, which gitee's master-protection will sometimes block.

## What "verified end-to-end" looks like

Three-way SHA parity on all repos after the first push-triggered workflow run. If even one repo shows a different top commit on gitee/gitcode vs GitHub, the workflow is not done — investigate before moving on.

The user's preference (recorded across two sessions): "全部直接提交代码，不需要 pr" — direct commit to master, no PR. Scoped 2026-09-27: mirror repos take push-triggered CI commits, which are direct by construction (there is no branch to PR from). Hand-authored code changes still follow the change-type rule in `git-standards` §3.3a — docs / config / comment-only direct-push, code via PR.
