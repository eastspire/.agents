# euv Signal: snapshot vs subscribe pattern (PR #174, 2026-09-07)

> Critical correction to `references/euv-demo-loading-and-rays.md` § "Bug 2 详解:euv fmt 自动 fix snapshot-vs-subscribe" —
> **euv fmt does NOT automatically rewrite `let x = signal.get(); if { !x }` into `if { !signal.get() }`.**
> That section's claim was incorrect. Verified empirically by reading the source of
> `euv-cli 0.13.6` (it has no signal-reactivity rewrite pass) and by the fact that
> PR #171 shipped with `let loaded = ...; if { !loaded }` still in master for **4
> days** before PR #174 fixed it manually.

## The bug pattern (real, recurring)

Any euv view fn that does this will silently break re-rendering on signal change:

```rust
fn lighting_canvas_tab(fullscreen: UseLightingFullscreen) -> VirtualNode {
    let state: UseLighting = use_lighting_state();
    let loaded: bool = state.get_loaded().get();   // ← snapshot into local
    let active: bool = state.get_active().get();   // ← snapshot into local
    ...
    html! {
        ...
        if { !loaded } {                           // ← re-renders check local bool, not signal
            canvas { id: LIGHTING_LOADING_CANVAS_ID ... }
        }
        ...
    }
}
```

When `state.get_loaded().set(true)` is called from a RAF callback 400 ms later,
the view does **not** re-render. The overlay canvas stays in the DOM at
`opacity=1` forever, even though the loop is alive and the main canvas is
actively rendering the scene behind it.

## What `euv fmt` actually does (and does NOT do)

`euv fmt` (v0.13.6):
- ✅ Expands `html!` / `class!` / `vars!` / `var!` / `#[component]` macro bodies and re-indents their internals.
- ✅ Reformats class! function-call chains and Component attribute order.
- ✅ Idempotent: running it twice produces zero diff.
- ❌ Does **NOT** rewrite `let x = state.get_X().get(); if { !x }` patterns.
- ❌ Does **NOT** track which locals are snapshot bindings of signals vs plain locals.

The mechanism for detecting snapshot bindings is fundamentally different from
syntactic formatting. `euv fmt` operates at the Rust AST + token-stream level;
it would need type info (which locals have type `Signal<T>` or derive from
`Signal::get()`) to do the rewrite. That's a clippy-level lint, not a
formatter.

## What does drive re-render correctly

`Signal::get()` does register the caller as a dependent **only inside a
DynamicNode render context** (euv-core sets `CURRENT_TRACKING_DYNAMIC_ID`
during render). Calling `.get()` outside that context (e.g. in a `Closure`
callback, in a `setTimeout` body, in a RAF frame) just reads the current
value — no subscription happens.

For the view fn to actually re-render on signal change, the `.get()` call
must happen **inline in the expression the view fn returns**, not in a local
bound before the `html!` invocation:

```rust
// ❌ BAD — local binding hides the dependency
let loaded: bool = state.get_loaded().get();
if { !loaded } { canvas { ... } }

// ✅ GOOD — signal read is in the expression the view tree cares about
if { !state.get_loaded().get() } { canvas { ... } }
```

This is the same pattern the WebGL and WebGPU tabs in the same page already
used. The Canvas 2D tab was the outlier.

## The fix that landed in PR #174

```diff
- let loaded: bool = state.get_loaded().get();
  let active: bool = state.get_active().get();
  ...
                          }
                      }
-                     if { !loaded } {
+                     if { !state.get_loaded().get() } {
                          canvas {
                              id: LIGHTING_LOADING_CANVAS_ID
                              class: c_game_loading_overlay()
                          }
                      }
```

The unused `let loaded` was also deleted (clippy caught `unused variable:
loaded` after the patch, with `light_cfg_canvas_tab` only used for the
`if { !loaded }` guard; the other Lighting tabs use `let loaded` because they
pass it to a status-text helper, so keep theirs).

## How to detect this pattern across a codebase

```bash
# Find every "let x = state.get_X().get();" + later use of x in if/match
grep -nE 'let [a-z_]+:\s*bool\s*=\s*state\.get_[a-z_]+\(\)\.get\(\)' \
  example/src/page/*/view/*.rs \
  example/src/page/*/hook/*.rs \
  example/src/component/*/view/*.rs
```

Each match is a candidate snapshot binding. For each, trace whether the
local is used in an `if {}` / `match {}` / `format!()` expression that lives
inside the returned `html!` tree. If yes, refactor to call the getter
inline.

