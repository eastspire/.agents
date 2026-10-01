---
name: x-post-via-browser
description: "Use when posting to X/Twitter through the user's logged-in browser. The proven path, and the four things that raise an unsaved-changes dialog."
version: 2.0.0
author: local
license: MIT
platforms: [macos, linux]
metadata:
  hermes:
    tags: [twitter, x, posting, cdp, browser-automation, real-profile, drafts]
    related_skills: [chrome-real-profile-launch, chrome-devtools-protocol, xurl]
---

# Posting to X from the user's logged-in browser

Verified 2026-10-01 on a Premium account: four long posts of 608–1060
characters published, each verified character-for-character on the profile
timeline afterwards.

## The shortest path that works

1. Launch the profile copy (headed — see below).
2. Open **one** tab on `x.com/compose/post`. This is the only page load.
3. Focus the editor, read what is in it.
4. If it is empty, put the whole post in with **one** `Input.insertText`.
5. Read it back and compare against the source, normalised.
6. If it matches and the button is enabled, click `[data-testid="tweetButton"]`.
7. Read the profile timeline and confirm the status id. `CLICKED` is not proof.
8. Post the next one the same way — X empties the composer itself after a post,
   so step 3 finds it empty and step 4 types into it.

## Never refresh, never clear, never navigate

These are the rules, and they are not stylistic.

**No `location.assign`, no `Page.reload`, no `Page.navigate`, no `one_tab.py`
style reopen, no second tab.** Every page load makes the user confirm it in
their UI. If the composer is not open, click the compose control already on
screen — `[data-testid="SideNav_NewTweetButton"]`, `a[href*="/compose/post"]`,
or `[data-testid="appTabBarPostBtn"]` — which opens it in place.

**Never empty the composer.** Clearing it, reloading, navigating and pressing
Escape all raise Chrome's own dialog, 「系统可能不会保存您所做的更改」, and that
modal then blocks every later CDP call until the user dismisses it. X sets no
`onbeforeunload` handler (verified `window.onbeforeunload === null`); the dialog
is Chrome's, caused by an IME composition left open on a contenteditable.

So the flow is read-only about the box: **read it; type only into an empty one;
if it already holds exactly the requested post, post it as it stands; if it
holds anything else, leave it and report.** There is no retry that does not
involve clearing, so a failure here is a stop, not a loop.

**Close the IME composition.** `Input.imeSetComposition` STARTS one. Always
follow it with `Input.insertText` carrying the same text, which commits it
once. Sending the composition twice duplicated a post to 376 characters. End
every run with an explicit close.

## Never take the mouse or the keyboard

No `Page.bringToFront`, no `Input.dispatchMouseEvent`, no computer_use
`bring_to_front`, no OS clicks. Focus is set with `el.focus()` inside the page.
The user's pointer and OS focus are never moved.

## A long post is ONE insertText

Measured: 2500 characters land in 0.0s, with newlines and all. Character-by-
character typing was only ever needed to work around a whole-string insert on
a **short** post, which X treated as a submit — that does not apply to a long
one. X expands past 280 characters into a thread on its own, so a long post
does not have to be split, and the paragraph breaks can stay.

A URL is the exception. Typed per character, X turns it into a link entity
mid-stream and the rest is dropped (`https://github.c` was all that survived).
`Input.imeSetComposition` with the whole URL delivers all of it. Put URLs near
the end, and check the link card after posting.

## Two traps in the editor

**Two nodes share `data-testid="tweetTextarea_0"`.** One is real (its `class`
contains `public-DraftEditor-content`), one is an empty duplicate.
`querySelector` returns whichever is first in document order, which changes
between renders. That alone produced writes that vanished and a click that
posted a single stray character. Address `document.activeElement` and refuse to
act when it is not the Draft editor.

`[data-testid="tweetText"]` is a **decoy** — a display layer whose
`textContent` goes stale. Never write to it and never read it to decide whether
text landed.

**The raw length lies.** X's Draft editor keeps hidden text nodes of its own,
so it reports 860 characters against an 859-character source even when the
visible text matches exactly. Gate on the normalised text compare, not on
length; a raw-length check rejects posts that are perfect.

## Verifying

Normalise both sides the same way: drop all whitespace, drop the space X
removes at a Latin/CJK boundary while typing (`AI 时代` becomes `AI时代`), and
strip URLs before comparing — then require every expected URL present verbatim
as the link's own **visible text**, since X rewrites the href to a `t.co`
shortener. A URL is stored as an `<a>` and is not in `textContent`.

Three rules that came from a post getting it wrong:

- A length check alone once passed a post with eight stray characters.
- A compare that ignores the link's visible text passes a truncated link.
- `CLICKED` proves nothing. Read the profile timeline and require the status id.

## Launching: headed, and through the local proxy

```bash
bash ~/.agents/skills/software-development/chrome-real-profile-launch/scripts/run.sh \
  --headed --port 9240 --fresh --no-tab
```

`run.sh` probes 7897/7890/7891/8080/10809/1080 and passes `--proxy-server` for
the first that answers. This is not optional on this machine. Without it a
browser launched with its own `--user-data-dir` cannot complete a TLS
handshake to any HTTPS host: DNS resolves, the TCP connection opens, and then
the handshake is cut — `curl` reports `SSL_ERROR_SYSCALL`, Chrome reports
`net_error -100` (ERR_CONNECTION_CLOSED). The daily browser works because Clash
Verge Rev routes it through a TUN interface, which a separate user-data-dir
does not get. It looks like a crash and is not; the Crashpad pending directory
is empty and no crash report is written. **Check the log for `net_error -100`
before concluding anything died.**

