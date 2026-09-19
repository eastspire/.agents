# euv-docs rendering fixes (build.rs + doc_page + image pipeline)

Concrete fixes applied against `euv-dev/euv-docs` for the docs-pages
rendering gaps the user surfaced in PR #238 / #239 cycle
(2026-09-19). Each fix is a complete cause-and-effect recipe: why
the upstream behaviour was wrong, what was changed, what the
verifiable outcome looks like.

Applies to euv-docs 0.25.x and euv-ui 0.25.x.

---

## 1. Image `src` rewrite — `/foo/bar.jpg` returns 0 bytes (root-cause + fix)

### Symptom

Markdown like `![](/essay/09-19/IMG_20250923_191003.jpg)` renders
into `<img src="/essay/09-19/IMG_20250923_191003.jpg">` and the
browser reports `naturalWidth: 0`. Probing the same URL with
`fetch()` returns `200 + content-type: text/html + length: 0` —
the SPA's nginx rule is serving the index shell, not the asset.

### Root cause

Two things conspire:

1. The deployed `index.html` ships `<base href="./">`. Browsers
   resolve relative URLs against the document's directory.
2. The ltpp.vip nginx rule serves the SPA's index shell for every
   short URL path (`/foo/`, `/foo/bar.jpg`). So `/essay/09-19/...`
   → SPA fallback, never the actual `www/essay/09-19/...` file
   that `copy_dir(docs/public -> www)` already wrote.

The image bytes are deployed correctly. The browser just never
asks for them at a URL the SPA can see.

### Fix

In `build.rs`, the `Tag::Image` handler must rewrite site-root-
absolute `src` to a URL that resolves against `<base href="./">`:

```rust
Event::Start(Tag::Image { dest_url, .. }) => {
    let alt_inlines: Vec<Inline> = parse_inlines(it, ctx, true);
    inlines.push(Inline::Image {
        src: rewrite_image_src(&dest_url, ctx.route),
        alt: inline_plain_text(&alt_inlines),
    });
}

fn rewrite_image_src(dest: &str, _route: &str) -> String {
    if dest.starts_with("http://")
        || dest.starts_with("https://")
        || dest.starts_with("data:")
        || dest.starts_with("blob:")
    {
        return dest.to_string();
    }
    let trimmed: &str = dest.trim_start_matches('/');
    if trimmed.is_empty() {
        return dest.to_string();
    }
    if dest.starts_with('/') {
        return format!("./{trimmed}");
    }
    dest.to_string()
}
```

The leading `/` becomes `./`; the browser resolves `./essay/...`
against `<base href="./">` → the page's directory → the actual
file in `www/essay/...`. External URLs and `data:` blobs are
untouched.

### Verification

Playwright after the build lands:

```js
[...document.querySelectorAll('img')].map(i => ({
    src: i.src,                    // http://127.0.0.1:5188/essay/.../IMG_xxx.jpg
    naturalWidth: i.naturalWidth,  // > 0
    rendered: i.getBoundingClientRect().height,  // > 0
}))
```

All images should report `naturalWidth > 0`. A remaining 0 means
either the asset isn't in `www/` (fix #2 below) or the nginx
rule has changed.

---

## 2. Inline asset copying — keep images next to `.md`

### Symptom

Authors keep image assets next to their content (`essay/posts/2025/
09-19/IMG_xxx.jpg`). The existing build only copies `docs/public/`
into `www/`; everything else is dropped on the floor. Even if
fix #1 above resolves the URL correctly, the bytes still aren't
deployed.

### Root cause

`build.rs::main()` walks `docs/`, runs `collect_md()` (only
matches `.md` extension), then calls `copy_dir(docs/public,
www)`. There's no pass that picks up non-md files sitting next
to a `.md` file. Authors must choose between putting assets in
`docs/public/` (URL prefix becomes `/public/...` not `/essay/...`)
or losing them entirely.

### Fix

Add a second pass after the public-dir copy:

```rust
copy_doc_assets(&docs_dir, &www_dir);
```

