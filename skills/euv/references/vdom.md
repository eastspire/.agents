---
synced_from: docs-pages/src/euv/usage-introduction/vdom.md@f972247
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

## VirtualNode 变体

`VirtualNode<T>` 是虚拟 DOM 的核心枚举，泛型参数 `T` 携带组件 Props 类型（非组件节点默认 `T = ()`），支持以下变体：

|            | 变体                                                                                          | 说明 |
| ---------- | --------------------------------------------------------------------------------------------- | ---- |
| `Element`  | HTML 元素节点，包含 `tag`（`Tag` 枚举）、`attributes`、`children`、`key`、`props`（仅组件有） |
| `Text`     | 文本节点（`TextNode`），可能绑定响应式信号                                                    |
| `Fragment` | 片段节点，包含多个子节点而无包装元素                                                          |
| `Dynamic`  | 动态节点，信号变化时自动重新渲染                                                              |
| `Empty`    | 空占位节点（默认值）                                                                          |

### VirtualNode trait 实现

| Trait       | 说明                                                                                                                                        |
| ----------- | ------------------------------------------------------------------------------------------------------------------------------------------- |
| `Clone`     | 深拷贝所有字段，`Element` 克隆 tag、attributes、children、key、props，`Dynamic` 克隆共享的 `Rc<UnsafeCell<RenderFnInner>>` 和 `HookContext` |
| `Debug`     | 格式化输出，`Dynamic` 变体省略内部细节，`props` 字段省略以保持简洁                                                                          |
| `PartialEq` | 视觉相等比较，用于动态节点 重新渲染时跳过不必要的 DOM 修补；`Event` 属性值始终视为相等，`Dynamic` 变体始终不相等（由内部渲染器管理）        |
| `Default`   | 返回 `VirtualNode::Empty`                                                                                                                   |

## Tag 枚举

`Tag` 枚举标识元素节点的类型：

|                     | 变体                                                   | 说明 |
| ------------------- | ------------------------------------------------------ | ---- |
| `Element(String)`   | 标准 HTML 元素或自定义 HTML5 元素（如 Web Components） |
| `Component(String)` | 用户定义的组件函数（通过 `#[component]` 标记）         |

`html!` 宏自动判断标签类型：标识符标签如果对应 `#[component]` 标记的函数，生成 `Tag::Component`；否则生成 `Tag::Element`。字符串字面量标签始终生成 `Tag::Element`。

## 创建节点

```rust
use euv::{web_sys::*, *};

// 创建动态节点（信号变化时自动重新渲染）
let count: Signal<i32> = App::use_signal(|| 0);
let node: VirtualNode = VirtualNode::create_dynamic(move |_: &mut HookContext| {
    html! {
        div { "Count: " count }
    }
});
```

### VirtualNode 构建方法

|                                           | 方法                                                                   | 说明 |
| ----------------------------------------- | ---------------------------------------------------------------------- | ---- |
| `create_dynamic<F>(render_fn: F) -> Self` | 从渲染闭包创建动态节点（闭包签名为 `FnMut(&mut HookContext) -> Self`） |

## VirtualNode 提取方法

|                                             | 方法                  | 返回值                                                                                                    | 说明 |
| ------------------------------------------- | --------------------- | --------------------------------------------------------------------------------------------------------- | ---- |
| `try_get_tag_name(&self)`                   | `Option<String>`      | 获取标签名（Element 和 Component 节点返回标签名，其他返回 `None`）                                        |
| `try_get_children(&self)`                   | `Option<&Vec<Self>>`  | 获取子节点引用（Element 和 Fragment 返回 `Some`，其他返回 `None`）                                        |
| `has_children(&self)`                       | `bool`                | 判断是否有非空子节点                                                                                      |
| `try_get_props(&self)`                      | `Option<T>`           | 克隆组件 Props（仅 Element 节点有 Props 时返回 `Some`，要求 `T: Clone`）                                  |
| `try_get_child_node(&self)`                 | `Option<VirtualNode>` | 获取子节点作为 VirtualNode（0 个子节点返回 `None`，1 个返回 `Some(该子节点)`，多个返回 `Some(Fragment)`） |
| `get_child_node(&self)`                     | `VirtualNode`         | 获取子节点作为 VirtualNode（0 个子节点返回 `Empty`，1 个返回该子节点，多个返回 `Fragment`）               |
| `extend_attributes<I>(self, extra) -> Self` | `Self`                | 在元素节点上追加 `AttributeEntry`，非 `Element` 变体原样返回（`html!` 宏内部使用，用户一般无需手动调用）  |

