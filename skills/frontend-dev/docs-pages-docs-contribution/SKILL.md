---
name: docs-pages-docs-contribution
description: docs-pages/docs VuePress site — direct push master.
license: MIT
metadata:
  version: "1.0.0"
  category: frontend-dev
  related_skills:
    - frontend-dev/euv-docs-contribution
    - gh-pr-creation-workflow
    - rust-standards
    - git-standards
---

# docs-pages-docs contribution (docs-pages/docs)

## When to use this skill

Load this skill when the user says any of:

- "docs-pages/docs" / "ltpp.vip docs" / "VuePress docs site" / "ltpp 文档"
- "补全子目录" / "对齐规范" / "补全 euv-docs 子目录" / "euv-docs 404"
- "src/<crate>/ 加新页" / "在 docs 里加一个 crate 的文档"
- references to a missing crate's pages (e.g. "点开 euv-docs 404")

**Do not** load this skill if the user is talking about `euv-dev/euv-docs` (the Rust/WASM markdown docs site) — use `frontend-dev/euv-docs-contribution` instead. The Disambiguation table below covers both projects.

**Do not** load this skill for editing the `docs-pages/pages` Vercel build artifact — that repo is overwritten by the next deploy and is not the source of truth.

`docs-pages/docs` is the eastspire / ltpp documentation site. VuePress 2 + `vuepress-theme-hope`, deployed to Vercel (`pages/` build output pushed to `docs-pages/pages` → served at `https://ltpp.vip/`). Each crate gets its own `src/<crate-name>/` directory; the home `src/README.md` features block + `src/.vuepress/sidebar.js` provide cross-links.

**Disambiguation** — there are TWO projects called "euv-docs":

| Project | Stack | Path | This skill covers? |
|---|---|---|---|
| `docs-pages/docs` | VuePress 2 + vuepress-theme-hope | `~/github/docs-pages/docs` | **Yes — default for "补全 euv-docs 子目录" / "ltpp.vip docs"** |
| `euv-dev/euv-docs` | Rust + euv WASM | `~/github/euv-dev/euv-docs` | No — see `frontend-dev/euv-docs-contribution` |

When the user says "补全 euv-docs" + mentions `ltpp.vip` or `VuePress`, this skill is the right one. The `euv-dev/euv-docs` skill explicitly disclaims the VuePress project — see its Disambiguation section.

## Repo layout (the contract)

```
docs-pages/docs/                      # private, fork-disabled, eastspire admin
├── src/                              # VuePress source tree (the only dir you edit)
│   ├── README.md                     # home: heroText, actions, features: [...]
│   ├── catalog.md                    # crate table
│   ├── .vuepress/
│   │   ├── config.ts                 # bundler, head meta, base_path
│   │   ├── navbar.ts                 # navbar([...])
│   │   ├── sidebar.ts                # sidebar({...}) — old/canonical
│   │   ├── sidebar.js                # sidebar({...}) — active (loads alphabetically)
│   │   ├── theme.ts                  # theme config
│   │   ├── styles/                   # SCSS overrides
│   │   ├── public/                   # img/, css/, js/, webfonts/, video/
│   │   ├── services/                 # TypeScript services
│   │   ├── client.ts
│   │   └── utils.ts
│   ├── <crate-name>/                 # one per crate documented
│   │   ├── README.md                 # index:true, has heroText + 徽章 + 简介
│   │   ├── LICENSE                   # MIT body matching upstream crate's LICENSE
│   │   ├── quick-start/
│   │   │   ├── README.md             # canonical install/run/guide template
│   │   │   └── <topic>.md            # additional quick-start topics
│   │   ├── guide/                    # user-facing prose docs
│   │   ├── macros/                   # optional, mirrors src/euv/macros pattern
│   │   ├── ui/                       # optional
│   │   ├── usage-introduction/       # optional
│   │   └── example/                  # optional
│   └── ... other crates ...
└── plugin/, quick-start/, cli/, ...  # ad-hoc auxiliary dirs (not crate pages)
```

