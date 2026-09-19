# euv Performance Audit Verification — master b108fa10

> Verified against `/root/github/euv-dev/euv` @ `b108fa10` (HEAD of master, 2026-09-10).
> Report baseline: `euv-perf-findings-0.20.6.md` (commit `83c4d39`).
>
> ## Merge state at b108fa10
> - ✅ PR #178 (`5918d907`) **MERGED**
> - ✅ PR #179 (`69ecc2d8`) **MERGED**
> - ❌ PR #180 (`1042d8b`, CHAR_SPACE &str const) **NOT MERGED** (separate branch)
> - ✅ PR #181 (`5f2396d1`, version bump 0.21.1) **MERGED**
> - Diff vs 83c4d39: `5918d907 + 69ecc2d8 + 5f2396d1 + b108fa10` (4 commits).
>
> ## Findings
> - **41 numbered items** (R1-R3, #1-#41) + 5 non-perf observations = **46 total**.
> - **CLOSED: 13** (R1, R2, R3, #3, #4, #12, #14, #17 [half], #18 [half], #22 [half], #31, #32, #38)
> - **OPEN: 33** (rest)
> - **REGRESSIONS: 0** (no items previously closed were re-broken)
>
> ---
>
> ## ✅ CLOSED (13 items)
>
> ### Closed by PR #178 (`5918d907`)
>
> | ID  | Finding | Closing evidence (current master) |
> |-----|---------|-----------------------------------|
> | R1  | `AttributeValue::PartialEq` missing StaticText/CssRef | `core/src/vdom/attribute/impl.rs:276-306` — now matches `(StaticText,StaticText)`, `(CssRef,CssRef)`, cross arms with Text/Css. |
> | R2  | `style: { color: "red" }` E0308 | `macros/src/html/fn.rs:1772-1815, 1831-1841` — wrapper points pass `#value` through. `prop_field_token` at `:2111-2118` handles Style by emitting `#value` (StaticText) for conditional / `.to_string()` for static. **Macro test added**: `macros/tests/html_static_style.rs:1-31`. |
> | R3  | OPT-13 over-detached mount | `core/src/renderer/render/fn.rs:66-72` — `is_connected()` gate returns early on detached parents. |
> | #3  | scheduler `current_time()` always 0.0 | `engine/src/scheduler/impl.rs:40-58` — Reflect then `unchecked_into::<Function>` + `call0(&performance)`. |
> | #4  | `LightingUniforms::lights` getter cloning Vec | `engine/src/lighting/struct.rs:62-63` — `#[get(pub(crate))]` (no `type(clone)`), returns `&Vec<Light>`. |
> | #12 | positional delete `last_child()` called twice | `core/src/renderer/render/impl.rs:628-642` — single `last_child()` call reused. |
> | #14 | Event handler unconditional re-attach | `core/src/renderer/render/impl.rs:296-315` — `Rc::ptr_eq` skip before `attach_event_listener`. |
> | #18 | 6× `join(&CHAR_SPACE.to_string())` (first pass: literal) | `core/src/vdom/attribute/impl.rs:129, 152, 186, 200, 683, 727` — all use `join(" ")`. **CHAR_SPACE const deleted from `core/src/vdom/attribute/const.rs`.** ⚠ PR #180 (1042d8b, restore as `&str` const) is OPEN on a separate branch and NOT yet in master. |
> | #32 | `SsaaCanvas::present()` calls `apply_quality` every frame | `engine/src/renderer/impl.rs:1260-1278` — `present()` only calls `clear_rect` + `draw_image`; quality set once in `enable_smoothing`. |
>
> ### Closed by PR #179 (`69ecc2d8`)
>
> | ID  | Finding | Closing evidence (current master) |
> |-----|---------|-----------------------------------|
> | #17 (half) | `Signal::with(FnOnce(&T))` added | `core/src/reactive/signal/impl.rs:99-114` — `with` exists. ⚠ `set()` at `:301-307` **still** clones `Vec<usize>` dependents via `get_dependents()` at `:284-286`. |
> | #22 (half) | i18n `t()` borrows via `Signal::with` | `ui/src/hook/i18n/impl.rs:117-141` — `t`/`locale_count`/`active_message_count` use `.with(...)`. ⚠ Messages **still** in Signal (`ui/src/hook/i18n/struct.rs:39: messages: Signal<HashMap<...>>`); full refactor to OnceLock/Rc deferred. |
> | #31 | `update_uniform_buffer` / `write_buffer` allocate JS typed arrays | `engine/src/renderer/impl.rs:3126` (Float32Array::view), `engine/src/renderer/impl.rs:3767` (Uint8Array::view). Both `unsafe { ...::view(data) }`. |
> | #38 | `SceneManager::update` clones `Option<String>` | `engine/src/scene/impl.rs:108-117` — borrows `try_get_current_scene_name()` + clones SceneRc. |
>
> ### Closed earlier (pre-PR #178/179 baseline)
>
> | ID | Finding | Status |
> |----|---------|--------|
> | (none of the explicitly numbered items closed by work older than #178/179 — all CLOSED items trace to #178 or #179) |
>
> ---
>
> ## ❌ OPEN (33 items)
>
> ### Tier 1: architecture-level (≥10× impact)
>
> #### #1 — Patch path lacks DomOp collection + batched commit
> - **Location**: `core/src/renderer/render/impl.rs:249-365` (`patch_attributes`), `:478-558` (keyed diff), `:599-643` (positional), `:162`/`599` (text set_text_content).
> - **Diff size**: large — new `commit.rs` module (200+ lines), `patch_*` signatures return `Vec<DomOp>`, glue-side changes.
> - **Type**: refactor (API touch).
> - **Risk**: medium-high — touches every render path; requires CDP regression (templates/cdp-mount-bench.py).
> - **Blockers**: needs JS glue call shape decision (single batch call per element? flush boundary?).
>
> #### #2 — Engine WebGPU full Reflect::get + from_str (partial via #179)
> - **Location**: 249 Reflect::get/set sites in `engine/src/renderer/impl.rs` alone (only ~10 use `cached_method_name`); ~94 Reflect::get total in engine/src.
> - **Diff size**: medium — `cached_method_name` helper exists (impl.rs:13-29); need to expand + add Function-level cache (1 helper + ~245 call-site swaps).
> - **Type**: refactor (no API touch, internal cache).
> - **Risk**: low for `cached_method_name` (already pattern-validated); medium for Function cache (needs thread_local Function map; correctness re: this binding).
> - **Blockers**: none for the from_str caching; Function-level needs binding model decision (call1 with explicit `this`).
>
> #### #5 — `Signal::create` allocates `Box<SignalInner>` per signal
> - **Location**: `core/src/reactive/signal/impl.rs:41-52` (`create`).
> - **Diff size**: medium — new slab/arena (~100 lines) + rewrite `SignalInner` storage.
> - **Type**: refactor (internal; signal API unchanged).
> - **Risk**: medium — touches core allocation pattern; needs stress test for cross-signal references.
> - **Blockers**: needs drop/reclamation design (currently uses BridgeRefsCell).
>
> #### #6 — Bridge signal chain (per-signal DOM bridge)
> - **Location**: `core/src/renderer/render/impl.rs:782-805` (attr signal), `:828-841` (InnerHtml), `:847-866` (text bridge), plus inner_html signal at `:820-835`.
> - **Diff size**: medium-large — rewrite to subscribe-closure-direct-DOM or new `register_attr_listener` typed API.
> - **Type**: refactor (touchy API — signal bridge is wired into renderer).
> - **Risk**: medium — needs CDP regression on signal-driven attribute updates.
> - **Blockers**: possibly needs design on HashMap<euv_id, Vec<usize>> (depends on #9).
>
> ### Tier 2: renderer per-element ops
>
> #### #7 — `track_signal_addr` N+1 write amplification
> - **Location**: `core/src/renderer/dom/impl.rs:172-181`.
> - **Diff size**: small — ~20 lines if combined with #9.
> - **Type**: refactor (internal).
> - **Risk**: low.
> - **Blockers**: tied to #9 (need Rust-side signal addr storage to eliminate DOM attribute).
>
> #### #8 — `dispatch_delegated_event` ancestor chain 2 JS per layer
> - **Location**: `core/src/renderer/registry/impl.rs:143-187` (per report; line numbers have drifted but pattern unchanged).
> - **Diff size**: medium — new JS glue fn for ancestor walk + euv_id callback; Rust side becomes single glue call per event.
> - **Type**: refactor (no public API change).
> - **Risk**: medium — JS glue changes affect event delegation correctness.
> - **Blockers**: needs glue-side design.
>
> #### #9 — `data-euv-signal-addrs` DOM attribute serialization
> - **Location**: write at `core/src/renderer/dom/impl.rs:172-181`; cleanup parse at `core/src/renderer/render/impl.rs:1214-1219`.
> - **Diff size**: small — add `HashMap<euv_id, Vec<usize>>` global, drop DOM attribute.
> - **Type**: refactor.
> - **Risk**: low — but affects all signal cleanup paths.
> - **Blockers**: none.
>
> #### #10 — `patch_attributes` builds 2 HashMaps per element per patch
> - **Location**: `core/src/renderer/render/impl.rs:255-262`.
> - **Diff size**: small — switch to linear scan for n<8 or reuse thread_local buffer.
> - **Type**: refactor.
> - **Risk**: low (linear scan degrades only when attrs >8).
> - **Blockers**: none.
>
> #### #11 — keyed diff lacks LIS
> - **Location**: `core/src/renderer/render/impl.rs:478-558` (keyed diff), HashMap+HashSet at `:489`/`:501`.
> - **Diff size**: medium — implement standard LIS (~50 lines); test on reorder workloads.
> - **Type**: refactor (no public API change).
> - **Risk**: medium — correctness on all reorder patterns; needs CDP regression.
> - **Blockers**: none.
>
> #### #13 — `cleanup_subtree` per-element 4+N JS crossings
> - **Location**: `core/src/renderer/render/impl.rs:1203-1233`.
> - **Diff size**: small-medium — replace with `query_selector_all("[data-euv-id],...")` 1 JS call.
> - **Type**: refactor.
> - **Risk**: low (one-shot cleanup path).
> - **Blockers**: none; combine with #9 for max benefit.
>
> #### #15 — `window_event_listener` Vec alloc + double lookup per event
> - **Location**: `core/src/renderer/registry/impl.rs:505-526`.
> - **Diff size**: small — in-place iteration (~10 lines).
> - **Type**: refactor.
> - **Risk**: low (window event path is well-isolated).
> - **Blockers**: none.
>
> #### #16 — `setup_dynamic_node` 3 Box allocations per dynamic mount
> - **Location**: `core/src/renderer/render/impl.rs:938, 944, 945` (Box<Renderer>, Box<usize>, Box<dyn FnMut>).
> - **Diff size**: small — combine renderer+arm into single Box (5-10 lines).
> - **Type**: refactor (internal allocation).
> - **Risk**: trivial.
> - **Blockers**: none.
>
> #### #19 — `try_reclaim_inactive` full scan + Vec alloc
> - **Location**: `core/src/reactive/signal/impl.rs:609-642`.
> - **Diff size**: small — drain small candidate queue (~15 lines).
> - **Type**: refactor.
> - **Risk**: low.
> - **Blockers**: none.
>
> #### #20 — merge_class/merge_style intermediate allocation chain
> - **Location**: `core/src/vdom/attribute/impl.rs:96-154` (merge_class), `:170-202` (merge_style).
> - **Diff size**: small — `String::with_capacity` direct-build + static &str borrow (~30 lines).
> - **Type**: refactor.
> - **Risk**: low.
> - **Blockers**: none.
>
> #### #21 — `VirtualNode::get_child_node` deep clones subtree
> - **Location**: `core/src/vdom/node/impl.rs:332-334` (`get_child_node`), `:271-280` (`try_get_child_node` → `children.clone()`).
> - **Diff size**: small — change to return `&[VirtualNode]` (5-10 lines + 12 ui component call-sites).
> - **Type**: refactor (API touch — return type changes).
> - **Risk**: low (call-sites are component bodies, all controlled).
> - **Blockers**: needs VirtualNode lifetime story; touch public API.
>
> ### Tier 2: UI / macros items
>
> #### #23 — vconsole per-render 3× filter + clone logs
> - **Location**: `ui/src/component/vconsole/hook/impl.rs:121-138` (`filter_entries`); callers at `ui/src/component/vconsole/view/fn.rs:219, 227, 232`.
> - **Diff size**: small-medium — computed cache + in-place append API (~30 lines).
> - **Type**: refactor.
> - **Risk**: low.
> - **Blockers**: none.
>
> #### #24 — virtual_list per-frame format! + NodeRef cache
> - **Location**: `ui/src/component/virtual_list/view/fn.rs:96-111` (format! calls); scroll handler at `ui/src/component/virtual_list/hook/impl.rs:33-37`.
> - **Diff size**: small — hoist height string + NodeRef cache for container (~15 lines).
> - **Type**: refactor.
> - **Risk**: low.
> - **Blockers**: none.
>
> #### #25 — touch hook 24 Reflect::get + from_str per event
> - **Location**: `ui/src/component/touch/hook/impl.rs:41-71, 130-160, 200+`.
> - **Diff size**: small — switch to web-sys Touch/TouchList typed getters (touchmove is hottest).
> - **Type**: refactor.
> - **Risk**: low.
> - **Blockers**: web-sys Touch feature flag.
>
> #### #26 — camera QR scan leaks Closure per tick
> - **Location**: `ui/src/component/camera/hook/impl.rs:259-289` (on_detected/on_scan_error Closure::wrap + forget per interval).
> - **Diff size**: small-medium — persistent Closure + interval reuse or async loop (~30 lines).
> - **Type**: bug-fix (memory leak).
> - **Risk**: low-medium (async timing changes).
> - **Blockers**: none.
>
> #### #27 — attr reactive if/match `.to_string()` per branch
> - **Location**: `macros/src/html/fn.rs:1508-1509, 1531-1534, 1567-1569`.
> - **Diff size**: small — emit `&'static str` via Cow for literal arms; or two-state Signal reuse.
> - **Type**: refactor (macro change, downstream consumers recompile).
> - **Risk**: low (compile-time only).
> - **Blockers**: doc vs code drift on `IntoReactiveString` (line 1481 comment); consider fixing comment too.
>
> #### #28 — parameterized class!/vars! re-creates Css per call
> - **Location**: `macros/src/class/impl.rs:390-396` (parameterized Css::new); `macros/src/var/impl.rs:118-124` (vars! format!).
> - **Diff size**: medium — global cache keyed by (name, param serialization) (~50 lines).
> - **Type**: refactor (macro + cache).
> - **Risk**: medium — cache eviction/memory.
> - **Blockers**: needs cache key serialization spec.
>
> #### #29 — literal TextNode allocates String per render
> - **Location**: `macros/src/html/impl.rs:428` (`#text.into()` → String).
> - **Diff size**: small — change `TextNode.content: String` → `Cow<'static, str>`, macro emits `Cow::Borrowed`.
> - **Type**: refactor (API touch — TextNode struct field).
> - **Risk**: low (callers use as_ref/clone pattern).
> - **Blockers**: TextNode struct change.
>
> #### #30 — markdown/navbar/sidebar/nav format! per render
> - **Location**: `ui/src/component/markdown/view/fn.rs:77, 146`; `navbar/view/fn.rs:49, 120`; `sidebar/view/fn.rs:78, 86, 96`; `nav/view/fn.rs:38, 43, 91`.
> - **Diff size**: small — hoist &str constants; reduce route_signal.get() clones.
> - **Type**: refactor.
> - **Risk**: trivial.
> - **Blockers**: none.
>
> ### Tier 2: engine
>
> #### #34 — `begin_render_pass_full` descriptor rebuilt every frame (partial via #179)
> - **Location**: `engine/src/renderer/impl.rs:2486+` (Object/Array allocation per frame); cached_method_name covers 9 sites but Object/Array itself is fresh.
> - **Diff size**: medium — descriptor cache + clear_value-only-mutate (~50 lines).
> - **Type**: refactor.
> - **Risk**: medium (descriptor caching needs to handle dynamic clear_value).
> - **Blockers**: design for invalidation when color/load/store op changes.
>
> #### #35 — `set_bind_group_with_dynamic_offsets` allocates JS Array per call
> - **Location**: `engine/src/renderer/impl.rs:5002-5022` and `:5043-5063` (compute variant).
> - **Diff size**: small — Uint32Array::view zero-copy (~10 lines × 2).
> - **Type**: refactor.
> - **Risk**: trivial (matches #31 pattern).
> - **Blockers**: none.
>
> #### #36 — VirtualNode children `Vec<VirtualNode>` no static sharing
> - **Location**: `core/src/vdom/node/enum.rs:63` (`children: Vec<VirtualNode>`); partial Eq at `core/src/vdom/node/impl.rs:112-158`.
> - **Diff size**: large — Rc<[VirtualNode]> in struct + macro emit changes + PartialEq rewrite.
> - **Type**: refactor (API touch — VirtualNode internals).
> - **Risk**: high (touches every vdom consumer).
> - **Blockers**: design decision on Rc vs Arc vs template-cloning; benchmark after R1 fix.
>
> #### #37 — for/inline-if children `Vec::new()` + push
> - **Location**: `macros/src/html/fn.rs:1228, 1281, 1315` (still emit `Vec::new()`); also `html/impl.rs:518-523`.
> - **Diff size**: small — `with_capacity(size_hint().0)` for for-loops (~5 lines × 3 sites).
> - **Type**: refactor.
> - **Risk**: trivial.
> - **Blockers**: none.
>
> #### #39 — input events use Reflect instead of typed getter
> - **Location**: `engine/src/input/impl.rs:15, 31, 60, 65` (code, mouse button, client_x, client_y).
> - **Diff size**: trivial — 4-line swap to web-sys typed getters.
> - **Type**: refactor.
> - **Risk**: trivial.
> - **Blockers**: web-sys feature flag (likely already enabled).
>
> #### #40 — DrawList batching broken by per-particle color
> - **Location**: `engine/src/renderer/impl.rs:670, 676, 701` (`Color::to_css(&color)` allocates String); particle `engine/src/particle/impl.rs:188-203`.
> - **Diff size**: medium — color quantization bucket OR sort-by-color pre-replay + use `write_css_rgba` (already at `:1035`).
> - **Type**: refactor.
> - **Risk**: medium (visual determinism).
> - **Blockers**: needs color bucket granularity decision.
>
> #### #41 — per-property signal rewrite
> - **Location**: `core/src/vdom/attribute/impl.rs:219` (`Registry::register_attr_listener`); entire attribute Signal system.
> - **Diff size**: very large — rewrite attribute reactive system.
> - **Type**: refactor (architectural).
> - **Risk**: high.
> - **Blockers**: API decision required; report defers indefinitely.
>
> ### Tier 3: tail items
>
> #### #33 (tail) — physics `grid.clear()` drops all cell Vec buffers
> - **Location**: `engine/src/spatial/impl.rs:88-90, 225-227` (still `cells.clear()`).
> - **Diff size**: small — `cells.values_mut().for_each(Vec::clear)` (~3 lines × 2).
> - **Type**: refactor.
> - **Risk**: trivial.
> - **Blockers**: none.
>
> #### #18 (tail) — CHAR_SPACE naming restored as `&str` const
> - **Location**: `core/src/vdom/attribute/const.rs` (CHAR_SPACE absent); `impl.rs:129, 152, 186, 200, 683, 727` use literal `" "`.
> - **Diff size**: trivial — add const + 6 call-site swaps. **Already drafted as PR #180** (`1042d8b4`); branch not yet merged.
> - **Type**: refactor (purely naming).
> - **Risk**: trivial.
> - **Blockers**: PR review.
>
> ---
>
> ## 🔵 NON-PERF OBSERVATIONS (4 items, all OPEN)
>
> ### NP-1 — SIGNAL_UPDATE_REGISTRY key space (NEXT_EUV_DYNAMIC_ID vs heap addr) lacks structural protection
> - **Location**: `core/src/renderer/registry/impl.rs:290` (`register_dynamic`) and `:310` (`register_attr_listener`); both share `SIGNAL_UPDATE_REGISTRY`.
> - **Diff size**: small — enum key or high-tag bit (~20 lines).
> - **Type**: refactor (internal registry key).
> - **Risk**: low.
> - **Blockers**: needs key encoding decision.
>
> ### NP-2 — euv-cli lacks wasm-opt step
> - **Location**: `cli/` (no wasm-opt in build/release pipeline).
> - **Diff size**: small-medium — add wasm-opt invocation to release path.
> - **Type**: additive (tooling).
> - **Risk**: low.
> - **Blockers**: none.
>
> ### NP-3 — NodeRef not cleared on unmount (correctness bug)
> - **Location**: `core/src/renderer/render/impl.rs:1179-1205` (`cleanup_subtree` has no NodeRef handling); mount at `:843` sets `node_ref.set(element_value)`.
> - **Diff size**: small — track NodeRefs in registry, clear on cleanup (~15 lines).
> - **Type**: bug-fix (correctness).
> - **Risk**: low.
> - **Blockers**: needs NodeRef enum/registry plumbing.
>
> ### NP-4 — Dead code shipped to wasm (diff_* fns, LruCache)
> - **Location**: `core/src/vdom/fn.rs:33, 53, 114` (`diff_children`/`diff_keyed`/`diff_positional`, only used by `core/tests/keyed`); `core/src/reactive/cache/` (only used by `core/tests/cache`).
> - **Diff size**: trivial — gate with `#[cfg(test)]` or wire to production (~5 lines).
> - **Type**: refactor (cfg gate).
> - **Risk**: trivial.
> - **Blockers**: none.
>
> ### NP-5 — `fc89f7a` commit message mislabels (PR #144 vs PR #146)
> - Historical only, not actionable in code.
> - **Status**: observation, not a fix.
>
> ---
>
> ## 📊 COUNTS
>
> | Bucket | Count | Items |
> |--------|-------|-------|
> | **Closed by PR #178** (`5918d907`) | **9** | R1, R2, R3, #3, #4, #12, #14, #18 (first pass), #32 |
> | **Closed by PR #179** (`69ecc2d8`) | **4 fully + 4 partial** | #17 (half), #22 (half), #31, #38, plus partial #2/#34 (cached_method_name scaffolding) |
> | **Closed by earlier work** | **0** | (no item closed before #178's window) |
> | **Open** | **33 numbered + 4 non-perf = 37** | #1, #2 (rest), #5, #6, #7, #8, #9, #10, #11, #13, #15, #16, #17 (set tail), #18 (PR #180 pending), #19, #20, #21, #22 (full), #23-#30, #33 (grid tail), #34 (descriptor), #35, #36, #37, #39, #40, #41 |
> | **Regressions** | **0** | (no previously closed item re-broken) |
> | **PR #180 still OPEN** | **1** | #18 CHAR_SPACE &str const (1042d8b on separate branch, not in master) |
>
> ### PR #178 closed items (per git diff scope: 10 files, +115/-57):
> - **R1, R2, R3** (regression fixes; R2 also added html_static_style.rs test)
> - **#3** (scheduler current_time)
> - **#4** (lighting getter)
> - **#12** (last_child reuse)
> - **#14** (Rc::ptr_eq)
> - **#18** (join → " " literal; CHAR_SPACE deleted)
> - **#32** (SsaaCanvas present)
>
> ### PR #179 closed items (per git diff scope: 13 files, +194/-59):
> - **#17** `Signal::with` only (set() dependents clone NOT done)
> - **#22** borrow via with only (messages-table move to OnceLock NOT done)
> - **#31** Float32Array/Uint8Array view
> - **#38** SceneManager Option<String> clone
> - Partial scaffolding for **#2** (`cached_method_name`) and **#34** (9 sites in begin_render_pass_full use cached_method_name)
>
> ### Half-closed items still requiring follow-up:
> - **#17** — `Signal::with` ✅; `set()` Vec<usize> clone still at `core/src/reactive/signal/impl.rs:284-286, 301-307`.
> - **#22** — `with`-borrow ✅; messages still in `Signal<HashMap<...>>` at `ui/src/hook/i18n/struct.rs:39`.
> - **#2** — `cached_method_name` helper at `engine/src/renderer/impl.rs:13-29`; only ~10 of 249 Reflect sites use it; Function-level cache not implemented.
> - **#34** — from_str cached at 9 sites in `begin_render_pass_full`; Object/Array allocations per frame unchanged.
> - **#33** — pair_buffer ✅, bboxes Vec::with_capacity ✅; `grid.clear()` still drops cell Vec buffers at `engine/src/spatial/impl.rs:88-90, 225-227`.
> - **#18** — joins use `" "` literal ✅; PR #180 (restore as `&str` const) OPEN.
>
> ---
>
> ## 🎯 RECOMMENDED NEXT BATCH (post-PR #180 close)
>
> Easy wins (trivial/low risk, ≤1 hour each):
> 1. **#33 tail** (grid.clear preserve buffer) — 6 lines.
> 2. **#35** (set_bind_group dynamic offsets Uint32Array::view) — 20 lines.
> 3. **#39** (input typed getter) — 4 lines.
> 4. **#16** (setup_dynamic_node Box merge) — 10 lines.
> 5. **#10** (patch_attributes linear scan) — 20 lines.
> 6. **#15** (window_event_listener in-place) — 15 lines.
> 7. **#19** (try_reclaim_inactive candidate drain) — 15 lines.
> 8. **#37** (for-loop with_capacity) — 5 lines × 3 sites.
> 9. **#30** (markdown/navbar/sidebar format! hoist) — 20 lines.
> 10. **NP-4** (dead-code cfg gate) — 5 lines.
> 11. **NP-3** (NodeRef clear on unmount) — 15 lines (correctness bug).
>
> Mid-pack (medium risk, multi-PR):
> - **#13 + #9 + #7** — single PR: cleanup_subtree query_selector_all + Rust-side HashMap for signal addrs + small write.
> - **#2 + #34 + #35** — engine Reflect cleanup (function cache + descriptor cache + offsets view).
> - **#17 + #22 (tails)** — Signal dependent swap/iteration + i18n messages move.
> - **#21 + #29** — VirtualNode children ref + TextNode Cow (paired VirtualNode touch).
> - **#11** — keyed diff LIS.
>
> Heavy (high risk, planning required):
> - **#1** — DomOp batched commit (needs JS glue shape + CDP regression).
> - **#36** — Rc<[VirtualNode]> (re-evaluate after R1 fix).
> - **#5 + #6** — Signal slab + bridge rewrite (paired, big API touch).
> - **#41** — per-property signal (architectural rewrite, deferred).