### 使用示例

```rust
// 获取标签名
let tag_name: Option<String> = node.try_get_tag_name();

// 获取子节点引用
let children: Option<&Vec<VirtualNode>> = node.try_get_children();

// 判断是否有子节点
let has_children: bool = node.has_children();

// 获取组件 Props（类型化方式）
let props: Option<MyCardProps> = node.try_get_props();

// 获取子节点作为 VirtualNode（适用于 children 字段）
let child_node: VirtualNode = node.get_child_node();
```

> [!tip]
>
> `get_child_node` 在 `#[component]` 函数中常用于提取 `children`：`let children: VirtualNode = node.get_child_node();`。它会根据子节点数量自动返回合适的变体。`try_get_child_node` 返回 `Option<VirtualNode>`，适用于需要区分有无子节点的场景。

## TextNode

`TextNode` 表示文本节点，包含文本内容（`content`）和一个可选的响应式信号（`signal`）。

```rust
// 创建静态文本节点
let text: TextNode = TextNode::new("Hello".to_string(), None);

// 创建响应式文本节点（由 Signal 驱动自动更新）
let text_signal: Signal<String> = App::use_signal(|| "Hello".to_string());
let reactive_text: TextNode = TextNode::new(
    text_signal.get(),
    Some(text_signal),
);
```

> [!tip]
>
> 通常不需要手动创建 `TextNode`，`html!` 宏会自动处理。`Signal<T>`（要求 `T: Display`）通过 `From<Signal<T>> for VirtualNode` 实现自动创建响应式文本节点。`TextNode` 的 `PartialEq` 实现仅比较文本内容，不比较信号（信号不影响视觉输出）。

## AttributeEntry 结构体

`AttributeEntry` 表示虚拟 DOM 节点上的单个属性，由属性名和属性值组成：

```rust
let attr: AttributeEntry = AttributeEntry::new(
    "class".to_string(),
    AttributeValue::Css(c_card()),
);
```

> [!tip]
>
> 通常不需要手动创建 `AttributeEntry`，`html!` 宏会自动生成。`AttributeEntry` 实现了 `PartialEq`，基于视觉输出进行比较（`Event` 值始终视为相等）。

## AttributeValue 枚举

`AttributeValue` 表示 HTML 属性的值，支持静态文本、响应式信号、事件处理器、动态表达式和 CSS 类引用：

|                             | 变体                                                                  | 说明 |
| --------------------------- | --------------------------------------------------------------------- | ---- |
| `Text(String)`              | 静态字符串值                                                          |
| `Signal(Signal<String>)`    | 响应式信号值                                                          |
| `Event(NativeEventHandler)` | 事件处理器                                                            |
| `Dynamic(String)`           | 动态表达式值（用于组件 props，`bool`/`i32`/`f64` 等类型的字符串表示） |
| `Css(Css)`                  | CSS 类引用                                                            |

## AttributeValue 工厂方法

`AttributeValue` 提供以下工厂方法，用于创建响应式属性值和合并多个属性值：

|                                                        | 方法                                                                     | 说明 |
| ------------------------------------------------------ | ------------------------------------------------------------------------ | ---- |
| `AttributeValue::reactive<F>(compute: F) -> Self`      | 从计算闭包创建响应式属性值，返回 `Signal<String>` 包装的 `Self::Signal`  |
| `AttributeValue::merge_class(values: &[Self]) -> Self` | 合并多个 `class:` 属性值为单个 `Self`，支持 `Css`、`Text`、`Signal` 混合 |
| `AttributeValue::merge_style(values: &[Self]) -> Self` | 合并多个 `style:` 属性值为单个 `Self`，支持 `Text`、`Signal` 混合        |

```rust
// 合并多个 class 属性
let merged: AttributeValue = AttributeValue::merge_class(&[
    AttributeValue::Css(c_flex_row()),
    AttributeValue::Css(c_padding()),
    AttributeValue::Text("extra-class".to_string()),
]);

// 合并多个 style 属性
let merged_style: AttributeValue = AttributeValue::merge_style(&[
    AttributeValue::Text("display: flex".to_string()),
    AttributeValue::Text("gap: 10px".to_string()),
]);
```

> [!tip]
>
> `reactive` 用于 `html!` 宏内部为包含 `if` 条件的属性值生成响应式信号。`merge_class` 和 `merge_style` 用于 `html!` 宏内部合并同一元素上的多个 `class:` 或 `style:` 属性。如果合并值中包含 `Signal`，结果自动成为响应式属性。通常不需要手动使用这些方法。

## AttributeValue 类型转换

