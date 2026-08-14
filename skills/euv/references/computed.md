---
synced_from: docs-pages/src/euv/macros/computed.md@f972247
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

## 基本用法

`computed!` 宏用于创建响应式计算信号，监听一个或多个输入信号并自动派生新的信号值。闭包的返回值即为计算信号的值，必须在 `->` 后显式标注返回类型。

```rust
use euv::*;

let first_name: Signal<String> = App::use_signal(|| String::from("John"));
let last_name: Signal<String> = App::use_signal(|| String::from("Doe"));

let full_name: Signal<String> = computed!(first_name, last_name, |first: String, last: String| -> String {
    format!("{} {}", first, last)
});
```

> [!tip]
>
> `computed!` 返回 `Signal<T>`，可以在 `html!` 宏中直接使用，与其他信号用法一致。

## 单个信号的计算

```rust
let price: Signal<f64> = App::use_signal(|| 100.0);

let total: Signal<String> = computed!(price, |price_value: f64| -> String {
    format!("{:.2}", price_value * 1.08)
});
```

> [!tip]
>
> 计算闭包内可以访问外部作用域的信号（如 `tax_rate`），但只有列在 `computed!` 参数中的信号变化时才会触发重新计算。

## 闭包参数

信号表达式的数量必须与闭包参数的数量一致。每个闭包参数接收对应信号的当前值（通过 `.get()` 获取）。参数类型标注是可选的，但建议显式标注以提高可读性：

```rust
// 带类型标注
computed!(red, green, blue, |r: i32, g: i32, b: i32| -> String {
    format!("#{:02x}{:02x}{:02x}", r.clamp(0, 255), g.clamp(0, 255), b.clamp(0, 255))
});

// 不带类型标注（类型自动推导）
computed!(red, green, blue, |r, g, b| -> String {
    format!("#{:02x}{:02x}{:02x}", r.clamp(0, 255), g.clamp(0, 255), b.clamp(0, 255))
});
```

### 匿名参数

不需要使用的信号参数可以用 `_` 忽略，支持带类型标注的忽略：

```rust
computed!(counter, timer, |count: i32, _: f64| -> String {
    format!("Count: {}", count)  // timer 值不参与计算
});

computed!(counter, timer, |count: i32, _| -> String {
    format!("Count: {}", count)
});
```

> [!warning]
>
> 返回类型必须在 `->` 后显式标注，不可省略。

## 与 watch! 的区别

|              | `watch!`                                            | `computed!`                                                     |
| ------------ | --------------------------------------------------- | --------------------------------------------------------------- |
| 返回值       | 无（执行副作用）                                    | `Signal<T>`（派生信号）                                         |
| 用途         | 日志、网络请求、手动同步等副作用                    | 从输入信号派生新的响应式值                                      |
| 闭包返回值   | 无                                                  | 必须返回计算值（类型与 `->` 标注一致）                          |
| DOM 更新调度 | 初始执行在 `batch` 内，`.set()` 不触发即时 DOM 调度 | 更新在 `batch` 内通过 `set()` 更新结果信号，不触发即时 DOM 调度 |

> [!tip]
>
> 需要执行副作用（如日志、网络请求、手动同步其他信号）时使用 `watch!`，需要派生新的响应式值时使用 `computed!`。

## 在 HTML 宏中使用

```rust
let width: Signal<i32> = App::use_signal(|| 100);
let height: Signal<i32> = App::use_signal(|| 200);

let area: Signal<String> = computed!(width, height, |w: i32, h: i32| -> String {
    (w * h).to_string()
});

html! {
    div {
        "Area: "
        area
    }
}
```

> [!tip]
>
> `computed!` 必须在动态节点 的渲染函数内部（即 `html!` 的 `{expr}` 花括号表达式内）使用，以确保其内部状态在重新渲染时持久化。`computed!` 内部通过 `App::use_signal` 创建结果信号并使用 `set` 更新值，更新操作在 `batch` 闭包内执行，确保不会触发过早的 DOM 调度。

<Bottom />
