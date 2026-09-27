---
name: euv-docs-styling
description: Iterate euv-docs sidebar, pagination, viewport lock, and right-side TOC active highlighting.
version: 0.3.0
author: Hermes Agent
license: MIT
platforms: [macos, linux]
metadata:
  hermes:
    tags: [euv, euv-docs, euv-ui, css, wasm, sidebar, pagination, viewport-lock]
---

# euv-docs Styling

Visual-design iteration on the euv-docs sample docs site (VuePress-style layout built on `euv` + `euv-ui`). Covers sidebar width / nesting / hover affordance, pagination row layout, and the viewport-lock pattern that pins the sidebar while the main column scrolls.

## When to Use

- User reports sidebar wrapping, pagination layout breakage, or sidebar scrolling with the page on the euv-docs sample site.
- User wants the sidebar width to adapt (clamp-based) or wants nested items indented less wastefully.
- User wants the desktop sidebar pinned while the right column scrolls independently.
- User wants the pagination prev/next row split evenly with the footer cleanly separated below.
- User wants the page footer pinned at the mobile viewport bottom (a sticky bar across the bottom of the phone screen).
- User wants the sidebar bottom attribution line ("基于 Euv & Wasm 构建") centred instead of left-aligned.

## Don't use for

- Editing the underlying `euv-ui` Rust component API (different skill territory).
- Theme tokens (light/dark) — those live in `ui/src/style/var/fn.rs` and `inject_app_global_css`.
- Markdown rendering rules or build-script codegen — those live in `euv-docs/build.rs` and `euv-docs/src/component/`.

## Project Layout

- `/Users/sqs/code/euv/euv-docs/` — the docs generator project (`Cargo.toml`, `build.rs`, `src/`, `template.html`, `docs/`, `out/`, `www/`).
- `/Users/sqs/code/euv/euv-docs/docs/` — **mostly empty** by default (only `README.md` + an empty `guide/`). Real docs content lives in `/Users/sqs/code/euv/cli/docs/`.
- `/Users/sqs/code/euv/ui/` — the upstream UI library; base styles live in `src/style/class/fn.rs`, design tokens in `src/style/var/fn.rs`. Sidebar component classes (`c_euv_sidebar_*`), shell classes (`c_app_nav`, `c_app_main`, `c_app_root`, `c_nav_items_scroll`), pagination (`c_euv_pagination*`), and `euv_doc_layout` (`c_euv_doc_*`) all live there.
- `/Users/sqs/code/euv/euv-docs/src/lib.rs` — giant `Css::inject_css(""" ... \`)` block of `!important` overrides that euv-docs applies on top of the base `euv-ui` styles.

## Build & Live Preview

The docs generator reads markdown via `EUV_DOCS_SRC_DIR` and compiles to WASM. Two build pipelines exist depending on which site you're iterating on:

```bash
# Eastspire docs site (~/code/docs, the user's personal docs):
cd /Users/sqs/code/docs
rm -rf dist
EUV_DOCS_SRC_DIR="$PWD/docs" euv-docs "$PWD/docs" --out "$PWD/dist"
# Output: dist/pkg/euv_docs_bg.wasm + dist/index.html

# euv sample docs site (~/code/euv/euv-docs, default EUV_DOCS_SRC_DIR=cli/docs):
cd /Users/sqs/code/euv/euv-docs
EUV_DOCS_SRC_DIR=/Users/sqs/code/euv/cli/docs euv build -- \
  --target web --out-dir www/pkg --out-name euv_docs --no-typescript --no-pack
```

**Do NOT run `euv-docs` from inside `~/code/euv/`** — `euv-docs` resolves the
source markdown relative to its working directory, and `~/code/euv/` has no
`docs/` subdirectory with pages, so the build errors with
"config.toml not found". Always run from the docs project root
(`~/code/docs` for eastspire, `~/code/euv/euv-docs` for the sample).

Then serve the static output:

```bash
cd /Users/sqs/code/docs/dist && python3 -m http.server 8765
# or for sample docs:
cd /Users/sqs/code/euv/euv-docs/www && python3 -m http.server 8765
# open http://localhost:8765/#/guide/getting-started.html
```

The hash-route scheme is `#/<locale-prefix>/<page>.html`. The English locale prefix is empty (`/`); Chinese is `/zh/`. Use `e.g. #/guide/getting-started.html` to land on a nested page with the sidebar visible.

Iterate: edit CSS in `ui/src/style/class/fn.rs` (and/or `var/fn.rs`) for upstream rules, or the inline string in `euv-docs/src/lib.rs` for docs-only overrides, then re-run the build. Cargo caches aggressively — the rebuild step is ~1–3 s after the first compile.

**Verification gotcha**: the browser caches `dist/pkg/euv_docs_bg.wasm` aggressively. After a rebuild, a `location.reload()` in the same tab does NOT pick up the new wasm — the JS glue imports the same URL and the cached bytecode is served. Always restart the server on a new port (or append `?v=NNN` to the wasm import) before verifying a CSS change. See the "wasm cache" pitfall below.

## Procedure

1. **Confirm the live state matches the bug.** Open the served page in the browser, take a screenshot, measure `getBoundingClientRect()` of `.c_app_nav` / `.c_app_main` / `.c_euv_pagination_link` at `scrollY=0` and after `scrollTo(0, 800)`. State-of-doc screenshot before any edit.

2. **Decide the layer.** Upstream rule (sidebar defaults, shell layout, pagination default flex) → edit `ui/src/style/class/fn.rs`. Docs-specific override (cosmetic adjustment for docs branding, e.g. theme colour, special alignment for the home page) → edit the inline string in `euv-docs/src/lib.rs`. Never duplicate a rule in both — pick one layer.

