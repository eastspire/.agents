# Audit script false-positive catalog

`scripts/audit_rust_standards.py` checks 13 categories of rust-standards
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

## 17. lib.rs `//!` doc comment IS allowed

The audit script category 5 (// comments in mod.rs) does NOT
flag lib.rs. Master explicitly allows a top-of-file `//!` crate
description on lib.rs. Same for raw_html.rs (the only non-lib.rs file
allowed to have `//!` as first lines — it's the proc-macro implementation
file in `macros/src/`).
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
