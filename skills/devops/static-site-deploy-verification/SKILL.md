---
name: static-site-deploy-verification
description: 'Use when checking a static site deploy reached end users.'
---

# Static Site Deploy Verification

Verifying that a static-site deploy (GitHub Pages repo, Vercel output, object-storage mirror) is **actually what end users receive**, not just that CI went green. Covers mirror/CDN lag, asset-hash polling, gzip false alarms, and fresh-context headless measurement.

## Core principle

`CI green ≠ artifact repo updated ≠ user-facing URL serves new bytes`. Verify every hop, in order:

1. **Artifact repo** — the deploy commit exists and the HTML references the new hashed assets (`gh api repos/<org>/<repo>/contents/<page>.html | base64 -d | grep -o 'assets/[^"]*\.css'`).
2. **User-facing URL** — if a mirror/CDN sits in front, it **lags** the artifact repo. Poll the served HTML's asset hash until it flips (see below). Observed lag on ltpp.vip: ~1 min (2026-08-30); treat minutes as normal.
3. **Fresh-context headless measurement** — the only trustworthy "what a new visitor sees" check. A stale-tab or warm-cache check proves nothing.

## Workflow

```bash
# 1) get the new build's asset hash from the artifact repo
# 2) poll the user-facing URL until the mirror catches up
for i in $(seq 1 10); do
  h=$(curl -s --compressed "$URL" | grep -o 'assets/app-[^"]*\.css' | sort -u)
  [ "$h" = "assets/<new-hash>.css" ] && echo SYNCED && break; sleep 30
done
# 3) fetch the CSS and grep the rules you shipped (always --compressed, see pitfalls)
curl -s --compressed "$BASE/assets/<new-hash>.css" -o /tmp/live.css
grep -c 'your-new-rule-marker' /tmp/live.css
```

Then run `scripts/check_deployed_site.py` (fresh-context Playwright: measures computed styles and geometry, can simulate a host-injected CSS variable). Only after all three hops pass, declare the deploy live.

## Pitfalls (all verified in production, 2026-08)

- **curl without `Accept-Encoding` can return raw .gz bytes with no `Content-Encoding` header** (ltpp.vip behavior) — `grep` on that reports "deploy didn't take" as a false alarm. Always `curl --compressed` or use a real browser.
- **Don't blame the user's browser cache until the mirror is confirmed synced.** Hash-named assets mean stale HTML ⇒ stale everything, but the mirror itself may be what's stale. Check the served hash first; only then advise clearing site data / cache-buster query.
- **CSS transitions corrupt immediate reads**: e.g. vuepress-theme-hope's `.vp-sidebar` has a padding transition — reading `getComputedStyle` right after setting a CSS variable returns the mid-transition value (0px). Wait ~1 s after injection before asserting.
- **Beware empty-body 200 short paths**: `docs.ltpp.vip/euv/` returns 200 with 0 bytes; the real root is the long mirror path. Verify you're testing the URL that actually serves content (see `references/ltpp-vip-mirror.md`).
- **Undefined CSS var without fallback invalidates the whole declaration** at computed-value time (`calc(var(--maybe-missing) + 8px)` → property unset). After shipping var-consuming rules, grep the served CSS to confirm every referenced var is actually defined there.
- **Porting a reference implementation's fix: copy it verbatim** (property structure, the upstream theme's own breakpoints, explicit defaults) — don't loosely "improve" it en route; every adaptation is a drift point (user correction 2026-08-30: 直接复制源样式).

## Files

- `references/ltpp-vip-mirror.md` — ltpp.vip mirror behavior: path layout, lag measurement, gzip quirk, empty-body short paths, how to diff mirror vs artifact repo.
- `scripts/check_deployed_site.py` — parameterized fresh-context verifier: hash poll → CSS grep → Playwright computed-style assertions, optional host-var injection.
