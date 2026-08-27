---
name: rust-crate-docs-html-sync
description: "Sync downstream docs HTML to upstream Rust crate releases."
license: MIT
---

# Sync Downstream Docs HTML Against Upstream Rust Crate Release

## The class of work

You have two repos:

1. **Upstream source repo** — Rust workspace, e.g. `euv-dev/euv` (`~/github/euv-dev/euv/`), `hyperlane-dev/hyperlane`. Authoritative for current API/source/README content.
2. **Downstream docs HTML repo** — flat HTML rendering of the upstream docs, e.g. `docs-pages/pages` (`~/github/docs-pages/pages/`). Each `.html` file mirrors one topic from upstream's README + source files.

The task is: **after an upstream release, propagate the relevant changes to the downstream HTML and open a PR.**

This skill covers the **triage + execution + PR workflow** for that cycle. It is NOT about editing the upstream crate (use `rust-standards` / `rust-crate-use` for that), and NOT about the build pipeline that originally rendered the HTML.

## Step 0 — Is sync even needed?

**Triage the upstream version bump before touching HTML.** Open `references/commit-theme-triage.md` for the full decision matrix. Short version:
- `feat:` / `feat(` ... `)` in the diff → new public API / surface → almost certainly needs HTML updates
- `fix:` → behavioral fix → check if HTML describes the buggy behavior, fix it
- `docs:` / `docs(` ... `)` ONLY → no API change → check if HTML quotes the doc text verbatim; usually no-op or trivial patch
- `refactor:` / `style:` / `chore: bump version` / `chore: sync ... version` / `cargo-toml` sort → pure internals, **no public surface change** → sync is almost always a no-op

**This is the most important step.** A 0.13.6 → 0.14.x release that's entirely `chore: bump version` + `refactor:` + `style:` commits means the downstream HTML **already reflects the source** — only the version-string text inside HTML (if any) needs touching.

Verified 2026-08-27 on euv 0.13.6 → 0.14.2: 28 commits, all `chore/refactor/style/docs` — actual HTML diff ended at 4 lines (two stale `0.1.0` references). PR body should explicitly call out "this version bump is pure docs/style, no public API change" so reviewers know the small diff is intentional.

## Step 1 — Identify the source repo + version

```bash
# local clone of upstream crate (eastspire is admin on these orgs)
cd ~/github/euv-dev/euv   # or crates-dev/<crate>, hyperlane-dev/<crate>
git log --oneline -5
git tag --sort=-creatordate | head -3
# confirm vs crates.io (proxy via tuna mirror)
export PATH=/root/.cargo/bin:$PATH
cargo search <crate> --limit 1 --registry crates-io
```

## Step 2 — Identify the downstream HTML repo + current state

```bash
cd ~/github/docs-pages/pages   # or wherever the published-HTML repo lives
# What commits are on master?
git log --all --oneline | head -10
# Any pending branches with "0.13.6"-style names that didn't get pushed?
git branch -a | grep -E 'docs|crate|sync' || true
# Has Vercel already auto-deployed the upstream changes? (look for "Deploy from @" signature)
git log --oneline | grep 'Deploy from'
```

If the master history is **only `Deploy from @<sha>` commits**, the HTML has been auto-rebuilt from upstream's source — usually already up to date.

## Step 3 — Find the content delta

Two recipes, pick whichever matches the user's framing:

### 3a) "Sync euv 0.14.2" — diff upstream README/source against current HTML

For each upstream sub-crate (`cli/`, `engine/`, `ui/`, `macros/`), read the relevant `README.md` + the source files that were touched in the version bump range:

```bash
cd ~/github/euv-dev/euv
git diff v0.13.6..HEAD -- cli/README.md
git diff v0.13.6..HEAD --stat -- 'engine/src/*/mod.rs'
```

Then in the downstream HTML, look for each touched section title (or its anchor `id="..."`):

```bash
cd ~/github/docs-pages/pages
grep -n "<h[23] id=\"" euv/cli/install.html   # see what sections exist
grep -n "<h[23] id=\"" euv/usage-introduction/engine.html
```

If a new section appears upstream but no matching `id` exists downstream → **add the section**.

### 3b) "Delete X directory" / "Update Y references" — narrow the search

When the user wants a structural change (delete a page, rename a nav item), the diff is much smaller:

```bash
# find every reference to the thing being removed
cd ~/github/docs-pages/pages
grep -rln "development-standards\|开发规范" --include="*.html" .
# in HTML files, single-line minified files need Python for the actual match-extraction
python3 -c "
import re
for f in open('catalog.html').read().splitlines(): pass
# ... or use execute_code() to extract block-level matches cleanly
"
```

For minified HTML (everything on one line), `grep -n` is misleading — match positions are accurate, **block extraction is a Python job**:

```python
# Find and print the li block containing a target string, so you can patch the whole <li>
import re
html = open('catalog.html').read()
pat = re.compile(r'<li[^>]*vp-catalog-item[^>]*>(?:(?!<li[^>]*vp-catalog-item).)*?TARGET(?:(?!</li>).)*?</li>', re.DOTALL)
for m in pat.finditer(html): print(m.group())
```

## Step 4 — Apply the changes

Three tool modes:

| Change | Tool |
| --- | --- |
| Delete whole file | `git rm <path>` |
| Replace inline text (small, in minified HTML) | `patch` with mode='replace' on the whole `old_string` chunk |
| Insert a new section | `patch` on a sentinel anchor unique to the insertion point; **never** mid-string on a 200KB line — use Python via `execute_code` to write a new file with the insertion |
| Whole-file rewrite (e.g. adding a 5-module chapter block to engine.html) | `execute_code` to do `open(path,'w').write(html[:idx] + new_block + html[idx:])` then `git add` |

