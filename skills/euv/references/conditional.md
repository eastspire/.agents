---
synced_from: docs-pages/src/euv/usage-introduction/conditional.md@0c74235
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

## if 条件渲染

`if` 条件渲染支持**响应式**和**内联**两种模式。

### 响应式 if（花括号条件）

条件表达式用 `{}` 包裹，自动包装为动态节点，信号变化时条件重新求值并切换分支：

```rust
let show_details: Signal<bool> = App::use_signal(|| false);

html! {
    primary_button {
        label: "Toggle"
        onclick: move |_event: Event| {
            let current: bool = show_details.get();
            show_details.set(!current);
        }
        "Toggle"
    }
    if { show_details.get() } {
        div {
            "Details visible"
        }
    } else {
        ""
    }
}
```

> [!warning]
>
> 响应式 `if` 表达式的 `else` 分支不能省略，空内容请使用 `""`。

### 内联 if（裸条件）

条件直接写（无花括号），在父级渲染时一次性求值，不产生动态节点。适合在 `for` 循环中根据循环变量做条件判断：

```rust
html! {
    ul {
        for item in items.get() {
            if item.len() > 5 {
                li { "Long: " item.clone() }
            } else {
                li { "Short: " item.clone() }
            }
        }
    }
}
```

> [!tip]
>
> 内联 `if` 的 `else` 分支同样不能省略。内联 `if` 运行在父级渲染的上下文中，不创建独立的动态节点，因此性能开销更小。适合在 `for` 循环内部使用，避免为每个列表项创建多余的动态节点。

### else if 链

```rust
html! {
    if { score.get() >= 90 } {
        div { "Excellent" }
    } else if { score.get() >= 60 } {
        div { "Pass" }
    } else {
        div { "Fail" }
    }
}
```

## match 条件渲染

`match` 支持响应式和内联两种模式。

### 响应式 match

```rust
let user_type: Signal<String> = App::use_signal(|| "guest".to_string());

html! {
    match { user_type.get().as_str() } {
        "guest" => {
            div { "Welcome, guest!" }
        }
        "user" => {
            div { "Hello, user!" }
        }
        _ => {
            div { "Welcome, administrator!" }
        }
    }
}
```

### 内联 match

```rust
html! {
    ul {
        for (index, item) in items.get().iter().enumerate() {
            li {
                match index % 3 {
                    0 => { "First" }
                    1 => { "Second" }
                    _ => { "Other" }
                }
            }
        }
    }
}
```

> [!tip]
>
> 响应式 `match` 的花括号条件自动包装为动态节点，信号变化时重新匹配。内联 `match` 在父级渲染时一次性求值，不产生动态节点，适合在 `for` 循环内使用。

> [!tip]
>
> `match` 必须包含 `_` 通配分支，否则编译不通过。

## 属性值条件渲染

`if` 条件渲染不仅可用于子节点位置，还可在属性值中使用，实现响应式的属性切换：

```rust
let is_active: Signal<bool> = App::use_signal(|| false);

html! {
    div {
        class: if { is_active.get() } { c_active() } else { c_inactive() }
        "Content"
    }
}
```

样式中同样支持条件渲染：

```rust
html! {
    div {
        style: {
            color: if { is_active.get() } { "#4f46e5".to_string() } else { "inherit".to_string() };
            border_bottom: if { is_active.get() } { "2px solid #4f46e5".to_string() } else { "2px solid transparent".to_string() };
        }
        "Tab item"
    }
}
```

> [!tip]
>
> 属性值中的 `if` 条件会自动包装为响应式 `Signal<String>`，信号变化时属性值自动更新，无需手动订阅。

## Tab 切换示例

结合 `match` 和属性值条件渲染实现 Tab 切换：

```rust
let tab: Signal<String> = App::use_signal(|| "info".to_string());

html! {
    div {
        div {
            class: c_tab_bar()
            div {
                class: if { tab.get() == "info" } { c_tab_item_active() } else { c_tab_item_inactive() }
                onclick: move |_event: Event| { tab.set("info".to_string()); }
                "Info"
            }
            div {
                class: if { tab.get() == "settings" } { c_tab_item_active() } else { c_tab_item_inactive() }
                onclick: move |_event: Event| { tab.set("settings".to_string()); }
                "Settings"
            }
        }
        match { tab.get().as_str() } {
            "info" => {
                div { "Information content" }
            }
            _ => {
                div { "Settings content" }
            }
        }
    }
}
```

<Bottom />
