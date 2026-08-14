---
synced_from: docs-pages/src/euv/usage-introduction/binding.md@f972247
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

## Props Down / Callback Up

父组件通过 Props 传递数据给子组件，子组件通过回调函数通知父组件：

```rust
use euv::{web_sys::*, *};
use euv_ui::*;

// 子组件 Props 定义
#[derive(Clone, Default)]
struct ChildDisplayProps {
    message: &'static str,
    onclick: Option<Rc<dyn Fn(Event)>>,
}

// 子组件
#[component]
pub fn child_display(node: VirtualNode<ChildDisplayProps>) -> VirtualNode {
    let ChildDisplayProps { message, onclick, .. } = node.try_get_props().unwrap_or_default();
    html! {
        div {
            p { "Child received: " message }
            button {
                onclick: onclick
                "Respond to Parent"
            }
        }
    }
}

// 父组件（on_input_value 来自 euv_ui::UseEuvInput）
html! {
    div {
        input {
            r#type: "text"
            value: parent_message.get()
            oninput: UseEuvInput::on_input_value(parent_message)
        }
        child_display {
            message: parent_message.get()
            onclick: move |_event: Event| {
                child_response.set(format!("Child received: {}", parent_message.get()));
            }
        }
    }
}
```

> [!tip]
>
> 回调属性类型为 `Option<Rc<dyn Fn(Event)>>`，在 `html!` 中使用 `onclick` 等 `on` 前缀格式传递。

## 强类型 Props

通过类型化 Props 结构体传递非 `String` 类型（如 `bool`、`i32`）的属性：

```rust
#[derive(Clone, Default)]
struct LimitedCounterProps {
    disabled: Signal<bool>,
    max_count: i32,
    on_increment: Option<Rc<dyn Fn(Event)>>,
    on_reset: Option<Rc<dyn Fn(Event)>>,
}

// 子组件提取强类型 props
#[component]
pub fn limited_counter(node: VirtualNode<LimitedCounterProps>) -> VirtualNode {
    let LimitedCounterProps { disabled, max_count, on_increment, on_reset, .. } = node.try_get_props().unwrap_or_default();
    html! {
        div {
            p { "Disabled: " {disabled.to_string()} ", Max: " {max_count.to_string()} }
            button {
                onclick: on_increment
                disabled: disabled
                "+1"
            }
        }
    }
}

// 父组件传递 bool 和 i32
html! {
    limited_counter {
        disabled: is_disabled
        max_count: max_count
        on_increment: my_handler
        on_reset: my_reset_handler
    }
}
```

> [!tip]
>
> 使用类型化 Props 结构体（派生 `Default`），`html!` 宏自动将属性值映射到结构体字段，`bool` 和 `i32` 等类型无需手动解析。

## 自定义回调

通过 Props 结构体的可选回调字段传递回调函数：

```rust
#[derive(Clone, Default)]
struct CallbackInputProps {
    on_change: Option<Rc<dyn Fn(Event)>>,
    on_submit: Option<Rc<dyn Fn(Event)>>,
    on_reset: Option<Rc<dyn Fn(Event)>>,
}

// 子组件
#[component]
pub fn callback_input(node: VirtualNode<CallbackInputProps>) -> VirtualNode {
    let CallbackInputProps { on_change, on_submit, on_reset, .. } = node.try_get_props().unwrap_or_default();
    html! {
        div {
            input {
                r#type: "text"
                oninput: on_change
            }
            button {
                onclick: on_submit
                "Submit"
            }
            button {
                onclick: on_reset
                "Reset"
            }
        }
    }
}

// 父组件传递自定义回调
html! {
    callback_input {
        on_change: my_on_change_handler
        on_submit: my_on_submit_handler
        on_reset: my_on_reset_handler
    }
}
```

## 双向绑定（Shared Signal）

父子组件共享同一个 `Signal`，任一方修改立即同步到另一方：

```rust
let shared_text: Signal<String> = App::use_signal(|| "Type here...".to_string());
let shared_count: Signal<i32> = App::use_signal(|| 0);

// 父组件
html! {
    div {
        p { "Text: " shared_text }
        p { "Count: " shared_count }
        button {
            onclick: move |_event: Event| {
                let current: i32 = shared_count.get();
                shared_count.set(current + 1);
            }
            "+"
        }
    }
    // 将 Signal 直接传给子组件
    { child_input(shared_text, shared_count) }
}

// 子组件 — 接收 Signal 参数（非 props）
pub fn child_input(text_signal: Signal<String>, count_signal: Signal<i32>) -> VirtualNode {
    html! {
        div {
            input {
                r#type: "text"
                value: text_signal.get()
                oninput: UseEuvInput::on_input_value(text_signal)
            }
            button {
                onclick: move |_event: Event| {
                    let current: i32 = count_signal.get();
                    count_signal.set(current - 1);
                }
                "-"
            }
        }
    }
}
```

> [!tip]
>
> `Signal` 实现了 `Copy`，传递给子组件的是同一个信号的副本，指向相同的内部状态。不需要通过 props 传递。

## 跨组件响应式绑定（watch!）

使用 `watch!` 宏连接不同信号，一个信号变化时自动更新另一个。`watch!` 的订阅回调和初始执行均在 `batch` 内运行，同一帧内的级联 `set` 调用会被合并为一次 DOM 更新：

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
> 当两个信号互相监听时，`watch!` 闭包内的 `set` 调用在 `batch` 内执行，同一帧内的级联更新会被合并为一次 DOM 更新，避免中间状态闪烁。

多信号联动（RGB → Hex 颜色）：

```rust
let red: Signal<i32> = App::use_signal(|| 79);
let green: Signal<i32> = App::use_signal(|| 70);
let blue: Signal<i32> = App::use_signal(|| 229);
let hex_color: Signal<String> = App::use_signal(|| "#4f46e5".to_string());

watch!(red, green, blue, |red_value: i32, green_value: i32, blue_value: i32| {
    hex_color.set(format!(
        "#{:02x}{:02x}{:02x}",
        red_value.clamp(0, 255),
        green_value.clamp(0, 255),
        blue_value.clamp(0, 255)
    ));
});
```

<Bottom />
