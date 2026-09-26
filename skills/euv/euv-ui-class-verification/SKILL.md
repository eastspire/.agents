---
name: euv-ui-class-verification
description: 'Edit verification for euv-ui class! design tokens.'
version: 1
author: eastspire
license: MIT
metadata:
  hermes:
    tags:
      - euv
      - ui
      - css
      - wasm
      - verification
    related_skills:
      - euv
      - euv-ui-standards
      - euv-standards
      - rust-pr-validation-checklist
      - mobile-web-debugging
---

# euv-ui `class!` block end-to-end verification

> A `class!` block compiles into a Rust `pub fn c_xxx() -> Css` but **does not type-check what the rendered CSS looks like**. Every style change can fail in the browser even when `cargo check` / `euv fmt` / `wasm-pack build` all succeed. This skill is the verification ladder that catches those failures.

## When to Use

Use this skill whenever you:

- Edit any `pub c_xxx { ... }` block in `ui/src/style/class/fn.rs` (the class registry;grep -cE "^\s+pub c_" 实地查看当前 count)。
- Edit any `pub c_xxx(bg, fg)` parameterized class in the same file.
- Edit `ui/src/style/var/fn.rs` (the `c_theme_light` / `c_theme_dark` token sets).
- Edit a local `example/src/style/class/fn.rs` page-scoped class block.
- Edit `docs-pages/src/style/**` or any project that ships an euv wasm bundle.
- Debug a user-reported "tag wraps wrong / border missing / dark mode broken" — verify by going through this ladder, not by re-reading the source.

Do not load for pure Rust logic, `html!` macro usage, `Signal` reactivity, euv-engine, hyperlane, or backend code — those have their own skills.

- You edited any `pub c_xxx { ... }` block in `ui/src/style/class/fn.rs` (the class registry;`wc -l` and `grep -cE "^\s+pub c_"` 看实际行数 / class 数)。
- You edited any `pub c_xxx(bg, fg)` parameterized class in the same file.
- You edited `ui/src/style/var/fn.rs` (the `c_theme_light` / `c_theme_dark` token sets).
- You edited a local `example/src/style/class/fn.rs` page-scoped class block.
- You edited `docs-pages/src/style/**` or any project that ships an euv wasm bundle.
- A user reported "tag wraps wrong / border missing / dark mode broken" — verify by going through this ladder, not by re-reading the source.

**Do not** load for: pure Rust logic, `html!` macro usage, `Signal` reactivity, euv-engine, hyperlane, backend code. Those have their own skills.

## Source-of-truth files (read first)

| File | Why it matters |
| --- | --- |
| `ui/src/style/class/fn.rs` | global `pub c_xxx { ... }` blocks, all in one file. Count by `grep -cE "^\s+pub c_" ui/src/style/class/fn.rs`. Every `display:` / `border:` / `padding:` / `var!(...)` lives here. |
| `ui/src/style/var/fn.rs` | 2 vars! blocks: `c_theme_light` / `c_theme_dark`. Token names are referenced via `var!(name)` → `var(--name)`. |
| `ui/src/component/<name>/view/fn.rs` | Each `euv_*` component's html! body — confirms which class the component actually applies (some components mix 2-3 classes). |
| `example/src/page/<name>/view/fn.rs` | The demo page that renders the component. Default: 30/32 pages render once on `/<page>` route. |
| `example/www/index.html` | Must reference `./pkg/euv_example.js` (not `./pkg/euv.js` — that name is a stale artifact; see pitfall §5.7). |

## The 5-step ladder (do them in order, do not skip)

### 1. Macro-aware format check

```bash
cd /root/github/euv-dev/euv
euv fmt
```

`euv fmt` expands the `class!` / `vars!` / `html!` macros before formatting, so it catches:

- `key: value;` semicolons missing inside macro blocks
- Mixed `padding: "8 12"` (no unit) vs `padding: "8px 12px"` (correct)
- Nested selector blocks indented wrong

Report is `Formatted N file(s), M unchanged.` — `N > 0` means it actually edited your file. `N = 0` is the happy path. Do **not** run `cargo fmt` on the whole workspace — it will touch unrelated files and dirty the PR diff.

