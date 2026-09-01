---
name: css-edge-cases
description: 'CSS box-model + DOM edge cases: borders/padding on wrapped inline content, baseline alignment of inline-block boxes, width-fill in table cells, **dropdown menu width vs trigger button alignment**, **percent-encoded anchor scroll in hash-router SPAs**, **secondary layout debt from removing a visual element (parent padding designed for a hover-revealed anchor now leaves dead whitespace on the heading)**, **when placement iteration is the wrong path — after 2 rounds of micro-tuning, propose the binary keep-it-or-drop-it choice**. Use when a styled element renders narrower/wider/taller than expected after wrap, baseline drifts from surrounding text, a TOC / menu / anchor click does not scroll, a header anchor clips out of viewport, or fixing one visual element makes the surrounding layout look misaligned. Triggers: inline code border missing on wrap, inline-block vertical-align off, td code fills too narrow, anchor # misaligned with heading, dropdown list narrower than trigger, TOC link no-scroll on Chinese page, multi-line framed text not on same baseline, heading text pushed right after hiding a per-heading glyph, "X is too far / X should align / X has gap" repeating across multiple PRs on the same selector.'
license: MIT
metadata:
  version: "1.3.0"
  category: frontend
  sources:
    - CSS Backgrounds & Borders Module Level 3 (W3C)
    - MDN box-decoration-break
    - MDN inline-block
    - MDN URL Encoding
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

---

## 5. Dropdown menu narrower than trigger button

**Symptom.** A `position: absolute; right: 0; min-width: 140px`
dropdown menu opens at exactly 140px wide even when its trigger
button is wider (e.g. a `width: 100%` trigger in a nav column
ends up 206px). The menu's right edge anchors to the dropdown
container's right edge but its left edge floats 60+px to the
right of the trigger's left edge, leaving a visible gap. Looks
like the menu is "shrinking into" the bottom-right corner of the
trigger.

This is not a wrapping / border / baseline issue — it's a
**container-width mismatch**: `min-width` only sets a floor; the
menu's actual width is shrink-to-fit of its widest item, so a
wider trigger never pulls the menu wider.

### The fix

Make the menu fill the dropdown container. With the trigger at
`width: 100%` of the same container, the menu and trigger line up
exactly on both left and right edges.

```css
.c_euv_dropdown {
    position: relative;       /* anchor for the absolute menu */
}
.c_euv_dropdown_menu {
    position: absolute;
    top: 44px;
    right: 0;
    width: 100%;              /* match the dropdown container (= trigger) */
    /* keep min-width: 0 — let items' padding guarantee a sensible floor */
    /* drop the old `min-width: 140px` */
}
```

If the trigger is wider than the menu's longest item, the menu
expands to match (good). If the trigger is narrower than 140px,
the menu shrinks below 140px — but inner item padding keeps the
content readable, so this is the right trade-off.

### Why not `width: max-content` or `min-width: max-content`?

`max-content` on a flex-column menu with multiple items resolves
to the longest item, which is exactly the bug we already have.
`min-content` collapses everything. `100%` matches the trigger
because the trigger matches the container, so all three line up.

### Verifying with Playwright

```python
pg.evaluate("trigger.click()")  # open the menu
pg.wait_for_timeout(800)        # wait for the open transition
info = pg.evaluate(r"""() => {
    const trigger = document.querySelector('.c_euv_dropdown > button');
    const menu = document.querySelector('.c_euv_dropdown_menu');
    const tr = trigger.getBoundingClientRect();
    const mr = menu.getBoundingClientRect();
    return {
        triggerW: tr.width, menuW: mr.width,
        triggerLeft: tr.left, menuLeft: mr.left,
        triggerRight: tr.right, menuRight: mr.right,
        triggerLeftEqMenuLeft: Math.abs(tr.left - mr.left) < 1,
        triggerRightEqMenuRight: Math.abs(tr.right - mr.right) < 1
    };
}""")
# Fix verified when:
#   triggerLeftEqMenuLeft AND triggerRightEqMenuRight are both true
```

Visual sanity check at `device_scale_factor: 4`: the menu's left
and right borders should align pixel-perfect with the trigger's
left and right borders. A 5+px gap on either side = still broken.

---

## 6. Percent-encoded anchor scroll fails in hash-router SPA

**Symptom.** Clicking a TOC link on a Chinese page
(e.g. `/zh/guide/getting-started.html#环境要求`) updates the URL
bar to `#/zh/guide/getting-started.html#%E7%8E%AF%E5%A2%83%E8%A6%81%E6%B1%82`
but **does not scroll** to the heading. The TOC item shows as
"active" in the URL but the page stays at top. English pages
work fine.

