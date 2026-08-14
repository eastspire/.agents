---
synced_from: docs-pages/src/euv/usage-introduction/select.md@f972247
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

euv 支持原生的 `<select>` 和 `<textarea>` 元素，通过信号绑定值并使用 `UseEuvInput` 工具处理事件。

## Select 下拉框

### 基本使用

使用 `onchange: UseEuvInput::on_change_value(signal)` 绑定信号：

```rust
use euv::{web_sys::*, *};
use euv_ui::*;

let selected_fruit: Signal<String> = App::use_signal(|| "apple".to_string());

html! {
    div {
        select {
            value: selected_fruit
            onchange: UseEuvInput::on_change_value(selected_fruit)
            option {
                value: "apple"
                "Apple"
            }
            option {
                value: "banana"
                "Banana"
            }
            option {
                value: "cherry"
                "Cherry"
            }
        }
        p {
            "Selected: "
            selected_fruit
        }
    }
}
```

### 级联选择

当第一个 select 变化时动态更新第二个 select 的选项：

```rust
let country: Signal<String> = App::use_signal(String::new);
let city: Signal<String> = App::use_signal(String::new);
let cities: Signal<Vec<(String, String)>> = App::use_signal(|| Vec::new());

let on_country_change = move |event: Event| {
    UseEuvInput::on_change_value(country)(event);
    let c = country.get();
    let items = match c.as_str() {
        "china" => vec![
            ("beijing".to_string(), "Beijing".to_string()),
            ("shanghai".to_string(), "Shanghai".to_string()),
        ],
        "japan" => vec![
            ("tokyo".to_string(), "Tokyo".to_string()),
            ("osaka".to_string(), "Osaka".to_string()),
        ],
        _ => Vec::new(),
    };
    cities.set(items);
    city.set(String::new());
};

html! {
    div {
        select {
            onchange: on_country_change
            option { value: "" "-- Select Country --" }
            option { value: "china" "China" }
            option { value: "japan" "Japan" }
        }
        if { !country.get().is_empty() } {
            select {
                value: city
                onchange: UseEuvInput::on_change_value(city)
                for (value, label) in { cities.get() } {
                    option {
                        value: value.clone()
                        label.clone()
                    }
                }
            }
        }
    }
}
```

## Textarea 文本框

### 基本使用

`textarea` 的用法与 `input` 类似，通过 `value` 和 `oninput` 绑定信号：

```rust
let content: Signal<String> = App::use_signal(String::new);

html! {
    textarea {
        placeholder: "Enter your feedback"
        value: content
        oninput: UseEuvInput::on_input_value(content)
        rows: "5"
        onfocus: UseEuvInput::on_focus_scroll_into_view()
        onblur: UseEuvInput::on_blur_restore_height()
    }
}
```

### 带字符计数的 Textarea

```rust
let feedback: Signal<String> = App::use_signal(String::new);
let feedback_error: Signal<String> = App::use_signal(String::new);

let on_input = move |event: Event| {
    UseEuvInput::on_input_value(feedback)(event);
    let len = feedback.get().len();
    if len > 200 {
        feedback_error.set("Exceeded 200 characters".to_string());
    } else {
        feedback_error.set(String::new());
    }
};

html! {
    div {
        textarea {
            placeholder: "Enter your feedback"
            value: feedback
            oninput: on_input
            rows: "5"
        }
        p {
            format!("{} / 200 characters", feedback.get().len())
        }
        if { !feedback_error.get().is_empty() } {
            p {
                style: {color: "red";}
                feedback_error
            }
        }
    }
}
```

> [!tip]
>
> `<select>` 使用 `onchange` + `UseEuvInput::on_change_value` 绑定信号值。`<textarea>` 使用 `oninput` + `UseEuvInput::on_input_value` 实现实时双向绑定。级联选择通过监听第一个 select 的变化动态更新第二个 select 的选项列表。

<Bottom />
