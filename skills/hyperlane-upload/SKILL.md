---
name: hyperlane-upload
description: Upload files to ltpp.vip (Hyperlane) and get shareable links. AUTO-TRIGGER on any upload intent — "上传", "upload", "上传到 ltpp", "上传截图", "upload to ltpp", "upload screenshot", "upload to ltpp.vip", "share via ltpp", "put on ltpp", "get a ltpp link", "deploy static site to ltpp", "publish HTML to ltpp". Use when user wants a public URL for an HTML page, screenshot, image, JS bundle, WASM, CSS, or any other file. Supports single-file upload and dependency-aware multi-resource upload (HTML+JS+WASM / HTML+CSS+font / HTML+images) where references are auto-rewritten to final ltpp URLs.
---

# Hyperlane Upload (ltpp.vip)

Upload any file(s) to `https://ltpp.vip/upload` and return the public download link(s).

This skill is the **only supported path** for getting a ltpp.vip URL. Use it every time the user wants to publish, host, share, or deploy a file to ltpp.

## When to Trigger

**Always** invoke this skill if the user request contains any of:

- "上传" / "传一下" / "放上去" / "发布" / "部署" / "托管" / "分享" / "得到一个 ltpp 链接"
- "upload" / "upload to ltpp" / "upload screenshot to ltpp" / "share via ltpp" / "publish to ltpp" / "host on ltpp" / "get a ltpp link" / "ltpp.vip" / "ltpp upload"
- A request to "把这个 HTML/截图/图片/JS/WASM/CSS 发到公网" / "make this public" / "give me a public link"
- A multi-file request like "把整个项目传上去" / "upload the whole project" / "deploy this site" — **must** go through the dependency-aware workflow below

If you're not sure, **invoke it**. Wrong trigger is cheap; missed trigger loses the user a round trip.

## How It Works

`upload.js` is a **pure single-file uploader** — it takes one or more file paths and uploads each independently. It does **not** parse HTML/JS or rewrite references.

That means: **for multi-file uploads with dependencies (HTML → JS → WASM, etc.), the agent must drive the workflow itself**: analyze the dependency graph, upload leaves first, rewrite references in dependent files with the returned URLs, then upload the rewritten versions. The script is called once per file in topological order.

## Script Usage

```bash
node <skill_dir>/scripts/upload.js <file-path> [file-path2 ...]
```

- Outputs a JSON array of `{ name, url, size }` for each uploaded file (in input order).
- `url` is **already the full absolute URL** (`https://ltpp.vip/upload/file/...`).
- Files are uploaded in parallel-safe order; each call is independent.

Verify the script exists:
```bash
ls -la <skill_dir>/scripts/upload.js   # expect ~4.5KB
node --version                          # expect v20+
```

## Scenario A — Single File

For a single file (one HTML, one screenshot, one image, one PDF, one JSON dump), just call the script with that one path and return the `url` field.

```bash
node scripts/upload.js /root/out/page.html
# → JSON array, first element has "url": "https://ltpp.vip/upload/file/abc123"
```

No dependency analysis needed.

## Scenario B — Multi-File with Dependencies (HTML + JS + WASM, HTML + CSS, etc.)

When a file references other local files (e.g. `<script src="app.js">` in HTML, `fetch("core.wasm")` in JS, `url("font.woff2")` in CSS), the references must be **rewritten to the final ltpp URLs** before the referencing file is uploaded. Otherwise the deployed site would 404 on every resource.

### Step 1 — Build the Dependency Graph

Scan every file in the input set for local references. Build a directed graph `file → [referenced local files]`.

**Scan patterns by file type:**

| File Type | What to scan | Patterns |
|-----------|--------------|----------|
| `.html` / `.htm` | Scripts, stylesheets, media, frames, sources | `src="..."`, `href="..."`, `srcset="..."`, `poster="..."`, `data-src="..."` inside `<script>`, `<link>`, `<img>`, `<video>`, `<audio>`, `<source>`, `<iframe>`, `<use>` (SVG) |
| `.js` / `.mjs` | Imports, fetches, URL constructors, WASM loads | `import "..."`, `import('...')`, `from "..."`, `fetch("...")`, `fetch('...')`, `new URL("...", import.meta.url)`, `new URL("...", document.baseURI)`, `WebAssembly.instantiateStreaming(...)`, `WebAssembly.compileStreaming(...)`, `importScripts("...")` (in workers), `new Worker("...")`, `new SharedWorker("...")` |
| `.css` | Images, fonts, other stylesheets | `url(...)`, `url('...')`, `url("...")`, `@import url(...)`, `@font-face { src: url(...) }`, `background-image: url(...)` |
| `.wasm` | (leaf — no further references) | — |
| `.svg` | Other SVGs, images, fragments | `xlink:href="..."`, `href="..."` inside `<use>`, `<image>` |
| `.json` / `.txt` | Data refs (rare) | `"path/to/file"` string literals (only if explicitly data refs) |

