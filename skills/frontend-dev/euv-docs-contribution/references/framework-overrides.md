# euv-docs framework overrides — CSS selector reference

This file consolidates the site-local CSS overrides that any non-trivial euv-docs fork will eventually need. All rules are meant to be injected via `Css::inject_css(...)` AFTER `Css::inject_css(EUV_MD_CSS)` in `main()`. Always use `!important` so future upstream selector-specificity bumps don't silently revert your changes.

Verified against euv-docs 0.18.x and euv-ui 0.18.x (the versions that `~/github/euv-dev/euv-docs` Cargo.toml pins). Will need re-verification when those major versions bump.

## DOM cheat sheet (verified with Playwright on docs-pages/docs-euv)

```
c_app_root
└── c_theme_light
    ├── c_app_nav                          # sidebar (desktop)
    │   ├── c_nav_header                   # brand header <a> with logo + title
    │   │   ├── c_euv_logo                  # ALWAYS renders "E" literal (upstream)
    │   │   └── c_nav_brand_title
    │   ├── c_nav_locale_row               # only if multiple locales (skip if 1)
    │   ├── c_nav_section_label             # "目录" / "Guide" — section label
    │   ├── c_nav_items_scroll
    │   │   └── c_euv_sidebar_group          # recursively nested
    │   │       ├── c_euv_sidebar_group_title
    │   │       └── c_euv_sidebar_children   # border-left: 1px dashed, padding-left: 12px
    │   │           ├── <div>               # framework inserts an unclassed wrapper here
    │   │           │   ├── c_euv_sidebar_group   (nested groups)
    │   │           │   └── c_euv_sidebar_link    (leaf links)
    │   ├── c_nav_theme_toggle              # moon/sun toggle button
    │   └── c_nav_footer                    # "Built with Euv & Wasm"
    └── c_app_main                         # paddingTop: 24px
        └── c_page_container
            ├── c_home                      # home page
            │   └── c_home_feature_grid      # 36 cards (one per feature)
            │       └── c_feature_card        # NO border by default, NO link: support
            │           ├── c_feature_header / c_feature_name
            │           └── c_feature_desc
            └── article.md-body             # content page (slot wraps actual content)
                └── <slot style="display:contents">
                    └── div > h1/h2/.../p/pre/...  # actual rendered content
```

## Override 1 — feature card border

```css
.c_home_feature_grid .c_feature_card {
  border: 1px solid var(--euv-c-border, #e3e3e3) !important;
  border-radius: 8px !important;
  padding: 16px !important;
  transition: border-color 0.15s ease, transform 0.15s ease;
  cursor: pointer;
}
.c_home_feature_grid .c_feature_card:hover {
  border-color: var(--euv-c-brand, #3451b2) !important;
  transform: translateY(-2px);
}
@media (prefers-color-scheme: dark) {
  .c_home_feature_grid .c_feature_card {
    border-color: var(--euv-c-border-dark, #2e2e2e) !important;
  }
  .c_home_feature_grid .c_feature_card:hover {
    border-color: var(--euv-c-brand-dark, #a8b1ff) !important;
  }
}
```

Verify: `getComputedStyle(card).borderTopWidth === '1px'`, `borderTopColor === 'rgb(227, 227, 227)'` (light mode).

## Override 2 — nested sidebar group titles align with parent text

The cleanest working pattern (verified 2026-09-17 on docs-pages/docs-euv, three iterations deep):

```css
/* Top-level group titles keep upstream padding (text at x=22) */
.c_nav_items_scroll .c_euv_sidebar_group_title {
  padding-left: 20px !important;
}
/* Nested (depth-2, depth-3+) group titles: zero padding-left so text
   lands at x = group.x = 23 — same column as the parent group's text. */
.c_nav_items_scroll .c_euv_sidebar_children .c_euv_sidebar_group_title {
  padding-left: 0 !important;
}
```

The key trick: **put the nested rule AFTER** the top-level rule. Both have `!important` and same specificity; CSS cascade picks the **last matching rule**. Reversing them means the top-level `padding-left: 20px` wins and the nested titles still get `20px`.

**Critical**: the unclassed `<div>` wrapper between `.c_euv_sidebar_children` and `.c_euv_sidebar_group` exists in the actual DOM (verified by `getBoundingClientRect()`) — the wrapper sits between children container and the nested group. The descendant selector (`.c_euv_sidebar_children .c_euv_sidebar_group_title`) bypasses the wrapper, so it doesn't matter that the wrapper has no class.

