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

Two separate findings, both measured on 2026-09-30 against a logged-in
`@eastspire_sheng` session. The first was wrong in this skill's earlier
revision and is corrected below; the correction matters more than the
conclusion.

1. **The restored drafts are SERVER-side and cannot be cleared from the
   client.** Two measurements point opposite ways and the second settles it:
   the drafts dialog is empty (`emptyState`: "保留想法 / 还没有准备好发帖？"),
   which suggests nothing is stored on x.com; but
   `Storage.clearDataForOrigin` (local_storage, indexeddb, cache_storage,
   service_workers) returns success and a brand new composer still comes back
   with a *different* draft every time. So the pool lives server-side, and the
   empty dialog is a view filter, not the store.
2. **Posting still needs an API app.** The internal endpoints refuse a web
   session even with a valid bearer, so the browser is for reading.

Use **`xurl`** for posting. Use the browser only to *read*.

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
   - `localStorage` and `sessionStorage` held no draft-like key, which at the
     time looked like proof they were local. **That inference was also wrong**,
     and was corrected by the successful `clearDataForOrigin` above.

Each open produced a *different* draft, so it is a pool, not one slot. Closing
composer tabs does not help: after closing every composer tab on a freshly
launched instance, a new composer still came back with text. Discarding the
restored draft via `app-bar-close` also does not help.

Consequence: **any "open a new tab, type, click Post" automation will overwrite
and publish whichever draft X happens to restore.** There is no selector that
avoids this; the selector finds a real editor that already has text in it.

What saved the drafts was a content assertion, not a better selector: the script
compared the editor's text against what it was about to type and refused. If
that check is missing, the user's unfinished tweet goes out under automation.

## Clearing the local drafts (the actual fix)

Because the drafts are local, `Storage.clearDataForOrigin` over CDP removes
them and leaves the login alone — **do not include `cookies` in
`storageTypes`** or the session is lost and has to be re-established.

```python
c.send("Storage.clearDataForOrigin",
       origin="https://x.com",
       storageTypes="local_storage,indexeddb,cache_storage,service_workers")
```

Then verify: open a composer and read
`document.querySelector('[data-testid="tweetText"]').textContent`. Empty means
the pool is clear.

**Do not use `indexedDB.databases()` in the page.** It hangs indefinitely
under headless Chrome — measured twice, each time a multi-minute stall. The
protocol method does not depend on the page and is the one to use.

With a clean pool the composer is safe to drive: type with
`document.execCommand('insertText')`, re-read the editor and compare it to
what was intended, then click `[data-testid="tweetButton"]`.

## Two CDP client bugs that cost hours here

Both were silent, which is what made them expensive. Use a client that handles
them, or copy `scripts/cdp.py` from this skill.

**WebSocket control frames are not JSON.** opcodes 8/9/10 (close/ping/pong) and
2 (binary) share the framing but not the payload. Parsing a ping as JSON raises
`UnicodeDecodeError`; swallowing that as "no reply" makes every
`Runtime.evaluate` look like it never ran. Check `b1 & 0x0F` before decoding.

**The first few evaluates on a new tab lose their replies.** While the renderer
swaps execution contexts the reply never comes back. Measured: 33 s of warm-up
on a fresh target, then 0.5 s per call. Fail fast (a 6 s wait) and retry
immediately — a long wait per attempt turns this into minutes of apparent
hang, and an unbounded wait produced a 14-minute freeze here. Budget ~35 s of
warm-up per new tab and reuse one tab when several calls are needed.

A `js()` that returns `None` on failure is the root of a whole class of false
conclusions. It must return a distinguishable error marker, and every caller
must check it. Two separate rounds concluded "the click did nothing" when the
real problem was a lost reply.

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
because it needs no app registration. **Launch it headed:**

```bash
bash ~/.agents/skills/software-development/chrome-real-profile-launch/scripts/run.sh \
  --headed --port 9232 --no-tab
```

Headless gets a 403 (see above). Then read the DOM.

Guardrails when reading:

- Open a tab on `/home`, not `/compose/post`. The composer is the only page
  that carries a restorable draft.
- Wait for real content: `document.body.innerText.length > 400`, not
  `readyState === "complete"`. X is a SPA and both a logged-out and a
  logged-in page can report complete with an empty body.
