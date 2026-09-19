# euv reactive `if` arm-swap drops event-handler re-bind

Verified across example timer page (Stopwatch + Countdown)
against euv master `adb21ab2` and `911a63d5` (0.24.1 / 0.24.4),
both release builds (`wasm-pack build --release` + `wasm-opt`).

## Symptom (UI-level)

A page renders Start and Pause as two `euv_button` widgets
inside a reactive `if { !running } { ButtonStart } else
{ ButtonPause }` branch. Initial mount shows Start. Click Start:
the button text flips to Pause, the timer ticks (Start handler
fired, `running.set(true)` propagated). Click Pause: **nothing
changes** — button text stays Pause, timer keeps ticking (Pause
handler never fired).

Same shape as the timer bug, but the diagnosis generalizes to
any `euv_*` widget whose `onclick: <closure>` differs across the
two arms of a reactive conditional: the new arm's closure is
built fresh, but the registry slot for that `data-euv-id` keeps
the old closure from initial mount.

## Root cause (code-level, two cooperating bugs)

Both bugs live in `core/src/`. Without fixing both, `patch_attributes`
silently skips the per-attribute walk that would otherwise call
`attach_event_listener` and rebind the slot.

### Bug 1 — `AttributeValue::Event` PartialEq always returns true

`core/src/vdom/attribute/impl.rs`:

```rust
impl PartialEq for AttributeValue {
    fn eq(&self, other: &Self) -> bool {
        match (self, other) {
            // ...
            (Self::Event(_), Self::Event(_)) => true,   // <-- always equal
            // ...
        }
    }
}
```

Comment in the code says "re-binding is handled by the handler
registry", but the registry only re-binds if
`attach_event_listener` is called for that element, which only
runs inside the per-attribute walk that bug 2 short-circuits
away.

### Bug 2 — `patch_attributes` fast-path shortcuts the whole walk

`core/src/renderer/render/impl.rs`:

```rust
fn patch_attributes(...) {
    if old_attrs == new_attrs {
        return;                  // <-- shortcuts the whole walk
    }
    for new_attr in new_attrs {
        match new_attr.get_value() {
            AttributeValue::Event(handler) => {
                if !already_attached {
                    self.attach_event_listener(element, handler);
                }
            }
            // ...
        }
    }
}
```

Because bug 1 says any two `Event` values are equal, `old_attrs
== new_attrs` is `true` whenever the element has an event handler
that didn't change. After an `if` arm-swap, the element's
`data-euv-id` is reused, the old handler slot still holds the
original closure, and the new closure never gets attached.

## Frame-level fix attempted in this session (verified cargo-clean, runtime unverified)

Commit `77aaa089` on `fix/event-attr-partialeq` branch made both
changes:

```rust
// core/src/vdom/attribute/impl.rs
(Self::Event(_), Self::Event(_)) => false,   // was: true

// core/src/renderer/render/impl.rs
fn patch_attributes(...) {
    if old_attrs == new_attrs && !new_attrs.iter().any(|a|
        matches!(a.get_value(), AttributeValue::Event(_))
    ) {
        return;
    }
    // ...
}
```

`cargo check --workspace` and `cargo clippy --workspace` both
pass. But running the patched wasm in chromium still showed the
bug — clicked Start flipped the label and started ticking,
clicked Pause did nothing. Two possibilities:

- `wasm-opt` release builds strip the `attach_event_listener`
  log instrumentation I tried to add (`web_sys::window().set_title`,
  `body.set_attribute("data-debug", ...)` — both stripped in the
  release artifact, see "Diagnostic recipe" below).
- A different code path entirely is responsible for the broken
  re-bind (e.g. `DynamicNode::setup_dynamic_node` registers a
  re-render callback that calls `renderer_mut.render_full_replace`
  on arm-swap, which goes through `unwrap_component_owned` +
  `create_dom_node` rather than `patch_node`, so the patch
  path never runs at all).