### Root cause

A hash router using `#<path>#<slug>` to encode both route and
in-page anchor exposes the slug to the browser's percent-encoding
machinery. `window.location.hash()` returns the encoded form for
non-ASCII slugs, but the heading `<h2 id="…">` attributes are
emitted in raw UTF-8 by the build script. `getElementById` of
the encoded slug returns `null` → the scroll handler falls back to
"back to top".

```
Browser URL:    #/zh/guide/getting-started.html#%E7%8E%AF%E5%A2%83...
location.hash:  "#/zh/guide/getting-started.html#%E7%8E%AF%E5%A2%83..."
After strip #1: /zh/guide/getting-started.html#%E7%8E%AF%E5%A2%83...
Split at # :    path = "/zh/guide/getting-started.html"
                anchor = "%E7%8E%AF%E5%A2%83..."
getElementById("环境要求") → element ✅
getElementById("%E7%8E%AF%E5%A2%83...") → null ❌
```

### The fix

Decode the anchor slug before any DOM lookup. One line, no new
dependency:

```rust
use js_sys::decode_uri_component;
// inside parse_route:
let anchor_decoded = js_sys::decode_uri_component(anchor)
    .ok()
    .and_then(|v| v.as_string())
    .unwrap_or_else(|| anchor.to_string());
```

For ASCII anchors, `decode_uri_component` returns the input
unchanged — no behaviour change. For non-ASCII, it round-trips
through UTF-8 and the `getElementById` lookup matches.

**Same fix in pure JS** (for framework users without Rust):
```js
const anchor = raw.split('#')[1];
const decoded = decodeURIComponent(anchor);
// then document.getElementById(decoded) for scrollIntoView
```

### Where the bug hides in the verification probe

The bug is invisible to a screenshot at any DPR — the page just
"looks like it didn't scroll". Two measurements matter:

```python
pg.evaluate("link.click()")  # click the TOC link
pg.wait_for_timeout(1500)
after = pg.evaluate("""() => {
    return {
        scrollTop: document.querySelector('[class*=c_app_main]').scrollTop,
        // AND: the actual heading top vs viewport top
        h2Top: document.getElementById('环境要求').getBoundingClientRect().top
    };
}""")
# Fix verified when:
#   scrollTop > 0    AND    h2Top is within 100px of viewport top
# Bug present when:
#   scrollTop === 0  OR   h2Top is far below the viewport top
```

Compare English vs Chinese side-by-side: identical scrollTop after
clicking equivalent TOC links means the fix landed. A 0 scrollTop
on Chinese but 47 on English is the smoking gun for this bug.

### Diagnostic for "the rule is in the CSS but does nothing"

If you fix this in `parse_route` and the bug still shows, check
whether the same anchor lookup is happening elsewhere in the code
(e.g. a separate `schedule_scroll` function that re-reads
`location.hash` and re-encodes). Fix once at the root, not in
every consumer.

---

## 7. Secondary layout debt: removing a visual element exposes parent padding designed around it

**Symptom.** You hide a per-element glyph that floats into the
parent container's left gutter (e.g. `display: none` a `.header-anchor`
that was doing `float: left; margin-left: -0.9em` next to each heading).
The user immediately reports "now the heading is no longer flush left"
or "there's a blank strip on the left of every title".

The heading element's left edge **did not move at all** — `getBoundingClientRect().left` is unchanged. What changed is **what the eye reads as the left edge**: with the glyph visible, the glyph occupied the leftmost ~24px of the row, so the eye registered "title text starts at the right of the glyph" ≈ "flush with the sidebar". Without the glyph, that 24px zone is empty whitespace, and the eye now reads "title text starts ~24px to the right of the sidebar".

This is the most common UX feedback after hiding a per-heading
hover anchor, a sidebar toggle icon, or any decorative inline
element that peeked into a gutter zone.

### Root cause

The gutter was originally justified by the now-removed element's
negative-margin float / position-absolute pattern:

```
main { padding-left: 28px; }       ← was designed to hold:
h1 .header-anchor {                 ←   this anchor in its gutter
    float: left;
    margin-left: -0.9em;            ← anchor extends left by ~24px
    opacity: 0;
}
h1:hover .header-anchor { opacity: 1; }

When the anchor exists: text starts at x=276 (main.left=248 + padding=28),
                       anchor paints at x≈249 — fills the gutter.
                       Eye reads "title flush left at sidebar edge".
When the anchor hidden: text still starts at x=276, gutter is empty.
                        Eye reads "title pushed right by 28px".
```

