---
name: x-post-via-browser
description: "Use when posting to X/Twitter through the user's logged-in browser. The one path that works, and the four things that raise a dialog."
version: 3.0.0
author: local
license: MIT
platforms: [macos, linux]
metadata:
  hermes:
    tags: [twitter, x, posting, cdp, browser-automation, real-profile]
    related_skills: [chrome-real-profile-launch, chrome-devtools-protocol, xurl]
---

# Posting to X from the user's logged-in browser

Verified 2026-10-01 on a Premium account. Four long posts of 608–1060
characters published and verified, then a 27-post series published on a timer.

## The path

One tab, already open on x.com. Nothing navigates, nothing clears, nothing
touches the mouse.

1. `python3 scripts/publish.py <port> --post N` — types, compares, does not click.
2. Read the line it prints. `match=True` and `urls_ok=True`, or it stops.
3. `--go` to click.
4. `python3 scripts/verify_post.py <port> <status_id> <copy.json> N` — proves it.

X empties the composer itself after a post, so the next run finds it empty and
types into it. That is the whole loop.

## Never navigate, never clear

**No `location.assign`, no `Page.reload`, no `Page.navigate`, no second tab.**
Every page load makes the user confirm it in their UI. If the composer is not
open, click the control already on screen — `[data-testid="SideNav_NewTweetButton"]`,
`a[href*="/compose/post"]`, `[data-testid="appTabBarPostBtn"]` — which opens it
in place.

**Never empty the composer.** Clearing, reloading, navigating and Escape all
raise Chrome's own dialog, 「系统可能不会保存您所做的更改」, and that modal then
blocks every later CDP call until the user dismisses it. X sets no
`onbeforeunload` handler (`window.onbeforeunload === null`); the dialog is
Chrome's, caused by an IME composition left open on a contenteditable.

So the flow is read-only about the box: **read it; type only into an empty one;
if it already holds exactly the requested post, post it as it stands; if it
holds anything else, leave it and report.** There is no retry that does not
involve clearing, so a failure here is a stop, not a loop.

End every run with `close_composition("")`. A composition left open is what
makes Chrome claim the page holds unsaved input on the next unload.

**Never take the mouse or the keyboard.** No `Page.bringToFront`, no
`Input.dispatchMouseEvent`, no OS clicks, no `pbcopy`/`pbpaste`. Focus is
`el.focus()` inside the page; the user's pointer and OS focus never move.

## One insertText for the whole post, URL included

2500 characters land in no time, newlines and all. The URL is not special to
the editor — it is just text, and it goes in the same call.

Everything else was tried and measured to break the text:

| Tried | What happened |
|---|---|
| `imeSetComposition` for the URL | strands the URL's first character in the body — the editor reads `…edition。h` against a source of `…` |
| committing it with a second `insertText` | the committed string arrives already formed, so X has nothing to linkify; plain text, no `<a>` |
| pasting the URL (`commands:["paste"]`) | X folds the separator into the host — the sentence comes back as `https://\ncrates.io` |
| typing the URL per character | X linkifies mid-stream and drops the rest (`https://github.c` survived) |
| clearing first, then typing | 4–24 characters survive, and a later reload raises the dialog |

## The editor has two nodes, and one of them is a decoy

Two elements carry `data-testid="tweetTextarea_0"`. One is real — its `class`
contains `public-DraftEditor-content` and it holds the text; the other is an
empty duplicate. `querySelector` returns whichever is first in document order,
and that changes between renders. This alone produced writes that vanished and
a click that published a single stray character. Take the **taller visible**
one, and refuse to act if it did not take focus.

`[data-testid="tweetText"]` is a decoy — a display layer whose `textContent`
goes stale. Never write to it. On the timeline it is also **clipped**: it holds
204 characters of a 462-character post with no "show more" control, so reading
it reports a correct post as truncated.

**The raw length lies.** X's Draft editor keeps hidden text nodes of its own,
so it reports 860 against an 859-character source on a post that matches
character for character. Gate on the normalised compare, never on length.

## X linkifies anything dotted, not just URLs

A bare `crates.io` in the body became a `t.co` shortener, and the span X
replaced then read back as a line break — the sentence split in two and **two
broken posts shipped** before this was caught. `publish.py` now refuses any
copy carrying a dotted token that is not one of the URLs it intends, before a
character is typed. Write "crates io" in the copy.

