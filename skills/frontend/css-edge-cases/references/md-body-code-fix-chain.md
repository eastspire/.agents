# `.md-body code` Fix Chain (euv 0.18.15 → 0.18.26)

Concrete reference for the class of inline `<code>` styling bugs
worked through in `euv-dev/euv` between 0.18.15 and 0.18.26.
Each entry: symptom → root cause → fix PR → CSS diff → Playwright
verification recipe. Read this AFTER `SKILL.md` §1–4 — it's the
worked-example companion.

## The bug class

Inline `<code>` (or any inline element with border + background)
rendered in narrow containers must:
1. Keep all four borders closed on every line fragment when text wraps.
2. Stay vertically aligned with surrounding prose baseline.
3. Fill the full available width inside table cells when wrapping.

Each of these is a separate CSS problem. The fixes DO NOT compose
trivially — you can solve one and regress another. Document the
shape of each fix so the next session starts with the right one.

## Fix 1 — wrapping border close (PR #72)

**Symptom.** `display: inline` + `box-decoration-break: clone`
alone is not enough. Chromium paints first fragment's right border
and next fragment's left border on top of each other at the same
x-coordinate (because `padding` is shared across fragments), and
`var(--accent-muted)` background fills the visual gap, so the two
1px borders look like one continuous vertical line.

**Fix.** Promote to `display: inline-block`. Each wrap fragment
becomes its own box with its own 4 sides.

```css
.md-body code {
    -webkit-box-decoration-break: clone;
    box-decoration-break: clone;
    display: inline-block;
}
```

**Verify.** `getComputedStyle(code).display === 'inline-block'`,
`getBoundingClientRect().width > 0 && .height > 0`, all four borders
=== `'1px solid rgb(...)'`. Then visual at `device_scale_factor: 4`.

## Fix 2 — baseline alignment (PR #77)

**Symptom.** After Fix 1, the inline-block `<code>` box visually
sits BELOW the surrounding prose baseline. Specifically the box
appears ~10–15px lower than expected on a `<code>` mid-sentence in
a `<li>`. Reason: `vertical-align: text-top` + `line-height: 1.4`
anchors the box top to the line top, then the box's own line-height
extends it downward, so the box bottom (and the glyph baseline
inside it) lands well below the parent's baseline.

User reports this as "`已安装` and `euv-cli` code are not on the
same horizontal line" — the framed text and the surrounding text
look like two different lines.

**Fix.** Use `vertical-align: baseline` + `line-height: 1`. The
inline-block has no extra leading so its baseline lines up with the
parent line's baseline.

```css
.md-body code {
    display: inline-block;
    vertical-align: baseline;  /* was: text-top */
    line-height: 1;            /* was: 1.4 */
}
```

**Common mistake.** Setting `vertical-align: middle` makes it worse
on wrapped `<code>` — `middle` aligns the box's vertical centre
with the line's x-height centre, so a tall wrapped `<code>` ends up
higher than a single-line one. `baseline` is the only correct value
when the inline content is just text glyphs.

**Verify.** Use Range API to extract the glyph baseline of the
`<code>` text vs the parent's text baseline. Delta should be < 3px.
See `SKILL.md` §5 for the probe script.

## Fix 3 — table-cell width fill (PR #79 + #80)

**Symptom.** A long inline `<code>` inside a narrow `<td>` (e.g.
`::: tip / warning / danger / note` in a feature-comparison table
column) wraps into a TALL NARROW box with a lot of empty space on
every shorter line. The box width = longest word + padding, NOT
the cell width, because `display: inline-block` shrinks to content.

**Fix.** Promote to `display: block` inside table cells so the box
fills the cell.

```css
.md-body td code,
.md-body th code {
    display: block;
}
```

### Two pitfalls when applying this fix

#### Pitfall 1: `td > code` direct-child selector doesn't match

euv-docs / VuePress insert `display: contents` `<div>` / `<slot>`
wrappers between the cell and the `<code>` at build/render time:

```
TABLE > TR > TD > DIV(display:contents) > SLOT(display:contents) > DIV(display:contents) > CODE
```

`td > code` therefore never matches the live DOM. Use the descendant
selector `td code` (which reaches the same element regardless of
how many `display: contents` wrappers the framework inserts).

**Diagnostic recipe** — always verify the selector matches before
releasing:

