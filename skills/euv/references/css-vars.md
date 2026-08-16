---
synced_from: docs-pages/src/euv/macros/css-vars.md@0c74235
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

## vars! 宏

`vars!` 宏用于定义 CSS 自定义属性（CSS Variables），生成 `Css` 函数。调用时自动将自定义属性注入 DOM。

变量名自动添加 `--` 前缀，支持 kebab-case 标识符或字符串字面量。

### 定义 CSS 变量

```rust
use euv::*;

vars! {
    pub c_theme_light {
        bg-primary: "#f8f9fb";
        text-primary: "#1a1a2e";
        border-color: "#e2e8f0";
    }
    pub c_theme_dark {
        bg-primary: "#1a1a2e";
        text-primary: "#f1f5f9";
        border-color: "#334155";
    }
}
```

### 可见性修饰

与 `class!` 宏一致：

|              |              | 说明 |
| ------------ | ------------ | ---- |
| `pub`        | 公开         |
| `pub(crate)` | crate 内可见 |
| `pub(super)` | 父模块内可见 |
| 无修饰       | 私有         |

### 参数化 CSS 变量

`vars!` 支持定义带参数的 CSS 变量块，值可以动态计算：

```rust
vars! {
    pub c_theme_dynamic(bg: &str, text: &str) {
        bg-primary: {bg};
        text-primary: {text};
    }
}
```

使用：

```rust
html! {
    div {
        class: c_theme_dynamic("#f8f9fb", "#1a1a2e")
        "Dynamic themed content"
    }
}
```

> [!tip]
>
> 参数化 CSS 变量块的样式值使用花括号 `{param}` 包裹动态表达式，静态值使用字符串字面量。框架根据参数值生成唯一类名，避免样式冲突。

### 在 HTML 宏中使用

```rust
html! {
    div {
        class: c_theme_light()
        "Themed content"
    }
}
```

> [!tip]
>
> `vars!` 宏生成的函数与 `class!` 宏一样返回 `Css` 实例（非参数化返回 `&'static Css`），因此可以直接用于 `class:` 属性。

<Bottom />
