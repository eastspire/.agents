# `use_async` 实战坑表 (euv-dev/euv#17)

PR#17 实现 `App::use_async` 时撞到的具体 Rust / euv 类型系统坑。给后续做 `use_resource` / `useTransition` / Suspense 的 session 直接用。

## 1. `Signal<T>` 的 bound chain 必须显式写出

```rust
pub struct Signal<T> where T: Clone + PartialEq + 'static { ... }
```

**任何把 `T` 包进 `Signal<T>` 的新结构,bound 必须显式写到所有相关位置** —— 不能依赖 derive 自动推断。例:`UseAsyncSlot<T, L>` 用 `Signal<AsyncState<T, L>>`,所以:

```rust
pub(crate) struct UseAsyncSlot<T, L>
where
    T: Clone + PartialEq + 'static,           // ← 必填
    L: Clone + PartialEq + HasLoadingHint + 'static,  // ← 必填
{ ... }
```

**漏了 `Clone + PartialEq` 编译报**:`the trait bound 'T: Clone' is not satisfied` / `can't compare 'T' with 'T'`。`#[derive(...)]` 不会自动加 bound,`derive(Clone, Copy)` 只在 T: Copy / L: Copy 时 `UseAsyncHandle` 才是 Copy。

## 2. `derive(Clone, Copy)` 不会让 struct 在所有 T/L 下 Copy

```rust
#[derive(Clone, Copy)]
pub struct UseAsyncHandle<T, L = ()>
where
    T: Clone + PartialEq + 'static,
    L: Clone + PartialEq + HasLoadingHint + 'static,
{ ... }
```

**Copy 只在 T: Copy 且 L: Copy 时自动满足**。但 `Clone + Copy` derive 不强制 `T: Copy + L: Copy`(只能靠手写 where bound 强加,但那就拒绝所有非 Copy 用户类型)。

**正确做法**:不用 Copy,改用显式 clone:

```rust
let handle_for_cleanup: UseAsyncHandle<T, L> = handle.clone();
let handle_for_hook: UseAsyncHandle<T, L> = handle.clone();
inner.get_mut_cleanups().push(Box::new(move || unsafe {
    handle_for_cleanup.release();
}));
```

`return existing.clone()` 比 `return *existing` 安全(existing 是 `&UseAsyncHandle<T,L>`,*existing move 不允许)。

## 3. refetch method 的 E 泛型必须挂在 method where,不能挂在 impl where

试过:

```rust
impl<T, L, E> UseAsyncHandle<T, L>
where
    T: Clone + PartialEq + 'static,
    L: Clone + PartialEq + HasLoadingHint + 'static,
    E: Into<String> + 'static,
{ ... }
```

编译器报 E0207 `the type parameter E is not constrained by the impl trait, self type, or predicates`。**因为 `UseAsyncHandle<T, L>` 本身没有 E,E 只在 method 内被用到**。Rust 要求 impl 块的泛型至少出现在 self type / impl trait / impl where 的其中一个(不能只出现在 method where)。

**正确做法**:把 `E` 从 impl 头移到 method where:

```rust
impl<T, L> UseAsyncHandle<T, L>
where
    T: Clone + PartialEq + 'static,
    L: Clone + PartialEq + HasLoadingHint + 'static,
{
    pub fn refetch<F, Fut, E>(&self, factory: F)
    where
        F: FnOnce() -> Fut + 'static,
        Fut: Future<Output = Result<T, E>> + 'static,
        E: Into<String> + 'static,
    { ... }
}
```

## 4. `wasm_bindgen_futures::spawn_local` 在 native target panic

```rust
wasm_bindgen_futures::spawn_local(task);
// native cargo test 上 panic: function not implemented on non-wasm32 targets
```

`spawn_local` 来自 `js_sys::futures`,js-sys 在 native target 上 crate 本身能编译,但 `spawn_local` 调用会 panic。要 `cfg(target_arch = "wasm32")` 隔开:

```rust
#[cfg(target_arch = "wasm32")]
{
    wasm_bindgen_futures::spawn_local(task);
}
#[cfg(not(target_arch = "wasm32"))]
{
    drop(task);  // 静默 no-op,测试用 set_state 驱动状态机
}
```

测试靠 `UseAsyncHandle::set_state(next: AsyncState<T, L>)` (cfg `#[cfg(test)]`) 直接驱动状态机,不依赖 spawn_local 实际跑 future。

## 5. `Pin<Box<dyn Future + 'static>>` 在闭包里的 Box::pin