**Skip (do not rewrite):**

- Absolute URLs starting with `http://`, `https://`, `//`, `data:`, `blob:`, `mailto:`, `tel:`
- Protocol-relative URLs (`//cdn.example.com/...`)
- Inline content (`<script>code</script>`, `<style>code</style>`)
- Anchors (`#section`)
- Query-only URLs (`?foo=bar`)

**Relative path resolution:**

- Resolve each found reference against the **referencing file's directory**.
- `./js/app.js` referenced from `/root/site/index.html` → `/root/site/js/app.js`
- `../assets/core.wasm` referenced from `/root/site/js/app.js` → `/root/site/assets/core.wasm`
- Bare paths like `core.wasm` are resolved against the same directory

Only files that actually exist on disk are added as edges in the graph. Missing references are flagged (warn the user).

### Step 2 — Topological Sort (Leaves First)

Walk the graph and produce an upload order such that every file's dependencies are uploaded **before** the file itself.

```
Leaves (no outgoing refs in the input set)  → uploaded first
  ↓
Intermediate (refs only leaves)             → uploaded after their deps
  ↓
Entry point (typically the .html)           → uploaded last
```

If the graph has cycles (rare; e.g. mutual imports in JS modules), break the cycle by uploading one side first and rewriting the reference in the other side to that URL (the cycle becomes a DAG at upload time).

If a file outside the input set is referenced (e.g. the HTML references a CDN file), it is **not** uploaded — leave that reference as-is.

### Step 3 — Upload & Rewrite Loop

For each file in topological order:

1. Read the file from disk.
2. For every local reference inside the file, look up the corresponding entry in the **already-uploaded map** (`local_path → final_url`) and rewrite the source to use the final URL.
3. If the rewritten content differs from the original, write a temp file to `/tmp/` and upload that temp file (so the original on disk stays untouched).
4. Call `node upload.js <temp-or-original-path>`.
5. Parse the JSON output and add `local_path → final_url` to the map.
6. Move on to the next file.

**Important:** if a referenced file is not in the input set and not yet uploaded (because it was outside the scope), **do not** rewrite that reference — leave it as a local path. Tell the user which files are external so they can decide.

### Step 4 — Report

After the loop, output a final mapping the user can refer to:

```json
{
  "entry_url": "https://ltpp.vip/upload/file/ghi789",
  "files": {
    "/root/site/index.html":  "https://ltpp.vip/upload/file/ghi789",
    "/root/site/js/app.js":   "https://ltpp.vip/upload/file/def456",
    "/root/site/core.wasm":   "https://ltpp.vip/upload/file/abc123"
  }
}
```

The `entry_url` is the one the user opens in a browser. The other URLs are inside the rewritten entry and don't need to be shared separately.

## URL Rewriting Cheatsheet

| Before (local) | After (uploaded) |
|----------------|------------------|
| `<script src="app.js">` | `<script src="https://ltpp.vip/upload/file/def456">` |
| `<link href="style.css" rel="stylesheet">` | `<link href="https://ltpp.vip/upload/file/xyz" rel="stylesheet">` |
| `<img src="../imgs/hero.png">` | `<img src="https://ltpp.vip/upload/file/qrs">` |
| `fetch("core.wasm")` | `fetch("https://ltpp.vip/upload/file/abc123")` |
| `WebAssembly.instantiateStreaming(fetch("core.wasm"))` | `WebAssembly.instantiateStreaming(fetch("https://ltpp.vip/upload/file/abc123"))` |
| `new URL("worker.js", import.meta.url)` | `new URL("https://ltpp.vip/upload/file/worker_url", import.meta.url)` |
| `import("./mod.js")` | `import("https://ltpp.vip/upload/file/mod_url")` |
| `background: url("../fonts/x.woff2")` | `background: url("https://ltpp.vip/upload/file/font_url")` |

**Attribute-aware for HTML:** when rewriting `srcset` (a comma-separated list with descriptors), each URL is rewritten independently. When rewriting `src` on a `<source>` inside `<picture>`, treat it like any other `src`.

**Quote-agnostic:** handle `"`, `'`, and unquoted attribute values. The scan regex should be permissive on quotes.

