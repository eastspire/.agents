# euv `euv_markdown` Heading `#` Anchor Layout — Site-Local Override Recipe

When a docs site (e.g. `euv-docs`) uses `euv_markdown` to render markdown headings, every `<h1>..<h6>` gets wrapped in `<a class="header-anchor"><span>#</span></a>`. The default euv-ui behavior reserves horizontal space for the invisible anchor and pushes heading text right, so headings look indented even when `#` isn't showing. This file documents the site-local CSS overrides that fix that, without modifying euv-ui upstream.

## Background — what euv-ui does by default

Read `ui/src/component/markdown/view/fn.rs` and `ui/src/style/css/const.rs` for source. Key behaviors:

- **Desktop**: `.header-anchor { float: left; margin-left: -0.9em; opacity: 0; }` — anchor floats left with a negative margin, but its width still occupies ~12px in the heading's flow. Hover state changes only `opacity: 1`. Text stays pushed right even when glyph is invisible.
- **Mobile** (`@media (max-width: 767px)`): `.header-anchor { display: inline-flex; width: 1.6em; margin-left: -1.6em; }` paired with `h1..h6 { padding-left: 1.6em; }` — same placeholder problem, mobile-sized.

So the **visible symptom** is "headings look indented, even though `#` is invisible". The invisible anchor is the cause.

## The pattern that works — `left: -<glyph-width>em` on the absolute anchor

**Final working CSS** (euv-docs PR #24, merged at `d9abff8`):

```css
@media (min-width: 768px) {
    .md-body h1, .md-body h2, .md-body h3, .md-body h4, .md-body h5, .md-body h6 {
        padding-left: 0 !important;
    }
    .md-body .header-anchor {
        position: absolute !important;
        left: -0.87em !important;
        right: auto !important;
        float: none !important;
        margin-left: 0 !important;
        padding-right: 0 !important;
    }
}
```

Inject after `Css::inject_css(EUV_MD_CSS)` so cascade order places these after the upstream defaults. Wrap in `#[wasm_bindgen] pub fn main()` like the existing site CSS overrides.

### Why this geometry, measured

| Element | Idle x | Hover x |
|---|---|---|
| `<h1>` element left edge | 276 | 276 |
| Heading text "Getting Started" left | 276 | 276 (unchanged) |
| `.header-anchor` x range | 250–275 | 250–275 |
| `.header-anchor` opacity | 0 | 1 |
| Body paragraph text left | 276 | 276 |
| Visual gap `#` glyph right → "G" left | n/a (invisible) | ~1px (visually touching) |

- `#` glyph natural width is ~0.83em. `left: -0.87em` puts the glyph's right edge at the heading's left edge (`x=276`). The extra 0.04em absorbs the heading text's first-character side-bearing so `#` and "G" visually touch.
- **Heading text never moves on hover.** This is the key property: heading x stays at paragraph x = 276, so the left-aligned column reads as a single block regardless of hover state.
- `padding-right: 0` removes upstream's 0.2em slack (which would otherwise push `#` *farther* from the text in this new layout).

## Patterns that DON'T work — lessons from PRs #19..#23

A trail of failed designs in the euv-docs history (commits `510e248`..`c634cc3`). Captured so the next session doesn't redo them:

### ❌ Pattern A — `display: none` (PR #19, `510e248`)
`.md-body .header-anchor { display: none !important; }`  
Hides the anchor entirely. User then complained "I want the `#` to appear on hover, just not reserve space". Wrong direction.

### ❌ Pattern B — `position: absolute; left: -0.9em` (PR #22, `5fb0cfe`)  
Pulls `#` into the heading's left-margin zone, but `#` is far from the heading text. With h1 font ~30px and `#` glyph at `left: -0.9em = -27px`, the `#` glyph right edge sits at x=249, heading text at x=276 → only **2px gap**, visually detached.

### ❌ Pattern C — `padding-left: 0 → 1.1em` hover transition (PR #23, `c634cc3`)  
Keeps anchor at `left: 0`, animates heading `padding-left` from `0` to `1.1em` on hover. `#` and heading text sit on baseline with 0.2em gap when hovering. But heading text shifts from x=276 to x=309 on hover, breaking left-alignment with body paragraphs (which stay at 276). User feedback: "井号距离文字距离太大" — interpreted as horizontal position, not glyph-vs-text gap.

### ✅ Pattern D (winning) — `left: -0.87em` (PR #24, `d9abff8`)  
Heading `padding-left` stays at `0` always. Anchor pinned at `left: -0.87em`. Heading text never moves. `#` glyph touches "G" on hover. **Headings and paragraphs always aligned at x=276.**

## Math reference

| Constant | Value | Notes |
|---|---|---|
| `#` glyph natural width | ~0.83em (≈25px at 30px font) | Source: Playwright `getBoundingClientRect` |
| Heading font-size (h1) | 30px | From euv-ui heading scale |
| Standard `0.2em` inline gap | ~6px | Project convention (`padding-right: 0.2em` on buttons, anchors) |
| `<main class="c_app_main">` `padding-left` | 28px | euv-ui upstream; non-zero by design for breathing room |

`0.87em ≈ glyph-width 0.83em + 0.04em slack ≈ 25 + 1.2px`. Slack absorbs first-character side-bearing for typical Latin glyphs ("G", "P", etc.). If the heading text starts with an unusual glyph (CJK, math), retune slack and re-measure.

## Mobile — leave alone

The CSS override is scoped to `@media (min-width: 768px)`. Mobile uses a different mechanism (`display: inline-flex` + heading `padding-left: 1.6em`) that already produces the right gutter placement, and changing it would touch many sites. Don't try to "fix" mobile unless the user reports it specifically.

## Verification

Built locally with `cargo build -p <site> --target wasm32-unknown-unknown --release` + `wasm-bindgen` + `python3 -m http.server`. Then Playwright probe to read computed style:

```python
info = await page.evaluate("""() => {
    const h1 = document.querySelector('.md-body h1');
    const a = h1.querySelector('.header-anchor');
    return {
        h1_paddingLeft: getComputedStyle(h1).paddingLeft,
        anchor_position: getComputedStyle(a).position,
        anchor_left: getComputedStyle(a).left,
        anchor_float: getComputedStyle(a).float,
        anchor_paddingRight: getComputedStyle(a).paddingRight,
    };
}""")
```

Idle and hover x measurements via `getBoundingClientRect` on the `<h1>`, the heading text `<slot>`, and the `.header-anchor`'s `<span>`. Compare:

| Property | Pattern D (correct) |
|---|---|
| `anchor_position` | `absolute` |
| `anchor_left` | `-26.1px` (≈ `-0.87em` at 30px font) |
| `anchor_paddingRight` | `0px` |
| `h1.paddingLeft` (idle and hover) | `0px` |
| heading text x (idle and hover) | 276 (unchanged) |

If any of these differ, the override didn't apply (cascade ordering issue, or `!important` over-spec'd upstream).