After every edit, validate the HTML didn't break:

```python
import re, os
for f in modified:
    html = open(f).read()
    div_open = len(re.findall(r'<div\b', html))
    div_close = len(re.findall(r'</div>', html))
    assert div_open == div_close, (f, div_open, div_close)
    assert html.rstrip().endswith('</html>'), f
    # No leftover references to deleted paths
    assert '/pages/development-standards/' not in html or f in keep_files, f
```

## Step 5 — Commit + PR

Use `github-pr-workflow` for the standard flow. Specifics for docs HTML sync:

- **Branch name**: `chore/<descr>-sync-euv-0.14.2-YYYY-MM-DD` (or `docs/...` if touching a known docs section). Date suffix avoids collisions if you re-run.
- **Commit subject**: `<type>(<scope>): <subject>` where scope is the HTML repo's directory name (`pages` for docs-pages/pages). Body in **English**, conventional commits style. Per user ironclad rule (see `gh-pr-creation-workflow` §"PR body 风格"): all public-Repo commit messages are English.
- **PR base**: `master` (or whatever the build-output repo's deploy branch is — usually `master`, sometimes `main`).
- **PR body** must include:
  1. **Source sync table** — what upstream version, what commit range, what files were diffed
  2. **What was found in HTML** — explicitly: which sections were already present, which were missing, which version strings were stale
  3. **What was changed** — files + line counts, with the deltas called out
  4. **Verification** — `grep` results showing no leftover references, div balance, file ends with `</html>`
  5. **Notes** — was the work a no-op because upstream was docs-only? Was an old un-unged branch discovered?

If the diff is tiny (4 lines / 2 stale version refs), **call it out explicitly**: "This is a pure-style release; the HTML content was already current via upstream merges; this PR cleans up two stale version references."

## Step 6 — Eastspire-Owned Orgs

All four orgs under user's eastspire (`hyperlane-dev`, `crates-dev`, `euv-dev`, `docs-pages`) — push **directly to upstream**, no fork. Reference `github-pr-workflow` §"Eastspire-Owned Orgs" for the recipe and the fork-disabled exception.

For `docs-pages/pages` specifically:
- `origin` remote is often the eastspire fork that may have been deleted (branch shows `:gone`). Use the `upstream` remote instead — see `github-pr-workflow` for the recipe, or my memory entry on "GH_TOKEN 加载".
- `upstream/master` is the only branch that matters; everything else is bot commits.
- The repo's history being dominated by `Deploy from @<sha>` (Vercel signature) is normal and expected — don't read it as "stale".

#### Common pitfalls

1. **Assuming the sync is needed.** Always run Step 0 first. A 0.13.6 → 0.14.x release with only `chore: bump version` + `refactor:` + `style:` commits is a no-op for content. Misclassifying it as "needs full sync" will produce an empty PR that wastes reviewer time.
2. **Forgetting that `pages/` is a build-output repo.** Even when the user explicitly says "edit the HTML", you MUST call out in the PR body that `pages/` is auto-deployed and the diff will only land if a separate source repo (`docs-pages/docs` private sibling) is the actual source. See `github-pr-workflow` §Pitfalls "Editing the build product" and `references/build-product-vs-source-repo.md`.
3. **Mid-string patches on 200KB minified HTML.** `patch` with old/new strings works only if both fit on the same line. For blocks that span 5–10 KB of minified content, write a Python replacement via `execute_code`. The `old_string` for `patch` must be **unique** in the file; minified HTML often has repeated `<span class="..."><span style="...">` boilerplate — include enough surrounding context (e.g. a unique `id="..."` anchor) to make the match unique.
4. **Leaving stale "X.1.0 / X.0.0" version refs in HTML after a sync.** Even if the content is otherwise current, literal version strings like `euv-engine 0.1.0` in a renderer-intro paragraph are wrong after every minor bump. Always grep `<html-repo>/> --include="*.html" -rn 'X.* 0\.[0-9]+'` and patch any literal that no longer matches the latest version.
5. **Trying to reconstruct an un-unged branch.** If you discover a branch like `docs/euv-0.13.6-updates` that was never pushed to upstream, its content has likely already been merged via auto-deploy commits. Don't try to "complete" or merge that branch — just create a new branch on `upstream/master` and layer the new diffs on top. Mention the discovered branch in the PR body for traceability.
6. **Pushing to the wrong remote.** Local clones of eastspire-owned repos sometimes have `origin = eastspire/<repo>` (personal fork / mirror) and `upstream = <org>/<repo>` (the real one). Push to `upstream`, not `origin`. Verify with `git remote -v` before the first push.
7. **Forgetting to set `user.name`/`user.email` if the container lacks git config.** In containers with no global git identity, use `git -c user.name='eastspire' -c user.email='root@ltpp.vip' commit ...` inline. Saves a `git config` round-trip.
8. **Not validating HTML after patches.** Minified HTML with a single misplaced `</div>` will render as a blank page in production. Always run the div-balance + ends-with-`</html>` check on every modified file before commit.

## Related

- `github-pr-workflow` — full PR lifecycle, fork decision, CI monitoring
- `gh-pr-creation-workflow` — eastspire/.agents PR style (English body, conventional commits, README files via heredoc)
- `rust-crate-use` — querying crates.io / docs.rs for the **target** version
- `rust-standards` — when the sync surfaces a code-level issue that needs upstream fix
- `agent-skills-source-sync` — sibling pattern for syncing `.agents/skills/*/SKILL.md` content (Hermes-side, not user-HTML-side)
- `references/commit-theme-triage.md` — detailed decision matrix for "is sync even needed"
- `references/build-product-vs-source-repo.md` — Vercel/Netlify/Cloudflare Pages detection