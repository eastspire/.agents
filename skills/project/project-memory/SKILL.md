---
name: project-memory
description: "eastspire/org facts: repos, PR flow, version rules."
license: MIT
version: 1.0.0
author: Hermes Agent + eastspire
metadata:
  hermes:
    tags: [project, registry, eastspire, docs-pages, euv-dev, hyperlane-dev, crates-dev]
    related_skills: [euv, hyperlane, gh-pr-creation-workflow, git-standards, rust-standards, github-pr-workflow]
---

# Project memory — eastspire/org

## When to use

Load this skill when:

- The user mentions any eastspire-owned repo by short name (docs / euv / hyperlane / crates / ltpp) or full name (docs-pages/docs, euv-dev/euv, hyperlane-dev/*, crates-dev/*).
- You're about to edit, clone, push to, or open a PR against any of those repos.
- The user asks "where is X", "how do we sync Y", "what's our rule for Z", or "what's the current version".
- The user says "based on latest version source" or similar — check the version policy before assuming.
- You're unsure which repo a request targets.

Update via `skill_manage(action='patch')` when a fact changes, with a brief rationale in the new content. Anything in here overrides a memory entry with the same topic; memory is for session-level preferences only.

## Repository registry

All repos live under `~/github/<owner>/<repo>/` (per `repo-projects` user preference — never `~/euv`, never inside `~/.hermes/`).

### `eastspire` GitHub organizations

| Org              | Purpose                              | Admin/permission model                          |
| ---------------- | ------------------------------------ | ----------------------------------------------- |
| `hyperlane-dev`  | hyperlane Rust framework repos       | eastspire admin, but **fork + PR** (orgs are non-personal; rule changed 2026-08-28) |
| `crates-dev`     | Rust crates release                  | eastspire admin, but **fork + PR**               |
| `euv-dev`        | euv UI framework repos               | eastspire admin, but **fork + PR** (`eastspire/euv` fork exists) |
| `docs-pages`     | Eastspire documentation site         | eastspire admin, but **fork + PR**; `docs-pages/docs` has fork disabled → Contents API flow below |

### Key repos — what lives where

| Repo                                 | Owner/org            | What it is                                                | Editing rule                                                  |
| ------------------------------------ | -------------------- | --------------------------------------------------------- | ------------------------------------------------------------- |
| `docs-pages/docs`                    | docs-pages           | VuePress source: `src/**/*.md`, sidebar/navbar/config.ts | **Source of truth** for the docs site. Edit here.              |
| `docs-pages/pages`                   | docs-pages           | Vercel build output: `*.html` + assets                    | **Do NOT edit by hand** — `Deploy from @<sha>` commits overwrite it. UI rebuilds on next deploy. |
| `euv-dev/euv`                        | euv-dev              | The euv framework Rust source (workspace, 6 member crates) | Fork + PR — push feature branches to the `eastspire/euv` fork, PR with `--head eastspire:<branch>`. |
| `euv-dev/euv-cli`                    | euv-dev              | Standalone CLI binary crate                               | Same as above (fork + PR).                              |
| `euv-dev/euv-core` / `euv-engine` / `euv-macros` / `euv-ui` / `euv-example` | euv-dev | The 6 member crates                  | Same as above (fork + PR).                              |
| `crates-dev/*`                       | crates-dev           | Crates-dev release repositories                           | Fork + PR.                                               |
| `hyperlane-dev/*`                    | hyperlane-dev        | hyperlane framework repos (incl. `hyperlane-quick-start`) | Fork + PR (`eastspire/hyperlane-quick-start` fork exists). |

### Short-name → repo mapping (user vocabulary)

- **"docs"** / **"文档站"** / **"the doc site"** → `docs-pages/docs` (VuePress source). **Not** `docs-pages/pages`.
- **"euv"** / **"the framework"** → `euv-dev/euv` for source code; **`docs-pages/docs/src/euv/`** for the docs section.
- **"hyperlane"** → `hyperlane-dev/*` repos.
- **"crates"** / **"crates-dev"** → `crates-dev/*` repos.
- **"ltpp"** → the LTPP suite of web tools. Docs at `docs-pages/docs/src/ltpp/`; apps live on the LTPP Vercel host.

If unsure which repo a request refers to, **ask before editing** — the wrong repo silently overwrites your changes on next deploy.

## PR / commit flow

### Hard rules

1. **Non-personal repos: all code changes go through PR** — no direct push to base branches there. Personal repos (`eastspire/*`) are exempt: direct push to `master` is allowed (rule changed 2026-08-28).
2. **Fork-first for every non-personal repo** (rule changed 2026-08-28) — the 4 eastspire orgs (`euv-dev`, `docs-pages`, `crates-dev`, `hyperlane-dev`) count as non-personal: `gh repo fork <org>/<repo>` once per repo (the `eastspire/<repo>` forks for `euv` and `hyperlane-quick-start` already exist), push feature branches to the **fork**, open the PR against the org repo with `--head eastspire:<branch>`.
3. **Personal repos: no fork, no PR** — repos under the `eastspire` **user account** itself (e.g. `eastspire/.agents`) accept direct commits + pushes to `master`. Forking your own personal repo fails with "single user account cannot own both parent and fork", and the PR step is explicitly waived.
4. **Exception: `docs-pages/docs` is private with fork disabled** — skip the fork, use the Contents API + git refs flow below (direct branch on upstream is the only option).
5. **PR body / commit message in English** — every public PR/issue/commit on these orgs uses English, three conventional sections (`## Summary` / `## Verification` / `## Notes`), no Chinese. Applies to commit messages too (rule extended 2026-08-27).
6. **`gh pr edit` for GraphQL fields silently fails** when `GH_TOKEN` lacks `read:org` scope. Fall back to REST `PATCH /repos/<owner>/<repo>/issues/<N>` (PRs share the issue endpoint) to update body/title without force-push/reopen.

### Standard recipe (org / third-party repo — fork-first)

```bash
# 1. Fork once per repo (skip when eastspire/<repo> already exists)
gh repo fork <owner>/<repo> --clone=false
# 2. Branch from upstream master
git fetch upstream && git checkout -b <type>/<descr>-YYYY-MM-DD upstream/master
# 3. Make changes, commit
git add -A
git -c user.name='eastspire' -c user.email='root@ltpp.vip' commit -m "<type>(<scope>): <subject>"
# 4. Push the branch to the FORK (local convention: `origin` = fork, `upstream` = source repo;
#    e.g. ~/github/euv-dev/euv has origin → eastspire/euv, upstream → euv-dev/euv)
git push -u origin <branch>
# 5. PR with the fork as head
gh pr create --repo <owner>/<repo> --base master --head eastspire:<branch> --title "..." --body-file /tmp/pr-body.md
```

For personal repos (`eastspire/*`): skip everything — commit directly on `master` and `git push origin master`. No fork, no branch, no PR.

### For large repos where `git checkout <tree>` times out

Use the **Contents API + git refs API** flow (verified on `docs-pages/docs` — 466 files, git checkout 28+ min, Contents API <2 min):

1. `POST /repos/<owner>/<repo>/git/refs` — create branch from `master` SHA.
2. For each modified file: `GET .../contents/<path>?ref=<branch>` (get current blob SHA) → `PUT .../contents/<path>` with `{message, branch, sha, content}`.
3. For each deleted file: same shape but `DELETE` method, omit `content`.
4. `gh pr create --base master --head <branch> ...`.
5. Cleanup: `DELETE /repos/<owner>/<repo>/git/refs/heads/<branch>` after PR merge.

The Contents API creates one commit per call; the diff is identical to a single batched git push. Rate-limit budget is 5000 req/hour per token; large file edits stay well under.

### Build-script / install-time file drift — reset before commit

`docs-pages/docs` has two files that change **on every `yarn install` or `yarn build`** without your edits touching them. They show up in `git status` after install/build and must be reset before staging:

| File | When it drifts | What it does | Reset |
| --- | --- | --- | --- |
| `package.json` | `yarn install` (yarn 4 normalizes key order alphabetically) | No semantic change, just key reordering | `git checkout HEAD -- package.json` |
| `src/.vuepress/sidebar.js` | `yarn build` (calls `node plugin/creat-sidebar.js` which regenerates the file from `ls src/`) | Real content drift — drops entries whose source dir is gone, adds entries for newly-added dirs (e.g. `/server-manager`, `/udp`, `/udp-request`); also strips trailing newline | `git checkout HEAD -- src/.vuepress/sidebar.js` |

These drifts are NOT caused by your edits and should NEVER be bundled with your fix's commit. After `yarn install` and `yarn build`, run:

```bash
git status --short | awk '{print $2}' | xargs -I{} git diff --quiet HEAD -- {} || \
  git checkout HEAD -- package.json src/.vuepress/sidebar.js
git status --short   # should now show only your intended files
```

Verified 2026-08-29 on `docs-pages/docs` (yarn 4.10.3 + vuepress 2.0.0-rc.26 + hope-theme 2.0.0-rc.101).

### Local build output path ≠ committed deploy path

The build script's `dest: resolve(__dirname, '../../pages')` writes to a **new sibling** `docs/pages/` inside the source checkout, NOT to the committed deploy path `~/github/docs-pages/pages/` (which is what Vercel reads). The committed `pages/` is a separate git repo (or directory) that Vercel auto-pushes to.

Implication for local testing:

- `yarn build` produces artifacts at `~/github/docs-pages/docs/pages/` (the `pages/` inside the source tree).
- Built HTML references assets as `/pages/assets/app-<hash>.css` etc. (base path = `/pages/`).
- To serve locally: `mkdir -p /tmp/docs-serve && ln -s ~/github/docs-pages/docs/pages /tmp/docs-serve/pages && python3 -m http.server 8765 -d /tmp/docs-serve` — then hit `http://localhost:8765/pages/`.
- DO NOT serve from `~/github/docs-pages/docs/pages/` directly — the asset URLs would resolve to `http://localhost:8765/assets/...` (404) instead of `/pages/assets/...`.

Verified 2026-08-29.

### Headless iPhone safe-area testing — `env()` returns 0 on Linux Chrome

Linux headless Chrome **cannot simulate iOS notch safe-area insets**. With viewport-fit=cover set, `env(safe-area-inset-top)` still resolves to `0px` — the OS doesn't have a notch to report. To verify a safe-area CSS rule fires correctly, **inject a CSS override that forces the computed value** instead of trying to fake the env():

```python
# Inject what env(safe-area-inset-top) WOULD return on an iPhone 14 Pro (47px)
page.add_style_tag(content="""
    .vp-navbar {
        padding-top: calc(47px + var(--navbar-padding-y)) !important;
        height: calc(var(--navbar-height) + 47px) !important;
    }
""")
# Now measure: navbar height should = original-height + 47px, logo top should = 47 + original-padding-y
```

Setting `--safe-area-inset-top: 47px` as a CSS custom property and reading it via `var()` does NOT work either — `env()` and `var()` are separate. Only the `env()` runtime call reads from the OS; `var()` reads from CSS custom properties. To verify the rule logic, substitute the env() expression with the hard-coded value it would compute to.

Verified 2026-08-29 on Chromium 138 + Playwright (Linux, no iOS emulation available). The 3-state verification pattern (no-notch baseline / simulated notch / desktop ≥768px) is the minimum to claim "no regression + correct on notch devices + desktop untouched".

### Safe-area fix recipe — `c_app_root`-style for any fixed-top element

When porting euv's `c_app_root` / `c_mobile_app_root` safe-area pattern to a non-euv site (e.g. VuePress hope-theme's `.vp-navbar`), the full recipe is:

1. **Add `viewport-fit=cover` to the viewport meta** in the framework config (VuePress: `src/.vuepress/config.ts` `head[]`):
   ```html
   <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
   ```
   Without this, `env(safe-area-inset-*)` always returns `0px` on iOS notch devices.

2. **Mobile-only (`@media (max-width: 767px)`)** — for `position: fixed; top: 0` elements, set:
   ```css
   .vp-navbar {
     padding-top: calc(env(safe-area-inset-top, 0px) + var(--navbar-padding-y));
     height:      calc(var(--navbar-height)      + env(safe-area-inset-top, 0px));
   }
   ```
   Just adding padding-top WITHOUT growing height leaves the logo overflowing — the box can hold `padding-top + padding-bottom + content` only as much as its fixed height allows. Grow height too.

3. **Desktop (`@media (min-width: 768px)`)** — leave untouched; hope-theme / framework default behavior preserved.

The reference implementation is `c_app_root` in `euv/ui/src/style/class/fn.rs`:
```rust
pub c_app_root {
    padding-top: var!(safe-area-inset-top);
    padding-bottom: var!(safe-area-inset-bottom);
    // ...
}
```
plus `c_mobile_app_root` which sets all four sides to `safe-area-inset-*`. The docs-pages fix (2026-08-29, PR open against `docs-pages/docs`) is the first external port of this pattern.

## Version policy

### docs仓 (docs-pages/docs)

- **Only the latest version is maintained.** No version banners, no "适用于 euv 0.x" callouts, no "euv 0.13.x" headers, no "(euv X.Y)" parentheticals.
- Documented examples reflect the **current** state of the source; if the source changes, the doc changes (sync, not fork).
- **Exception**: Demo/example data inside code blocks (`let version: &str = "0.8.29";`) is fine — it's a value, not a version statement.
- Search before editing euv sections: `grep -rn "euv[\s-].*0\.[1-9]\.\d\|0\.1[3-9]\.\d"` should return 0 matches in body (frontmatter `version: '*'` is fine).

### Cargo.toml version bumps (euv, hyperlane-quick-start, and every Rust repo here)

When the user says **"升级版本" / "bump the version"** (rule extended 2026-08-28 — previously euv-only, now applies to `euv-dev/*` **and** `hyperlane-dev/hyperlane-quick-start` alike):

- Bump **one place only**: the root `Cargo.toml`'s **first** `version` field — the `[package] version` line (e.g. `euv`: `0.16.0`; `hyperlane-quick-start`: `23.0.36`).
- **Do not** touch `[workspace.dependencies]` path-dep `version` fields, **do not** touch sub-crate `package.version` — the `sync_workspace_version` CI job propagates root → all members.
- **Do not** sed-replace `version = "X.Y.Z"` globally — collides with third-party dep versions (e.g. `qrcode = "0.14.2"`). Use Python TOML parsing to edit only the root `[package]` section.

### Source-of-truth for "what's the current euv version"

- `euv-dev/euv` master HEAD's `[package] version` line.
- crates.io: `cargo search euv --limit 5 --registry crates-io`.
- These should match after every release PR merges.

## Naming conventions

- Branch names: `<type>/<scope>-<short-desc>-YYYY-MM-DD` (e.g. `docs/fn-no-doc-audit-2026-08-27`, `chore/remove-dev-standards-sync-euv-0.14.2-2026-08-27`). Type ∈ {feat, fix, refactor, docs, perf, test, ci, chore, style, build}.
- Commit subjects: same conventional-commits style as branch.
- euv sub-crate layout: each `fn` and `impl` lives in its own file: `<name>/fn.rs`, `<name>/impl.rs`, `<name>/struct.rs`, `<name>/enum.rs`, `<name>/type.rs`, `<name>/const.rs`. `mod.rs` is 3-line `pub use` + `pub mod`. `lib.rs` does all imports; other files use `super::*`.
- euv component folder: `ui/src/component/<name>/` with `view/{fn.rs, impl.rs}`, `struct.rs` for Props, `enum.rs` for variant enums, `hook/{fn.rs, impl.rs}` for state helpers.

## Local host facts

- Sandbox/VM identity: **VM-24-7-opencloudos** (Alibaba Cloud Linux).
- `/` is 60 GB and fills fast — `/tmp/cargo-*.log`, `/tmp/c-*.log`, browser-use temp dirs (`cp-inspect-*` / `cp-tab-*` / `cp-shot-*` ~600MB each) accumulate. `/tmp/chrome-linux` (~658MB) is browser-use runtime bundle — keep, or move to `~/LTPP-MINIMAX/`.
- Cargo: rustc 1.97.1, `euv-cli 0.13.6` / `euv-cli 0.14.2` (post-bump), `hyperlane-cli 0.1.25`. PATH does **not** include `~/.cargo/bin` by default — `export PATH=/root/.cargo/bin:$PATH` before any cargo call.
- Cargo registry: `/root/.cargo/config.toml` uses Tsinghua tuna mirror. `cargo search` without `--registry crates-io` errors with "non-remote-registry"; install/build still work.
- Working directory gotcha: a `cd <deleted-dir>` from a previous session makes the **terminal** hang on exit-code 126. Workaround: pass `workdir=/abs/path` to `terminal()` instead of chaining `cd`.
- Long-timeout command pattern: `git clone` over SSH from GitHub through GFW can take 28+ minutes for ~120MB repos. Default terminal timeout (180s) SIGTERMs mid-download. Pattern: `terminal(background=true, notify_on_complete=true)`, then `process(action='wait', timeout=600)`.
- GitHub auth: `GH_TOKEN` in `/root/.bashrc.d/gh_token.sh`. Sandbox doesn't auto-inherit — export manually: `TOKEN=$(grep -oP 'export GH_TOKEN="\\K[^"]+' /root/.bashrc.d/gh_token.sh); GH_TOKEN=$TOKEN gh ...`.

## Skills ↔ project mapping

When a task involves a project below, load the entry skill first, then the standards skill it points to:

| Skill                         | Project                                                        | What it covers                              |
| ----------------------------- | -------------------------------------------------------------- | ------------------------------------------- |
| `euv` (entry)                 | euv framework                                                  | API/pitfall cheatsheet; loads `euv-standards`, `euv-ui-standards` |
| `euv-standards`               | euv framework                                                  | Complete API table + 13-class pitfall list   |
| `euv-ui-standards`            | euv framework                                                  | 306 design tokens + 22 `euv_*` components    |
| `euv-app`                     | euv example app                                                | Tauri 2.x Android packaging                  |
| `euv-html-macro-traps`        | euv framework                                                  | 9 html! macro pitfalls                        |
| `euv-engine-design`           | euv-engine                                                     | `Engine` zero-sized façade contract          |
| `euv-hook-context-collision`  | euv framework                                                  | `HookContext::current()` thread_local hazards |
| `hyperlane` (entry)           | hyperlane framework                                            | Hyperlane API + pitfalls                     |
| `hyperlane-standards`         | hyperlane framework                                            | Full API + pitfall list                      |
| `hyperlane-upload`            | hyperlane framework                                            | Deploy to ltpp.vip                           |
| `docs-rs-api-fetcher`         | all crates                                                     | Pulls docs.rs / crates.io live data          |
| `gh-pr-creation-workflow`     | all PRs                                                        | gh CLI PR lifecycle cheatsheet               |
| `github-pr-workflow`          | all PRs                                                        | Full PR lifecycle with fork decisions        |
| `github-issue-to-pr`          | all repos                                                      | Issue → PR pipeline                          |
| `git-standards`               | all repos                                                      | Commit + PR conventions                      |
| `rust-standards`              | all Rust                                                       | Auditable Rust coding rules                  |
| `code-formatting-tools`       | all langs                                                      | Format MD/YAML/TOML/Rust/web before commit  |
| `rust-pr-contribution-workflow` | external Rust crates                                          | External crate PR pipeline                   |
| `rust-pr-validation-checklist` | external Rust crates                                          | Pre-PR validation                            |
| `rust-cargo-mirror-setup`     | local dev                                                      | Cargo mirror config (TUNA)                   |
| `computer-use`                | desktop automation                                             | cua-driver behind-the-scenes control         |
| `obsidian`                    | local notes                                                    | Obsidian vault read/write                    |

## Out of scope for this skill

- Per-task session progress → use `session_search`, not this skill.
- User identity / preferences → memory (this skill defers to memory on those).
- Hermes Agent internals → `hermes-agent` skill (autonomous-ai-agents/).