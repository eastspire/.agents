---
synced_from: docs-pages/src/euv/usage-introduction/list.md@f972247
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

## for 循环渲染

`html!` 宏支持 `for` 循环语法用于渲染列表。`for` 本身**不是响应式结构**（不同于 `if { expr }` 会生成动态节点），它是一个普通的 Rust `for` 循环，在父级渲染时运行。当 `for` 位于某个 动态节点 内部时，该动态节点信号变化会导致父级重新渲染，从而重新运行 `for` 循环。

迭代表达式支持**带花括号**和**不带花括号**两种写法，功能完全等价，生成相同的 Rust 代码。

### 迭代表达式带花括号 `{}`

花括号作为表达式边界，宏解析时剥掉外层 `{}` 提取内部表达式作为迭代源：

```rust
let items: Signal<Vec<String>> = App::use_signal(|| {
    vec!["Learn Rust".to_string(), "Build UI".to_string()]
});

html! {
    ul {
        for item in { items.get() } {
            li { item }
        }
    }
}
```

### 迭代表达式不带花括号

宏直接解析表达式，以循环体作为表达式结束边界：

```rust
html! {
    ul {
        for item in items.get() {
            li { item }
        }
        for index in 0..100 {
            li { format!("Item {}", index + 1) }
        }
    }
}
```

### 带索引的循环（花括号形式）

```rust
html! {
    ul {
        for (index, item) in { items.get().iter().enumerate() } {
            li {
                span { index }
                span { item }
            }
        }
    }
}
```

### 带索引的循环（无花括号形式）

```rust
html! {
    ul {
        for (index, item) in items.get().iter().enumerate() {
            li {
                span { index }
                span { item }
            }
        }
    }
}
```

> [!tip]
>
> `for` 循环的迭代表达式有**两种写法**：
>
> - **带花括号** `{ expr }`：花括号明确标出表达式边界，宏解析时会剥掉外层 `{}` 提取内部的表达式。
> - **不带花括号** `expr`：宏直接解析表达式，遇到循环体 `{` 时自动停止。
>
> 两种写法**功能完全等价**，生成完全相同的 Rust 代码，区别仅在于语法风格。

## 手动渲染列表

如果需要更细粒度的控制，也可以手动构建列表节点：

```rust
fn render_items(items: Signal<Vec<String>>) -> VirtualNode {
    let item_list: Vec<String> = items.get();
    let mut children_node: Vec<VirtualNode> = Vec::new();
    for (index, item) in item_list.iter().enumerate() {
        let item_clone: String = item.clone();
        let index_clone: usize = index;
        let node: VirtualNode = html! {
            li {
                item_clone
            }
        };
        children_node.push(node);
    }
    html! {
        ul {
            children_node
        }
    }
}
```

## 添加项目

```rust
let items: Signal<Vec<String>> = App::use_signal(|| Vec::new());
let items_updater: Signal<Vec<String>> = items;
let new_item: Signal<String> = App::use_signal(|| "".to_string());
let new_item_updater: Signal<String> = new_item;

html! {
    div {
        input {
            r#type: "text"
            value: new_item
            oninput: move |event: Event| {
                if let Some(target) = event.target()
                    && let Ok(input) = target.clone().dyn_into::<HtmlInputElement>() {
                        new_item_updater.set(input.value());
                    }
            }
        }
        button {
            onclick: move |_event: Event| {
                let text: String = new_item_updater.get();
                if !text.trim().is_empty() {
                    let mut current: Vec<String> = items_updater.get();
                    current.push(text);
                    items_updater.set(current);
                }
            }
            "Add"
        }
    }
}
```

## 删除项目

```rust
let items_remove: Signal<Vec<String>> = items;
let index_clone: usize = index;

html! {
    button {
        onclick: move |_event: Event| {
            let mut current: Vec<String> = items_remove.get();
            if index_clone < current.len() {
                current.remove(index_clone);
                items_remove.set(current);
            }
        }
        "Remove"
    }
}
```

<Bottom />
