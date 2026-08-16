---
synced_from: docs-pages/src/euv/usage-introduction/reactive.md@0c74235
sync_method: scripts/sync-references.sh
sync_date: 2026-08-16
---

<!--
This file is auto-synced from the upstream docs-pages repo.
Manual edits will be overwritten on the next sync. To pin a custom version
of this reference, add "# manual override:" to its mapping line and the
script will leave it alone.
-->


<Share colorful />

## use_signal

创建响应式信号：

```rust
use euv::{web_sys::*, *};

let count: Signal<i32> = App::use_signal(|| 0);
let name: Signal<String> = App::use_signal(|| String::from("euv"));
let visible: Signal<bool> = App::use_signal(|| true);
```

> [!tip]
>
> 在动态节点 渲染函数内部调用 `use_signal` 时，信号状态会在重新渲染之间持久化。后续渲染返回相同的信号句柄，保留其当前值。

> [!warning]
>
> `use_signal` 的初始化闭包 `init` 只能是 `FnOnce() -> T`，不能捕获当前作用域中的可变借用或触发借用冲突的值。如果闭包中需要访问外部信号，请先克隆一份再移入闭包。

## Signal 方法汇总

`Signal<T>` 要求泛型参数 `T` 满足 `Clone + PartialEq + 'static`，提供以下方法：

| 方法                         | 返回值      | 说明                                                     |
| ---------------------------- | ----------- | -------------------------------------------------------- |
| `Signal::create(value)`      | `Signal<T>` | 直接创建信号（不依赖 HookContext，适用于全局信号初始化） |
| `Signal::default()`          | `Signal<T>` | 使用 `T::default()` 创建信号（要求 `T: Default`）        |
| `get(&self)`                 | `T`         | 获取当前值                                               |
| `set(&self, value)`          | `()`        | 设置值并通知监听器 + 调度 DOM 更新（值相同时不触发）     |
| `subscribe(&self, callback)` | `()`        | 追加监听器（`FnMut() + 'static`）                        |

## 读取值

```rust
let value: i32 = count.get();
```

> [!tip]
>
> `get` 内部实现了精确依赖追踪：如果在动态节点 渲染函数内部调用 `get`，该信号会自动注册当前动态节点为依赖。当信号变化时，只有依赖该信号的动态节点会被标记为脏并重新渲染，而非广播到所有动态节点。如果信号已被 `deactivate`，`get` 仍返回最后存储的值，但不会注册依赖。

## 写入值

```rust
count.set(42);
```

> [!tip]
>
> `set` 内部做相等性检查，新值与当前值相同时不会触发更新和通知，避免不必要的重新渲染。

> [!tip]
>
> 在 `App::batch` 闭包内调用 `set` 时，DOM 更新会被延迟到闭包结束后统一调度，不会在每次 `set` 时立即触发动态节点 重新渲染。`watch!` 宏的初始执行和 `computed!` 宏的信号更新均在 `App::batch` 内进行，确保闭包内的 `set` 调用不会触发过早的 DOM 更新。

## 订阅变化

### subscribe — 追加监听器

```rust
let count_for_sub: Signal<i32> = count;
count.subscribe(move || {
    let new_value: i32 = count_for_sub.get();
    web_sys::console::log_1(&format!("Count changed to: {}", new_value).into());
});
```

> [!tip]
>
> `subscribe` 追加一个监听器，信号值变化时会调用所有已注册的监听器。`replace_listener` 和 `deactivate` 是框架内部使用的方法，不对外暴露。`replace_listener` 用于信号属性绑定时替换监听器，避免在动态节点 重新渲染时产生监听器累积。`deactivate` 用于 `match` 分支切换时清理旧信号（清除所有监听器和依赖列表，将信号标记为不活跃），确保过时的异步闭包引用这些信号时变为无害操作。`deactivate` 不会释放堆内存，因为 `Signal<T>` 是 `Copy` 类型（仅存储指针地址），异步回调可能仍持有副本，释放会导致 use-after-free。

## use_cleanup

注册一个清理回调，当当前 Hook 上下文被清除时执行（如 `match` 分支切换时）。适用于清理副作用，如 `setInterval`、`setTimeout` 或订阅。

清理回调仅在首次渲染时注册一次，后续重新渲染时为空操作。

