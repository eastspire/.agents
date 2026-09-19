# ltpp.vip mirror behavior

Verified 2026-08-30 (docs-pages/docs #24, euv/euv-docs GH Pages via
`rust-wasm-gh-pages-deploy-pitfalls` pitfall 9).

ltpp.vip mirrors several GitHub Pages repos at fixed paths. The rules below
apply to **every** mirrored repo — not specific to docs-pages/pages.

## Mirrored repos observed

| Source repo (GitHub Pages) | Short alias | Real content path |
| --- | --- | --- |
| `docs-pages/pages` (VuePress build output) | `https://docs.ltpp.vip/<path>` | `https://docs.ltpp.vip/github/pages/docs-pages/pages/<path>` |
| `euv-dev/euv` (example wasm bundle) | `https://ltpp.vip/euv/<path>` (302 → ...) | `https://ltpp.vip/github/pages/euv-dev/euv/<path>` |
| `euv-dev/euv-docs` (docs-site wasm bundle) | `https://ltpp.vip/euv-docs/<path>` | `https://ltpp.vip/github/pages/euv-dev/euv-docs/<path>` |

Add more rows as you encounter them.

## Path layout rules

- The short alias (`/euv`, `/euv-docs`, etc.) does a **302 redirect** to the long
  mirror path (`/github/pages/<owner>/<repo>/<path>`).
- Following the 302 with a real browser (Playwright, Chrome, Firefox) reaches the
  body and the SPA renders normally.
- Following the 302 with `curl` **does not auto-follow** unless `-L` is given —
  and even then the body may be empty (see Short-alias 0-byte bug below).

## Short-alias 0-byte bug (critical)

- `curl -sI https://ltpp.vip/euv-docs/` returns **`200` with `content-length: 0`** —
  no 302 in the body, no error. Same for `/euv/`, `/euv-docs/`. All UAs.
- The actual content lives at the long mirror path:
  `curl --compressed https://ltpp.vip/github/pages/euv-dev/euv-docs/` returns the
  real HTML.
- **Never** test or hand a user the short alias URL. Always use the long mirror
  path.
- **Diagnostic shortcut**: if a user reports "ltpp.vip shows nothing", the first
  question is "which URL did you hit?". If they typed the short alias directly
  into the browser address bar, the browser **does** follow the 302 and renders
  correctly — so this bug only manifests in `curl` / scripts that don't follow
  redirects.

## Triggering mirror sync after a GitHub Pages deploy

ltpp.vip does NOT poll GitHub Pages for new commits. After `actions/deploy-pages@v4`
finishes, the mirror continues serving the old content until something tells it
to refresh.

To force a refresh from CI or locally:

```bash
# CI (in the repo's Pages workflow, after the deploy step):
- name: Sync Pages
  run: |
    curl -sf -X POST https://ltpp.vip/api/github/pages/sync/<owner>/<repo> \
      -H "Connection: close"

# Locally:
scripts/sync-pages.sh <owner>/<repo>
# → see rust-wasm-gh-pages-deploy-pitfalls/scripts/sync-pages.sh
```

The API returns `{"code":200,"message":"Success","data":"Synced",...}` on success.
Mirror lag from successful sync → CDN-served new content: **~30–60 s** (verified
2026-08-30 on `euv-dev/euv-docs`).

## Mirror lag (for verifying a deploy reached users)

The mirror is **not instant**. After sync API returns success, the served bytes
may still be the old version for 30–60 s.

Diff mirror vs artifact repo:

```bash
# what the mirror serves:
curl -s --compressed "https://<alias>.ltpp.vip/github/pages/<owner>/<repo>/<path>" \
  | grep -o 'assets/app-[^"]*\.css' | sort -u

# what the artifact repo has:
gh api "repos/<owner>/<repo>/contents/<path>?ref=<branch>" -q '.content' \
  | base64 -d | grep -o 'assets/app-[^"]*\.css' | sort -u

# until the served hash matches the artifact hash, the mirror is still stale.
```

Consequences:

1. After CI green + sync API success, poll the served asset hash before
   claiming "live".
2. When a user reports "still broken" right after a deploy, check the served
   hash **before** blaming their browser cache.
3. euv wasm bundles don't have content-hashed filenames (the file is
   `euv_example_bg.wasm`, not `euv_example_bg-<hash>.wasm`), so hash polling
   doesn't apply. Use Playwright DOM probe (`document.title`, `document.body`
   presence) instead — see `euv-ui-class-verification` skill §4.

## gzip quirk

`curl` **without** `Accept-Encoding` gets raw `.gz` bytes and **no
`Content-Encoding` header** — grepping that produces "old build" false alarms.
Always `curl --compressed` (or Playwright). Verified: decompressed bytes then
match the artifact repo exactly (md5-equal).

## Headers

Mirror sends `cache-control: no-cache, no-store, must-revalidate` on HTML and
assets — server side does not ask for caching. Stale views come from (a) mirror
lag, (b) aggressive client browsers that ignore no-store (Chinese Android
browsers), NOT from server cache headers. There is no service worker / manifest
on these sites.

## vuepress-theme-hope facts (rc.101, docs site only — `docs-pages/pages`)

- Theme mobile breakpoint is **719px** (`@media (max-width: 719px)`), not 767px.
- On `@media (max-width: 959px)` the theme redefines on `#app`: `--navbar-height: var(--navbar-mobile-height)` (3.25rem), `--navbar-padding-y: var(--navbar-mobile-padding-y)` (.5rem), `--navbar-padding-x` (1rem). Desktop defaults: 3.26rem / .7rem / 1.5rem.
- Mobile `.vp-navbar` rule: `position: fixed; inset: 0 0 auto; z-index: 175`.
- `.vp-sidebar` has a **padding transition** — wait ~1 s after any CSS-var change before reading computed padding.
- Theme bundle contains **zero** `env(`/`safe-area` references; all safe-area handling lives in user `index.scss`.