The **canonical crate directory template** is `src/euv/` (and `src/hyperlane/`). Mirror that structure when adding a new crate subdir. Reference templates you can copy from:

- `src/euv/README.md` — index page with frontmatter `head` block, GitHub/crates.io/docs.rs badges, prose intro, license link, contribution/contact blocks
- `src/euv/quick-start/README.md` — full-content install + first-app walk-through
- `src/euv/cli/README.md`, `src/euv/macros/README.md`, `src/euv/ui/README.md`, `src/euv/example/README.md`, `src/euv/usage-introduction/README.md` — frontmatter-only stubs (acceptable when content not yet written)
- `src/hyperlane/quick-start/directory.md` — long-form tree dump example

## Frontmatter template (canonical)

Every page that ends up as a route uses VuePress frontmatter that follows this pattern (extracted from `src/euv/quick-start/README.md`):

```yaml
---
head:
  - - meta
    - name: keywords
    - content: 快速开始,<crate-name>,<topics...>
title: <Chinese title>
index: true|false
icon: fas fa-<icon-name>
category:
  - <crate-name>
  - <topic-tags...>
dir:
  order: <integer>
dataset: true|false
---
```

Special keys:
- `index: true` — exposes the page as the section landing (sidebar entry shows it)
- `dataset: true` — global search index picks the page up
- `dir.order` — sorts pages within a section (lower = earlier)
- `<Share colorful />` — go at the top of body, after frontmatter; renders social share row
- `<Bottom />` — go at the very end of body

The home page (`src/README.md`) additionally uses:

```yaml
---
home: true
icon: home
title: 首页
heroText: eastspire
tagline: '<one-line motto>'
heroFullScreen: true
bgImage: /img/light-background.png
bgImageDark: /img/dark-background.png
actions:
  - text: <CTA>
    link: /<path>
    icon: <icon>
    type: primary
features:
  - title: <crate>
    details: <one-line>
    icon: blog
    link: /<crate>/
---
```

Add a feature card per crate that has a `src/<crate>/` directory; **delete the feature card if the subdirectory is removed**. Same for the homepage features block — orphaned cards → 404.

## Adding a new crate subdirectory (canonical workflow)

```bash
# 1. Confirm the crate exists upstream and the subdir doesn't already exist
gh api repos/docs-pages/docs/contents/src/<crate> --jq '.message // .name'   # 404 → new

# 2. Read existing src/euv/README.md and src/euv/quick-start/README.md as templates
gh api repos/docs-pages/docs/contents/src/euv/README.md --jq '.content' | base64 -d > /tmp/euv-readme.md
gh api repos/docs-pages/docs/contents/src/euv/quick-start/README.md --jq '.content' | base64 -d > /tmp/euv-qs.md

# 3. Author the new files locally mirroring those templates
#    - Replace GitHub URL (e.g. https://github.com/euv-dev/euv → https://github.com/<org>/<crate>)
#    - Replace crate name in frontmatter categories / keywords / icon
#    - Replace prose to describe THIS crate, not euv

# 4. Push via Contents API (small batch) OR clone via SSH + git push (large batch, >10 files)
#    Contents API pattern:
gh api -X PUT repos/docs-pages/docs/contents/src/<crate>/README.md \
  -f message='docs(<crate>): scaffold subdirectory' \
  -f content="$(base64 -w0 < <local-file>)" \
  -f branch=master

#    For >10 files: clone via SSH (long timeout — handshake ~10s, index-pack minutes)
GIT_SSH_COMMAND="ssh -o StrictHostKeyChecking=no" git clone git@github.com:docs-pages/docs.git \
  ~/github/docs-pages/docs 2>&1 | tail
cd ~/github/docs-pages/docs
git checkout master
mkdir -p src/<crate>/{quick-start,guide,macros,ui,usage-introduction,example}
# ... write files ...
git add src/<crate>/ src/.vuepress/sidebar.js   # sidebar.js edit too
git -c user.name=eastspire -c user.email=eastspire@users.noreply.github.com \
  commit -m "docs(<crate>): scaffold subdirectory + register sidebar"
git push origin master                         # direct to master — see "PR flow" below

# 5. After Vercel auto-deploys (push to master triggers workflow), wait 2-3 min, then verify
curl -s --compressed -o /tmp/out.html -w "%{http_code} %{size_download}\n" \
  https://ltpp.vip/<crate>/
# expect 200 + size_download > 10000 (the rendered HTML), NOT 0 bytes
# If size is 0 → see "ltpp.vip 0-byte trap" pitfall below
```

