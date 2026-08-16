---
synced_from: docs-pages/src/euv/macros/class.md@0c74235
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

## 定义 CSS 类

```rust
use euv::*;

class! {
    pub container {
        max_width: "800px";
        margin: "0 auto";
    }
    pub(crate) header {
        font_size: "28px";
    }
    hidden {
        display: "none";
    }
}
```

## 可见性修饰

|              | 修饰符                      | 说明 |
| ------------ | --------------------------- | ---- |
| `pub`        | 公开，生成公开的 CSS 类函数 |
| `pub(crate)` | crate 内可见                |
| `pub(super)` | 父模块内可见                |
| 无修饰       | 私有                        |

## 参数化 CSS 类

`class!` 宏支持定义带参数的 CSS 类，样式值可动态计算：

```rust
class! {
    pub dynamic_color(color: &str) {
        color: {color};
        padding: "8px 16px";
        border_radius: "4px";
    }
    pub size_box(width: &str, height: &str) {
        width: {width};
        height: {height};
        border: "1px solid #ccc";
    }
}
```

使用：

```rust
html! {
    div {
        class: dynamic_color("#4f46e5")
        "Colored text"
    }
    div {
        class: size_box("200px", "100px")
        "Sized box"
    }
}
```

> [!tip]
>
> 参数化 CSS 类的样式值使用花括号 `{param}` 包裹动态表达式，静态值仍使用字符串字面量。框架会根据参数值生成唯一的类名（如 `dynamic_color-4f46e5`），避免样式冲突。

> [!warning]
>
> 参数化类返回 `Css` 实例（每次调用创建新实例），非参数化类返回 `&'static Css`（通过 `OnceLock` 单例缓存）。对于频繁使用的静态样式，优先使用非参数化形式以获得更好的性能。

## 继承（extends）

`class!` 宏支持类继承语法，一个类可以继承一个或多个父类的样式属性、伪类规则和媒体查询规则：

```rust
class! {
    pub c_base {
        padding: "8px 16px";
        border_radius: "4px";
        font_size: "14px";
    }
    pub c_primary {
        background: "#4f46e5";
        color: "white";
    }
    pub c_primary_button {
        c_base();
        c_primary();
        cursor: "pointer";
        hover {
            background: "#4338ca";
        }
    }
}
```

使用：

```rust
html! {
    button {
        class: c_euv_button_primary_md()
        "Primary Button"
    }
}
```

继承支持参数化类：

```rust
class! {
    pub c_size(size: &str) {
        padding: {size};
    }
    pub c_large_button {
        c_size("12px 24px");
        background: "#4f46e5";
        color: "white";
    }
}
```

> [!tip]
>
> 继承语法 `c_base();` 会将父类的所有样式属性合并到子类中，生成完整的 CSS 字符串。父类的样式放在子类样式之前，子类可以覆盖继承的属性。父类的**伪类/伪元素规则**和**媒体查询规则**也会一并继承，子类可通过重定义同名伪类或媒体查询来覆盖父类的规则。

## 在 HTML 宏中使用

```rust
html! {
    div {
        class: c_card()
        h3 { "Card Title" }
        p { "Card content" }
    }
}
```

> [!tip]
>
> `class!` 宏会生成与类名同名的函数，返回 `Css` 实例，调用时需要加 `()`。

## 配合 vars! 使用

`class!` 宏的样式值支持使用 `var!` 宏引用 CSS 自定义属性，实现主题化样式：

```rust
vars! {
    pub c_theme_light {
        bg-primary: "#f8f9fb";
        text-primary: "#1a1a2e";
    }
    pub c_theme_dark {
        bg-primary: "#1a1a2e";
        text-primary: "#f1f5f9";
    }
}

class! {
    pub c_container {
        background: var!(bg-primary);
        color: var!(text-primary);
        max_width: "800px";
        margin: "0 auto";
    }
}
```

### 在 format! 中拼接 var!

`var!` 宏可以在 `format!` 宏中使用，用于将 CSS 变量引用与其他字符串动态拼接：

```rust
class! {
    pub c_nav {
        width: var!(nav-width);
        border-right: format!("1px solid {}", var!(glass-border));
        scrollbar-color: format!("{} {}", var!(scrollbar-thumb), var!(scrollbar-track));
    }
}
```