### 2. Compile check — wasm target only

```bash
cd /root/github/euv-dev/euv
cargo check -p euv-ui --target wasm32-unknown-unknown
cargo check -p euv-example --target wasm32-unknown-unknown
```

`cargo check` on the host target (`cargo check` without `--target wasm32-unknown-unknown`) **will not exercise** `euv-ui`'s macro proc-macro paths the same way as the wasm32 build, and several css! block syntax errors only surface in the wasm target. Run both. Skip CLI / engine crates — they don't touch the style registry.

If you only edited a page's local class (`example/src/style/class/fn.rs`), the second command alone is enough; the first still doesn't hurt.

### 3. Build wasm bundle — output is `euv_example.js`, not `euv.js`

```bash
cd /root/github/euv-dev/euv/example
wasm-pack build --target web --out-dir www/pkg --release
```

Pitfall: `wasm-pack build --out-name euv` produces `./pkg/euv.js` and `./pkg/euv_bg.wasm`. **`example/www/index.html` references `./pkg/euv.js`** but the current wasm-pack output naming convention for `--target web` is `<crate-name>.js` → `euv_example.js`. The mismatch is a latent bug in upstream `example/www/index.html` (the `www/` dir is excluded from git, so it never gets auto-fixed). Fix the import path manually after each build, or rely on `euv run` (which knows the right name) instead of `wasm-pack` directly.

Verify the new class actually made it into the bundle:

```bash
strings www/pkg/euv_example_bg.wasm | grep -o "c_euv_tag_solid_black[^c]*" | head -1 | cut -c1-200
```

You should see the class name followed by the actual CSS body (`line-height: 1; var(--space-xs)` etc.). If the only match is empty, the macro didn't pick up your edit and the browser will render the old CSS.

### 4. Serve + Playwright DOM probe — the real test

The Rust checks above prove the class is **in the wasm**. They don't prove the CSS is **right** in the browser.

```bash
cd /root/github/euv-dev/euv/example/www
python3 -m http.server 8765 &
```

Then with Playwright (chromium / chrome — see `euv-standards` §0 for the local chromium path `/root/LTPP-MINIMAX/chrome-linux/chrome`):

```python
import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(
            executable_path='/root/LTPP-MINIMAX/chrome-linux/chrome',
            args=['--no-sandbox'],
        )
        c = await b.new_context(viewport={'width': 1280, 'height': 900},
                                device_scale_factor=2)
        pg = await c.new_page()
        msgs = []
        pg.on('console', lambda m: msgs.append(f'[{m.type}] {m.text[:200]}'))
        pg.on('pageerror', lambda e: msgs.append(f'[pageerror] {e}'))
        await pg.goto('http://localhost:8765/#/<page>', wait_until='networkidle',
                      timeout=60_000)
        await pg.wait_for_timeout(3000)  # let App::mount finish

        # 4a. Verify the rule body (proves the class! macro picked up your edit)
        info = await pg.evaluate("""() => {
          const t = document.querySelector('[class*="c_euv_<name>"]');
          const matching = [];
          for (const sheet of document.styleSheets) {
            try {
              for (const rule of sheet.cssRules || []) {
                if (rule.cssText && rule.cssText.includes(t.className.split(' ')[0])) {
                  matching.push(rule.cssText.slice(0, 600));
                }
              }
            } catch(e) {}
          }
          return {cls: t.className, computedDisplay: getComputedStyle(t).display, rules: matching.slice(0,1)};
        }""")
        print(info)

        # 4b. Visual snapshot at 2x device pixel ratio
        await pg.screenshot(path='/tmp/<page>.png', full_page=True)

        # 4c. Inject a multi-line regression — force text wrap to verify the fix
        # for tag/badge/button-like atoms with borders.
        await pg.evaluate("""() => {
          const t = document.querySelector('[class*="c_euv_<name>"]');
          t.textContent = 'A reasonably long label that should wrap to two lines';
          const card = t.closest('.c_card');
          if (card) card.style.maxWidth = '280px';
        }""")
        await pg.wait_for_timeout(300)
        await pg.screenshot(path='/tmp/<page>-wrapped.png', full_page=True)

        await b.close()
```