3. **Apply minimal change.** One class at a time. Avoid blanket `:not()` selectors that reach into layout containers — they break children's own `display: flex` contracts. The known-bad pattern: `c_euv_doc_content > div:not(.c_euv_doc_toc):not(.c_euv_doc_content):not(article) { display: flex; flex-direction: column }` was what broke `c_euv_pagination` (it forced pagination's inner div into column flex, making the prev/next row collapse and the footer bleed into the prev box).

4. **Rebuild.** `cd /Users/sqs/code/euv/euv-docs && EUV_DOCS_SRC_DIR=/Users/sqs/code/euv/cli/docs euv build -- ...` (full command above). Then `Cmd+Shift+R` reload in the browser to bypass the euv-docs live-reload SSE that occasionally gets stuck.

5. **Verify with the same measurements** as step 1. Capture before/after screenshots for pagination bottom + sidebar hover + nested-item alignment.

## CSS Patterns That Worked

### Sidebar width (clamp-based, adapts to viewport)

```css
nav-width: clamp(248px, 22vw, 320px);  /* min unchanged, max reasonable */
```

For the mobile drawer, prefer `width: min(100%, var(--sidebar-max))` rather than the clamp.

### Sidebar nesting (compact indent, text aligns with dashed border)

`c_euv_sidebar_children` should use `margin-left: var(--space-sm); padding-left: var(--space-sm); border-left: 1px dashed var(--border);` — total ≈17 px. The original 33 px (margin 20 + border 1 + padding 12) wasted horizontal space. Keep left padding of parent group title/leaf link equal to `margin-left + border-width + padding-left` of the children container so text on a parent and text on its first child land on the same x.

### Hover affordance — "insert a thick bar between dashed border and text, never move the text"