```rust
class! {
    pub c_nav_header {
        padding: format!("{} {}", var!(space-xl), var!(space-xl));
        border-bottom: format!("1px solid {}", var!(border-subtle));
        gap: format!("{}", var!(space-md));
    }
}
```

> [!tip]
>
> `class!` 宏会自动展开嵌套在 `format!` 中的 `var!(name)` 调用为 `"var(--name)"` 字符串字面量，因此 `format!("1px solid {}", var!(glass-border))` 在编译期等价于 `format!("1px solid {}", "var(--glass-border)")`。

> [!tip]
>
> `var!` 宏在 `class!` 内部会展开为 CSS `var(--variable-name)` 字符串，支持 kebab-case 标识符或字符串字面量。详细用法参见 [vars! 和 var! 宏](../macros/css-vars.md)。

## 样式属性名

样式属性名使用 snake_case，自动转换为 kebab-case：

```rust
class! {
    pub c_flex_row {
        display: "flex";
        flex_direction: "row";      // → flex-direction
        align_items: "center";      // → align-items
        justify_content: "center";  // → justify-content
        gap: "10px";
    }
}
```

## 伪类/伪元素规则

`class!` 宏支持在类定义中嵌套伪类和伪元素规则块，使用关键字 + 花括号语法：

```rust
class! {
    pub c_button {
        padding: "10px 20px";
        border_radius: "6px";
        cursor: "pointer";
        background: "#4f46e5";
        color: "white";
        hover {
            background: "#4338ca";
            box_shadow: "0 4px 12px rgba(67, 56, 202, 0.4)";
        }
        focus {
            outline: "2px solid #818cf8";
            outline_offset: "2px";
        }
        active {
            background: "#3730a3";
            transform: "scale(0.98)";
        }
        disabled {
            opacity: "0.5";
            cursor: "not-allowed";
        }
        before {
            content: "\"→\"";
            margin_right: "8px";
        }
    }
}
```

### 支持的伪类关键字

| 关键字              | CSS 选择器           |
| ------------------- | -------------------- |
| `hover`             | `:hover`             |
| `focus`             | `:focus`             |
| `focus_within`      | `:focus-within`      |
| `focus_visible`     | `:focus-visible`     |
| `active`            | `:active`            |
| `visited`           | `:visited`           |
| `disabled`          | `:disabled`          |
| `enabled`           | `:enabled`           |
| `checked`           | `:checked`           |
| `readonly`          | `:read-only`         |
| `readwrite`         | `:read-write`        |
| `required`          | `:required`          |
| `optional`          | `:optional`          |
| `valid`             | `:valid`             |
| `invalid`           | `:invalid`           |
| `in_range`          | `:in-range`          |
| `out_of_range`      | `:out-of-range`      |
| `placeholder_shown` | `:placeholder-shown` |
| `first_child`       | `:first-child`       |
| `last_child`        | `:last-child`        |
| `only_child`        | `:only-child`        |
| `first_of_type`     | `:first-of-type`     |
| `last_of_type`      | `:last-of-type`      |
| `only_of_type`      | `:only-of-type`      |
| `root`              | `:root`              |
| `empty`             | `:empty`             |
| `target`            | `:target`            |
| `link`              | `:link`              |
| `any_link`          | `:any-link`          |

### 支持的伪元素关键字

| 关键字           | CSS 选择器         |
| ---------------- | ------------------ |
| `before`         | `::before`         |
| `after`          | `::after`          |
| `first_line`     | `::first-line`     |
| `first_letter`   | `::first-letter`   |
| `selection`      | `::selection`      |
| `placeholder`    | `::placeholder`    |
| `backdrop`       | `::backdrop`       |
| `marker`         | `::marker`         |
| `spelling_error` | `::spelling-error` |
| `grammar_error`  | `::grammar-error`  |

### nth-child 参数化伪类

`nth_child` 和 `nth_last_child` 支持参数化，括号内传入参数：

```rust
class! {
    pub c_stripe_row {
        padding: "8px 12px";
        nth_child(2n+1) {
            background: "rgba(0, 0, 0, 0.05)";
        }
        nth_last_child(1) {
            border_bottom: "none";
        }
    }
}
```

