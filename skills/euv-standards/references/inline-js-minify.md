# `#[wasm_bindgen(inline_js = ...)]` snippets — mechanism + minify

> verified 2026-09-14, euv 0.24.5 / euv-cli build pipeline.
> Source: `core/src/renderer/registry/fn.rs` (event id chain),
> `core/src/renderer/render/fn.rs` (subtree ids), `cli/src/build/fn.rs` (minify step).

## What wasm-bindgen does with `inline_js`

`#[wasm_bindgen(inline_js = r#" ... "#)]` blocks are extracted verbatim from
the Rust source by wasm-bindgen at build time. The string is written into
a custom section of the `.wasm`, and at runtime the wasm-bindgen JS glue
(`pkg/euv_example.js`'s `__wbg_*` init code) reads that section and `eval`s
it once on first load, producing per-crate ES modules that the wrapper
`euv_example.js` then imports.

Output layout (after `wasm-pack build`):

```
pkg/
├── euv_example.js          # main glue, imports snippets
├── euv_example_bg.wasm
└── snippets/
    ├── euv-core-<hash1>/inline0.js
    ├── euv-core-<hash1>/inline1.js
    ├── euv-core-<hash2>/inline0.js   ← <hash> changes when source changes;
    └── ...                                old hashes are NOT auto-cleaned
```

The `<hash>` is content-derived; euv source unchanged ⇒ same hash. Source
changes ⇒ new hash directory, old one stays until `clean_out_dir` removes it.

## Why euv uses `inline_js` for these two functions

Both functions walk the DOM and return a `Float64Array`:

| Function (file) | What it does | Called from |
| --- | --- | --- |
| `euv_event_collect_id_chain(event, max_depth)` (`core/src/renderer/registry/fn.rs`) | Walk `event.target` up via `parentElement`, collect `data-euv-id` values | **Every delegated event** (click / input / scroll via `Registry::delegation`) |
| `euv_collect_subtree_ids(root)` (`core/src/renderer/render/fn.rs`) | Pre-order traversal, collect `(data-euv-id, data-euv-dynamic-id)` pairs | Patch path when subtree ids need to be re-resolved |

Both must return `Float64Array`. `Float64Array` is **zero-copy** across the
JS↔wasm boundary — V8 backs it with a typed-array buffer that the wasm
linear memory shares. This is the entire reason these are JS, not Rust:

- Doing the walk in Rust would mean N cross-boundary calls per walk
  (`parent_element()` + `get_attribute()` per hop, ~100–500 ns each).
- The current JS version makes **1** cross-boundary call total — the
  whole walk runs in V8, and only the resulting `Float64Array` is handed
  to wasm.

**Do not "port them to Rust for performance".** Every past attempt made
event delegation measurably slower.

## Why minify

The `inline_js` strings ship verbatim — wasm-bindgen does **not** run
them through a minifier. A typical euv build emits ~2 KB of uncompressed
JS that the browser downloads on every page load:

```
$ wc -c pkg/snippets/euv-core-*/inline*.js
 432 pkg/snippets/euv-core-*/inline0.js
 326 pkg/snippets/euv-core-*/inline1.js
 758 total
```

(Those are post-minify sizes — pre-minify they are 809 + 1095 = **1904 B**,
a **60.2 % savings**.)

## Minifier choice — `minify-js 0.6.0`

| Crate | Verdict | Why |
| --- | --- | --- |
| `minify-js = "0.6.0"` | **Chosen** | 3 direct deps (`aho-corasick`, `lazy_static`, `parse-js`), edition 2024 compatible, pure Rust, no dev-snapshot deps. ES module output preserves export names. |
| `oxc_minifier = "0.149.0"` | Rejected | 24 direct deps, including `insta` (dev snapshot). Even though the V8 team uses it, the dep graph adds ~5× the compiled-binary weight to `euv-cli`. Disproportionate for compressing ~2 KB. |
| `terser` (wasm) | Rejected | Build complexity, slow, no win for the use case. |

API used:

```rust
use minify_js;
let session = minify_js::Session::new();
let mut out: Vec<u8> = Vec::new();
minify_js::minify(&session, minify_js::TopLevelMode::Module, &input, &mut out)?;
// out contains minified ES module with original export names preserved
```

`TopLevelMode::Module` is mandatory — the snippets are ES modules
(`export function euv_...`), not scripts. Switching to `Global` silently
strips the `export` keyword and breaks the wasm-bindgen glue loader.

## Why export names MUST be preserved

`pkg/euv_example.js` does:

```js
import { euv_event_collect_id_chain } from './snippets/euv-core-<hash>/inline1.js';
```

The import is by name. A minifier that mangles export names (`export {a as euv_event_collect_id_chain}` is fine; `export {a}` is not) will break the import at runtime with `TypeError: undefined is not a function`. `minify-js` happens to preserve export names by default; verify on any replacement.

## Build pipeline integration (verified pattern)

Add a post-`build_wasm` step that walks `pkg/snippets/**/inline*.js` and
rewrites each file in place:

```rust
// cli/src/build/fn.rs
pub async fn minify_inline_js_snippets(out_dir: &Path) -> Result<(), EuvError> {
    let snippets_root = out_dir.join(SNIPPETS_DIR_NAME); // "snippets"
    if !snippets_root.is_dir() { return Ok(()); }
    // ... walk every <crate-hash>/ subdir, every "inline*.js" file
    // minify in place with TopLevelMode::Module
    // log a single summary line: "Minified N snippets: in_bytes -> out_bytes (X%)"
}
```

Hook into both `run_build_only_pipeline` (one-shot build) and `run_build_pipeline` (watch loop), immediately after `build_wasm` succeeds and before HTML generation. Failures: `log::warn!` + skip (a malformed snippet is already caught by wasm-pack itself; this layer should never abort the build).

## Stale `snippets/<hash>` directories

Every source change creates a new `<hash>` subdir under `snippets/`. Old
hashes are not auto-cleaned by wasm-pack. Without intervention, the
directory grows one entry per build. Two cures:

1. `clean_out_dir(out_dir)` (already in `run_build_only_pipeline`) wipes
   `pkg/` entirely before each build — **kills the stale-hash problem
   but also wipes the whole pkg**.
2. Targeted cleanup: walk `snippets/`, delete every directory that
   isn't imported by the freshly-generated `pkg/euv_example.js`. Do this
   if you want incremental builds.

euv's current pipeline uses option 1 (clean before build). If you switch
to incremental builds, add option 2 to avoid shipping 5+ stale hash dirs
per page load.

## Verification recipe

```bash
# 1. Build once
cd example && wasm-pack build --release --out-dir www/pkg --target web

# 2. Check emitted snippets
wc -c www/pkg/snippets/*/inline*.js

# 3. Run minify step (or rebuild via `euv build`)

# 4. Confirm export names survived
grep -c '^export' www/pkg/snippets/*/inline*.js   # each file should have >=1
grep -oE 'euv_[a-z_]+' www/pkg/snippets/*/inline*.js | sort -u
# Expected: euv_collect_subtree_ids, euv_event_collect_id_chain

# 5. Headless smoke test — load the page, click anywhere, verify delegated
#    event still routes correctly (the most common failure mode if export
#    names are mangled).
```

## Unit test template

```rust
#[tokio::test]
async fn minifies_uncompressed_snippet() {
    let tmp = tempfile::tempdir().unwrap();
    let pkg = tmp.path().join("pkg");
    let crate_dir = pkg.join("snippets").join("euv-core-abc");
    std::fs::create_dir_all(&crate_dir).unwrap();
    let original = r#"export function euv_event_collect_id_chain(event, max_depth) {
        const ids = [];
        // ...real body...
        return Float64Array.from(ids);
    }"#;
    std::fs::write(crate_dir.join("inline0.js"), original).unwrap();
    super::minify_inline_js_snippets(&pkg).await.unwrap();
    let minified = std::fs::read_to_string(crate_dir.join("inline0.js")).unwrap();
    assert!(minified.len() < original.len() / 2);
    assert!(minified.contains("euv_event_collect_id_chain"));
    assert!(!minified.contains("//"), "comments should be stripped");
}
```

Pair with two negative tests:

- `skips_missing_snippets_dir` — `minify_inline_js_snippets(&empty_pkg)` returns `Ok(())` without error.
- `leaves_non_inline_js_files_alone` — a `helper.js` / `.d.ts` / `package.json` sibling in the same `snippets/<hash>/` directory is **not** rewritten.

## PR scope reminder

Inline-js minify is a build-pipeline change — PR should touch:

- `Cargo.toml` (workspace dep)
- `cli/Cargo.toml` (dep + dev-dep)
- `cli/src/build/const.rs` (`SNIPPETS_DIR_NAME`, `SNIPPET_FILE_PREFIX`)
- `cli/src/build/fn.rs` (helper + 2 call sites + tests)

**Never** edit `pkg/` — that's a build artifact, regenerated every build.
**Never** edit the `inline_js` strings in `core/src/renderer/{registry,render}/fn.rs` unless intentionally changing semantics — the export-name contract is load-bearing.