The padding wasn't a generic content gutter — it was the
**reservation** for the anchor. Hiding the anchor does not
eliminate the reservation.

### The fix

When you hide a decorative inline element that floated into a
parent gutter, **also collapse the gutter it occupied**, not just
the element itself. Site-local CSS override is appropriate when
the parent rule comes from a shared framework and other consumers
of that framework still want the gutter:

```css
/* hide the element */
.md-body .header-anchor { display: none !important; }

/* collapse the gutter it used to fill — asymmetrically:
   only zero the side the element was on, keep the other side
   so a sibling column (TOC) still has breathing room */
.c_app_main, .c_mobile_main {
    padding-left: 0 !important;
    padding-right: 28px !important;
}
```

### Why this is site-local, not a framework change

The framework's parent-padding rule is **correct for every other
consumer** that still renders the per-element glyph (and its
negative-margin float into the gutter). Don't push the change
upstream — it'd regress apps that rely on the glyph. Make it a
site-local CSS override at the same level where you hid the glyph.

### Verifying with Playwright — the 4-element probe

The bug is invisible at the heading element. You MUST walk the
parent chain to find which ancestor owns the dead whitespace:

```python
info = pg.evaluate("""() => {
    const h = document.querySelector('.md-body h1');
    if (!h) return {error: 'no h1'};
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
    // Also: bounding rect of the heading's text content
    // (skip display:contents wrappers that have no own box)
    let textLeft = null;
    if (h.querySelector('slot')) {
        const range = document.createRange();
        range.selectNodeContents(h.querySelector('slot'));
        const tr = range.getBoundingClientRect();
        textLeft = Math.round(tr.left);
    }
    return {chain, textLeft};
}""")
# Bug present when:
#   chain contains a {paddingLeft: "28px", paddingRight: "0px"} ancestor
#   AND the heading's text rect starts AT or AFTER that ancestor's left + padding
# Fix verified when:
#   that ancestor's paddingLeft is now 0
#   heading text rect left equals that ancestor's left
#   (other side, paddingRight, is unchanged if it was asymmetric)
```

Also compare sidebar right edge to heading text left:

| Sidebar right | Heading text left | Verdict |
|---|---|---|
| 248 | 248 | flush — fix landed |
| 248 | 276 | off by ~sidebar gutter width — bug present |

### Diagnostic when the parent isn't `<main>`

The dead gutter can live in any ancestor with non-zero padding.
Walk the chain and look for the **first ancestor whose padding
matches the visual gap**:

```python
# In the chain, find the smallest ancestor that is wider than its
# children, which is the layout container, then check its padding.
gutter_owner = next(
    (a for a in chain if a['paddingLeft'] != '0px'),
    None
)
```

If `gutter_owner` exists, that's where the fix goes.

### Lesson: don't ship a "hide X" CSS patch without re-screenshotting the parent

The 28px drift isn't visible in dev tools' "computed styles"
panel because no single element's value looks wrong. It's only
visible when comparing sidebar-right-edge to heading-text-left.
Always take a Playwright screenshot at the deployed URL after a
display:none fix and inspect the heading's horizontal position
relative to neighbouring landmarks (sidebar edge, sibling column,
viewport edge). If text is no longer flush with the landmark it
was flush with before, you've found secondary layout debt.

### Generalizing

This isn't specific to heading anchors. Any time you hide / remove
a visual element that:

1. Used `float: left/right` + negative margin to escape its parent, OR
2. Used `position: absolute` to occupy a reserved zone in the parent, OR
3. Was the only thing painting in a `padding-*` gutter

…expect the gutter to read as "dead whitespace" once it's gone.
Plan for a parent-padding adjustment in the same PR, not as a
follow-up. If you don't, the user will report "fix worked but now
content is misaligned" — and you'll open a follow-up PR for a
change that should have been bundled with the first.

Worked example with full Playwright probes and the local-vs-deployed
diff → `references/anchor-hide-secondary-layout-debt.md`.

---

## 8. When placement iteration is the wrong path — ask whether to keep the element at all

**Symptom.** You've shipped 3+ PRs adjusting the same element's
position, alignment, or visibility state. Each PR fixes one
specific gap or off-by-one measurement. The user keeps giving
feedback on the same element. The feedback cycle looks like:

