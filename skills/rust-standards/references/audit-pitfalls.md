# Audit script false-positive catalog

`scripts/audit_rust_standards.py` checks 20 categories of rust-standards
violations in a single pass. Several categories cannot be checked
statically because the master repo has pattern exceptions that look like
violations to a non-master-aware script. This document enumerates every
known false positive so the next session doesn't waste time chasing them.

## 1. `mod r#<keyword>;` in any mod.rs — NOT a violation

`mod r#struct;`, `mod r#impl;`, `mod r#fn;`, `mod r#enum;`, `mod
r#const;`, `mod r#static;`, `mod r#type;`, `mod r#trait;` are all
**required** by master pattern (R6.2). The `r#` prefix is needed
because `struct`/`impl`/`fn`/etc. are Rust keywords. The audit script's
"r# on non-keyword file" check excludes these 9 names — if you see other
files with `r#`, that's a real violation.

## 2. `mod r#<sub>;` inside `core/src/tests/mod.rs` — NOT a violation

Per R14.1a, the test mod.rs uses `mod r#<sub>;` (with `r#`) for every
sub-test, even when `<sub>` is not a keyword (e.g. `mod r#signal;`,
`mod r#cache;`). This is the explicit exception in R14.1a and the
audit script skips `core/src/tests/mod.rs` and `cli/tests/mod.rs`
entirely. Audit category 11 (r# on non-keyword file) already skips
files in `/tests/` subdirs.

## 3. `pub use super::*;` (with `pub`) as last line of
   `core/src/tests/<sub>/mod.rs` — NOT a violation

Per R14.1a, test mod.rs files in `core/src/tests/<sub>/` use `pub use
super::*;` (with `pub`) as their last non-blank line. This is required
so the tests can access parent-module symbols via `use super::*;` in
`fn.rs`. The audit script's category 6 (mod.rs trailing `use
super::*`) accepts both `use super::*;` AND `pub use super::*;` as
valid endings, so this should not appear as a failure.

## 4. `use super::*;` (no `pub`) as last line of `core/tests/<sub>/mod.rs` — NOT a violation

Per R14.1b, integration test mod.rs files in `core/tests/<sub>/` use
`use super::*;` (no `pub`) as the last line. The `pub` would trigger
"no imported item is public enough" warnings because integration tests
are a separate compile crate. Master pattern: every line in
`core/tests/<sub>/mod.rs` ends with `use super::*;` without `pub`.

## 5. Direct `///` doc comment on `enum.rs` / `struct.rs` / `type.rs`
   without `use super::*;` first — NOT a violation

Master pattern allows `enum.rs` / `struct.rs` / `type.rs` to open with
a `///` doc comment if the type does not need to reference any symbol
from the parent module. Example:

```rust
/// The phase of a `SuspenseState`.
///
/// - `Pending` — the underlying data is still loading.
#[derive(Clone, Debug)]
pub enum SuspensePhase { ... }
```

The audit script's category 7 (sub-file first line) reports these as
"violations" because the first non-comment line is `#[derive(...)]`,
not `use super::*;`. Manually confirm the file doesn't reference any
parent-module symbol via the `use super::*;` chain before fixing.

## 6. `//!` module-level doc comment as first line — NOT a violation

Module-level `//!` doc comments are allowed on **any** sub-file as the
first lines. The audit script's category 7 reports these as
"violations" because the first non-comment line is past the doc block
and may not be `use super::*;`. The script tries to handle this by
looking at the first non-blank, non-comment line — if your file opens
with `//!` and then has a `use super::*;` after a blank line, it is
correct.

## 7. `//` comment explaining "intentionally NOT imported super::*" — NOT a violation

Some files like `core/src/reactive/use_async/struct.rs` deliberately
skip `use super::*;` because the module defines its own trait and uses
fully-qualified `core::...` paths. The file opens with a `//` comment
explaining this. Audit script category 7 reports it; manually verify
the comment before fixing.

## 7a. Direct `///` doc comment on `const.rs` / `static.rs` / `fn.rs`
    / `trait.rs` / `impl.rs` without `use super::*;` first — NOT a
    violation

Master pattern treats every keyword-only sub-file the same way
`audit-pitfalls #5` already covers `enum.rs` / `struct.rs` /
`type.rs`: when the file defines only items in its dedicated keyword
(constants / statics / fns / traits / impls) and does not need any
parent-module symbol, it may open with a `///` doc comment directly.
A repo-wide grep for the first non-comment line across
`example/src/**/const.rs` returns 26 files in master, none of which
start with `use super::*;` — confirming the pattern is universal.

The audit script category 7 used to misreport these. As of
2026-08-28 it now matches by `basename` and skips every
keyword-only sub-file (`const.rs` / `static.rs` / `fn.rs` /
`enum.rs` / `struct.rs` / `trait.rs` / `impl.rs` / `type.rs`).
When in doubt, manually confirm the file doesn't reference any
parent-module symbol via the `use super::*;` chain before fixing.

## 7b. `mod r#async;` / `mod r#await;` / `mod r#try;` / `mod r#dyn;`
    in any mod.rs — NOT a violation

Per audit-pitfalls #1, `mod r#<keyword>;` is required whenever the
module path collides with a Rust keyword. The original exemption
list covered the nine traditional keywords (`const`, `static`, `fn`,
`enum`, `struct`, `trait`, `impl`, `type`, `mod`) but missed the
four keywords added by RFC 2018 (`async`, `await`, `try`) and the
2018 keyword-softening pass (`dyn`). Master accepts `mod r#async;`
in `example/src/page/mod.rs` and other pages whose module path
matches an RFC 2018 keyword. Audit script category 11 now matches
the full keyword list; if you see `mod r#<reserved>;` and the
identifier is a Rust keyword, the report is stale and should be
ignored.

## 8. `try_get_child_node` (or any helper that "should be removed") — VERIFY before deletion

The R6.4 audit table says helpers only used by ONE caller should be
inlined. But if the helper has been kept across many versions and the
calling site is the sole user, the deletion is safe. Grep the entire
crate (not just production) for the helper name before deleting:
`git grep -n "helper_name" $(git rev-parse --show-toplevel)`.

## 9. `#[allow(static_mut_refs)]` on a single line — likely intentional

If you see one `#[allow(static_mut_refs)]` on a `registry` / `get_mut_*`
function, it's the standard pattern for accessing `static mut` WASM
globals — don't strip these in a style audit pass. They are explicit,
single-line, and each gates a specific `unsafe { &mut *GLOBAL }`
access.

## 10. `panic!` inside `core/src/reactive/<feature>/tests/*.rs` or
   `core/src/tests/<sub>/fn.rs` — INTENTIONAL

Tests use `panic!()` / `.unwrap()` / `.expect()` directly per R11.4
exception. Audit script category 3 (production unwrap/expect/panic)
already excludes `tests/` paths; if you see a panic in the audit output
that's in a `tests/` file, the audit script has a bug — re-grep with
`grep -v "/tests/"` and verify.

## 11. `tag.get_name().as_str()` after `Tag::Element(Cow<'static, str>)` refactor

The `as_str()` method on `&str` is unstable in newer Rust toolchains
when called through auto-deref on `Cow<'_, str>` (Rust 2024 E0658
`str_as_str`). Use `.as_ref()` (returns `&str` via `AsRef<str>` impl)
or `&**name` (explicit deref) instead. Same pattern for
`HashMap<&str, ...>` keys produced from `attr.get_name().as_str()`
inside `patch_attributes` — needs `.as_ref()`.

## 12. macro emit `Tag::Element("div".to_string())` → `Cow::Borrowed("div")`

When refactoring `Tag::Element(String)` to `Tag::Element(Cow<'static,
str>)`, the macro `tag_literal = "#tag_name.to_string()"` token
**does not work** when wrapped in `Cow::Borrowed(...)` because
`"div".to_string()` is not `'static`. Use the raw string literal token
directly: `tag_literal = #tag_name` (no `.to_string()`) → wrap in
`Cow::Borrowed(#tag_literal)` at the call site.

## 13. `String::from(literal_string)` inside `html!` macro for portal target

Portal macro emits `String::from(#expr)` to support both string
literals (which become owned Strings) and `Signal<String>::get()`
values. After the `Cow` refactor, wrap the whole expression in
`Cow::Owned(String::from(#expr))` instead of `Cow::Borrowed(...)` —
portals accept runtime selectors, not just literals.

## 14. Duplicate `use super::*;` from prior migration

When migrating from a file with leading `//!` doc comment to the
R14.1 pattern (which requires `use super::*;` as first line), a
mechanical prepend of `use super::*;\n\n` to the original content
sometimes leaves the old `//!` block followed by ANOTHER
`use super::*;`. Always check: if a file has TWO consecutive
`use super::*;` lines, the first one is from the bad migration and
should be removed (the original `//!` block is also deleted in the
correct migration).

## 15. `match cache_ref.queue_microtask.as_ref() { Some(...) => ..., None => return false }`

After caching `queueMicrotask` as `Option<Function>`, the "checked
once, used many times" pattern is:

```rust
let fn = match cache_opt {
    Some(f) => f,
    None => return false,
};
```

NOT `.unwrap()`. The early-return-on-None makes the unwrap "safe" but
the audit rejects it. Use `match` or `if let Some(_) = ... else
{ return; }`.

## 16. Cargo.toml workspace deps come FIRST

Master convention for `[dependencies]` ordering: workspace-internal
deps first (e.g. `euv-core`, `euv-macros` for `Cargo.toml`; `euv`,
`euv-engine`, `euv-ui` for `example/Cargo.toml`), then externals in
length-ordered alphabetical order (shorter strings first). `core/Cargo.toml`
has no workspace deps, so the externals start with `js-sys`.

Blank lines between sections:
- After `[package]` block
- Between `[dependencies]` and `[dev-dependencies]`
- Between `[dev-dependencies]` and `[build-dependencies]` (if any)
- Between `[build-dependencies]` and `[lib]` (if any)
- No blank line AFTER the last block (no trailing newline-of-blank-line)

## 17. lib.rs `//!` doc comment IS allowed [DEPRECATED 2026-09-26 fifth iteration]

The audit script category 5 (// comments in mod.rs) does NOT
flag lib.rs. Master explicitly allows a top-of-file `//!` crate
description on lib.rs. Same for raw_html.rs (the only non-lib.rs file
allowed to have `//!` as first lines — it's the proc-macro implementation
file in `macros/src/`).

**[DEPRECATED 2026-09-26 fifth iteration]**:  This exemption is upgraded
to a MANDATORY rule by `verify_lib_rs_doc_comment.py` (audit check 37).
Per user original (2026-09-26 第五轮): "对于 lib.rs 必须要检查是否存在
//! 注释,注释第一行 //! 后是包名后面是一行 //! 再后面才是内容".
The required structure is now:

  //! <package_name>     // text must equal [package].name from Cargo.toml
  //!
  //! <description>      // project description

Real-workspace findings (euv): 5 lib.rs files violate this rule:
- `core/src/lib.rs:1` 写 `//! euv` 但 `[package].name = "euv-core"`
- `example/src/lib.rs:1` 写 `//! euv Example` 但 `name = "euv-example"`
- `docs/src/lib.rs:1` 完全没 `//!` 块
- `cli/src/lib.rs:1` 写 `//! euv CLI` 但 `name = "euv-cli"`
- `macros/src/lib.rs:1` 写 `//! euv_macros` 但 `name = "euv-macros"`

The historical "allowed" framing here is now reversed: missing the
`//!` block is a violation; the only "allowed" form is the canonical
3-line structure documented above.
## 18. `struct`/`fn` at column 0 inside WGSL shader raw strings — NOT a violation

Keyword-file purity scans (R1.3) that match top-level items by "line starts
at column 0" false-positive on `example/src/page/game_2d/hook/const.rs` and
`game_3d/hook/const.rs`: the WGSL shader source inside
`pub(crate) const GAME_*_WEBGPU_SHADER: &str = r#"..."#;` contains
`struct BallData {`, `fn vs_main(...)` etc. at column 0. These are shader
code, not Rust items. Any purity scanner must strip `r#"..."#` (and
`r##"..."##`) raw-string contents before matching col-0 item keywords, and
any block extractor must skip raw strings when brace-matching (a `}` inside
a shader string corrupts the depth counter and truncates the extracted
block).

## 19. test-file `use std::panic::{AssertUnwindSafe, catch_unwind};` — NOT a hoist target

The "dependency imports go to lib.rs" rule (R6.1) does NOT apply inside
`#[cfg(test)] mod tests;` blocks. The lib crate compiles in two passes
(`cargo check --lib` ignores `#[cfg(test)]` items, `cargo check --tests`
includes them); the top-level `use std::panic::{...};` in `core/src/lib.rs`
IS visible to `cargo check --lib`, but the TEST-side uses of
`catch_unwind` / `AssertUnwindSafe` live in `core/src/tests/<sub>/fn.rs`
where the lib's `use` line is NOT propagated because the tests/<sub>/fn.rs
is part of the `tests` module (inside `#[cfg(test)] mod tests` in lib.rs),
not the lib crate's compile unit.

**Consequence**: `cargo check --lib` will see the panic imports as
unused (warning), but `cargo check --tests` needs them. The cleanest
fix is to keep `use std::panic::{AssertUnwindSafe, catch_unwind};`
INSIDE the test file (`core/src/tests/<sub>/fn.rs`) and let the lib's
own copy live or die based on actual production usage.

**Detection**: after running hoist_uses, any test file under
`core/src/tests/*/fn.rs` that references `AssertUnwindSafe` or
`catch_unwind` must keep its `use std::panic::{...};` import —
the audit script should skip `tests/` paths.

## 20. `self.field` direct access in owned-self consumers — NOT a violation

When an `impl` block owns `self` (`fn into_inner(self) -> T`, `impl Default`,
`fn new(...) -> Self`, or destructors like `Drop`) and needs the **owned**
value of a field, the lombok-generated `get_field(&self)` returns `&Field`
which is unusable: a generic `T: ?Sized` cannot be `Clone`d, and an
`unsafe { ptr::read(&self.field) }` would defeat the safety guarantee
that the struct's field-visibility rule (§6.4.1) was set up to provide.

**Permitted direct-field access sites** (no `#[allow]`, no `pub` bump):
- `fn into_inner(self) -> T { self.inner }` — adapter consumes self
  (e.g. `EventAdapter<F>::into_inner`, `AttrValueAdapter<T>::into_inner`,
  `InnerHtmlAdapter<T>::into_inner` in `core/vdom/cast/impl.rs`).
- `impl Default for X { fn default() -> Self { Self { field: ... } } }`
  — struct-literal init.
- `fn new(...) -> Self { Self { field } }` — constructor body.

**Why this is NOT a violation of "use the macro-generated accessor"**:
the lombok `get_field()` and a field-access inside a consumer are NOT
functionally equivalent (`&T` vs `T`); the macro is not an alternative
here. The hand-written `into_inner` IS the only Rust-idiomatic way to
move out of `self`.

**Companion rule**: `EngineCell` / `MaybeEngineCell` in
`engine/src/cell/struct.rs` carry a `T: ?Sized` bound that prevents
`#[derive(Data)]` (lombok requires `Sized`); they hand-write
`get_inner` / `set_inner` accessors explicitly noted in the struct doc
as "Lombok-shaped counterparts". The body of those hand-written accessors
uses `&self.inner` / `&mut self.inner` — this is also a §20-style
exception (the hand-written accessor IS the lombok contract for this
type). External call sites should still use `self.get_inner()` /
`self.set_inner(val)`.

**Detection**: an audit script can whitelist these sites by checking
the enclosing function is one of:
  - `fn into_inner(self) -> T`,
  - `impl Default for X { fn default() -> Self }`,
  - `fn new(...) -> Self { Self { ... } }`,
  - `impl Drop for X { fn drop(&mut self) }`,
  - or any function whose body is a hand-written `get_*` / `set_*`
    accessor for a `T: ?Sized` type.
Everything else should use `get_field` / `get_mut_field` / `set_field`.



## 21. `use super::*;` omission for leaf sub-files (clarification of §6.3)

`rust-standards/references/06-module-imports.md` §6.3 says sub-files "must"
have `use super::*;` as their first line, with the explicit exemption
for `const.rs` (which usually doesn't reference parent symbols). This
section extends the exemption: **any sub-file whose body does not
reference any parent-module identifier may omit `use super::*;`**.

**Why**: `use super::*;` triggers Rust's `unused_imports` lint when
the sub-file body genuinely has nothing to import from the parent.
Adding `#[allow(unused_imports)]` is forbidden by the warning-handling
principle (it would mask real dead imports later), and removing the
`use` would force every leaf enum/struct/type to add a comment
explaining "this file has no parent imports" — pure noise.

**Detection**: an audit script must NOT count a missing `use super::*;`
as a violation if the sub-file body, after stripping its own top-level
declarations and standard prelude types, has zero remaining identifier
references that could plausibly come from the parent module.

**Examples of sub-files legitimately exempt**:
- `enum.rs` that only defines `pub enum FooBar { ... }` with no
  body that references any sibling struct / type / fn.
- `type.rs` that only defines a single type alias.
- `fn.rs` that only defines a single free `pub fn name(...)` with
  no parent-module references.
- `trait.rs` that only defines a single trait with method bodies
  using only primitive types.

**NOT exempt** (still need `use super::*;`):
- `impl.rs` (impl bodies almost always reference sibling types).
- `fn.rs` with multiple free functions that cross-reference each other.
- Any sub-file where the body references a symbol declared in a
  sibling sub-file or the parent mod.rs.

The companion rule §6.3 still applies to non-leaf sub-files.
## 22. bulk rewriter applying R17.3 — must skip hand-written accessor bodies

When a rewriter script tries to enforce "every `self.field` becomes
`self.get_field()`" across the whole crate, it will blindly replace
`&self.inner` (inside the body of a hand-written `pub fn get_inner(&self)`
for a `T: ?Sized` type like `EngineCell`) with `self.get_inner()` — which
recurses infinitely.

**Pattern that triggers the bug** (seen in `engine/src/cell/impl.rs`):

```rust
impl<T: ?Sized> EngineCell<T> {
    pub fn get_inner(&self) -> &UnsafeCell<T> {
        &self.inner          // ← rewriter changes to `self.get_inner()` → recursion
    }
}
```

**Root cause**: a generic `T: ?Sized` type can't `#[derive(Data)]`, so
the project hand-writes `get_inner` / `set_inner` accessors that satisfy
the same Lombok contract. The rewriter can't tell the difference between
"external call site needing the macro accessor" and "hand-written
accessor body that has to use the field directly".

**Fix in the rewriter**: skip impl blocks where the target struct has
a hand-written `pub fn get_<field>(&self)` or `pub fn <field>(&self)`
*and* the body of the rewrite site is *inside* one of those functions.
Equivalently, identify "hand-written Lombok-shaped accessors" by the
presence of a `// Lombok-shaped counterpart for parity with ...` doc
comment (see `engine/src/cell/struct.rs` for the project's
convention).

**Detection after running the rewriter**: `cargo check` will report
`warning: function cannot return without recursing` on the rewritten
accessor. If you see two warnings of this shape back-to-back (one for
each `get_inner` body in `EngineCell` and `MaybeEngineCell`), the
rewriter misfired — revert those two bodies back to `&self.inner`.

**General lesson**: any audit-or-fix script that targets the *language
level* (R1.3 purity, R17.3 fields, etc.) must special-case *project-
level conventions* before blindly rewriting. The §19/§20 white lists
are exactly this kind of carve-out.

## 23. `#[macro_use] extern crate X;` is the only way to expose a macro to child modules

A common miss when migrating "dependency imports to lib.rs": the type
items (`X::TypeName`) can be re-exported via `pub use X::TypeName;` and
become reachable to sub-files via `use super::*;`, but the *macro items*
(`X::macro_name!`) cannot be re-exported via `use`. Macros are
textually scoped to the crate root, and the only way to make
`quote!` / `parse_macro_input!` callable from a child module is
`#[macro_use] extern crate quote;` at the top of `lib.rs` (Rust 2018+
also accepts `use quote::quote;` in `lib.rs` *only* if the call site is
itself in `lib.rs`).

**Concrete pattern from `euv-macros`** (`macros/src/lib.rs` after this
session's refactor):

```rust
#[macro_use]
extern crate syn;     // makes parse_macro_input! callable in raw_html.rs

// then all type re-exports stay as plain `use`:
use syn::LitStr;      // → raw_html.rs can `use super::*;` and reach LitStr
```

**Why `quote!` doesn't need `#[macro_use]`** in the same file: it has a
`use quote::quote;` in `lib.rs` which is enough to bring `quote!` into
the *crate root* namespace, and `lib.rs`'s own modules (`html/`,
`class/`, etc.) call `quote!` directly. The asymmetry: `#[macro_use]`
is only needed for macros that need to cross a `mod` boundary into a
child file.

**Verification**: after consolidation, run `cargo check -p <crate>` and
look for `cannot find macro 'X!' in this scope` in the child module
file. If it appears, add `#[macro_use] extern crate X;` to `lib.rs`.

## 24. private `use std::{...};` block vs `pub use std::{...};` — test-only items must be `pub`

The R6.1 rule "dependency imports go to lib.rs" is incomplete: sub-files
under `#[cfg(test)] mod tests` need to reach those imports via
`super::*;`, but a *private* `use std::panic::catch_unwind;` in
`lib.rs` does NOT propagate through `pub use super::*;` (private use
items stay crate-private even when re-exported as part of a glob).

**Concrete pattern** (from `core/src/lib.rs`):

```rust
// WORKS for production code (private is fine — only this crate uses it)
use std::{ cell::Cell, rc::Rc, ... };

// WORKS for test code too — must be `pub use` so `core::tests::*` can see it
pub use std::{
    collections::hash_map::DefaultHasher,
    hash::{Hash, Hasher},
    panic::{AssertUnwindSafe, catch_unwind},
    vec::Vec,
};
```

**Detection**: `cargo check --tests` (not `cargo check --lib`) will
surface `cannot find function/type X in this scope` inside a test
`fn.rs`. The fix is to move the corresponding items from the private
`use std::{...}` block into the `pub use std::{...}` block, NOT to
re-add the `use` line inside the test file.




## 26. `change_*` setter naming — Lombok `Data` macro collision escape hatch

`rust-standards/references/07-naming.md` §7.2 mandates `snake_case` for
function names. The **implicit project-wide convention** (observed
across the master codebase) is direct verbs for setters: `set_*` (31
methods), `update_*` (10 methods), `with_*` (9 methods), `add_*`,
`remove_*`, `submit`, `validate`, `measure`, `prefetch`, `refetch`,
`toggle`, `tick`, `enter`, `exit`, `reset`, `clear`, etc. — **0
`change_*` methods** in master.

**However**, `#[derive(Data, New)]` from `lombok_macros` automatically
generates `set_<field>(&mut self, val: <FieldType>)` accessors for
every field. When a setter's semantics differ from the macro-generated
one, naming it `set_X` would either shadow the generated accessor (at
best a confusing name collision, at worst a compile error).

**Concrete examples** where the prefix `change_*` is the documented
correct escape hatch:

1. `I18n::change_locale(&self, locale: &str)` —
   `#[derive(Data)]` would generate `set_locale(&mut self, val: Signal<String>)`.
   The hand-written method accepts `&str` (not `Signal<String>`) and
   `&self` (not `&mut self`) because the field is itself a `Signal`,
   and writing into a signal only requires `&self` access. Doc comment:
   `Named 'change_locale' (not 'set_locale') to avoid colliding with
   the 'set_locale' getter generated by '#[derive(Data)]'.`

2. `I18n::change_fallback_locale(&self, locale: &str)` — same rationale.

3. `Transition::change_config(&self, config: TransitionConfig)` —
   Lombok would generate `set_config(&mut self, val: Signal<TransitionConfig>)`.
   The hand-written method accepts the full `TransitionConfig` value
   and writes it INTO the existing `Signal`. Doc comment:
   `Named 'change_config' (not 'set_config') to avoid colliding with
   the 'set_config' setter generated by '#[derive(Data)]'.`

4. `LazyComponent::change_factory(&self, factory: impl Fn() -> T + 'static)`
   — same pattern.

**Detection rule**: a `change_*` method is legitimate when **all four**
hold:
- the type's `struct.rs` declares `#[derive(Data, New)]` (or `Data` alone)
- the field being "set" is `Signal<T>` (not a plain `T`)
- the method accepts the inner `T` (not `Signal<T>`) and `&self` (not `&mut self`)
- the method's doc comment explicitly references the Lombok collision

**NOT legitimate**: introducing new `change_*` methods on types that
do NOT derive `Data`, or on types where the field is plain (not
wrapped in a `Signal`). The plain case has no Lombok collision and
`set_*` should be used.

This exception was confirmed by the audit of
`perf/renderer-and-signal-2026-08-24` where 4 `change_*` methods were
found — all 4 satisfy the criteria above (all derive `Data`, all have
`Signal<T>` fields, all accept the inner type, all have the
Lombok-collision doc comment).

**For top-level free functions in `fn.rs`**: a `change_*` function in
`fn.rs` is **NEVER** legitimate — if it's a free function it's not a
method, and the Lombok collision argument doesn't apply. Always use
`set_*` / `update_*` / `with_*` / etc. for free functions.
## 25. fn/const naming audit — verify against project baseline, not generic Rust rules

The rust-standards §5.2 / §7 rules establish generic Rust naming
(`snake_case` fn, `CamelCase` types, `UPPER_SNAKE_CASE` const). They do
NOT capture **project-specific** naming conventions like "setters use
`set_X` not `change_X`". When the user asks "is the PR naming compliant?",
a generic regex check returns "yes" for everything but misses the real
project-specific deviations.

**The audit method** (5 steps, run in this order):

1. **Identify the PR's "added fn" set, not the diff**.
   ```bash
   # Get fn declarations added by the PR (not just changed):
   git diff --diff-filter=AM -U0 BASE..HEAD -- '*.rs'      | grep -E '^\+.*fn \w+\s*[<(]'      | sed 's/^.*fn //' | sort -u
   ```
   The merge-base matters: `master..HEAD` includes prior PRs in the same
   branch; `df9c9c6..HEAD` includes only the perf PR's commits.
   Whichever range the user is reviewing, scope your audit to that range.

2. **Filter to production fns** (drop `tests/`, `wasm_only`, generic
   Rust trait impls like `new`/`default`/`clone`/`fmt`/`from`/`into`).
   Project-specific fns are the ones that need the convention check;
   generic trait impls are auto-derived.

3. **Build a project-baseline prefix frequency table**.
   ```bash
   git show master:$(git ls-tree --name-only -r master | grep '\.rs$' | head)      | grep -oE 'fn (set_\w+|change_\w+|update_\w+|with_\w+)'      | sort | uniq -c | sort -rn
   ```
   This answers "what prefix does the project ACTUALLY use for setters?"
   rather than "what prefix does Rust convention suggest?". Count zero
   `change_*` in master means `change_*` is project-banned, even though
   it's a perfectly valid English verb.

4. **Verify each new fn against (a) snake_case regex, (b) baseline
   prefix list, (c) descriptive semantic English, no abbreviations**.
   The third check matters: `try_reclaim_inactive` passes (try/reclaim/
   inactive are all standard English words), but `try_rec_inact` would
   fail even though it's snake_case.

5. **Verify consts against UPPER_SNAKE_CASE regex + the same
   descriptive-vocabulary check**. Constants encode project-specific
   intent (e.g. `MAX_ANCESTOR_DEPTH_FOR_HIGH_FREQ` — every component
   word must be standard English, no internal abbreviations).

**The "PR diff only" trap**: when PR #21 was reviewed for fn naming,
the initial scan showed `change_locale`, `change_factory`,
`change_config`, `change_fallback_locale` as "newly added" — but those
were actually introduced in PR #20 (the rust-standards refactor PR
whose commits `a70fe8b` → `df9c9c6` were already merged into the
branch). The perf PR `df9c9c6..HEAD` only added `try_reclaim_inactive`
+ 2 consts + 4 wasm_bindgen_test helpers. Always scope the naming
audit to the PR being reviewed, not the entire branch.

**Detection**: when the user asks "命名规范", "naming conventions", or
"PR 改动的所有 fn", ALWAYS:
- Use `git merge-base master HEAD` to find the true PR boundary.
- Run the diff against that boundary.
- Build the project baseline from `git show master:<file>` samples.
- Report findings with the project's actual prefix conventions,
  not generic Rust style rules.

## 27. fn-body `use std::xxx;` re-importing symbols already in lib.rs `pub use std::{...}` — REAL violation

Sub-files inherit `use super::*;` which globs every symbol re-exported
by the parent `mod.rs` (which in turn re-exports from `lib.rs`'s `pub
use std::{...}` block). If a sub-file's function body adds a redundant
`use std::collections::{HashMap, HashSet};` (or any std / project
symbol already exposed via the chain), rustc emits a compile error
(unambiguous glob) **or** clippy fires `unused_imports` — both are
review-blocking.

**Concrete pattern (PR #202, euv keyed-diff planner)**:
- Before: `fn.rs::compute_child_ops_plan` opened with
  `use std::collections::{HashMap, HashSet};` even though `lib.rs` line
  18 has `pub use std::collections::{HashMap, HashSet, VecDeque};`.
- After: remove the in-fn `use`; sub-file accesses `HashMap` /
  `HashSet` directly via the `use super::*;` chain.

**Detection rule**:
- Before committing a sub-file, grep the file body for any `use` line
  that re-imports a symbol already in `lib.rs`'s `pub use` block:
  ```bash
  grep -nE '^    use |^        use ' <crate>/src/<sub>/fn.rs | grep std
  ```
  Every hit is a candidate for removal.
- Audit script cannot statically detect this (it doesn't model which
  symbols lib.rs re-exports); review manually.

**NOT a violation**:
- `use std::collections::HashMap;` in `lib.rs` itself (the entry point
  — no super::* above).
- `use std::path::PathBuf;` in a `fn.rs` if `PathBuf` is **not** in
  lib.rs's `pub use std::{...}` block.
- `#[cfg(test)] mod tests { use super::*; use std::time::Instant; }`
  if the test needs `Instant` and lib.rs doesn't re-export it.

## 28. `pub(crate) enum` / `pub(crate) type` declared inside `fn.rs` — REAL violation (§1.3 keyword purity)

`fn.rs` is one of the 9 keyword-only files (§1.3). It accepts only
`fn` declarations + free functions. New types (`pub(crate) enum
ChildOpPlan`, `pub(crate) struct FooBar`, `pub(crate) type MyAlias =
...`, `impl X for Y`) declared directly inside `fn.rs` violate §1.3
purity and the audit script's category 1 (`non-keyword prod files`)
won't catch it because the file basename **is** `fn.rs`.

**Concrete pattern (PR #202)**:
- Before: `core/src/renderer/render/fn.rs` contained
  `pub(crate) enum ChildOpPlan { ... }` inline with `lis_indices` and
  `compute_child_ops_plan`.
- After: move `ChildOpPlan` to a new `core/src/renderer/render/enum.rs`
  (first line `use super::*;`), declare it in `mod.rs` as
  `mod r#enum;` + `pub(crate) use {r#enum::*};` (§6.2 strict three-
  segment).

**Detection rule**:
- Before declaring any new type / impl / trait in a sub-file, check
  the file's keyword by basename:
  `const.rs` → only const; `static.rs` → only static; `fn.rs` → only
  fn; `enum.rs` → only enum; `struct.rs` → only struct; `trait.rs` →
  only trait; `impl.rs` → only impl; `type.rs` → only type alias.
- `grep -nE '^(pub |pub\(crate\) )?(struct|type|enum|trait|impl)' <file>`
  should return zero matches (comments / doc strings excepted).
- `fn.rs` and `struct.rs` are the most common offenders because they
  get used as "grab-bag" files; resist the temptation.

**NOT a violation**:
- `type TestKeyList = Vec<Option<&'static str>>;` inside
  `#[cfg(test)] mod tests { ... }` — test-module-only type alias
  doesn't pollute the file's production purity.
- Any keyword file that contains only its declared keyword (e.g.
  `enum.rs` containing only `pub(crate) enum Foo { ... }`).

## 29. Blank lines inside fn bodies — REAL violation (§9.1 item 10)

`rust-standards/references/09-follow-existing.md` §9.1 item 10
explicitly forbids blank lines inside function bodies. Section
breaks are expressed by comment lines (`// Phase 1: ...`,
`// Pass 3: emit Remove for ...`), not by blank lines. The previous
implementation style of "blank line then comment header then code"
does not match this project's master convention.

**Concrete pattern (PR #202)**:
- Before: comment blocks inside `patch_children_keyed` were separated
  by single blank lines (line 718 was the only true blank inside the
  fn body — between comment block and code).
- After: blank line removed; `// OPT 16: ...` comment sits flush
  against the previous code line.

**Detection rule**:
- For every `pub fn` / `pub(crate) fn` / `fn` body in a PR's diff,
  walk from the `)` opening brace to the matching `}` and count blank
  lines (`^$`). Each blank is a §9.1 violation.
- A quick awk one-liner:
  ```bash
  awk '
    /pub fn |pub\(crate\) fn |^fn / && !in_fn { in_fn=1; start=NR; blanks=0; next }
    in_fn && /^}$/ { if (blanks > 0) print FILENAME ":" start "-" NR ": " blanks " blank line(s) in fn body"; in_fn=0; next }
    in_fn && /^$/ { blanks++ }
    in_fn && /^\s*\/\// { next }  # comment lines don't count as breaks
  ' <file>
  ```
- `euv fmt` and `cargo fmt` do **not** auto-remove fn-body blanks
  (they only format whitespace around tokens, not inter-statement
  spacing inside a block). Review manually.

**NOT a violation**:
- Blank lines **between** `#[test] fn a() { ... }` and `#[test] fn b() { ... }`
  inside `#[cfg(test)] mod tests { ... }` — test separators are
  idiomatic.
- Blank lines **between** free functions at file scope (after the
  closing `}` of fn A and before the doc comment of fn B) — that
  space separates top-level items, not fn bodies.
- Blank lines inside struct / enum literals (e.g. between struct
  fields with explicit visual grouping).

## 30. audit script rule 8 broken regex — silent false-positive (audit-pitfalls #10's hidden bug)

`audit_rust_standards.py` rule 8 ("`#[cfg(test)]` in production", R14.5)
historically had a broken ERE regex that made the rule silently PASS
even when real inline `#[cfg(test)] mod tests { ... }` violations
existed in the diff.

**The bug** (pre-2026-09-12):

```python
('#[cfg(test)] in production', '''
cd {target}
git diff -U0 origin/master HEAD -- "*.rs" 2>/dev/null | grep -E "^\\+.*#\\[(test|cfg\\(test\\)\\)" | head -20
'''),
```

The Python triple-quoted string is fed through `.format(target=target)`
(which preserves backslashes literally) and then handed to bash via
`subprocess.run(['bash', '-c', cmd])`. After both escape layers, grep
saw a malformed ERE with unmatched parentheses and printed
`grep: Unmatched ( or \\(` to stderr while r.stdout stayed empty — the
rule printed "PASS: 8. #[cfg(test)] in production" because the script
counts `r.stdout` lines, not stderr.

**Why this matters**:

- The rule was supposed to catch inline `#[cfg(test)] mod tests` per
  §14.4 (single-tests must live in `tests/` directory, not inline).
- Anyone reading "14/14 PASS" thought their inline tests were
  compliant when in fact the audit was failing silently.
- Rule 4 ("#[test] in production", separate grep) had the same
  escape-layer bug for a different regex — fixed in the same pass.

**The fix** (2026-09-12):

Replace `grep -E <regex>` with `grep -F <literal>` whenever the rule
needs to match a fixed Rust token:

```python
('#[cfg(test)] in production', '''
cd {target}
git diff -U0 origin/master HEAD -- "*.rs" 2>/dev/null | grep -F "#[cfg(test)]" | grep -v "^[+][+][+] b/" | grep "^[+]" | head -20
'''),
```

`grep -F` interprets the pattern literally — no ERE parsing, no
parentheses/backslash collision. The `grep -v "^[+][+][+] b/"` strips
the diff "+++ b/path" header lines so only actual `+` content lines
remain.

**Detection when adding a new audit rule**:

When you write a new `CHECKS.append((name, shell_template))` block,
before committing:

1. Run the rule directly in a shell with the same template format to
   verify it actually emits output when a violation exists:
   ```bash
   cd <repo-root>
   <paste the shell_template body, replacing {target} with the path>
   ```
2. Verify the rule FAILS (prints hits) when the diff contains a
   violation, and PASSES when the diff is clean.
3. **Never** trust "PASS" until you have manually confirmed a known
   violation triggers "FAIL".

If the rule keeps PASSing despite visible violations, check
`r.stderr` from `subprocess.run([...])` for `grep: ...` errors — that's
the symptom of a broken ERE.

**Master-exception exemption REMOVED (2026-09-12 user 第二轮)**:

user 原话:

> "src里所有单测删除,有tests目录是单测的,如果单测的功能不是pub那就忽略"

这条把 §14.4 的"master 例外 pattern"(允许 `pub(crate)` item 用 `#[cfg(test)] mod tests { ... }` + `// These tests live inline` 注释保留 inline 测试)**完全推翻**。现在的规则:

- 任何 inline `#[cfg(test)] mod tests { ... }` 块 = violation,不管有没有 `// These tests live inline` 注释。
- `pub(crate)` item 没有单元测试——算法正确性必须通过 `pub` API 的 end-to-end 测试间接覆盖。
- `pub` item 的测试必须搬到 `<crate>/tests/<feature>/fn.rs`,不能改 visibility。

**audit script rule 8 修改**:删掉 `// These tests live inline` 注释的 exemption,任何 `+#[cfg(test)]` 行都 FAIL。**euv PR #203 实测**:core/src/renderer/render/fn.rs 922 行 inline tests + engine 三个 inline tests + master 注释全部删除/迁移。

**迁移目标**:
- `pub(crate)` fn 关联的 inline 测试 → **整块删除**(不带任何注释保留)。
- `pub` fn 关联的 inline 测试 → 搬到 `<crate>/tests/<feature>/fn.rs`,开头 `use euv_engine::*;` / `use euv_core::*;`(该 crate 的 `pub use` re-export 链)。

**§14.4 文档同步**:`references/14-testing.md` 已更新,删掉"master 例外 pattern"小节,改为"`pub(crate)` item 的测试怎么办 — DELETE,不保留 inline"。

## 31. audit rule + SKILL.md rule consistency — single source of truth

Adding a new rust-standards rule requires updating FOUR places
consistently:

1. **SKILL.md** (`key-rules` pitfall callout) — the rule itself.
2. **references/<topic>.md** — the long-form justification + examples.
3. **references/audit-pitfalls.md** — false-positive / false-negative
   catalog if applicable.
4. **scripts/audit_rust_standards.py** — mechanical enforcement
   (when a regex/static check can express it).

**Skipping any of the four** creates a knowledge gap that bites future
sessions. Concrete example from this session:

- §14.4 "single-tests in tests/ only" was added to `references/14-testing.md`
  AND rule 8 of audit script was fixed to actually catch it.
- §6.4 "no fn-body `use std::xxx;` re-imports" was added to
  `references/06-module-imports.md` AND audit-pitfalls #27 cataloged
  the violation pattern (audit script can't statically detect it
  because it doesn't model lib.rs's `pub use` chain, so manual review
  is the only enforcement).
- §1.3a "keyword file purity enforcement" was added to
  `references/01-directory-structure.md` AND audit-pitfalls #28
  cataloged it.

**Checklist when adding a new rule**:

1. Write the rule prose in the most specific references file (where
   the topic naturally belongs).
2. If it can be statically checked: add a CHECKS entry to
   `audit_rust_standards.py` and **verify** the rule with a known
   violation (see §30 detection steps above).
3. If it can't be statically checked: add an audit-pitfalls entry
   cataloging the false-positive catalog (#N above) so the next
   session knows it's a manual-review item.
4. Update SKILL.md's "key rules" section with a one-line callout
   linking to the references file.
5. Mention in commit message which of the four you updated.

**Sign of missing step 4** — when you read SKILL.md's "key rules"
section and a documented rule has no callout, future agents loading
the skill for the first time won't know it exists. Always cross-link
SKILL.md ↔ references ↔ audit script.

## 32. WGSL shader raw strings in `const.rs` — re-scan with raw-string-aware parser (refines §18)

`audit-pitfalls #18` documents that `struct` / `fn` at column 0 inside
WGSL shader raw strings are **not** violations. But the §18 entry only
names the **symptom** (false positive in column-0 keyword scans) — it
does not give a **re-scan recipe** for a future session that hits it.

This session (2026-09-12, euv PR #202 + master §1.3a audit) found that
**master has 38 such false positives** in
`example/src/page/{game_2d,game_3d,lighting,raytrace}/hook/const.rs` —
all `pub(crate) const *_WEBGPU_SHADER: &str = r#" ... "#;` blocks
containing WGSL `struct BallData { ... }` / `fn vs_main(...)` etc. at
column 0.

**The raw-string-aware re-scan recipe** (Python; runnable as a
`while`-loop replacement for the broken scan):

```python
import os, re

# per-file state
in_raw_string = False
raw_delim = None  # "#" / "##" / etc.

for line in file:
    # skip line/block comments (audit-pitfalls #10)
    ...
    if in_raw_string:
        close_marker = f'"{raw_delim}'
        if close_marker in line:
            pos = line.find(close_marker)
            after = line[pos + len(close_marker):]
            in_raw_string = False
            # process `after` as code (re-enter the brace / keyword loop)
            ...
        continue  # line fully consumed by raw-string contents
    # detect raw-string start
    m = re.search(r'r(#+)["\']', line)
    if m:
        delim = m.group(1)
        close_marker = f'"{delim}'
        pos_start = line.find(m.group(0))
        pre = line[:pos_start]
        # process `pre` as code
        ...
        rest = line[pos_start + len(m.group(0)):]
        if close_marker in rest:
            pos_close = rest.find(close_marker)
            after = rest[pos_close + len(close_marker):]
            # process `after` as code
            ...
            continue
        in_raw_string = True
        raw_delim = delim
        continue
    # normal code line — apply the keyword scan
    ...
```

**Three invariants this scanner must preserve** to be correct:

1. **Block-comment / line-comment skip** before raw-string detection
   (comments can contain `r#"..."#` literally; if you don't skip them,
   the state machine mis-flips).
2. **Pre-raw-string code (`pre`)** — anything before the `r#"..."#` token
   on the same line still needs to be scanned as code (e.g. the `pub(crate) const NAME: &str =` prefix on line 1 of the shader const).
3. **Post-raw-string code (`after`)** — anything after the closing `r#"..."#` on the same line is also code (rare in master, but possible if a shader const is on the same line as a `;` or other code).

**Master occurrences to ignore** (re-scan post-filter):
- `example/src/page/game_2d/hook/const.rs` — `GAME_2D_WEBGPU_SHADER` r#"..."#
- `example/src/page/game_3d/hook/const.rs` — `GAME_3D_WEBGPU_SHADER` r#"..."#
- `example/src/page/lighting/hook/const.rs` — `LIGHTING_WEBGPU_SHADER` r#"..."#
- `example/src/page/raytrace/hook/const.rs` — `RAYTRACE_WEBGPU_SHADER` r#"..."#

After applying the raw-string-aware scan, the count drops from 38 to 0
true violations — all were shader code.

## 33. Brace-tracking scanner for §9.5 (fn-body blank lines) — false-positive traps

The naïve "track global brace depth, treat every `{` as fn-body start"
scanner produces **40+ false positives** in master (verified this
session, 2026-09-12). Three classes of false positive that the naive
scanner must special-case:

1. **`use std::{ ... }` blocks** (blank lines inside the use list, e.g.
   `cli/src/lib.rs:24`) — these are NOT inside a fn body even though
   brace depth > 0.
2. **`pub trait Foo { fn method_a(&self); fn method_b(&self); }`** — blank
   lines between trait method signatures are idiomatic Rust; not a §9.5
   violation.
3. **`pub const A: ...; ... pub const B: ...;` blocks** inside `const.rs` —
   blank lines between const items are not inside a fn body.

**The fix**: classify the brace-opening context, not just count braces.
Before pushing onto the brace stack, look at the text up to and
including the `{`:

```python
import re

def is_fn_open(prefix: str) -> bool:
    """prefix is the text up to and including the opening brace.
    Returns True iff this brace opens a function body."""
    s = prefix.rstrip().rstrip("{").rstrip()
    # Last word sequence before the brace must be a fn keyword:
    #   fn foo() -> ...
    #   pub fn foo() -> ...
    #   pub(crate) async unsafe const fn foo() -> ...
    return bool(re.search(
        r'\b(fn|async\s+fn|const\s+fn|unsafe\s+fn|pub(\([^)]*\))?\s+fn)\b\s*$',
        s,
    ))
```

The naïve regex `^(pub(\([^)]*\))?\s\w+\s+\w)` (matches `pub trait Collider`
because "trait" is `\w+`) **fails** because it doesn't require the
keyword to be `fn`. The fix above requires the last word(s) before `{`
to be `fn` / `async fn` / etc. — false-positive rate drops from 42 hits
to 0 hits on master.

**Other context flags to push instead of "fn"**:
- `mod tests { ... }` preceded by `#[cfg(test)]` attribute → push `test`
  (the scanner checks the preceding ~4 lines for `cfg(test)`).
- `use { ... }` / `const { ... }` / `static { ... }` / `trait { ... }` /
  `impl { ... }` / `mod { ... }` → push `other`.

Then in the blank-line check, only count as a §9.5 violation when the
topmost "fn" frame on the stack is **not** under a "test" frame (i.e.
production fn body, not test fn body).

**Master confirmed-false-positive sites** (after fix, scanner reports 0
hits at these locations):
- `core/src/renderer/dom/trait.rs:21` (trait method separator)
- `engine/src/collider/trait.rs:11,18,29` (trait method separators)
- `engine/src/entity/trait.rs:32` (trait method separator)
- `engine/src/renderer/trait.rs:22-...` (trait method separators)
- `engine/src/scene/trait.rs:10` (trait method separator)
- `engine/src/scheduler/trait.rs:12` (trait method separator)
- `cli/src/fmt/const.rs:53` (const item separator)
- `core/src/vdom/attribute/const.rs:23,50` (const item separators)
- `macros/src/class/const.rs:57` (const item separator)
- `macros/src/lib.rs:21` (`use std::{...}` block separator)
- `ui/src/lib.rs:11` (`use std::{...}` block separator)

## 34. `fn` in `fn.rs` is **crate-private** by default — needs `pub(crate)` for sibling `impl.rs` use

When moving a free function from `impl.rs` to `fn.rs` (per §1.3 keyword
purity), the function is now in a different sibling file. The
mod.rs `pub(crate) use r#fn::*` glob re-exports only **public +
pub(crate)** symbols. A plain `fn name(...)` (no `pub`) is **private**
to the fn.rs file itself; the sibling `impl.rs` cannot see it via
`use super::*;` even though the mod.rs glob re-exports `r#fn::*`.

**Concrete failure (this session, euv PR #202 + style cleanup)**:

After moving `cached_method_name` from `impl.rs` to `fn.rs`, cargo
emits `error[E0425]: cannot find function 'cached_method_name' in
this scope` at every callsite in `impl.rs`. Fix:

```rust
// engine/src/renderer/fn.rs
- fn cached_method_name(name: &'static str) -> JsValue {
+ pub(crate) fn cached_method_name(name: &'static str) -> JsValue {
```

Same pattern for `messages_lock` (i18n), `cached_method`,
`cached_method_call`, `fmt_lit_str` (macros) — all needed `pub(crate)`
after the §1.3 move.

**Detection**:
- Before moving a `fn` between sibling sub-files, grep the source crate
  for the function name: `git grep -nE 'fn name\(' -- '*.rs'`.
- After the move + first compile, if cargo emits E0425 at callsites
  outside the fn.rs file, add `pub(crate)`.

**NOT applicable**:
- `pub fn` is already public; sibling files see it via the glob.
- Free functions that are **only called from within fn.rs itself** stay
  plain `fn` (no `pub(crate)` needed).
- Methods inside `impl X { fn ... }` blocks are governed by the impl
  block's visibility, not the file-level `pub(crate)` requirement.

## 35. `audit_rust_standards.py` regex escape double-layer (Python `format()` + bash + grep ERE) — verification protocol

This session found that `audit_rust_standards.py` rule 8 had a broken
ERE regex (see §30) that PASSED silently despite real violations.
The root cause is **double-layer escaping**: the regex lives inside a
Python triple-quoted string that is fed through `.format(target=target)`
(preserves backslashes literally) and then handed to bash via
`subprocess.run(['bash', '-c', cmd])` (one more shell parse), and
finally to `grep -E` (one more ERE parse).

Three backslash layers, three chances for the regex to break. Every
existing audit rule that uses `grep -E` should be re-verified by:

1. **Run the rule manually in a shell** with a known violation:
   ```bash
   cd /root/github/<owner>/<repo>
   git diff -U0 origin/master HEAD -- "*.rs" 2>/dev/null | \
     grep -E "<exact-pattern-from-script>" | head -20
   ```
   The output should NOT be empty; if it is, the regex is broken.

2. **Verify `r.stderr` is clean** — broken ERE produces
   `grep: Unmatched ( or \\(` on stderr. If you see this, the rule is
   silently broken regardless of what `r.stdout` says.

3. **Check `subprocess.run(..., capture_output=True)` exit code** —
   `grep` returns 1 when no match is found. If the rule shell template
   ends with `head -20`, the pipeline exit code is `head`'s (always 0),
   masking the `grep` failure.

**Prefer `grep -F <literal>` over `grep -E <regex>`** for fixed Rust
tokens (rule 8's `#[cfg(test)]`, rule 4's `#[test]`, rule 3's
`panic!`, etc.). `grep -F` interprets the pattern literally — no
parentheses/backslash collision possible. Use `grep -E` only when the
pattern genuinely needs alternation or quantifiers.

**Rules in this audit script that should be re-verified with a known
violation**:

| Rule | Pattern | Risk | Fix |
|------|---------|------|-----|
| 3 | `panic!(\|\.expect\(\|\.unwrap\(\)` (in shell template) | backslash collision | `grep -F` "panic!" + separate `grep -F` ".expect(" + "grep -F" ".unwrap("; OR `grep -E` verified |
| 4 | `^#[test]` | low | OK |
| 8 | `^\\+.*#\\[(test\|cfg\\(test\\)\\)\\]` | **HIGH — was broken** | `grep -F "#[cfg(test)]"` (fixed 2026-09-12) |
| 11 | `mod r#<keyword>` | low (literal `r#` prefix) | OK |
| 13 | `^#!\[cfg\(test\)\]` | medium — backslash collision | `grep -F "#![cfg(test)]"` |
| 14 | `^pub(crate) fn .*\(self\)` | low | OK |

**Add a `verify_audit_rules.py` script** under `scripts/` (per the
"§31 single source of truth" checklist) that walks every `CHECKS.append`
rule, injects a synthetic violation into a temp file, runs the rule,
and confirms `r.stdout` is non-empty. Skip if the rule has no
synthesizable violation (e.g. file-level scans that need real `.rs` files).


### 35-B. Python heredoc inside `r'''` shell template — every `{` and `}` must be doubled, even outside `.format()` callsites

When a `CHECKS.append` rule's shell template embeds a `python3 - <<'PY' ... PY`
heredoc, **every literal `{` and `}` inside the heredoc is interpreted by
`.format(target=target)` in `run_check`** — not just the `{target}` placeholder.
Audit check 17 (the new "sub-file body uses external crate full path"
rule) had three separate unescape bugs that crashed with
`IndexError: Replacement index 0 out of range for positional args tuple`:

1. `IGNORE = {"std", "core", ...}` — the Python set literal `{...}` was
   consumed by `.format()`. Fix: `IGNORE = {{"std", "core", ...}}`.
2. `added_lines = {}` — the empty dict literal. Fix: `added_lines = {{}}`.
3. Any `{` `}` in regex literals inside the heredoc, e.g.
   `re.match(r"\{", line)` becomes a malformed pattern after `.format()`
   passes the single `{` through. Fix: double them too (`{{` `}}`).

**Symptom** is always the same: a rule that worked in isolation crashes
when the audit script runs `cmd = shell_template.format(target=target)`,
because `.format()` raises `IndexError` on any unmatched positional
placeholder (even just `{}`). The traceback is at
`audit_rust_standards.py:391: cmd = shell_template.format(target=target)`.

**Defense**: after editing any shell template in `CHECKS.append`, run

```python
import importlib.util
spec = importlib.util.spec_from_file_location(
    "a", "/root/.agents/skills/rust-standards/scripts/audit_rust_standards.py")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
for n, t in m.CHECKS:
    m.run_check(n, t, "/root/github/euv-dev/euv")
```

Every rule should produce empty output (no false positives on a clean
repo); any rule that crashes or hits an `IndexError` has an unescaped
`{}` somewhere.

### 35-C. `'''` close can be silently missing between adjacent `CHECKS.append` entries — Python sees one long string instead of N

When a `CHECKS.append` rule ends with a multi-line `r'''...''')` and the
next entry starts on the line after, **the audit script silently
concatenates them** if the closing `''')` is missing from entry N.
The first entry looks "fine" because the syntax parses (the open `r'''`
of entry N+1 closes entry N's string), and entry N+1 picks up where
entry N's content left off. This causes:

- Entry N's actual close `'''),` is missing → N's content leaks into
  N+1 → N+1's shell template contains unrelated code.
- Audit reports fewer rules than expected (the audit prints "N/17 PASS"
  instead of "16/17 PASS") because two entries merged into one.
- No syntax error — Python is happy with the merged string.

**Symptom**: `audit_rust_standards.py` reports fewer total checks than
the `len(CHECKS)` you expect, OR `rule X` shows up named for what should
be rule Y. Diagnostic:

```python
import importlib.util
spec = importlib.util.spec_from_file_location(
    "a", "/root/.agents/skills/rust-standards/scripts/audit_rust_standards.py")
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
print(len(m.CHECKS))   # should match the "X/Y PASS" output's Y
```

**Defense**:

```bash
grep -nE "^'''\),$|^r'''$" /root/.agents/skills/rust-standards/scripts/audit_rust_standards.py
```

should print exactly `2 × len(CHECKS)` lines (each entry has one open
`r'''`/`'''` and one close `'''),`). Mismatch → some entry's close is
missing.

### 35-D. Check 17 R6.4-pitfall-b — too broad, then over-narrowed; final scope is "top-of-file `use` and type annotations only"

R6.3 / §6.4 spirit says sub-files should reach external symbols via
`use super::*;` and `lib.rs` re-export, not via qualified full paths.
But §6.3 *literal* only forbids two patterns:

1. Top-of-file `use external_crate::xxx;` (R6.3)
2. `let x: external_crate::Type = ...` type annotations (R6.4 spirit)

It does **not** forbid:

- `log::warn!(...)` macro calls
- `tokio::fs::read(&path)` qualified path calls
- `clap::Parser` derive macro paths
- `serde_json::from_str` qualified function calls

An earlier version of check 17 grepped `\b<ext>::[A-Za-z_]` across the
whole file (not just `+` diff lines) and treated macro calls as
violations, producing 41 false positives on a single PR (all `log::warn!`,
plus historical `tokio::fs::*` calls that were already merged). The
fixed version of check 17 only scans **added lines from
`git diff -U0 origin/master HEAD -- <file>`**, and only matches the two
literal patterns above (top-of-file `use`, type-annotation `:`).

**If you change check 17's regex, reproduce both directions**:

- Add a synthetic `use external_crate::xxx;` to a test diff → expect 1 hit
- Add a synthetic `log::warn!("...")` to a test diff → expect 0 hits
- Add a synthetic `let x: external_crate::Type = ...;` → expect 1 hit
- Add a synthetic `tokio::fs::read(...)` call → expect 0 hits

If any of these expectations are wrong, the regex is over- or
under-matching. Also remember the §35-B escape rule: any `{` or `}` in
the heredoc must be `{{` / `}}` to survive `.format(target=target)`.


## 36. `rust-analyzer` lint false positive on Rust 2024 `let chains` and `async fn` — don't trust editor lints blindly

This session moved several declarations across files. After every move,
`patch` and `read_file` reported lint errors like:

```
error[E0670]: `async fn` is not permitted in Rust 2015
  --> engine/src/engine/impl.rs:44:9
   |
44 |     pub async fn run(config: EngineConfig, handler: TickHandlerRc) -> EngineHandle {
   |         ^^^^^ to use `async fn`, switch to Rust 2018 or later
```

`let chains` similarly:
```
error: let chains are only allowed in Rust 2024 or later
   --> macros/src/html/fn.rs:334:12
```

Both were **false positives** because:
- The repo's `core/Cargo.toml`, `engine/Cargo.toml`, etc. all set `edition = "2024"`.
- The patch tool's lint runs **rust-analyzer in standalone mode** without picking up the workspace's `Cargo.toml`, so it defaults to Rust 2015/2018 syntax checking.

**Detection**:
- When `patch` or `read_file` reports a lint error AFTER a successful
  `cargo check`/`cargo build`, the lint is almost certainly a
  rust-analyzer false positive.
- The error message is the giveaway: `Rust 2015` / `Rust 2018` when
  the workspace edition is `2024`.

**Action**: trust `cargo check` exit code (or `cargo build --tests`),
not the lint output. Continue with the move + commit + push workflow.
The lint false positive does not affect the actual compilation.

**When the lint IS real** (e.g. genuinely missing edition upgrade or
real syntax error): the lint output ALSO shows up in `cargo check`
stderr. If `cargo check` exits 0, the file is fine.

## 29.1 patch tool deletes preceding `///` doc-comment block when old_string starts mid-function — verified 2026-09-14 (euv-cli inline-js minify PR #233)

**Symptom**: A patch with `old_string` of the form
`<last line of preceding function's body>\n<blank line>\n/// - &Path - ...\n///\n/// - &Path - description.\npub async fn some_fn(...) {`
silently deletes the preceding function's `///` doc comment (4–8 lines
above the matched position). Worse, attempting to "re-patch" the deleted
doc comment back in by adding a fresh `/// Cleans ...\n/// Cleans ...`
block creates **duplicated `///` lines** that no longer compile-cleanly
even by lint standards — the duplicate-merge is itself malformed and
requires a third patch to fully restore.

**Why**: the patch tool's fuzzy match collapses multiple `///` lines
above the matched anchor into whitespace-equivalent noise, dropping them
on the assumption that they are decorative comments the user is replacing
as a unit. The pattern that triggers it: `old_string` ending with
`<code line>` + `\n` + `<blank line>` + `/// ...` + `pub async fn X()`.

**Detection**:
- After every multi-line patch that includes `///` doc-comment lines,
  immediately `git diff <file>` and confirm the actual file structure
  matches intent (especially doc comments around non-edited functions).
- `git diff --stat` showing 0 deleted lines but `wc -l <file>` decreased
  → indicates patch tool deleted content silently.

**Action**: prefer Python `re.sub` over `patch` for any change that
touches `///` doc-comment blocks around a function signature. The
replacement string itself stays clear of `///` ambiguity. Specifically:

```python
import re
from pathlib import Path
text = Path("file.rs").read_text()
new_text = re.sub(r'<single-line anchor pattern>', '<replacement>', text, count=1)
Path("file.rs").write_text(new_text)
```

If `patch` is unavoidable, **anchor the old_string on a unique token
that lives INSIDE the doc comment** (e.g. the function name) rather
than on the function-signature line, and include the doc-comment lines
IN the replacement string verbatim to avoid the silent-deletion bug:

```
old_string:
/// Cleans the output directory before a fresh build.
///
/// Removes all files and subdirectories within the output directory
/// so that stale artifacts from previous builds do not remain.
/// The directory itself is preserved (recreated if missing).
///
/// # Arguments
///
/// - &Path - The output directory to clean.
pub async fn clean_out_dir(out_dir: &Path) {

new_string:
/// Cleans the output directory before a fresh build.
/// ... full new doc ...
pub async fn clean_out_dir(out_dir: &Path) {
```

**Recovery**: when the bug fires, `git checkout HEAD -- <file>` and
retry with a Python script. Don't try to amend the deletion — the
3-step recovery (delete-clean, recover-via-patch, de-duplicate) costs
more than the rebuild.


## 30. audit rule 8 (#[cfg(test)] detection) broken regex — fixed 2026-09-12

**Symptom**: audit script rule 8 `grep -E "^\\+.*#\\[(test|cfg\\(test\\)\\)"` (Python format → shell escape → grep ERE) failed because `\\(` in ERE is invalid syntax. `grep` emitted `Unmatched ( or \(` to stderr and stdout was empty, so the rule always reported PASS — **false-positive PASS** even when `#[cfg(test)] mod tests` truly exists in production code.

**Detection**:
- Run audit in isolation: `python3 ~/.agents/skills/rust-standards/scripts/audit_rust_standards.py <repo>`.
- If rule 8 reports PASS but you KNOW your PR has `#[cfg(test)] mod tests` inline, audit rule 8 is broken.

**Action**: rewritten rule 8 to use `grep -F "#[cfg(test)]"` (fixed string match) plus master-exception check (lines containing `// These tests live inline` explanation comment are skipped — see §14.4 master pattern).

**Verified**: rule 8 now correctly reports FAIL when a new file adds inline `#[cfg(test)] mod tests` without master-exception comment.

## 31. audit rule 15 (R1.3a raw-string-aware keyword purity) — added 2026-09-12

**Why**: rule 1 only checks for non-keyword basename (e.g. `foo.rs` outside the 8 keyword-file names). It did NOT catch column-0 decl mismatches WITHIN keyword files (e.g. `pub(crate) enum X` declared in `struct.rs`, which is forbidden).

**Detection**: rule 15 walks each keyword file modified by the PR, parses column-0 decl lines, and flags any decl whose keyword type does not match the file's allowed type. Example:
- `fn.rs` should only contain `fn` decls → `pub(crate) enum Foo` in `fn.rs` is FAIL.
- `struct.rs` should only contain `struct` decls → `pub(crate) enum Bar` in `struct.rs` is FAIL.

**Raw-string aware**: when a column-0 `struct BallData { ... }` line appears INSIDE a `pub(crate) const GAME_2D_WEBGPU_SHADER: &str = r#"..."#;` raw string, it is a WGSL shader code, NOT a Rust decl → not flagged.

**Action**: any FAIL of rule 15 in your PR means you declared a wrong-type item in a keyword file. Move the decl to the correct keyword file per §1.3a:
- `enum Foo` → `enum.rs`
- `struct Bar` → `struct.rs`
- `fn baz()` → `fn.rs`
- `impl X { ... }` → `impl.rs`
- `trait T { ... }` → `trait.rs`
- `type Alias = ...` → `type.rs`
- `const FOO` / `static BAR` → `const.rs` / `static.rs`

**Verified**: rule 15 catches all column-0 decl mismatches that rule 1 missed, including the historical euv master violations (PR #202 cleanup) and WGSL shader code in raw strings (correctly excluded).

## 37. `tests/` comment rules — user iteration pattern + audit rule 16 false-positive traps

User went through three rounds of corrections on the same `tests/` topic, each round strictly tightening the rule. Future sessions debugging "why does audit rule 16 fire?" need to know the exact scope and the false-positive traps:

### Round 1 (2026-09-12): §14.4 — no visibility widening for tests

User 原话:
> "你不应该修改模块可见性,你应该使用已有可见的api去在tests里做单测,通过已有的api覆盖,没有暴露的api的单测"

So `pub(crate)` items have no tests — `#[cfg(test)] mod tests` blocks testing them must be **deleted entirely**, not moved.

### Round 2 (2026-09-12): §14.4 — no inline `mod tests` at all

User 原话:
> "src里所有单测删除,有tests目录是单测的,如果单测的功能不是pub那就忽略,如果是pub就加到tests里"

This nuked the prior "master-exception" exemption (§14.4 master pattern `// These tests live inline` comment as a marker). ALL inline `#[cfg(test)] mod tests` blocks are forbidden across the whole codebase. Tests for `pub` items move to `<crate>/tests/<feature>/fn.rs`; tests for `pub(crate)` items are deleted.

### Round 3 (2026-09-12): §14.5 — no comments in tests

User 原话:
> "单测不需要任何注释,删除所有单测注释"

Tests have zero comments — no file-level `//!`, no per-fn `///`, no fn-body inline `//`. Test fn name = documentation; assertion messages = expected behavior.

### Audit rule 16 implementation + false-positive traps

```bash
# Real implementation in audit_rust_standards.py (rule 16):
for f in $(git diff --name-only origin/master HEAD -- "*.rs" 2>/dev/null | grep -E "/tests/.*\\.rs$"); do
  hits=$(grep -nE "^\s*//[^/]" "$f" 2>/dev/null)
  if [ -n "$hits" ]; then
    echo "FAIL: $f has comments:"
    echo "$hits" | head -3
  fi
done
```

The regex `^\s*//[^/]` matches:
- `// normal comment` — FAIL (correct)
- `//path/with/slashes` — FAIL (false positive — a `//` URL fragment in a comment or string would also match, but tests shouldn't contain URL fragments anyway)
- `/// doc comment` — does NOT match (good — the regex requires `[^/]` after `//`, so `///` becomes `//` + `/` = second char is `/`, doesn't match)

Note: rule 16 does NOT separately detect `///` or `//!` — they fall under the same rule because the pattern requires the next char after `//` to NOT be `/`. So `///` and `//!` are excluded (good — they're handled separately by rule 5/§14.4).

If rule 16 fires on a test file, the action is: **delete every comment line**. There are NO exemptions. Reformat test fn names if they're ambiguous; add `.clone()` to `assert_eq!` calls instead of explaining "we compare owned values". Use the assertion message parameter for any necessary clarification:

```rust
// ❌ Forbidden (any context in tests/)
// Comment explaining the test
#[test]
fn foo() {
    // inline comment
    assert!(x);
}

// ✅ Correct: bare test, self-documenting
#[test]
fn foo_returns_true_when_input_is_positive() {
    let x = compute();
    assert!(x, "compute() must return true for positive input");
}
```

### Top-level integration-test mod.rs `use super::*;` is invalid Rust

`engine/tests/mod.rs` / `ui/tests/mod.rs` / `core/tests/mod.rs` are at the integration-test crate root — `super::*` would be "too many leading super keywords" (E0433). Rule 6 already excludes these from the trailing-`use super::*;` check. Engine / ui top-level mod.rs end with `use wasm_bindgen::JsValue;` (after any `use std::{...};`); core top-level mod.rs ends with `use std::{...};` or similar. Do not try to add `use super::*;` here.

**Verified**: euv PR #203 final state, audit rule 16 PASSES with 30/30 engine tests + 0 core inline tests, all comment-stripped.

## 38. CI `cargo fmt --check` is stricter than local `cargo fmt` (version skew pitfall)

2026-09-12 PR #203: local `cargo fmt --all` ran idempotent (0 changed), but CI's `cargo fmt -- --check` failed on `engine/tests/mod.rs:7` because CI had a trailing blank line that local rustfmt (1.9.0-stable) didn't normalize but CI rustfmt (1.98.1) did.

**Symptoms**: local idempotent, CI fails with a small diff like:
```
Diff in <path>/mod.rs:7:
 use euv_engine::*;
 
 use wasm_bindgen::JsValue;
-
 ##[error]Process completed with exit code 1.
```

**Fix**: when local `cargo fmt --all` is idempotent but CI fails, run `cargo fmt -- --check` locally (uses the same binary but the `--check` flag forces stricter comparison). If still failing in CI only, the issue is the rustfmt version skew between local stable (1.9.0-stable as of 2026-07) and CI stable (1.98.1 as of 2026-09-01).

**Action**: after local `cargo fmt` is idempotent, also run `euv fmt` (if euv project) then re-check. If they diverge, manually fix the discrepancy and re-commit. PR #203 commit `d0ab4ae5` was exactly this fix — a single line removal.

This is environment-dependent (rustfmt version skew) but the **workflow lesson** is durable: when local is idempotent and CI fails on fmt, don't just re-run `cargo fmt` — manually inspect the diff CI reports and apply it directly.

## 17. `debug/` or other dev-scratch subdir in crate root — NOT a violation

Some crates (lombok-macros is the canonical example) keep a manual
test scratch crate in a sibling subdir like `debug/` whose contents
include a `src/main.rs` with `fn main()` full of `assert!()` calls
exercising new derive features. This subdir is **explicitly excluded**
from the parent crate's `Cargo.toml`:

```toml
exclude = ["target", "Cargo.lock", "sh", ".github", "debug"]
```

It is **not** a workspace member (no `[workspace]` entry in
`debug/Cargo.toml`'s parent). The audit script does NOT know about
the `exclude` list and will flag it as:

- **Check #1** "non-keyword prod files" — `debug/src/main.rs` is
  reported as a production keyword-file violation.
- **Check #7** "sub-file first line not `use super::*`" — `debug/src/main.rs:1`
  starts with `use lombok_macros::*;` (or equivalent), but `debug/` is
  a **standalone binary crate** with its own `[package]`, so there is
  no `super` module to import from.

Both are false positives. The fix is **not** to add `use super::*;`
or move the file — `debug/` is a legitimate dev-only scratch crate
that must stay outside the production compile path. When audit
returns these two checks as FAIL and **only** these two, and a
sibling subdir like `debug/` exists with its own `Cargo.toml`,
verify the subdir is excluded from the parent and treat as
informational, not as a violation to fix.

Verified against `crates-dev/lombok-macros` (2026-09-12): `debug/`
ships 7 raw-pointer test structs (`GenericPtr<T>`, `DstPtr`,
`ConstPtr`, `OptPtr`, `OptDstPtr`, `CopyPtr`, `TuplePtr`) in
`debug/src/main.rs`, all gated by `fn main()` assertions, run via
`cargo run -p debug` from the subdir. Audit reports 14/16 PASS
with these two checks as the only failures.


## 39. `cli/src/main.rs` — NOT a violation of §1.3a (keyword file purity)

`main.rs` is the binary entry point of any `[[bin]]` target in a Cargo
workspace — it MUST be named `main.rs` (or referenced by
`[[bin]] path = "..."` in Cargo.toml), because cargo's default `[[bin]]`
discovery looks for `src/main.rs`. Renaming it to `fn.rs`/`mod.rs` etc.
to "satisfy" the keyword-purity rule would break the binary build.

Audit category 1 (`non-keyword prod files`) historically missed this
case — when a PR adds `cli/src/main.rs` (e.g. a `[[bin]]` crate being
imported into the workspace), the rule reports `NON-KEYWORD: cli/src/main.rs`.
The fix (2026-09-14): add `/main\.rs$` to the grep -vE exclusion list
in the rule template, alongside `/lib\.rs$` and `/raw_html\.rs$`.

**NOT a violation**: any `main.rs` (or `bin/<name>.rs` referenced from
`[[bin]] path`) — these are bin-target entry points, not production
keyword files.

**Still a violation**: any other non-keyword `*.rs` file under `src/`
(e.g. `src/foo.rs`, `src/utils.rs`, `src/helpers.rs`) — those should
be re-organized into keyword subdirectory + `mod.rs`.

Verified during hyperlane monorepo migration (PR #34): audit now PASSes
on `cli/src/main.rs` after the rule fix.


## 39a. `src/bin/<name>.rs` and `build.rs` — NOT violations of §1.3a (keyword file purity)

`src/bin/<name>.rs` is the cargo-discovered binary entry path
(`[[bin]] path = "src/bin/<name>.rs"` in Cargo.toml), equivalent to
`src/main.rs` for binary targets. `build.rs` is the cargo build script
entry point. Both are legitimate cargo conventions that must not be
re-organised into keyword subdirectory + `mod.rs` — cargo's discovery
rules require them at the conventional paths.

**Audit fix (2026-09-18)**: add `/bin/[^/]+\.rs$` and `(^|/)build\.rs$` to
the grep -vE exclusion list in audit rule #1 (non-keyword prod files)
and rule #7 (sub-file first line not `use super::*`), alongside
`/main\.rs$`. The `(^|/)` prefix is required because `build.rs` lives
at the repo root (no leading `/`); the pattern `(^|/)build\.rs$`
matches `build.rs` and `path/to/build.rs` but not `sub_build.rs`.

Triggered by `eastspire/euv-docs` PR #31 (feat/cli-binary): adding
`[[bin]] name = "euv-docs"` plus a 14-line env-var block in `build.rs`
to support a CLI binary. Both files are mandatory cargo conventions.

**NOT a violation**: any `src/bin/<name>.rs` (cargo auto-discovery for
`[[bin]]`) or `build.rs` (cargo build script entry point). Both files
must stay at the conventional paths and cannot be re-organised.

**Still a violation**: any other non-keyword `*.rs` file under `src/`
(e.g. `src/foo.rs`, `src/utils.rs`, `src/helpers.rs`) — those should
be re-organised into keyword subdirectory + `mod.rs`. The exclusion
matches only files that satisfy the `bin/<one-segment>.rs` or top-level
`build.rs` pattern.


## 39b. audit script check 19 (R9.1 §9.1 item 10 — fn-body blank lines) — added 2026-09-18

**Why**: §9.1 item 10 forbids blank lines inside function bodies. The
audit script previously had no check for this (audit-pitfalls #33 gave
the recipe but no rule was wired in), so a hand-written `pub fn` with
multiple blank lines between statements would PASS the audit and only
fail user review.

**Audit fix (2026-09-18)**: check 19 added to `audit_rust_standards.py`.
Detection algorithm:

1. Classify brace-opening context per audit-pitfalls #33:
   - text before `{` matches `\b(fn|async\s+fn|const\s+fn|unsafe\s+fn)\b` → push `"fn"`
   - preceding 3 lines contain `#[cfg(test)]` / `#[test]` / `mod tests` → push `"test"`
   - else → push `"other"`
2. Walk lines tracking the stack. When a blank line is seen and the
   topmost frame is `"fn"`, flag it as a violation.
3. Skip raw-string contents (WGSL shader code in `r#"..."#`), block
   doc-comments (`/** ... */`), and line doc-comments (`///` / `//`).

**Diff-hunk scoping** (added in same fix): only flag blank lines whose
new-file line number falls inside a hunk range from
`git diff <base> HEAD -U0 -- <file>`. This prevents upstream historical
violations from being blamed on the PR. Verified against
`eastspire/euv-docs` PR #31 (feat/cli-binary): build.rs has 25 fn-body
blank lines upstream-side but **0 in PR diff hunks** — audit correctly
reports 19/19 PASS for that PR.

**Base branch detection** (added in same fix): prefer the merge-base
between HEAD and `upstream/master` when a `remote.upstream.url` is
configured (Track 2 fork + PR setup). Falls back to `origin/master` for
non-fork repos. Verified against the same PR: `git merge-base HEAD
upstream/master` = `2e7fbb5`, diff scope = 4 files (the PR's actual
diff), not 6 (which is what `origin/master..HEAD` would return because
the local fork master contains 2 commits not yet merged upstream).

**Verified against**: `eastspire/euv-docs` PR #31 with hand-cleaned
`src/bin/euv-docs.rs` (4 phase comments replace inter-statement blank
lines) — 19/19 PASS, 0 false positives.

**NOT a violation** (per audit-pitfalls #33):
- Blank lines between top-level items (after one fn's `}` and before
  the next fn's doc comment) — these separate items, not inside bodies.
- Blank lines inside `#[cfg(test)] mod tests { ... }` — test fns are
  exempt per `tests/` pattern.
- Blank lines between trait method signatures (`pub trait Foo { fn a();
  fn b(); }`).
- Blank lines inside `use { ... }` blocks or const-item lists.


## 40. `mod.rs` 末尾 `use super::*;` 在子文件全无 parent symbol 用法时是 unused — auditor should accept absence

Audit category 6 (`mod.rs missing trailing use super::*`) currently
requires every `mod.rs` to end with `use super::*;` regardless of
whether the mod.rs itself or any sub-file actually consumes a
parent-module symbol. When **no sub-file** uses `use super::*;` to
access parent symbols (i.e. the entire `mod.rs` subtree is self-
contained — common for leaf enums like `pub enum CommandType { ... }`
with no methods), adding `use super::*;` triggers `unused_imports` at
mod.rs level (which propagates to all sub-files via `use super::*;`).
rustc 2024 edition treats `unused_imports` as a warning by default.

**Concrete case (hyperlane monorepo, PR #34)**: `cli/src/command/mod.rs`
contains `mod r#enum;` + `pub use r#enum::*;`. The only sub-file
`cli/src/command/enum.rs` declares a pure `pub enum CommandType`
without any `use super::*;` chain reference. Adding `use super::*;`
to `mod.rs` raises `warning: unused import: super::*` because:

- the sub-file `enum.rs` doesn't `use super::*;` (audit-pitfalls #21
  exemption — leaf enum with no parent symbol references)
- the `mod.rs` itself doesn't reference any super symbol

**Compounded rule** (extends #21 to the mod.rs level):

1. If a `mod.rs` has any sub-file that uses `use super::*;` (and that
   chain reaches the parent), `mod.rs` MUST keep `use super::*;` (the
   super symbol is consumed via the chain).
2. If **all** sub-files in a `mod.rs` are exempt from `use super::*;`
   per #21 (i.e. leaf enum / struct / type / fn / const files that
   reference no parent symbol), the mod.rs's `use super::*;` is
   legitimately unused and may be omitted.
3. When in doubt, run `cargo check -p <crate>` and look for
   `unused_imports: super::*` warnings — if 0 warnings, the omission
   is consistent.

**Audit script update** (2026-09-14): category 6 should be relaxed to
"missing `use super::*;` AND at least one sub-file uses parent
symbols" — if the sub-file analysis shows zero parent-symbol usage,
the mod.rs's `use super::*;` is exempt. Equivalent check:

```bash
# Detect: does any sub-file use super::* chain to parent?
has_parent_use=0
for f in $(find "$(dirname "$modfile")" -name '*.rs' ! -name 'mod.rs' ! -name 'lib.rs'); do
  if grep -q "^use super::\*;" "$f" 2>/dev/null; then
    has_parent_use=1
    break
  fi
done
if [ "$has_parent_use" -eq 0 ]; then
  # No sub-file uses parent — mod.rs's use super::* is legitimately unused
  continue
fi
```

Verified during hyperlane monorepo migration (PR #34): `cli/src/command`,
`cli/src/help`, `cli/src/version`, `type/src/box_leak`, `type/src/lifetime`
all contain only leaf enum/struct/trait sub-files. `cli/src/logger/mod.rs`
does need `use super::*;` because it has sub-files (impl.rs) that use
super symbols.


## 41. `try_X().unwrap()` in `get_X()` wrappers — INTENTIONAL upstream pattern

A common Rust idiom for projects with explicit `try_X` (Result-returning)
and `get_X` (panicking) APIs is:

```rust
pub fn get_header<K>(&self, key: K) -> String
where
    K: AsRef<str>,
{
    self.try_get_header(key).unwrap()   // panics if missing
}
```

The semantics are explicit: `try_X` returns `Result<T, E>` (caller-
controlled), `get_X` panics (caller asserts presence). The panic in
`get_X` is **part of the API contract**, not a defensive unwrap.

**Audit script (category 3)** currently flags any `unwrap()` /
`expect()` / `panic!()` in `*.rs` files (excluding `/tests/`) as a
violation, without inspecting the call pattern. This produces false
positives for the `try_X().unwrap()` wrapper pattern.

**Concrete case (hyperlane monorepo, PR #34)**: 15 occurrences across
`type/src/request/impl.rs`, `type/src/response/impl.rs`,
`type/src/stream/impl.rs`, `type/src/websocket_frame/impl.rs` — all of
them `try_X().unwrap()` inside a `pub fn get_X(...)` wrapper.

**Detection rule** (would require a smarter audit check, not yet
implemented):
- A `pub fn get_X` whose body is exactly `self.try_X(args).unwrap()`
  (or `.expect(msg)`) — by definition, the function's panic-on-missing
  contract is documented in the surrounding doc comment.

**Currently**: category 3 reports these as violations. PR authors are
expected to either:
1. Accept the FAIL (and document it in the PR description as "upstream
   wrapper pattern — not modified in this PR"), OR
2. Replace `try_X().unwrap()` with `try_X().expect("descriptive
   message")` (audit still flags, but the panic message is more
   useful), OR
3. Change `get_X` to return `Result<T, E>` and propagate with `?`
   (BREAKING — out of scope for migration PRs).

Verified during hyperlane monorepo migration (PR #34): all 15
occurrences follow this pattern. They are upstream code copied from
http-type (crates-dev) and not introduced by the migration.


## 42. Sub-file `external_crate::Type` type annotations in monorepo PR scope — INTENTIONAL upstream carry-over

When merging multiple crates into a monorepo via `mv src core/src`, the
upstream code's type annotations (e.g. `let x: proc_macro2::TokenStream
= ...`, `let level: log::Level = ...`, `let err: notify::Error = ...`)
are preserved as-is. The monorepo PR's scope is "consolidate workspace
structure", not "rewrite each upstream type annotation to a re-exported
alias".

Audit category 17 (`sub-file body uses external crate full path`) only
flags two patterns:

- top-of-file `use external_crate::xxx;` (R6.3 spirit)
- type annotation `: external_crate::Type` (R6.4 spirit)

But it parses `[workspace.dependencies]` only, NOT each sub-crate's
`[dependencies]` — so type annotations like `proc_macro2::TokenStream`
(macros sub-crate), `log::Level` (cli sub-crate), `notify::Error`
(cli sub-crate) are not detected.

**Concrete case (hyperlane monorepo, PR #34)**:

- `macros/src/common/fn.rs`: `proc_macro2::TokenStream` annotations
- `cli/src/logger/impl.rs`: `log::Level`, `log::LevelFilter`
- `cli/src/publish/fn.rs`: `notify::Error`
- `macros/src/inject/fn.rs`: `syn::Ident`, `syn::Path`, etc.

These are all upstream code style; the monorepo PR does not introduce
new violations. They are noted for follow-up cleanup (each sub-crate's
`lib.rs` should `pub use proc_macro2::TokenStream` / `pub use log::Level`
etc. to satisfy R6.4 fully).

**Detection rule** (audit script enhancement, not yet implemented):
parse `[dependencies]` from each sub-crate's `Cargo.toml`, not just
`[workspace.dependencies]` of root. This would catch the
`proc_macro2::TokenStream`-in-macros and `log::Level`-in-cli cases.

**Migration PR convention**: preserve upstream type annotations in the
initial monorepo PR; address each sub-crate's lib.rs re-export in
follow-up PRs scoped to that crate (one PR per crate keeps review
diff small).

## 43. Check 19 false positives — R14.7 `tests/<sub>/fn.rs` non-super use (2026-09-25 new check)

Check 19 wraps `verify_test_imports_centralized.sh`. The script's detection:

- Path glob: `*/tests/*/fn.rs` — any `tests/` immediate subdir whose filename
  is exactly `fn.rs`. This **deliberately** skips `tests/mod.rs` (the test
  crate root) and `tests/<sub>.rs` (loose integration-test files at root).
- Each matching file: extract every line matching `^use ` at column 0, then
  subtract lines that are exactly `use super::*;` (fixed-string match, no
  regex pitfalls). What's left = violation.

Known **non**-false-positive cases (these are real violations; auto-fixable):

1. `tests/<sub>/fn.rs` has `use std::path::Path;` at the top.
   Fix: move to `tests/<sub>/mod.rs` as `pub use std::path::Path;`,
   delete from `fn.rs`. Or run `strictify_tests_layout.py`.
2. `tests/<sub>/fn.rs` has `use wasm_bindgen_test::wasm_bindgen_test;`.
   Same fix path — move to mod.rs as `pub use wasm_bindgen_test::wasm_bindgen_test;`.
3. `tests/<sub>/fn.rs` has `use web_sys::HtmlElement;` or similar.
   Same fix path — move to mod.rs as `pub use web_sys::HtmlElement;`.
4. `tests/<sub>/fn.rs` has `use crate_name::SomeType;`.
   Same — but FIRST confirm the type is `pub` (if `pub(crate)` the test
   belongs to a deleted path per §14.4 — there's nothing to re-export).

Known **actual** false-positive patterns (the script's logic intentionally
excludes these; if you see one reported, file a bug):

1. None known yet. **The check is new (2026-09-25)**; run it on every
   eastspire-owned repo and add new entries here as they appear.

**Auto-fixer caveat**: `strictify_tests_layout.py` always rewrites
`tests/<sub>/mod.rs` even if `fn.rs` was already compliant — it normalizes
mod.rs to: top `pub use xxx;` block(s) + `mod r#fn;` + `use super::*;`.
Run it twice on a clean repo: second run should print `0 0 0` for all
counts (sub mod.rs / sub fn.rs / loose .rs). If not, debug before
claiming compliance — usually means upstream code has a corner case
the strictifier doesn't model.

If R14.7 FAIL surfaces in CI but the **only** offending file is one your
PR didn't touch (i.e. upstream had this violation historically): don't
fix it in this PR — open a follow-up PR scoped to that one test file.
Reasons:
- Mixing R14.7 cleanup with your actual feature diff dilutes review.
- Audit check 19 only flags files in the git diff against origin/master
  (when audit-runs from the PR's perspective) — so if CI ran against
  master HEAD, that's the upstream state. Confirm with
  `git diff origin/master..HEAD -- '*/tests/*/fn.rs'` first.

**Reference**: `references/14-testing.md §14.7` for the full prose.

## 44. §13.7 排序规则第四轮变更(2026-09-26,length+lex)

`verify_dep_order.py` 在 2026-09-26 升级为第四轮规则:**本地 vs 三方分组,组内按 entry 完整长度升序 + 长度相同按 dep key 字典序**。前 3 轮规则版本:

- 第一轮 (2026-09-14):块内 (key 长度, 字典序)
- 第二轮 (2026-09-14):(len, lex) + workspace.dependencies alphabetic,无分组空行
- 第三轮 (2026-09-14):本地 vs 三方分组 + 组内 alphabetic + 唯一空行在组边界
- **第四轮 (current, 2026-09-26):本地 vs 三方分组 + 组内 (entry 完整长度, key 字典序) + 唯一空行在组边界**

**用户原话**:「toml依赖导入需要严格遵守顺序,首先本地依赖是同一组,外部依赖是一组,不同组之间需要空行分割,同组之间按照完整的长度(含特性等字段)升序排序,一样的长度按照字典序升序」。

**脚本实现要点**:

- `expected_order_with_blank` 内:排序 key 从 `lambda kv: kv[0]`(纯字典序)改为 `lambda kv: (_entry_chars(kv[1]), kv[0])`。
- `_entry_chars(raw_lines)`:把每个非空行 `.strip()`,用 `" ".join(...)` 拼起来,再 `re.sub(r"\s+", "", ...)` 去所有空白,返回 `len`。这样 `serde = { version = "1.0.229", features = ["derive"] }` 长度是 46,`toml = "0.9.12"` 长度是 14,与 tablo formatter(默认 `=` 两侧空格、4 空格缩进)无关。
- 双向验证 fixture:compliant `demo-cli < demo-core < demo-engine < demo-macros, clap < serde < serde_json < tokio` 排列 = exit 0;violated 打散 = exit 1 且 actual/expected 反向可见。

**euv 单仓实测结果**(2026-09-26,在第四轮规则下):

| 文件 | 当前轮(第三轮 alphabetic)顺序 | 期望(第四轮 length+lex)顺序 |
|---|---|---|
| `euv/Cargo.toml [dependencies]` | `euv-core, euv-macros` 本地 → `alloc, console, js-sys, lombok, wasm, wasm-futures, web-sys` | `euv-core, euv-macros` 本地 → `js-sys, web-sys, wasm, lombok, alloc, wasm-futures, console` |
| `euv/Cargo.toml [workspace.dependencies]` | 7 个本地 alphabetic → 27 个三方 alphabetic | 7 个本地按 path 长度排(`euv < euv-ui < euv-cli < euv-core < euv-engine < euv-macros < euv-example`)→ 三方按 entry 长度排(`log < toml < quote < chrono < ignore < js-sys < if-addrs < hyperlane < serde_json < lombok < proc-macro2 < color-output < hyperlane-cli < wasm-bindgen < alloc-no-stdlib < compare_version < serde-wasm-bindgen < wasm-bindgen-test < wasm-bindgen-futures < console < clap < serde < syn < qrcode < notify < tokio < web-sys`) |
| `euv/cli/Cargo.toml [dependencies]` | 全三方 alphabetic | 全三方按 entry 长度排 |

**为什么这个变更值得记录到 audit-pitfalls**:第三轮 → 第四轮的迁移是破坏性的,任何 euv / hyperlane / crates-dev / docs-pages 仓跑 `verify_dep_order.py` 都会大量 FAIL,**仓主需要在第四轮迁移前接受一次性大批量重排**(每个 dep 块的条目都按 entry 长度重排,涉及的 PR 数量级是一次重排)。不放在 audit-pitfalls.md 记录,未来 session 在 review 旧 PR 时会以为 `verify_dep_order.py` 是 bug。

**注意**:workspace root 与单 crate root 行为差异。`is_local` 依赖 `[workspace] members` 列表解析;fixture 不写 `[workspace]` 时,本地组会被认为是空、整块当三方处理。真实仓上不会撞到这里(workspace.toml 总是带 `[workspace]` 段)。


## 45. audit shell template wraps a `.py` script with `bash <script.py>` instead of `python3 <script.py>` — 2026-09-26 `verify_dep_order.py` 接入实测

**Symptom**: Audit check 21 calls `verify_dep_order.py` and the wrapper hangs with `exit code = 127` and stderr `syntax error near unexpected token '('`.看上去像是 shell 报错,但实际上——

**Root cause**: 在 audit check 21 的 `CHECKS.append` shell template 里写了 `bash "{{audit_script_dir}}/verify_dep_order.py" "{{target}}"`,把 Python 脚本喂给 bash 当 shell 脚本执行。bash 看到脚本里的中文双引号 docstring `"完整的长度..."` 立刻 syntax error,exit 127。

**Wrong**:
```bash
bash "{{audit_script_dir}}/verify_dep_order.py" "{{target}}"
```

**Right**:
```bash
python3 "{{audit_script_dir}}/verify_dep_order.py" "{{target}}"
```

脚本头部已有 `#!/usr/bin/env python3` shebang,但 `bash <script.py>` 不读 shebang —— bash 永远把后缀是 `.py` 的文件也当 bash parse。**audit wrap 一个 Python 脚本必须显式 `python3 <script.py>`,不可省**。

**Detection**:
- audit 跑出 `exit 127` + stderr `syntax error near unexpected token` —— 100% 是 wrap 成 `bash *.py` 了
- audit 跑出 `exit 2` 且找不到 toml —— 可能是 `cwd=` 不对 或 `find` 路径过滤问题(见 §46)

**Verification**: 双向 fixture 自测 compliant→0 + violated→1,数据可见,exit 0/1,不是 127。

## 46. `find -not -path '*/tmp/*'` 误过滤 `/tmp/...` 测试根 — 2026-09-26 `verify_dep_order.py` 接入实测

**Symptom**: 接 audit check 21 双向 fixture 自测时,临时的 `/tmp/dep_order_test_*` 仓根被 `find` 跳过,`verify_dep_order.py` 报 `exit 2`(内部 `if not files: return 2`)。

**Wrong**:
```bash
find str(root) -name Cargo.toml -not -path '*/target/*' -not -path '*/tmp/*'
```

`-not -path '*/tmp/*'` 匹配任何路径里出现 `/tmp/` —— 包括合法 `/tmp/dep_order_test_compliant/Cargo.toml`,整个测试根都被过滤掉。

**Right**(命名空间粒度):
```bash
find str(root) -name Cargo.toml -not -path '*/target/*' -not -path '*/tmp/test_*'
```

`-path '*/tmp/test_*'` 只匹配 `tmp/test_xxx/...`(cc / crate-cli 的 test-helper fixture),不会误伤 `/tmp/<fixture-root>/...`。

**两条规则**:
1. 任何 verifier script 的 `find`/`walk`/glob 过滤,不要写 `*/tmp/*` 这种全名空间 broad 匹配
2. 用 verifier 仓根做 fixture 测试时,fixture 路径不能用 verifier 不希望过滤的子串(`/tmp/`、`/target/`、`*/.cargo/registry/*`);否则过滤器把 fixture 自己也过滤掉,verifier 报"0 files",看起来像 verifier bug。

## 47. verifier → audit wrapper 的 stdout 过滤与 exit-code 传递契约 — 2026-09-26 check 21 接入实测

**Symptom**: 接入 verifier 到 audit 时,如果 verifier exit 0 也打印 status line(例如 `N files checked, 0 violations`),audit 把它当成 violation hit 显示,变成 false-fail。

**契约**(audit 默认把任何非空 stdout 当 FAIL 看待,见 §43 + §35-B):

```bash
cd {{target}}
python3 "{{audit_script_dir}}/verify_<rule>.py" "{{target}}" \
    | grep -v -E '^[0-9]+ files checked, 0 violations$'
exit_code=${PIPESTATUS[0]}
test "$exit_code" -ne 0 && echo "FAIL: verify_<rule>.py exited $exit_code"
exit "$exit_code"
```

三个关键点:

1. `grep -v -E` 过滤**只是**成功路径尾随行(`0 violations`),让违规文件路径 + actual/expected diff 原样抛给 audit 显示
2. `${PIPESTATUS[0]}` 捕获 verifier 的 exit code(不是 `grep` 的,也不是 `head` 的)
3. `exit "$exit_code"` 把 verifier 的真实 exit 透传给 audit runner(`run_check` 数 `r.stdout` 但 `audit_rust_standards.main` 看最终 subprocess 的 returncode)

**常见错误**:
- 用 `bash -c "...; echo PASS"` 而 verifier 失败时`; echo "FAIL: ..."` 替换 stdout 但 exit 0 —— audit 看 stdout 知道是 fail,但 exit 0 让 main 当 PASS
- 直接 `python3 verify.py 2>/dev/null` 吃掉 verifier 的真实错误日志
- 把 `tail -1` 加在 pipeline 末尾覆盖了真实 exit code

**Detection**: 接入任何 verifier 到 audit 后,**必须双向 fixture 自测**:
- compliant 仓:audit check N 输出 PASS,suite 计数 +1(通过)
- violated 仓:audit check N 输出 FAIL,suite 计数不增;FAIL message 包含实际违规文件的行号

然后跑完整 audit `python3 ~/.agents/skills/rust-standards/scripts/audit_rust_standards.py <repo>` 看 `SUMMARY: N/M PASS`,N = 通过的项数,M = 总项数。

## 48. verifier 与 auto-fixer 必须共用一套 parse 逻辑(2026-09-26 fix_dep_order.py 接入实测)

**Symptom**: verify 报 "实际顺序 = [...], 期望顺序 = [...],但我手动排好的 fix 写盘后,fix 再跑一次 verifier 报 FAIL(actual vs expected 不一致)——明明 verify 与 fix 用的是同一份 round 4 规则。

**Root cause**: verifier 自己一份 parse 逻辑(Cargo.toml → 4 类块 → entry list),fix 又写一份 parse 逻辑(从 ASCII 文本重建 block);当 entry 跨多行(tokio features `[ ... ]` 跨 6-10 行)或 entry 内部有 bracket(`notify = { ... features = [ ... ] }`),两套 parsers 对"一个 entry 的边界"看法不同 → fix 用它自己的 parser 决定"完成 entry 边界"的位置,写出 fix 内容但 verifier 用它的 parser 重新 tokenize 后认为多/少了 entry → mismatch。

**Prevention — verifier 模块必须 expose parse API + auto-fixer re-import**:

```python
# scripts/fix_dep_order.py 头部
import importlib.util
VERIFY_SCRIPT = Path(__file__).resolve().parent / "verify_dep_order.py"
_SPEC = importlib.util.spec_from_file_location("verify_dep_order", VERIFY_SCRIPT)
assert _SPEC is not None and _SPEC.loader is not None
_verify = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_verify)

KEY_PATTERN = _verify.KEY_PATTERN
parse_block = _verify.parse_block
_entry_chars = _verify._entry_chars
find_cargo_tomls = _verify.find_cargo_tomls
read_local_crate_names = _verify.read_local_crate_names
```

**之后 fix 脚本仅在下列点偏离 verifier**:
- 排序逻辑:verifier 排序后用作 expected,fix 排序后用作 fix 后 actual
- entry 文本提取与重组:verifier 把 block 切成 (key, lines) tuples 后丢掉 lines;fix 拿到 tuples 后重排 lines,按 round 4 规则组装 block 文本

**这套规则适用于任何 structural-config 校验**:
- `verify_*.py` 提供 `parse_*` / `expected_*` 函数
- `fix_*.py` import `verify_*.py` 的函数,只做"重排 + 重组"
- 任何"verifier 与 rewriter 各自实现一遍 parse"的代码 = review reject,合并到一个 parser

**Detection**: fix 跑完后再跑 verify,应 exit 0;循环 `fix && verify && fix && verify` 第二次必须 no-op(幂等)。若不幂等 → 两套 parsers 分歧,立即合并到一个 verifier 模块。

## 50. Long rust-refactor sessions: commit incrementally or worktree gets auto-pruned and 6 turns of work vanish (2026-09-26)

**Symptom**: A session that does 6+ turns of cross-cutting Rust refactor (Request/Response API redesign, parser module split, field flatten, etc.) on a `git worktree` branch can lose **all uncommitted work** if:

- The user follows the "user owns merge decisions" rule and the agent never `git commit`s during the refactor (defers to user at end)
- Another agent run on the same machine does `git worktree prune` on a parent shell, or the `.worktrees/<name>` directory is wiped by cleanup/session tooling
- The branch's HEAD still points at the base commit because nothing was committed

`git fsck --unreachable --no-reflogs` returns 0 unreachable commits and `git reflog --all` shows the worktree path's HEAD reset to base. **The refactor is gone**, not recoverable from git.

**Concrete loss** (this session, refactor of `hyperlane-type::Request`):
- 9 files modified across 6 turns (~1500 LOC)
- 0 commits made during refactor (deferred per "user owns merge decisions")
- Worktree directory disappeared between sessions
- Branch `refactor/request-api-align-core` still at `499ebb5` (base); no new commits
- 0 unreachable blobs / unreachable commits — reflog cleared

**Rule** (durable lesson for any future rust-refactor session):

1. **After every completed refactor slice** (each coherent change set: "parser module split", "host field removal", "headers VecDeque flatten", etc.) run:
   ```bash
   git add <files>
   git commit -m "refactor(<scope>): <slice-name>

   <what changed + why>

   Co-authored-by: agent"
   ```
   Push or not — doesn't matter; the commit is the recovery point.

2. **If the user really wants one squashed PR at end**, at minimum `git stash` after each slice:
   ```bash
   git stash push -u -m "<slice-name>" -- <files>
   git worktree add .worktrees/<refactor> <branch>
   cd .worktrees/<refactor>
   git stash pop
   ```
   The stash survives worktree prune because stash reflog is global, not per-worktree.

3. **Verify recovery before continuing**:
   ```bash
   git -C <worktree-path> rev-parse HEAD  # should match base + N
   git -C <worktree-path> status --short  # should be empty between commits
   ```
   If HEAD is at base and `git status --short` is empty after slice N, the slice didn't commit — re-commit or stash before next turn.

**Why this is hard rule, not optional**:

- User's "user owns merge decisions" rule is about the **PR**, not the local commit granularity. `git commit` on a feature branch (not master) doesn't violate that rule — user still reviews + merges the squashed / rebased PR. Local commits are safety checkpoints.
- A refactor touching 5+ files is structurally a 5+ slice task. Bundling all into one commit at end means one bash slip / worktree prune / git reset wipes the entire session.
- Re-doing 6 turns of refactor from memory is impossible — specific patch blocks, exact code, exact Lombok attribute syntax can't be re-derived.

**Recovery if the disaster already happened**:

- Check `git fsck --unreachable --no-reflogs` first — if any unreachable blobs/commits exist, recover via `git stash list` + `git show <unreachable-sha>:<path>`.
- Check the agent's session_search (compacted history may have file contents).
- Otherwise: stop, tell the user honestly what was lost, ask if they have a backup or want to restart from scratch with the incremental-commit rule applied.

**When this rule does NOT apply**:

- Single-file edits / 1-2 turn tasks — `git commit` after each is still cheap insurance, but the disaster window is narrow enough that worktree prune is unlikely to land.
- Worktree-free workflows (editing directly on master or single non-worktree branch) — `git commit` is still preferable but no worktree-prune failure mode exists.
- Truly atomic single-commit tasks (rename one symbol across 30 files in one commit) — one commit at the end is fine, because the change is atomic and a stale worktree's HEAD still has the right files.

## 49. Check 22 (§17) — `verify_ci_no_bump.py` 接入 audit 实战 (2026-09-26)

新增 §17:CI 流水线不允许 bump / 写 `version =` 行。配套 verifier `scripts/verify_ci_no_bump.py` 在三仓( ctares / hyperlane / euv )首次接入时的实测 pitfall 列表。

### 49.1 — `python3 -c` 内嵌 regex 跨多层 shell + python 转义(2026-09-26 实测)

CI 工作流的 inline python 脚本(如 `docs/Cargo.toml` version 镜像脚本)会把 regex `version\s*=\s*\"` 通过 bash 单/双引号 → python `r'...'` 再传到 `re.sub`。每一层都可能再加一层 backslash escape:

```bash
# 第 1 层:原始 regex 文本
version\s*=\s*"

# 第 2 层:bash 双引号包裹,无转义
"import re; re.sub(r'version\s*=\s*\"[^\"]*\"', ...)"

# 第 3 层:bash 单引号包裹,无转义
'import re; re.sub(r"version\s*=\s*\"[^\"]*\"", ...)'

# 第 4 层(罕见):heredoc + bash escape,会被加倍
<<EOF
VERSION="\$VERSION" python3 -c "...re.sub(r'^(version\\s*=\\s*\\"[^\\"]*\\")',...)"
EOF
# 在 yml 文件中实际写入的字节是:
# version\\s*=\\s*\\"  ← 两个反斜杠
# 甚至 version\\\\s*=\\\\s*=\\\\"  ← 四个反斜杠(多层嵌套)
```

**正确做法**:verifier 的 `PYTHON_VERSION_LITERAL_RE` 不要尝试精确匹配 `\s` `*` `\"` 等子串;改用宽松模式 `version\s*[^\"']*?\s*=\s*[^\"']*?[\"']`,接受 0-多个反斜杠 + 任意非引号字符 + 最终引号。配合上游 python-write-keyword(`write_text` / `re.sub(` / `.replace(` 等)的存在,误报率几乎为 0。

### 49.2 — allowlist marker 必须 tightly-coupled(2026-09-26 实测)

verifier 支持 `# ci-allow-version-write: <reason>` 注释豁免某行违规。最初设计允许 marker 在 violation 上方 6 行内匹配,实测中:

- 6 个 `echo` 之后接 marker 接 python invocation 的 fixture 里,marker 距 violation **正好 1 行**(第 13 行的 marker,第 14 行的 python)→ 仍被豁免。
- 但若 marker 上方还有几行 echo(脚本扩展等),marker 距离 violation 变成 2+ 行 → 仍被豁免(误报 PASS)。

**正确做法**:把 marker 距离缩到「紧挨 violation 的上一行」(`lines[lineno - 2]` 即 0-indexed `lineno - 2`)。任何 2 行及以上的间隔都不豁免,迫使 author 把 marker 紧贴 violation 写,不易漏看。

### 49.3 — `cc` / `crate` 是同一个工具的两种 binary name(2026-09-26 实测)

crate-cli 在不同发布版本里 binary name 是 `cc`(老版本)或 `crate`(新版本,per `crate-cli v0.2.5` cargo install list 显示 `cc`,但 `0.2.8` 已改)。**正确做法**:verifier 用 `\b(?:cc|crate)\s+bump\b` 同时匹配两种 binary,不要硬编码。

### 49.4 — `sed -i` 与 read-only `sed -E` 必须区分(2026-09-26 实测)

CI workflow 里有两类 `sed` 调用:

```bash
# 读:VERSION=$(grep ... | sed -E 's/^version = "([^"]+)".*/\1/')  # 提取,允许
# 写:sed -i 's/version = ".*"/version = "9.9.9"/' Cargo.toml        # 改写,禁止
# 写:sed ... > Cargo.toml                                           # 改写,禁止
# 写:sed ... | tee Cargo.toml                                       # 改写,禁止
```

**正确做法**:`SED_VERSION_WRITE_RE` 只匹配 `sed -i` / `perl -pi` / `> file` / `| tee file` 这四种写盘模式,不匹配 `$()` 替换里的只读 sed。配上 `SED_VERSION_LITERAL_RE = \bversion\b`,只在「写盘 + 涉及 version」两个条件都满足时违规。

### 49.5 — euv docs/Cargo.toml mirror script: removed, version now human-maintained (2026-09-26)

`euv-dev/euv/.github/workflows/rust.yml` originally had an inline
python step mirroring root's `version =` into the non-workspace-member
`docs/Cargo.toml`:

```bash
VERSION="$VERSION" python3 -c "import re,pathlib,os; p=pathlib.Path('docs/Cargo.toml'); t=p.read_text(); p.write_text(re.sub(r'^(version\\s*=\\s*\\\"[^\\\"]*\\\")', lambda m: m.group(1) + os.environ.get('VERSION','0.0.0') + m.group(2), t, count=1, flags=re.M))"
```

The user deleted this script in preference of having authors update
`docs/Cargo.toml` by hand in the same PR that bumps root. After
deletion the euv workflow has zero `version =` writes and verifier
returns exit 0 cleanly. Trade-off documented in
`rust-workspace-release` "Non-workspace-member manifests" sub-section.

The allowlist-marker path (`# ci-allow-version-write: docs mirror`)
was the alternative; the user rejected it because it required adding a
comment to the workflow, which conflicted with the same user's "no
explanatory comments in CI" rule (`rust-workspace-release` "Keep CI
workflows free of explanatory comments" sub-section).

If a new repo shows the same shape, the decision is repo-local — ask
the user which side of the trade-off they prefer; do not default.

---

## §54-§57 — 2026-09-26 second iteration (user-driven, checks 29-32)

User 原话 (2026-09-26 第二轮):

> "mod.rs 的 mod 前面不能有可见性"
> "rust skill 里的其他内容也需要通过脚本完成校验"

This iteration adds 4 new verification scripts (checks 29-32) covering
4 previously-non-scripted or partially-scripted rules.  Bidirectional
fixture self-tests are mandatory before audit wiring (same protocol as
§49-§53).

### §54 — verify_mod_visibility.py (check 29, §6.2)

User explicitly added §6.2 in this round:
`mod r#xxx;` in mod.rs MUST be bare — no `pub mod`, no `pub(crate) mod`,
no `pub(super) mod`.  Older codebases have stray `pub(crate) mod r#xxx;`
lines (euv `cli/src/build/mod.rs:4` had one).  Implementation:

- Regex: `^(?:pub(?:\([^)]*\))?\s+)?mod\s+`.  Matches `pub mod`,
  `pub(crate) mod`, `pub(super) mod`.  Bare `mod` skips through.
- Filter by file basename: only `mod.rs` is audited.  All other
  files are exempt because `pub mod foo;` in `lib.rs` is the
  correct way to declare a public module.
- Raw-string-aware: lines inside `r#"..."#` raw string literals
  are skipped (mirrors `verify_doc_comment_format.py`).

Bidirectional fixture test:
- Compliant: 0 violations / exit 0
- Violating: 3 violations (pub, pub(crate), pub(super)) / exit 1

Real-workspace finding (euv PR #40): 1 hit at
`cli/src/build/mod.rs:4: pub(crate) mod r#inline;`.

### §55 — verify_no_allow_lints.py (check 30, §14)

User original (2026-09-14): "从根源修复 warn, 禁止使用 allow 宏".
Existing check 2 in `audit_rust_standards.py` was git-diff scoped:
only flagged `#[allow(...)]` introduced in the current PR.  This
left historical `#[allow]`s in the codebase invisible to the audit.
The new script does tree-wide scan:

- Regex: `^\s*#\[\s*(?:allow|expect)\s*\(` — catches all variants
  (allow, allow(unused), allow(clippy::xxx), expect(...), etc.).
- Exemptions:
  - Inside `#[cfg(test)] mod tests { ... }` block (the test
    helper function may legitimately silence unused warnings).
  - Inside any `tests/` directory tree (R14.7 self-contained).
- Coexists with check 2 (git-diff scope).  Both can be active;
  check 2 is the PR gate, check 30 is the baseline gate.

Bidirectional fixture test: 0/3 violations.

Real-workspace findings:
- ctares: 4 hits.
- euv: 1 hit.

### §56 — verify_explicit_type_annotations.py (check 31, §5.1)

User original (rule 6, 2026-09-26): "所有变量 / 参数 / 返回值必须显式
类型".  The existing check 12 in `audit_rust_standards.py` only catches
`Vec::new()` (single regex).  The new script catches all 12 standard
collection constructors + the `Vec<_>` placeholder pattern:

- Regex family 1: `let <name> = (Vec|VecDeque|HashMap|HashSet|BTreeMap|
  BTreeSet|LinkedList|BinaryHeap|String|Box|Rc|Arc)::new();` — catches
  bare collection constructor without type annotation.
- Regex family 2: `let <name>: Vec<_> = ...collect();` — catches the
  `Vec<_>` placeholder which defeats the rule's purpose (reader still
  has to infer the element type).
- Skips `tests/` (R14.7 self-contained).

Bidirectional fixture test: 0/4 violations.

Real-workspace findings: ctares 1 hit, euv 0 hits.

### §57 — verify_no_wasm_inline.py (check 32, §12)

User original (rule 12, 2026-09-26): "WASM 项目禁止所有 inline 注解".
This is a WASM-specific rule — only applies to crates declared as
`crate-type = ["cdylib", ...]` in their Cargo.toml.  Pure rlib /
bin crates are unaffected.

Implementation:

1. Find all `Cargo.toml` files in the tree, skip `target/` and
   `.cargo/registry/`.
2. For each, regex `crate-type\s*=\s*\[?\s*["\']cdylib["\']` — if
   matches, this crate is a cdylib crate.
3. For each cdylib crate, audit its `src/` tree for `^\s*#\[\s*inline
   (?:\s*\([^\)]*\))?\s*\]` — matches `#[inline]`, `#[inline(always)]`,
   `#[inline(never)]`.
4. If no cdylib crates exist, exit 0 with "rule §12 not applicable".

Bidirectional fixture test: 0/3 violations (all 3 inline variants
caught).



---

## §58-§61 — 2026-09-26 third iteration (user-driven, checks 33-36)

User 原话 (2026-09-26 第三轮):

> "let 的类型必须要显示标注 (包含 let _ = )"
> "闭包参数需要显示标注"
> "非单侧的 fn 必须要符合格式的文档注释"
> "硬编码字符串必须要维护到 const.rs"

This iteration adds 4 new verification scripts (checks 33-36) covering
4 hard rules the user explicitly added in this round.  All scripts
pass bidirectional fixture self-tests before audit wiring (same
protocol as §49-§57).

### §58 — verify_let_type_annotations.py (check 33, §5.1 comprehensive)

User explicitly added §5.1 in this round:
"let 的类型必须要显示标注 (包含 let _ = )" — every `let` binding,
including `let _ = ...`, MUST declare its type.

This is the **comprehensive** successor to `verify_explicit_type_annotations.py`
(check 31), which only catches collection constructors specifically.
The new script catches ALL `let` bindings without `: T` annotation:

- `let x = 5;` — violation
- `let s = "hello";` — violation
- `let v = vec![1, 2, 3];` — violation
- `let _ = fs::remove();` — violation (per user explicit)
- `let _: T = expr;` — ok
- `if let Some(x) = ...` — exempt (pattern guard, not let stmt)
- Rust 2024 let-chains `if let X = ... && let Y = ...` — exempt
  (regex won't match second `let` in chain)

Bidirectional fixture test: 0/5 violations.

Real-workspace findings:
- ctares: 34 hits.
- euv: 333 hits.

### §59 — verify_closure_type_annotations.py (check 34, §5.2)

User explicitly added §5.2: "闭包参数需要显示标注".  Closure
parameters must have explicit `: T` annotation.  Implementation
heuristic:

- Regex `\|(?P<params>[^|=][^|]*?)\|` finds closures.  Empty
  `||` (operator) is excluded by the `[^|=]` first-char requirement.
- Param splitter `_split_top_commas()` walks the captured string
  character-by-character, tracking `<>`/`()`/`{}` depth, splitting
  only on top-level commas.
- Each param is checked via `_has_explicit_type()`:
  - `..` (rest pattern) — exempt
  - `&pat: T` or `&mut pat: T` — ok
  - `(pat): T` (tuple destructure with type) — ok
  - bare `name` or `_name` without `: T` — violation
  - `name: T` — ok
- The script handles `|x: &u32|`, `|(a, b): &(u32, u32)|`, and
  `|&x: &T|` correctly.

Bidirectional fixture test: 0/5 violations (including tuple
destructuring without type).

Real-workspace findings:
- ctares: 102 hits.
- euv: 179 hits.

### §60 — verify_doc_comment_format.py (check 35, §2.1 / §2.2 authoritative)

User explicitly added §2.1: "非单侧的 fn 必须要符合格式的文档注释".
The existing check 25 (also `verify_doc_comment_format.py`) was
de-duplicated; this check 35 is the AUTHORITATIVE entry per user
iteration.

Test files are exempt because R14.5 forbids ALL comments in test
files; thus no `///` doc comments there either.  Non-test fn /
impl method must have `///` doc comment with:

- Layer 1 (existence): at least one `///` line above fn/impl.
- Layer 2 (completeness): `# Arguments` section if non-self params,
  `# Returns` section if non-() return.
- Layer 3 (format): argument items use `- \`Type\` - description`
  form, return items use `- \`Type\`: description` form.

Bidirectional fixture test: 0/3 violations.

Real-workspace findings: ctares 1048 hits, euv 3151 hits.  These
are large-scale coverage gaps — projects need a sustained
doc-comment addition campaign.  Per pitfall §39a, use the
`doc_comment_audit.py` fixer (`--write`) to bulk-add template
doc-comments before manual review.

### §61 — verify_hardcoded_strings.py (check 36, §1.3c strengthened)

User explicitly added §1.3c strengthened: "硬编码字符串必须要维护到
const.rs".  This is the **comprehensive** successor to the
fn.rs-only byte/char/multi-char check 18.  Catches ALL string
literals (≥ 4 non-trivial chars) in any non-const file.

Implementation:

- Regex `r"([^"\\]|\\.){4,}"` finds string literals.
- Per-line filter:
  - `const.rs` itself — exempt (canonical home).
  - `tests/` — exempt (R14.7 self-contained).
  - Lines starting with `#[` — exempt (attribute lines like
    `#[doc = "..."]` / `#[serde(rename = "...")]`).
  - Format macro format strings — exempt via
    `_is_format_macro()` heuristic: finds `<macro>!(<str>...)`
    where the string is the FIRST positional argument.
  - Otherwise — violation.

Bidirectional fixture test: 0/4 violations.

Real-workspace findings: ctares 447 hits, euv 3384 hits.  This is
the largest single-class violation; will require sustained
const-extraction work, especially for `eprintln!`/`println!`
arguments (which are exempt but adjacent code may have other
hardcoded strings).

### §62 — verify_keyword_file_purity.py first-line check applies to mod.rs (false positive class)

`verify_keyword_file_purity.py`'s `_check_first_line_super()` runs on
EVERY file with a KEYWORD_BASENAMES basename — including `mod.rs`. But
§6.2 says `mod.rs` first line MUST be `mod r#xxx;` (the three-stage
template). The first-line rule (§6.3 sub-file rule) does NOT apply to
mod.rs. Verifier produces ~80+ false-positive hits on every `mod.rs`
whose first line is `mod r#const;` or similar.

Symptom: `audit_rust_standards.py` check 23 reports "X hits in Y files"
with hit count vastly exceeding real first-line violations (e.g. 135
hits when only 5 are real).

Fix path (skill-script side, out of workspace scope): exempt mod.rs
from `_check_first_line_super()` in `verify_keyword_file_purity.py`.

Workaround when running audit on workspace: filter check 23 output for
non-mod.rs lines only — those are the real first-line violations.

### §63 — verify_dep_order.py crashes on `cli/tmp/test_*/Cargo.toml` fixtures, Traceback counted as 135 hits

`verify_dep_order.py` `check_file_v2` has a `return violations`
statement indented INSIDE the `for sec in [...]` loop. When a Cargo.toml
file (e.g. `cli/tmp/test_sync_no_version/Cargo.toml` fixtures used by
the audit self-test) contains no matching dep sections, the loop
falls through and the function returns `None`. The main() then iterates
`for v in check_file_v2(...):` → `TypeError: 'NoneType' object is not
iterable`.

The Traceback lines (130+) are emitted to stdout. `audit_rust_standards.py`
`run_check` counts `len(out)` where `out = [l for l in r.stdout.strip().split('\n') if l]`
— so Traceback lines become "hits" and check 21 reports 6 violations
with 130+ Traceback lines inflating the count, even though exit code is
non-zero for a non-violation reason.

Fix path (skill-script side): move the `return violations` out one
indent level (line ~249) so it runs after the for-loop completes, not
inside it.

### §64 — `and_then` closure receives Ok value, not Err

`Result<T, E>::and_then(F)` requires `F: FnOnce(T) -> Result<U, E>` —
the closure receives the `T` (Ok value), NOT the `E` (Err). So when
adding closure type annotations:

- `write_all(&data)` returns `Result<(), io::Error>` → `and_then(|_: ()| flush())`
  not `and_then(|_: io::Error| flush())`.
- `.ok().and_then(|u: HttpUrlComponents| u.host.clone())` — closure
  receives the Ok-wrapped T, type-annotated as T itself (not &T).

Verifier `verify_closure_type_annotations.py` does NOT type-check
closures — only checks for `: T` annotation presence. So getting the
type wrong compiles under audit but fails `cargo check` with
`type mismatch in closure arguments` (E0631).

Always sanity-check closure type annotations with `cargo check` after
applying bulk regex fixes.

### §65 — `Option::map_or` passes T by value, not &T

`Option<T>::map_or(default, F)` requires `F: FnOnce(T) -> U` — closure
receives the unwrapped `T` by value (move), NOT `&T`.

Common false annotation in macros:
- `try_get_header_back(...)` returns `Option<String>` → `.map_or(true, |referer_header: &String| ...)` WRONG, compiler error.
- Correct: `.map_or(true, |referer_header: String| ...)` or `|referer_header: ::hyperlane_core::RequestHeadersValueItem|`.

Compare with `HashMap::get(K)` returns `Option<&V>` → `.map(|value: &V| ...)`
takes `&V` (because the Ok value of `Option<&V>` is itself `&V`).

When in doubt: `Option<&T>::map_or(default, |x| ...)` takes `&T`.
`Option<T>::map_or(default, |x| ...)` takes `T` (moved).

### §66 — audit-verifier output count vs. real violation count

`audit_rust_standards.py` `run_check()` returns `out = [l for l in r.stdout.strip().split('\n') if l]`
and reports `FAIL: NN. <name>: {len(out)} hits`. The count is **all
non-empty stdout lines**, not the number of violations.

When a verifier script crashes with a Traceback (e.g. verify_dep_order.py
on fixture Cargo.toml), the Traceback is on stderr but mixed with stdout
output. Even if exit code is non-zero for the RIGHT reason, the count
can be inflated by Traceback lines.

When the reported hit count seems suspiciously high relative to the
visible violation lines (e.g. 135 hits in 5 visible lines), suspect
verifier crash + Traceback inflation. Run the verifier standalone and
look at its actual output.

Cross-check: `audit_rust_standards.py` template `if [ "$exit_code" -ne 0 ]; then echo "FAIL: ..." >&2; fi`
puts diagnostic on stderr, so the FAIL trailer itself doesn't pollute
stdout count — only the verifier script's stdout counts.


---

## §62 — 2026-09-26 fifth iteration (user-driven, check 37)

User 原话 (2026-09-26 第五轮):

> "对于 lib.rs 必须要检查是否存在 //! 注释,注释第一行 //! 后是
>  包名后面是一行 //! 再后面才是内容"

This iteration strengthens the existing lib.rs comment policy from
"allowed but optional" (§17 historical) to MANDATORY 3-line structure.
The new script `verify_lib_rs_doc_comment.py` reads the nearest
`Cargo.toml`'s `[package].name` field and validates that lib.rs
starts with:

  //! <package_name>     // text must equal [package].name
  //!
  //! <description>      // content

Implementation:

1. Walk up from `lib.rs` to find the closest `Cargo.toml`.
2. Parse `[package].name` (regex `^\s*name\s*=\s*"(?P<name>[^"]+)"`).
3. For each `lib.rs`:
   - First non-blank line must be `//!` (else: violation).
   - First `//!` line text must equal `[package].name`
     (else: violation, mismatch).
   - Second `//!` line must be EMPTY (just `//!`) — the
     canonical separator (else: violation).
   - Third `//!` line is required (description content) —
     any text allowed (else: violation, EOF).

Bidirectional fixture test: 0/2 violations (one missing-block, one
incomplete structure).

Real-workspace findings (euv): 5 lib.rs files violate:
- `core/src/lib.rs` — text "euv" but name "euv-core"
- `example/src/lib.rs` — text "euv Example" but name "euv-example"
- `docs/src/lib.rs` — no `//!` block at all
- `cli/src/lib.rs` — text "euv CLI" but name "euv-cli"
- `macros/src/lib.rs` — text "euv_macros" but name "euv-macros"

The historical "audit-pitfalls §17 lib.rs `//!` doc comment IS
allowed" entry is marked DEPRECATED — see that section for the
full evolution narrative.