```rust
let handle: Signal<Option<IntervalHandle>> = App::use_signal(|| None);
App::use_cleanup(move || {
    if let Some(h) = handle.get() {
        h.clear();
    }
});
```

> [!tip]
>
> `use_cleanup` 必须在动态节点 的渲染函数内部使用。当 `match` 分支切换导致 Hook 上下文清理时，所有通过 `use_cleanup` 注册的回调会按注册顺序执行。对于 `keep-alive` 模式（CSS `display` 切换），组件不会被销毁，`use_cleanup` 不会被调用。

## use_window_event

注册 `window.addEventListener` 事件监听器，使用事件委托机制，在 Hook 上下文清除时自动移除。通过全局窗口事件代理注册表，同一事件名只会在 `window` 上绑定一次 `addEventListener`，清理时仅移除处理器条目，共享的 `window` 监听器保持活跃。

事件监听器仅在首次渲染时注册，后续重新渲染时为空操作。

```rust
let route_signal: Signal<String> = App::use_signal(current_route);

App::use_window_event("hashchange", move || {
    let new_route: String = current_route();
    route_signal.set(new_route);
});

App::use_window_event("resize", move || {
    // 处理窗口大小变化
});
```

> [!tip]
>
> `App::use_window_event` 适用于需要在组件级别监听全局 `window` 事件的场景，如 `hashchange`、`popstate`、`resize` 等。回调闭包签名为 `FnMut() + 'static`（不接收 `Event` 参数）。监听器会在 Hook 上下文清除时自动移除（如 `match` 分支切换或组件卸载时），无需手动清理。

## use_interval

创建一个定时执行的间隔回调，返回 `IntervalHandle`，在 Hook 上下文清除时自动清除定时器（即组件卸载或 `match` 分支切换时）。与手动调用 `setInterval` + `Closure::forget()` 不同，此 Hook 确保定时器被正确清理，防止内存泄漏和过时回调。

间隔定时器仅在首次渲染时创建，后续重新渲染时返回已有的句柄。

```rust
let count: Signal<i32> = App::use_signal(|| 0);
let count_ref: Signal<i32> = count;

let handle: IntervalHandle = App::use_interval(1000, move || {
    let current: i32 = count_ref.get();
    count_ref.set(current + 1);
});
```

### IntervalHandle

`IntervalHandle` 存储浏览器 `setInterval` 返回的定时器 ID，提供以下方法：

|                           | 方法                                           | 说明 |
| ------------------------- | ---------------------------------------------- | ---- |
| `IntervalHandle::new(id)` | 创建间隔句柄（框架内部使用）                   |
| `handle.clear(&self)`     | 取消关联的浏览器间隔定时器，调用后回调不再触发 |

手动提前取消定时器：

```rust
let handle: IntervalHandle = App::use_interval(1000, move || {
    // 每秒执行
});

// 提前取消
handle.clear();
```

> [!tip]
>
> `App::use_interval` 适用于需要周期性执行任务的场景（如倒计时、轮询数据、动画帧等）。通常不需要手动调用 `handle.clear()`，Hook 上下文清除时会自动清理。但如果需要在定时器运行期间提前取消，可以使用 `handle.clear()`。

## 在 HTML 宏中使用

```rust
fn counter() -> VirtualNode {
    let count: Signal<i32> = App::use_signal(|| 0);
    let count_updater: Signal<i32> = count;
    html! {
        div {
            p {
                "Count: "
                count
            }
            button {
                onclick: move |_event: Event| {
                    let current: i32 = count_updater.get();
                    count_updater.set(current + 1);
                }
                "Increment"
            }
        }
    }
}
```

## Signal::create

`Signal::create` 直接创建一个新的响应式信号，不依赖 `HookContext`。适用于在动态节点 渲染函数外部创建信号（如全局信号初始化）：

```rust
let count: Signal<i32> = Signal::create(0);
let name: Signal<String> = Signal::create(String::from("euv"));
```

> [!tip]
>
> 在动态节点 渲染函数内部请使用 `use_signal`，它会通过 `HookContext` 管理信号的生命周期，确保重新渲染时信号状态持久化。`Signal::create` 不会与 `HookContext` 关联，适用于一次性创建的场景。

## Signal::default

`Signal<T>` 实现了 `Default` trait（要求 `T: Clone + Default + PartialEq + 'static`），调用 `Signal::default()` 等价于 `Signal::create(T::default())`：

