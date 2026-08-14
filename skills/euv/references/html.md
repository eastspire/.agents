---
synced_from: docs-pages/src/euv/macros/html.md@f972247
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

## 基本用法

```rust
use euv::{web_sys::*, *};

html! {
    div {
        class: c_container()
        h1 { "Hello, euv!" }
        button {
            onclick: move |_| { /* handle click */ },
            "Click me"
        }
    }
}
```

## 字符串属性

```rust
html! {
    input {
        r#type: "text"
        placeholder: "Enter your name"
        value: "default value"
    }
}
```

> [!tip]
>
> Rust 关键字（如 `type`）需使用 `r#` 前缀：`r#type: "text"`

## 信号属性

```rust
let count: Signal<i32> = App::use_signal(|| 0);

html! {
    span { count }
}
```

## 事件属性

事件闭包签名为 `FnMut(Event)`，其中 `Event` 是 `web_sys::Event`：

```rust
html! {
    button {
        onclick: move |event: Event| {
            // 处理点击
        }
        "Click me"
    }
}
```

## CSS 类属性

```rust
html! {
    div {
        class: c_container()
        "Content"
    }
}
```

### 多 class 合并

同一元素上可以声明多个 `class:` 属性，框架会自动将它们合并为一个空格分隔的类名字符串：

```rust
html! {
    div {
        class: c_flex_row()
        class: c_padding()
        class: c_card()
        "Multiple classes"
    }
}
```

> [!tip]
>
> 多个 `class:` 属性在编译时自动合并，效果等同于将所有类名拼接。如果其中任何一个 class 值是响应式 `Signal`，合并后的结果也会自动成为响应式属性。

## 多 style 合并

同一元素上可以声明多个 `style:` 属性，框架会自动将它们合并为完整的 CSS 样式字符串：

```rust
html! {
    div {
        style: {display: "flex"; gap: "10px";}
        style: {padding: "20px"; background: "white";}
        "Merged styles"
    }
}
```

> [!tip]
>
> 多个 `style:` 属性在编译时自动合并。如果其中任何一个 style 包含响应式 `if` 条件，合并后的结果也会自动成为响应式属性。

## 内联样式属性

支持两种语法——对象语法和表达式语法：

### 对象语法

```rust
html! {
    div {
        style: {display: "flex"; padding: "10px"; font_size: "14px";}
        "Content"
    }
}
```

### 动态样式值

样式属性值支持花括号包裹的动态表达式：

```rust
html! {
    div {
        style: {background: {color};}
        "Dynamic background"
    }
}
```

### 样式中的条件渲染

样式属性值同样支持 `if` 条件渲染，实现响应式的样式切换：

```rust
let is_active: Signal<bool> = App::use_signal(|| false);

html! {
    div {
        style: {
            color: if { is_active.get() } { "#4f46e5".to_string() } else { "inherit".to_string() };
            font_weight: if { is_active.get() } { "700".to_string() } else { "400".to_string() };
        }
        "Conditional styles"
    }
}
```

> [!tip]
>
> 样式属性值中的 `if` 条件会自动包装为响应式 `Signal<String>`，信号变化时样式自动更新。

> [!tip]
>
> 内联样式使用 snake_case，自动转换为 kebab-case（如 `font_size` → `font-size`）。

## 布尔属性

```rust
let agree: Signal<bool> = App::use_signal(|| true);

html! {
    input {
        r#type: "checkbox"
        checked: agree
    }
}
```

## 自定义属性

```rust
html! {
    div {
        data_role: "container"
        data_id: "12345"
        aria_label: "Demo section"
        "Custom attributes"
    }
}
```

> [!tip]
>
> `data_*` 和 `aria_*` 属性自动转换为 `data-*` 和 `aria-*` 格式。使用 `r#` 前缀处理 Rust 保留字。

## 条件渲染

`html!` 宏支持 `if` 条件渲染，有**响应式**和**内联**两种模式。