For string-formatted locals (`let fps_display: String = format!("{:.1}", fps.get())`),
the situation is different — the local holds a derived string snapshot, not a
direct signal read. `fps.get()` inside `format!` does subscribe, but the
**resulting String** is what the view tree uses. So you DO want
`let fps_display = ...; fps_display` in view, and the subscription is
registered by the `fps.get()` call inside `format!`. Don't refactor those.

Rule of thumb: only the **boolean** snapshot pattern is dangerous. String /
numeric / struct locals derived from `signal.get()` inside `format!` or
arithmetic expressions are fine — the subscription is registered by the inner
`.get()` call.

## Empirical verification that overlay was the symptom (not loop_start)

The mistake I almost made (and didn't, after instrumenting) was concluding
the loop wasn't running because the loading overlay was still up. To
disambiguate: if FPS counter is ticking / canvas is rendering but the overlay
is still up, the bug is **view-side snapshot**, not **loop-side start**.

Diagnostic set (run all four; each rules out a hypothesis):

```js
// 1. Loop alive? FPS counter ticks?
setInterval(() => document.body.innerText.match(/FPS:\s*([\d.]+)/)?.[1], 200);

// 2. Main canvas has rendered pixels? (not stuck on first-frame black)
const c = document.getElementById('<page>-canvas');
const ctx = c.getContext('2d');
const d = ctx.getImageData(0, 0, c.width, c.height).data;
let nonBlack = 0;
for (let i = 0; i < d.length; i += 4) {
  if (0.299*d[i] + 0.587*d[i+1] + 0.114*d[i+2] > 8) nonBlack++;
}

// 3. Loading overlay still in DOM at opacity 1?
const overlay = document.getElementById('<page>-loading-canvas');
overlay && getComputedStyle(overlay).opacity;

// 4. Signal value actually true? (instrument via wasm console.log)
console.log // (added inside `lighting_set_loaded_delayed` closure)
//   "DEBUG: loaded.set(true) called, current=true"
```

If 1 + 2 = healthy but 3 = overlay still opacity 1 and 4 = signal is true,
the bug is **view fn snapshot**, exactly the pattern above.

## Why the bug took 4 days to surface

- PR #171 landed `let Some(loading_window) = window() else { return; };`
  early-return fix on 2026-09-07 04:17 UTC. That fix unblocked the RAF loop.
- Loop started running. `state.get_loaded().set(true)` was called ~400 ms
  later via `setTimeout`.
- View fn had `let loaded = state.get_loaded().get(); if { !loaded }` snapshot
  pattern. View never re-rendered in response to the set.
- Result: loop running, canvas rendering, FPS ticking, **but loading overlay
  still on top**. The user reported "Phong Lighting 2D tab 一直 loading 没展示画布".
- Initial diagnosis (mine) was "browser cache, hard refresh". It wasn't —
  the master HEAD had the right code, the symptom was in view fn.
- PR #174 added the live-getter `if { !state.get_loaded().get() }` and
  removed the unused `let loaded`. Verified end-to-end with Playwright:
  overlay removes within ~500 ms, main canvas continues rendering Phong
  spheres (FPS ≈ 47).

## Recommendations for next time

1. **Don't trust the "euv fmt auto-rewrite" myth.** That reference was
   wrong. If you see `let x = state.get_X().get()` followed by view use of
   `x`, fix it manually before submitting the PR.
2. **Snapshot detection is a clippy-level concern**, not a formatter
   concern. If we want it automatic, write a clippy lint
   (`euv_signal::signal_get_into_local_bool` or similar) that emits
   `signal_used_via_local_bool` and points at the fix.
3. **When a fix "didn't work", instrument before retrying.** I burned ~30
   minutes reasoning about the loop, the setTimeout closure, the
   `try_set` semantics, etc., before adding the four-line wasm-side
   `console.log` that showed `loaded.set(true)` was actually being called
   and the signal value was true. Five lines of `web_sys::console::log_1`
   would have cut that to two minutes.
4. **Compare sibling tabs that work.** The WebGL and WebGPU tabs in the
   same page used `if { !state.get_loaded().get() }` (live getter) and they
   were healthy. The Canvas 2D tab used `if { !loaded }` (snapshot) and it
   was broken. Side-by-side diffing would have flagged this within a minute.

## See also

- `references/euv-demo-loading-and-rays.md` § "Bug 1 详解" — for the
  `let-else` early-return pattern, which is the **other** reason a loading
  overlay never unmounts (separate fix, separate file).
- `euv-standards` § reactive signals — for the full reactive model.
