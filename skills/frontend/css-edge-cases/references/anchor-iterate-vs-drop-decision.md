# When "iterate on placement" is the wrong path — the euv-docs # anchor arc (PR #19 → #27)

Companion to `SKILL.md` §8. Full case study: 9 PRs across 6 days on
`euv-dev/euv-docs` adjusting the heading `#` anchor glyph's placement,
culminating in the user saying "drop the glyph entirely."

The lesson: rounds 2–6 of micro-tuning were wasted work. A clarification
after round 2 would have saved 4 PRs.

## Timeline

| Round | PR | Title (concise) | What it did | User reaction |
|---|---|---|---|---|
| 1 | #19 | hide hover anchor glyph | `.header-anchor { display: none !important; }` + hover opacity 0 | "you modified wrong project — actually undo and do euv-docs" |
| 2 | #20 | pull md headings flush left | Asymmetric `<main>` padding collapse (per §7) | "X is flush left now but where's the #?" |
| 2 | #21 | restore hover-revealed # glyph | Re-assert `opacity: 1` on hover | "X is too far from heading text" |
| 3 | #22 | stop invisible # from reserving heading space | `position: absolute; left: -0.9em; float: none` | "ok but X is now ~24px off the heading edge" |
| 3 | #23 | tighten # anchor spacing on hover (0.2em gap) | `padding-left: 1.1em` on hover, `padding-right: 0.2em` on anchor | "X still too far / doesn't align with body text" |
| 4 | #24 | make hover # glyph touch heading text | `transform: translateX(-100%)`, heading `padding-left: 0` | "no placeholder ✓ / but gap too big / doesn't align with body text" |
| 5 | #25 | promote desktop override to mobile | Remove `@media (min-width: 768px)` scope, all-viewport rule | "mobile still has 20px gap" |
| 6 | #26 | shrink anchor box on mobile | `display: block !important; width: auto !important` on anchor | **"all viewports — drop the # glyph entirely"** |
| 7 | #27 | hide heading # glyph entirely on every viewport | `display: none !important` on `.header-anchor` and all 6 `h*:hover .header-anchor` variants | shipped |

After round 7, the end-state equals round 1 (PR #19) plus the gutter
collapse from round 2 (PR #20). **Rounds 3–6 were pure waste.**

## What was changing each round

The diagnostic metric kept changing:

| PR | Round's complaint | Probe data at end of round |
|---|---|---|
| #19 | "# is visible on hover" | `display: none` → `#` invisible |
| #20 | "left is blank" | `<main>` padding 28px → 0px |
| #21 | "I want # back" | hover `opacity: 1` |
| #22 | "# reserves 12px space" | `position: absolute` lifts anchor |
| #23 | "gap is 8px, want 0.2em" | `padding-right: 0.2em` |
| #24 | "1px gap left, want 0" | `transform: translateX(-100%)` |
| #25 | "doesn't work on mobile" | remove `@media` |
| #26 | "20px gap on mobile h1" | `display: block; width: auto` |
| **#27** | **"just drop the #"** | **`display: none` everywhere** |

The metric kept migrating: "too far" → "too close" → "wrong on mobile"
→ "still wrong" → "drop it." Each round's fix targeted the previous
round's complaint, never the underlying question of whether the element
should exist.

## Why this was an iterate-vs-drop scenario

The anchor glyph was **framework-default decorative content** —
`euv-ui`'s `euv_markdown` wraps every heading in
`<a class="header-anchor"><span>#</span></a>`. The user (this docs
site, `euv-dev/euv-docs`) never asked for the `#` glyph; it was
inherited from upstream.

That makes the `#` a **decorative carry-over**, not a feature request.
The user's repeated "X is too far / X should align / X doesn't fit"
feedback is the body-language of someone who's not sure they want the
glyph but hasn't yet articulated "just drop it." Continuing to perfect
placement is solving the wrong problem.

## Where the binary clarification should have happened

After PR #22 (round 3 first half) or at latest after PR #24 (round 4),
before opening the next iteration PR, the agent should have asked:

> "We've done 4 PRs on the # glyph. Two options at this point:
> (a) keep tuning placement until it's perfect on mobile + desktop,
> or (b) drop the glyph entirely via `display: none` and collapse
> the gutter it occupied. Which way?"

A reasonable user answer at PR #24's stage would still have been (a),
but the agent would have surfaced the binary early. By PR #26, after
4 more rounds of work, the answer flipped to (b) — and the entire
chain of micro-tunings was discardable.

## The signals to look for (re-stated for grep-ability)

```
SIGMAL_ITERATE_VS_DROP = (
    # ≥3 commits on the same selector in <7 days
    # AND user gave ≥2 distinct visual feedbacks on the same element
    # AND feedback metric changes each round ("8px" → "1px" → "20px")
    # AND element is inherited from framework, not user-requested
)
```

When this fires, ask the binary clarification. Don't ship another
micro-tuning PR without it.

## What the final drop looked like

```rust
Css::inject_css(
    ".md-body h1, .md-body h2, .md-body h3, .md-body h4, .md-body h5, .md-body h6 { padding-left: 0 !important; } \
     .md-body .header-anchor, \
     .md-body h1:hover .header-anchor, \
     .md-body h2:hover .header-anchor, \
     .md-body h3:hover .header-anchor, \
     .md-body h4:hover .header-anchor, \
     .md-body h5:hover .header-anchor, \
     .md-body h6:hover .header-anchor { display: none !important; }",
);
```

Three lines of effective CSS (the rest is selector plumbing). The
`:hover` variants are needed because upstream has separate
`.md-body h*:hover .header-anchor { opacity: 1 }` rules that
re-assert visibility under `:hover` — without our override those
would re-show the `#` on hover.

The anchor element itself stays in the DOM (euv-ui emits it as part of
every heading), so URL hash fragments still resolve for deep linking.
Only the glyph is hidden.

## Lesson (extracted to SKILL.md §8)

1. **3+ PRs on the same selector is a smell**, not a feature.
2. **Changing metric each round means you're chasing noise.**
3. **Inherited/framework-default decorative elements are candidates for drop**, not for perfect placement.
4. **Propose the binary after round 2.** Both outcomes are
   legitimate; the wrong choice is to keep tuning without asking.
5. **The final state often equals an early state plus accumulated
   lesson.** Here, PR #27's end-state is PR #19's end-state plus
   the gutter collapse from PR #20 — 5 PRs of placement work
   discarded.
