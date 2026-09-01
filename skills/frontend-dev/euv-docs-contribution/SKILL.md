---
name: euv-docs-contribution
description: Modifying euv-dev/euv-docs — a Rust + euv WASM markdown docs site. Covers parser limitations (image title dropped, data: URL with UTF-8 SVG breaks, setext heading levels), EN+ZH parity rule, no-version-numbers-in-prose rule, fork+PR workflow via gh-pr-creation-workflow, build pipeline (euv build + wasm-bindgen + python3 http.server), Playwright verification. Use when the user says "改 euv-docs", "euv-docs 文档", "markdown features", or references the euv-docs live URL https://euv-dev.github.io/euv-docs/. Triggers: euv-docs, euv-dev/euv-docs, euv docs site, euv markdown docs.
license: MIT
---

# euv-docs contribution (euv-dev/euv-docs)

`euv-dev/euv-docs` is the canonical docs site for the [euv framework](https://github.com/euv-dev/euv), built as a single Rust/WASM application. `build.rs` parses every `docs/**/*.md` file at compile time into a typed `DocsSite` AST; the runtime renders it with native `euv-ui` components — no markdown parsing happens in the browser.

When the user says "改 euv-docs" / "euv-docs 文档" / "补全语法 case" they mean this repo, **not** `docs-pages/docs` (a separate VuePress site — see *Disambiguation* below).

## Disambiguation

There are two projects the user has called "euv-docs" at different times. They are NOT the same:

| Project | Stack | Path |
|---|---|---|
| `euv-dev/euv-docs` (the real one) | Rust + euv WASM | `~/github/euv-dev/euv-docs` |
| `docs-pages/docs` | VuePress 2 + vuepress-theme-hope | `~/github/docs-pages/docs` |

User has corrected this multiple times ("你修改错项目了，撤销。你应该修改 euv-docs 这个仓库"). When the user says "euv-docs", default to `euv-dev/euv-docs` unless they explicitly say "vuepress" / "docs-pages".

## Project layout

```
~/github/euv-dev/euv-docs/
├── Cargo.toml              # name = "euv-docs", depends on euv + euv-ui (workspace = ../euv)
├── build.rs                # pulldown-cmark 0.12 → DocsSite AST codegen → OUT_DIR/docs_gen.rs
├── src/
│   ├── lib.rs              # WASM entry: injects EUV_MD_CSS + site-local CSS overrides, mounts app
│   ├── component/          # doc_page, layout (drawer + main + toc), ...
│   ├── data/struct.rs      # DocsPage struct (route, locale, title, blocks, headings, home, ...)
│   ├── router/             # hash router (/#/guide/getting-started.html)
│   └── ...
├── docs/                   # Markdown source — the actual content the user edits
│   ├── config.toml         # [site] + [[locales]] (locale prefix, lang, label, navbar)
│   ├── README.md           # home page (frontmatter: home: true)
│   ├── guide/              # English locale content
│   │   ├── README.md
│   │   ├── getting-started.md
│   │   ├── markdown.md     # canonical grammar reference (the file we just expanded)
│   │   └── advanced/
│   ├── zh/                 # Chinese locale content (mirrors guide/ + advanced/)
│   └── public/             # static assets copied into www/ at build time
├── template.html           # WASM entry HTML template (hand-edited before serving)
├── www/                    # build output dir for the euv wasm bundle + assets
└── target/                 # cargo target
```

## Build / dev

```bash
cd ~/github/euv-dev/euv-docs

# Full build (release WASM bundle in www/pkg/)
euv build

# Manual build chain (use this if euv build's auto-bundling skips files):
export PATH=/root/.cargo/bin:$PATH
cargo build -p euv-docs --target wasm32-unknown-unknown --release
wasm-bindgen target/wasm32-unknown-unknown/release/euv_docs.wasm \
  --out-dir pkg --out-name euv_docs --target web --no-typescript
cp template.html pkg/index.html
sed -i 's|__IMPORT_PATH__|./euv_docs.js|g' pkg/index.html

# Local dev server
cd pkg && python3 -m http.server 5188 &
# open http://127.0.0.1:5188/
```

**Important**: `euv build` produces only the consumer bundle (`euv_docs.js` + `euv_docs_bg.wasm`). The `euv.js` / `euv_bg.wasm` framework runtime files in `www/pkg/` come from a separate manual step (CI or upstream-bundle sync) — they are NOT built by `euv build`. Do not assume a clean `euv build` regenerates them.

## PR workflow (fork + PR via gh-pr-creation-workflow)

`euv-dev/euv-docs` is an **organization repo under `euv-dev/`** — Track 2 in the user's contribution model:

```bash
cd ~/github/euv-dev/euv-docs
git checkout master && git pull upstream master   # MUST start from clean upstream master
git checkout -b <branch>
git add <files>
git -c user.name=eastspire -c user.email=eastspire@users.noreply.github.com \
  commit -m "<type>(<scope>): <subject>"
git push -u origin <branch>
gh pr create --repo euv-dev/euv-docs --base master --head eastspire:<branch> \
  --title "<type>(<scope>): <subject>" --body-file /tmp/pr-body.md
gh pr merge <N> --repo euv-dev/euv-docs --squash --delete-branch --body-file /tmp/pr-body.md
```

Full PR rules (English body, conventional commits, body sections, never auto-merge if downstream depends, etc.) live in `gh-pr-creation-workflow` and `rust-pr-validation-checklist` — this skill only documents the euv-docs-specific overrides.

**Critical pitfall**: open new branches from clean `upstream/master`, NOT from a previous un-merged PR's branch. PRs opened off an unmerged base show diffs that include the unmerged PR's commits. See `git-standards` / `gh-pr-creation-workflow` for the full lesson.

## Deploy chain

Push to master → GitHub Actions `pages.yml` deploys to GitHub Pages (typical 3–5 min, run id available via `gh run list --branch master --limit 1`).

- Live URL: `https://euv-dev.github.io/euv-docs/`
- ltpp.vip mirror: `https://ltpp.vip/github/pages/euv-dev/euv-docs/` (SPA hash router — `/#/guide/markdown.html`)
- Cross-repo deploy (euv master merge → euv-docs rebuild), mobile safe-area, version bump chain, etc. live in `rust-wasm-gh-pages-deploy-pitfalls`. **Do not duplicate those deploy notes here.**

## Markdown parser — verified limitations (workarounds needed)

These are verified by reading `build.rs` (pulldown-cmark 0.12 with `ENABLE_TABLES | ENABLE_STRIKETHROUGH | ENABLE_FOOTNOTES | ENABLE_TASKLISTS | ENABLE_HEADING_ATTRIBUTES`) and probing the generated `docs_gen.rs` AST. If you hit them, **document the workaround, not the failure**.

| Pattern | Status | Workaround |
|---|---|---|
| `![alt](src)` | ✅ works | — |
| `![alt](src "title")` | ❌ `Inline::Image` AST has no `title` field; parser drops it | Don't claim tooltip support in docs. `build.rs:885` only reads `dest_url`. To support title, add `title: String` to `build.rs::Inline::Image` AND `euv-ui`'s `EuvMdInline::Image` (cross-repo change). |
| `![alt](data:image/svg+xml;utf8,<svg ...>)` | ❌ pulldown-cmark raw-HTML scanner picks up the inline `<svg>` tag → AST gets raw HTML, no `Image` node | Use `data:image/svg+xml;base64,<base64>` — base64 makes the payload opaque to the raw-HTML scanner. The image renders from the AST as a normal `<img>`. |
| `## Heading {#custom-id}` | ✅ setext-style and ATX heading attribute overrides work; slug becomes the element id | — |
| Setext headings `text\n===` | ⚠️ Maps to **h1**, NOT h2. `text\n---` maps to **h2** | Doc this accurately. Don't write "Setext = h2/h3" without confirming against your parser. |
| Footnote reference `[^name]` inline | ✅ works (renders as literal `[^name]` text) | — |
| Footnote definition `[^name]: body` | ⚠️ Definition is rendered as a `<blockquote>` containing a leading `[^name]` paragraph + the body. Not auto-numbered. | Document it as "definition renders as blockquote", not as "footnote list". |
| Reference-style links `[text][id]` + `[id]: url "title"` | ✅ id reuse works (e.g. `[text][id]` twice) | — |
| Bare-URL autolink `<https://...>` | ✅ works (default pulldown-cmark behavior) | — |
| Custom container `::: tip / warning / danger / info / note / details` | ✅ all kinds supported (defined in euv-ui CSS); custom title after kind works; multi-block containers work; **containers do not nest** (inner `:::` becomes literal text) | Don't demo nested containers. |

## Documentation content rules

### EN+ZH parity

Every page added in `docs/guide/...` must have a counterpart in `docs/zh/guide/...` with the same section structure, same code examples (translate prose, keep code identical), same anchors (CJK chars in headings become CJK slugs). When editing `markdown.md`, also edit `zh/guide/markdown.md` in the same PR.

### No version numbers in prose

The docs always reflect "the latest version". Do not write:
- `euv 0.x / euv-cli 0.x / euv-engine 0.x` in text
- `version banner`, `同步至 euv X.Y`, `当前版本` lines
- Numbered "since 0.18" callouts

Acceptable: code-block examples showing `euv = "0.18"` in `Cargo.toml` (that's user-facing API), or a fictional `let version: &str = "0.8.29"` to demo an `euv_info` component.

### Markdown features page is the grammar reference

`docs/guide/markdown.md` (and its ZH mirror) is the **canonical** grammar reference — every case the parser supports must have a demo + the rendered output. When adding a new parser feature, add a demo section to `markdown.md` showing it.

## Headless verification with Playwright

For content / CSS changes on euv-docs:

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
        # SPA — must include hash router fragment
        await page.goto('http://127.0.0.1:5188/#/guide/markdown.html',
                        wait_until='networkidle', timeout=60000)
        await page.wait_for_selector('.md-body h1', timeout=30000)
        await page.wait_for_timeout(2000)

        # Probe element counts and key computed styles
        info = await page.evaluate('''() => ({
            h2: [...document.querySelectorAll('.md-body h2')].length,
            h3: [...document.querySelectorAll('.md-body h3')].length,
            imgs: [...document.querySelectorAll('.md-body img')].map(i => ({
                src: i.src.slice(0, 80),
                nat: `${i.naturalWidth}x${i.naturalHeight}`,
                complete: i.complete,
            })),
            toc: document.querySelectorAll('.c_euv_doc_toc a').length,
            anchor_disp: getComputedStyle(
                document.querySelector('.md-body h1 .header-anchor')
            ).display,
        })''')
        # ...

        await browser.close()

asyncio.run(main())
```

For CJK-heavy pages, verify via DOM inspection rather than `vision_analyze` on screenshots — see `euv-docs-contribution` history and the `css-edge-cases` skill for the CJK rendering caveat.

After local verification, run `gh pr merge` and wait for the GitHub Actions Pages deploy (`gh run list --branch master --limit 1`), then probe the live site at `https://euv-dev.github.io/euv-docs/...` to confirm the deploy actually picked up the change (this catches the cargo-cache and Pages-cdn-cache failure modes).

## Pitfalls

- **euv-ui upstream changes may require euv-docs Cargo.toml bump**: `euv-docs/Cargo.toml` pins `euv = "0.18"` + `euv-ui = "0.18"`. If you change a class in `euv-ui` and the cached `Cargo.lock` doesn't refresh, `cargo build` may silently use the old class. `cargo update -p euv -p euv-ui` and re-test.
- **Edited `vars!` / `class!` source but no effect at runtime**: the `vars!` macro bakes the CSS at compile time. If cargo cache isn't invalidated, the change won't appear in the wasm bundle. `touch ui/src/style/<file>` then re-build, or `cargo clean -p euv-ui`. Cross-reference: `rust-wasm-gh-pages-deploy-pitfalls`.
- **`template.html` uses `__IMPORT_PATH__` placeholder**: when manually running `wasm-bindgen` you'll have a `template.html` with `import init from './pkg/euv_docs.js'` hard-coded if you forgot to substitute, or you need to `sed -i 's|__IMPORT_PATH__|./euv_docs.js|g'` after copying `template.html` to `pkg/index.html`.
- **`build.rs::Inline::Image` only stores `src` and `alt`**: image `title` attribute is dropped silently. Don't claim tooltip support in docs prose.
- **CSS injected via `Css::inject_css`**: site-local overrides must go AFTER `Css::inject_css(EUV_MD_CSS)` in `main()`, otherwise cascade order is wrong. Use `!important` to win against upstream selector-specificity bumps. See existing anchor override in `src/lib.rs` for the pattern.
- **Heading attribute `{#slug}` only affects the slug**, not the heading level. Don't write `### H3 {#...}` and expect `h3` to become anything else.
- **The TOC lists only h2 + h3**: `h1`, `h4`, `h5`, `h6` render as plain headings but never go into the right-side anchor TOC. This is by design (existing behaviour). Don't be surprised when probing.
- **GitHub Pages CDN caching**: the live URL `https://euv-dev.github.io/euv-docs/...` may serve a stale `euv_docs_bg.wasm` for a few minutes even after the deploy succeeds. Wait 30–60s and re-probe, or hit `https://euv-dev.github.io/euv-docs/euv_docs_bg.wasm?t=<timestamp>` to bypass cache.
- **CJK slugs**: heading text containing CJK characters produces a slug that preserves the CJK chars (`#你好-euv-docs`). When writing an anchor link from EN → ZH section, the link target uses the CJK slug — easy to typo. Always grep the `c_euv_doc_toc` to confirm the exact href before writing cross-locale anchor links.

## Verification checklist for euv-docs content / CSS PRs

- [ ] Branch from clean `upstream/master` (not from another open PR's branch)
- [ ] If `Cargo.toml` or `build.rs` changed: `cargo build -p euv-docs --target wasm32-unknown-unknown` + `cargo clippy -p euv-docs --target wasm32-unknown-unknown --no-deps` clean
- [ ] If site-local CSS injected via `Css::inject_css` changed: `touch ui/src/style/<file>` before re-building to bust the macro cache; verify the override appears in the wasm bundle (`grep` the bundle's `instantiate` output or probe `getComputedStyle` for the override)
- [ ] Local dev server + Playwright: getComputedStyle returns the expected values; element counts (h2/h3/img/code) match the new content
- [ ] If `markdown.md` content changed: ZH mirror at `docs/zh/guide/markdown.md` updated with same structure; same anchor ids (CJK-aware); toc count matches both files
- [ ] `cargo fmt --all` clean (no project prettier / taplo config; euv-ui upstream has its own `euv fmt`)
- [ ] PR body has `## Summary` / `## Verification` / `## Notes` (or the euv-standards 4-section template); English; uses `--body-file`
- [ ] After merge: GitHub Actions Pages deploy success (`gh run list --branch master --limit 1`); live URL probed with Playwright (not curl — see `static-site-deploy-verification`)

## Existing conventions in `src/lib.rs` (don't break)

`src/lib.rs::main()` already injects site-local CSS overrides after `EUV_MD_CSS`. The canonical pattern:

```rust
Css::inject_css(EUV_MD_CSS);
// Site-level CSS override: <short description>
//
// <2–4 lines of WHY this override exists, what upstream rule it beats, what the user-visible behaviour should be after this rule takes effect.>
//
// Loaded after EUV_MD_CSS so cascade order places these rules after the upstream defaults;
// !important keeps the rule safe against future selector-specificity bumps from upstream.
Css::inject_css("\
  <one or more rules, semicolon-separated>\
");
App::mount("#app", app);
```

Always carry a comment block explaining **why**, not just **what**. Match the existing anchor override style for tone and depth.