### 响应式 if（花括号条件）

条件表达式用 `{}` 包裹，自动包装为动态节点（响应式）。信号变化时条件会重新求值并切换渲染分支：

```rust
let show: Signal<bool> = App::use_signal(|| true);

html! {
    if { show.get() } {
        div { "Visible" }
    } else {
        ""
    }
}
```

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

### else if 链（响应式）

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

### match 表达式

`match` 也支持响应式和内联两种模式。响应式 `match { expr }` 自动包装为动态节点；内联 `match expr` 在父级渲染时一次性求值：

```rust
// 响应式 match——信号变化时重新匹配
html! {
    match { route.get().as_str() } {
        "/" => { page_home() }
        "/about" => { page_about() }
        _ => { page_not_found() }
    }
}

// 内联 match——在父级渲染时一次性求值，适合 for 循环内
html! {
    ul {
        for (index, item) in items.iter().enumerate() {
            li {
                match index % 2 {
                    0 => { "Even" }
                    _ => { "Odd" }
                }
            }
        }
    }
}
```

> [!warning]
>
> 响应式 `if` 的 `else` 分支不能省略，`match` 必须包含 `_` 通配分支。

### 属性值条件渲染

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

## 列表渲染（for 循环）

`html!` 宏支持 `for` 循环语法来渲染列表。迭代表达式支持带花括号和不带花括号两种写法。`for` 本身**不是响应式结构**（不同于 `if { expr }` 会生成动态节点），它是一个普通的 Rust `for` 循环，在父级渲染时运行。

### 带花括号形式

花括号作为表达式边界，宏解析时剥掉外层 `{}` 提取内部表达式作为迭代源：

```rust
let items: Signal<Vec<String>> = App::use_signal(|| vec!["Rust".to_string(), "euv".to_string()]);

html! {
    ul {
        for item in { items.get() } {
            li { item }
        }
    }
}
```

带索引的循环：

```rust
html! {
    ul {
        for (index, item) in { items.get().iter().enumerate() } {
            li { item }
        }
    }
}
```

### 不带花括号形式

宏直接解析表达式，以循环体 `{` 作为表达式结束边界：

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

带索引的循环：

```rust
html! {
    ul {
        for (index, item) in items.get().iter().enumerate() {
            li { item }
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

### 带 key 的列表渲染

为列表项添加 `key` 属性可以启用 Keyed Diffing，优化列表重排序时的 DOM 操作：

```rust
struct Item {
    id: String,
    name: String,
}

html! {
    ul {
        for item in { items.get() } {
            li {
                key: item.id
                item.name
            }
        }
    }
}
```

> [!tip]
>
> `key` 属性帮助框架识别哪些节点可以复用。当列表项的顺序变化时，Keyed Diffing 通过 `key` 匹配已有 DOM 节点，仅移动节点而不重建，提升性能。如果列表项没有 `key`，框架按位置逐一对比。

## 字符串字面量标签（Web Components）

`html!` 宏支持使用字符串字面量作为标签名，用于渲染自定义 HTML5 元素（如 Web Components）。字符串字面量标签始终生成 `Tag::Element`，不会被识别为组件：

```rust
html! {
    "my-custom-element" {
        class: c_container()
        "Web Component content"
    }
    "paper-button" {
        raised: true
        "Material button"
    }
}
```

> [!tip]
>
> 字符串字面量标签适用于渲染 Web Components 或自定义 HTML5 元素。标识符标签（如 `div`、`my_card`）如果对应 `#[component]` 标记的函数，会被识别为组件；否则作为原生 HTML 元素处理。字符串字面量标签则始终作为原生 HTML 元素，即使存在同名组件函数。

## 动态标签

`html!` 宏支持动态标签语法 `{tag_expr} { content }`，标签名在运行时根据信号值决定。标签可以是原生 HTML 元素，也可以是用户组件：

