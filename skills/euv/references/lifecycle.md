---
synced_from: docs-pages/src/euv/usage-introduction/lifecycle.md@f972247
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

## 概述

euv 的函数组件本质上是渲染函数，每次信号变化时重新调用。通过信号和 Hook 的组合可以追踪组件的渲染次数和状态变化。

## 渲染计数追踪

使用 `use_signal` 创建计数器信号，在渲染函数中自增即可追踪渲染次数：

```rust
use euv::{web_sys::*, *};

#[component]
fn page_lifecycle(_node: VirtualNode<()>) -> VirtualNode {
    let render_count: Signal<i32> = App::use_signal(|| 0);
    let prev = render_count.get();
    render_count.set(prev + 1);

    html! {
        div {
            p {
                "This page has been rendered "
                render_count
                " times."
            }
        }
    }
}
```

## 与 watch! 配合监控

使用 `watch!` 宏在信号变化时执行日志或其他副作用：

```rust
let render_count: Signal<i32> = App::use_signal(|| 0);

watch!(render_count, |count: i32| {
    web_sys::console::log_1(&format!("Render count: {}", count).into());
});
```

## 组件挂载和卸载

euv 没有显式的 `on_mount` / `on_unmount` 生命周期钩子，但可通过以下等效模式实现：

### use_signal 初始化

`use_signal` 的初始化闭包仅在首次渲染时执行，可作为"挂载时执行一次"的等效：

```rust
let initialized: Signal<bool> = App::use_signal(|| {
    // 该闭包仅在组件首次挂载时执行
    web_sys::console::log_1(&"Component mounted".into());
    true
});
```

### use_cleanup 清理

`use_cleanup` 注册的回调在 Hook 上下文清除时执行，可作为"卸载时执行一次"的等效：

```rust
App::use_cleanup(move || {
    web_sys::console::log_1(&"Component unmounted".into());
});
```

### 结合使用

```rust
#[component]
fn lifecycle_demo(_node: VirtualNode<()>) -> VirtualNode {
    let _mounted: Signal<bool> = App::use_signal(|| {
        web_sys::console::log_1(&"Mounted".into());
        true
    });

    App::use_cleanup(move || {
        web_sys::console::log_1(&"Cleanup".into());
    });

    html! {
        div { "Lifecycle Demo" }
    }
}
```

## use_interval 定时任务

结合 `use_interval` 实现定时检查和更新：

```rust
let counter: Signal<i32> = App::use_signal(|| 0);

App::use_interval(1000, move || {
    let current = counter.get();
    counter.set(current + 1);
});
```

> [!tip]
>
> euv 没有类 React 的 `useEffect` / `useLayoutEffect` 钩子。通过 `use_signal` 一次初始化、`use_cleanup` 清理和 `watch!` / `computed!` 响应式组合，可以实现所有生命周期需求。`use_window_event` 也可实现类似 `addEventListener` / `removeEventListener` 的效果。

<Bottom />