## PR flow — direct to master, NO fork, NO PR

`docs-pages/docs` is **private + eastspire admin**, and as of 2026-09-05 the entire `docs-pages/*` namespace is on `gh-pr-creation-workflow` Track 1 (direct-push). The flow is:

- `git push origin master` directly (admin SSH)
- **No PR, no branch, no fork**. Just commit on `master` and push.
- The push triggers the `Deploy Pages` GitHub Actions workflow which rebuilds + pushes HTML to `docs-pages/pages` (see Deploy chain below).

> **Don't even think of forking or opening a PR.** `gh repo fork` errors: "Cannot fork a repository you own" (eastspire is the only admin). `gh pr create` against `docs-pages/docs` after pushing a branch would create an unmergeable PR (branch == master). If you accidentally create a branch, delete it (`git push origin --delete <branch>`) and re-push to master.

> **Historical note**: prior to 2026-09-05, docs-pages was on Track 2 with a Contents-API workaround. PRs #16–#27 in `docs-pages/docs` are all from that era; after 2026-09-05 no PRs should be opened against `docs-pages/docs` for any reason — the workflow is direct-push to master.

## Sidebar registration (REQUIRED for every new subdirectory)

`src/.vuepress/sidebar.js` is the active sidebar config (`.ts` is the older/canonical sibling). Format:

```js
import { sidebar } from "vuepress-theme-hope";
export default sidebar({
  "/existing-crate": 'structure',
  "/new-crate": 'structure',     // <-- add this line, alphabetical with peers
  ...
});
```

- Insertion order: **alphabetical**, between `/<prev>` and `/<next>` (e.g. between `/essay` and `/file-operation` for `/euv-docs`)
- One line per crate — value is always `'structure'` (means auto-derive from frontmatter headings)
- Forgetting this = subdir renders content but is invisible from the sidebar nav

## Content authoring rules (mirroring `src/euv/`)

1. **Chinese prose, English code**. Body content in Chinese (matching existing `src/euv/`); all code samples (`rust`, `sh`, `toml`, `html` fences) in English.
2. **No version numbers in prose**. Forbidden: `euv 0.x / euv-cli 0.x / 当前版本 / 同步至 euv X.Y / version banner`. Allowed: `euv = "*"` in a `Cargo.toml` code block (user-facing API), or a fictional `let version: &str = "0.8.29"` inside an `euv_info` demo.
3. **All GitHub-visible text is English**: commit messages, PR titles, PR bodies (when one is opened). The home page is Chinese, the user's chat is Chinese — but git history is reviewer-facing.
4. **Frontmatter `head` is multi-line list syntax** (VuePress 2 + `hope` theme). Use the exact `head:\n  - - meta\n    - name: keywords\n    - content: ...` form, not single-line.
5. **`<Share colorful />` at top of body, `<Bottom />` at end**. Otherwise the page renders with a stray header-anchor clip.
6. **Callouts** use `> [!tip]` / `> [!warning]` / `> [!danger]` (not the `:::tip` container — that's `euv-dev/euv-docs`'s WASM site, this is VuePress).
7. **Mirror `src/euv/` sidebar depth**: README → quick-start/ → guide/ → macros|ui|usage-introduction|example/. Don't invent new top-level dirs unless mirroring an upstream crate's directory structure.
8. **Edit LICENSE to match upstream**. `src/euv/LICENSE` mirrors `euv-dev/euv/LICENSE`; same idea for new crates — pull the canonical MIT body from the upstream crate's LICENSE.

