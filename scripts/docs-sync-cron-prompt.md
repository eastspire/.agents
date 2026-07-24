You are running as a scheduled cron job (every 6h). Your job is to keep three local skill documents in sync with the upstream code they describe. You are NOT in an interactive chat — finish autonomously and return a short structured report.

## 1. Scope (the only three files you may touch)

Target skills (in this repo, branch `master`):
- `C:\Users\14915\.agents\skills\euv\SKILL.md`      ← upstream: euv-dev/euv
- `C:\Users\14915\.agents\skills\euv-app\SKILL.md`  ← upstream: euv-dev/euv-app
- `C:\Users\14915\.agents\skills\hyperlane\SKILL.md`← upstream: hyperlane-dev/hyperlane

Do NOT touch any other file under `C:\Users\14915\.agents\`. In particular, do NOT modify any `README.md` outside the three target SKILL.md files (the user has flagged that drift).

## 2. Upstream repos (already cloned, freshly synced by `sync-docs-repos.sh`)

- `C:\Users\14915\.cache\docs-update\euv\`        — branch `master`, default
- `C:\Users\14915\.cache\docs-update\euv-app\`    — branch `master`, default
- `C:\Users\14915\.cache\docs-update\hyperlane\`  — branch `master`, default

The script `C:\Users\14915\.agents\scripts\sync-docs-repos.sh` already ran before this session. **Run it again now yourself** to make sure you have the freshest code, and capture the output (HEAD SHAs) for your PR description:

```bash
bash /c/Users/14915/.agents/scripts/sync-docs-repos.sh 2>&1 | tee /tmp/sync-docs-output.txt
```

The `_backup_user_dump/` directory under `~/.cache/docs-update/` is the user's manual source dump — leave it alone, never delete or clone into it.

## 3. Diff procedure (the part that needs real judgment)

For each of the three target SKILL.md files:

1. **Read the current SKILL.md** end-to-end. Note which APIs, modules, config options, code snippets, and behavioral claims are documented.
2. **Inventory the upstream code**: walk the source tree, focusing on `lib.rs`/`mod.rs`, public `pub fn`/`pub struct`/`pub enum`/`pub trait`, `Cargo.toml` features and dependencies, examples, and the project README. Also check `git log --oneline -50` for recent changes since the last sync (find the previous sync point by reading the most recent "Last verified" line in the SKILL.md, if present).
3. **Build a drift list**:
   - **New public API** not in SKILL.md → must be added
   - **API removed/deprecated** in upstream → must be removed from SKILL.md
   - **API whose signature/behavior changed** → must be corrected
   - **New feature/example/Cargo.toml field** that SKILL.md should mention
   - **Wrong/stale claims** (e.g. edition, license, crate count, module layout, signature, behavior) → must be fixed
4. **Edit the SKILL.md** to resolve every drift item. Use `patch`/`write_file`/`read_file` as appropriate. Preserve the user's existing voice and section structure — this is a diff-based update, not a rewrite.
5. **Honesty rule**: if you claim an API exists in the doc, it must exist in the code. If you cite a code snippet, it must compile against the current upstream. If the doc describes a behavior, you must have read the actual macro/impl, not inferred from naming. Reject "looks like" / "probably does X" claims.

Do NOT delete working examples or accurate sections just to "freshen" the doc. Drift fix ≠ wholesale rewrite.

## 4. Build verification (mandatory before commit)

For euv and euv-app, run a workspace check to confirm your cited code still compiles:

```bash
cd "/c/Users/14915/.cache/docs-update/euv"        && cargo check --workspace --quiet 2>&1 | tail -20
cd "/c/Users/14915/.cache/docs-update/euv-app"    && cargo check --workspace --quiet 2>&1 | tail -20
cd "/c/Users/14915/.cache/docs-update/hyperlane"  && cargo check --quiet 2>&1 | tail -20
```

If cargo isn't installed, `command -v cargo` first; if missing, log it and continue — don't block on toolchain.

If you cited any Rust snippet in the diff, ensure it still parses against the current `Cargo.toml` (rough check: features exist, dependency versions line up, module paths still resolve). Fix any snippet that would fail.

## 5. If nothing changed

If after step 3 the drift list for a repo is empty, do not edit that SKILL.md. Still include that repo in the PR title/body as "no drift detected" so the user knows it was checked. If ALL three are empty, do not create a PR — just print a one-line report and exit.

## 6. Commit + branch + PR (always create one PR per run that has any change)

Work from the user's agents repo. Use a single branch for this run that bundles all three SKILL.md changes; user reviews once per cron tick:

```bash
cd /c/Users/14915/.agents
git fetch origin master
git checkout -b "docs/sync-$(date -u +%Y%m%d-%H%M)" origin/master
git add skills/euv/SKILL.md skills/euv-app/SKILL.md skills/hyperlane/SKILL.md
git commit -m "docs(skills): sync euv, euv-app, hyperlane from upstream

- euv: <one-line summary of drift items, or 'no drift'>
- euv-app: <one-line summary, or 'no drift'>
- hyperlane: <one-line summary, or 'no drift'>

Sync run at $(date -u +%Y-%m-%dT%H:%M:%SZ)"
git push -u origin HEAD
gh pr create --fill-verbose --base master --head "docs/sync-$(date -u +%Y%m%d-%H%M)"
```

`gh` is already authenticated as `eastspire` via keyring. `--fill-verbose` pulls the commit body into the PR description automatically. Don't include `--no-maintainer-edit` — let the user amend freely.

If `git push` fails because the branch name already exists (race with a previous cron tick), append `-$(date +%s)` to the branch name and retry once.

If `gh pr create` fails with "no commits between master and branch" (means the SKILL.md files didn't actually change), delete the branch locally and remotely and exit without a PR.

## 7. Final report (the only thing this cron delivery carries)

After everything, print a short structured summary the user can scan in <10s:

```
docs-sync <UTC timestamp> <overall outcome>
  euv       <# items changed> | upstream <short-sha> "<commit msg>"
  euv-app   <# items changed> | upstream <short-sha> "<commit msg>"
  hyperlane <# items changed> | upstream <short-sha> "<commit msg>"
branch: docs/sync-<YYYYMMDD-HHMM>
pr: <URL or "none — no drift">
errors: <none | short list>
```

If you encountered any error, surface it explicitly — do not silently swallow.

## 8. Hard constraints

- This cron session has a 10-minute inactivity timeout by default (`HERMES_CRON_TIMEOUT=600s`). Stay well under that — `cargo check` on euv can take 30-60s the first time. If you risk exceeding it, stop at the most recent commit and report what you did/didn't get to. Don't leave the working tree dirty (commit partial work, then write a follow-up note in the report).
- Do NOT modify `~/.agents/.skill-lock.json`, `~/.agents/skills/*/SKILL.md.lock` files, or any lock/state file under `~/.agents/.hermes/`.
- Do NOT run `cargo update` or `cargo publish`. Read-only verification only.
- If you need to delegate, do not — finish inline. Subagents add latency you can't afford.
- Skills loaded: rust-standards, euv-standards (if present), hyperlane (if present). Use them for project-specific conventions.