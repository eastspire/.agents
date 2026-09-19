# Keep the hover-revealed glyph, kill its placeholder

Companion to `SKILL.md` §8. **Opposite design intent from §7**: the
user wants to **retain** the hover-revealed `#` glyph (it's the
affordance) but **eliminate the space it reserves** when invisible.

## Timeline (euv-dev/euv-docs 2026-08-31)

| PR | Title | Effect |
|---|---|---|
| #19 | hide hover anchor glyph | `.header-anchor { display: none }` — glyph gone. |
| #20 | pull md headings flush left | Asymmetric padding fix for §7's secondary debt. |
| #21 | revert #19 + #20 | User pushed back: `#` was a feature, hiding it regressed UX. |
| **#22** | **stop invisible `#` from reserving heading space** | **`position: absolute` lifts anchor out of flow entirely.** |

## Why "width: 0 / width: auto on hover" is wrong

First instinct: collapse the anchor's width when invisible, restore
on hover. Mechanically works — but **heading text shifts right by
the anchor's intrinsic width on every hover** because `float: left`
(desktop) / `display: inline-flex` (mobile) still applies.

| State | Idle text x | Hover text x | Jitters? |
|---|---|---|---|
| Upstream default | 276 | 276 | no |
| Width-toggle approach | 276 | ~288 | **YES — bug** |
| `position: absolute` approach | 276 | 276 | **no** |

The width-toggle approach was rejected after a Playwright probe showed
text x = 276 → 288 on hover.

## The fix that landed

```rust
Css::inject_css(
    "@media (min-width: 768px) { \
     .md-body .header-anchor { position: absolute !important; left: -0.9em !important; float: none !important; margin-left: 0 !important; padding-right: 0.2em !important; } \
     }",
);
```

Upstream already provides `position: relative` on `.md-body h1..h6`,
so the absolute anchor is positioned relative to its heading, not
the viewport. The anchor renders at `left: -0.9em` (= -27px on this
site's font) when `opacity` flips to 1, and **occupies zero flow
space** because absolute positioning removes it from the heading's
content area.

## The 4-state Playwright probe

Critical: verify text x **does not change** between idle and hover.

```python
# Idle
info_idle = pg.evaluate("""() => {
    const h = document.querySelector('.md-body h1');
    const a = h.querySelector('.header-anchor');
    const slot = h.querySelector('slot');
    const range = document.createRange();
    range.selectNodeContents(slot);
    return {
        textX: Math.round(range.getBoundingClientRect().left),
        anchorX: Math.round(a.getBoundingClientRect().left),
        anchorOpacity: getComputedStyle(a).opacity,
        anchorPosition: getComputedStyle(a).position,
        anchorLeft: getComputedStyle(a).left,
    };
}""")

# Hover
pg.locator('.md-body h1').first.hover()
pg.wait_for_timeout(700)
info_hover = pg.evaluate("""() => {
    const h = document.querySelector('.md-body h1');
    const a = h.querySelector('.header-anchor');
    const slot = h.querySelector('slot');
    const range = document.createRange();
    range.selectNodeContents(slot);
    return {
        textX: Math.round(range.getBoundingClientRect().left),
        anchorX: Math.round(a.getBoundingClientRect().left),
        anchorOpacity: getComputedStyle(a).opacity,
        anchorPosition: getComputedStyle(a).position,
        anchorLeft: getComputedStyle(a).left,
    };
}""")
```

Verified (euv-docs local build, 1280×900):

| Measurement | Idle | Hover | Verdict |
|---|---|---|---|
| `textX` | 276 | 276 | unchanged — fix landed |
| `anchorX` | 249 | 249 | same position |
| `anchorOpacity` | 0 | 1 | upstream toggle works |
| `anchorPosition` | `absolute` | `absolute` | override sticks |
| `anchorLeft` (computed) | `-27px` | `-27px` | pinned |

## Why @media (min-width: 768px) scope

Mobile uses a **different mechanism** — upstream's mobile rule is
`.md-body .header-anchor { display: inline-flex; width: 1.6em;
margin-left: -1.6em }` with `.md-body h1..h6 { padding-left: 1.6em }`
on the heading. That inline-flex + heading padding-left combination
already produces the right gutter placement on narrow viewports
(without the desktop float trick pushing `#` off-screen). Don't
override mobile unless you also redefine its `padding-left`.

## Why this is site-local, not framework

`euv-ui` ships `float: left; margin-left: -0.9em; opacity: 0` as the
default. This is **correct** for apps that want heading text to
permanently make room for the `#`. Other apps (blog readers, changelogs,
this docs site) want text flush left with `#` as a hover affordance.
Both are legitimate — the framework can't decide. Override at the
consumer site (euv-docs), not upstream.

## Lessons (extracted to SKILL.md §8)

1. **Don't ship `width: 0/auto` toggle fixes for hover affordances.**
   It always introduces text-shift on hover. Use `position: absolute`
   to remove the element from layout participation entirely.
2. **Verify with a 4-state probe** (idle / hover, position / text x).
   Single-state probes miss the text-shift regression.
3. **Scope the override to the breakpoint where it matters.**
   `@media (min-width: 768px)` keeps mobile's existing inline-flex
   mechanism untouched.
4. **Don't toggle positioning.** If you switch from `absolute` to
   `static` on hover, text jumps again. Keep `absolute` always.
5. **Upstream's deliberate choice is not your bug.**
   The `float: left; margin-left: -0.9em` exists because the
   framework author wanted heading text to permanently make room for
   `#`. If that doesn't match your design intent, override at the
   consumer level.

## Comparison to §7 (the other anchor reference)

| Aspect | §7 (anchor-hide-secondary-layout-debt.md) | §8 (this file) |
|---|---|---|
| User intent | remove `#` entirely | keep `#` but kill its placeholder |
| First instinct fix | `display: none` + parent padding 0 | `width: 0/auto` toggle |
| That fix's failure | works (whole element gone) | text jitters on hover |
| Correct fix | `display: none` + parent padding 0 | `position: absolute` always |
| Parent chain walks? | yes (find padding owner) | no (anchor is already self-contained) |
| Mobile handling | same rule covers both | scope to `@media (min-width: 768px)` |
| Probe shape | before/after parent padding + text x | 4-state: idle/hover, position/text x |