Verify: walk every group title's inner `<a>`/`<span>`:

```js
const titles = [...document.querySelectorAll('.c_euv_sidebar_group_title')];
titles.map(t => t.querySelector('span, a').getBoundingClientRect().x | 0)
// → 22 for top-level ("LTPP-GIT仓库"), 23 for nested ("APP") — all group titles share one column
```

Leaf links (`c_euv_sidebar_link`) keep their original indent at x=23 (direct children of children container) or x=44 (children of a nested group). The hierarchy becomes visually obvious: all bold group titles share x=22, all leaf links are indented right.

### Earlier attempts that didn't work (avoid these)

1. **margin-left: -22px + padding-left: 0**: shifted nested text to x=0 (cut off the left side of the title — "A" of "APP" was clipped). Bad.
2. **margin-left: -1px + width: calc(100% + 1px) + padding-left: 0**: text at x=22 BUT the title element extends 1px past the parent group's right edge, which sometimes clipped the trailing arrow `▸` glyph.
3. **border-left: 1px dashed on the nested group itself**: created a second dashed rule inside the parent's children container. Both borders visible, looked messy.
4. **margin-left: 21px + width: calc(100% - 21px) on the group**: shifted entire group to the right, making nested title text end up at x=65, far from where we wanted it.

**What finally worked** — pure padding-left manipulation with cascade ordering:

## Override 3 — content page first heading y matches home hero

```css
.c_euv_doc_content > article > *:first-child {
  margin-top: 0 !important;
}
.c_euv_doc_content > article h1:first-of-type,
.c_euv_doc_content > article h2:first-of-type,
.c_euv_doc_content > article h3:first-of-type,
.c_euv_doc_content > article h4:first-of-type,
.c_euv_doc_content > article h5:first-of-type,
.c_euv_doc_content > article h6:first-of-type {
  margin-top: 0 !important;
  padding-top: 0 !important;
}
```

Without this: heading is at y=56.4. With this: y=24 (= `c_app_main` padding-top). Match home hero `c_home_title` exactly.

The slot host `<slot style="display:contents">` makes its children behave as direct descendants for layout purposes. So `> *:first-child` (catches the slot) AND `h*:first-of-type` (catches the first heading inside the slot) are both needed.

## Override 4 — heading anchor `#` glyph hidden + no horizontal space reserved

```css
.md-body h1, .md-body h2, .md-body h3, .md-body h4, .md-body h5, .md-body h6 {
  padding-left: 0 !important;
}
.md-body .header-anchor,
.md-body h1:hover .header-anchor,
.md-body h2:hover .header-anchor,
.md-body h3:hover .header-anchor,
.md-body h4:hover .header-anchor,
.md-body h5:hover .header-anchor,
.md-body h6:hover .header-anchor {
  display: none !important;
}
```

euv-ui wraps every heading in `<a class="header-anchor">#</a>`. Without override, this reserves ~12px horizontal space (desktop) or 1.6em (mobile) for an invisible glyph, pushing heading text right regardless of hover state. The anchor's `href` is still in the DOM so deep links resolve — just visually hidden.

## JS override — feature card click delegation

`EuvFeature` struct has no `link` field, so feature cards aren't clickable out-of-box. Inject JS from Rust via `js_sys::eval`:

```rust
const ROUTES_JSON: &str = r##"{"ltpp":"#/ltpp","hyperlane":"#/hyperlane/process.html"}"##;
// after App::mount("#app", app):
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
```

The `__docsEuvFeatureWired` flag prevents re-installation when `App::mount` re-renders after SPA route changes. The map stays as a `r##"..."##` literal in `lib.rs` — gets baked into the binary at compile time, no runtime JSON parsing needed.

## Hash route conventions

| Source `link:` | Hash rendered | Resolves to |
|---|---|---|
| `/foo` | `#/foo` | `docs/foo/README.md` (README auto-detect) |
| `/foo.html` | `#/foo.html` | `docs/foo.md` |
| `/foo/bar.html` | `#/foo/bar.html` | `docs/foo/bar.md` |
| `https://...` | (external) | new tab via `window.open` |
| `mailto:...` | `#/mailto:...` ❌ 404 | — framework doesn't recognize mailto |

Always use `.html` suffix in hero `actions[].link` for safety. The README auto-detect is convenient but only works when `README.md` exists at that path.