框架通过标准库 `From` trait 实现了多种类型到 `AttributeValue` 的自动转换：

| 源类型                       | 目标变体                           | 说明                                              |
| ---------------------------- | ---------------------------------- | ------------------------------------------------- |
| `String` / `&str`            | `AttributeValue::Text`             | 静态字符串值                                      |
| `Signal<String>`             | `AttributeValue::Signal`           | 响应式信号值                                      |
| `Signal<bool>`               | `AttributeValue::Signal`           | 响应式布尔信号（自动映射为 `"true"` / `"false"`） |
| `bool` / `i32` / `f64`       | `AttributeValue::Dynamic`          | 动态表达式值（用于组件 props）                    |
| `Css` / `&'static Css`       | `AttributeValue::Css`              | CSS 类引用                                        |
| `FnMut(Event) + 'static`     | `AttributeValue::Event`            | 闭包事件处理器                                    |
| `NativeEventHandler`         | `AttributeValue::Event`            | 事件处理器                                        |
| `Option<NativeEventHandler>` | `AttributeValue::Event` 或 `Text`  | 可选事件处理器                                    |
| `Option<Signal<String>>`     | `AttributeValue::Signal` 或 `Text` | 可选响应式信号                                    |

> [!tip]
>
> 这些 `From` 实现由 `html!` 宏在编译时自动调用，无需手动转换。事件处理器闭包自动包装为 `NativeEventHandler`。信号值自动注册依赖关系，变化时触发 DOM 更新。

## EventAdapter / AttrValueAdapter

`EventAdapter<T>` 和 `AttrValueAdapter<T>` 是框架内部的适配器结构体，由 `html!` 宏生成代码使用，用于将各种类型的属性值表达式统一转换为 `AttributeValue`：

|                       | 结构体           | 说明                                                                                                                                                               |
| --------------------- | ---------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `EventAdapter<T>`     | 事件属性适配器   | 处理三种情况：`FnMut(Event)` 闭包 → `AttributeValue::Event`；`NativeEventHandler` 直接 → `AttributeValue::Event`；`Option<NativeEventHandler>` → `Event` 或 `Text` |
| `AttrValueAdapter<T>` | 通用属性值适配器 | 事件属性（`on` 前缀）走事件适配逻辑；非事件属性通过 `From` trait 转为响应式值                                                                                      |

> [!tip]
>
> 这两个适配器是 `html!` 宏内部使用的优化机制，替代了之前为每个属性站点生成的多个辅助类型（`__EventWrapper`、`__IsClosure`、`__ClosurePicker` 等），显著减少了宏输出代码量。通常不需要手动使用。

## VirtualNode 类型转换

框架通过标准库 `From` trait 实现了多种类型到 `VirtualNode` 的自动转换：

| 源类型                                             | 目标变体                           | 说明                                 |
| -------------------------------------------------- | ---------------------------------- | ------------------------------------ |
| `String` / `&str`                                  | `VirtualNode::Text`                | 静态文本节点                         |
| `i32` / `usize` / `bool`                           | `VirtualNode::Text`                | 数值/布尔值文本节点                  |
| `Signal<T>`（要求 `T: Display`）                   | `VirtualNode::Text`（带信号）      | 响应式文本节点，自动更新             |
| `FnMut(&mut HookContext) -> VirtualNode + 'static` | `VirtualNode::Dynamic`             | 动态节点，信号变化时自动重新渲染     |
| `Vec<VirtualNode>`                                 | `VirtualNode::Fragment`            | 片段节点（空列表返回 `Empty`）       |
| `Option<VirtualNode>`                              | `VirtualNode` 或 `Empty`           | `Some` 返回节点，`None` 返回 `Empty` |
| `Option<Vec<VirtualNode>>`                         | `VirtualNode::Fragment` 或 `Empty` | 可选片段节点                         |

> [!tip]
>
> 在 `html!` 宏中，裸标识符通过 `From` 转换（静态），`{expr}` 花括号表达式自动包装为动态节点（响应式）。`FnMut(&mut HookContext) -> VirtualNode` 闭包的 `From` 实现会自动创建动态节点并附带 `HookContext`。

## 内联样式

```rust
// 从键值对数组直接创建 CSS 字符串（静态样式，html! 宏内部使用的优化方法）
let css_string: String = Css::style_string(&[
    ("flex_direction", "column"),
    ("padding", "10px"),
]);

// 从 owned 键值对数组创建 CSS 字符串（响应式样式，用于 if 条件场景）
let css_string: String = Css::style_string_owned(&[
    ("color".to_string(), "red".to_string()),
    ("font_size".to_string(), "16px".to_string()),
]);
```

