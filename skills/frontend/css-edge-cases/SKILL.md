---
name: css-edge-cases
description: Borders/padding misbehaving on wrapped inline content.
license: MIT
metadata:
  version: "1.0.0"
  category: frontend
  sources:
    - CSS Backgrounds & Borders Module Level 3 (W3C)
    - MDN box-decoration-break
    - MDN inline-block
---

# CSS Edge Cases & Box-Model Quirks

CSS box-model behavior that does NOT match what the eye expects.
Each entry has (a) the visual symptom, (b) the root cause at the
box-model level, (c) the verified fix, and (d) the Playwright probe
used to verify it.

---

## 1. Inline element border collapse when text wraps

**Symptom.** An inline `<code>` (or any inline element) with a
visible border wraps to multiple lines in a narrow container. The
first line's right border and subsequent lines' left borders look
missing — only the very top of the first line and the very bottom
of the last line have borders.

### Why the obvious fix isn't enough

`box-decoration-break: clone` paints the border on each line
*fragment*, but on Chromium it does NOT close the visual gap:

- The first fragment's right border and the second fragment's left
  border paint at the same x-coordinate (because `padding` is
  shared across fragments).
- Any background color (`background: var(--accent-muted)` etc.)
  fills the gap between fragments, so the two 1px borders visually
  collapse into one vertical line — the right border of line 1
  *looks like* the left border of line 2, and neither looks fully
  closed.

### The fix that actually works

Treat the inline element as a block-level fragment per line:

```css
code {
    /* keep box-decoration-break as defensive fallback */
    -webkit-box-decoration-break: clone;
    box-decoration-break: clone;
    /* the real fix: force each wrap fragment to be its own box */
    display: inline-block;
    vertical-align: text-top;  /* or middle — depends on context */
    line-height: 1.4;           /* match surrounding text line-height */
}
```

This is the same pattern used by chip/tag components (e.g.
`euv_tag` uses `inline-block` + `vertical-align: middle` +
`line-height: 1` + `box-sizing: border-box`). When you find an
inline-with-border component, copy its CSS wholesale — the tag
pattern is canonical.

### When this matters most

- Inline `<code>` inside `<pre>` blocks that wrap on narrow viewports.
- Inline `<code>` inside `<td>` cells of narrow tables.
- Inline `<code>` inside `<li>` items in narrow sidebars.
- Any inline tag/chip component (border + padding) that may wrap.

### Verifying with Playwright

Don't trust screenshots at 1x DPR — borders are 1px and will alias.
Force `device_scale_factor: 4` (or higher) and screenshot the
element's `getBoundingClientRect()` clipped region:

```python
bbox = pg.evaluate("""() => {
    const el = document.querySelector('selector');
    el.scrollIntoView({block: 'center'});
    const r = el.getBoundingClientRect();
    return {x: r.x, y: r.y, w: r.width, h: r.height};
}""")
pg.screenshot(path='/tmp/bug.png', clip={
    'x': max(0, bbox['x']-10), 'y': max(0, bbox['y']-10),
    'width': bbox['w']+20, 'height': bbox['h']+20
})
```

Also probe `getComputedStyle` for confirmation:

```python
cs = pg.evaluate("""() => {
    const el = document.querySelector('selector');
    const cs = getComputedStyle(el);
    return {
        display: cs.display,
        borderTop: cs.borderTopWidth + ' ' + cs.borderTopStyle,
        borderRight: cs.borderRightWidth + ' ' + cs.borderRightStyle,
        borderBottom: cs.borderBottomWidth + ' ' + cs.borderBottomStyle,
        borderLeft: cs.borderLeftWidth + ' ' + cs.borderLeftStyle,
        boxDecorationBreak: cs.boxDecorationBreak,
        width: el.getBoundingClientRect().width,
        height: el.getBoundingClientRect().height
    };
}""")
```

`display === 'inline-block'` and all four borders === `'1px solid'`
are necessary but NOT sufficient — they only prove the rule is
applied, not that the visual rendering closes. Always visually
verify at high DPR.

---

## 2. Reading the actual rendered CSS, not what you wrote

When the deployed site uses a library version that may differ from
your local checkout (e.g. cargo workspace resolves a newer semver
from crates.io than the version in your local lock file), don't
trust your local source. Verify what the browser actually applied:

