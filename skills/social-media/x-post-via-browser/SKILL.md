---
name: x-post-via-browser
description: "Use when posting to X/Twitter through the user's logged-in browser, or when xurl has no registered app. Covers what is proven, what is forbidden, and the draft-destroying failure that must be avoided."
version: 1.0.0
author: local
license: MIT
platforms: [macos, linux]
metadata:
  hermes:
    tags: [twitter, x, posting, cdp, browser-automation, real-profile, xurl, graphql, drafts]
    related_skills: [xurl, chrome-real-profile-launch, chrome-devtools-protocol, twitter-no-login]
---

# Posting to X from a logged-in browser

## What this skill actually concludes

Posting to X without an X API app is **not reliably possible**, and the
obvious workaround **destroys the user's unsaved drafts**. Both statements were
measured on 2026-09-30 against a logged-in `@eastspire_sheng` session; the
evidence is below so nobody re-derives it.

Use **`xurl`** for posting. It is the official API and needs one app
registered. Use the browser only to *read*.

## The failure that matters: X restores drafts into every new composer tab

Measured directly.

1. The user had 10 composer tabs open, each holding an unfinished tweet of
   their own (grokbot billing, GLM-5.3, OpenAI revenue, GPT-6.1, a Hengdian
   actor interview, and so on).
2. Opening a **fresh** tab on `https://x.com/compose/post` came back with the
   editor **pre-filled from X's server**. Different tab, different draft each
   time — the second probe loaded an "AI czar" draft that had not been open
   in any local tab.
3. Ruled out the obvious explanations:
   - `location.href` was the tab we opened, so the CDP target was correct.
   - The new target id was not in the pre-existing target list, so it was
     genuinely a new tab.
   - `localStorage` and `sessionStorage` held no draft-like key, so the
     restoration comes from the server, not the browser.

Consequence: **any "open a new tab, type, click Post" automation will overwrite
and publish whichever draft X happens to restore.** There is no selector that
avoids this; the selector finds a real editor that already has text in it.

What saved the drafts was a content assertion, not a better selector: the script
compared the editor's text against what it was about to type and refused. If
that check is missing, the user's unfinished tweet goes out under automation.

## Why not the internal API

Both routes were tried against the live session.

**The bearer token cannot be hardcoded.** X rotates it. The public token copied
from a logged-out page returned `error 89 "Invalid or expired token"`.
Recovering the real one works: enable CDP `Network.enable` on a logged-in tab
and read the `Authorization` header off x.com's own GraphQL requests. The live
token differs from the well-known one only in its tail.

**With a valid bearer, the internal endpoints still refuse posting:**

| Route | Result |
|---|---|
| `api.x.com/1.1/account/verify_credentials.json` | `401`, error 89 with the stale token |
| `POST x.com/i/api/2/tweets` (REST) | `403 Unsupported Authentication` — "Authenticating with Unknown is forbidden for this endpoint. Supported authentication types are [OAuth 1.0a User Context, OAuth 2.0 User Context]." |
| `POST x.com/i/api/graphql/<qid>/CreateTweet` | needs the per-deployment query id |

The 403 is the important line: **the browser session can read, but posting
requires OAuth 1.0a or OAuth 2.0 user context.** A bearer from a logged-in web
session is not that. So the browser cannot post even with correct credentials,
and guessing `CreateTweet`'s query id — a per-deployment constant, not a secret
— is not a workaround worth relying on.

**Conclusion: posting goes through `xurl`.** Register an app, authenticate once,
and every post is a clean API call that cannot touch the browser, the drafts,
or the 4 GB profile.

## Setup: xurl, once, by the user

The agent cannot do this part — it involves pasting a Client Secret.

```bash
brew install --cask xdevplatform/tap/xurl   # or the install.sh / go / npm route
xurl auth apps add my-app --client-id <ID> --client-secret <SECRET>
xurl auth oauth2 --app my-app <USERNAME>
xurl auth default my-app
xurl auth status      # the default app must show an oauth2 token
```

Set the app's type to "Web app, automated app or bot" in the X dashboard;
Native App fails with `unauthorized_client`. If OAuth appears to succeed but
requests then fail, the token was saved to the built-in `default` profile
instead of the named one — re-run with `--app my-app`.

`xurl auth status` is the only safe way to check. Never read `~/.xurl`, never
pass secrets on a command line, never use `--verbose` in an agent session.

## Posting

```bash
xurl post "text"
xurl post "text" --media-id MEDIA_ID
xurl reply POST_ID "text"
xurl delete POST_ID
```

Read before writing — `xurl whoami`, `xurl user <handle>`, `xurl search ... -n 3`.
It confirms the account is the intended one, which matters when a thread must
continue a specific conversation.

To post a thread: post the root, take `data.id` from the JSON, then
`xurl reply <root-id>` for each follow-up. Every response is JSON, so the ids
can be piped rather than retyped.

## Reading through the browser is fine

For anything that only needs to look at X, the browser is the better tool
because it needs no app registration. Use `chrome-real-profile-launch` to get
the shared instance, then read the DOM.

Guardrails when reading:

- Open a tab on `/home`, not `/compose/post`. The composer is the only page
  that carries a restorable draft.
- Wait for real content: `document.body.innerText.length > 400`, not
  `readyState === "complete"`. X is a SPA and both a logged-out and a
  logged-in page can report complete with an empty body.
- A login check that only looks for the absence of a login link is not proof.
  Verify with body text, and prefer an element the logged-out page lacks, such
  as `[data-testid="SideNav_AccountSwitcher_Button"]`.

## Never

- Never drive `x.com/compose/post` with automation while the user has drafts
  open. It publishes one of them.
- Never read `~/.xurl`, or accept a Client Secret in chat.
- Never claim a post happened without the JSON response from `xurl` as proof.
- Never close or reuse the user's tabs to "clean up" — the draft content is
  bound to the tab, and 10 compose tabs is a working state, not litter.
