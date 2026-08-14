---
synced_from: docs-pages/src/euv/usage-introduction/animation.md@f972247
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

## CSS 过渡

通过响应式信号切换 CSS 属性值，结合 `transition` 实现平滑过渡效果：

```rust
let is_active: Signal<bool> = App::use_signal(|| false);

html! {
    div {
        style: {
            background: if { is_active.get() } { "#4f46e5".to_string() } else { "#e5e7eb".to_string() };
            transition: "background 0.5s ease";
        }
        onclick: move |_event: Event| {
            let current: bool = is_active.get();
            is_active.set(!current);
        }
        "Click to toggle"
    }
}
```

> [!tip]
>
> 在 `style:` 中使用 `transition` 属性，配合 `if` 条件切换样式值，即可实现 CSS 过渡动画。框架自动将 `if` 条件包装为响应式信号，信号变化时样式自动更新。

## CSS 关键帧动画

`class!` 宏中可定义关键帧动画类。`euv-ui` crate 提供的 `inject_app_global_css()` 函数已通过 `Css::inject_css()` 预注入以下 `@keyframes`：

| 动画名               | 说明         |
| -------------------- | ------------ |
| `euv-spin`           | 旋转动画     |
| `euv-fade-in`        | 淡入动画     |
| `euv-pulse`          | 脉冲动画     |
| `euv-progress`       | 进度条动画   |
| `euv-scale-in-modal` | 模态缩放动画 |

使用预注入的关键帧动画：

```rust
class! {
    pub c_anim_spin {
        animation: "euv-spin 1s linear infinite";
    }
    pub c_anim_fade_in {
        animation: "euv-fade-in 0.3s ease forwards";
    }
    pub c_anim_pulse {
        animation: "euv-pulse 1.5s ease-in-out infinite";
    }
}

html! {
    div {
        class: c_anim_spin()
        "Spinning"
    }
}
```

## 条件动画

结合 `if` 条件和 CSS 类实现动画的启动和停止：

```rust
let spin_active: Signal<bool> = App::use_signal(|| false);

html! {
    primary_button {
        label: "Toggle"
        onclick: move |_event: Event| {
            let current: bool = spin_active.get();
            spin_active.set(!current);
        }
        if { spin_active.get() } { "Stop Spin" } else { "Start Spin" }
    }
    div {
        class: if { spin_active.get() } { c_anim_spin() } else { c_anim_spin_stopped() }
        "⟳"
    }
}
```

```rust
class! {
    pub c_anim_spin {
        animation: "euv-spin 1s linear infinite";
    }
    pub c_anim_spin_stopped {
        animation: "none";
    }
}
```

> [!tip]
>
> 使用 `if` 条件切换不同的 CSS 类，实现动画的启动/停止切换。

## 自定义关键帧动画

在 `class!` 中使用自定义 `animation` 属性，并通过 `Css::inject_css()` 注入对应的 `@keyframes`：

```rust
// 注入自定义关键帧
Css::inject_css("@keyframes my-bounce { 0%, 100% { transform: translateY(0); } 50% { transform: translateY(-20px); } }");

class! {
    pub c_bounce {
        animation: "my-bounce 0.6s ease infinite";
    }
}

html! {
    div {
        class: c_bounce()
        "Bouncing"
    }
}
```

## 进度条动画

结合定时器和响应式信号实现动态进度条：

```rust
let progress: Signal<i32> = App::use_signal(|| 0);

html! {
    div {
        class: c_progress_container()
        div {
            class: c_progress_bar_running()
            style: {
                width: format!("{}%", progress.get());
                transition: "width 0.1s ease";
                background: if { progress.get() >= 100 } { "#059669".to_string() } else { "#4f46e5".to_string() };
            }
        }
    }
    p {
        progress
        "%"
    }
}
```

> [!tip]
>
> 进度条通过 `width` 百分比 + `transition` 实现平滑动画，`background` 配合 `if` 条件在完成时变色。

<Bottom />
