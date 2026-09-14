# euv clickable `<div>` inside scrollable container is broken on iOS Safari

Verified against euv master `8cbd5c1a` (0.24.4); fix shipped as
PR #231 → 0.24.5.

## Symptom (UI-level)

Open any page with the framework `c_tab_bar` / `c_tab_item_*` on
iOS Safari — `/conditional` "Tab Switching" card, `/game_2d`,
`/game_3d`, `/keep_alive`. Tap a tab. Nothing happens. No state
change, no panel switch, no console error. On Android Chrome
or desktop Safari the very same tab clicks switch the panel
correctly.

iOS-only. Android and PC unaffected. `euv_button` is also
unaffected (those are real `<button>` elements — iOS treats
them as natively interactive and dispatches click reliably).

## Root cause (two cooperating iOS WebKit behaviours)

### Cause 1 — iOS synthetic-click suppression on non-button elements

When `touch-action` is the default `auto`, iOS WebKit treats
every tap as a candidate scroll gesture. After `touchend`, iOS
looks at the touch trajectory and decides: did the finger
move? If yes (or if the element lives inside a scrollable
container), iOS classifies the gesture as "scroll begin" and
**does not dispatch the synthetic `click`** that the framework
relies on. Chrome and Firefox have no equivalent
disambiguation on touch input, which is why Android/PC work.

The framework's `Registry::delegation("click", ...)` listens on
`window` and walks up the DOM tree from the event target
looking for `data-euv-id` ancestors. If iOS never dispatches
the synthetic click, the delegated listener never fires and the
handler slot is never looked up. Same code path, no handler call.

### Cause 2 — iOS text-selection bubble intercepts the tap on `<div>` text

Even when iOS does dispatch click, `c_tab_item_*` elements are
rendered with plain text content (`"Info"`, `"Settings"`, etc.).
iOS treats them as a selection target and pops the text-selection
bubble on long-press / drag, which can swallow or delay the
click event. With `user-select: text` (default), tap-and-hold for
~400ms is enough to suppress click entirely.

## Fix shipped in PR #231

Two CSS properties added to `c_tab_item_active` and
`c_tab_item_inactive` in `ui/src/style/class/fn.rs`:

```css
touch-action: manipulation;       /* and iOS: no double-tap-zoom wait,
                                     no scroll-gesture disambiguation —
                                     synthetic click fires immediately
                                     after touchend */
user-select: none;                /* and iOS: suppress the text-selection
                                     bubble that would otherwise swallow
                                     the tap on the <div> text content */
-webkit-user-select: none;        /* legacy iOS prefix */
```

`touch-action: manipulation` tells iOS: this element only
responds to taps and panning. The browser no longer waits to see
if the gesture is a double-tap zoom, and no longer tries to
disambiguate between tap and scroll-init. The synthetic click
is dispatched immediately after `touchend`. `user-select: none`
suppresses the text-selection bubble.

Properties are scoped to the tab item classes — the scrollable
container `c_app_main { overflow: auto }` is untouched, so
existing scroll behaviour is preserved.

## When to apply this fix (generalisation)

The same fix applies to **any custom clickable element** that is
a `<div>` / `<span>` (not `<button>` / `<a href>`) and lives
inside a scrollable container on iOS Safari. Search for
`onclick:` paired with bare `<div>` / `<span>` tags in example
code:

```bash
grep -nE '^\s*(div|span) \{' example/src/page/*/view/fn.rs \
  | grep -B1 'onclick:'
```

If you find non-`<button>` clickable elements with `onclick:`
in example code, they need the same `touch-action:
manipulation` + `user-select: none` treatment to work on iOS.
Real `<button>` elements via `euv_button` are unaffected because
iOS treats them as natively interactive.

## What NOT to do

- **Do not** set `touch-action: manipulation` on the scrollable
  container `c_app_main` itself — that disables touch panning
  on the page. Apply it to the clickable leaf element.
- **Do not** try to detect iOS in JavaScript and conditionally
  bind both `click` + `touchend` — the delegated handler
  already runs on `click`, the issue is that iOS suppresses
  the synthetic click. Adding a `touchend` listener inside
  the example code would cause every tap to fire twice on
  Android/PC.
- **Do not** switch from `<div>` to `<button>` everywhere as a
  "fix" — `c_tab_item_active` uses `background: var!(accent)`
  with `border-bottom: 2px solid var!(accent)`, which is a
  non-button visual presentation. Forcing `<button>` would
  require resetting browser default button styles in every
  state, which is more brittle than two CSS properties on the
  existing `<div>` class.

## Diagnostic recipe

If a future page has a clickable `<div>` that doesn't respond
on iOS:

1. Open the page in iOS Safari (or Safari Technology Preview
   on macOS, which is closer to iOS WebKit than desktop Chrome).
2. Tap the element — observe nothing happens.
3. Inspect the element with Safari Web Inspector: confirm it
   has `data-euv-id` attribute and an `onclick` is bound via
   the framework's `attach_event_listener` (look in
   `core/src/renderer/render/impl.rs:1546`).
4. Add `touch-action: manipulation; user-select: none;` to the
   element's class. Reload. Tap — should now work.

If the element is inside a fixed-position overlay or fullscreen
container, the cause is usually different — check whether the
overlay itself has `pointer-events: none` (which would block
all clicks, not just iOS) before assuming the iOS WebKit trap.

## Related references

- `euv-standards/references/euv-event-handler-rerender-pitfall.md`
  — different bug, same family: framework event-handler
  re-binding on reactive `if` arm-swap. That bug fires on ALL
  platforms (not iOS-only); this one fires only on iOS.
- `euv-standards` §12 坑表 — look for "patch_attributes"
  and "AttributeValue::Event" for the related
  cross-platform event-handler-rebind bug.