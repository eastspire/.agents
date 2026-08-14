---
synced_from: docs-pages/src/euv/macros/watch.md@f972247
sync_method: scripts/sync-references.sh
sync_date: 2026-08-14
---

<!--
This file is auto-synced from the upstream docs-pages repo.
Manual edits will be overwritten on the next sync. To pin a custom version
of this reference, add "# manual override:" to its mapping line and the
script will leave it alone.
-->


<Share colorful />

## 单个信号监听

```rust
use euv::*;

let count: Signal<i32> = App::use_signal(|| 0);

watch!(count, |count_val: i32| {
    web_sys::console::log_1(&format!("Count: {}", count_val).into());
});
```

## 多个信号监听

```rust
let count: Signal<i32> = App::use_signal(|| 0);
let name: Signal<String> = App::use_signal(|| String::from("euv"));

watch!(count, name, |count_val: i32, name_val: String| {
    web_sys::console::log_1(&format!("count={}, name={}", count_val, name_val).into());
});
```

> [!tip]
>
> 闭包参数的类型标注是可选的，但建议显式标注以提高可读性。每个闭包参数接收对应信号的当前值（通过 `.get()` 获取）。

> [!tip]
>
> 闭包会在创建时立即执行一次（初始执行在 `batch` 内进行，闭包内的 `.set()` 调用不会触发即时 DOM 更新），之后在任意信号变化时再次执行（同样在 `batch` 内）。初始执行后不会重复订阅。

> [!warning]
>
> 信号表达式的数量必须与闭包参数的数量一致。

## 匿名参数

不需要使用的信号参数可以用 `_` 忽略，支持带类型标注的忽略：

```rust
let timer: Signal<f64> = App::use_signal(|| 0.0);
let count: Signal<i32> = App::use_signal(|| 0);

// timer 变化也会触发回调，但其值被忽略
watch!(timer, count, |_, count_val: i32| {
    web_sys::console::log_1(&format!("Count: {}", count_val).into());
});

// 带类型标注的匿名参数
watch!(timer, |_: f64| {
    web_sys::console::log_1(&"Timer triggered".into());
});
```

> [!tip]
>
> `watch!` 必须在动态节点 的渲染函数内部（即 `html!` 的 `{expr}` 花括号表达式内）使用，以确保其内部状态在重新渲染时持久化。`watch!` 内部确保订阅和初始执行只发生一次，不会在每次 动态节点 重新渲染时重复执行。

## 打破循环依赖

当两个信号互相监听时，在 `watch!` 闭包内使用 `batch` 包裹 `set` 调用，延迟 DOM 调度以避免在同一帧内触发级联更新：

```rust
let celsius: Signal<f64> = App::use_signal(|| 0.0);
let fahrenheit: Signal<f64> = App::use_signal(|| 32.0);

// 摄氏度变化 → 更新华氏度
watch!(celsius, |celsius_value: f64| {
    fahrenheit.set(celsius_value * 9.0 / 5.0 + 32.0);
});

// 华氏度变化 → 更新摄氏度
watch!(fahrenheit, |fahrenheit_value: f64| {
    celsius.set((fahrenheit_value - 32.0) * 5.0 / 9.0);
});
```

> [!tip]
>
> `watch!` 的订阅回调和初始执行均在 `batch` 内运行，闭包内的 `set` 调用会标记依赖的动态节点 为脏，但不会立即触发 DOM 更新，而是在 `batch` 结束后统一调度。当两个信号互相监听时，同一帧内的级联 `set` 调用会被合并为一次 DOM 更新，避免中间状态闪烁。

<Bottom />