`--fresh` also matters: it drops the scratch profile and re-copies, and it
excludes the `Singleton*` files.

## Do not inject to defeat headless detection

X blocks headless browsers; `--headed` is the answer. Injecting a spoofed
fingerprint to get past the detection is circumventing an access control, and
this skill does not do it. Driving the composer's own input path in a browser
the user is logged into is a different thing from impersonating a human client
to the server, and only the first is in scope here.

## Two CDP client bugs that cost hours

Both are silent. `scripts/cdp.py` handles them; use it or copy its patterns.

**WebSocket control frames are not JSON.** opcodes 8/9/10 (close/ping/pong) and
2 (binary) share the framing but not the payload. Check `b1 & 0x0F` before
decoding. Parsing a ping as JSON raises `UnicodeDecodeError`; swallowing that
as "no reply" makes every `Runtime.evaluate` look like it never ran.

**The first evaluates on a new tab lose their replies.** While the renderer
swaps execution contexts the reply never comes. Measured: ~33 s of warm-up on a
fresh target, then 0.5 s per call. Fail fast (6 s) and retry immediately — a
long wait per attempt turns this into minutes of apparent hang, and an
unbounded wait produced a 14-minute freeze. Reuse one tab.

**Long idles kill the socket.** A `settle()` that leaves the connection
untouched for minutes gets dropped by Chrome, and the browser stays perfectly
healthy while the Python client raises
`WebSocketConnectionClosedException` mid-post. Reconnect on send.

A `js()` that returns `None` on failure is the root of a whole class of false
conclusions — two separate rounds concluded "the click did nothing" when the
real problem was a lost reply. Return a distinguishable error marker and check
it at every call site.

## Dead ends, so they are not re-tried

- `execCommand('insertText')` — returns false, inserts nothing.
- `textContent = t` plus `beforeinput`/`input` events — text appears and
  verifies, but Draft's state never sees it and the button stays disabled.
- `computer_use set_value` — the AX tree exposes the editor as `AXTextArea`,
  and setting its value changes the DOM, but the button stays disabled and a
  post went out as the single character `e`. Real OS keystrokes also cannot
  send CJK: a 159-character Chinese post delivered `0 of 159`.
- React internals — the composer's `__reactProps$` has `handlers: []` at every
  depth, `__reactFiber$` carries only click handlers, and a breadth-first walk
  of 13,764 nodes finds no input handler. The production build is minified, so
  the component names that would identify Draft are stripped.
- `Input.dispatchKeyEvent` with `commands: ["paste"]`, and `pbcopy` — both hang
  or insert nothing here.
- The restored-draft pool was once thought to be server-side and unclearable.
  That was wrong. The drafts are X's own, restored into the composer by X, and
  the whole problem is avoided by never clearing and never racing the box.

## Guardrails

- Never drive the composer while the user has their own drafts open, unless the
  box is empty or already holds exactly the intended text. A mistimed click
  publishes somebody's unfinished tweet — that is what happened once here
  (`2105508309361217688`, a stray `e`, since deleted).
- Never claim a post happened without the timeline read-back.
- Never close or reuse the user's tabs to "clean up".
- Never read credentials. Do not put cookies, tokens or a Client Secret in the
  conversation; write them as `[REDACTED]`.

## Deleting a post

The same single tab, no navigation: open the status, the article's `caret`
button, 删除 in the menu, 删除 in the confirmation dialog. Verify the article is
gone before moving on. The user may prefer to do this by hand.

## The alternative, and when it is better

`xurl` posts through the official API: fast, retryable, and it cannot touch the
browser, the drafts, or the profile. It needs the user to register an app once
(pasting a Client Secret, which the agent cannot do). When a run is long, the
draft pool is rotating, or the user wants the posts queued rather than typed,
that is the better tool — reach for it rather than fighting the composer.

## Scripts

| Script | Purpose |
|---|---|
| `scripts/cdp.py` | CDP client: control-frame handling, retrying `js()`, auto-reconnect on send, `set_port()`, `close_composition()`. |
| `scripts/selftest.py` | Verifies the client before trusting it. **Run this first.** |
| `scripts/bench.py` | Measures evaluate latency, to tell warm-up from a real stall. |
| `scripts/publish.py` | The publisher. `--post N` reads the box and posts only on an exact match; `--go` clicks. `--show` prints the copy, `--tabs` the X tabs. |
| `scripts/top_of_timeline.py` | Reads the newest posts off the profile with their ids and text. This is the verification step — run it after every post. |

`publish.py` takes its copy from `x_copy_long.json` next to it. It opens
nothing, navigates nowhere, clears nothing, and never touches the mouse or the
OS focus; the tab must already be on `x.com/compose/post`.

```bash
# once, and only if no instance is up
bash ~/.agents/skills/software-development/chrome-real-profile-launch/scripts/run.sh \
  --headed --port 9240 --fresh --no-tab

python3 scripts/publish.py 9240 --show            # read the copy first
python3 scripts/publish.py 9240 --post 0          # type and verify, no click
python3 scripts/publish.py 9240 --post 0 --go     # click
python3 scripts/top_of_timeline.py 9240           # confirm it landed

# a different set of posts
X_COPY=/path/to/other.json python3 scripts/publish.py 9240 --post 0 --go
```

The copy defaults to `scripts/x_copy_example.json` next to the script, which is
the set that was actually published. Replace it, or point `X_COPY` elsewhere;
the content is yours, not the skill's.

`selftest.py` earns its place: on its first run it reported `close_tab` as
broken when the check's own arithmetic was wrong, and it flagged a "slow"
client that was really just doing its warm-up.
