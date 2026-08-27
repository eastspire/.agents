# `docs-pages/docs` vs `docs-pages/pages` — which to edit

The `docs-pages/*` org has **two private repos** with confusingly similar names. The skill description and history focus on `pages` (the Vercel HTML build output), but the user's "docs" / "文档站" colloquialism refers to **`docs-pages/docs`** — the VuePress markdown source.

| Repo | Holds | Built by | Edit target? | Local path |
| --- | --- | --- | --- | --- |
| `docs-pages/docs` | VuePress markdown source (`src/**/*.md`, `src/.vuepress/*.ts`) | manual commits + Vercel CI | **YES** | `~/github/docs-pages/docs` |
| `docs-pages/pages` | Vercel HTML build output (`*.html`, `assets/`) | Vercel auto-deploy bot | **NO** | `~/github/docs-pages/pages` |

## How to tell which is which in <10 seconds

```bash
# 1. List remote refs (works even with empty working tree)
git ls-remote https://github.com/docs-pages/docs.git
git ls-remote https://github.com/docs-pages/pages.git

# 2. Inspect file types via REST API (auth required for private repos)
curl -s -H "Authorization: token $GH_TOKEN" \
  "https://api.github.com/repos/docs-pages/docs/contents/?ref=master" \
  | jq -r '.[].name' | head -20
# Expected: .github, .gitignore, .npmrc, .vercelignore, README.md, src, ...
# (presence of .vuepress/ + src/*.md + package.json = VuePress source)

curl -s -H "Authorization: token $GH_TOKEN" \
  "https://api.github.com/repos/docs-pages/pages/contents/?ref=master" \
  | jq -r '.[].name' | head -20
# Expected: 404.html, catalog.html, index.html, ..., development-standards/, euv/
# (presence of *.html + assets/ + only `Deploy from @<sha>` commits = Vercel output)
```

## Master commit history signatures

- `docs-pages/docs` master = squash-merged feature branches. Typical messages: `docs(euv): 同步 euv 0.13.6 — CLI install 补 Formatting Rules / ...` merged via `Merge pull request #N from docs-pages/docs/<branch>`. **Single-commit history per merged branch is normal** — don't read it as "the squash went wrong".
- `docs-pages/pages` master = pure `Deploy from @<sha>` Vercel bot commits. Never edit this.

## Common navigation errors to avoid

- "Let me just check what's in the pages repo" → stop. If the user said "delete dev-standards" or "update euv docs", they're talking about `docs`, not `pages`.
- "I see the page exists at `docs-pages/pages`" → yes, the *built* page exists there; the *source* is `docs-pages/docs`. The HTML diff will be overwritten by the next Vercel deploy if you push there.
- "The pages repo is empty / a fresh clone has only `.git`" → that's normal for `pages` (Vercel never checked out a working tree) AND for `docs` (the local clone was set up with `git init` not `git checkout` — the 466 files exist on remote, just not in your working tree).

## Verified facts (2026-08-27)

- `docs-pages/docs` master HEAD = `bf123e7c9064d902db5710b0421be30080686be6` (NOT local `c756019` — that was a stale squashed ref)
- 466 files, including `src/.vuepress/{config,sidebar,navbar}.ts`, `src/README.md`, and 68 euv topic files under `src/euv/**`
- Pre-existing merged branches (visible on remote): `2025_3_14`, `chore/cleanup-broken-links-and-replace-navbar-ides`, `fix/ltpp-add-ghfind-roast-badge`, plus the squash-merged euv sync branches (`docs/euv-0.13.6-updates`, `docs/euv-0.13.6-sync`)
- `origin` remote URL in the local clone is `git@github.com:docs-pages/docs.git` (eastspire is admin, fork disabled)

## Local clone workflow

If the local working tree is empty (just `.git`), the right way to populate it is **Contents API, not `git checkout`** — a 466-file checkout can hang past 420s. See `contents-api-no-clone.md` for the recipe. If you need full local access, clone fresh:

```bash
GIT_TERMINAL_PROMPT=0 git clone --depth 1 \
  git@github.com:docs-pages/docs.git \
  ~/github/docs-pages/docs
# SSH clone under GFW throttling: observed ~28 min for this repo
# (128 MB working tree + .git). Foreground terminal timeouts kick in
# around 7 min — use background process + notify_on_complete.
```

## PR wording

When opening a PR against `docs-pages/docs`, the body should clarify it's the **VuePress source**, not the build output, so reviewers understand why the diff is markdown and not HTML. Sample phrasing: "This PR modifies `src/<topic>.md` (the VuePress markdown source) on `docs-pages/docs`. The Vercel build pipeline renders this into `docs-pages/pages/<topic>.html` on the next deploy; no manual edit of `pages/` is needed."