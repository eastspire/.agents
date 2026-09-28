---
name: cross-platform-git-mirror
description: Mirror a GitHub repo to gitee and gitcode automatically.
version: 0.1.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [git, gitee, gitcode, github-actions, mirror, sync]
---

# Cross-platform git mirror (GitHub → gitee + gitcode)

GitHub is authoritative; gitee and gitcode are read-only mirrors driven by GitHub Actions `push` events. Use when the user asks to mirror a GitHub repo to one or both Chinese platforms.

## When to use this

- User says "提交到 GitHub 自动同步到 gitee/gitcode" / "GitHub push 后镜像到 X / Y".
- Source is GitHub (e.g. `eastspire/<repo>`); targets are user-owned namespaces on gitee / gitcode.

## Architecture

```
GitHub push event
    │ webhook
    ▼
GitHub Actions runner (ubuntu-latest)
    │ git push <refspecs> --force   (branches + tags, no refs/remotes)
    ├─→ gitee.com/<user>/<repo>
    └─→ gitcode.com/<user>/<repo>
```

**No feedback loop**: Actions triggers fire only on GitHub-side pushes; pushes to gitee/gitcode do not trigger GitHub Actions. Safe to use `push: branches: ["**"]`.

**GitHub is the only authoritative source.** `--mirror --force` overwrites everything on the targets. NEVER push from the user's machine to gitee/gitcode as a real workflow — only the Actions runner does.

## Phase gate (user preference)

When the user says "先做配置不要改代码" / "configure first", **stop at the workflow deployment step** and verify with the consistency audit before continuing. This is a phase gate, not a soft preference.

## Per-platform URL & auth

| Platform | Push URL | API create-repo | API auth |
|---|---|---|---|
| **gitee** | `https://USER:TOKEN@gitee.com/USER/REPO.git` | `POST https://gitee.com/api/v5/user/repos` (body: `access_token`, `name`, `private`, `auto_init`) | `?access_token=TOKEN` query on REST |
| **gitcode** | `https://oauth2:TOKEN@gitcode.com/USER/REPO.git` | `POST https://gitcode.com/api/v5/user/repos` (header: `private-token: TOKEN`, body: `name`, `private`, `auto_init`) | `private-token: TOKEN` header on REST |

Critical pitfalls:

- **gitcode `oauth2:` prefix is NOT optional.** `https://TOKEN@...` or `https://user:TOKEN@...` fail. Only `oauth2:TOKEN` works.
- **gitcode API rejects `access_token` in body** — must be `private-token` header. Error: `Orchestration error: Invalid header parameter: private-token, required`.
- **gitee rejects `.`-prefixed names intermittently** — its own docs say `.` allowed at start, validator fails on first try, succeeds on retry. Always retry once.
- **gitee/gitcode empty repos don't auto-activate `default_branch`** — first `--mirror` push lands content but `default_branch` stays null. PATCH after pushing:
  - gitee: `PUT /repos/USER/REPO?access_token=...&default_branch=master` (note: PUT not PATCH)
  - gitcode: `PATCH /repos/USER/REPO` with `{"default_branch":"master"}`, header `private-token`
- **gitcode PATCH returns success but GET doesn't echo `default_branch`** — verify via `GET /repos/USER/REPO/branches` (each branch has `default_branch: true|false`).

## Phase 1 — Probe (no writes)

```bash
# GitHub (use PAT, not unauthenticated /users/<u>/repos which omits private)
curl -H "Authorization: Bearer $GH_TOKEN" \
  "https://api.github.com/user/repos?per_page=100&visibility=all&affiliation=owner"

# gitee / gitcode probe per repo — 200 = exists, 404 = needs creation
curl -o /dev/null -w "%{http_code}" "https://gitee.com/api/v5/repos/USER/REPO?access_token=$GITEE"
curl -o /dev/null -w "%{http_code}" "https://gitcode.com/api/v5/repos/USER/REPO?access_token=$GITCODE"
```

## Phase 2 — Create missing repos

**Visibility is inherited from the GitHub source, never hardcoded.** New repos are private by
default (`github-repo-management` §2), so the mirror of a private repo must be private too — a
public mirror of a private source leaks it. Read `private` off the GitHub repo object and pass it
through.

```bash
# gitee (token in body)
curl -X POST -H "Content-Type: application/json" \
  -d '{"name":"REPO","access_token":"'$GITEE'","private":'$IS_PRIVATE',"auto_init":false}' \
  https://gitee.com/api/v5/user/repos

# gitcode (header not body)
curl -X POST -H "Content-Type: application/json" -H "private-token: $GITCODE" \
  -d '{"name":"REPO","private":'$IS_PRIVATE',"auto_init":false}' \
  https://gitcode.com/api/v5/user/repos
```

