---
name: euv-docs-contribution
description: Modifying euv-dev/euv-docs — a Rust + euv WASM markdown docs site. Covers parser limitations (image title dropped, data: URL with UTF-8 SVG breaks, setext heading levels), EN+ZH parity rule, no-version-numbers-in-prose rule, branch+PR workflow via gh-pr-creation-workflow, build pipeline (euv build + wasm-bindgen + python3 http.server), Playwright verification, **the audit-first workflow for layout bugs that hit multiple pages** (e.g. the H1↔firstBlock gap on essay/*.html), and the source-path vs build-artifact trap (no per-page HTML is produced — every route is hashed from a single index.html). Use when the user says "改 euv-docs", "euv-docs 文档", "markdown features", "essay has gap", "标题和正文之间大片空白", "audit all pages", or references the euv-docs live URL https://euv-dev.github.io/euv-docs/. Triggers: euv-docs, euv-dev/euv-docs, euv docs site, euv markdown docs, layout bug, essay, audit, H1 gap, space-between.
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

## PR workflow (branch + PR + auto-delete-branch)

`euv-dev/euv-docs` is an eastspire-owned org repo — uses the unified
single-track flow (2026-09-25). Branch off `master`, push the branch
straight to upstream, open a PR, and `gh pr merge --delete-branch` cleans
up the head branch the moment the squash lands. No fork, no
`--head eastspire:` prefix (the branch lives on the upstream repo
itself). See `gh-pr-creation-workflow` for the canonical reference.

```bash
cd ~/github/euv-dev/euv-docs
git fetch origin
git checkout master && git pull --ff-only origin master   # MUST start from clean origin/master
git checkout -b <type>/<scope>-<slug>-YYYY-MM-DD
git add <files>
git -c user.name=eastspire -c user.email=eastspire@users.noreply.github.com \
  commit -m "<type>(<scope>): <subject>"
git push -u origin <branch>
gh pr create --repo euv-dev/euv-docs --base master --head <branch> \
  --title "<type>(<scope>): <subject>" --body-file /tmp/pr-body.md
gh pr checks --watch                    # STOP at green, wait for user "merge it"
gh pr merge <N> --repo euv-dev/euv-docs --squash --delete-branch
git fetch origin master && git checkout master && git reset --hard origin/master
git branch -d <branch>
```

`delete_branch_on_merge=true` is set at the repo level for `euv-dev/euv-docs`
(verified 2026-09-25 batch update), so `--delete-branch` removes the head
branch on the upstream repo automatically. Verify with
`gh repo view euv-dev/euv-docs --json deleteBranchOnMerge` before relying
on auto-delete.

Full PR rules (English body, conventional commits, body sections, never
auto-merge if downstream depends, etc.) live in `gh-pr-creation-workflow`
and `rust-pr-validation-checklist` — this skill only documents the
euv-docs-specific overrides.

**Critical pitfall**: open new branches from clean `origin/master`, NOT
from a previous un-merged PR's branch. PRs opened off an unmerged base
show diffs that include the unmerged PR's commits. See `git-standards` /
`gh-pr-creation-workflow` for the full lesson.

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
- **`euv_logo` component hardcodes the letter `"E"`**: the upstream `euv-ui` component in `src/component/logo/view/fn.rs` renders `"E"` as a literal in both `<button>` and `<span>` branches — it does NOT accept a prop and ignores `DocsSite.logo` even though `build.rs` writes that field into `SITE`. **The intended fix is to leave `logo = ""` (empty) in `docs/config.toml`** — the framework then falls back to its hardcoded `"E"` literal. Don't try to override via JS (overkill) or fork euv-ui (extreme). Setting `logo = "📘"` (or any emoji) has zero effect. Setting `logo = "◆"` (geometric char) does render via the JS hack but the cleanest production solution is just empty `logo = ""`.
- **Hash router auto-detects `README.md`**: route `#/foo` resolves to `docs/foo/README.md` (and only that file — `docs/foo.md` 404s, `docs/foo/index.html` 404s). `#/foo/bar.html` resolves to `docs/foo/bar.md` (NOT `docs/foo/bar/index.md`). Verified by Playwright `c_euv_result_code === '404'` tests. Hero button `link: /catalog` (no extension) 404s; must be `link: /catalog.html`. Always use the `.html` suffix on hash links to be explicit, OR verify the README convention before relying on it.
- **`** 💡 TIP**` (no space) parses; `** TIP**` (space inside `**`) renders as literal text**: refinement of the `[!tip]` workaround (坑 15 in `rust-wasm-gh-pages-deploy-pitfalls`). CommonMark's emphasis rule disallows whitespace adjacent to the closing `**`. After the bulk emoji-strip pass, every `**💡 TIP**` becomes `** TIP**` (leading space inside the asterisks from the regex insertion point) → DOM shows literal `** TIP` instead of bold `TIP`. Fix: another regex sweep `\s+\*\*\s+(\w)` → `**$1` to collapse the space. Always check the rendered DOM `article.querySelectorAll('strong')` after any bulk-frontmatter rewrite that touches `**...**` markers.
- **Nested sidebar group titles indent as if they were leaf links**: when a sidebar group contains another group (e.g. `ltpp` → `LTPP-APP` → `dev-build`), the nested group title renders at x=43 because the framework wraps it in an unwrapped `<div>` inside `.c_euv_sidebar_children`. The hierarchy looks broken — a parent group title and its nested sibling title appear at different x positions, while nested group title and its leaf child end up at the same x=44. Fix: site-local CSS override to pull nested group titles left and align with the parent text x. Full selector pattern under "Framework limitations and overrides" below.
- **`H1↔firstBlock gap on short doc pages is TWO bugs, not one`**: when a user reports "essay/X.html has a big H1↔H2 gap", the cause is BOTH `.md-body h2 { margin-top: 1.8em }` (43px) AND `c_euv_doc_content { justify-content: space-between; min-height: 100vh }` (pushes article upward by ~80–110px when article + tail < 100vh). Override 4 only fixes the first one. Short pages (article < ~400px) show the worst gap (147.8px on 07-05). Fix recipe + audit loop in `references/rendering-fixes.md` §8. **Always audit every page sharing the doc_layout before fixing** — the gap varies 32→148px across essay pages, and one-off CSS hacks miss the worst offenders.
- **`essay/X.html` is a SOURCE path, not a build artifact**: `euv-docs` produces ONE `index.html` + WASM bundle. Every doc route is hashed from that single index via `location.hash`. There is no `dist/essay/.../X.html` static file. `find dist -name '*.html' | wc -l` returns 1. To reproduce a visual bug on a specific essay, serve `dist/` and `location.hash = '#/essay/...X.html'` — do NOT try to open `dist/essay/.../X.html` directly (404).
- **`c_feature_card` events: framework has no `link` field**: confirmed坑 18 in `rust-wasm-gh-pages-deploy-pitfalls`. The only in-workspace fix without forking the framework is to inject JS event delegation from `lib.rs` after `App::mount` — a single `document.addEventListener('click', ...)` that walks up to `.c_feature_card` and routes by `c_feature_name` text via a hardcoded title→route map. External URLs use `window.open(url, '_blank', 'noopener,noreferrer')`. This pattern works because `web_sys::eval` lets the WASM module inject JS without going through Rust-side event handler closures. The map lives as a `r##"..."##` `&'static str` in `lib.rs` so it gets baked into the binary at compile time.
- **`mailto:` in `home.actions[].link` 404s as hash route**: the framework's hash router treats every `link:` value as an internal route unless it starts with `http://`/`https://`. `link: mailto:root@ltpp.vip` renders as `#mailto:root@ltpp.vip` → 404. Workaround: use `link: https://github.com/<org>/issues` (target=_blank) or any `https://` URL. Framework's only special-case for external is the http(s) prefix.
- **Emoji-strip regex catches mobile drawer `☰` and `✕` glyphs**: the bulk emoji purge regex `[\U0001F000-\U0001FFFF\u2600-\u27BF\u2300-\u23FF]` covers `\u2600-\u27BF` (Dingbats block) which **includes `☰` (U+2630 Trigram for Heaven, hamburger menu)** and **`✕` (U+2715 Multiplication X, close button)**. These are NOT emoji but the regex strips them anyway, leaving mobile menu button / drawer close button empty after purge. After any emoji-strip pass, restore them in `src/component/layout/view/fn.rs`: `c_mobile_menu_button()` → `"☰"`, `c_mobile_drawer_close_button()` → `"✕"`. Verify with Playwright at 375px viewport: `page.locator('.c_mobile_menu_button').innerText === '☰'`.

## Framework limitations and overrides (2026-09 docs-pages/docs-euv)

The upstream `euv-docs` engine has three hard-coded UX choices that any non-trivial fork will need to override via site-local CSS or JS injection. All overrides must be applied AFTER `Css::inject_css(EUV_MD_CSS)` in `main()`.

### Override 1: feature card clickable navigation

`EuvFeature` does NOT carry a `link` field — the framework silently drops `link:` keys from feature YAML. The pattern that works without forking the framework:

```rust
const ROUTES_JSON: &str = r##"{"ltpp":"#/ltpp","hyperlane":"#/hyperlane/process.html","euv":"https://github.com/euv-dev/euv", ...}"##;

fn inject_feature_card_click_routes() {
    let window = web_sys::window().unwrap();
    let js = format!(r#"
        (function() {{
            if (window.__docsEuvFeatureWired) return;
            window.__docsEuvFeatureWired = true;
            var ROUTES = {routes};
            document.addEventListener('click', function(ev) {{
                var el = ev.target;
                while (el && el !== document) {{
                    if (el.classList && el.classList.contains('c_feature_card')) {{
                        var name = el.querySelector('.c_feature_name');
                        var title = name ? name.textContent.trim() : '';
                        var route = ROUTES[title];
                        if (route) {{
                            ev.preventDefault();
                            if (route.indexOf('http') === 0) {{
                                window.open(route, '_blank', 'noopener,noreferrer');
                            }} else {{
                                window.location.hash = route;
                            }}
                        }}
                        return;
                    }}
                    el = el.parentNode;
                }}
            }}, true);
        }})();
        "#, routes = ROUTES_JSON);
    let _ = js_sys::eval(&js);
}
```

Call after `App::mount("#app", app)`. The `window.__docsEuvFeatureWired` flag prevents re-installation across SPA route changes. Use raw `js_sys::eval` instead of `Closure` machinery — keeps WASM binary small, avoids `Send`/`Sync` headaches with `web_sys` types, no `forget()` bookkeeping.

### Override 2: feature card border

`euv-ui`'s `.c_feature_card` CSS has no `border` attribute. The site-local CSS override:

```rust
Css::inject_css(
    ".c_home_feature_grid .c_feature_card { \
         border: 1px solid var(--euv-c-border, #e3e3e3) !important; \
         border-radius: 8px !important; \
         padding: 16px !important; \
         transition: border-color 0.15s ease, transform 0.15s ease; \
         cursor: pointer; \
     } \
     .c_home_feature_grid .c_feature_card:hover { \
         border-color: var(--euv-c-brand, #3451b2) !important; \
         transform: translateY(-2px); \
     } \
     @media (prefers-color-scheme: dark) { \
         .c_home_feature_grid .c_feature_card { border-color: var(--euv-c-border-dark, #2e2e2e) !important; } \
         .c_home_feature_grid .c_feature_card:hover { border-color: var(--euv-c-brand-dark, #a8b1ff) !important; } \
     }",
);
```

Use `var(--euv-c-..., #fallback)` so theme-color vars degrade gracefully if euv-ui renames them in a future release. Hardcoded brand colors like `#3451b2` only belong in `:hover` states.

### Override 3: nested sidebar group titles align with parent text x=22

Without override: nested group titles (`APP`, `桌面客户端`, etc.) render at x=43 — visually indistinguishable from leaf links (`开发构建说明` at x=44). Hierarchy looks broken. Override to pull them back to x=22 (same as parent text):

```rust
Css::inject_css(
    /* Nested (depth-2) group titles: align with parent text x=22.
       The title's parent group sits at x=23 (children container
       x=10 with 1px border + 12px padding). Pull left by 1px and
       zero padding so the inner span starts at x=22. Width grows
       by 1px so the right edge stays flush with the parent. */
    ".c_euv_sidebar_children > div > .c_euv_sidebar_group > .c_euv_sidebar_group_title { \
         margin-left: -1px !important; \
         padding-left: 0 !important; \
         width: calc(100% + 1px) !important; \
     } \
     .c_euv_sidebar_children .c_euv_sidebar_children > div > .c_euv_sidebar_group > .c_euv_sidebar_group_title { \
         margin-left: -1px !important; \
         padding-left: 0 !important; \
         width: calc(100% + 1px) !important; \
     }",
);
```

Selector chain walks through `.c_euv_sidebar_children > div` (the unwrapped wrapper `<div>` the framework inserts — there's no class on it, but it exists as a direct child of `c_euv_sidebar_children`). Same pattern works for depth-3 nested groups (use the second selector to target children of children). Leaf links (`c_euv_sidebar_link`) keep their original indent at x=44 — visually obvious hierarchy after the override.

### Override 4: content-page first heading y-position matches home hero (24px from top)

First heading inside `article.md-body` has upstream `margin-top: ~32px` that collapses through the wrapping `<slot style="display:contents">` and pushes the article down 32px below `c_app_main`'s `padding-top: 24px`. Visually misaligned with the home hero `h1` (which starts flush at y=24). Override:

```rust
Css::inject_css(
    ".c_euv_doc_content > article > *:first-child { margin-top: 0 !important; } \
     .c_euv_doc_content > article h1:first-of-type, \
     .c_euv_doc_content > article h2:first-of-type, \
     .c_euv_doc_content > article h3:first-of-type, \
     .c_euv_doc_content > article h4:first-of-type, \
     .c_euv_doc_content > article h5:first-of-type, \
     .c_euv_doc_content > article h6:first-of-type { margin-top: 0 !important; padding-top: 0 !important; }",
);
```

Verify with Playwright `article.querySelector('h1, h2, h3, h4, h5, h6').getBoundingClientRect().top === 24`. Both `> *:first-child` (catches the slot) and `h*:first-of-type` (catches the first heading inside the slot) are needed because the slot's `display:contents` makes its children behave like direct descendants for layout purposes.

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

## References

- `references/framework-overrides.md` — site-local CSS override selectors for euv-docs framework limitations (feature card border, nested sidebar group alignment, heading y-position, anchor glyph hiding, JS event delegation for click routing, hash route conventions). Full selector chains + verification recipes, copied verbatim from the docs-pages/docs-euv site fork. Use when implementing any euv-docs fork that needs to beat an upstream framework limitation.
- `references/rendering-fixes.md` — concrete build.rs + doc_page + image-pipeline fixes from PR #238/#239 cycle: image src rewrite (`/foo.jpg` → `./foo.jpg`), inline asset copying (`copy_doc_assets`), GitHub-style `> [!TIP]` alert parsing (`transform_github_alerts`), content-page h1 rendering, and the **§8 audit-first workflow** for layout bugs (the `H1↔firstBlock` gap caused by `.md-body h2 { margin-top: 1.8em }` PLUS `c_euv_doc_content { space-between; min-height: 100vh }`). Includes the `var!()`/raw-CSS pitfall, the `essay/X.html` source-vs-artifact pitfall, and a full audit → classify → fix recipe. Use when the user reports "essay/X has a big gap between title and first heading", "audit all pages", "标题和正文之间大片空白", or any layout bug that mentions a specific doc page.
- `references/cli-binary.md` — adding a `[[bin]]` native CLI to a cdylib euv-docs crate that builds any markdown directory. Covers the three-edit recipe (Cargo.toml / build.rs env-var lookup / src/bin/euv-docs.rs), three reproduced pitfalls (missing Cargo.toml from inherited cwd, PATH forwarding, sccache target dir layout), and the no-clap / no-anyhow justification per `rust-standards` §13.1. Use when the user asks "turn euv-docs into a CLI" / "build docs from any markdown dir" / "add `--out` flag".
