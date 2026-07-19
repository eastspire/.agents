---
name: lombok-macros
description: "A Rust procedural macro collection providing Lombok-like functionality. Automatically generates getters/setters with field-level visibility control, custom Debug implementations with field skipping, and Display trait implementations. Supports structs, enums, generics and lifetimes. Load when chasing E0599 'no method named get_X' on a field you clearly declared, or when a Signal<T>/Form/JSON-body wrapper complains about field accessors that are named differently than the field, or when an Option<T> field behaves like the unwrapped T (returns String, not Option<String>) — these are the lombok-macros 2.0.x Data derive generator's actual signatures, not the obvious ones."
---

# lombok-macros — `Data` derive, generated accessor signatures, and the unwrap-on-Option gotchas

Reference: <https://crates.io/crates/lombok-macros> (lombok-macros 2.0.31 as used by hyperlane-quick-start 2026-07).

## 1. The `Data` derive generates two accessors per field, with non-obvious types

For `#[derive(lombok_macros::Data)]`, the macro emits for every field `field_name: T`:

| Field type | `get_field_name(&self) -> ...` | `try_get_field_name(&self) -> ...` |
|---|---|---|
| `String` | `String` (cloned) | `Option<&String>` |
| `Option<String>` | **`String`** (macro unwraps the inner `Some(...)`) | `Option<&String>` |
| `i64` / `i32` / `u64` / `usize` | **`&i64`** (reference!) | `Option<&i64>` |
| `f64` / `f32` | `&f64` | `Option<&f64>` |
| `bool` | `&bool` | `Option<&bool>` |
| `Vec<T>` | `Vec<T>` (cloned) | `Option<&Vec<T>>` |

Two things that **always surprise people** the first time:

1. `i64` / `i32` etc. are returned by **reference**, not by value. Even though `i64: Copy`, the macro emits `&self.field` and the return type is `&i64`. Code like `let x: i64 = request.get_id();` fails with `expected i64, found &i64` — you must write `let x: i64 = *request.get_id();` to deref.

2. `Option<String>`'s `get` returns **`String`**, not `Option<String>`. The macro unwraps the `Some(...)` and clones the inner value. If you `match request.get_name() { Some(n) => ... }` you get `mismatched types: expected String, found Option<_>`. Use `match request.try_get_name() { Some(s) => s.to_string(), None => default }`, OR pre-check with `if let Some(n) = request.try_get_name()`.

**Why the macro does this**: lombok-macros 2.0.x treats `get_*` as 'give me the value, I'll unwrap for you' and `try_get_*` as 'give me the actual Option' — two distinct APIs with different return types. The names map onto Java's `Optional.get()` (throws) vs `Optional.tryGet()` (returns Option) but the Rust signatures are inverted (get clones, try_get returns a borrow).

## 2. The `Data` derive + `Signal<T>` (euv / hyperlane reactive state)

`Signal<T>` requires `T: Clone + PartialEq + 'static` (see `euv/core/src/reactive/signal/struct.rs`). When you store a `Data`-derived struct in a `Signal`:

- The struct's `Clone` is auto-derived by `Data` (it generates `#[derive(Clone)]` for you).
- You must also `#[derive(PartialEq)]` on the struct — `Data` does NOT add `PartialEq`, and `Signal::set` needs it for the dirty-check.
- `Data` generates `set_field_name(&mut self, val: T) -> &mut Self` and a non-returning variant. The `&mut Self` form lets you chain `.set_a(x).set_b(y)`.

If you forget `PartialEq` and wrap in `Signal`, the error is `E0599: the method 'set' exists for struct 'Signal<MyState>', but its trait bounds were not satisfied` — note it points at `set` on `Signal`, not at your struct, which is easy to misread as 'Signal is broken'. The actual fix is `#[derive(PartialEq)]` on `MyState`.

## 3. `Signal::new(value)` is the wrong API — use `Signal::create(value)` or `App::use_signal(|| value)`

`Signal<T>` is a `lombok_macros::New`-derived struct, and `New` generates `new(value: T, _: PhantomData<T>)` — **two arguments**, the second is a phantom-data zero-sized marker. Calling `Signal::new(false)` fails with `E0061: this function takes 2 arguments but 1 argument was supplied`.

Two correct single-arg paths:

```rust
// Inside a #[component] body — registers in the current hook context
let s: Signal<bool> = App::use_signal(|| false);

// Anywhere — standalone signal, no hook context
let s: Signal<bool> = Signal::create(false);
```