## Deploy chain (actual mechanism — verified from run logs 2026-09-04)

`git push origin master` triggers `docs-pages/docs` GitHub Actions workflow `Deploy Pages` (`.github/workflows/deploy-pages.yml`, NOT Vercel — there is no Vercel integration; Vercel is a misleading label from the home-page actions marker). The workflow runs 5 steps in one job (`build-and-push`):

1. **Checkout** — `actions/checkout@v4` for the docs repo
2. **Checkout Docs Pages** — `actions/checkout@v4` with `repository: docs-pages/pages, path: __docs_pages, token: secrets.DOCS_REPO_PAT` (PAT-tokened sub-checkout)
3. **Setup Node + Corepack + yarn install** (Node 22, yarn 4.10.3, `yarn install --immutable`)
4. **Build** — `yarn run build` (= `node plugin/creat-sidebar.js && node plugin/creat-dataset.js && vuepress build src`, NODE_ENV=production)
5. **Push to Docs Repository** — `find . -maxdepth 1 -not -name '.git' -exec rm -rf {} +` then `cp -r $GITHUB_WORKSPACE/pages/* .`, `git fetch origin master`, `git rebase -X theirs origin/master || git rebase --abort`, `git push origin master`. Concurrency group `deploy-pages` serializes runs.
6. **Sync Pages** — `curl -sf -X POST https://ltpp.vip/api/github/pages/sync/docs-pages/pages` with up to 60 retries × 60s. Returns `{"code":200,"message":"Success","data":"Synced"}` on success.

Key invariants to verify after push:
- `docs-pages/pages` HEAD commit is `Deploy from @<your-sha>` within ~2-3 min of push
- All new HTML files appear in the commit (look for `create mode 100644 <crate>/<page>.html` lines in the workflow log)
- `ltpp.vip/api/github/pages/sync/docs-pages/pages` returns 200 — this is a hard sync trigger independent of any nginx/edge cache

Manual replay: if a deploy looks stuck, hit `curl -X POST https://ltpp.vip/api/github/pages/sync/docs-pages/pages` from anywhere — this is a public endpoint that re-pulls from `docs-pages/pages`.

**ltpp.vip rewrite rules (verified by probing, 2026-09-04)**:
- `https://ltpp.vip/` (root) → `302 → /github/pages/docs-pages/pages/` → 8,006 bytes (works)
- `https://ltpp.vip/<feature>/` (any short path like `/euv-docs/`, `/euv/`, `/hyperlane/`) → `200 + content-length: 0` (always)
- `https://ltpp.vip/github/pages/docs-pages/pages/<feature>/` (long path) → real HTML, works for everything

So `ltpp.vip/<feature>/` short paths have been **0-byte since at least master `04d7fdbb` (2026-08-31)** — well before any subdir scaffold. Per user confirmation this is the expected nginx config, not a bug. To verify a new subdir, always probe the **long** path `https://ltpp.vip/github/pages/docs-pages/pages/<crate>/` — that is the source of truth.

## ltpp.vip 0-byte trap (verified pitfall, 2026-09-04)

When `https://ltpp.vip/<crate>/` returns `200 + content-length: 0`, the most common causes in order of likelihood:

1. **The subdir doesn't exist in `docs-pages/docs`** — `gh api repos/docs-pages/docs/contents/src/<crate>` → 404. **Action**: scaffold the subdir per this skill.
2. **Vercel deploy hasn't fired yet** — push was <2-3 min ago. **Action**: wait, then re-probe.
3. **ltpp.vip nginx serve config mismatch** — `https://ltpp.vip/<crate>/index.html` returns 0 but `https://ltpp.vip/github/pages/docs-pages/pages/<crate>/index.html` returns full HTML. **Action**: nginx-side problem, not this skill's scope. Report to user.
4. **The build failed silently** — check `docs-pages/pages` repo's recent commits; if no new "Deploy from @<sha>" commit since your push, the Vercel workflow errored. **Action**: read the workflow run logs.

