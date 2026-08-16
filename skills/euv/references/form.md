---
synced_from: docs-pages/src/euv/usage-introduction/form.md@0c74235
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

## 文本输入

```rust
use euv::{web_sys::*, *};
use euv_ui::*;

let username: Signal<String> = App::use_signal(|| "".to_string());
let username_updater: Signal<String> = username;

html! {
    input {
        r#type: "text"
        placeholder: "Enter username"
        value: username
        oninput: move |event: Event| {
            if let Some(target) = event.target()
                && let Ok(input) = target.clone().dyn_into::<HtmlInputElement>() {
                    username_updater.set(input.value());
                }
        }
    }
}
```

## 复选框

```rust
let agree: Signal<bool> = App::use_signal(|| true);
let agree_updater: Signal<bool> = agree;

html! {
    input {
        r#type: "checkbox"
        checked: agree
        onchange: move |event: Event| {
            if let Some(target) = event.target()
                && let Ok(input) = target.clone().dyn_into::<HtmlInputElement>() {
                    agree_updater.set(input.checked());
                }
        }
    }
    label { "I agree to the terms" }
}
```

> [!tip]
>
> 复选框必须使用 `onchange` 而非 `oninput` 监听变化。通过 `event.target()` 获取 DOM 元素后，用 `dyn_into::<HtmlInputElement>()` 读取 `checked` 属性。

## 表单验证

```rust
let errors: Signal<String> = App::use_signal(|| "".to_string());
let submitted: Signal<String> = App::use_signal(|| "".to_string());

html! {
    button {
        onclick: move |_event: Event| {
            let mut validation_errors: Vec<String> = Vec::new();
            if username.get().trim().is_empty() {
                validation_errors.push("Username is required".to_string());
            }
            if email.get().trim().is_empty() {
                validation_errors.push("Email is required".to_string());
            }
            if validation_errors.is_empty() {
                errors.set("".to_string());
                submitted.set(format!("Submitted: {}", username.get()));
            } else {
                errors.set(validation_errors.join("; "));
            }
        }
        "Submit"
    }
}
```

> [!warning]
>
> `onsubmit` 事件中需要自行阻止默认提交行为（`event.prevent_default()`），否则页面会刷新。

## 下拉框（Select）

使用 `select` + `option` 组合创建下拉选择框，通过 `onchange` 事件和 `UseEuvInput::on_change_value` 绑定选中值：

```rust
let selected_fruit: Signal<String> = App::use_signal(|| "apple".to_string());

html! {
    select {
        value: selected_fruit.get()
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
}
```

### 级联下拉框

通过 `watch!` 或 `onchange` 事件联动多个下拉框：

```rust
let selected_country: Signal<String> = App::use_signal(String::new);
let selected_city: Signal<String> = App::use_signal(String::new);

html! {
    select {
        onchange: move |event: Event| {
            if let Some(target) = event.target()
                && let Ok(select) = target.clone().dyn_into::<HtmlSelectElement>() {
                    selected_country.set(select.value());
                    selected_city.set(String::new());
                }
        }
        option { value: "" "-- Select Country --" }
        option { value: "china" "China" }
        option { value: "japan" "Japan" }
    }
    if { selected_country.get() == "china" } {
        select {
            onchange: UseEuvInput::on_change_value(selected_city)
            option { value: "beijing" "Beijing" }
            option { value: "shanghai" "Shanghai" }
        }
    } else if { selected_country.get() == "japan" } {
        select {
            onchange: UseEuvInput::on_change_value(selected_city)
            option { value: "tokyo" "Tokyo" }
            option { value: "osaka" "Osaka" }
        }
    } else {
        ""
    }
}
```

> [!tip]
>
> `UseEuvInput::on_change_value` 自动识别 `HtmlSelectElement`，无需为 select 编写单独的事件处理器。

## 文本域（Textarea）

```rust
let message: Signal<String> = App::use_signal(String::new);

html! {
    textarea {
        id: "message"
        name: "message"
        placeholder: "Write a message..."
        value: message.get()
        class: c_textarea_input()
        rows: "4"
        oninput: UseEuvInput::on_input_value(message)
    }
    p {
        { format!("{} / 200 characters", message.get().len()) }
    }
}
```

> [!tip]
>
> `on_input_value` 自动识别 `HtmlTextAreaElement`，与 `input` 和 `select` 使用相同的事件处理器函数。

## 文件上传

### 文件选择

使用 `<input type="file">` 实现文件选择，通过 `onchange` 事件读取文件列表：

```rust
html! {
    input {
        r#type: "file"
        accept: ".png,.jpg,image/*"
        multiple: true
        onchange: move |event: Event| {
            if let Some(target) = event.target()
                && let Ok(input) = target.clone().dyn_into::<HtmlInputElement>() {
                    if let Some(files) = input.files() {
                        let count: u32 = files.length();
                        for i in 0..count {
                            if let Some(file) = files.get(i) {
                                let name: String = file.name();
                                web_sys::console::log_1(&format!("File: {}", name).into());
                            }
                        }
                    }
                }
        }
    }
}
```

### 拖拽上传

结合拖拽事件实现拖拽上传区域：

```rust
let is_drag_over: Signal<bool> = App::use_signal(|| false);
let is_drag_over_for_style: Signal<bool> = is_drag_over;

html! {
    div {
        class: if { is_drag_over.get() } { c_event_drop_zone_active() } else { c_event_drop_zone() }
        ondragenter: move |_event: Event| { is_drag_over.set(true); }
        ondragleave: move |_event: Event| { is_drag_over.set(false); }
        ondragover: move |event: Event| { event.prevent_default(); }
        ondrop: move |event: Event| {
            event.prevent_default();
            is_drag_over.set(false);
            if let Some(drag_event) = event.dyn_ref::<DragEvent>() {
                if let Some(data_transfer) = drag_event.data_transfer() {
                    if let Some(files) = data_transfer.files() {
                        let count: u32 = files.length();
                        web_sys::console::log_1(&format!("Dropped {} files", count).into());
                    }
                }
            }
        }
        p { "Drag & drop files here" }
    }
}
```

> [!tip]
>
> `ondragover` 中需要调用 `event.prevent_default()` 才能使 `ondrop` 事件正常触发。

<Bottom />
