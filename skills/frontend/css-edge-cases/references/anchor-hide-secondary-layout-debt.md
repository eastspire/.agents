# Secondary layout debt — anchor hide exposes dead `<main>` padding (euv-docs 2026-08-31)

Companion to `SKILL.md` §7. Worked example: hiding the per-heading `#`
anchor glyph on `euv-dev/euv-docs` exposed 28px of dead whitespace on
the left of every heading because `c_app_main`'s `padding-left` was
designed to reserve space for that anchor's negative-margin float.

## Timeline

| PR | Title | Effect |
|---|---|---|
| #19 | hide hover anchor glyph | `.header-anchor { display: none }` — glyph gone, but heading text `x=276` instead of `x=248` (sidebar right). User reports "left side is blank". |
| #20 | pull md headings flush left | Adds `.c_app_main, .c_mobile_main { padding-left: 0; padding-right: 28px; }` — heading text now at `x=248`, flush with sidebar. |

Both PRs were against `euv-dev/euv-docs`. Site-local CSS overrides
appended to `Css::inject_css(EUV_MD_CSS)` in `src/lib.rs::main()`,
alongside the existing anchor-hide rule.

## Why a separate PR was needed

The fix in #19 was complete on its own (the `#` glyph was gone, and
`<h1-h6>` kept their `id` for URL-hash deep linking). The user
perceived a new visual bug introduced by #19, but it was actually
**debt that #19 surfaced** — the `<main>` padding was always there,
just hidden by the now-removed anchor's negative-margin float.

Bundling the parent-padding fix into #19 would have been ideal, but
at the time of writing #19, we did not know the parent padding was
designed for the anchor (the euv-ui source was not on screen). The
user feedback ("标题直接靠左展示就行了") triggered the secondary
investigation.

**Lesson:** when you ship a "hide X" CSS fix, screenshot the parent
and compare sidebar-right-edge to heading-text-left. If they don't
match, #19 isn't done.

## The probe that found the dead padding

The heading element's own `.getBoundingClientRect()` showed `left=276`
on both before-fix and after-fix screenshots. The drift wasn't in
the heading — it was in the ancestor. Walking the parent chain
revealed `<main class="c_app_main">` with `padding-left: 28px`,
`padding-right: 0`.

```python
info = pg.evaluate("""() => {
    const h = document.querySelector('.md-body h1');
    const chain = [];
    let el = h;
    for (let i = 0; i < 8 && el; i++) {
        const r = el.getBoundingClientRect();
        const cs = getComputedStyle(el);
        chain.push({
            tag: el.tagName, class: el.className,
            left: Math.round(r.left), width: Math.round(r.width),
            paddingLeft: cs.paddingLeft, paddingRight: cs.paddingRight,
            marginLeft: cs.marginLeft, display: cs.display,
        });
        el = el.parentElement;
    }
    return chain;
}""")
# chain:
#  H1       left=276 width=736 padding=0/0      margin=0/0  display=block
#  DIV      left=0   width=0   padding=0/0      margin=0/0  display=contents
#  SLOT     left=0   width=0   padding=0/0      margin=0/0  display=contents
#  ARTICLE  left=276 width=736 padding=0/0      margin=0/0  display=block   ← .md-body
#  DIV      left=276 width=976 padding=0/0      margin=0/0  display=block   ← c_euv_doc_content
#  DIV      left=276 width=976 padding=0/0      margin=0/0  display=flex    ← c_euv_doc_layout
#  DIV      left=0   width=0   padding=0/0      margin=0/0  display=contents
#  MAIN     left=248 width=1032 padding=28px/0  margin=0/0  display=block   ← c_app_main ← here
```

Sidebar's right edge is at `x=248`. `<main>` left is at `248`. `<main>`
padding-left is `28px`. So content under `<main>` (everything after
the flex wrapper) starts at `248 + 28 = 276`. The heading text
inherited that, and the anchor used to occupy the 248-274 zone via
`float: left; margin-left: -0.9em ≈ -28px`. Without the anchor, the
zone is empty.

## The fix shape

Append the gutter-collapse to the same `Css::inject_css` call that
already has the anchor-hide rule:

```rust
Css::inject_css(
    ".md-body .header-anchor { display: none !important; } \
     .md-body h1:hover .header-anchor, \
     .md-body h2:hover .header-anchor, \
     .md-body h3:hover .header-anchor, \
     .md-body h4:hover .header-anchor, \
     .md-body h5:hover .header-anchor, \
     .md-body h6:hover .header-anchor { opacity: 0 !important; pointer-events: none !important; } \
     .c_app_main, .c_mobile_main { padding-left: 0 !important; padding-right: 28px !important; }",
);
```

Asymmetric: zero only the side the anchor occupied (`padding-left`).
Keep `padding-right` because the TOC column is on the right and still
needs breathing room before the viewport edge.

## Verification

Local wasm build + Playwright at 1280×900:

| Element | Before | After |
|---|---|---|
| `<main>` left | 248 | 248 |
| `<main>` padding-left | **28px** | **0px** |
| `.md-body` left | 276 | 248 |
| `<h1>` left | 276 | 248 |
| `<h1>` text rect left | 276 | 248 |
| Sidebar right edge | 248 | 248 |
| TOC column left | 1052 | 1052 (unchanged) |
| `<main>` padding-right | 0 | 28 (preserved for TOC) |

Build / lint / clippy:

```
cargo fmt --all
cargo check  -p euv-docs --target wasm32-unknown-unknown      # clean (3 pre-existing warnings)
cargo clippy -p euv-docs --target wasm32-unknown-unknown --no-deps  # clean (4 pre-existing warnings)
cargo build  -p euv-docs --target wasm32-unknown-unknown --release
wasm-bindgen target/wasm32-unknown-unknown/release/euv_docs.wasm \
    --out-dir pkg --out-name euv_docs --target web --no-typescript
python3 -m http.server 5181 -d pkg &
python3 /tmp/probe-local.py   # verifies the table above
```

## Why the same rule covers `c_app_main` AND `c_mobile_main`

On desktop, `c_app_main` is the layout column (sidebar + main).
`c_mobile_main` is the mobile counterpart where the sidebar lives
behind a drawer. On mobile there is no drawer/landscape gutter —
a 28px left padding has no element to hold, so the same `padding-left: 0`
is correct on both.

## Why this is site-local, not framework-level

`c_app_main` / `c_mobile_main` are in `euv-ui` (`~/github/euv-dev/euv/ui/`),
not in `euv-docs`. Many apps depend on euv-ui's `padding-left: 28px` to
hold the hover-revealed `#` anchor on each heading. Changing
euv-ui's rule upstream would break every app that uses the anchor.

The override must live in the consumer (euv-docs), not the framework.
If a future framework-level refactor changes `c_app_main` padding,
the override's `!important` keeps the euv-docs local fix intact.

## Lessons (extracted to SKILL.md §7)

1. **A "hide X" CSS fix is incomplete if a parent was designed around X.**
   Always re-screenshot the parent and compare against landmarks
   (sidebar edge, sibling column edge, viewport edge).
2. **The dead gutter is the price of removing a negative-margin float.**
   If you can't float into it anymore, the gutter should not exist.
3. **Walk the parent chain.** `getBoundingClientRect()` on the
   changed element alone won't tell you which ancestor owns the
   drift.
4. **Asymmetric padding collapse.** Zero only the side that held
   the now-removed element; keep the other side for sibling-column
   breathing room.
5. **Site-local override, not framework change.** The framework's
   rule is correct for the default case; this is a consumer-specific
   preference.