`auto_init: false` is critical — init'd repo has a master commit that conflicts with the first mirror push. Empty repo accepts the push cleanly.

After the 201, confirm the visibility actually landed (`GET /repos/USER/REPO` → `private` matches
the source) — the create endpoint silently ignores `private` for some accounts.

## Phase 3 — GitHub Actions setup

### 3a. Write secrets via API

GitHub encrypts `secrets.*` values with the repo's RSA public key.

```python
import json, os, subprocess, base64
from nacl import encoding, public

key = json.loads(subprocess.check_output([
    "curl","-sS","-H",f"Authorization: Bearer {GH_TOKEN}",
    f"https://api.github.com/repos/{OWNER}/{REPO}/actions/secrets/public-key"
]))

def encrypt(public_key_b64, plaintext):
    pk = public.PublicKey(public_key_b64.encode(), encoding.Base64Encoder())
    sealed = public.SealedBox(pk).encrypt(plaintext.encode())
    return encoding.Base64Encoder().encode(sealed).decode()

for name, value in [("GITEE_TOKEN", GITEE_TOKEN), ("GITCODE_TOKEN", GITCODE_TOKEN)]:
    body = json.dumps({"encrypted_value": encrypt(key["key"], value), "key_id": key["key_id"]})
    subprocess.run([
        "curl","-sS","-X","PUT",
        "-H",f"Authorization: Bearer {GH_TOKEN}",
        "-H","Content-Type: application/json",
        "-d", body,
        f"https://api.github.com/repos/{OWNER}/{REPO}/actions/secrets/{name}"
    ], capture_output=True, text=True)
```

**Misleading response**: PUT returns `{}` on BOTH success and silent failure. Verify with GET:

```bash
curl -H "Authorization: Bearer $GH_TOKEN" \
  "https://api.github.com/repos/$OWNER/$REPO/actions/secrets"
# New name must appear in secrets[] with updated_at recent
```

### 3b. Write the workflow file (Contents API)

```python
# Canonical copy lives in the sibling skill's templates/ dir; expanduser keeps it
# portable — never bake a machine-local absolute path into this skill.
TEMPLATE = os.path.expanduser(
    "~/.hermes/skills/github-cross-platform-mirror/templates/mirror.yml")
content_b64 = base64.b64encode(open(TEMPLATE, "rb").read()).decode()
body = json.dumps({
    "message": "ci: add mirror sync workflow for gitee/gitcode",
    "content": content_b64,
    "branch": "master",  # or repo's actual default
})
subprocess.run([
    "curl","-sS","-X","PUT",
    "-H",f"Authorization: Bearer {GH_TOKEN}",
    "-H","Content-Type: application/json",
    "-d", body,
    f"https://api.github.com/repos/{OWNER}/{REPO}/contents/.github/workflows/mirror.yml"
])
```

### 3c. The workflow file (verified working)

**Do not paste the YAML by hand.** Copy `github-cross-platform-mirror/templates/mirror.yml` —
byte-identical to what `euv` / `hyperlane` / `ctares` ship at `.github/workflows/mirror.yml`:

```bash
curl -s -X PUT -H "Authorization: Bearer $GH_TOKEN" -H "Content-Type: application/json" \
  https://api.github.com/repos/$OWNER/$REPO/contents/.github/workflows/mirror.yml \
  -d "$(python -c 'import base64,json,sys; print(json.dumps({
        "message": "ci: add mirror sync workflow for gitee/gitcode",
        "content": base64.b64encode(open(sys.argv[1],"rb").read()).decode(),
        "branch": sys.argv[2]}))' \
        ~/.hermes/skills/github-cross-platform-mirror/templates/mirror.yml master)"
```

The properties that matter, and why you must not "simplify" them:

- **File name is `mirror.yml`**, not `mirror-sync.yml`, and it lives at `.github/workflows/mirror.yml`.
  Same path in every repo — that is what makes the default work.
