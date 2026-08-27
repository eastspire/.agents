# euv renderer + signal lifecycle patterns (2026-08-24 PR#21)

> Verified patterns + pitfalls from PR#21
> (https://github.com/euv-dev/euv/pull/21) — three performance /
> correctness fixes on the renderer + signal lifecycle. Use this as the
> reference when:
>
> - Adding a new SPA-sweep / orphan-heap-reclamation function to
>   `Signal<T>`.
> - Optimizing a hot path that lives inside `dispatch_delegated_event`
>   or `Renderer::patch_*`.
> - Writing `#[wasm_bindgen_test]` cases that exercise real DOM mutation
>   (not the pure-Rust diff algorithm).

## 1. SPA orphan heap reclamation — narrow async race, NOT a TypeId-wide registry scan

**First instinct when asked to "reclaim `Box<SignalInner<T>>` heap
allocations left parked after the source signal deactivated"**: scan
the whole `SIGNAL_INNER_REGISTRY`, match each address by
`TypeId::of::<T>()`, free the matching `alive == false` ones. **This
is a big architectural change** (registry becomes `HashMap<usize,
TypeId>`) and the actual production invariant is already handled
synchronously.

**The real orphan invariant is much narrower:**

1. `Signal::deactivate` atomically does:
   - (a) remove self from every bridge's dep set in `BridgeRefsCell`;
   - (b) if dep set empty AND bridge not in registry → free bridge heap;
   - (c) remove bridge entry from `BridgeRefsCell`.
2. `Signal::<String>::clear_listeners` removes the bridge from
   `SIGNAL_INNER_REGISTRY` but does NOT free the heap — it waits for
   the source's `deactivate` to confirm no stale listener still
   captures the bridge address by `move`.
3. The orphan case left after (1)+(2): bridge was DOM-detached first
   (`clear_listeners` ran, bridge out of registry), source deactivates
   later (or never does, for long-lived SPA top-level signals).
   Between those two events the bridge sits parked in
   `BridgeRefsCell` with an empty dep set.

**Correct sweep API** — `Signal::<String>::try_reclaim_inactive(max_freed)`:

- Scan `BridgeRefsCell` (NOT the registry) for entries whose dep set is
  empty AND whose address is not in `SIGNAL_INNER_REGISTRY`.
- Free the matching `Box<SignalInner<String>>` heap.
- No `TypeId` needed — the orphan invariant already restricts to
  bridges whose `SignalInner<T>` type matches `T` of the sweep
  function (in practice `T = String` for DOM text/attr bridges).

**Wrong sign that you over-designed:** if your sweep requires upgrading
`SIGNAL_INNER_REGISTRY` from `HashSet<usize>` to `HashMap<usize,
TypeId>` or scanning the whole registry with `TypeId::of::<T>()`
filter, you've over-scoped. The fix is to narrow the sweep target to
`BridgeRefsCell`.

**Test pattern** (orphan state is constructed manually): production
never produces "empty dep set + bridge still in BridgeRefsCell"
because `deactivate` is atomic. To exercise the sweep in tests,
construct it by hand:

```rust
BridgeRefsCell::track(bridge_addr, source.get_inner());
// Manually empty the dep set WITHOUT removing the bridge entry —
// mimics source.deactivate doing step (a) but skipping step (b).
BridgeRefsCell::map_mut()
    .get_mut(&bridge_addr).unwrap()
    .remove(&source.get_inner());
Signal::<String>::clear_listeners(bridge_addr);
// Now: dep set empty, bridge not in registry, bridge still in
// BridgeRefsCell — orphan invariant.
let freed = Signal::<String>::try_reclaim_inactive(usize::MAX);
assert_eq!(freed, 1);
```

## 2. HookContext::switch_arm is the natural reclamation point

When wiring the sweep (or any opportunistic cleanup hook) to the
Signal lifecycle, do **NOT** call it from inside `Signal::deactivate`
itself — that creates a recursion (deactivate → sweep → mutate
BridgeRefsCell → which depends on Signal state → could trigger another
deactivate via cleanup queue) AND burns CPU on every signal-set cycle
even when no cleanup is needed.

**The right integration point is `HookContext::switch_arm`** — the
function that drains the cleanup queue after a `match` arm transition.
At that moment:

- Every cleanup callback in the queue has just run its
  `Signal::deactivate` on signals owned by the torn-down hook context.
- Any bridge whose source WAS one of those signals AND whose DOM
  element was detached BEFORE the deactivate is now an orphan (empty
  dep set, not in registry).
- `switch_arm` is the natural collection moment for those allocations.

```rust
pub fn switch_arm(&mut self, changed: usize) {
    let cleanups: Vec<Box<dyn FnOnce()>>;
    { /* ... drain cleanups ... */ }
    for cleanup in cleanups { cleanup(); }
    // After the queue runs, sweep orphans the deactivated bridges
    // left behind.
    let _freed: usize =
        Signal::<String>::try_reclaim_inactive(usize::MAX);
    self.reset_index();
}
```

The `_freed` return value is intentionally discarded — the call is
opportunistic, not load-bearing. Failing to reclaim this frame defers
to the next; it never blocks the UI.

## 3. dispatch_delegated_event ancestor-walk cap — disjoint from NON_BUBBLING_EVENTS

For high-frequency events (mousemove / touchmove / pointermove / wheel),
capping the ancestor walk depth in `dispatch_delegated_event` saves
~3.6ms of CPU per second per pointer event on a typical 30-deep DOM
(each `get_attribute` JS-boundary call is ~1µs on Chrome).

**The list gating the depth cap MUST be disjoint from
`NON_BUBBLING_EVENTS`** — an event that doesn't bubble can never reach
`dispatch_delegated_event` in the first place (it gets attached
directly to the target element, see `is_non_bubbling` /
`NON_BUBBLING_EVENTS` definition). Adding a non-bubbling event to the
high-frequency list silently disables its dispatch (the ancestor walk
never happens because `delegation` is never called for non-bubbling
events) and is invisible until someone tests the disabled case.

**The trap**: `scroll` is non-bubbling per W3C DOM Level 3 — do NOT
add it to the high-frequency cap list. The list should contain only
bubbling events whose handlers are locality-preserving:

```rust
pub(crate) const HIGH_FREQUENCY_EVENTS: [&str; 5] = [
    "mousemove", "mousewheel", "pointermove", "touchmove", "wheel",
];
// scroll is in NON_BUBBLING_EVENTS, NOT here.
```

**Detection**: a single `#[test]` that asserts the two lists are
disjoint catches the trap immediately:

```rust
for hf in HIGH_FREQUENCY_EVENTS.iter() {
    assert!(
        !NON_BUBBLING_EVENTS.contains(hf),
        "{} is in both lists — cannot be window-delegated, so the \
         depth cap is irrelevant",
        hf,
    );
}
```

**Capture `max_depth` once at registration, not per event**:
`delegation(event_name)` computes `max_depth` once based on
`HIGH_FREQUENCY_EVENTS.contains(event_name)` and captures it in the
window-level closure. Per-event recomputation wastes CPU on the hot
path.

```rust
let max_depth: usize = if HIGH_FREQUENCY_EVENTS.contains(&event_name) {
    MAX_ANCESTOR_DEPTH_FOR_HIGH_FREQ
} else {
    usize::MAX
};
let closure: Closure<dyn FnMut(Event)> = Closure::wrap(Box::new(move |event: Event| {
    Self::dispatch_delegated_event(&event, event_name, max_depth);
}));
```

## 4. wasm_bindgen_test for DOM mutation — fingerprint attributes as fault injection

When testing that a DOM diff/patch implementation reuses DOM nodes
rather than recreating them, you can't easily mock the patch path —
you have to drive a real render and inspect the resulting
`childNodes` list. But "are these the SAME nodes?" is hard to verify
directly because `NodeList` returns live `Node` handles.

**The fingerprint-attribute trick**: stamp a DOM attribute that the
patcher never reads (e.g. `data-stamp="stamp-0"`) on each child
BEFORE the second render. After the patched render, check which
indices now carry which stamps:

- If keyed reorder `[a, b, c] → [c, a, b]` results in stamps
  `[stamp-2, stamp-0, stamp-1]` (the stamps follow the ORIGINAL
  0,1,2 order), then the patcher MOVED the existing DOM nodes.
- If stamps are `[stamp-0, stamp-1, stamp-2]` (re-issued in render
  order), the patcher destroyed and recreated them.

Same trick works for the `patch_attributes` stable-value no-op test:
stamp `data-sentinel="alive"` between two renders where the patched
attribute has the same value. After the second render, if the sentinel
survives, the stable-value skip is firing. If the sentinel was wiped,
the patcher is re-setAttribute'ing every render and burning a JS
boundary for nothing.

```rust
#[wasm_bindgen_test]
fn keyed_reorder_preserves_dom_node_identity() {
    // ... render [a, b, c] keyed ...
    for i in 0..list.length() {
        el.set_attribute("data-stamp", &format!("stamp-{i}"));
    }
    // ... re-render with [c, a, b] ...
    let after: NodeList = root.child_nodes();
    let stamps: Vec<String> = (0..after.length())
        .map(|i| after.get(i)
            .and_then(|n| n.dyn_ref::<Element>().cloned())
            .and_then(|el| el.get_attribute("data-stamp"))
            .unwrap_or_default())
        .collect();
    // Element at index 0 (id=c) was originally at index 2 (stamp-2).
    assert_eq!(stamps, vec!["stamp-2", "stamp-0", "stamp-1"]);
}
```

The fingerprint attribute must be one the patcher never reads (i.e.
not in its diff table), so the patcher doesn't strip or rewrite it.
`data-*` attributes are safe by convention.

## 5. `document.body()` returns `Option<HtmlElement>` not `Option<Element>`

This bites in every `wasm_bindgen_test` that needs to mount a test
container into `<body>`:

```rust
// ❌ E0308: mismatched types — Option<HtmlElement> is not Option<Element>
let body = document.body().expect("body");
let _: Result<web_sys::Node, JsValue> =
    body.append_child(&div);

// ✅ Coerce via .into()
let body: web_sys::HtmlElement = document.body().expect("body");
let body_node: web_sys::Node = body.into();
let _: Result<web_sys::Node, JsValue> = body_node.append_child(&div);
```

`Element::remove()` returns `()` not `Result<(), JsValue>`, so don't
wrap it in a `Result<(), JsValue>` assignment:

```rust
// ❌ E0308: expected Result<(), JsValue>, found ()
let _: Result<(), JsValue> = root.remove();
// ✅
root.remove();
```

## 6. Pub(crate) re-export across sibling submodules — `pub use *` ≠ private `use *`

euv-core is built on `pub use {app::*, event::*, noderef::*,
reactive::*, vdom::*}` in `lib.rs`. The `pub use *` re-exports the
**pub** items of each submodule; **private `use std::panic::catch_unwind;`
in lib.rs does NOT propagate** to submodules via `use super::*;` (a
private `use` stays crate-private even when re-exported through a
glob).

But **`pub(crate)` items DO propagate** to sibling submodules. When
`Signal::<String>::try_reclaim_inactive` (a `pub(crate)` function)
needed to be called from `core/src/reactive/hook/impl.rs`, the call
worked via `Signal::<String>::try_reclaim_inactive(...)` after the
`use super::*;` in hook/impl.rs resolved `Signal` from the reactive
re-export — no explicit `crate::reactive::signal::Signal` path
needed.

The asymmetry to remember:

| Path | Resolves to | Reaches sibling submodule's `pub(crate)` items? |
|---|---|---|
| `pub use mod::TypeName;` | `mod::TypeName` | Yes, `pub(crate)` visible |
| `use mod::TypeName;` (private) | `mod::TypeName` | Yes, but the re-export via glob doesn't propagate |
| `use mod::fn_name;` | `mod::fn_name` (if `pub`) | No — macros and `pub fn` need explicit re-export |
| `#[macro_use] extern crate mod;` | `mod!` macro | Yes, **macros are textually scoped** |

## 7. Test-pattern: 5-key validation matrix for orphan reclamation

For any SPA-sweep / reclamation function, the test matrix must
include ALL five orthogonal cases — not just the happy path:

| Case | Setup | Expected `freed` |
|---|---|---|
| No orphans | (no bridges created) | 0 |
| Zero cap | `try_reclaim_inactive(0)` | 0 (short-circuit) |
| Canonical orphan | `track + manually_empty_dep_set + clear_listeners` | 1 |
| Bridge still in registry | `track + DON'T clear_listeners` | 0 (UAF guard) |
| Bridge with live source | `track + clear_listeners + DON'T empty dep set` | 0 (UAF guard) |
| Multiple orphans, capped sweep | two orphans + `max_freed=1` | 1 + 1 (across two calls) |
| Idempotent | sweep twice | `freed=1` then `freed=0` |

The "bridge still in registry" case is the most important — it
prevents freeing a bridge whose DOM element is still attached. The
"bridge with live source" case prevents freeing a bridge whose
source signal still has a `subscribe` closure capturing the address.

## 8. Production caller resolution — `#[allow(dead_code)]` is not an option

After adding `try_reclaim_inactive` and tests for it, `cargo check
-p euv-core` reported:

```
warning: associated function `try_reclaim_inactive` is never used
   --> core/src/reactive/signal/impl.rs:550:19
```

This is the audit-pitfalls §23 / §17 problem (any non-dependency
`#[allow]` is forbidden). **Resolution**: wire the function to a
production caller. For `try_reclaim_inactive`, the natural caller is
`HookContext::switch_arm` (see §2 above). For other "added but
unused" functions, find the integration point in the framework
(rarely the new function itself — usually a cleanup queue drain or
a frame boundary) and add a single call site.

## 9. PR commit separation: 4 commits for 3 user-stated optimizations

User asked for 3 optimizations. The natural split was 4 commits:

1. `perf(signal): add SPA reclamation for orphan bridge signals` — the
   function itself, no caller.
2. `perf(renderer): cap ancestor walk depth for high-frequency events`
   — the const + the closure capture.
3. `test+feat: native tests for SPA sweep and high-frequency event cap`
   — tests + integration into `switch_arm` (resolves the
   `dead_code` warning from commit 1).
5. `test(renderer): browser-side wasm_bindgen_test for keyed diff and
   attribute alignment` — wasm tests for the renderer patch paths.

Why split: each commit is independently verifiable; the
`dead_code` warning is naturally resolved by commit 3; the PR
reviewer can see the production code change (commits 1+2) before the
tests (commit 3) and the optional browser tests (commit 4) come last
as a separate review unit.

## Reference: actual PR#21 patch layout

```
perf/renderer-and-signal-2026-08-24 branch
├── 2e18e21 perf(signal): add SPA reclamation for orphan bridge signals
│   └── core/src/reactive/signal/impl.rs                +83/-2
├── 2ea95c8 perf(renderer): cap ancestor walk depth for high-frequency events
│   ├── core/src/renderer/registry/const.rs             +40/-2
│   └── core/src/renderer/registry/impl.rs              +36/-0
├── 9d21725 test+feat: native tests for SPA sweep and high-frequency event cap
│   ├── core/src/renderer/registry/const.rs             +3/-2   (dropped scroll)
│   ├── core/src/reactive/signal/impl.rs                +14 (switch_arm integration)
│   ├── core/src/reactive/hook/impl.rs                  +16
│   ├── core/src/tests/renderer_const/fn.rs             +75
│   └── core/src/tests/signal/fn.rs                     +184
└── 5d07b89 test(renderer): browser-side wasm_bindgen_test for keyed diff and attribute alignment
    └── core/src/tests/keyed_diff/fn.rs                 +408

Total: 4 commits, 8 files, +843/-6, 14 new native tests + 6 wasm tests
```

PR URL: https://github.com/euv-dev/euv/pull/21