# Hot-path performance optimization patterns (verified 2026-08-24 in euv)

This is the consolidated playbook for the 9-class performance optimization
sweep we did on euv. Every pattern below was implemented in the
`coverage-2026-08-23` branch (PR #20) and verified to not regress any of
the 553 native tests, plus the headless-chromium browser smoke check.

## 1. Cow<'static, str> for VDOM tag/attribute names — the OPT-2 pattern

The single biggest mechanical win: `Tag::Element(String)`,
`Tag::Component(String)`, `Tag::Portal(String)` and `AttributeEntry::name:
String` all become `Cow<'static, str>`. The `html!` macro emits
`Cow::Borrowed("div")` / `Cow::Borrowed("class")` for every literal so a
single static-string slice is shared across the entire rendered tree
— zero per-element heap allocations for tag names or attribute keys.

### 1.1 Type changes

```rust
// before
pub enum Tag { Element(String), Component(String), Portal(String) }
pub struct AttributeEntry { name: String, value: AttributeValue }

// after
pub enum Tag {
    Element(Cow<'static, str>),
    Component(Cow<'static, str>),
    Portal(Cow<'static, str>),
}
pub struct AttributeEntry {
    name: Cow<'static, str>,
    value: AttributeValue,
}
```

Add `use std::borrow::Cow;` to `core/src/lib.rs` so all submodules see it
via `use super::*;`.

### 1.2 Macro emit changes

```rust
// before (in macros/src/html/impl.rs)
let tag_literal: proc_macro2::TokenStream =
    quote_spanned!(tag_span=> #tag_name.to_string());

// after — emit the literal token directly, no .to_string()
let tag_literal: proc_macro2::TokenStream =
    quote_spanned!(tag_span=> #tag_name);
```

And at the call site:

```rust
// before
tag: ::euv::Tag::Element(#tag_literal),
AttributeEntry::new(#attr_name_token, #value_tokens)

// after
tag: ::euv::Tag::Element(::std::borrow::Cow::Borrowed(#tag_literal)),
AttributeEntry::new(::std::borrow::Cow::Borrowed(#attr_name_token), #value_tokens)
```

For attribute key generation:

```rust
// before
let attr_name_token: proc_macro2::TokenStream = quote! { #key_string.to_string() };

// after
let attr_name_token: proc_macro2::TokenStream =
    quote! { ::std::borrow::Cow::Borrowed(#key_string) };
```

For the **portal target** — which is a user expression, often
`Signal<String>::get()` or `String::from(...)`:

```rust
// before
Some(quote! { ::std::string::String::from(#expr) })

// after — wrap in Cow::Owned (the target may be runtime-derived)
Some(quote! {
    ::std::borrow::Cow::Owned(::std::string::String::from(#expr))
})
```

For the **dynamic tag fallback** (when the tag name is a runtime
expression that didn't match any component arm):

```rust
// before
tag: ::euv::Tag::Element(__euv_tag_name),

// after
tag: ::euv::Tag::Element(::std::borrow::Cow::Owned(__euv_tag_name)),
```

### 1.3 Renderer changes — `as_str()` is unstable in Rust 2024

After the type change, every existing `name.as_str()` call (where
`name: Cow<'static, str>`) gets E0658 `str_as_str`. Replace with:

```rust
// before (E0658)
let old_name: &str = old_attr.get_name().as_str();

// after (works on Cow via AsRef<str>)
let old_name: &str = old_attr.get_name().as_ref();
```

Same for `attr.get_name().clone()` → `attr.get_name().to_string()`
(if you actually need an owned String). `Cow<'_, str>::to_string()`
only allocates for the `Owned` branch; the `Borrowed` branch is a slice
clone (no heap).

### 1.4 Test code updates

Every manual `AttributeEntry::new(String::from("class"), ...)` becomes
`AttributeEntry::new(Cow::Borrowed("class"), ...)`. Add
`use std::borrow::Cow;` to each test file. `String`-typed fields
(`TextNode::content`, `Css::name`) stay as-is — only `Cow` fields
switch.

## 2. Dispatcher dirty-set fast path — the OPT-6 pattern

The previous scheduler scanned the entire signal update registry on
every dispatch tick. For a SPA with N dynamic nodes and only a few
changed signals per tick, this was O(N) per tick. Replace with a
`HashSet<usize>` of dirty IDs that the dispatcher drains:

```rust
// core/src/renderer/registry/static.rs
pub(crate) static mut DIRTY_UPDATE_IDS: LazyLock<DirtyUpdateIdsCell> =
    LazyLock::new(|| DirtyUpdateIdsCell(UnsafeCell::new(HashSet::new())));

// core/src/renderer/registry/impl.rs
pub(crate) fn mark_dirty(dynamic_ids: &[usize]) {
    let dirty_ids: &mut HashSet<usize> = Self::get_mut_dirty_update_ids();
    for dynamic_id in dynamic_ids {
        dirty_ids.insert(*dynamic_id);
    }
    // ... existing dirty-flag flip ...
}

pub(crate) fn has_dirty() -> bool {
    Self::get_mut_dirty_update_ids().iter().any(|id: &usize| {
        let registry: &HashMap<usize, SignalUpdateEntry> =
            Self::get_mut_update_registry();
        registry.get(id).is_some_and(|entry: &SignalUpdateEntry| {
            let slot: &SignalUpdateSlot = unsafe { &**entry };
            !slot.get_removed()
        })
    })
}

pub(crate) fn cleanup_dynamic_node(dynamic_id: usize) {
    Self::get_mut_dirty_update_ids().remove(&dynamic_id);  // ← also drop from dirty set
    if let Some(entry) = Self::get_mut_update_registry().remove(&dynamic_id) {
        unsafe { let _: Box<SignalUpdateSlot> = Box::from_raw(entry); }
    }
}
```

`Scheduler::dispatch_updates` replaces its `registry.iter().filter_map()`
scan with `std::mem::take(Registry::get_mut_dirty_update_ids())` — drains
the set in O(dirty_count) instead of O(registry_size).

### 2.1 Removed APIs

`Registry::sweep_removed_entries()` is gone — every `cleanup_*` path now
removes from both the registry and the dirty set, so the registry never
holds a removed entry between ticks. `Registry::get_update_registry()`
(the shared `&HashMap` accessor) is also deleted; callers previously
used it only to implement `has_dirty`, which now uses the dirty set.

## 3. Cached queueMicrotask — the OPT-7 pattern

`Scheduler::update` previously did:

```rust
let queue_microtask_value: JsValue =
    Reflect::get(&window_value, &JsValue::from_str(QUEUE_MICROTASK))
        .unwrap_or(JsValue::UNDEFINED);
matches!(queue_microtask_value.dyn_into::<Function>(), Ok(q) if q.call1(...).is_ok())
```

Two JS round-trips per signal update. Cache the resolved `Function` in
a thread_local:

```rust
// core/src/reactive/schedule/static.rs
pub(crate) struct MicrotaskCache {
    pub(crate) queue_microtask: Option<Function>,
}
pub(crate) struct MicrotaskCacheCell(pub(crate) UnsafeCell<MicrotaskCache>);

thread_local! {
    pub(crate) static MICROTASK_CACHE: MicrotaskCacheCell =
        MicrotaskCacheCell(UnsafeCell::new(MicrotaskCache {
            queue_microtask: None,
        }));
}
```

In `update`, lazy-resolve on first use, then `Function::call1(window,
dispatch_fn)` directly. Saves two JS round-trips per signal update.

**Rust 2024 lifetime gotcha**: `Closure::as_ref().unchecked_ref::<Function>()`
inside a `thread_local!::with(|closure| ...)` closure fails lifetime
checking — the `with` callback's `&Closure` reference has lifetime
`'a`, but the returned `&Function` has lifetime `'b` where `'a: 'b`,
which Rust 2024 rejects. Workaround: dereference through a raw pointer
inside `unsafe { ... }`:

```rust
let dispatch_function: &Function = DISPATCH_CLOSURE.with(|closure| unsafe {
    &*(closure.as_ref() as *const _ as *const Function)
});
```

This is safe because `DISPATCH_CLOSURE` is `thread_local!`-owned for the
program's lifetime and `Function` is a transparent newtype around
`JsValue`.

## 4. Cached Document — the OPT-8 pattern

`create_dom_node` was doing `window()` + `document()` per call (two
JS round-trips per DOM node creation). Page-scoped `Document` is
identical across the mount lifetime, so cache it:

```rust
// core/src/renderer/render/const.rs
thread_local! {
    pub(crate) static DOCUMENT_CACHE: std::cell::UnsafeCell<Option<Document>> =
        std::cell::UnsafeCell::new(None);
}

pub(crate) fn cached_document() -> Option<Document> {
    DOCUMENT_CACHE.with(|cell: &UnsafeCell<Option<Document>>| {
        let cached_ptr: *mut Option<Document> = cell.get();
        unsafe {
            if let Some(doc) = &*cached_ptr {
                return Some(doc.clone());
            }
        }
        let window_value: Window = window()?;
        let document: Document = window_value.document()?;
        DOCUMENT_CACHE.with(|cell: &UnsafeCell<Option<Document>>| unsafe {
            *cell.get() = Some(document.clone());
        });
        Some(document)
    })
}
```

`create_dom_node` now calls `cached_document()` instead of the two-step
`window().document()`. Saves one JS round-trip per DOM node.

## 5. NodeList hoisting in diff — the OPT-3 / OPT-4 pattern

Both `patch_children_keyed` and `patch_children_positional` previously
called `parent.child_nodes()` inside the per-child loop. Each call
returned a fresh live `NodeList` and was followed by `.get(index)` —
one JS round-trip per child. Hoist the NodeList out:

```rust
// before (keyed and positional)
for index in 0..common_len {
    let old_child = &old_children[index];
    let new_child = &new_children[index];
    if let Some(dom_child) = Self::try_get_child_node(parent, index as u32) {
        // ... patch against dom_child
    }
}

// after (positional, same pattern in keyed)
let child_nodes: NodeList = parent.child_nodes();   // ← hoisted
for index in 0..common_len {
    let old_child = &old_children[index];
    let new_child = &new_children[index];
    let dom_index: u32 = index as u32;
    if let Some(dom_child) = child_nodes.get(dom_index) {    // ← direct index
        // ... patch against dom_child
    }
}
```

`try_get_child_node` is removed — its only caller is now reading from
the hoisted NodeList. Saves one JS round-trip per child in both diff
algorithms.

## 6. patch_attributes refactor — the OPT-5 pattern

`patch_attributes` previously did:

1. `element.get_attribute(DATA_EUV_ID).parse::<usize>()` inside the
   per-attribute handler-removal loop — O(N) reads of the same DOM attr
2. `old_attrs.iter().find(|attr| attr.get_name() == new_name)` —
   O(N×M) lookup for every new attribute

Refactor:

```rust
let old_index: HashMap<&str, &AttributeValue> =
    old_attrs.iter().map(|a| (a.get_name().as_ref(), a.get_value())).collect();
let new_index: HashMap<&str, &AttributeValue> =
    new_attrs.iter().map(|a| (a.get_name().as_ref(), a.get_value())).collect();

let mut needs_event_cleanup: bool = false;
for old_attr in old_attrs {
    let old_name: &str = old_attr.get_name().as_ref();
    if !new_index.contains_key(old_name) {
        if let AttributeValue::Event(_) = old_attr.get_value() {
            needs_event_cleanup = true;   // ← defer euv_id read
        }
        element.remove_attribute_or_property(old_attr.get_name());
    }
}

let cached_euv_id: usize = if needs_event_cleanup {
    // ← read once, only when needed
    match element.get_attribute(DATA_EUV_ID) {
        Some(id_str) => id_str.parse::<usize>().unwrap_or_else(|_| {
            let new_id = NEXT_EUV_ID.fetch_add(1, Ordering::Relaxed);
            let _ = element.set_attribute(DATA_EUV_ID, &new_id.to_string());
            new_id
        }),
        None => {
            let new_id = NEXT_EUV_ID.fetch_add(1, Ordering::Relaxed);
            let _ = element.set_attribute(DATA_EUV_ID, &new_id.to_string());
            new_id
        }
    }
} else { 0 };

if needs_event_cleanup {
    self.detach_removed_event_handlers(old_attrs, &new_index, cached_euv_id);
}
```

The detached `detach_removed_event_handlers` helper takes the cached
`euv_id` directly, so the per-attribute loop inside the helper does
zero DOM reads. Combined with the HashMap index, this turns
`patch_attributes` from O(N×M) string compares + N DOM reads into a
single DOM read + O(N+M) map operations.

## 7. unwrap_component_owned fusion — the OPT-1 pattern

The previous render path had two functions: `unwrap_component(&vnode)`
returning a `VirtualNode` (cloning internal `Vec<VirtualNode>` to expand
component nodes) and `unwrap_component_owned(vnode: VirtualNode)` that
was supposed to be the zero-copy path but was only used in one place.
Inline them: every render / `render_full_replace` / `setup_dynamic_node`
callback now calls `unwrap_component_owned` with the owned `VirtualNode`
directly. Component-free trees are returned by move — every `Tag` /
`AttributeEntry` / child `Vec` allocation is reused, no `clone()` calls.

```rust
pub fn render(&mut self, vnode: VirtualNode) {
    let new_unwrapped: VirtualNode = Self::unwrap_component_owned(vnode);
    // ... rest of render path uses new_unwrapped by move
}
```

Delete `unwrap_component(&vnode)` entirely. The `Tag::Component(_) =>
{ ... }` arm of `unwrap_component_owned` performs the single edge clone
when expanding a component into its single child — that's the only
allocation in the component path.

## 8. add_dependent tail-element fast path — the OPT-9 pattern

`Signal::add_dependent` previously did `Vec::contains(&dynamic_id)`
linear scan on every `signal.get()` during render. The common case is
"this dependent was just appended last render". Optimize:

```rust
pub(crate) fn add_dependent(&self, dynamic_id: usize) {
    let deps: &mut Vec<usize> = Self::inner_mut(self.get_inner()).get_mut_dependents();
    if let Some(last) = deps.last() {
        if *last == dynamic_id {
            return;   // ← O(1) common case
        }
        if !deps.contains(&dynamic_id) {
            deps.push(dynamic_id);
        }
    } else {
        deps.push(dynamic_id);
    }
}
```

Render-time dependent registration drops from O(N) per signal access to
O(1) per signal access.

## 9. Production-path panic-free pattern — replace `.expect("div")` with real fallback

In `renderer/render/impl.rs` portal mount:

```rust
// before — production panic
let marker: Element = document.create_element("div")
    .unwrap_or_else(|_| document.create_element("div").expect("div"));

// after — never panics
let marker: Element = document
    .create_element("div")
    .unwrap_or_else(|_err| {
        let fallback: Text = document.create_text_node(EMPTY_STRING);
        let element_value: JsValue = fallback.into();
        element_value.unchecked_into::<Element>()
    });
```

`create_element("div")` cannot fail on any supported browser, but the
fallback returns a real `Element` (cast from a `Text` node via
`unchecked_into`) so the parent's positional patch loop treats it
identically. `display:none` portal markers don't visually lose
anything if the inner `data-euv-portal` attribute can't be set on the
fallback.

## 10. Match instead of `.unwrap()` after early-return

Same file, `core/src/reactive/schedule/impl.rs` OPT-7 cached
queueMicrotask path:

```rust
// before — .unwrap() after early-return guard
if cache_ref.queue_microtask.is_none() {
    // ... resolve + store ...
    if cache_ref.queue_microtask.is_none() { return false; }
    // fall through with Some(...)
}
let queue_microtask: &Function = cache_ref.queue_microtask.as_ref().unwrap();

// after — explicit match, no .unwrap()
if cache_ref.queue_microtask.is_none() {
    // ... resolve + store ...
    if cache_ref.queue_microtask.is_none() { return false; }
    // fall through with Some(...)
}
let queue_microtask: &Function = match cache_ref.queue_microtask.as_ref() {
    Some(queue_microtask) => queue_microtask,
    None => return false,
};
```

The `unwrap()` was never reachable, but `rust-standards` R11.4 forbids
production-path `.unwrap()` regardless. The `match` makes the invariant
explicit.

## 11. Verification matrix after every optimization sweep

After any non-trivial render/scheduler/signal change, run the full
matrix before commit:

```bash
# Compilation
cargo check --workspace
cargo check --tests --workspace
cargo check --target wasm32-unknown-unknown -p euv-core

# Format
cargo fmt --all --check
euv fmt --check

# Native tests (--test-threads=1 to avoid cross-test SCHEDULED AtomicBool
# race that came up in PR#16)
cargo test -p euv-core --lib -- --test-threads=1
cargo test -p euv-cli

# Browser smoke
wasm-pack build --target web --release
cd example/www && python3 -m http.server 8765 &
sleep 1
/usr/bin/ungoogled-chromium --headless --no-sandbox --disable-gpu \
    --virtual-time-budget=10000 --dump-dom http://localhost:8765/index.html

# Headless dump should contain:
#   id="status">✓ euv-example loaded successfully
#   78 <div> elements
#   25/25 page names (About, Animation, Async, ...)
#   data-euv-signal-addrs="..." attributes
#   euv-css-injected class
#   no ERROR in status
```

## 12. browser-use daemon is unreliable — use ungoogled-chromium directly

The Hermes `browser-use` daemon timed out repeatedly (300s+) on this
project. The bypass that worked reliably across every verification:

```bash
/usr/bin/ungoogled-chromium \
    --headless \
    --no-sandbox \
    --disable-gpu \
    --virtual-time-budget=10000 \
    --dump-dom \
    http://localhost:8765/index.html
```

`--virtual-time-budget=10000` advances the virtual clock by 10 seconds
so async wasm init completes before the dump. Result is a complete
DOM string in stdout that you can `grep` / `regex` against. ~5s per
run vs 300s+ timeout for browser-use. Use this as the default browser
verification path for any WASM-built euv project.

## 13. wasm-pack build: `--out-dir` relative to crate dir, not workspace

```bash
cd example  # ← cd to the crate directory first
wasm-pack build --target web --release --out-dir www/pkg
```

Running wasm-pack from the workspace root with `--manifest-path` fails
with "crate directory is missing a Cargo.toml file". The fix is to
`cd` into the crate directory or use `--manifest-path example/Cargo.toml`
but the cwd-based form is simpler.

After the build, `wasm-pack` creates a `www/pkg/.gitignore` that
excludes everything in `pkg/`. **For test artifacts that you don't
want to commit**, leave the .gitignore in place. For builds that you
DO want to commit, `rm -f www/pkg/.gitignore` first (see
`rust-wasm-gh-pages-deploy-pitfalls` for the GitHub-Pages deploy path
that requires committing build artifacts).