## End-to-End Example (HTML + JS + WASM)

```
Input files:
  /root/site/index.html   — references app.js
  /root/site/app.js       — references core.wasm
  /root/site/core.wasm    — leaf

Graph:
  index.html → app.js → core.wasm

Upload order: core.wasm, app.js, index.html

1. Upload core.wasm (no rewrites needed)
   → URL: https://ltpp.vip/upload/file/abc123

2. Rewrite app.js: fetch("core.wasm") → fetch("https://ltpp.vip/upload/file/abc123")
   Write to /tmp/app.rewritten.js, upload
   → URL: https://ltpp.vip/upload/file/def456

3. Rewrite index.html: <script src="app.js"> → <script src="https://ltpp.vip/upload/file/def456">
   Write to /tmp/index.rewritten.html, upload
   → URL: https://ltpp.vip/upload/file/ghi789

Return entry_url: https://ltpp.vip/upload/file/ghi789
```

## Common Patterns

### One HTML page (no deps)
```bash
node scripts/upload.js /root/out/page.html
```

### HTML + sibling assets (CSS, images, fonts)
The agent scans `index.html` for `<link>`, `<img>`, `<source>`, finds `style.css`, `hero.png`, uploads them first, then uploads the rewritten HTML.

### A whole static site (HTML + nested JS + WASM + CSS + images)
Recursive: scan every file in the directory, build the full graph, topo-sort, upload leaves first. The entry point is whatever `.html` the user named (or the only `.html` if there's one).

### Screenshots / images / PDFs (no deps)
Just upload each one and return the URLs.

## What to Tell the User

After upload, respond with:
- The final entry URL (for HTML: the one to open in browser)
- The full file→URL mapping if they need to reference individual files
- Any external references that were left as-is (so they know what wasn't covered)

## Failure Modes & Recovery

- **Network error / timeout during chunk upload** — the script logs which step failed. Just re-run `upload.js` for that single file; the server treats each registration as independent.
- **`register` returns non-200** — usually means the filename conflicts with an active upload session. Wait 30s and retry, or rename the file.
- **Reference not found on disk** — warn the user with the file and the missing path. Do not silently skip. Do not invent a URL.
- **Puppeteer not available** — irrelevant; this script uses raw `https` and doesn't need a browser. If you find yourself reaching for puppeteer, you've drifted to the wrong path.
- **Output JSON parse error** — almost always means a chunk failed; look at the previous log line for which step.

## Common Pitfalls When Implementing the Workflow

These tripped the author during verification — re-read before writing your own scan/rewrite code:

1. **Don't try to read binary files as text.** When scanning for references, only open files with text extensions (`.html .htm .js .mjs .css .svg .json .txt`). For `.wasm .png .jpg .woff2 .pdf .ico` etc., there are no references inside — they're always leaves. Opening them as UTF-8 throws `UnicodeDecodeError` on byte `0x89` (PNG) or `0x00` (WASM).
2. **Scanner regexes must be whitespace-tolerant.** `await fetch("core.wasm")` and `fetch  (  "x"  )` are both legal. Use `\s*` between keywords and around parens, not `\(\s*...\s*\)` only inside the parens. A naive `fetch\("..."\)` regex misses anything with intervening whitespace.
3. **Sort siblings of the same depth deterministically.** Use a sorted queue in the topological sort. Two files at the same depth uploaded in different orders across runs will produce different URLs each time — that's fine, but if you want reproducibility, sort the leaf queue by path.
4. **Rewrite with multiple reference forms.** When you have `url_map[local_path] = final_url`, the same file may be referenced as `"app.js"`, `"./js/app.js"`, `"js/app.js"`, or `"../js/app.js"` depending on the referencing file's directory. Try all of them as replace patterns. For CSS, the `url(...)` form has no quotes, so the regex needs a separate branch.
5. **Preserve the original files on disk.** Always write rewritten content to a temp file (under `/tmp/`) and pass the temp path to `upload.js`. Never mutate the user's source. Clean up the temp file after upload.
6. **Don't loop forever on cycles.** A real-world example: a JS module that does `import.meta.url` resolution against itself, or CSS `@import` of a file that re-imports the original. If the topo sort doesn't converge after N iterations, break the cycle by treating one side as if it had no incoming edge (and tell the user).
7. **`script type="module"` matters.** An HTML with `<script type="module" src="...">` is treated as a module by the browser — `import` statements inside work as expected, but the script must be served with the correct MIME type. ltpp.vip serves uploaded files with MIME inferred from extension, so `.js` and `.mjs` get `application/javascript` automatically. No special handling needed.