```rust
fn copy_doc_assets(docs_dir: &Path, www_dir: &Path) {
    copy_doc_assets_recurse(docs_dir, docs_dir, www_dir);
}

fn copy_doc_assets_recurse(root: &Path, dir: &Path, www_dir: &Path) {
    let Ok(entries) = fs::read_dir(dir) else { return; };
    for entry in entries.flatten() {
        let path: PathBuf = entry.path();
        if path.is_dir() {
            // docs/public/ already handled by copy_dir(docs/public, www)
            if path.file_name().is_some_and(|n| n == "public") {
                continue;
            }
            copy_doc_assets_recurse(root, &path, www_dir);
        } else if path.extension().is_some_and(|e| e != "md") {
            let Ok(rel) = path.strip_prefix(root) else { continue; };
            let target: PathBuf = www_dir.join(rel);
            if let Some(parent) = target.parent() {
                let _ = fs::create_dir_all(parent);
            }
            let _ = fs::copy(&path, &target);
        }
    }
}
```

Skip `public/` so the existing `copy_dir(docs/public, www)` pass
isn't double-walked.

### Verification

```bash
ls www/essay/posts/2025/09-19/  # IMG_xxx.jpg present
# or after live deploy:
curl -sI https://ltpp.vip/github/pages/docs-pages/pages/essay/posts/2025/09-19/IMG_xxx.jpg
# → 200, content-type: image/jpeg, content-length: <bytes>
```

---

## 3. GitHub-style alert blockquotes (`> [!TIP]` etc.)

### Symptom

`> [!TIP]\n> body` renders as a plain `<blockquote>` with literal
`[!TIP]` text inside it. The user wants it to render as a styled
box with a title bar.

### Existing parser

`build.rs::split_containers()` already recognises `:::` kind
custom containers. The markdown parser just needs to rewrite the
GitHub-style `[!kind]` form into the `::: kind` form before the
container splitter runs.

### Fix

```rust
const GITHUB_ALERT_KINDS: &[&str] = &[
    "tip", "note", "warning", "danger", "important", "caution",
];

fn render_markdown(body: &str, route: &str) -> (Vec<Block>, Vec<Heading>, Option<String>) {
    let segments: Vec<Segment> = split_containers(&transform_github_alerts(body));
    // ... rest unchanged
}

fn transform_github_alerts(body: &str) -> String {
    let mut out: String = String::with_capacity(body.len());
    let lines: Vec<&str> = body.lines().collect();
    let mut idx: usize = 0;
    while idx < lines.len() {
        let line: &str = lines[idx];
        let stripped: &str = line.trim_start().strip_prefix('>').unwrap_or("");
        if !line.trim_start().starts_with('>')
            || !stripped.trim_start().starts_with("[!")
        {
            out.push_str(line);
            out.push('\n');
            idx += 1;
            continue;
        }
        let after_marker: &str =
            stripped.trim_start().trim_start_matches("[!");
        let close: Option<usize> = after_marker.find(']');
        let Some(close) = close else {
            out.push_str(line);
            out.push('\n');
            idx += 1;
            continue;
        };
        let kind_candidate: String =
            after_marker[..close].trim().to_ascii_lowercase();
        if !GITHUB_ALERT_KINDS.contains(&kind_candidate.as_str()) {
            out.push_str(line);
            out.push('\n');
            idx += 1;
            continue;
        }
        // Optional second line is treated as the title (when it
        // doesn't itself start with "[!" and isn't empty).
        let title_line: Option<String> = (idx + 1 < lines.len())
            .then(|| {
                lines[idx + 1]
                    .trim_start()
                    .strip_prefix('>')
                    .unwrap_or("")
                    .trim()
            })
            .filter(|s: &&str| !s.is_empty() && !s.starts_with("[!"))
            .map(str::to_string);
        out.push_str(&format!("::: {kind_candidate}"));
        if let Some(title) = &title_line {
            out.push(' ');
            out.push_str(title);
        }
        out.push('\n');
        let mut body_idx: usize = idx + 1;
        if title_line.is_some() {
            body_idx += 1;
        }
        while body_idx < lines.len() {
            let next: &str = lines[body_idx];
            if let Some(rest) = next.trim_start().strip_prefix('>') {
                out.push_str(rest.trim_start());
                out.push('\n');
                body_idx += 1;
            } else {
                break;
            }
        }
        out.push_str(":::\n");
        idx = body_idx;
    }
    out
}
```