- A login check that only looks for the absence of a login link is not proof.
  Verify with body text, and prefer an element the logged-out page lacks, such
  as `[data-testid="SideNav_AccountSwitcher_Button"]`.

## The composer cannot be driven: five failures, all measured

Every way of putting text into the X composer was tried against the live one.
All five fail, and none of them is a selector problem.

| Approach | Result |
|---|---|
| `execCommand('insertText')` | returns `false`, inserts nothing |
| `el.textContent = t` + `beforeinput`/`input` events | text lands and verifies, but Draft.js's React state never sees it — the Post button stays `disabled` forever |
| `Input.insertText` (whole string) | only the last line survives: a 159-char post left `"I suggest using 硅头."` |
| `Input.insertText` (per line) | the restored draft rotates underneath and ends up being what would be posted |
| real key events, one char at a time | same — mid-typing the editor swapped to a different draft (a 42-character "雷电芽衣" post) |

`Input.dispatchKeyEvent` with `commands: ["paste"]` pastes nothing because the
clipboard is empty, and populating it with `pbcopy` hung outright in this
environment.

The blocker underneath all of them: **the draft pool rotates while you work.**
A fresh composer, a re-render, or a slow typing run can each replace the
editor contents with a different draft. Anything that takes more than one
evaluate — or more than a second — is racing it. That is also why the drafts
are dangerous to automate against, independent of any typing problem: a
mistimed click publishes somebody's unfinished text.

**Conclusion: post through `xurl` with a registered app.** The browser is for
reading only. If that is not acceptable, the only safe route is a human at the
keyboard.

## `--headless` gets 403; `--headed` does not

Worth its own note because it is easy to misdiagnose. After a long session, the
headless instance stopped serving x.com entirely:

```
href: chrome-error://chromewebdata/
body: 访问 x.com 的请求遭到拒绝 / HTTP ERROR 403
```

A plain `curl https://x.com/` from the same machine returned **200**, so this is
not a rate limit and not an IP block — x.com is rejecting the headless
fingerprint. `run.sh --headed` fixed it immediately: 2527 body characters,
logged in as `@eastspire_sheng`.

A 403 page reports ~53 body characters and no composer element, so an
"is the composer empty?" check answers "empty" and looks like success. Always
confirm the page is really x.com first:

```python
href = c.js("location.href")
assert href.startswith("https://x.com"), f"blocked or error page: {href}"
```

## Rate limiting and the 403 wall

After a long session of opening and closing composer tabs, x.com stopped
serving the headless instance entirely:

```
href:  chrome-error://chromewebdata/
body:  访问 x.com 的请求遭到拒绝 / HTTP ERROR 403
```

The user's own Chrome was unaffected — the block applies to the copied
profile's instance, not the account.

This matters beyond publishing: **a 403 error page reports a tiny body
(`bodyChars: 53`) and no composer element**, so a "is the composer empty?"
check answers "empty" and looks like success. Always confirm the page really
is x.com before trusting anything read from it:

```python
href = c.js("location.href")
assert href.startswith("https://x.com"), f"blocked or error page: {href}"
```

Re-launching the instance does not clear it; it needs time. Treat a burst of
tab churn as the trigger and pace the work accordingly.

## The scripts

| Script | Purpose |
|---|---|
| `scripts/cdp.py` | Minimal CDP client. Control-frame handling, retrying `js()`, `set_port()`, `composer_text()`. |
| `scripts/selftest.py` | Verifies the client before trusting it. **Run this first.** |
| `scripts/bench.py` | Measures evaluate latency. Use it to tell warm-up from a real stall. |
| `scripts/probe_draft_restore.py` | Re-derives the draft-restore finding and refuses rather than acting. |

`selftest.py` earns its place: on its first run it reported `close_tab` as
broken when the check's own arithmetic was wrong (the preceding open had
already restored the count), and it flagged a "slow" client that was really
just doing its warm-up. Both were faults in the check, and neither was
visible without running it.

## Never

- Never drive `x.com/compose/post` with automation while the user has drafts
  open. It publishes one of them.
- Never read `~/.xurl`, or accept a Client Secret in chat.
- Never claim a post happened without the JSON response from `xurl` as proof.
- Never close or reuse the user's tabs to "clean up" — the draft content is
  bound to the tab, and 10 compose tabs is a working state, not litter.