**Why the wrap-injection step matters**: an inline-flex element with `border` 4 sides can look correct in single-line screenshots while failing visibly only when the text wraps — the box stretches to parent width, `justify-content: center` only centers the first line, and wrapped lines left-align with the box's first-line right edge far to their right. This is the **most common class! bug shape**, and only a multi-line screenshot reveals it.

### 5. Diff the screenshot — visual ground truth

Use `vision_analyze` on the screenshots. Ask specifically about each side (top / right / bottom / left) and the multi-line case. A black-background + black-border solid tag (`c_euv_tag_solid_black` in light theme) is the **worst case to visually verify** — `border` and `background` are both `var!(accent)`, so the border is invisible against the background and only the computed `document.styleSheets` text in §4a proves the rule exists. Always do §4a first; never trust a screenshot of a same-color border + fill.

## Pitfalls specific to euv-ui class! blocks

### 5.1 `inline-flex` + multi-line text + `justify-content: center`

`inline-flex` is an atomic inline-level box — its internal text wraps but the box itself does not re-center each line. `justify-content: center` only affects the **first** line; wrapped lines left-align to the box left edge and the box's right border falls far to the right of the trailing text, **looking exactly like "right border missing on wrapped lines"**.

Fix: switch to `display: inline-block` + `vertical-align: middle` + `text-align: center` + `line-height: 1` + `box-sizing: border-box`. This produces a box whose width covers all wrapped lines and whose border always encloses them.

This was the root cause of euv PR #68 (euv_tag border missing on wrapped lines). See `references/euv-tag-wrap-recipe.md` for the full before/after diff.

**Scope limit — this recipe only applies to badge/tag-style elements** (multi-line wrap with `text-align: center` for visual centering). For **inline `<code>` in running prose** (paragraphs, list items, table cells), use `vertical-align: baseline` + `line-height: 1` instead — see §5.9 for the full reasoning. Mixing the two recipes causes baseline drift.

### 5.2 `box-decoration-break: clone` does **not** help inline-flex

It only matters for inline (non-atomic) boxes — `inline-flex` is atomic, so the property is a no-op. Don't waste time on it.

### 5.3 `border` shorthand vs per-side on inline atoms

Same problem shape as 5.1. Inline-level boxes draw 4 sides from the box geometry, but box width is dominated by the first line when the box is `inline-flex`. Per-side declarations (`border-top:` / `border-right:` etc.) don't fix this either — same box model. Always switch `display` first.

### 5.4 dark theme override

`vars!` produces two blocks: `c_theme_light` + `c_theme_dark`. If you add a new token in `c_theme_light`, you **must** also add it to `c_theme_dark` with the inverted value — `#[derive(Debug)]` will not catch this, the browser will fall back to `initial`. Test in both themes by toggling with the theme button on the example navbar.

### 5.5 `var!(token)` typo → silent CSS invalid

If you write `var!(accentt)` instead of `var!(accent)`, the macro expands to `var(--accentt)` which the browser parses as an unknown property and silently falls back. No compile error, no runtime warning. After every edit:

```bash
strings www/pkg/euv_example_bg.wasm | grep -oE "var\(--[a-z-]+\)" | sort -u
```

Cross-reference against the names in `ui/src/style/var/fn.rs`. Same for `c_xxx()` typos — the macro generates the function but the resulting CSS rule uses the literal class name string.

### 5.6 `class!` block inheritance — call form, not `extends`

A child block reuses a parent via `c_parent();` inside the child body, not via a keyword. Same-name properties follow CSS cascade (last wins). Verified by inspection of `ui/src/style/class/fn.rs` and noted in `euv-standards` §5.

### 5.7 `Cargo.toml` exclude = `www` = index.html drift

`example/Cargo.toml` has `exclude = [..., "www", ...]`. Changes to `example/www/index.html` (e.g. the `euv.js` → `euv_example.js` import path) never go through git, so they never get CI'd, so they never get fixed at the source. This is a known latent bug; until it's fixed upstream, fix it locally after every build.