The styling lives in the site-local `Css::inject_css` block in
`src/lib.rs`:

```css
.docs-container-tip, .docs-container-note,
.docs-container-important, .docs-container-info {
    border: 1px dashed var(--foreground, #000);
    border-left-width: 4px;
    padding: 0.75rem 1rem;
    margin: 1rem 0;
    background: var(--accent-muted, rgba(0,0,0,0.04));
}
.docs-container-warning, .docs-container-caution {
    border: 1px solid var(--foreground, #000);
    border-left-width: 4px;
    /* ... */
}
.docs-container-danger {
    border: 1px solid var(--foreground, #000);
    border-left-width: 4px;
    background: rgba(0,0,0,0.06);
}
.docs-container-title {
    font-weight: 600;
    margin: 0 0 0.25rem 0;
    font-size: 0.875rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}
.docs-container-title:empty { display: none; }
```

### Verification

```js
const tips = [...document.querySelectorAll('[class*="docs-container"]')];
// → 2+ entries with cls like "docs-container tip"
const titles = [...document.querySelectorAll('.docs-container-title')];
// → 2+ entries, text = "TIP" / "WARNING" / etc.
const cs = getComputedStyle(tips[0]);
// borderLeftWidth: "4px"
// backgroundColor: not transparent
```

---

## 4. Page title rendering — content pages need a visible h1

### Symptom

`euv_doc_layout` does not render a page title. Content pages
have no h1; the first body h2 sits at y=400+ after the markdown
preamble. The user wants the page title to appear at the top,
aligned with the home hero title (y=76).

### Fix

In `src/component/doc_page/view/fn.rs::docs_doc_page`, emit an
h1 before `euv_markdown`:

```rust
html! {
    euv_doc_layout {
        toc_title: locale.toc_label
        toc_items: page.headings
        prev_label: locale.prev_label
        next_label: locale.next_label
        prev: prev
        next: next
        footer: footer_text
        if { !page.title.is_empty() } {
            h1 {
                class: "c_docs_page_title"
                {
                    page.title
                }
            }
        }
        euv_markdown {
            blocks: page.blocks
        }
    }
}
```

Style in `src/lib.rs` site-local CSS (raw string; do NOT use the
`var!()` proc macro inside `Css::inject_css` strings — it's only
valid in `class!` blocks):

```css
.c_docs_page_title {
    font-size: 2.25rem;          /* was var!(font-4xl) = "2.25rem" */
    font-weight: 800;
    letter-spacing: -0.02em;
    margin: 0 0 1rem 0;
    padding-top: 0;
    color: var(--foreground, #000);
}
```

### Verification

```js
const dt = document.querySelector('.c_docs_page_title');
const ht = document.querySelector('.c_home_title');
Math.abs(dt.getBoundingClientRect().top - ht.getBoundingClientRect().top) < 5;
// → true (both at y=76)
```

---

## 5. Pitfall — `var!()` / `class!` macros do NOT work in raw CSS strings