## Verifying

`verify_post.py` proves three things at once, and each one exists because
without it a check produced a false verdict:

- **The author.** Matching a status id found a stranger's post sitting in the
  same feed — the id was real, the text was real, and "my post landed" was
  wrong. `whose_posts.py` lists what is on screen split by author.
- **The visible text against the source PREFIX.** `tweetText` is clipped, so a
  full character compare reports good posts as broken.
- **The link card.** A `t.co` href never contains the source URL, so the link
  is proved by the card X rendered from it, which names the repository.

`CLICKED` proves nothing. The publisher's own text compare proves the composer
held the right characters; only the timeline read proves it was published.

## Launching: headed, and through the local proxy

```bash
bash ~/.agents/skills/software-development/chrome-real-profile-launch/scripts/run.sh \
  --headed --port 9240 --fresh --no-tab
```

`run.sh` probes 7897/7890/7891/8080/10809/1080 and passes `--proxy-server` for
the first that answers. This is not optional on this machine. Without it a
browser launched with its own `--user-data-dir` cannot complete a TLS
handshake: DNS resolves, the TCP connection opens, then the handshake is cut —
`curl` reports `SSL_ERROR_SYSCALL`, Chrome reports `net_error -100`
(ERR_CONNECTION_CLOSED). The daily browser works because Clash Verge Rev
routes it through a TUN interface, which a separate user-data-dir does not get.
It looks like a crash and is not; Crashpad's pending directory is empty and no
crash report is written. **Check the log for `net_error -100` before
concluding anything died.**

`--fresh` drops the scratch profile and re-copies, excluding the `Singleton*`
files.

## Do not inject to defeat headless detection

X blocks headless browsers; `--headed` is the answer. Injecting a spoofed
fingerprint to get past the detection is circumventing an access control, and
this skill does not do it. Driving the composer's own input path in a browser
the user is logged into is a different thing from impersonating a human client
to the server.

## The button, and why "the button never enabled" is usually a wrong answer

X mounts `tweetButtonInline` for the inline composer and does not reliably
mount `tweetButton` at all. A lookup that requires `tweetButton` finds nothing
on a composer whose button is right there and enabled — which reads as "the
button never enabled" and silently drops a post whose text matched exactly.
Accept either; prefer the primary one.

## Two CDP client bugs that cost hours

Both are silent. `scripts/cdp.py` handles them; use it rather than a
hand-rolled socket.

**WebSocket control frames are not JSON.** opcodes 8/9/10 (close/ping/pong) and
2 (binary) share the framing but not the payload; check `b1 & 0x0F` before
decoding. Parsing a ping as JSON raises `UnicodeDecodeError`, and swallowing
that as "no reply" makes every `Runtime.evaluate` look like it never ran.

**The first evaluates on a new tab lose their replies.** While the renderer
swaps execution contexts the reply never comes — measured ~33 s of warm-up on a
fresh target, then 0.5 s per call. Fail fast and retry immediately; a long wait
per attempt turns this into minutes of apparent hang.

**Long idles kill the socket.** A `settle()` that leaves the connection
untouched for minutes gets dropped by Chrome, and the browser stays healthy
while the client raises `WebSocketConnectionClosedException` mid-post. Reconnect
on send.

A `js()` that returns `None` on failure is the root of a whole class of false
conclusions — two separate rounds concluded "the click did nothing" when the
real problem was a lost reply. It returns a distinguishable error marker, and
every call site checks it.

## Dead ends, so they are not re-tried

- `execCommand('insertText')` — returns false, inserts nothing.
- `textContent = t` plus `beforeinput`/`input` events — text appears and
  verifies, but Draft's state never sees it and the button stays disabled.
- `computer_use set_value` — the AX tree exposes the editor as `AXTextArea`,
  and setting its value changes the DOM, but the button stays disabled and a
  post went out as the single character `e` (`2105508309361217688`, since
  deleted). Real OS keystrokes also cannot send CJK: a 159-character Chinese
  post delivered `0 of 159`.
- React internals — the composer's `__reactProps$` has `handlers: []` at every
  depth, `__reactFiber$` carries only click handlers, and a breadth-first walk
  of 13,764 nodes finds no input handler. The production build is minified, so
  the component names that would identify Draft are stripped.