- **Explicit refspecs instead of `git push --mirror`**: `'refs/heads/*:refs/heads/*' '+refs/tags/*:refs/tags/*' --force`.
  `--mirror` also pushes refs/remotes/* and refs/pull/*, which gitee rejects with
  `deny updating a hidden ref`.
- **8 attempts with `2 ** attempt` backoff**, `timeout-minutes: 30`. Both Chinese platforms
  throttle and reset connections under load; a single-shot push fails for reasons unrelated to
  credentials.
- **A real failure exits 1**, it does not `|| exit 0` behind a `::warning::`. A mirror that
  reports success while silently diverging from GitHub is the worst outcome. The user does not
  accept silent success.
- **Two independent steps**, not a matrix — gitee failing must not hide gitcode's state.
- `actions/checkout@v4` with `fetch-depth: 0, fetch-tags: true`; `permissions: contents: read`.

## Phase 4 — Verify (always end-to-end)

### Per-repo: three-way HEAD sha comparison

```python
def top_sha(platform, repo):
    if platform == "github":
        r = curl(f"https://api.github.com/repos/{repo}/commits?per_page=1",
                 headers={"Authorization": f"Bearer {GH_TOKEN}"})
    elif platform == "gitee":
        r = curl(f"https://gitee.com/api/v5/repos/eastspire/{repo}/commits?access_token={GITEE}&per_page=1")
    elif platform == "gitcode":
        r = curl(f"https://gitcode.com/api/v5/repos/eastspire/{repo}/commits?access_token={GITCODE}&per_page=1")
    return json.loads(r)[0]["sha"][:10] if json.loads(r) else "EMPTY"

gh, g, c = top_sha("github", "eastspire/REPO"), top_sha("gitee", "REPO"), top_sha("gitcode", "REPO")
match = "✓" if (gh == g == c and gh != "EMPTY") else "✗"
```

**This catches default-branch drift**: if gitee/gitcode's `default_branch` is set to a stale feature branch (e.g. `feat/init-plugin-skeleton`), `/commits?per_page=1` returns that branch's top commit, which won't match GitHub's master HEAD. Fix with PATCH as in Phase 2 notes.

### Per-repo: workflow execution check

```bash
curl -H "Authorization: Bearer $GH_TOKEN" \
  "https://api.github.com/repos/$OWNER/$REPO/actions/runs?per_page=1"
# Expect: status=completed, conclusion=success

curl -H "Authorization: Bearer $GH_TOKEN" \
  "https://api.github.com/repos/$OWNER/$REPO/actions/runs/$RUN_ID/jobs"
# Expect: each step in mirror job has "conclusion": "success"
```

## Pitfalls (generalizable)

- **`timeout` is GNU-only.** macOS doesn't ship it. Wrap long-running commands with a Python helper:
  ```python
  #!/usr/bin/env python3
  import subprocess, sys
  secs = int(sys.argv[1])
  p = subprocess.Popen(sys.argv[2:])
  try: sys.exit(p.wait(timeout=secs))
  except subprocess.TimeoutExpired:
      p.kill(); p.wait(); sys.exit(124)
  ```
  Use `python3 _timeout.py 900 git clone --bare …` for big repos (250MB+) where network stalls are common.

- **HTTPS pushes to GitHub from China-throttled hosts stall mid-pack.** Symptoms: `RPC failed; curl 92 HTTP/2 stream … was not closed cleanly: CANCEL`, `N bytes of body are still expected`, `fetch-pack: unexpected disconnect`. Mitigation: 15-minute per-repo timeout, accept partial clones and retry — subsequent `--mirror` push will refetch.

- **First-time token push to a repo may be blocked by gitee/gitcode backend** even if API "create" succeeded. Symptom: `git push` returns 403 "Forbidden" / "no permission". User must enable "Token push" / "Access Token push" in the repo's web UI. List per-run failures and tell the user.

- **`--mirror --force` semantics**: pushes ALL refs (branches + tags), overwriting whatever's on the remote. Any commits the user made directly on gitee/gitcode (e.g. README edits in web UI) get overwritten on next sync. GitHub is the only authoritative source — tell the user upfront.

- **No `if:` guard needed to prevent loops.** GitHub Actions triggers only fire for events on the GitHub repo. Pushes to gitee/gitcode do not flow back. Don't add `if: github.repository == '…'` — it's noise here.

- **Token name conventions**: GitHub Actions secret names must match exactly (case-sensitive) — `GITEE_TOKEN` / `GITCODE_TOKEN`. Mismatch surfaces as `::error::GITEE_TOKEN secret is missing` in workflow logs.

- **Before decommissioning a "central config" repo that the mirror workflow consumed (e.g. a local helper that wrote remote URLs into `.git/config`), verify no live code still reads it.** Mirror-driven configs are usually a one-shot: each downstream repo's `.git/config` already stores its own remotes after the first run, so deleting the central config is safe weeks later. But that only holds because the workflow did its one-shot — if a new consumer script is added after the original run that re-reads the config on every invocation, deletion breaks all consumers silently. Audit with `grep -rn "<config name>" --include="*.toml" --include="*.rs" --include="*.sh" --include="*.yml"` across all known consumer repos before deleting. Treat "no live readers" as a precondition for the delete; surface it in the commit body so reviewers see the audit.