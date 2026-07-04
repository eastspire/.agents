---
name: hyperlane-upload
description: Upload files and images to ltpp.vip/upload (Hyperlane). Use when user asks to upload files to ltpp.vip, upload screenshots to ltpp, or needs the upload link from ltpp.vip/upload. Supports single file upload and dependency-aware multi-resource upload (HTML→JS→WASM with automatic URL rewriting). Triggers on "upload to ltpp", "ltpp upload", "upload screenshot to ltpp", "ltpp.vip/upload".
---

# Hyperlane Upload

Upload files to `https://ltpp.vip/upload` and return the download link.

## How It Works

The Hyperlane upload page uses custom Web Components (`<hyperlane-file-input>`) with Shadow DOM, which prevents standard Puppeteer/CDP file input manipulation. The bypass: call the page's internal `uploadFile()` function directly with a File object constructed from base64 data.

## Single File Upload

```bash
node <skill_dir>/scripts/upload.js <file-path>
```

Outputs JSON array of `{ name, url, size }` for the uploaded file.

## Multi-File Upload with Dependency Resolution

When uploading multiple interrelated resources (e.g., HTML that references JS, JS that references WASM), the upload must follow a dependency-aware workflow to ensure all references can be rewritten to final URLs.

### Dependency Analysis

Before uploading, analyze each file's references to build a dependency graph:

| Resource Type  | References To                    | Scan Pattern                                                                                               |
| -------------- | -------------------------------- | ---------------------------------------------------------------------------------------------------------- |
| `.html`        | `.js`, `.css`, `.wasm`, images   | `<script src="...">`, `<link href="...">`, `<img src="...">`                                               |
| `.js` / `.mjs` | `.wasm`, other `.js`, data files | `fetch("...")`, `new URL("...", import.meta.url)`, `import "...", WebAssembly.instantiateStreaming("...")` |
| `.css`         | fonts, images                    | `url(...)`, `@import url(...)`                                                                             |
| `.wasm`        | (leaf — no further references)   | —                                                                                                          |

### Upload Order

Upload must proceed in **reverse dependency order** (leaves first):

1. **Leaf files first** (`.wasm`, images, fonts) — no dependent references, upload directly
2. **Intermediate files** (`.js`, `.css`) — after leaf URLs are known, replace local references with uploaded URLs, then upload
3. **Entry point last** (`.html`) — after all resource URLs are known, replace all local references with uploaded URLs, then upload

### URL Rewriting Rules

After each leaf upload, rewrite references in dependent files:

```
Local:  <script src="app.js">
After:  <script src="https://ltpp.vip/upload/file/xxxxx">

Local:  WebAssembly.instantiateStreaming(fetch("core.wasm"))
After:  WebAssembly.instantiateStreaming(fetch("https://ltpp.vip/upload/file/yyyyy"))

Local:  new URL("worker.js", import.meta.url)
After:  new URL("https://ltpp.vip/upload/file/zzzzz", import.meta.url)
```

### Algorithm

```
1. Parse all input files, scan for resource references
2. Build dependency graph: node → [dependencies]
3. Topological sort to determine upload order (leaves → root)
4. For each file in upload order:
   a. Rewrite all references → replace local paths with already-uploaded URLs
   b. Upload the rewritten file content
   c. Record the returned URL
5. Output mapping: { "local/path" → "https://ltpp.vip/upload/file/..." }
```

### Reference Patterns to Scan

When scanning files, detect these patterns:

**HTML** (`<script>`, `<link>`, `<img>`, `<video>`, `<audio>`, `<source>`, `<iframe>`):

- `src="path"`, `href="path"`, `srcset="path"`, `poster="path"`
- Relative paths (`./`, `../`) and bare paths (`js/app.js`)

**JavaScript**:

- `fetch("path")`, `fetch('path')`
- `new URL("path", import.meta.url)`
- `import("path")`
- `WebAssembly.instantiateStreaming(fetch("path"))`
- Static `import` declarations
- `import.meta.url` resolved paths

**CSS**:

- `url("path")`, `url('path')`, `url(path)`
- `@import url("path")`
- `src: url("path")` (font-face)

## Example: Upload HTML + JS + WASM

```bash
# Files:
#   index.html  → <script src="app.js">
#   app.js      → fetch("core.wasm")
#   core.wasm   → (leaf)

# Step 1: Upload wasm (leaf)
node scripts/upload.js core.wasm
# → URL: https://ltpp.vip/upload/file/abc123

# Step 2: Rewrite app.js → replace "core.wasm" with "https://ltpp.vip/upload/file/abc123"
# Upload rewritten app.js
node scripts/upload.js app.js
# → URL: https://ltpp.vip/upload/file/def456

# Step 3: Rewrite index.html → replace "app.js" with "https://ltpp.vip/upload/file/def456"
# Upload rewritten index.html
node scripts/upload.js index.html
# → URL: https://ltpp.vip/upload/file/ghi789
```

## Prerequisites

- Node.js + puppeteer (`npm install puppeteer` in a directory with package.json)
- Chrome browser available

## Workflow

1. Analyze dependency graph from provided file paths
2. Sort files by dependency depth (leaves first)
3. For each file in order:
   a. Rewrite local references using already-known uploaded URLs
   b. Launch puppeteer, navigate to ltpp.vip/upload
   c. Read file as base64, convert to File object in browser context
   d. Call `uploadFile(file, fileId)` — the page's internal upload function
   e. Retrieve the download URL from IndexedDB via `getAllFiles()`
   f. Record URL for use in subsequent rewrites
4. Output final JSON with all URLs

## API Details

The page exposes these global functions:

- `uploadFile(file, fileId)` — uploads a File object
- `getAllFiles()` — returns array of `{ id, name, size, progress, url, uploadTime }`

Upload API endpoints (called internally):

- `POST /api/upload/register`
- `POST /api/upload/save`
- `POST /api/upload/merge`

## Output Format

```json
[
  {
    "name": "core.wasm",
    "url": "https://ltpp.vip/upload/file/abc123",
    "size": 123456
  },
  {
    "name": "app.js",
    "url": "https://ltpp.vip/upload/file/def456",
    "size": 7890
  },
  {
    "name": "index.html",
    "url": "https://ltpp.vip/upload/file/ghi789",
    "size": 2048
  }
]
```

## Notes

- Files are stored in the browser's IndexedDB under `FileUploadDB` / `uploadedFiles`
- The `url` in the response is a relative path — prepend `https://ltpp.vip` for the full link
- Multiple leaf files can be uploaded in one browser session
- Relative paths in references (e.g., `./js/app.js`, `../assets/core.wasm`) must be resolved against the referencing file's location before matching against the dependency map
- References embedded in generated code (e.g., `WebAssembly.instantiateStreaming` with a string path) should be replaced at the source-code level before upload