`App::use_signal` MUST be called from inside a `#[component]` function body (the hook context comes from the macro's wrapping closure). Outside components, use `Signal::create`. The signal's `set` / `get` methods are not affected by which constructor you used.

## 4. `Signal<bool>::set(...)` only triggers re-render if the new value differs

`Signal::set` internally compares the new value to the current via `T: PartialEq`. If you `set(true)` when the signal is already `true`, **no re-render fires**. This is the 'did my signal actually fire?' trap when you're chaining sets in a click handler — back-to-back identical sets look like nothing happened.

Workaround for 'force re-render on every set':
- Bump a paired generation counter: `let gen: Signal<u32> = ...; s.set(s.get() + 1)` — same pattern as React's `useState` + `useReducer` pairing.
- Or use `euv_core::reactive::signal::force_set` if exposed (verify in your euv version).

## 5. `#[derive(Data, New)]` auto-generates `new(a, b, c)` constructor with positional args

`New` generates `new(field1, field2, ...)` with positional args for every field NOT marked `#[new(skip)]`. `#[new(skip)]` fields are excluded from `new()` and fall back to `Default::default()` (which means the type must impl `Default`).

If you write `impl Default for X`, you cannot also `#[derive(New)]` (New also generates `default()`). Pick one.

For a struct with 4 fields all needing init, you must write `X::new(a, b, c, d)` — all four args, no shortcuts. If this looks ugly, write a typed factory method (e.g. `X::from_config(cfg)`) instead of forcing callers to spell out the entire arg chain.

## 6. `#[derive(Data)]` cannot be applied to enums

```rust
#[derive(Clone, Copy, Data, Debug, Default, ...)]
pub enum Status { Idle, Requesting, Ready, Failed }   // ❌ proc-macro panic
```

```
error: proc-macro derive panicked
  = help: message: #[derive(Data)] is only supported for structs.
```

`lombok_macros::Data` is struct-only. For enums, use plain `#[derive(Clone, Copy, Debug, Default, PartialEq, Eq, ...)]` and read its values via `match` / `if let` — no accessor methods. Store the enum in a `Signal<T>` only if it implements `Clone + Copy + PartialEq + 'static` (which the plain derives give you).

## 7. `Data` is required to make a struct work as `Signal<T>` content

The `Signal<T>::set` method takes `T` and the dirty-check requires `T: PartialEq`. But `Signal<T>` also calls into `get_xxx` / `set_xxx` methods on the stored struct to read/write fields — those methods are generated by `Data`. Without `Data`, even `Signal<MyState>::set(my_state)` (passing the whole struct) compiles, but **structurally reading/mutating fields on a `Signal<MyState>`** won't compile.

Practical impact: any state struct that lives in a `Signal<T>` must `#[derive(Data)]`. If you also need `PartialEq` for the dirty check, add it explicitly (Data does not derive PartialEq).

## 8. Working with `try_get_*` in match arms — the 'I want the inner value' pattern

The common pattern when you have `Option<String>` field and want to switch on `Some` / `None` to decide a default:

```rust
// WRONG — `get` unwraps and you lose the None branch
let final_name: String = match request.get_name() {
    Some(n) => n.trim().to_string(),
    None => "Untitled".to_string(),     // <- ERROR: expected String, found Option<String>
};

// RIGHT — use `try_get` for the Option<&String> shape
let final_name: String = match request.try_get_name() {
    Some(s) => {
        let trimmed = s.trim();
        if trimmed.is_empty() { "Untitled".to_string() } else { trimmed.to_string() }
    }
    None => "Untitled".to_string(),
};

// ALSO RIGHT — for fields where empty string is a sentinel for 'keep prior',
// use a match guard:
let code: Option<String> = match request.try_get_code() {
    Some(c) if !c.is_empty() => Some(c.to_string()),
    _ => None,
};
```

`try_get_*` is the right primitive for 'treat empty / missing as None'.

## 9. The `lombok-macros::New` two-argument trap recurs in other macro-generated constructors

Same shape appears in:
- `JwtConfig::new(secret, expiration, issuer)` (3-arg)
- `JwtService::from(config)` (1-arg, OK)
- `JsonResponse::new(code, message, data)` (3-arg)

The pattern: any struct that derives `lombok_macros::New` gets a positional `new(...)` with one arg per non-skipped field. Look at the field list to count the args, don't trust the docstring's 'convenient constructor' framing. (`JwtConfig::new` is 3-arg, not 1-arg as the field count might suggest if you only count 'the secret'.)

## 10. The 60-second mental model: 'Data = Java-style getter generator, with one gotcha'

`Data` emits `get_*` / `try_get_*` for every field:

- `get_*` returns the field value directly (unwrapping `Option` if present, cloning owned values, returning a reference for `Copy` types).
- `try_get_*` returns the field as an `Option` (with a borrow) so you can pattern-match.

The two accessors exist because hyperlane's request structs use both: a field with default-when-missing semantics calls `get_*` directly (the macro fills in the default), while a field that may genuinely be absent calls `try_get_*` and branches. The Data-derive is the 'default-fill' layer; try_get is the 'explicit absence' layer.

If you find yourself wanting a third accessor shape — 'get but also tell me if it was the default' — that's not in the macro. Hand-roll a method on the struct that uses `try_get_*` and `String::is_empty()` (or similar) to derive the flag.

## See also

- `euv-html-macro-traps` §12 'Online-IDE / code-playground architecture' — where this `Data`-derive behavior bites when you have an euv playground that accepts POSTed Rust source. The Request struct fields like `code: String` follow the same `get_xxx() -> String` rule described here.
- `rust-standards` for general Rust idioms
- `hyperlane-quick-start` for the project context that exercises these patterns

## Docs (preserved)

- GitHub: <https://github.com/crates-dev/lombok-macros.git>
- crates.io: <https://crates.io/crates/lombok-macros>
- docs.rs: <https://docs.rs/lombok-macros/latest/>

[Api Docs](https://docs.rs/lombok-macros/latest/)

> A Rust procedural macro collection providing Lombok-like functionality. Automatically generates getters/setters with field-level visibility control, custom Debug implementations with field skipping, and Display trait implementations. Supports structs, enums, generics and lifetimes.

## Installation

To use this crate, you can run cmd:

```shell
cargo add lombok-macros
```