## Deploy verification (cross-repo deploy chain)

Per `rust-wasm-gh-pages-deploy-pitfalls` SKILL.md main body, euv master merge does NOT auto-trigger euv-docs deploy. Sites with their own repo (e.g. `euv-dev/euv-docs`) have their own `.github/workflows/deploy.yml` that builds on push to master via `euv build` + `actions/upload-pages-artifact` + `actions/deploy-pages@v4`.

Post-deploy verification pattern (this PR was merged at `d9abff8`, deploy completed at `2026-09-01T00:58:35Z`):

```bash
# 1. Check deploy succeeded
gh run list --branch master --limit 5 \
  --json databaseId,headSha,status,conclusion,name,createdAt,updatedAt

# 2. Probe authoritative source (GitHub Pages)
#     euv-dev.github.io/<site>/  — sync within ~2 minutes of merge
playwright_probe -> https://euv-dev.github.io/euv-docs/#/guide/getting-started.html

# 3. Probe mirror (ltpp.vip) — lags by minutes-to-hours, NOT authoritative
#     ltpp.vip/github/pages/<org>/<site>/  — mirrors GH Pages via cron
#     cross-check: ltpp.vip wasm content-length vs GH Pages wasm content-length
curl -sI https://euv-dev.github.io/<site>/pkg/<site>_bg.wasm | grep content-length
curl -sI https://ltpp.vip/github/pages/<org>/<site>/pkg/<site>_bg.wasm | grep content-length
# If lengths differ, ltpp.vip mirror hasn't caught up yet
```

CSS verification must be done with Playwright (headless browser) reading `getComputedStyle()`, **not** curl. CSS is injected dynamically into `<style>` tags from the WASM binary's runtime, so the `.js` file source contains no CSS strings. curl will always see the old version until the WASM cache is busted — Playwright re-renders fresh on each page load.

When user asks "is it deployed yet", probe **both** URLs and report. If only the mirror is lagging, say so explicitly; if neither is up, report deploy status from `gh run list` and explain the build is still in progress.