The branch was abandoned because the working example-layer
workaround (below) shipped as PR #223 and verified end-to-end.
The framework-level investigation is unfinished — a future
session picking this up should start from
`Renderer::render` (`core/src/renderer/render/impl.rs:76`) and
trace whether the arm-swap path goes through `render_full_replace`
or `patch_node` for the euv_button wrapper.

## Example-layer workaround (verified, shipped as PR #223)

Collapse the Start/Pause pair into a single `<button>` element
(not `euv_button`) with a stable toggle handler. The handler is
built once in the hook layer, reads `running` at click time, and
dispatches to start or pause. The label flips via a reactive text
node `if { !running } { "Start" } else { "Pause" }`, which the
renderer patches in place rather than replacing the button.

```rust
// hook layer — toggle closure, built once per render but stable
// identity across renders because we never replace the slot
pub(crate) fn stopwatch_on_start(state: UseStopwatch) -> Option<Rc<dyn Fn(Event)>> {
    Some(Rc::new(move |_: Event| {
        if state.get_running().get() {
            stopwatch_on_pause_inner(state);
        } else {
            stopwatch_on_start_inner(state);
        }
    }))
}

// view layer — single element, no euv_button wrapper
button {
    class: c_euv_button_primary_md()
    onclick: stopwatch_on_start(stopwatch)
    if { !stopwatch.get_running().get() } { "Start" } else { "Pause" }
}
```

Three reasons this works around the bug:

1. **No reactive `if { ButtonA } else { ButtonB }`** — the button
   element is in a fixed position in the vdom tree, never
   replaced. Its `data-euv-id` is stable across renders.
2. **Handler identity is stable across renders** — the
   `Rc<dyn Fn(Event)>` is captured once per render, and since
   the button is in a fixed slot, `attach_event_listener` is
   only ever called once (at mount). No re-bind, no bug.
3. **Label flip is just text-node patching** — the `if { ... }
   else { ... }` inside the button produces a text-node change,
   which is the cheapest possible patch (`patch_text` in
   `core/src/renderer/render/impl.rs:169`).

Verified locally with headless chromium (see "Diagnostic recipe"
below):

- Stopwatch Start click → button text flips to Pause, ticks 0→3
- Stopwatch Pause click → button text flips to Start, holds at 3
  (no further ticks)
- Countdown Start click → button text flips to Pause, counts
  60→57
- Countdown Pause click → button text flips to Start, holds at 57

## Related pitfall: timing-page counter row alignment

After fixing the timer page, the user iterated on the timing page
counter row three times — PR #222 (move text below input),
PR #225 (pad to align with input content area, weight 500), PR
#227 (drop padding, weight 400, align to card edge). The lesson
is captured in `css-edge-cases` §8: after 2 rounds of micro-tuning
on the same element's position or alignment, the design question
is unsettled. Stop and ask the user to commit to a direction
(continue iterating, or drop the element entirely) before
opening the 3rd PR. The timing counter landed on "align to card
edge with normal weight" — which would have shipped in one PR
if asked up front.

## Diagnostic recipe: verify any euv example page via chromium + Python websockets

curl alone is not enough to verify wasm-only behaviour — it
returns the bytes, doesn't run them. Headless chromium with
remote-debugging-port + Python `websockets` library gives full
CDP access: evaluate JS in the page, capture screenshots,
subscribe to console + exception events, dispatch synthetic
clicks.

This is the recipe that finally pinpointed the bug after
several rounds of "the rule is there but the click doesn't
fire". Three details matter:

### 1. `chromium` binary on this VM is `ungoogled-chromium`

```bash
/usr/bin/ungoogled-chromium \
    --headless --disable-gpu --no-sandbox \
    --remote-debugging-port=9123 \
    --user-data-dir=/tmp/chrome-euv-test \
    --hide-scrollbars \
    --window-size=1280,800 \
    "http://127.0.0.1:8123/index.html#/timer"
```

