---
synced_from: docs-pages/src/euv/usage-introduction/keep-alive.md@f972247
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

## 问题

在 euv 中，使用 `match` 或 `if/else` 切换组件时，旧分支的组件会被销毁，新分支的组件会重新创建。这意味着切换回来时，所有 Hook 状态（信号值、表单输入、定时器等）都会重置。

## 解决方案：CSS display 切换

同时渲染所有 Tab 内容，通过 CSS `display: none/block` 控制可见性，而非条件渲染。这样所有动态节点 及其 `HookContext` 保持存活——信号保留值、`setInterval` 继续运行、表单输入得到保留。

```rust
let tab: Signal<String> = App::use_signal(|| "counter".to_string());

html! {
    div {
        // Tab 栏
        div {
            class: c_tab_bar()
            div {
                class: if { tab.get() == "counter" } { c_tab_item_active() } else { c_tab_item_inactive() }
                onclick: move |_event: Event| { tab.set("counter".to_string()); }
                "Counter"
            }
            div {
                class: if { tab.get() == "form" } { c_tab_item_active() } else { c_tab_item_inactive() }
                onclick: move |_event: Event| { tab.set("form".to_string()); }
                "Form"
            }
        }
        // 同时渲染所有 Tab，用 display 控制可见性
        div {
            style: { display: if { tab.get() == "counter" } { "block".to_string() } else { "none".to_string() }; }
            { counter_tab() }
        }
        div {
            style: { display: if { tab.get() == "form" } { "block".to_string() } else { "none".to_string() }; }
            { form_tab() }
        }
    }
}
```

## 配合 App::use_cleanup 和 watch! 管理定时器

Keep-Alive 模式下组件不会被销毁，`App::use_cleanup` 不会在 Tab 切换时被调用。但可以在组件首次渲染时使用 `App::use_cleanup` 注册清理回调，确保组件最终被销毁时（如路由离开）定时器被正确清理：

```rust
fn timer_tab() -> VirtualNode {
    let elapsed: Signal<i32> = App::use_signal(|| 0);
    let running: Signal<bool> = App::use_signal(|| false);
    let handle: Signal<Option<IntervalHandle>> = App::use_signal(|| None);

    // 组件最终销毁时清理定时器
    App::use_cleanup(move || {
        if let Some(h) = handle.get() {
            h.clear();
        }
    });

    // use_interval 不能在 watch! 闭包内调用（必须在动态节点渲染函数顶层注册）。
    // 正确做法：在组件初始化时无条件创建 interval，再用 watch! 监听 running 信号
    // 控制 start/pause 或直接使用 running 信号作为条件。
    // 参见 timer.md 的"秒表（Stopwatch）"节获取可编译的完整示例。
    html! {
        div {
            span { { format_time(elapsed.get()) } }
            if { !running.get() } {
                button {
                    onclick: move |_event: Event| { running.set(true); }
                    "Start"
                }
            } else {
                button {
                    onclick: move |_event: Event| { running.set(false); }
                    "Pause"
                }
            }
        }
    }
}

fn format_time(total_seconds: i32) -> String {
    let minutes: i32 = total_seconds / 60;
    let seconds: i32 = total_seconds % 60;
    format!("{:02}:{:02}", minutes, seconds)
}
```

> [!tip]
>
> Keep-Alive 模式下，`App::use_cleanup` 只在组件最终被销毁时调用（如整个页面被替换），而非 Tab 切换时调用。定时器在 Tab 切换后仍然在后台运行，这正是 Keep-Alive 的预期行为。

## 适用场景

| 场景            | 说明                                            |
| --------------- | ----------------------------------------------- |
| 多 Tab 切换     | Tab 内容需要保持滚动位置、输入值、展开/折叠状态 |
| 定时器保持      | 后台 Tab 中的 `setInterval` 继续运行            |
| 表单状态保留    | 用户在多个 Tab 中填写表单，切换后不丢失输入     |
| 计数器/进度保持 | 进度条、计时器等需持续更新的状态                |

> [!warning]
>
> 所有 Tab 内容会同时存在于 DOM 中，对于包含大量节点的 Tab 需注意性能影响。

<Bottom />
