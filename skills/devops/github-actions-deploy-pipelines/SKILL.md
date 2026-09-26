---
name: github-actions-deploy-pipelines
description: 'Use when editing GitHub Actions deploy workflows.'
---

# GitHub Actions deploy pipelines

Operating and hardening `workflow_dispatch` / `schedule` / `workflow_run`-driven deploy workflows — the kind that build a static site and push the output somewhere (GitHub Pages repo, artifact repo, rsync target). Covers triggers (cron schedules, workflow_run chains), concurrency control, artifact-push races, and post-merge run verification. For PR/issue/gh-CLI mechanics use the `github` skill family; this skill is only about the Actions side.

## 1. Triggers

- **`schedule` cron is always UTC.** Convert local intent explicitly and write the conversion into a comment so the next editor doesn't "fix" it back:
  ```yaml
  on:
    schedule:
      # daily 01:00 Beijing time = 17:00 UTC
      - cron: "0 17 * * *"
  ```
- A newly merged `schedule:` / `workflow_run:` trigger **does not fire on merge and is not validated by GitHub until it fires**. Always force one manual run to prove the pipeline end-to-end (§3).
- `workflow_run` only fires for workflows that exist **on the default branch** of the same repo — a trigger naming a workflow that doesn't exist (renamed/deleted) silently never runs. Grep the workflows directory before trusting it.

## 2. Concurrent deploy runs racing an artifact push

Pattern that breaks: the job checks out a second "pages" repo, wipes it, copies fresh build output, commits, `git push origin master`. A burst of triggers (rapid pushes, a new cron overlapping a push) starts concurrent runs that all checked out the same base SHA — first push wins, the rest die at the very end with:

```
! [rejected]  master -> master (fetch first)
error: failed to push some refs
```

Fix with **both** layers (verified 2026-08-29 on `docs-pages/docs` → `docs-pages/pages`, where 2 of 3 racing runs failed exactly like this):

```yaml
# top of the workflow — serialize runs, never cancel mid-deploy
concurrency:
  group: deploy-pages
  cancel-in-progress: false
```

```bash
# in the push step — rebase the deploy commit onto the latest remote;
# the site is fully regenerated each run, so the fresh build wins conflicts
git add -A
git diff --cached --quiet || git commit -m "Deploy from @${{ github.sha }}"
git fetch origin master
git rebase -X theirs origin/master || git rebase --abort
git push origin master
```

`-X theirs` in rebase context favors the commit being replayed (the fresh deploy commit) — correct for generated artifacts; never hand-merge build output.

## 3. Post-merge verification

A green PR merge says nothing about the next workflow run. After merging any workflow-file change:

```bash
gh workflow run <file>.yml --repo <org>/<repo>          # force one run
RUN=$(gh run list --repo <org>/<repo> --workflow <name> --limit 1 --json databaseId --jq '.[0].databaseId')
gh run watch $RUN --repo <org>/<repo> --exit-status --interval 30
```

Then check the wider health — trigger bursts reveal races the single manual run won't:

```bash
gh run list --repo <org>/<repo> --workflow <name> --limit 5
gh run view <run-id> --repo <org>/<repo> --log-failed   # read any red one before declaring done
```

## 4. Adding `pull_request` to an existing `push`-only workflow

When a workflow was set up for `push: branches: [master]` only (typical for projects where the maintainer publishes after merge), adding `pull_request` is the right move so contributors get format / lint / test / build feedback before review. But the job-graph evaluation is non-obvious:

- **`sync_workspace_version` (or any job that does `git push`)** must be gated to push events: `if: github.event_name == 'push' && github.ref_name == 'master'`. On PR it has no write token and would try to push back to the contributor's branch.
- **`publish` / `release` (any job that needs secrets like `CARGO_REGISTRY_TOKEN` and `contents/packages: write`)** must be gated the same way. PR tokens are read-only by design; they exist exactly so untrusted fork code can't exfiltrate secrets.
- **Build/test/clippy jobs** must keep `needs: <sync_job>` for the master path (so they wait for the version sync), but run on PR too. The formula:
  ```yaml
  jobs:
    check:
      needs: sync_workspace_version
      if: always() && (github.event_name == 'pull_request' || (github.event_name == 'push' && needs.sync_workspace_version.result == 'success'))
  ```
  The `always()` is the key: without it, a skipped upstream on PR also skips the downstream (default `needs: success()` treats `'skipped'` as not success), so the entire CI silently becomes "all skipped" on PR. See the pitfalls section for the verification recipe.

## Pitfalls

- **Cron times documented without timezone** — the next editor reads "0 1 * * *" as local and shifts it. Always comment both UTC and local.
- **Serializing with `cancel-in-progress: true`** — kills a half-finished deploy and can leave the artifact repo with a partial push window; deploy queues use `false`.
- **Rebasing generated artifacts without `-X theirs`** — conflicts on regenerated assets block the run on an interactive editor prompt that never comes in CI; the job just dies.
- **Only watching the run you triggered** — a concurrent push-triggered run may be the one that fails; check `gh run list` for the whole workflow, not just your run.
- **Adding `pull_request` to a workflow with `needs: <push-only-job>` and expecting downstream to run** — `needs: <job>` defaults to `needs: success()`. When the upstream job is **skipped** (because its own `if:` gates it to `push`), GitHub Actions treats its result as `'skipped'`, which is not `'success'`, so every downstream job is skipped too. The whole CI on PR silently turns into "everything skipped" with no error. Verified on euv `rust.yml` PR #70 first push: 7 jobs created, all 7 skipped. Always pair `pull_request` trigger with `if: always() && (event-condition || other-condition)` on downstream jobs, then re-apply the gating logic inside the condition.
- **Verifying a workflow trigger change by reading the YAML** — the YAML parsing is fine; the failure mode is the GitHub Actions job-graph evaluation that only runs on a real trigger. Always smoke-test trigger changes on the very PR that introduces them. If `gh pr checks <N>` shows the new job as `skipped` instead of `in_progress`, the `if:` is wrong and the CI did not actually verify the code.
- **Binary subprocesses inherit the runner's `current_dir`, not the user's project tree**. A CLI that runs `euv build` (or any tool) with `current_dir = <CLI's manifest_dir>` and forwards a *relative* `--out-dir` will silently write into the CLI's source tree, not the user's project. Symptom is `private artifacts under <CLI repo>/www/` while the user's `<out_dir>/` has only the public asset tree (no `index.html`, no `pkg/`). The fix lives in the CLI (resolve the relative `--out` against `env::current_dir()` before forwarding), but the workflow-side diagnostic is: `ls <user out_dir>` after build and confirm `index.html` + `pkg/` are both present. If `www/` is missing `pkg/`, the relative-path bug bit — don't waste cycles on `euv build`/wasm-pack flags.
- **Cross-repo push needs the target PAT, not the source GITHUB_TOKEN**. Failure message is the workflow log showing `git push origin master` failing with `could not read Username for 'https://github.com'`. Check `secrets.DOCS_REP_PAS` (or whatever name was used) is actually present via `gh api repos/<org>/<repo>/actions/secrets --jq '.secrets[].name'` — if empty, the workflow has never had the secret and `persist-credentials: true` silently had nothing to persist.
- **`git push --mirror` to a non-GitHub forge triggers "deny updating a hidden ref"** — gitee and gitcode both reject `--mirror` pushes because `--mirror` also pushes the local `refs/remotes/origin/*` tracking refs, which the receiving forge interprets as protected "hidden refs". The push log shows `+ master -> master (forced update)` followed immediately by `! [remote rejected] origin/master -> origin/master (deny updating a hidden ref)` and `error: failed to push some refs`. **Retry does NOT fix this** — gitee's protection is stateful, not transient; 8 retries all fail identically. Fix: use `git push <remote> 'refs/heads/*:refs/heads/*' '+refs/tags/*:refs/tags/*' --force` to push only branches and tags. Confirmed on `euv-dev/euv` mirror workflow: `--mirror` failed all 9 attempts with the same error; switching to explicit refspec succeeded on attempt 1.
- **Mirroring workflow's `|| exit 0` silently swallows real failures** — the pattern `git push gitee --mirror --force 2>&1 || { echo "::warning::..."; exit 0; }` makes the step succeed even when the push failed. Across many repos this looks like "everything is green" while gitee/gitcode are silently stale. Either remove the `exit 0` (so a real failure makes the run red and surfaces the problem) or wrap the push in a retry loop that fails after N attempts (`exit 1` after the loop). Pair with retry semantics: `while attempt <= max_retries; do attempt++; if git push ...; then exit 0; fi; sleep $((2**attempt)); done; exit 1`. Exponential backoff `2^n` seconds matches the `crate-cli` publish retry shape so the user already has the mental model.
- **Default branch is per-repo, not per-org** — a batch deploy that hardcodes `branch: master` in a `PUT /repos/<o>/<r>/contents/<path>` body (used to write a workflow file via the Contents API) will fail with `Branch master not found` on every repo whose default is `main`. Fetch each repo's `default_branch` from `GET /repos/<o>/<r>` first and parameterize the body field. Confirmed across a 48-repo batch deploy: 10 repos returned `default_branch=main`, 38 returned `master`, and one had no workflow at all yet. Iterating per-repo with the fetched branch is the only correct path.
- **Secrets encryption is libsodium sealed-box, not raw RSA** — `PUT /repos/<o>/<r>/actions/secrets/<NAME>` requires `encrypted_value` to be a base64-encoded sealed box over the repo's X25519 public key (fetched from `GET .../actions/secrets/public-key`). `pynacl` is the canonical Python library; install via `pip install pynacl` if missing. The full 8-line recipe is in §8 above; copy it verbatim rather than improvising.

## 5. Cargo release pipelines (`cargo install`-friendly)

For Rust projects that publish a binary to crates.io so users can `cargo install <crate>`:

### Tailor the template to the project shape

The euv `rust.yml` is a multi-job workspace setup with `sync_workspace_version` (rewrites inline + sub-table `[workspace.dependencies.<pkg>].version` + every member's `package.version`) and a wasm32 build step. **Drop both** for a single-crate project — they reference non-existent workspace members and waste CI minutes. Minimum pipeline for a single crate:

```
setup → check / tests / clippy / build → publish → release
```

`sync_workspace_version` and `--target wasm32-unknown-unknown` only matter if the project has multiple crates or ships to wasm.

### `Cargo.toml` exclude vs `cargo install`

`exclude = ["Cargo.lock"]` in `[package]` does **not** prevent `Cargo.lock` from landing in the published `.crate` — cargo's hard rule is that `cargo package` and `cargo publish` always include `Cargo.lock` so downstream `cargo install` can resolve a reproducible dependency graph. So a lib+bin project can keep the rust-standards `exclude = ["Cargo.lock"]` (which only affects git and `cargo package --no-verify` listings) without breaking `cargo install`. Verified locally:

```
$ cargo package --list | grep -i lock
.cargo_vcs_info.json
Cargo.lock
```

### `.gitignore` blocks `.github/`

If the project's `.gitignore` lists `.github/` (some templates do — e.g. when the maintainer previously ran a local-only CI), the new workflow file under `.github/workflows/*.yml` is silently never committed, and the pipeline never fires. After adding `.github/workflows/`, immediately check `git status` shows the YAML as a new file, not ignored.

### Smoke-test the built binary in the build job

`cargo build --release` alone proves the code compiles — it does not prove the binary runs. Add a build-job step that backgrounds the binary and curls a known endpoint:

```yaml
- name: Smoke test binary
  run: |
    ./target/release/${{ needs.setup.outputs.package_name }} &
    PID=$!
    sleep 2
    curl -sf http://127.0.0.1:7842/health || { kill $PID; exit 1; }
    kill $PID
```

Catches runtime panics, wrong bind address, and missing config files that compilation hides.

## 6. Manual `gh workflow run` vs automatic push trigger

`gh workflow run <file>.yml --repo <org>/<repo>` only works on workflows that declare `workflow_dispatch`. A `push`-triggered workflow does **not** need a manual dispatch — pushing the commit triggers it automatically, and `gh run watch` immediately picks it up. If the workflow has no `workflow_dispatch`, the dispatch call fails with:

```
HTTP 422: Workflow does not have 'workflow_dispatch' trigger
```

Just push the commit and watch — no manual run needed.

## 7. Diagnosing missing secrets

A publish job failing with:

```
please paste the token found on https://crates.io/me below
error: credential provider `cargo:token` failed action `login`
Caused by: please provide a non-empty token
```

…means the GitHub repo secret `CARGO_REGISTRY_TOKEN` is unset or empty. Confirm by reading the workflow log: an empty value renders as `CARGO_REGISTRY_TOKEN: \n` (or just whitespace) on the `env:` line. `gh secret list --repo <org>/<repo>` returning empty is consistent with the secret being absent for the same user, but a fine-grained PAT with restricted scopes can also report empty — the workflow log is the source of truth. Remediation: `Settings → Secrets and variables → Actions → New repository secret`, name `CARGO_REGISTRY_TOKEN`, value from `https://crates.io/me/`.

## 8. Cross-repo pushes: source repo workflow → different target repo

Pattern that breaks the standard Pages flow: the **source** repo (where the build runs) needs to write into a **different** target repo (e.g. `docs-pages/docs-euv` building → pushing `master` of `docs-pages/pages`). GitHub's built-in `GITHUB_TOKEN` is scoped to the source repo only — it cannot push to a sibling repo, and `actions/deploy-pages@v4` is hard-wired to a Pages host on the source repo. Need a PAT in a repo secret and a `actions/checkout@v4` with `repository:` + `token:` to materialize it on disk.

```yaml
- name: Checkout source
  uses: actions/checkout@v4

- name: Checkout target (different repo)
  uses: actions/checkout@v4
  with:
    repository: <org>/<target-repo>
    path: __target
    persist-credentials: true    # lets the later `git push` reuse the token
    token: ${{ secrets.DOCS_REP_PAS }}

# … build, write to ./www …

- name: Push to target
  run: |
    set -euo pipefail
    cd __target
    # wipe everything except .git/, copy fresh build, commit, rebase, push
    find . -maxdepth 1 -not -name '.git' -not -name '.' -not -name '..' -exec rm -rf {} +
    cp -r ../www/* .
    git config user.name "eastspire"
    git config user.email "root@ltpp.vip"
    git add -A
    git diff --cached --quiet || git commit -m "Deploy from @${GITHUB_SHA}"
    git fetch origin master
    git rebase -X theirs origin/master || git rebase --abort
    git push origin master
```

Two details that bite:

- **`persist-credentials: true` is required** — without it, the `git push` step can't re-authenticate and dies with `could not read Username for 'https://github.com'`.
- **`permissions: contents: read` on the source workflow is enough** — the write happens via the target's PAT, not via GITHUB_TOKEN. Adding `contents: write` to the source workflow does nothing for cross-repo writes.

### Creating the `DOCS_REP_PAS` (or any cross-repo PAT) secret via API

When `Settings → Secrets` is not available headless, use the GitHub API. The endpoint requires the secret value to be **sealed-box encrypted** with the repo's public key (libsodium sealed box, not raw RSA).

```python
import json, base64, urllib.request
from nacl import public

# 1) fetch the repo's public key (admin only)
req = urllib.request.Request(
    f'https://api.github.com/repos/{owner}/{repo}/actions/secrets/public-key',
    headers={'Authorization': f'token {admin_token}', 'Accept': 'application/vnd.github+json'},
)
key = json.loads(urllib.request.urlopen(req).read())

# 2) encrypt the PAT (or any string) using libsodium sealed box
pk = public.PublicKey(base64.b64decode(key['key']))
encrypted = public.SealedBox(pk).encrypt(pat_value.encode('utf-8'))

# 3) PUT the encrypted value
req = urllib.request.Request(
    f'https://api.github.com/repos/{owner}/{repo}/actions/secrets/{SECRET_NAME}',
    method='PUT',
    headers={
        'Authorization': f'token {admin_token}',
        'Content-Type': 'application/json',
        'Accept': 'application/vnd.github+json',
    },
    data=json.dumps({
        'encrypted_value': base64.b64encode(encrypted).decode('utf-8'),
        'key_id': key['key_id'],
    }).encode('utf-8'),
)
urllib.request.urlopen(req)  # 201 Created
```

If `pynacl` isn't installed, `pip install pynacl`. The encryption is correct as long as the public key is fetched at request time and the response includes both `key_id` and `key` (base64 32-byte X25519).

Confirm with `gh api repos/<org>/<repo>/actions/secrets --jq '.secrets[].name'`. If it returns empty, the secret wasn't actually created (the `PUT` may have returned 200 with an empty body on some key-id mismatches).

### Required tools not on `ubuntu-latest`

The runner image lacks `wasm-pack` even when the project needs it (euv-docs CLI shells out to `wasm-pack build` via `euv build`). Add an init step:

```yaml
- name: Install wasm-pack
  run: curl https://rustwasm.github.io/wasm-pack/installer/init.sh -sSf | sh
```

Place it **before** any step that invokes the downstream tool. Failing at "Failed to execute wasm-pack: No such file or directory" mid-build is the symptom — the build looks like a Rust compile error but is actually a missing binary.

## 9. Cross-forge mirroring: GitHub → gitee / gitcode

Pattern: push the same source-of-truth repo on every push to one or more non-GitHub forges, with a separate per-forge access token in `secrets`. Verified working shape (see `references/forge-mirroring.md` for the full provider quirks):

```yaml
on:
  push:
    branches: ['**']
  workflow_dispatch:
permissions:
  contents: read
jobs:
  mirror:
    name: Push
    runs-on: ubuntu-latest
    timeout-minutes: 30
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
          fetch-tags: true

      - name: Push to Gitee
        env:
          GITEE_TOKEN: ${{ secrets.GITEE_TOKEN }}
          REPO_NAME:   ${{ github.event.repository.name }}
        run: |
          if [ -z "$GITEE_TOKEN" ]; then echo "::error::missing"; exit 1; fi
          git remote remove gitee 2>/dev/null || true
          git remote add gitee "https://eastspire:${GITEE_TOKEN}@gitee.com/eastspire/${REPO_NAME}.git"
          # Branches + tags only. NEVER `git push --mirror`: it also pushes refs/remotes/origin/*
          # which gitee rejects with "deny updating a hidden ref" (see Pitfalls).
          git push gitee 'refs/heads/*:refs/heads/*' '+refs/tags/*:refs/tags/*' --force
```

Two facts that bite if not designed in up-front:

- **Per-forge URL auth shape is different.** gitee wants `https://user:TOKEN@host/owner/repo.git`. gitcode wants `https://oauth2:TOKEN@host/owner/repo.git` — using `?access_token=...` query (works for read) returns 200 with no auth on push. See `references/forge-mirroring.md` for the full provider matrix.
- **Default branch varies per repo, not per org.** A batch deploy that hardcodes `branch: master` in the `PUT /contents` body will fail on every repo whose default is `main`. Fetch each repo's `default_branch` from GitHub API first and parameterize. Full API recipe + secrets-encryption snippet is in `references/forge-mirroring.md`.

Adding retry to a cross-forge push is the same shape as §8 — bash `while attempt <= max; do try; done` with exponential backoff. Default 8 attempts × `2^attempt` seconds matches the project's `crate-cli` publish retry shape, so users who know one already know the other.