> [!tip]
>
> `nth_child` 和 `nth_last_child` 的下划线会自动转换为 CSS 的 `nth-child` 和 `nth-last-child`。

## 媒体查询规则

`class!` 宏支持 `media(...)` 块，在类定义中定义响应式样式：

```rust
class! {
    pub c_responsive_container {
        max_width: "800px";
        padding: "20px";
        media("(max-width: 768px)") {
            padding: "12px";
            font_size: "14px";
        }
        media("(min-width: 1200px)") {
            max_width: "1200px";
            font_size: "18px";
        }
    }
}
```

### 媒体查询内嵌套伪元素规则

`media(...)` 块内可以嵌套伪元素规则，生成的 CSS 为 `@media (条件) { .class-name::pseudo { ... } }`：

```rust
class! {
    pub c_scrollable {
        overflow_y: "auto";
        media("(max-width: 767px)") {
            font_size: "14px";
            scrollbar {
                width: "0px";
            }
        }
    }
}
```

> [!tip]
>
> 媒体查询条件以字符串形式写在 `media(...)` 的括号内，生成的 CSS 为 `@media (条件) { .class-name { ... } }`。

## @keyframes 关键帧动画

`class!` 块内可使用 `keyframes(名称) { ... }` 定义关键帧动画，关键帧内可用 `from / to / <百分比> { ... }` 形式：

```rust
class! {
    pub c_fade_in {
        keyframes(fade-in) {
            from { opacity: 0; }
            to   { opacity: 1; }
        }
        animation: "fade-in 0.3s ease-out";
    }
}
```

> [!tip]
>
> 宏内部支持的 22 种 at-rule（`media / keyframes / supports / layer / container / property / scope / font-face / charset / import / namespace / page / color-profile / counter-style / font-feature-values / font-palette-values / document / starting-style / view-transition / position-try / custom-media / function`）按相同语法书写。详细规则参考 [`class/fn.rs:544-568`](https://github.com/euv-dev/euv)。

## CSS 注入机制

CSS 类首次使用时，框架会自动将样式注入 DOM 的 `<style id="euv-css-injected">` 元素。注入规则如下：

1. 基础样式：`.class-name { style }`
2. 伪类/伪元素规则：`.class-name:selector { style }`
3. 媒体查询规则：`@media (query) { .class-name { style } }`

同时注入以下全局样式：

| 全局样式                                                       | 说明         |
| -------------------------------------------------------------- | ------------ |
| `html, body, #app { height: 100%; margin: 0; ... }`            | 全局重置     |
| `* { scrollbar-width: thin; }` + `::-webkit-scrollbar { ... }` | 全局滚动条   |
| `@media (prefers-reduced-motion: reduce) { ... }`              | 减弱动效     |
| `@media (hover: none) and (pointer: coarse) { ... }`           | 触屏适配     |
| `@keyframes euv-spin`                                          | 旋转动画     |
| `@keyframes euv-fade-in`                                       | 淡入动画     |
| `@keyframes euv-pulse`                                         | 脉冲动画     |
| `@keyframes euv-progress`                                      | 进度条动画   |
| `@keyframes euv-scale-in-modal`                                | 模态缩放动画 |

> [!tip]
>
> CSS 类首次使用时自动注入样式到 DOM，无需手动引入 CSS 文件。相同类名的样式只会注入一次。样式注入采用追加模式（`appendChild`），不会读取和重写整个 `<style>` 元素的内容，避免性能开销。

## 动态属性名

样式属性名也可以使用花括号 `{expr}` 包裹动态表达式，在运行时计算属性名：

```rust
class! {
    pub c_dynamic_style(prop_key: &str, prop_value: &str) {
        {prop_key}: {prop_value};
        padding: "8px 16px";
    }
}
```

使用：

```rust
html! {
    div {
        class: c_dynamic_style("background", "#4f46e5")
        "Dynamic style"
    }
}
```

> [!warning]
>
> 使用动态属性名时，由于属性名在编译期不可知，该类无法被静态优化，会退化为运行时拼接模式。优先使用静态属性名（snake_case 标识符）以获得更好的性能。

<Bottom />
