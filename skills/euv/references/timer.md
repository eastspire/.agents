---
synced_from: docs-pages/src/euv/usage-introduction/timer.md@0c74235
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

## 概述

euv 通过 `App::use_interval` 创建间隔定时器，通过 `App::use_cleanup` 清理定时器。`use_interval` 返回 `IntervalHandle`，可提前取消。

## 基本用法

```rust
use euv::{web_sys::*, *};

let count: Signal<i32> = App::use_signal(|| 0);

// 每秒递增
let handle: IntervalHandle = App::use_interval(1000, move || {
    let current: i32 = count.get();
    count.set(current + 1);
});

html! {
    p { "Count: " count }
}
```

## 秒表（Stopwatch）

```rust
struct Stopwatch {
    seconds: Signal<i32>,
    running: Signal<bool>,
    handle: Signal<Option<IntervalHandle>>,
}

fn use_stopwatch() -> Stopwatch {
    Stopwatch {
        seconds: App::use_signal(|| 0),
        running: App::use_signal(|| false),
        handle: App::use_signal(|| None),
    }
}

fn start_stopwatch(sw: &Stopwatch) {
    if sw.running.get() { return; }
    sw.running.set(true);
    let seconds = sw.seconds;
    let running = sw.running;
    let handle = App::use_interval(1000, move || {
        let current = seconds.get();
        seconds.set(current + 1);
    });
    sw.handle.set(Some(handle));
}

fn pause_stopwatch(sw: &Stopwatch) {
    if let Some(h) = sw.handle.get() {
        h.clear();
    }
    sw.handle.set(None);
    sw.running.set(false);
}

fn reset_stopwatch(sw: &Stopwatch) {
    pause_stopwatch(sw);
    sw.seconds.set(0);
}
```

## 倒计时（Countdown）

```rust
struct Countdown {
    remaining: Signal<i32>,
    running: Signal<bool>,
    input: Signal<String>,
    handle: Signal<Option<IntervalHandle>>,
}

fn start_countdown(cd: &Countdown) {
    let remaining = cd.remaining.get();
    if cd.running.get() || remaining <= 0 { return; }
    cd.running.set(true);
    let remaining_signal = cd.remaining;
    let running_signal = cd.running;
    let handle = App::use_interval(1000, move || {
        let current = remaining_signal.get();
        if current <= 1 {
            remaining_signal.set(0);
            running_signal.set(false);
        } else {
            remaining_signal.set(current - 1);
        }
    });
    cd.handle.set(Some(handle));
}
```

## 格式化为 MM:SS

```rust
fn format_time(total_seconds: i32) -> String {
    let minutes = total_seconds / 60;
    let seconds = total_seconds % 60;
    format!("{:02}:{:02}", minutes, seconds)
}
```

## 在组件中使用

```rust
let stopwatch = use_stopwatch();

// 组件卸载时清理
App::use_cleanup({
    let sw = stopwatch;
    move || {
        if let Some(handle) = sw.handle.get() {
            handle.clear();
        }
    }
});

html! {
    div {
        h3 { "Stopwatch" }
        p { format_time(stopwatch.seconds.get()) }
        euv_button {
            variant: EuvButtonVariant::Primary
            label: if { stopwatch.running.get() } { "Pause" } else { "Start" }
            onclick: if { stopwatch.running.get() } {
                move |_: Event| { pause_stopwatch(&stopwatch); }
            } else {
                move |_: Event| { start_stopwatch(&stopwatch); }
            }
        }
        euv_button {
            variant: EuvButtonVariant::Primary
            label: "Reset"
            onclick: move |_: Event| { reset_stopwatch(&stopwatch); }
        }
    }
}
```

## IntervalHandle

`IntervalHandle` 是 `use_interval` 返回的句柄，用于管理定时器生命周期：

| 方法                      | 说明                             |
| ------------------------- | -------------------------------- |
| `IntervalHandle::new(id)` | 创建定时间隔句柄（框架内部使用） |
| `handle.clear()`          | 取消定时器，调用后回调不再触发   |

## 清理说明

`use_interval` 创建的定时器在 Hook 上下文清除时自动清理（组件卸载或 `match` 分支切换），无需手动调用 `handle.clear()`。但如果需要在定时器运行期间提前取消，可调用 `handle.clear()`。

```rust
let handle: IntervalHandle = App::use_interval(5000, move || {
    // 5 秒后执行
});

// 提前取消
handle.clear();
```

> [!tip]
>
> `use_interval` 仅在第一渲染创建定时器，后续渲染返回已有句柄。适用于所有需要周期性执行的场景（倒计时、轮询、动画帧等）。定时器创建时使用 `Closure::wrap` + `forget` 模式，生命周期由 `IntervalHandle` 管理。

<Bottom />