- The restored-draft pool was once thought to be server-side and unclearable.
  That was wrong. The drafts are X's own, restored into the composer by X, and
  the whole problem is avoided by never clearing and never racing the box.

## Guardrails

- Never drive the composer while the user has their own drafts open, unless the
  box is empty or already holds exactly the intended text. A mistimed click
  publishes somebody's unfinished tweet — that is what happened once here
  (`2105508309361217688`).
- Never claim a post happened without the timeline read-back.
- Never close or reuse the user's tabs to "clean up".
- Never read credentials. Do not put cookies, tokens or a Client Secret in the
  conversation; write them as `[REDACTED]`.

## Scripts

| Script | Purpose |
|---|---|
| `scripts/cdp.py` | CDP client: control frames, retrying `js()`, auto-reconnect, `close_composition()`. **No `new_tab()`** — a client that offers the call is a client that gets used. |
| `scripts/publish.py` | The publisher. `--show` the copy, `--tabs` the X tab, `--post N` type and compare, `--go` click. |
| `scripts/verify_post.py` | Proves one post landed: author, text prefix, link card. |
| `scripts/whose_posts.py` | What is on screen, split by author. |
| `scripts/run_ctares_tick.py` | Idempotent queue runner — one crate per invocation, for a cron series. |
| `scripts/verify_no_unsafe_posting.py` | The commit gate. `--self-test` proves every rule fires. |

```bash
# once, and only if no instance is up
bash ~/.agents/skills/software-development/chrome-real-profile-launch/scripts/run.sh \
  --headed --port 9240 --fresh --no-tab

python3 scripts/publish.py 9240 --show            # read the copy first
python3 scripts/publish.py 9240 --post 0          # type and compare, no click
python3 scripts/publish.py 9240 --post 0 --go     # click
python3 scripts/whose_posts.py 9240              # find the status id
python3 scripts/verify_post.py 9240 <sid> x_copy_example.json 0

X_COPY=/path/to/other.json python3 scripts/publish.py 9240 --post 0 --go
```

The copy defaults to `scripts/x_copy_example.json` next to the script — posts
that were actually published. Replace it or point `X_COPY` elsewhere; the
content is yours, not the skill's.

## The gate is registered, not just written

`verify_no_unsafe_posting.py` runs from the **global pre-commit hook**
(`~/.git-hooks/pre-commit`, installed via `core.hooksPath`), before the Rust
detection, so it applies to every repo — including the skills repo, which the
existing hook skips for having no `Cargo.toml`. A rule that lives only in this
document is a rule the next person breaks without knowing why; that has
happened to every rule on this list.

| Rule | What it stops |
|---|---|
| `no-page-load` | `location.assign`, `Page.reload`, `Page.navigate`, `new_tab`, `Target.createTarget` |
| `no-clearing` | `clear(c)`, `execCommand('delete'/'selectAll')`, a Backspace loop |
| `no-open-ime` | `imeSetComposition` with nothing that commits it |
| `no-mouse-keyboard` | `Page.bringToFront`, `Input.dispatchMouseEvent`, `bring_to_front`, `click_at_xy` |
| `no-clipboard` | `pbcopy`, `pbpaste`, a paste key event |

It tokenizes the source instead of regexing raw text, so prose that *mentions*
a banned call (this document's own notes do) is not a violation while a real
call is, and line numbers are true. `--self-test` runs twelve violating
fixtures and three clean ones and asserts each rule fires on its own, because a
gate never shown to fail is indistinguishable from no gate.

It caught a real violation on first run: `top_of_timeline.py` opened a new tab
on every verification, so the verification step broke the rule it existed to
confirm.

## Deleting a post

The same single tab, no navigation: open the status, the article's `caret`
button, 删除 in the menu, 删除 in the confirmation dialog. Verify the article is
gone. The user may prefer to do this by hand.

## The alternative, and when it is better

`xurl` posts through the official API: fast, retryable, and it cannot touch the
browser, the drafts, or the profile. It needs the user to register an app once
(pasting a Client Secret, which the agent cannot do). When a run is long, the
draft pool is rotating, or the user wants posts queued rather than typed, that
is the better tool — reach for it rather than fighting the composer.
