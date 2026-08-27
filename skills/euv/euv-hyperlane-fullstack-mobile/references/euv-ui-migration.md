# Migrating an existing euv 0.13 project to use euv-ui design system

When (and when not) to migrate:

- Migrate when:
  - The project hand-rolls a `style.rs` with 20+ `c_*` classes using hard-coded hex colours (`#0f1115`, `#888`, …) and you can tell the result is going to look like a 2014 SPA.
  - You want to add a dark/light theme without touching every page.
  - You want the same nav, button, badge, and form look as the euv example app.
- Do not migrate when:
  - You have only one or two hand-rolled classes that genuinely don't exist in the euv-ui registry (just keep them in a local `style/fn.rs`).
  - You're on an euv version earlier than 0.13.3 — the 22-component / 306-class surface stabilised there.

## Migration in 7 steps (verified end-to-end on visa-tracker 2026-08-20)

1. **Add `lombok-macros = "2.0.36"`** to `[workspace.dependencies]` (euv uses this version; 0.1 only has the `Data` derive macro, `New` / `CustomDebug` are missing). In `client/Cargo.toml` add `lombok-macros = { workspace = true }`.
2. **Delete `client/src/style.rs`** and create `client/src/style/{mod.rs, fn.rs}` instead. The new `fn.rs` contains a single `class! { ... }` block with only the classes that euv-ui's 306-class registry does NOT cover (typically ~10-15: `c_form_grid`, `c_form_hint`, `c_stats_grid`, `c_list_filter_count`, `c_map_placeholder`, …).
3. **Restructure the source tree** to the euv example page-mode layout:
   ```
   src/
   ├── lib.rs              (#[wasm_bindgen] main + App::mount)
   ├── mod.rs              (sub-dir only, NOT at crate root — see pitfall 18 below)
   ├── api/{mod.rs, fn.rs}
   ├── models/{mod.rs, struct.rs}
   ├── state/{mod.rs, fn.rs, struct.rs}
   ├── style/{mod.rs, fn.rs}
   └── page/{mod.rs, list|map|stats/{mod.rs, view/{mod.rs, fn.rs}, hook/{mod.rs, fn.rs}}}
   ```
   Every page directory MUST have a `hook/{mod.rs, fn.rs}` pair even when hooks are empty placeholders — this matches the euv example convention and means adding real hooks later doesn't require restructuring.
4. **Declare all sub-modules in `lib.rs`** (`mod api; mod models; mod state; mod page; mod style;`), not in a top-level `mod.rs`. If both `lib.rs` and `mod.rs` exist, rustc treats `lib.rs` as the crate root and the `mod.rs` becomes dead code (errors look like `unresolved import crate::page`).
5. **Rename business views to use euv-ui components**:
   - Hand-rolled header → `euv_header { icon: "🛂" title: "..." subtitle: "..." }`
   - Card-shaped sections → `euv_card { title: "..." children }`
   - Form inputs → `euv_field { id label input_type placeholder value error }`
   - Buttons → `euv_button { variant: EuvButtonVariant::Primary label: "..." onclick }`
   - Status pills → `euv_badge { text outline on_click }` or `euv_tag { variant color text on_click }`
   - Key-value rows in stats → `euv_info { label "..." children }`
   - Error state → `euv_alert { variant: AlertVariant::Error children }` (note: `AlertVariant`, NOT `EuvAlertVariant`)
   - Loading state → `euv_loading { title subtitle overlay background }`
   - Tab buttons → use euv global classes `c_tab_bar` / `c_tab_item_active` / `c_tab_item_inactive`
6. **Make public structs derive `Clone, Data, Debug, New, CustomDebug`** and add `use lombok_macros::*;` at the top of each file that uses them. The `Data` derive produces the `Getter` / `GetterMut` / `Setter` accessors; `New` produces `Self { ... }`; `CustomDebug` produces a `Debug` impl that skips `Rc<dyn Fn(...)>` fields when annotated `#[debug(skip)]`.
7. **Build**:
   ```
   cargo build --release --target wasm32-unknown-unknown
   wasm-bindgen target/wasm32-unknown-unknown/release/<crate>.wasm \
       --target web --out-dir client/www/pkg --out-name <crate> --no-typescript
   ```

## Pitfalls encountered during migration (2026-08-20 visa-tracker)

| Symptom | Root cause | Fix |
|---|---|---|
| `unresolved import crate::page` | Both `lib.rs` and `mod.rs` present at crate root | Delete `mod.rs`; put `mod foo;` declarations in `lib.rs` |
| `mod fn` fails with `expected identifier, found keyword 'fn'` | `fn` is a Rust keyword; bare `mod fn;` is a parse error | Use `mod r#fn;` (file is still `fn.rs`) |
| `cannot find derive macro New` / `CustomDebug` | `lombok-macros = "0.1"` only provides `Data` | Use `lombok-macros = "2.0.36"` (the version euv itself uses) |
| `no rules expected keyword let` inside html! | `for x in items { helper_fn(x) }` — for body must be a single element | `for x in items { div { ... inline content using x ... } }` |
| `no rules expected keyword let` inside html! | `format!(...)` used as a bare child | Wrap in `{ format!("...") }` |
| `expected ',' following 'match' arm` | `if cond { ... } else { for x in items { ... } }` — html! macro parser doesn't like else-for | Split: `if !cond { for x in items { ... } }` then `if cond { ... }` |
| `cannot find type EuvAlertVariant` | Type is `AlertVariant` (no `Euv` prefix) | Check `ui/src/component/<name>/view/enum.rs` for the actual name |
| `class!` block won't compile after `sed` strips `///` | The doc comment text remains as bare Rust tokens after the `///` removal | Keep doc comments OUT of class! blocks; use plain `//` comments above the block |
| Final `git status` shows `target/` listed as `D` even though `.gitignore` has `target/` | The directory was committed before `.gitignore` was added | `git rm --cached -r target/` then commit the deletions |
| Linter complains about every `async fn` | The linter default edition is 2015 | Real cargo build uses `edition = "2024"` — linter noise, not a real error |

## Verification after migration

After building and deploying:

1. `cargo build --release --target wasm32-unknown-unknown` succeeds in <30s, 0 errors (a handful of dead-code warnings is fine).
2. `wasm-bindgen` produces a `_bg.wasm` roughly the same size as the original or larger (more components = bigger wasm).
3. Headless Chrome loads the page; the `<title>` shows `[ready]` (or similar sentinel) when `App::mount` finishes.
4. The first 4 GET requests hit `/api/countries`, `/api/visas`, `/api/stats`, `/api/stats/by-country` and return 200.
5. POST + DELETE cycle in the browser context succeeds end-to-end (write through, read back, delete, confirm gone).

## Why this skill exists

Before this migration, the visa-tracker frontend had a hand-rolled 34-class CSS block using `#0f1115` black and a flat layout that did not match the euv design language. After migrating, the same UI uses `euv_card` / `euv_field` / `euv_button` / `euv_badge` / `euv_tag` / `euv_info` / `euv_alert` / `euv_loading` (8 of the 22 euv-ui components) and the page picks up the correct monochrome palette + spacing + typography for free.