The CURE for case (1) is **this entire skill**: scaffold the subdir, mirror `src/euv/`, push to master, wait, re-probe.

The CURE for case (4) is rare but real: check the GitHub Actions run for `docs-pages/docs` (`gh run list --repo docs-pages/docs --workflow=vercel --limit 3`) and read the failed step output.

## Verification checklist

- [ ] `gh api repos/docs-pages/docs/contents/src/<crate>/README.md --jq .sha` confirms the new file landed (not 404)
- [ ] `gh api repos/docs-pages/docs/contents/src/.vuepress/sidebar.js --jq '.content' | base64 -d` includes `"/<crate>": 'structure'`
- [ ] `src/.vuepress/sidebar.js` was edited in the same commit as the subdir scaffold (so they deploy together)
- [ ] Push landed on master (no PR opened, no branch — Track 1 direct push)
- [ ] 2-3 min after push, `curl -s --compressed -w "%{http_code} %{size_download}" https://ltpp.vip/<crate>/` shows size > 10000
- [ ] Side-by-side probe of `https://ltpp.vip/<existing-crate>/` to confirm other paths unaffected
- [ ] No version numbers in any prose (grep `<crate>` for `euv 0` / `当前版本` / `同步至`)

## Existing crates to model

The "complete crate subdirectory" reference is `src/euv/` — it's the deepest one and the canonical template. When in doubt, mirror it. Other reference crates to consult:

| Crate | Subdir layout | Notes |
|---|---|---|
| `euv` | README + 6 subdirs (`cli`/`example`/`macros`/`quick-start`/`ui`/`usage-introduction`) | **Canonical — mirror this** |
| `hyperlane` | README + 6 subdirs (`config`/`help`/`markdown-images`/`middleware`/`quick-start`/`speed`/`usage-introduction`/`utils`) | Also deep; good cross-check |
| `ltpp` | (legacy; lighter structure) | Pre-existing legacy content |
| `lombok-macros` | (single README) | Bare-minimum structure reference |
| `ltpp-ssh` | (single README) | Bare-minimum structure reference |

When a new crate mirrors one of these in upstream structure, mirror the corresponding subdir layout in `src/<crate>/`.

## Pitfalls

