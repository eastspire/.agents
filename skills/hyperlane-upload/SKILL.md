---
name: hyperlane-upload
description: Upload files and images to ltpp.vip/upload (Hyperlane). Use when user asks to upload files to ltpp.vip, upload screenshots to ltpp, or needs the upload link from ltpp.vip/upload. Triggers on "upload to ltpp", "ltpp upload", "upload screenshot to ltpp", "ltpp.vip/upload".
---

# LTTP Upload

Upload files to `https://ltpp.vip/upload` and return the download link.

## How It Works

The Hyperlane upload page uses custom Web Components (`<hyperlane-file-input>`) with Shadow DOM, which prevents standard Puppeteer/CDP file input manipulation. The bypass: call the page's internal `uploadFile()` function directly with a File object constructed from base64 data.

## Usage

```bash
node <skill_dir>/scripts/upload.js <file-path> [file-path2 ...]
```

Outputs JSON array of `{ name, url, size }` for each uploaded file.

## Prerequisites

- Node.js + puppeteer (`npm install puppeteer` in a directory with package.json)
- Chrome browser available

## Workflow

1. Run the upload script with the file path(s)
2. Script launches headless Chrome, navigates to ltpp.vip/upload
3. Reads file as base64, converts to File object in browser context
4. Calls `uploadFile(file, fileId)` — the page's internal upload function
5. Retrieves the download URL from IndexedDB via `getAllFiles()`
6. Outputs JSON with `https://ltpp.vip` prefix added to the URL

## API Details

The page exposes these global functions:

- `uploadFile(file, fileId)` — uploads a File object
- `getAllFiles()` — returns array of `{ id, name, size, progress, url, uploadTime }`

Upload API endpoints (called internally):

- `POST /api/upload/register`
- `POST /api/upload/save`
- `POST /api/upload/merge`

## Example

```bash
node scripts/upload.js D:\screenshots\photo.png
# Output: [{"name":"photo.png","url":"https://ltpp.vip/upload/file/...","size":12345}]
```

## Notes

- Files are stored in the browser's IndexedDB under `FileUploadDB` / `uploadedFiles`
- The `url` in the response is a relative path — prepend `https://ltpp.vip` for the full link
- Multiple files can be uploaded in one invocation
- Upload progress is tracked in IndexedDB (progress: 0-100)