```python
info = pg.evaluate("""() => {
    const code = Array.from(document.querySelectorAll('.md-body code'))
        .find(c => c.textContent.includes('::: tip'));
    if (!code) return null;
    let chain = []; let p = code;
    while (p) { chain.push({tag: p.tagName, disp: getComputedStyle(p).display}); p = p.parentElement; }
    return {
        chain,
        matchesTdDirectChild: code.matches('td > code'),
        matchesTdDescendant: code.matches('td code'),
        computedDisplay: getComputedStyle(code).display
    };
}""")
# If matchesTdDirectChild=false && matchesTdDescendant=true, use the descendant selector.
```

#### Pitfall 2: specificity is enough — don't add `!important`

CSS specificity for the two rules:

| Selector | Specificity |
|---|---|
| `.md-body code` | (0, 1, 1) |
| `.md-body td code` | (0, 1, 2) |

`(0, 1, 2)` beats `(0, 1, 1)` at the element-tag column. No
`!important`, no class duplication needed. Verify by querying
`document.styleSheets` for matching rules on the element after
deploy.

**Verify.** `getComputedStyle(code).display === 'block'`,
`getBoundingClientRect().width ≈ td_width − 2 × td_padding − 2 ×
code_border` (within 1–2px). If the box still shrinks to longest
word, the selector isn't matching — check Pitfall 1.

## Fix 4 — mobile header `#` anchor alignment (PR #74, #75, #76, #78)

Distinct bug class from `<code>`. The `<a class="header-anchor">`
inside `<h1>–<h6>` needs different handling because of how the
desktop layout (negative `margin-left: -0.9em` floats the anchor
to the left of the heading text) breaks on narrow viewports.

### Stage A: keep anchor inside viewport (PR #74)

**Symptom.** On a 380px viewport, the `<h1>` hover anchor's `#`
sits at `x ≈ -11px` — clipped outside the viewport.

**Fix.** Mobile media query overrides the desktop float pattern:

```css
@media (max-width: 767px) {
    .md-body .header-anchor {
        float: none;
        margin-left: 0;
        margin-right: 0.3em;
        padding: 0;
        display: inline-block;
    }
}
```

### Stage B: anchor interferes with first-line wrap (PR #75)

**Symptom.** Even after Stage A, a long heading like "Markdown
Features" wraps with "Features" alone on the second line and a
huge empty space after "Markdown" — because the inline-block
anchor occupies ~25px of the first line.

**Fix (v1 — later superseded).** `position: absolute` + heading
`padding-left: 1.6em` so the anchor lives in the gutter:

```css
@media (max-width: 767px) {
    .md-body h1, .md-body h2, .md-body h3,
    .md-body h4, .md-body h5, .md-body h6 {
        position: relative;
        padding-left: 1.6em;
    }
    .md-body .header-anchor {
        position: absolute; left: 0; top: 0;
        height: 100%; width: 1em;
        display: inline-flex; align-items: center; justify-content: center;
    }
}
```

### Stage C: anchor not vertically aligned with first-line text (PR #78)

**Symptom.** After Stage B, the `#` appears on the geometric
vertical centre of the heading box. For wrapped headings like
"Markdown Features" that puts `#` BETWEEN the two lines — visually
it looks like `#` belongs to "Features" not "Markdown", and the
two are not on the same horizontal line.

**Root cause.** `height: 100%; align-items: center` stretches the
anchor box to the full heading height and centres `#` in it. For a
two-line heading that centres on the line between the words, not
on the first word's baseline.

**Fix.** Remove `height: 100%`, switch to inline flow with
`vertical-align: baseline`:

```css
@media (max-width: 767px) {
    .md-body h1, .md-body h2, .md-body h3,
    .md-body h4, .md-body h5, .md-body h6 {
        padding-left: 1.6em;
    }
    .md-body .header-anchor {
        float: none;
        margin-left: -1.6em;          /* pull into the gutter */
        margin-right: 0;
        padding: 0; width: 1.6em;
        display: inline-flex;
        align-items: flex-end;        /* # baseline at box bottom */
        justify-content: flex-start;
        font-size: 0.85em;
        line-height: 1;
        vertical-align: baseline;
    }
}
```

Net effect: `#` glyph baseline lands on the heading's first-line
baseline, regardless of how many lines the heading wraps to.

### Companion fix — drop the dashed underline (PR #76)

`.md-body a` has global `text-decoration: underline dashed`. The
header anchor inherits it, leaving a short dashed line under `#`.
Visually noisy:

```css
.md-body .header-anchor { text-decoration: none; }
```

## Quick reference: which CSS property to use

