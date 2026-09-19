# euv_tag border missing on wrapped lines — full recipe (PR #68)

> Reference for euv-ui-class-verification §5.1. The exact `inline-flex` → `inline-block` swap applied to the four `c_euv_tag_*` variants on 2026-08-30. Use this as a template when fixing any tag/badge/button border + multi-line bug in `ui/src/style/class/fn.rs`.

## Symptom (user-reported)

User: "euv-docs 标签如果换行,会导致第一边右边框丢失,换行之后的左侧边框丢失."

What the user actually saw: the tag's right border appeared to "disappear" on lines after the first; left border looked fine (it's actually continuous, but the box geometry stretched to parent width, so visually the right edge sat far from the wrapped text — looking like a missing border).

## Reproduce with Playwright

Inject long text into a tag inside a narrow card:

```js
const t = document.querySelector('.c_euv_tag_solid_black');
t.textContent = 'Solid Black very long tag text that wraps here';
t.closest('.c_card').style.maxWidth = '280px';
```

Before fix: the second line "that wraps here" left-aligns to box left, box right border sits ~50px to the right of the trailing word. Before-fix rect (from `getBoundingClientRect` + `getClientRects` on the line):

```
box:    { w: 220, h: 58 }                                  // parent-width box
line 1: { l: 66,  r: 179,  w: 113 }
line 2: { l: 66,  r: 132,  w: 66   }                       // left-aligned, NOT centered
```

## Root cause

`display: inline-flex` makes the tag an atomic inline-level box. `justify-content: center` only centers the **first** line of wrapped text within the flex item — wrapped lines default to `align-self: auto` = `stretch` along the cross axis, but the main axis content is packed by `justify-content` only on the first line. The box itself stretches to parent width (because `inline-flex` defaults to `width: max-content` capped by parent), so its right border is far from the wrapped text on lines 2+.

`box-decoration-break: clone` does **not** help: it only affects `inline` (non-atomic) boxes, not `inline-flex` (atomic). Verified by setting it manually and reading `getComputedStyle(...).boxDecorationBreak` — value became `clone` but the layout was unchanged.

## Fix

Swap `display: inline-flex` → `display: inline-block` in all four `c_euv_tag_*` variants, and replace the flex centering with text-based centering:

```diff
 pub c_euv_tag_solid_black {
-    display: "inline-flex";
-    align-items: "center";
-    justify-content: "center";
+    display: "inline-block";
+    vertical-align: "middle";
+    text-align: "center";
+    line-height: "1";
     color: var!(text-on-accent);
     padding: format!("{} {}", var!(space-xs), var!(space-md));
     font-size: var!(font-sm);
     font-weight: "600";
     cursor: "pointer";
     background: var!(accent);
     border: format!("1px solid {}", var!(accent));
+    box-sizing: "border-box";
 }
```

Same diff for `c_euv_tag_solid_white`, `c_euv_tag_outline_black`, `c_euv_tag_outline_white`.

**Why each property matters**:

| Property | Purpose |
| --- | --- |
| `display: inline-block` | Atomic box, but its content layout is normal block-flow — wrapped lines fill the box width, then `text-align: center` centers each line inside the box. |
| `vertical-align: middle` | Matches the original `inline-flex` baseline alignment with surrounding text (otherwise tags sit at the bottom of the line). |
| `text-align: center` | Centers wrapped lines horizontally inside the box. The replacement for `justify-content: center` in a block-flow context. |
| `line-height: 1` | Collapses stray line-height so box height stays close to the original inline-flex height (~24-32px depending on font-size). Without it, line-height of surrounding `<p>` (1.5-1.6) inflates the tag height. |
| `box-sizing: border-box` | Includes padding + border in the box width; without it, padding+border add to width and the box can exceed parent. |

## After-fix rect (Playwright)

```
box:    { w: 280, h: 38 }                                  // fills the narrow card
line 1: { l: 377.3, r: 610.7, w: 233.4 }                  // centered, second line below
line 2: { l: 430.97, r: 557.0, w: 126.1 }                 // centered: 430.97 = 354 + (280-126.06)/2
```

4-side border encloses both wrapped lines; second line is horizontally centered inside the box.

## Why the user-facing PR fix is only the CSS diff

The `euv_tag` html! body in `ui/src/component/tag/view/fn.rs` is unchanged:

```rust
EuvTagVariant::Solid => match color {
    EuvTagColor::Black => html! {
        span { class: c_euv_tag_solid_black() onclick: on_click text }
    },
    // ...
},
```

No need to wrap with `display: contents` or extra `<div>` — `inline-block` on the existing `<span>` does everything. The fix is **purely in the CSS class registry**.

## Verification ladder (must do all 4)

1. `euv fmt` → 0 file changed (the macro blocks survive the formatter).
2. `cargo check -p euv-ui --target wasm32-unknown-unknown && cargo check -p euv-example --target wasm32-unknown-unknown` → exit 0.
3. `wasm-pack build --target web --out-dir www/pkg --release` → produces `euv_example_bg.wasm`. Verify:
   ```bash
   strings www/pkg/euv_example_bg.wasm | grep -o "c_euv_tag_solid_black[^c]*" | head -1
   # → c_euv_tag_solid_blackdisplay: inline-block; vertical-align: middle; text-align: center; ...
   ```
4. Playwright on `/badge` route: single-line tag still 69x24, multi-line tag centered, 4-side border complete (single-line screenshot + wrap-injection screenshot).

## Common follow-up: the `euv.js` vs `euv_example.js` import mismatch

`example/www/index.html` ships with `import init, { main } from './pkg/euv.js';` but `wasm-pack build` produces `euv_example.js`. Two solutions:

- Local: edit `example/www/index.html` after every build (the file is git-excluded via `Cargo.toml` `exclude = ["www"]`, so this drifts per developer).
- Better: use `euv run` instead of `wasm-pack` directly — `euv` knows the right import path.

## Don't do this for other components (without re-checking)

This fix is specifically for **atomic inline elements that wrap text and have a border**. Other `inline-flex` usages in `ui/src/style/class/fn.rs` are correct as-is:

- `c_euv_button_primary_md` / `outline_md` — button text doesn't wrap (`white-space: nowrap` set), so `inline-flex` + `justify-content: center` is fine.
- `c_loading_container` / `c_loading_text_col` — flex layout for spinner + text side-by-side, no wrap.
- `c_home_actions` — flex row of buttons, no wrap inside items.

Audit rule: **only swap `inline-flex` → `inline-block` when the box can wrap multiple text lines AND has a border around it**.

> ⚠️ **Don't apply the `vertical-align: middle` half of this recipe to inline `<code>`**. For inline `<code>` in running prose (paragraphs, list items), use `vertical-align: baseline` + `line-height: 1` instead — see `euv-ui-class-verification` §5.9 for the full reason. `middle` lets multi-line wrapped code drift vertically; `baseline` is rock-steady for any wrap state. The `.md-body code` rule uses the baseline variant (euv PR #77, 0.18.23+).

## PR

Title: `fix(ui): keep euv_tag border complete when text wraps to multiple lines`
PR: https://github.com/euv-dev/euv/pull/68
Branch: `eastspire:fix/euv-tag-wrapped-border` (fork + PR workflow per euv-dev standard).