`Css::inject_css` takes a `&'static str` literal. The `var!(token)`
and `class!` proc macros only expand inside Rust source the
framework controls (the `class!` block in `ui/src/style/class/fn.rs`).
Inlining `var!(font-4xl)` inside a `Css::inject_css("...")` raw
string compiles but the runtime CSS still contains the literal
`var!(font-4xl)` (the macro doesn't run on string content).

Use the resolved CSS value instead:

```css
/* WRONG */
.c_docs_page_title { font-size: var!(font-4xl); }  /* literal text */

/* RIGHT */
.c_docs_page_title { font-size: 2.25rem; }          /* var!(font-4xl) value */
```

`var(--foreground, #000)` (CSS custom property syntax with
fallback) IS valid in raw CSS strings — that works fine.

---

## 6. Pitfall — image bytes ARE deployed; nginx short-path rule is the issue

When debugging "image doesn't display":

1. Check `www/` actually contains the asset (`find www -name "*.jpg"`).
2. Probe the **long** path directly:
   `curl -sI https://ltpp.vip/github/pages/docs-pages/pages/foo.jpg` →
   expect 200 + image/jpeg + nonzero length.
3. If long path works but short path returns `200 + text/html + 0`,
   the SPA's nginx rule is the issue. Fix #1 (relative src rewrite)
   is the standard cure.

Don't add asset bytes logic before checking (2). The build often
already deployed the file correctly.

---

## 7. Verification recipe (full)

After applying fixes #1-#4 and rebuilding, probe with headless
Chromium against the locally-built WASM bundle served via
`python3 -m http.server`:

```python
import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            executable_path='/root/LTPP-MINIMAX/chrome-linux/chrome',
            args=['--no-sandbox', '--disable-dev-shm-usage'],
        )
        ctx = await browser.new_context(viewport={'width': 1280, 'height': 900})
        page = await ctx.new_page()
        await page.goto('http://127.0.0.1:5188/', wait_until='networkidle', timeout=60000)
        await page.wait_for_timeout(3500)

        # HOME baseline (hero title at y=76, sidebar first group at y=106)
        home = await page.evaluate('''() => ({
            home_y: document.querySelector('.c_home_title')?.getBoundingClientRect().top|0,
            sidebar_y: document.querySelector('.c_euv_sidebar_group_title')?.getBoundingClientRect().top|0,
        })''')

        # 1. Title alignment on doc page
        await page.evaluate("location.hash = '#/hyperlane-macros/'")
        await page.wait_for_timeout(3000)
        doc_title_y = await page.evaluate('''() =>
            document.querySelector('.c_docs_page_title')?.getBoundingClientRect().top|0
        ''')
        assert abs(doc_title_y - home['home_y']) < 5, f"title y={doc_title_y} != home y={home['home_y']}"

        # 2. Images
        await page.evaluate("location.hash = '#/essay/posts/2025/09-19.html'")
        await page.wait_for_timeout(4500)
        imgs = await page.evaluate('''() =>
            [...document.querySelectorAll('img')].filter(i => i.naturalWidth > 0).length
        ''')
        assert imgs == 10, f"expected 10 loaded images, got {imgs}"

        # 3. Home cards are <a> tags, no "blog" text
        await page.evaluate("location.href = 'http://127.0.0.1:5188/'")
        await page.wait_for_timeout(3500)
        cards = await page.evaluate('''() => {
            const all = [...document.querySelectorAll('.c_docs_feature_card')];
            return {
                total: all.length,
                as_a: all.filter(c => c.tagName === 'A').length,
                with_blog: all.filter(c => c.textContent.toLowerCase().includes('blog')).length,
            };
        }''')
        assert cards['as_a'] == cards['total'], "not all cards are clickable"
        assert cards['with_blog'] == 0, "blog literal still rendering"

        # 4. Sidebar indent + dashed border + hover
        sidebar = await page.evaluate('''() => {
            const top = [...document.querySelectorAll('.c_euv_sidebar_group:not(.c_euv_sidebar_children .c_euv_sidebar_group) > .c_euv_sidebar_group_title')];
            const nested = [...document.querySelectorAll('.c_euv_sidebar_children .c_euv_sidebar_children .c_euv_sidebar_group_title')];
            const children = document.querySelector('.c_euv_sidebar_children');
            return {
                top_x: top[0]?.getBoundingClientRect().x|0,
                nested_x: nested[0]?.getBoundingClientRect().x|0,
                border: children ? getComputedStyle(children).borderLeft : null,
            };
        }''')
        assert sidebar['nested_x'] - sidebar['top_x'] >= 20, "nested title not indented"
        assert 'dashed' in sidebar['border'], "children border not dashed"

        # 5. [!tip] renders
        await page.evaluate("location.hash = '#/hyperlane-macros/attributes.html'")
        await page.wait_for_timeout(3000)
        tip_count = await page.evaluate('''() =>
            [...document.querySelectorAll('[class*="docs-container tip"]')].length
        ''')
        assert tip_count >= 1, "no tip containers rendered"

        await browser.close()
        print("ALL CHECKS PASS")

asyncio.run(main())
```

If any assertion fails, fix and re-run before opening the PR.