| Goal | Wrong choice | Right choice |
|---|---|---|
| Keep wrapped `<code>` borders closed | `box-decoration-break: clone` alone | + `display: inline-block` |
| Align wrapped `<code>` to surrounding baseline | `vertical-align: text-top` | `vertical-align: baseline` |
| Fill table cell width with wrapped `<code>` | `display: inline-block` | `display: block` (with `td code` selector) |
| Match `<code>` inside `<td>` despite `display: contents` wrappers | `td > code` | `td code` (descendant) |
| Mobile `#` anchor visible in viewport | (desktop `float: left; margin-left: -0.9em`) | `position: absolute` + `padding-left: 1.6em` |
| Mobile `#` anchor on heading first-line baseline | `height: 100%; align-items: center` (geometric centre) | inline flow + `align-items: flex-end` + `vertical-align: baseline` |
| Dropdown menu matches wider `width: 100%` trigger | `min-width: 140px` + `right: 0` | `width: 100%` (drop the `min-width`) |
| TOC anchor scrolls on Chinese page (hash router) | `parse_route` returns raw anchor string | `decodeURIComponent(anchor)` before `getElementById` |

## Quick reference: Playwright baseline alignment probe

```python
# Skip display:contents wrappers when finding layout parent
def real_parent(el):
    p = el.parentElement
    while p and getComputedStyle(p).display === 'contents':
        p = p.parentElement
    return p

# For each inline element, find the nearest inline text on the same line box
delta = pg.evaluate("""() => {
    function realParent(el) {
        let p = el.parentElement;
        while (p && getComputedStyle(p).display === 'contents') p = p.parentElement;
        return p;
    }
    const results = [];
    document.querySelectorAll('.md-body code, .md-body a.header-anchor').forEach(el => {
        const cs = getComputedStyle(el);
        if (!cs.display.includes('inline') || cs.display === 'inline') return;
        if (!el.textContent.trim()) return;
        const rect = el.getBoundingClientRect();
        if (rect.height === 0 || rect.width === 0) return;
        const realP = realParent(el);
        if (!realP) return;
        const myCenterY = (rect.top + rect.bottom) / 2;
        let best = null;
        const walker = document.createTreeWalker(realP, NodeFilter.SHOW_ALL);
        let n;
        while (n = walker.nextNode()) {
            if (n === el || n.contains(el)) continue;
            let r = null, fontSize;
            if (n.nodeType === 3 && n.textContent.trim()) {
                try {
                    const range = document.createRange(); range.selectNode(n);
                    r = range.getBoundingClientRect();
                    fontSize = parseFloat(getComputedStyle(n.parentElement).fontSize);
                } catch(e) {}
            } else if (n.nodeType === 1) {
                const cs2 = getComputedStyle(n);
                if (cs2.display.includes('inline') && n.textContent.trim()) {
                    r = n.getBoundingClientRect(); fontSize = parseFloat(cs2.fontSize);
                }
            }
            if (!r || r.height === 0) continue;
            const overlapY = Math.min(rect.bottom, r.bottom) - Math.max(rect.top, r.top);
            if (overlapY < 4) continue;  /* must be on same line box */
            const baseline = r.bottom - fontSize * 0.2;
            if (!best || Math.abs(baseline - rect.bottom) < Math.abs(best.baseline - rect.bottom))
                best = {baseline, height: r.height};
        }
        if (!best) return;
        const elBaseline = rect.bottom - parseFloat(cs.fontSize) * 0.2;
        results.push({
            tag: el.tagName.toLowerCase(),
            text: el.textContent.trim().substring(0, 40),
            display: cs.display,
            va: cs.verticalAlign,
            delta: elBaseline - best.baseline,
            border: cs.borderTopWidth !== '0px',
            rectH: rect.height
        });
    });
    return results;
}""")
# Sort by abs(delta); |delta| > 5px is a real bug worth fixing
```

## Specificity quick reference

`.foo .bar baz` = (0, 1, 2) — two classes, one element
`.foo .bar .baz` = (0, 2, 1) — three classes, zero elements
`.foo .bar baz qux` = (0, 1, 3) — one class, three elements
`.foo .bar baz, .foo .bar baz` = same as one — duplicates don't sum

Common misconception: `.md-body td code` (0, 1, 2) is NOT less
specific than `.md-body code` (0, 1, 1). They differ at the element
column (2 vs 1), and (0, 1, 2) > (0, 1, 1). The class column is
equal. So the more-specific selector wins, no `!important` needed.