- **Forgetting to update `sidebar.js`** when adding a new subdir — content exists but is unreachable from nav. Re-read the sidebar.js section above; this is the single most common miss.
- **Forgetting to update home `src/README.md` features block** — sidebar can still discover the subdir via routing, but the home hero card won't link to it. The inverse is also true: an orphaned home card (`/euv-docs/` link) with no subdir → 404.
- **Frontmatter `head` collapsed to single line** — `hope` theme parser expects nested list form (`- - meta\n    - name: keywords\n    - content: ...`), not a single `- name: keywords` line. Test by re-fetching the rendered page and checking the `<meta name="keywords">` is populated.
- **`<Bottom />` placed before content ends** — pages with trailing content after `<Bottom />` render with a stray empty nav-pager block at the very bottom. Always end-of-body.
- **Forging a PR when direct-push works** — `docs-pages/docs` is admin-only; just push master. Opening a PR against your own admin access wastes a round-trip. (Exception: if you actually want CI to gate it, that's a separate workflow setup.)
- **`git push origin master` rejected with "non-fast-forward"** — means local master drifted (a teammate/auto-process committed since you cloned). `git fetch origin && git reset --hard origin/master` is the safe sync (no local work lost if you committed first).
- **Clone via SSH hangs at "index-pack"** — handshake completes in ~10s but a non-trivial repo takes minutes. Use `timeout=300` foreground or `background=true` with `notify_on_complete=true`. See `git-standards` for the rule.
- **Don't write `euv-docs` to mean `euv-dev/euv-docs`** — they are two separate repos with overlapping names. When the user says "euv-docs" without context, default to `docs-pages/docs` if the conversation mentions VuePress or `ltpp.vip`; default to `euv-dev/euv-docs` if it mentions Rust, WASM, or the parser. Confirm if ambiguous.
- **"Pipeline didn't take effect" ≠ deploy failed** — when a user says the GitHub pipeline or build didn't take effect on a live page, **never** answer from memory. Always self-explore: fetch the Actions run, read the logs, and probe `ltpp.vip/api/github/pages/sync/docs-pages/pages` + the long path. The most likely explanations are (a) the user's browser was hitting a 0-byte short path (the ltpp.vip nginx rule, expected), (b) the user assumed Vercel was involved when it's actually GitHub Actions + a custom ltpp.vip sync API, or (c) Vercel label was misleading. Don't ask the user to clarify when the evidence is one `gh run view --log` away.
- **VuePress dev server returns 344-byte placeholder for every route** — `yarn dev` runs at `0.0.0.0:8080` but VuePress dev mode does NOT SSR; body is `<div id="app"></div>` until JS hydrates. `curl http://127.0.0.1:8080/<route>/` returns the same 344-byte stub regardless of whether the subdir scaffolded correctly. To verify dev-mode content, must use headless chromium (Playwright). `gh api`+ curl alone cannot validate dev mode. See Verification section.
- **GitHub Actions UI page never reaches `networkidle`** — the actions run page uses socket.io for live updates, so `wait_until='networkidle'` times out at 60s. Use `wait_until='domcontentloaded'` instead, or skip the browser entirely and use `gh api repos/docs-pages/docs/actions/runs/<id>/logs | unzip` to read logs as text.

## Verification — verifying dev server content (Playwright, not curl)

VuePress dev mode body is a JS-hydrated `<div id="app"></div>` stub. Curl cannot see rendered content. The reusable recipe:

```python
import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            executable_path='/root/LTPP-MINIMAX/chrome-linux/chrome',
            args=['--no-sandbox', '--disable-dev-shm-usage'],
        )
        ctx = await browser.new_context(viewport={'width': 1280, 'height': 900})
        page = await ctx.new_page()

        await page.goto('http://127.0.0.1:8080/', wait_until='networkidle', timeout=60000)
        await page.wait_for_timeout(3000)
        # vuepress-theme-hope features use generic class, NOT .feature — query by h2/h3 + a
        info = await page.evaluate('''() => ({
            title: document.title,
            n_links_with_crate: [...document.querySelectorAll('a[href*="<crate>"]')].length,
            body_html_length: document.body.innerHTML.length,
        })''')

        await page.goto('http://127.0.0.1:8080/<crate>/', wait_until='networkidle', timeout=60000)
        await page.wait_for_timeout(2000)
        sub = await page.evaluate('''() => ({
            h1: document.querySelector('h1')?.textContent?.trim(),
            n_h2: document.querySelectorAll('h2').length,
            n_code: document.querySelectorAll('pre code').length,
            sidebar_items: [...document.querySelectorAll('.sidebar a, aside a')].map(a => a.textContent.trim()).filter(Boolean),
        })''')
        # h1 should match crate name, n_h2 > 0, sidebar_items non-empty

        await browser.close()
```

Pass criteria: `title` contains the crate name, `h1` is the crate title, `n_h2 >= 1`, `n_code > 0` for content-heavy pages, sidebar_items has the frontmatter-derived section labels.

## Reading GitHub Actions logs directly (no browser)

`gh api repos/docs-pages/docs/actions/runs/<id>/logs` returns a zip; unzip and grep:

```bash
gh api repos/docs-pages/docs/actions/runs/<run-id>/logs > /tmp/run-logs.zip
unzip -o /tmp/run-logs.zip -d /tmp/run-logs/
grep -E "create mode 100644|Error|Failed|Sync succeeded|Push to" /tmp/run-logs/*.txt
```

This is the canonical evidence for "did the pipeline actually fire and succeed" — way more reliable than clicking through the actions UI.