> Round 1: "X is too far right" → you tighten `padding-left`
> Round 2: "X is too far left"  → you reverse to `left: 0`
> Round 3: "X should touch Y"   → you add `transform: translateX(-100%)`
> Round 4: "X doesn't align with Z on mobile" → you add `@media`
> Round 5: "X still has 20px gap on mobile"  → you shrink the box
> Round 6: User: "actually drop X entirely"

The element itself is fine — but the **design intent was wrong from
the start**, and each round of micro-tuning was just chasing the
previous round's mistake.

### When this pattern is happening

Look for these signals in the conversation log:

- **3+ PRs touching the same selector / element with overlapping intent.**
  `git log --oneline -- <file>` shows multiple commits all
  tweaking `.header-anchor` or similar.
- **Each new round cites a different metric from the last.**
  "8px gap" → "1px gap" → "20px overlap" → "baseline off" → "not aligned with body text".
  When the metric changes every round, the placement values are
  noise around a missing decision.
- **The element's "purpose" keeps getting reinterpreted.**
  Round 1: "X is a hover affordance" → Round 3: "X is a leading
  inline decoration" → Round 5: it doesn't have a clear purpose.
- **The user is reporting against landmarks that don't move**
  (sidebar edge, paragraph text x, viewport left). When the metric
  is "X should align with the static landmark," X is decorative
  and might not need to exist.

### What to do instead

**After the 2nd round of micro-tuning on the same element, before
opening the 3rd PR, propose a 2-option clarification**:

> "We're now on round 3 of tweaking the # glyph's placement. Two
> options at this point: (a) keep iterating placement until it's
> perfect, or (b) drop the glyph entirely via `display: none` and
> collapse the gutter it occupied (per §7). Which way?"

This forces the user to either commit to placement-perfection or
admit the element is decoration that doesn't earn its keep. The
clarify takes 30 seconds and saves the next 4 PR rounds.

### The two end-states

| User picks | Outcome |
|---|---|
| (a) Keep iterating | You continue with the 4-state probe pattern from `references/anchor-keep-hover-collapsed-placeholder.md`. Set explicit measurement targets ("geometric gap = 0 on mobile AND desktop") and stop when both are met — don't keep tuning after that. |
| (b) Drop it | Apply §7's hide-and-collapse-gutter pattern. One PR, done. Often the right call when the element is framework-default decorative content the consumer app never asked for. |

### Why this is a meta-lesson, not a CSS technique

This isn't about which CSS property to use. It's about
**recognizing a conversation pattern** that means the design
question is unsettled. The CSS primitives (`position: absolute`,
`transform`, `display: none`) are already covered in §7 and the
`anchor-keep-hover-collapsed-placeholder` reference. The new skill
here is **noticing when iteration has stopped being productive
and proposing the binary choice**.

### Worked example: euv-docs PR #19 → #27 (9 PRs, 6 days)

The full arc is documented in
`references/anchor-iterate-vs-drop-decision.md`. Short version:

| Round | PR | What changed | Why it didn't land |
|---|---|---|---|
| 1 | #19 | `display: none` the anchor | User: "now heading is no longer flush left" (§7 secondary debt) |
| 2 | #20 + #21 | Restore anchor + collapse `<main>` padding | User: "X is too far from heading text" |
| 3 | #23 | Tighten `padding-right` to `0.2em` (project inline gap spec) | User: "X is still too far" |
| 4 | #24 | `transform: translateX(-100%)` to make X touch heading text | User: "X doesn't align with body text" |
| 5 | #25 | Promote desktop override to mobile | User: "X has 20px gap on mobile" |
| 6 | #26 | Shrink anchor box (`display: block; width: auto`) to drop 20px gap | User: "drop X entirely on every viewport" |
| 7 | #27 | `display: none` X + collapse mobile `<main>` padding | shipped |

After round 7, the user had the same end-state as round 1 (PR #19),
plus the gutter collapse from round 2 (PR #20). **Rounds 2–6
were pure waste.** A clarification after round 2 would have
saved 4 PRs and ~20 minutes of build/deploy/probe cycles.

### Heuristic for when to trigger this clarification

If `git log --oneline -- <file>` shows ≥3 commits that all tweak
the same selector within a week, and the user has given explicit
visual feedback on that selector ≥2 times, the design question
is unsettled. Stop, propose the binary, and let the user pick.

This applies to any decorative visual element: header anchors,
sidebar toggles, hover-revealed icons, status badges, decorative
SVG flourishes. The pattern is the same regardless of which
specific element is involved.