```python
info = pg.evaluate("""() => {
    const el = document.querySelector('selector');
    return {
        outerHTML: el.outerHTML,
        computedDisplay: getComputedStyle(el).display,
        computedBorder: getComputedStyle(el).border,
        path: (() => {
            const path = []; let n = el;
            while (n && n !== document.body) {
                path.push({tag: n.tagName, class: n.className});
                n = n.parentElement;
            }
            return path;
        })()
    };
}""")
```

This is essential when verifying a fix end-to-end through a CI
deployed site — the wasm in `www/pkg/` may have been compiled
against a different crate version than the one in your local lock
file.

---

## 3. Pitfalls when probing a deployed SPA

- **Don't assume static `.html` paths exist** — most SPAs (e.g.
  euv-docs) use hash routing. The path that works is the one in
  the sidebar `<a href="#/guide/foo.html">`, not
  `/guide/foo.html` directly. A direct `curl` of the non-hash
  URL returns GitHub Pages' generic 404 page, NOT the rendered
  page — so don't conclude "site is broken" from a 404.
- **Wait for `wait_for_function` on a real DOM marker** —
  `wait_for_load_state('networkidle')` is not enough; wait for
  the specific element that proves the route resolved:
  `pg.wait_for_selector('.md-body code', timeout=10000)`.
- **Sidebar links may be outside the viewport** at narrow widths
  (sidebar collapses). Click via JS evaluate or set the hash
  directly instead of `pg.locator(...).click()`. Two reliable
  patterns:
  ```python
  # option A: set hash directly (after wasm is loaded)
  pg.evaluate("location.hash = '#/guide/markdown.html'")
  pg.wait_for_selector('.md-body code', timeout=10000)

  # option B: dispatch click via JS (avoids Playwright actionability checks)
  pg.evaluate("document.querySelector('a[href=\"#/guide/markdown.html\"]').click()")
  ```
- **Forcing viewport size change does NOT re-render CSS rules**
  that are already computed — but it does re-trigger wrapping for
  `inline-block` elements inside, which is what you want for
  narrow-width repro. Set viewport BEFORE clicking the link if
  you need the narrow layout from the start.
- **Playwright async API returns empty stdout in this environment**.
  Use the **sync API** (`from playwright.sync_api import sync_playwright`)
  when the script needs to print evaluated JS results — the async
  version sometimes swallows prints entirely.

---

## 4. Dynamic wrappers (`display: contents`) inside the inline element

**Symptom.** When the bug source is dynamic euv content (anything
rendered via `html! { ... }` at runtime, including text passed
through `EuvMdInline::Text("...")` then re-rendered), the actual
DOM may look like:

```html
<code><div style="display: contents;" data-euv-dynamic-id="266">::: tip / warning / danger / note</div></code>
```

The `<div style="display: contents">` is euv's wrapper for any
dynamic text node — it has no own box (width=0, height=0), the
text content flows directly into the parent.

This is FINE for `display: contents` semantics — the `<div>` does
not interfere with the `<code>`'s box model. But it WILL mislead
your probe: Playwright `element.querySelector('div')` returns the
inner div, and `getBoundingClientRect()` on it returns 0/0, which
makes you think there's a layout bug when there isn't.

**Verify with computed style + bbox on the OUTER `<code>`, not
the inner `<div>`:**

```python
info = pg.evaluate("""() => {
    const code = document.querySelectorAll('code')[0];
    const inner = code.querySelector('div[data-euv-dynamic-id]');
    const cs = getComputedStyle(code);
    return {
        outerDisplay: cs.display,
        outerBorder: cs.border,
        outerWidth: code.getBoundingClientRect().width,
        outerHeight: code.getBoundingClientRect().height,
        innerDisplay: inner ? getComputedStyle(inner).display : null,
        innerWidth: inner ? inner.getBoundingClientRect().width : null,
        innerHeight: inner ? inner.getBoundingClientRect().height : null,
        outerHTML: code.outerHTML.slice(0, 200)
    };
}""")
# The fix is verified when:
#   outerDisplay === 'inline-block'
#   outerBorder === '1px solid rgb(...)'
#   outerWidth > 0 && outerHeight > 0  (the wrap is real)
#   innerWidth === 0 && innerHeight === 0  (display:contents is a no-op)
```