This is the locked-in pattern after several iterations. Earlier attempts (grey background wash, real `border-left` on the hovered item with `padding-left` compensation, `:has(:hover)` thickening the parent's dashed border) were all rejected. The accepted pattern paints a 3 px solid bar INSIDE the hovered item's existing padding box via `inset box-shadow`, which never participates in layout and therefore never moves the text.

```css
/* In ui/src/style/class/fn.rs, on c_euv_sidebar_link / c_euv_sidebar_group_title: */
.c_euv_sidebar_link:hover,
.c_euv_sidebar_group_title:hover {
  box-shadow: inset 3px 0 0 0 var(--foreground);
}

/* c_euv_sidebar_children's dashed border is left untouched. The bar lives
   inside the link's padding box, so it sits between the parent dashed tree
   guide (further left) and the link's text (further right). */
```

In the `class! { ... }` macro the same rule is written:

```rust
:hover {
    box-shadow: format!("inset 3px 0 0 0 {}", var!(foreground));
}
```

For euv-docs-only layers, mirror into `euv-docs/src/lib.rs` with `!important` and `border: 0` to defeat any leftover `border-left`:

```css
.c_euv_sidebar_link:hover,
.c_euv_sidebar_group_title:hover {
  background: transparent !important;
  color: var(--foreground, #000) !important;
  border: 0 !important;
  box-shadow: inset 3px 0 0 0 var(--foreground, #000) !important;
}
.c_theme_dark .c_euv_sidebar_link:hover,
.c_theme_dark .c_euv_sidebar_group_title:hover {
  background: transparent !important;
  color: var(--foreground, #fff) !important;
  box-shadow: inset 3px 0 0 0 var(--foreground, #fff) !important;
}
```

The `_active` variants must NOT use the inset-bar `:hover` shadow — see the "active-vs-hover precedence" pitfall below. Use `box-shadow: none` on `_active:hover` (both base UI class and docs override with `!important`).

Top-level items use the identical rule; the visual result is the same — a 3 px bar between the sidebar's outer `c_app_nav` left border and the item text.

**Never add a grey hover background.** `background: var(--accent-muted)` (or any `rgba(0,0,0,0.08)` wash) was tried and rejected outright.

**Never use a real `border-left` to fake the bar.** Borders grow the border-edge; compensating via `padding-left: calc(space-md + 3px)` looks correct on paper but in practice the text x drifts by up to 6 px because block elements under flex parents re-layout the inner padding box when a border appears. `box-shadow inset` is paint-only and provably zero layout impact — measure `getBoundingClientRect().left` plus `parseFloat(borderLeftWidth) + parseFloat(paddingLeft)` before and after a forced hover; both should be byte-identical.

### Snug-to-border bar (when the inset-shadow can't reach the parent border)

The inset-shadow pattern above lives **inside the link's padding box**, which sits ~8 px to the right of the parent `c_euv_sidebar_children` dashed border. When the design wants the bar to land **flush with that dashed border** (no gap, no overlap) the shadow has no way to escape the padding box — it can only move rightward, never reach the parent's left edge.

The accepted answer is a `::before` pseudo-element with negative `left` that extends out of the link into the parent gutter. The parent gutter is whatever space sits between the link's left edge and the nearest visual landmark:

| Item position | Nearest left landmark | `::before` `left:` value |
|---|---|---|
| Nested link | parent `c_euv_sidebar_children` 1 px dashed border | `-8px` (clears the link's `padding-left` ≈ 12 px minus the dashed-border offset ≈ 4 px) |
| Top-level item | sidebar's outer `c_app_nav` border | `-2px` (clears the item's `padding-left` only) |

```css
/* In euv-docs/src/lib.rs injected CSS (NOT in the upstream ui class! — keeps the framework clean) */
.c_euv_sidebar_link,
.c_euv_sidebar_group_title {
  position: relative !important;       /* anchor for the absolutely-positioned ::before */
}
.c_euv_sidebar_link::before,
.c_euv_sidebar_group_title::before {
  content: '' !important;
  position: absolute !important;
  top: 0 !important;
  bottom: 0 !important;
  width: 5px !important;
  pointer-events: none !important;     /* never intercept the link's click */
}
.c_euv_sidebar_link::before           { left: -8px !important; }   /* nested */
.c_euv_sidebar_group_title::before    { left: -2px !important; }   /* top-level */

/* Hover paints the bar with currentColor so it tracks text colour */
.c_euv_sidebar_link:hover::before,
.c_euv_sidebar_group_title:hover::before {
  background: currentColor !important;
}
.c_euv_sidebar_link:hover,
.c_euv_sidebar_group_title:hover {
  background: transparent !important;
  box-shadow: none !important;
  border: 0 !important;
}
```

The active variant uses the same `::before` slot but paints it with the **accent colour** (the fill colour, not the text colour). For the active state the link's own `background` is set to `transparent` so the accent bar visually reads as the entire element's left edge:

```css
.c_euv_sidebar_link_active,
.c_euv_sidebar_group_title_active {
  background: transparent !important;
}
.c_euv_sidebar_link_active::before,
.c_euv_sidebar_group_title_active::before {
  background: var(--accent, #000) !important;       /* bar carries the accent */
}
.c_euv_sidebar_link_active,
.c_euv_sidebar_group_title_active {
  color: var(--background, #fff) !important;        /* in dark mode accent is white; in light it is black, background flips */
}
/* Hover must keep the active look — see the "active-vs-hover precedence" pitfall */
.c_euv_sidebar_link_active:hover,
.c_euv_sidebar_group_title_active:hover {
  background: transparent !important;
  box-shadow: none !important;
  border: 0 !important;
  color: var(--background, #fff) !important;
}
```

**Specificity gotcha:** `_active::before` is (0,2,1) and `_link::before` is (0,1,1). For props NOT redeclared in the more-specific rule, the cascade falls back to the less-specific one — but ONLY for props the more-specific rule declared too. If `_active::before` only declares `background`, then `content`/`position`/`width`/`left`/`top`/`bottom`/`pointer-events` all keep their declared-or-default values from the LESS-specific rule. **Self-contained rule wins**: the `_active::before` rule must redeclare every prop the base `::before` rule declared, all with `!important`. A rule that only overrides `background` looks like it should "just change the colour" but the browser actually reverts the pseudo-element to `content: none` (no `::before` rendered at all) — see the "self-contained `::before` rules" pitfall below.

### Sidebar bottom attribution line (centered)

The `c_nav_footer` link at the bottom of the desktop sidebar renders its "Built with Euv & Wasm" text left-aligned by default (it inherits the sidebar's `padding-left` and follows the column flow). The expected look is centered:

```css
/* In ui/src/style/class/fn.rs (c_nav_footer): */
.c_nav_footer {
  display: flex;
  align-items: center;
  justify-content: center;   /* center the attribution line */
  text-align: center;        /* centre multi-line wraps */
  gap: var!(space-xs);
  /* …padding, position, font-size, etc… */
}
```

The absolute-positioned divider on top (`c_nav_footer_divider { left: var!(space-lg); right: var!(space-lg); }`) is independent of the link's own alignment, so it stays full-width regardless.

### Footer / pagination position — sits after article, NOT pinned to viewport bottom

The user does NOT want a sticky/fixed footer. Pagination + footer sit
in normal document flow at the end of the article (right under the last
paragraph / image / heading). `c_euv_doc_content` is `flex column` with
`justify-content: flex-start` (NOT `space-between`).

If `space-between` is used, short articles produce a large empty band
between the H1 page title and the article body (measured ~120px on a
short essay: the article gets pushed to the geometric middle because
space-between distributes the spare viewport height across the gaps).
This was the original pattern; the user rejected it when iterating on
short essay pages and the new accepted answer is `flex-start` with the
pagination/footer following the article normally — matching VuePress /
Docusaurus default behavior.

Implementation:

1. Wrap pagination + footer in a single flex child so the content
   column has a predictable set of children.
   In `ui/src/component/doc_layout/view/fn.rs`:

```rust
html! {
    div { class: c_euv_doc_layout()
        div { class: c_euv_doc_content()
            children           // article (auto-injected as slot)
            div { class: c_euv_doc_tail()    // groups pagination + footer
                euv_pagination { ... }
                if !footer.is_empty() {
                    footer { class: c_euv_footer() { footer } }
                }
            }
        }
    }
}
```

2. `c_euv_doc_tail` is just `display: block` — its only job is grouping
   pagination + footer into one block so they render together.

3. `c_euv_doc_content` is a column flex with `flex-start` (NOT
   `space-between`):

```css
c_euv_doc_content {
    flex: 1;
    min-width: 0px;
    max-width: var(content-max-width);
    display: flex;
    flex-direction: column;
    justify-content: flex-start;   /* pagination/footer follows article in normal flow */
    min-height: 100vh;             /* keeps the column at least one viewport tall */
}
```

DO NOT use `position: sticky` or `position: fixed` on the footer — the
user explicitly rejected both ("为什么固定?" / "不要固定").

DO NOT use `justify-content: space-between` on `c_euv_doc_content` —
it pushes short articles to the geometric middle of the viewport, leaving
a large blank band between the H1 page title and the article body.

### Pagination (equal-width prev/next, footer cleanly below)

Use CSS **grid**, not flex, for the pagination row. With `grid-template-columns: 1fr 1fr`
the two prev/next tracks split the row width **exactly 50/50** regardless
of link content length. Flex with `1 1 0` or `1 1 auto` does NOT achieve
this: each link starts at its content size (different per link because
page titles have different widths), and only the leftover space splits
evenly. Measured before/after the grid switch:

```
flex 1 1 auto:  prevW=298.25, nextW=301.16   (3 px difference — looks off)
grid 1fr 1fr:   prevW=299.703, nextW=299.703 (pixel-perfect)
```

The mobile breakpoint stacks the grid to a single column, which behaves
identically to the column-flex fallback. `minmax(0, 1fr)` is required so
long titles can ellipsize inside the track; bare `1fr` does not shrink
below content size and the second track overflows.

```css
c_euv_pagination {
  display: grid;
  grid-template-columns: 1fr 1fr;        /* desktop: exact 50/50 split */
  gap: var(--gap-component);
  margin-top: var!(space-2xl);
  min-width: 0;
  width: 100%;
  @media ((max-width: 767px)) {
    grid-template-columns: minmax(0, 1fr);  /* mobile: single column */
  }
}
pub c_euv_pagination_link {
  min-width: 0;        /* lets long titles ellipsize inside the grid track */
  border: format!("1px solid {}", var!(border));
  padding: var!(space-lg);
  cursor: "pointer";
  display: flex;
  flex-direction: column;
  gap: var!(space-2xs);
  overflow: hidden;
  :hover { border-color: var!(accent); }
}
/* Ellipsis needs all THREE properties — `text-overflow: ellipsis`
 * alone does nothing without `white-space: nowrap` (text wraps to a
 * second line) and `overflow: hidden` (the text fragment is still
 * painted). Verified by injecting a very long title into the live page:
 * `scrollWidth=608, clientWidth=274` → "Internationalization and
 * Localizati…" with the `…` glyph, single line. */
pub c_euv_pagination_text {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  min-width: 0;
}
c_euv_footer {
    /* Tight rhythm: 1.5rem margin-top matches the article→pagination gap,
     * 1rem padding top/bottom keeps the dashed separator close to the
     * text. The original 5rem margin (space-7xl) + 1.5rem padding
     * (space-2xl) pushed the footer far away from the pagination above it
     * — user reported "距离顶部艰巨太大, 都不符合规范". */
    margin-top: var!(space-2xl);
    padding: format!("{} 0px", var!(space-lg));
    border-top: format!("1px dashed {}", var!(border));
    text-align: "center";
    font-size: var!(font-sm);
    color: var!(muted-foreground);
}
```

`c_euv_pagination` margin-top should match — `var!(space-2xl)` (1.5rem).
Anything bigger reads as "too much gap before pagination" to the user.

DO NOT use `margin-top: auto` on the footer. `margin-top: auto` only
works when the footer is a flex item of a column flex container with
spare space — inside `c_euv_doc_tail` (a plain `display: block` wrapper)
it does nothing, and on long pages where content overflows the column
it also does nothing. The `space-between` on `c_euv_doc_content` is the
only mechanism that moves the tail.

### Viewport lock (sidebar pinned, main scrolls independently)

The single biggest gotcha in this layout. Without viewport lock the document grows past 100 vh, the whole shell scrolls together, and the sidebar slides off-screen.

Required combination:

```css
html, body { height: 100% !important; overflow: hidden !important; }
#app       { height: 100% !important; }

c_app_main { overflow-y: auto !important; overflow-x: hidden !important; }

c_app_nav {
  position: sticky;
  top: 0;
  align-self: flex-start;  /* override the row-flex `stretch` default */
  height: 100vh;            /* not `height: 100%` — that needs an
                               ancestor with explicit height, which the
                               viewport doesn't provide */
}
```

The root shell **must** carry the `c_app_root` class (`display: flex; height: 100%`); without it `html/body` height has nothing to attach to and `c_app_main`'s `overflow: auto` finds no scroll container. In `euv-docs/src/component/layout/view/fn.rs` the desktop shell root div needs `class: c_app_root()` added (mobile shell is structurally different and doesn't need it).

### TOC stickiness (right column also pinned while main scrolls)

Same viewport-lock pattern but with one extra requirement that bites hard: **`c_euv_doc_layout` must size to its content height, not to `c_app_main`'s visible height.** The default row-flex `min-height: 0` collapses the layout to one viewport tall, the right TOC's `position: sticky` range becomes a single viewport, and the TOC slides off-screen as soon as the user scrolls past one screenful.

```css
/* In euv-docs/src/lib.rs (or any caller that overrides the layout): */
.c_euv_doc_layout {
  min-height: auto !important;  /* NOT 0 — let it grow to content height */
  height: auto !important;
}
.c_euv_doc_toc {
  position: sticky !important;
  top: 0 !important;
  align-self: flex-start !important;  /* keep column at content height */
  max-height: 100vh !important;        /* let long TOC pages scroll inside */
  overflow-y: auto !important;
}

/* In ui/src/style/class/fn.rs (base UI): */
c_euv_doc_toc {
  position: sticky;
  top: 0;
  padding-top: var!(padding-main-top);
  /* no align-self override — leave it stretch so sticky range = full article */
}

c_euv_toc {
  /* remove the original `position: sticky; top: 76px` — the outer
     c_euv_doc_toc is already sticky, double-stickying double-offsets. */
  display: flex;
  flex-direction: column;
  gap: var!(space-xs);
  border-left: 1px solid var!(border);
  padding-left: var!(space-lg);
}
```

Verify after the change: `getBoundingClientRect().height` on `.c_euv_doc_layout` should match the article's natural height (~1600 px on long docs), and `getBoundingClientRect().top` on `.c_euv_toc` should stay pinned near the top of `c_app_main` after `main.scrollTop = 600`.

## Pitfalls

- **`EUV_DOCS_SRC_DIR` defaults to `euv-docs/docs/`, which is mostly empty.** First symptom: every route 404s after a build. Always set it to `/Users/sqs/code/euv/cli/docs` for the actual sample content.

- **`password_gate` Rust 2015 lint errors are project noise, not your bug.** `euv-docs/src/component/password_gate/view/fn.rs` errors with `async fn is not permitted in Rust 2015` and `let chains are only allowed in Rust 2024 or later`. The `patch` tool surfaces them, but they were there before your edit; `wasm-pack build` ignores them and the build still succeeds. Do not chase them.

- **`calc(...)` inside `class! { ... }` blocks must be wrapped in `format!()`, not used raw.** The macro expands to string concatenation; bare `calc(var!(x) - 1px)` parses as Rust syntax and errors with `invalid suffix 'px' for number literal` and `cannot find function 'calc'`. Always write `padding-left: format!("calc({} - 1px)", var!(space-md));`. Look for the existing call sites (e.g. `format!("calc({} - 1px)", var!(space-md))`) as a reference pattern.

- **Never use `/* ... */ \` inside `inject_css("""... \`)` strings.** The trailing `\` after `*/` makes rustc parse `*/` as a line-continuation start and error with `unknown start of token: \`. Use `// line comments` inside the string body.

- **`height: 100%` on `.c_app_nav` silently fails** when no ancestor has explicit height. The document body expands to fit content, so 100 % becomes "whatever fits," and the sidebar scrolls with the page. Use `height: 100vh` plus the viewport-lock pattern above.

- **Row-flex containers default to `min-height: 0` inside flex parents.** This collapses `c_euv_doc_layout` to one viewport tall inside `c_app_main` (which is itself a flex column in euv-docs). Symptom: the right TOC's `position: sticky` disengages after one screen of scrolling because the sticky range equals the collapsed layout height. Override to `min-height: auto !important; height: auto !important` on any row-flex container that holds a sticky side column.

- **`c_euv_doc_content > div:not(...)` blanket styling breaks pagination.** It forced pagination's inner `<div>` into column flex, making the prev/next row collapse and the footer bleed into the prev box. Always target known specific descendants: `c_euv_doc_content article.md-body`, `c_euv_doc_content article.md-body > div`, `c_euv_doc_toc`, `c_euv_pagination`, `c_euv_pagination_link`, `c_euv_footer`, `c_euv_doc_tail` — each as its own rule.

- **`display: contents` on the `c_euv_doc_tail` wrapper defeats the
  `space-between` contract.** The wrapper's job is to group pagination +
  footer into ONE flex item so `c_euv_doc_content` distributes two items,
  not three. With `display: contents`, the wrapper is skipped and
  pagination + footer act as direct children of `c_euv_doc_content`,
  producing three items where `space-between` puts the middle one (footer)
  in the wrong place. Use `display: block` (or no display rule at all
  — block is the default for `<div>`).

- **`flex: 1 1 auto` on `c_euv_pagination_link` does NOT give equal-width columns.** Even though both links have `flex-grow: 1`, each starts at its content size (different page-title widths mean different basis), and only the leftover space is split evenly. Measured: prevW=298.25, nextW=301.16 — a 3 px gap that reads as visually off-balance. Use CSS grid (`grid-template-columns: 1fr 1fr`) for true 50/50 split regardless of content length. Mobile breakpoint collapses to `minmax(0, 1fr)` (single column, sizes to content).

- **Pagination text ellipsis needs all three properties together** (`white-space: nowrap; overflow: hidden; text-overflow: ellipsis`). `text-overflow: ellipsis` alone is a no-op — without `white-space: nowrap` the title wraps to a second line and the ellipsis never fires; without `overflow: hidden` the text fragment is still painted past the box edge. The middle `min-width: 0` on `c_euv_pagination_text` is also required because flex/grid items default to `min-width: auto` (= content size), which prevents the box from shrinking below content width and the ellipsis never engages. Apply this pattern to `c_euv_pagination_text` (page title inside the link), not the link itself — the link uses `overflow: hidden` to clip its own contents, the title uses ellipsis to truncate the text inside.

- **`align-self: stretch` (row-flex default) on the sidebar fights `position: sticky`.** Without `align-self: flex-start`, the sidebar stretches to match the main column's height (which equals the document height when content is long), and sticky has no room to pin. Always set `align-self: flex-start` together with `position: sticky; height: 100vh`.

- **The user does NOT want a sticky/fixed footer on mobile.** After one
  iteration that implemented `position: sticky; bottom: 0` (which DID push
  the footer to viewport bottom), the user asked "为什么固定?" and then
  "不要固定". The accepted pattern is `space-between + min-height: 100vh`
  with a `c_euv_doc_tail` wrapper around (pagination + footer) — see
  "Footer at end of article" section above. Do not re-propose sticky as
  the answer; it has been tried and rejected.

- **The CSS inside `Css::inject_css(""" ... \`)` should contain NO
  comments.** The user reported "注入的css不需要任何注释" — even useful
  multi-line `/* ... */` blocks documenting the rationale must be
  stripped from the injected stylesheet. The reasoning belongs in
  source comments next to the `inject_css` call (Rust line comments) or
  in commit messages, NOT inside the CSS string body. Strip them all
  before merging.

- **`c_euv_pagination` margin-top should be ~`space-2xl` (1.5rem = 24px),
  not `space-4xl` or larger.** User feedback: "距离上面元素太大". The
  base UI default was `space-4xl` (2.5rem = 40px), and the docs override
  ALSO added `padding-top: space-4xl` on top of that — combined ~104px
  of empty space above the pagination boxes. Use `space-2xl` (24px) for
  both the base rule and remove the docs-only `padding-top` override.

- **`c_euv_footer` margin-top should be ~`space-2xl` (24px) and padding
  ~`space-lg` (1rem).** User feedback: "距离顶部艰巨太大, 都不符合规范".
  The original `space-7xl` (5rem = 80px) margin + `space-2xl` padding
  looked detached from the pagination above it.

- **`c_nav_footer` (sidebar bottom attribution line) should be centered**, not left-aligned. Add `justify-content: center; text-align: center` to it. The divider on top of it (`c_nav_footer_divider`) is `position: absolute` with `left: var(--space-lg); right: var(--space-lg)` so it stays full-width regardless of the link's own alignment.

- **CDP `CSS.forcePseudoState` requires `CSS.enable` first.** Calling `cdp('CSS.forcePseudoState', nodeId=nid, forcedPseudoClasses=['hover'])` without first invoking `cdp('CSS.enable')` in the same session fails with `{'code': -32000, 'message': 'CSS agent was not enabled'}`. Always pair them in the same `browser_exec` block — `browser_exec` runs each call in a fresh session, so a `cdp('CSS.enable')` from one call does NOT carry over.

- **The euv-docs live-reload SSE occasionally serves stale content.** After a `euv build`, hard-reload (Cmd+Shift+R) before measuring; the SSE `__euv_reload` endpoint sometimes misses the `Reload` event.

- **`Css::inject_css` accepts one big concatenated string**; you can append your override block to the existing one in `euv-docs/src/lib.rs` rather than adding a second `inject_css` call. Multiple `inject_css` calls work but stack the same rules twice in the document.

- **`!important` is necessary in the inline CSS block** to beat the upstream specificity of `euv-ui` class rules. Don't strip them — they're how the docs layer signals "this beats the upstream."

- **`border-left + padding-left compensation` cannot reliably keep text x stable across browsers.** Compensating `padding-left: calc(space-md + 3px)` for a `border-left: 3px solid` looks correct in math but block elements inside flex parents re-layout the inner padding box when the border appears, drifting the text by up to 6 px (measured: 48 px → 54 px on a 12-px-padded link). Use `box-shadow: inset 3px 0 0 0 color` instead — paint-only, provably zero layout impact, and verification via `getBoundingClientRect().left + parseFloat(borderLeftWidth) + parseFloat(paddingLeft)` returns identical bytes before and after a forced hover.

- **Unescaped `"` inside `// ... */ \` injected CSS comments terminates the surrounding string.** `Css::inject_css(""" ... \`)` strings are concatenated with `\` line-continuations; if a `/* ... */` block comment inside the string body contains a literal `"`, rustc parses it as the end of the `&str` literal and errors with `expected one of ), ,, ., ?, or an operator`. Stick to `//` line comments inside the CSS body, or write the comment without quotation marks (e.g. "the nearest left border" → "the nearest left border").

- **`article.md-body`'s direct DOM children are NOT the rendered markdown blocks.** The `euv_markdown` component renders into `<article class="md-body"><slot></slot></article>`, and the virtual DOM slot content is mounted as `<div>` wrappers under the slot at runtime. So `article.children.length === 1` (just the `<slot>`) and `article.children[0].tagName === "SLOT"`. A selector like `.md-body > :first-child { margin-top: 0 }` therefore targets the `<slot>` element (margin-top: 0 anyway), NOT the first H2/H3 paragraph the user sees. To remove the first block's top margin, use `.md-body h1:first-of-type`, `.md-body h2:first-of-type`, etc. (matches the first heading of each type anywhere inside the article — descendant selector, not direct child). Verify by inspecting `Array.from(article.children).map(c => c.tagName)` in the live DOM — if the only child is `SLOT`, you need `:first-of-type` selectors, not `:first-child`.

- **H1 page-title to first-content-block gap stacks three things.** When a page has a frontmatter `title:` (rendered as `<h1 class="c_docs_page_title">`) followed by a markdown body whose first element is a heading (H2/H3) or paragraph, the gap between them is `(c_docs_page_title margin-bottom, default 1rem) + (article-element margin-top on first block, e.g. .md-body h2 { margin-top: 1.8em } ≈ 43.2 px at font-2xl) + (any flex space-between gap pushing the article away from H1)`. Each layer looks small in isolation but adds up to 50–150 px. Fix in `euv-docs/src/lib.rs` injected CSS: set `.c_docs_page_title { margin: 0 }`, add `.md-body h1:first-of-type, .md-body h2:first-of-type, ... { margin-top: 0 !important }`, and use `justify-content: flex-start` (not `space-between`) on `.c_euv_doc_content` — see the Footer / pagination position section above.

- **Active sidebar item must dominate its hover state.** The blanket `.c_euv_sidebar_link:hover, .c_euv_sidebar_group_title:hover { ... }` rule matches both regular and `_active` variants (CSS class selectors don't exclude subclasses). On dark theme with `_active` carrying an accent background (e.g. `rgb(0,0,0)`), the inset 3 px bar drawn by `:hover` is the same color as the background — invisible in isolation but it kills the visual hierarchy: the user reads the item as "hovered regular link with a faint dark fill" rather than "this is the page you're on". Two-layer fix needed because the blanket rule and the base `_active:hover` rule both compete:
  - In `ui/src/style/class/fn.rs`: drop the inset bar on the `_active` variants — `:hover { box-shadow: none; }` on both `c_euv_sidebar_link_active` and `c_euv_sidebar_group_title_active`. Without `!important` here it loses to the `class!` macro output, but `class!` doesn't `!important` its `:hover` rules, so plain `none` works at this layer.
  - In `euv-docs/src/lib.rs` injected CSS: add explicit `_active:hover { box-shadow: none !important; }` (and a `.c_theme_dark` variant). The `!important` is required because the docs site's blanket hover rule has `!important` on its `box-shadow`. Specificity is identical between the two rules; later declaration wins for same-specificity `!important`s, so the `_active:hover` rules MUST be listed after the blanket ones in the injected string.
  - Verification: at the live page with the active item force-hovered via CDP `CSS.forcePseudoState`, `getComputedStyle(.c_euv_sidebar_link_active).boxShadow === 'none'` and `backgroundColor === rgb(0,0,0)` (the accent), confirming the accent fill is what the user sees. Same check on a non-active link hovered: `boxShadow === rgb(0,0,0) 3px 0px 0px 0px inset` (the bar still appears) — the hover affordance is preserved where it should be.

- **`location.reload()` does NOT bust the euv-docs wasm cache in the same tab.** The browser holds the `euv_docs_bg.wasm` response by URL (no query string, no Cache-Control forcing revalidation); even after a hard reload of the HTML, the WASM bytecode the JS glue imports is the previously-cached copy. Symptom: you rebuild, run `euv-docs`, the on-disk `dist/pkg/euv_docs_bg.wasm` has your new rules (verify with `strings dist/pkg/euv_docs_bg.wasm | grep '<your-rule-marker>'`), but the live DOM's `#euv-css-injected` text content still shows the old CSS — `cdp('CSS.forcePseudoState')` measurements and screenshots reflect the pre-fix state. Two reliable busts:
  1. Restart the static server on a different port (`python3 -m http.server 8426` instead of 8425) and open a fresh tab at the new URL.
  2. Append a query string to the wasm URL itself: change the `import` line in `dist/index.html` from `from './pkg/euv_docs_bg.wasm'` to `from './pkg/euv_docs_bg.wasm?v=' + Date.now()`, or hit the URL directly with `?cb=NNN` from the address bar.
  `Cmd+Shift+R` is NOT enough — the browser still serves the cached wasm. Always verify with one of the two methods above before claiming a CSS fix worked.

- **Markdown body goes AFTER the closing `---` of frontmatter, not between YAML keys.** Home page `docs/README.md` has YAML frontmatter with `home: true`, `heroText`, `tagline`, `actions:`, `stats:`, `sidebar_order:` — and VuePress-style lets the body Markdown follow the closing `---`. Inserting a `## heading` Markdown block between `stats:` and `sidebar_order:` makes the body land INSIDE the YAML frontmatter, which silently corrupts `sidebar_order` (YAML sees the heading as a literal string and breaks the list). Symptom: heroText/actions render but sidebar disappears or hero stats mis-count. Always insert Markdown body after the closing `---` of the frontmatter block; if `stats:` is the last key before the closing `---`, write your new section below `---`. Pattern check before/after the patch: `awk 'NR==1,/^---$/ {print}' docs/README.md | head -3` should show the frontmatter opener; `awk '/^---$/{c++; next} c==2' docs/README.md` should list the body.

- **Self-contained `::before` rules: a more-specific rule that only declares one prop can revert the whole pseudo-element to invisible.** When two `::before` rules overlap (e.g. base `c_euv_sidebar_link::before { content: ''; position: absolute; left: -8px; width: 5px; … }` and the more-specific `c_euv_sidebar_link_active::before { background: var(--accent) }`), the more-specific rule wins for props it declares (background), but for props it DOESN'T declare, the cascade does NOT silently merge with the less-specific rule — the missing props revert to the user-agent default (or to `none`/`auto`/`0`). Symptom: a rule that *looks* like it should "just change the colour" leaves the `::before` with `content: none` (no pseudo-element rendered at all), `position: static` (no longer positioned where expected), and the bar disappears. Fix: the more-specific rule must redeclare EVERY prop the less-specific rule declared, all with `!important` — `content: '' !important; position: absolute !important; top/bottom/left/width/pointer-events: ... !important; background: ... !important`. Verify by reading `getComputedStyle(el, '::before').content` after applying the more-specific rule; if it returns `'normal'` (the UA default for `content: none`), the rule is incomplete and the `::before` isn't being rendered.

- **`transition: font-weight` (and similar animatable non-numeric props) stalls when a MutationObserver removes then re-adds the same class in the same tick.** A `MutationObserver` watching the URL hash will fire on every class mutation it observes; if your handler does `links.forEach(a => a.classList.remove(...))` followed by `links[best].classList.add(...)`, both operations are mutations and trigger more observer callbacks. When the same prop is animated by a CSS transition, the remove starts a transition back to the base value, and the immediate re-add cancels or reverses the transition mid-flight — the final computed value lands somewhere between the two endpoints, and depending on browser timing can stay at the base value forever. Symptom: live test shows `getComputedStyle(activeLink).fontWeight === '700'` for one element but `'400'` for another even though both have the same class list. Fix: either drop the `transition: <prop>` declaration on the elements you're manipulating programmatically, or use a CSS animation that fires once on class add rather than a transition that fires on every prop change. Verify by reading `el.getAnimations().length` after the manipulation completes — if non-zero, a transition is mid-flight and may not have settled; wait for it to finish or remove the transition.

- **The `euv_toc` component renders one `<a class="c_euv_toc_link">` per heading with no built-in active state.** The framework's right-side TOC is purely static markup — no scroll-spy, no `:target`-driven class swap, no hash-route matching. To get an "active" look on the currently-viewed section you must add it yourself in docs-side JS. The two signals available are `window.location.hash` (which is the *clicked* anchor, not the *currently scrolled-into-view* anchor — close enough for click-driven navigation but stale on scroll) and an `IntersectionObserver` on each `<h2>/<h3>` heading inside the rendered markdown (true scroll-spy but heavier and harder to integrate into the virtual DOM). For the click-driven case: a single `js_sys::eval("…")` call in `euv-docs/src/lib.rs` that registers both a `hashchange` listener and a `MutationObserver` on the toc container, computes the best-matching link from the current URL fragment, and toggles `_active` / `_nested_active` on it — is sufficient. The MutationObserver is needed because route changes re-render the whole toc subtree and the hashchange handler fires before the new DOM is mounted.

### Right-side TOC active highlight (no built-in framework support)

The framework renders the right-side table-of-contents as a static list of `<a class="c_euv_toc_link">` / `<a class="c_euv_toc_link_nested">` — no active state, no scroll-spy, no `:target` class swap. To highlight the currently-viewed section, layer two pieces into `euv-docs/src/lib.rs`:

1. **CSS** that makes hover and the synthesized `_active` state bold, plus dark-theme variants:

```css
.c_euv_toc_link, .c_euv_toc_link_nested {
  font-weight: 400 !important;
}
.c_euv_toc_link:hover, .c_euv_toc_link_nested:hover {
  color: var(--accent, #000) !important;
  font-weight: 700 !important;
}
.c_euv_toc_link_active, .c_euv_toc_link_nested_active {
  color: var(--accent, #000) !important;
  font-weight: 700 !important;
}
.c_theme_dark .c_euv_toc_link_active,
.c_theme_dark .c_euv_toc_link_nested_active {
  color: var(--background, #fff) !important;
}
```

Do NOT add `transition: font-weight 0.15s` here — the JS below removes + re-adds the class on every hashchange / route mutation, which stalls the transition mid-flight and leaves the active link visually unbolded. Bold is an instant state, not an animated one.

2. **JS** mounted via a second `js_sys::eval("…")` after `App::mount(...)`:

```js
(function(){
  var container = document.querySelector('.c_euv_doc_toc');
  if (!container) return;
  function apply(){
    var h = (window.location.hash || '').split('#').pop() || '';
    h = h.toLowerCase();
    var links = container.querySelectorAll('a');
    var best = null, bestLen = 0;
    links.forEach(function(a){
      a.classList.remove('c_euv_toc_link_active');
      a.classList.remove('c_euv_toc_link_nested_active');
      var href = (a.getAttribute('href') || '').split('#').pop() || '';
      if (!href) return;
      href = href.toLowerCase();
      if (h && h.indexOf(href) === 0 && href.length > bestLen) {
        best = a; bestLen = href.length;
      }
    });
    if (best) {
      var add = best.classList.contains('c_euv_toc_link_nested')
        ? 'c_euv_toc_link_nested_active' : 'c_euv_toc_link_active';
      best.classList.add(add);
    }
  }
  apply();
  window.addEventListener('hashchange', apply);
  new MutationObserver(apply).observe(container, {childList: true, subtree: true});
})();
```

The longest-prefix match handles nested anchors (e.g. `#installation-via-cargo` correctly matches `#installation` when the more specific anchor doesn't exist). The `MutationObserver` catches route re-renders that wipe the toc subtree. Verify by clicking a different heading in the live page — the previously active link loses its `_active` class, the new one gains it, and `getComputedStyle(activeLink).fontWeight === '700'` (no transitions in flight).

## Verification

- `cargo check -p euv-ui` succeeds (rules are well-formed Rust syntax for the `class!` macro).
- `EUV_DOCS_SRC_DIR=... euv build -- --target web ...` produces `www/pkg/euv_docs_bg.wasm` and exits 0.
- Browser at `http://localhost:8765/#/guide/getting-started.html`:
  - Sidebar width `getComputedStyle(.c_app_nav).width` is between 248 and 320 px (clamp range) at the current viewport.
  - "Internationalization" leaf link sits on one line, text x matches the dashed border's right edge.
  - Force-hover on a leaf link via CDP `CSS.forcePseudoState(nodeId, forcedPseudoClasses=['hover'])` — call `cdp('CSS.enable')` first in the SAME `browser_exec` block (each block is a fresh CDP session). Only an inset 3 px shadow appears on the left of the padding box, no background tint, no real border, no text x shift. Verify by computing `getBoundingClientRect().left + parseFloat(borderLeftWidth) + parseFloat(paddingLeft)` for that link before and after forcing hover; the two values must be byte-identical.
  - `window.scrollTo(0, 800)` does not move `.c_app_nav` (sidebar top stays 0). Main column internal `scrollTop` advances instead.
  - `main.scrollTop = 600` does not move `.c_euv_toc` (TOC top stays pinned near the top of `c_app_main`).
  - Page bottom: PREVIOUS and NEXT boxes are two **pixel-exact equal-width columns** (both `getBoundingClientRect().width` must be byte-identical — typically 299.7 px on a 611 px pagination row), footer "MIT Licensed | …" is on its own line below them with the dashed separator. Long page titles inside the link truncate with `…` on the right edge (e.g. "Internationalization and Localizati…"), never wrap to a second line.
- Mobile emulation (set `Emulation.setDeviceMetricsOverride { width: 420, height: 800, deviceScaleFactor: 2, mobile: true }` AND reload in the same `browser_exec` block):
  - At `mobile_main.scrollTop = 0`: the sticky footer is pinned at the viewport bottom (`getBoundingClientRect().top ≈ viewportH - footerH`).
  - At `mobile_main.scrollTop = mobile_main.scrollHeight`: PREVIOUS and NEXT boxes each measure ~70 px tall (not 26 px — the latter means `flex: 1 1 0` was used and the text is clipped); the article's last paragraph ("Then open http://localhost:8080" + TIP block) is fully visible, not hidden under the sticky footer; the footer is still pinned at the viewport bottom.
- Diff `git diff ui/src/style/class/fn.rs euv-docs/src/lib.rs euv-docs/src/component/layout/view/fn.rs` is reviewable in one pass; no stray `replace_all` collisions.