```rust
let count: Signal<i32> = Signal::default(); // 等价于 Signal::create(0)
let name: Signal<String> = Signal::default(); // 等价于 Signal::create(String::new())
```

> [!tip]
>
> `Signal::default()` 主要用于 Props 结构体的 `Default` 派生，确保 `Signal<T>` 类型的字段有合理的默认值（创建一个有效的信号，而非空指针）。不要手动构造 `inner = 0` 的无效信号，调用 `.get()` 会导致 panic。

## Signal 特性

`Signal<T>` 要求泛型参数 `T` 满足 `Clone + PartialEq + 'static`，实现了 `Copy` 和 `Clone`，所有副本共享相同的内部状态。这是因为 `Signal` 本质上是一个原始指针，复制只是比特位的拷贝。

```rust
let signal_a: Signal<i32> = App::use_signal(|| 0);
let signal_b: Signal<i32> = signal_a; // Copy，共享状态
signal_a.set(42);
assert_eq!(signal_b.get(), 42); // signal_b 也看到了变化
```

> [!tip]
>
> `Signal<T>` 不支持直接解引用，必须使用 `.get()` 和 `.set()` 方法读写值。

## SignalCell

`SignalCell<T>` 是一个 `Sync` 包装器，用于在 `static` 上下文中存储 `Signal`，实现全局信号访问：

```rust
use euv::{web_sys::*, *};

static GLOBAL_COUNT: SignalCell<i32> = SignalCell::none();

fn init_global_count() {
    let count: Signal<i32> = App::use_signal(|| 0);
    GLOBAL_COUNT.set(count);
}

fn get_global_count() -> Signal<i32> {
    GLOBAL_COUNT.get()
}
```

`SignalCell` 提供的方法：

| 方法                 | 说明                                                    |
| -------------------- | ------------------------------------------------------- |
| `SignalCell::none()` | 创建一个空的 `SignalCell`，适合在 `static` 上下文中使用 |
| `cell.set(signal)`   | 存储 `Signal` 到 cell 中，重复调用会 panic              |
| `cell.get()`         | 获取存储的 `Signal`，未初始化时调用会 panic             |

> [!warning]
>
> `SignalCell` 仅适用于单线程 WASM 环境。虽然它实现了 `Sync` 以允许作为 `static` 变量使用，但在多线程环境中并发访问会导致未定义行为。

> [!tip]
>
> `SignalCell` 适用于需要在多个函数间共享全局信号的场景，如全局状态管理。在组件内部使用 `use_signal` 即可，无需 `SignalCell`。

## HookContext

`HookContext` 管理动态节点的 Hook 状态，在渲染周期之间持久化 `use_signal` 等钩子状态。框架内部自动为每个 动态节点 创建和管理 `HookContext`。

### HookContext 方法

|                                         | 方法                                                                                                | 说明 |
| --------------------------------------- | --------------------------------------------------------------------------------------------------- | ---- |
| `HookContext::default() -> Self`        | 创建一个全新的 `HookContext`（空 Hook 列表 + 0 hook 索引）                                          |      |
| `reset_index(&mut self)`                | 重置 Hook 索引为零，每个渲染周期开始时调用，确保 `use_signal` 等钩子按调用顺序正确索引              |
| `switch_arm(&mut self, changed: usize)` | 通知 Hook 上下文当前 `match` 分支索引；索引变化时清除所有旧 Hook 状态和清理回调，然后重置 Hook 索引 |
| `Clone for HookContext`                 | 所有克隆共享同一内部状态（`Rc<RefCell<HookContextInner>>`）                                         |      |

> [!tip]
>
> 通常不需要手动使用 `HookContext`，`html!` 宏自动为动态节点 和条件渲染创建和管理 Hook 上下文。`switch_arm` 在 `match` 分支切换时自动调用，确保不同分支的 Hook 状态互不干扰。

## 动态节点

动态节点是由闭包驱动的渲染单元，信号变化时自动重新渲染。框架内部为每个动态节点管理一个 `HookContext`，用于跨渲染持久化 Hook 状态。

### 方法

| 方法                                                 | 返回值        | 说明                                                      |
| ---------------------------------------------------- | ------------- | --------------------------------------------------------- |
| `DynamicNode::default()`                             | `DynamicNode` | 创建默认动态节点（空渲染函数，返回 `VirtualNode::Empty`） |
| `node.render(&self, hook_context: &mut HookContext)` | `VirtualNode` | 调用渲染闭包，返回产生的虚拟 DOM 节点                     |