### Css 样式方法

|                                                                 | 方法                                                                | 说明 |
| --------------------------------------------------------------- | ------------------------------------------------------------------- | ---- |
| `Css::style_string(props: &[(&str, &str)]) -> String`           | 从借用键值对数组直接创建 CSS 字符串（`html!` 宏内部使用的优化方法） |
| `Css::style_string_owned(props: &[(String, String)]) -> String` | 从 owned 键值对数组创建 CSS 字符串（用于响应式 `if` 条件样式）      |

> [!tip]
>
> 样式属性名使用 snake_case，框架自动转换为 kebab-case（如 `flex_direction` → `flex-direction`）。

## PseudoRule 结构体

`PseudoRule` 表示 CSS 伪类/伪元素规则，附加在某个 CSS 类上：

```rust
let rule: PseudoRule = PseudoRule::new(
    ":hover".to_string(),
    "background: #4338ca;".to_string(),
);
```

| 字段       | 类型     | 说明                                                             |
| ---------- | -------- | ---------------------------------------------------------------- |
| `selector` | `String` | CSS 伪选择器后缀（如 `:hover`、`::before`、`:nth-child(2n)` 等） |
| `style`    | `String` | 该伪规则内的 CSS 声明字符串                                      |

## MediaRule 结构体

`MediaRule` 表示 CSS `@media` 规则，附加在某个 CSS 类上：

```rust
let rule: MediaRule = MediaRule::new(
    "(max-width: 767px)".to_string(),
    "font-size: 14px; padding: 8px;".to_string(),
);
```

| 字段           | 类型              | 说明                                                   |
| -------------- | ----------------- | ------------------------------------------------------ |
| `query`        | `String`          | 媒体查询条件（如 `(max-width: 767px)`）                |
| `style`        | `String`          | 该媒体规则内的 CSS 声明字符串                          |
| `pseudo_rules` | `Vec<PseudoRule>` | 媒体规则内嵌套的伪元素规则（如 `::-webkit-scrollbar`） |

## CSS 类

```rust
// class! 宏定义的 CSS 类可直接在 html! 中使用
html! {
    div {
        class: c_card()
        "Content"
    }
}
```

`Css` 结构体包含 `name`、`style`、`pseudo_rules` 和 `media_rules` 字段，首次使用时通过 `inject_style()` 自动将样式注入 DOM 的 `<style>` 元素。注入规则为：基础样式 → 伪类/伪元素规则 → 媒体查询规则。

`Css` 实现了 `Display` trait，`format!("{}", css)` 输出类名字符串。`Css` 的 `PartialEq` 实现仅比较类名（类名唯一标识视觉样式规则）。

`Css` 提供的主要方法：

|                                                                  | 方法                                                                    | 说明 |
| ---------------------------------------------------------------- | ----------------------------------------------------------------------- | ---- |
| `new(name, style, pseudo_rules, media_rules) -> Self`            | 创建 CSS 类（包含伪类规则和媒体查询）                                   |
| `inject_style(&self)`                                            | 将样式注入 DOM（重复调用只注入一次）                                    |
| `inject_css<S: AsRef<str>>(css: S)`                              | 向全局 `<style>` 元素追加 CSS 文本（用于注入 `@keyframes`、全局重置等） |
| `style_string<K, V>(props: &[(K, V)]) -> String`                 | 从键值对数组直接创建 CSS 字符串（`html!` 宏内部使用的优化方法）         |
| `style_string_owned(props: &[(String, String)]) -> String`       | 从 owned 键值对数组创建 CSS 字符串（用于响应式 `if` 条件样式）          |
| `parse_pseudo_rules<I: AsRef<str>>(input: I) -> Vec<PseudoRule>` | 从紧凑序列化字符串解析伪类/伪元素规则（`class!` 宏内部使用）            |
| `parse_media_rules<S: AsRef<str>>(input: S) -> Vec<MediaRule>`   | 从紧凑序列化字符串解析媒体查询规则（`class!` 宏内部使用）               |

> [!tip]
>
> CSS 类首次使用时自动注入样式到 DOM，无需手动引入 CSS 文件。`inject_css` 采用追加模式（`appendChild`），不会读取和重写整个 `<style>` 元素的内容，避免性能开销。`Css` 实现了 `Display` trait，`format!("{}", css)` 输出类名字符串，用于响应式 `if` 条件中的 class 属性。`parse_pseudo_rules` 和 `parse_media_rules` 是 `class!` 宏内部使用的解析方法，通常不需要手动调用。

<Bottom />