`which chromium` returns nothing — only `ungoogled-chromium`. The
binary must be invoked by full path.

### 2. `web_sys::console::log_1` / `set_title` / `body.set_attribute` are stripped by `wasm-opt` in release builds

If you need to verify a fix actually runs in wasm, do NOT
instrument the rust code with `console.log`, `set_title`, or
`document.body.set_attribute`. wasm-opt release builds will
DCE these side effects even when the string literals are
preserved in the binary. Verify via the page DOM instead:

```python
import json, asyncio, websockets, urllib.request

tabs = json.loads(urllib.request.urlopen(
    'http://127.0.0.1:9123/json').read())
ws_url = [t for t in tabs
          if '127.0.0.1:8123' in t.get('url','')][0]['webSocketDebuggerUrl']

async def main():
    async with websockets.connect(ws_url, max_size=10_000_000) as ws:
        msg_id = [0]
        async def call(method, params=None):
            msg_id[0] += 1
            await ws.send(json.dumps({'id': msg_id[0],
                                      'method': method,
                                      'params': params or {}}))
            while True:
                msg = json.loads(await ws.recv())
                if msg.get('id') == msg_id[0]:
                    return msg.get('result')
        # Runtime.evaluate to inspect state
        r = await call('Runtime.evaluate', {
            'expression': 'document.title',
            'returnByValue': True})
        return r['result']['value']

print(asyncio.run(main()))
```

For `wasm-pack build --debug` (without wasm-opt), instrumentation
DOES survive — but that's 5-10x slower than release. Reserve
debug builds for dev iteration, not CI.

### 3. wasm-pack output naming gotcha — `www/pkg/euv.js` vs `www/pkg/euv_example.js`

After `wasm-pack build --out-dir www/pkg --out-name euv_example`,
`www/pkg/` contains:

- `euv_example.js` — the actual app entry that exports `main()`
- `euv_example_bg.wasm` — the actual app wasm
- `euv.js` — **a stale orphan from a previous build** that
  imports `./euv_bg.js` (which doesn't exist in this build) and
  references an outdated inline JS hash (e.g. `euv-core-ec7cb25e91e723a2`
  vs the current `euv-core-e7914052a740d51e`)

`www/index.html` imports `./pkg/euv.js`, which is the orphan.
After deleting `euv.js` + `euv_bg.wasm` from `pkg/` and editing
`www/index.html` to import `./pkg/euv_example.js` instead, the
new wasm actually loads and renders. Without this fix, the
served wasm is stale even after a clean rebuild, and the page
appears to ignore all your changes.

```bash
cd /root/github/euv-dev/euv/example/www/pkg
rm -f euv.js euv_bg.wasm
sed -i 's|/pkg/euv\\.js|/pkg/euv_example.js|' ../index.html
```

Verify with:

```bash
grep -c 'new_class_name' pkg/euv_example_bg.wasm   # new code is there
grep -c 'new_class_name' /tmp/dl.wasm             # served wasm matches
```

## References

- Code locations verified: `core/src/vdom/attribute/impl.rs`
  (PartialEq), `core/src/renderer/render/impl.rs` (patch_attributes),
  `core/src/renderer/registry/impl.rs` (dispatch_delegated_event),
  `core/src/reactive/hook/impl.rs` (DynamicNode re-render).
- Branch `fix/event-attr-partialeq` (commit `77aaa089`)
  contains the framework-level fix attempt — cargo-clean but
  runtime-unverified, abandoned in favor of the example-layer
  workaround.
- PR #223 (`248f1137` on master) shipped the example-layer
  workaround. PR #222 (`f07865fd`) shipped the first timing
  counter row below input. PR #225 (`58b64bcf`) shipped the
  padding + weight 500 alignment. PR #227 (`248f1137`) shipped
  the no-padding, weight 400, card-edge alignment final.
- Related: `euv-standards` §17 (euv release bump + `euv fmt` +
  PR + `sync_workspace_version` propagation pattern).