> [!tip]
>
> 通常不需要手动创建或调用动态节点，`html!` 宏会自动通过 `VirtualNode::create_dynamic` 创建动态节点。`render` 方法由框架内部的渲染器调用，不需要手动调用。

## 批量更新

`App::batch` 在闭包执行期间批量处理信号更新，闭包内的 `set` 调用不会触发动态节点 重新渲染，闭包结束后统一触发一次 DOM 更新：

```rust
App::batch(|| {
    count.set(1);
    name.set("updated".to_string());
});
// 闭包结束后，框架统一调度一次 DOM 更新
```

> [!tip]
>
> `batch` 适用于同一帧内需要更新多个信号的场景，将多次 DOM 更新合并为一次，避免中间状态的闪烁。

## computed! 派生信号

`computed!` 宏用于从输入信号派生新的响应式信号。当输入信号变化时，计算信号自动重新计算：

```rust
let first_name: Signal<String> = App::use_signal(|| String::from("John"));
let last_name: Signal<String> = App::use_signal(|| String::from("Doe"));

let full_name: Signal<String> = computed!(first_name, last_name, |first: String, last: String| -> String {
    format!("{} {}", first, last)
});
```

> [!tip]
>
> `computed!` 内部通过 `use_signal` 创建结果信号，使用 `set` 更新值。更新操作在 `batch` 闭包内执行，确保不会触发过早的 DOM 调度。详细用法参见 [computed! 宏](../macros/computed.md)。

## 更新调度机制

信号更新通过微任务批量调度，采用精确脏标记（precise dirty marking）：当信号变化时，只有依赖该信号的动态节点会被标记为脏并重新渲染，而非广播到所有动态节点。`set` 内部调用 `update` 更新值，然后通过 `App::schedule_update` 将依赖该信号的动态节点标记为脏，并调度一次微任务刷新。

调度优先级如下：

1. `queueMicrotask` — 首选，最轻量的延迟方式
2. `setTimeout(0)` — 当 `queueMicrotask` 不可用时回退
3. `requestAnimationFrame` — 当以上两种都不可用时回退

> [!tip]
>
> 使用微任务调度确保无论同一帧内发生多少次信号更新（如滑块快速拖动），仅执行一次 DOM 更新，避免 CPU 峰值。调度机制会自动选择当前环境可用的最优方案。`batch` 闭包内 `App::schedule_update` 仅标记脏而不调度微任务，闭包结束后由最外层的 `set` 统一调度。

## FireHandle

`FireHandle` 是 `watch!` 和 `computed!` 宏内部使用的句柄类型，用于跨异步边界安全地传递和触发闭包。`watch!` 和 `computed!` 在编译期为每个监听回调生成一个 `FireHandle`，该句柄持有泄漏的 `Box<dyn FnMut()>` 的堆地址，所有权从闭包中剥离以满足 `FnMut() + 'static` 订阅要求。

### 方法

| 方法                                                | 说明                                                 |
| --------------------------------------------------- | ---------------------------------------------------- |
| `FireHandle::new<F: FnMut() + 'static>(f) -> Self`  | 将闭包装箱泄漏，返回持有其堆地址的句柄               |
| `FireHandle::from<F: FnMut() + 'static>(f) -> Self` | `From` trait 实现，等价于 `new`                      |
| `unsafe fn fire(self)`                              | 调用底层闭包（`Copy` 句柄可多次调用，操作同一闭包）  |
| `unsafe fn fire_at(addr: usize)`                    | 通过地址调用闭包（用于宏生成的 `move` 闭包捕获地址） |

### From 实现

```rust
// FireHandle: From<FnMut() + 'static>
let handle: FireHandle = (move || { /* ... */ }).into();

// usize: From<FireHandle>
let addr: usize = handle.into();
```

> [!tip]
>
> `FireHandle` 是 `watch!` 和 `computed!` 宏的底层实现细节，普通用户通常无需直接使用。框架内部通过 `FireHandle::new` + `fire_at` 的组合让异步闭包能安全捕获非 `'static` 的局部变量。如果在自定义订阅回调中遇到类似需求（需要将闭包泄漏为稳定地址），可参考 `FireHandle` 的 API。

<Bottom />