```rust
let task: core::pin::Pin<Box<dyn Future<Output = ()>>> = Box::pin(async move {
    let outcome: Result<T, E> = task_fut.await;
    // ...
});
```

`Box<dyn Future<Output = ()>>` 不能直接 `Box::pin` —— `dyn Future` 不是 Sized,Pin 需要 heap 上 pinned future,用 `Box::pin` 创建 pinned box。

## 6. Cancellation 用 `Rc<Cell<bool>>`,已知有 refetch race

```rust
pub(crate) cancel: Rc<Cell<bool>>,
```

**已知 race**:`refetch()` 把 cancel 设回 false,但 in-flight 旧 future 跟新 future 共享同一个 `Rc<Cell<bool>>`。旧 future 的 late resolution 可能看到 false → 写入 state,覆盖新 future 的结果。

**plan 修法**(PR#17 未做,留给 follow-up):
```rust
pub(crate) generation: Rc<Cell<u64>>,  // 每次 refetch ++
// future 内:
if my_generation != slot.generation.get() { return; }
slot.state.set(next);
```

`u64` counter 永不溢出(wrap around 也要 2^64 次 refetch),无需 mutex。代价:slot 多 8 bytes。

## 7. `Future` trait 必须显式 `use std::future::Future`

```rust
use std::future::Future;
```

euv-core 不像 `std::prelude` 那样自动 re-export `Future`。hook/impl.rs 和 app/impl.rs 都需要单独 `use std::future::Future;`,否则 `Future<Output = ...>` 报 "cannot find trait `Future` in this scope"。

## 8. `HookContext.hooks` slot reuse:downcast + clone

```rust
if index < inner.get_hooks().len()
    && let Some(existing) = inner.get_hooks()[index]
        .downcast_ref::<UseAsyncHandle<T, L>>()
{
    return existing.clone();
}
```

`downcast_ref` 返回 `Option<&UseAsyncHandle<T,L>>`。**不能 `*existing` move**(`&T` 解引用拿不到 owned)。**不能 `existing.copy()`**(UseAsyncHandle 不总是 Copy)。统一 `existing.clone()`。

## 9. macro emit `use_async` 调用的类型推导

外部用户写:
```rust
let handle = App::use_async::<String, (), _, _, String>(|| async {
    Ok::<String, String>(String::from("payload"))
});
```

**5 个泛型参数都得显式标**:`<T, L, F, Fut, E>`。让 F / Fut 自动推断必须用户加 turbofish,否则 E 的 trait bound `Into<String>` 无法确定 turbofish。**不要**把 E 绑到工厂类型上(让 factory closure 类型推断),helper 用户也能不写 turbofish 的版本(用 `fn() -> impl Future<Result<T, String>>`)做不到 —— 因为 helper 仍然要写 `<T, L, _, _, String>` 才能落地。

## 10. `pub use` 链要传到 hook/impl.rs

`reactive::use_async` 是新模块,要让 hook/impl.rs 看得到:

```rust
// reactive/mod.rs
pub use {hook::*, signal::*, use_async::*};

// hook/mod.rs
pub use crate::reactive::use_async::*;
```

两处都要 pub use,否则 hook::impl.rs 写 `super::*` 看不到 `UseAsyncHandle`,写 `crate::reactive::use_async::UseAsyncHandle` 又绕。

## 11. `unsafe_op_in_unsafe_fn` warning on Rust 2024 edition

euv-core 用 edition = "2024"。Rust 2024 默认 `unsafe_op_in_unsafe_fn` warn —— 即 `unsafe fn foo() { *ptr; }` 报 "unsafe op in unsafe fn needs explicit unsafe block"。要么在 fn 头加 `unsafe fn` (已加),要么在 fn 内重新包 `unsafe { ... }`:

```rust
pub(crate) unsafe fn slot(&self) -> &UseAsyncSlot<T, L> {
    unsafe { &*(self.inner as *const UseAsyncSlot<T, L>) }  // ← 这里的 unsafe
}
```

## 12. 验证 checklist (已用 PR#17 走通)

- [x] `cargo check --workspace` exit 0
- [x] `cargo check --target wasm32-unknown-unknown -p euv-core` exit 0
- [x] `cargo test -p euv-core --lib` ≥ 12 passed
- [x] 端到端 throwaway crate:`App::use_async::<String, (), _, _, String>(|| async { Ok(...) })` + `match AsyncState::Loading(()) { ... }` 必须编译过
- [x] `euv fmt --check` exit 0
- [x] `cargo fmt --all --check` exit 0
- [x] workspace dependency: `wasm-bindgen-futures = { workspace = true }` 加进 core/Cargo.toml