```rust
let tag_name: Signal<String> = App::use_signal(|| "div".to_string());

html! {
    div {
        { tag_name.get() } {
            "Hello, dynamic tag!"
        }
    }
}
```

动态标签支持传入属性：

```rust
html! {
    { tag_name.get() } {
        title: "Dynamic my_card"
        onclick: move |_event: Event| { /* handle */ }
        { content.get() }
    }
}
```

> [!tip]
>
> 动态标签通过 `{expr}` 语法将标签名变为响应式，信号变化时自动重新渲染。如果动态标签名对应 `#[component]` 标记的函数，会被识别为组件；否则作为原生 HTML 元素处理。

> [!warning]
>
> 动态标签切换时，整个标签及其子树会被替换，不会进行增量 Diff。

## 动态属性键

`html!` 宏支持动态属性键语法 `{key}: value`，属性名在运行时根据变量值决定：

```rust
let dynamic_key: Signal<String> = App::use_signal(|| "data-custom".to_string());
let dynamic_value: Signal<String> = App::use_signal(String::new);

html! {
    div {
        { dynamic_key.get() }: dynamic_value
        class: c_demo()
        "Dynamic attribute"
    }
}
```

静态属性键也支持表达式形式：

```rust
let static_key: String = "data-role".to_string();
let static_value: String = "container".to_string();

html! {
    div {
        { static_key }: static_value
        "Static key, static value"
    }
}
```

`class!` 宏同样支持动态 CSS 属性键：

```rust
let class_prop_key: Signal<String> = App::use_signal(|| "background".to_string());
let class_prop_value: Signal<String> = App::use_signal(|| "#4f46e5".to_string());

class! {
    pub c_dynamic_demo(key: &str, value: &str) {
        {key}: {value};
    }
}

html! {
    div {
        class: c_dynamic_demo(&class_prop_key.get(), &class_prop_value.get())
        "Dynamic CSS property"
    }
}
```

> [!tip]
>
> 动态属性键通过 `{expr}` 语法将属性名变为响应式，常用于 `data-*` 自定义属性或动态 CSS 属性等场景。属性键和属性值都可以是动态表达式。

## 嵌入表达式

### 动态表达式（响应式）

使用花括号 `{expr}` 包裹的表达式会自动包装为动态节点，信号变化时自动重新渲染：

```rust
html! {
    div {
        {format!("Count: {}", count.get())}
    }
}
```

### 静态表达式

裸标识符（无花括号）通过 `From` trait 进行静态一次性转换，不会响应信号变化：

```rust
html! {
    div {
        count
    }
}
```

## 组件标签

使用 `#[component]` 属性宏标记的函数会被 `html!` 宏识别为自定义组件。在 `html!` 宏中使用同名标签即可调用该组件，框架自动将属性映射到 Props 结构体字段：

```rust
html! {
    my_card {
        title: "Card Title"
        p { "Card content" }
    }
}
```

等价于调用 `my_card(MyCardProps { title: "Card Title", ..Default::default() })`，子节点通过 `node.get_child_node()` 获取。

```rust
#[derive(Clone, Default)]
struct MyCardProps {
    title: &'static str,
}

#[component]
pub fn my_card(node: VirtualNode<MyCardProps>) -> VirtualNode {
    let MyCardProps { title, .. }: MyCardProps = node.try_get_props().unwrap_or_default();
    let children: VirtualNode = node.get_child_node();
    html! {
        div {
            h3 { title }
            children
        }
    }
}
```

> [!tip]
>
> 组件函数必须使用 `#[component]` 属性宏标记，`html!` 宏在编译时扫描项目源码查找所有 `#[component]` 标记的函数。未标记的标识符一律被视为原生 HTML 元素。组件的属性通过类型化 Props 结构体接收，未传递的字段使用 `Default::default()` 填充。推荐使用 `node.get_child_node()` 获取子节点，Props 结构体中无需定义 `children` 字段。

<Bottom />