### 5.8 `euv fmt` ≠ `cargo fmt`

Always `euv fmt`. `cargo fmt` skips inside macro bodies and leaves misaligned `key: value;` lines. `euv fmt` is macro-aware (it preprocesses class!/html!/vars! before formatting).

### 5.9 inline `<code>` / inline-atom baseline alignment — `vertical-align: middle` ≠ `baseline`

The PR #68 fix recommended `vertical-align: middle` for `inline-block` atoms. That works for **multi-line tag-style elements** (`euv_tag`) where `text-align: center` handles the horizontal axis. But for **inline `<code>` in running prose** (paragraphs, list items, table cells), `vertical-align: middle` is the wrong choice:

- `vertical-align: middle` aligns the **x-height center** of the box to the line's x-height center — visually OK for short code, but for **multi-line wrapped code** the box top/bottom can drift across fragments.
- `vertical-align: baseline` aligns the box's last-line baseline to the line's baseline — **rock-steady** for any code length, any wrap state.

The second revision of `.md-body code` (PR #77, euv 0.18.23) corrected this:

```css
/* WRONG — vertical-align: text-top + line-height: 1.4 (PR #72)
   - box top aligns to line top, but box bottom descends 8-10px below
     baseline due to 1.4 line-height on 14px font (box h = 25.78px).
   - Looks like code "floats on the next line" relative to surrounding text. */
display: inline-block; vertical-align: text-top; line-height: 1.4;

/* RIGHT — vertical-align: baseline + line-height: 1 (PR #77) */
display: inline-block; vertical-align: baseline; line-height: 1;
```

**When to use which**:

| Element shape | vertical-align | line-height | Why |
|--------------|----------------|-------------|-----|
| euv_tag (badge-style, can wrap multiple lines) | `middle` | `1` | `text-align: center` handles horizontal; `middle` lets the box float above the text slightly — that's fine because tag is "decorative" |
| inline `<code>` (句中高亮, can wrap) | `baseline` | `1` | Must align with surrounding prose baseline exactly — any drift is very noticeable |
| inline `<kbd>` / `<span>` with border | `baseline` | `1` | Same as code — inline highlight |

**Diagnostic**: device_scale_factor=4 screenshot + overlay a horizontal red line at the surrounding text's baseline position. If the code box's baseline (text inside the box) sits below the red line, vertical-align is wrong.

**Playwright baseline overlay technique** (reusable):

```js
// Calculate baseline position empirically
const baseline_y = target.getBoundingClientRect().top + 22;  // 22 ≈ ascent for 16px font
const line = document.createElement('div');
line.style.cssText = `position:absolute; left:0; top:${baseline_y}px; width:100%; height:2px; background:red;`;
document.body.appendChild(line);
```

## Reference: what this ladder catches that pure cargo doesn't

| Failure | Caught by | Notes |
| --- | --- | --- |
| Missing `;` inside class! block | `euv fmt` | macro-aware |
| `inline-flex` multi-line wrap losing right border | step 4 multi-line screenshot | only visible with wrap-injection |
| dark-theme token missing | step 4 dark-theme toggle | needs two screenshots |
| `var!(typo)` silent fallback | `strings \| grep` token audit | no error anywhere else |
| `euv.js` vs `euv_example.js` import mismatch | step 3 build output inspection | www/ is git-excluded |
| `display:` field silently dropped by macro | step 4a `document.styleSheets` rule read | inspect the actual `rule.cssText` |

## Quick checklist (one screen)

```
[ ] euv fmt                                           # macro-aware format
[ ] cargo check -p euv-ui    --target wasm32-unknown-unknown
[ ] cargo check -p euv-example --target wasm32-unknown-unknown
[ ] wasm-pack build --target web --out-dir www/pkg --release
[ ] strings www/pkg/euv_example_bg.wasm | grep <new class>  # in bundle
[ ] python3 -m http.server 8765 &                       # serve www/
[ ] Playwright open http://localhost:8765/#/<page>
[ ] read document.styleSheets — confirm new rule body matches edit
[ ] single-line screenshot
[ ] multi-line wrap-injection screenshot               # most common bug shape
[ ] dark-theme screenshot (toggle nav theme button)
[ ] kill http.server, commit, push, gh pr create
```

## Iterative design-token tuning — multi-round alpha/colour pick workflow

User-driven feedback loops on a single design token (typically `bg-overlay`,
`accent`, or `bg-overlay`-like) can iterate 3+ times in one session:
"too prominent" → "softer" → "still too white on dark" → final. Each round is
its own PR + version bump + publish + redeploy. Don't try to batch them.

### Round structure (per iteration)

1. Edit `ui/src/style/var/fn.rs` (or `class/fn.rs`) — one token, both themes.
2. `euv fmt` + `cargo check -p euv-ui --target wasm32-unknown-unknown`.
3. `cd example && euv build` (NOT `wasm-pack` directly — see §5.7).
4. **Cache-bust** when verifying locally (mandatory — see below).
5. Verify BOTH themes via Playwright + computed-style probe + screenshot.
6. Visual diff via `vision_analyze`; check perceptual weight symmetry
   (light scrim RGB distance to white ≈ dark scrim RGB distance to black).
7. Commit + push + `gh pr create --repo euv-dev/euv` → merge → bump patch
   version (`X.Y.Z` → `X.Y.(Z+1)` for cosmetic tuning, NOT `X.(Y+1).0`).
9. Wait for `Rust workflow` to land `publish` job → confirm on crates.io API.
10. Trigger `euv-example` rebuild + upload to ltpp.vip via
    `hyperlane-upload` skill (the wasm-URL rewrite two-pass pattern).
11. Optionally wait for `Deploy Pages` to auto-deploy to
    https://euv-dev.github.io/euv/.

**Two PRs per round**:
- `fix(ui): <description>` — actual code change (small, often 1 line)
- `chore(release): bump all crates to X.Y.Z` — 7-file Cargo.toml sed

Both squash-merged, both with `--delete-branch`.

### Playwright cache-bust (mandatory after rebuild)

Even after `cp -f www/pkg/*.wasm www/pkg/*.js /tmp/euv-srv/pkg/`, Playwright
**frequently reports stale values** because the wasm is keyed by URL not by
file mtime. Three fixes, all required together:

```python
async with async_playwright() as p:
    b = await p.chromium.launch(
        executable_path='/root/LTPP-MINIMAX/chrome-linux/chrome',
        args=['--no-sandbox', '--disable-dev-shm-usage', '--disable-cache'],
    )
    c = await b.new_context(viewport={'width': 1280, 'height': 900},
                            color_scheme='dark', bypass_csp=True)
    pg = await c.new_page()
    # Cache-bust the HTML itself
    await pg.goto('http://localhost:8765/?bust=<TOKEN>#/<page>',
                  wait_until='networkidle', timeout=60000)
```

If you don't, you'll spend 10 minutes "verifying" the OLD values were
still there — a silent regression test that wastes an iteration. Token
matters: `?bust=dark`, `?bust=light`, `?bust=0.20` all work; pick a
unique one per round so you don't accidentally re-test a cached page.

### Verified token → RGB table (overlay scrim case study)

Each row was an actual PR + euv release. Use this as a starting point when
deciding what alpha value to try first, not as ground truth:

| euv version | Light `bg-overlay` | Light resolved on `#fff` | Dark `bg-overlay` | Dark resolved on `#000` | User feedback |
|---|---|---|---|---|---|
| 0.18.27 | rgba(0,0,0,0.45) | rgb(140,140,140) | rgba(0,0,0,0.60) | rgb(0,0,0) [invisible] | "dark overlay invisible" |
| 0.18.28 | rgba(0,0,0,0.45) | rgb(140,140,140) | rgba(255,255,255,0.15) | rgb(38,38,38) | "good but asymmetric" |
| 0.18.29 | rgba(0,0,0,0.45) | rgb(140,140,140) | rgba(255,255,255,0.45) | rgb(115,115,115) | "consistent but heavy" |
| 0.18.30 | rgba(0,0,0,0.20) | rgb(204,204,204) | rgba(255,255,255,0.20) | rgb(51,51,51) | "softer but dark too bright" |
| **0.18.31** | rgba(0,0,0,0.20) | rgb(204,204,204) | rgba(255,255,255,0.10) | rgb(26,26,26) | accepted |

**Recipe for any overlay / scrim token**: start at 0.45 (heavy but visible),
then drop 0.05–0.10 per iteration. Convergence is usually 2–4 rounds.
**Anti-recipe**: don't try 0.15, 0.20, 0.25 in one PR — pick one, ship, get
feedback, iterate.

### Workspace version bump — when CI's `sync_workspace_version` exists

euv's `rust.yml` has a `sync_workspace_version` job that pushes a follow-up
commit bumping sub-crates to match root. So the rule (from
`rust-pr-validation-checklist` §10) — "only touch root `[package] version`,
let CI sync the rest" — **is correct for euv as long as the bump commit is
the merge commit on master**.

In practice the workflow I verified this session was:
1. Manually `sed -i 's/version = "0.18.27"/version = "0.18.28"/g'` over
   all 7 Cargo.toml files (root + 6 sub-crates). This is bounded to
   specific files, NOT a global sed across the repo, so it cannot
   accidentally hit third-party deps (e.g. `qrcode`).
2. Single commit `chore(release): bump all crates to X.Y.Z` (7 files,
   14 +/-).
3. Merge → CI sync job sees workspace is already consistent
   (`git diff --cached --quiet` exits 0 in the runner) → no follow-up commit.

**This is fine and not redundant.** If you only bumped root, sync would
push the diff and you'd have one extra commit on master — visually
equivalent but log-noisier. Either approach works; just don't mix them.

**Pitfall to AVOID**: `sed -i 's/version = "OLD"/version = "NEW"/g' **/*.toml`
globally. This will match any third-party `version = "OLD"` line in any
Cargo.toml in the workspace (including ones published at the same number by
coincidence). Always scope to explicit file paths.

### Pages workflow cancellation — `concurrency.cancel-in-progress`

`euv-dev/euv/.github/workflows/pages.yml` declares:

```yaml
concurrency:
  group: pages
  cancel-in-progress: true
```

If two PRs merge into master within a few minutes (typical when a fix PR
+ a chore release PR land back-to-back), the **earlier** `Deploy Pages`
workflow run gets cancelled mid-`cargo run -p euv-cli -- build` (looks
like "the operation was canceled" in the runner log). The system
auto-triggers a retry via `workflow_run` for the **second** event, which
usually succeeds. Symptom in `gh run list`:

```json
{"conclusion":"cancelled", "name":"Deploy Pages", "headSha":"<earlier merge>"}
{"conclusion":"success",    "name":"Deploy Pages", "headSha":"<later merge>"}
```

**Don't panic** — wait ~2 minutes for the auto-retry, then verify Pages
deployed the later commit. If the retry also cancels, manually re-run via
`gh workflow run pages.yml --repo euv-dev/euv`.

If you want a deterministic deploy regardless of timing, set
`cancel-in-progress: false` in the workflow file — but then back-to-back
merges queue up instead of cancelling, and you wait longer for the final
state. Trade-off; default (`true`) is the right choice for cosmetic
iterations.

## Related skills

- `euv-ui-standards` — full class catalogue + design tokens(`grep -cE "^\s+pub c_" ui/src/style/class/fn.rs` 看当前 count;load for naming)
- `euv-standards` — macro syntax + 28 euv-ui components (load for component API)
- `rust-pr-validation-checklist` — generic Rust PR checks (cargo build / test / fmt / clippy); does **not** cover the wasm-pack + Playwright steps here
- `mobile-web-debugging` — for runtime browser-layer CSS issues not caught by class! edits (env()/safe-area etc.)
- `inspecting-hermes-desktop-dom` — for desktop DOM inspection, not wasm pages

## Support files

- `references/euv-tag-wrap-recipe.md` — full before/after for PR #68, with computed-style diff and the inline-flex → inline-block rationale. Read before fixing any tag/badge/button border or wrap issue.