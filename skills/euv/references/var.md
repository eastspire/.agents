---
synced_from: docs-pages/src/euv/macros/var.md@0c74235
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

## 基本用法

`var!` 宏用于引用 `vars!` 定义的 CSS 自定义属性，展开为 CSS `var()` 字符串：

```rust
use euv::*;

// 两种写法等价
var!(bg-primary)        // → "var(--bg-primary)"
var!("bg-primary")      // → "var(--bg-primary)"
```

> [!tip]
>
> 变量名支持 kebab-case 标识符（如 `bg-primary`）或字符串字面量（如 `"bg-primary"`）。kebab-case 标识符会自动转换为 `--bg-primary` 格式。

## 配合 vars! 实现主题切换

`var!` 宏与 `vars!` 配合，通过切换 CSS 变量类实现主题切换：

```rust
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

class! {
    pub c_container {
        background: var!(bg-primary);
        color: var!(text-primary);
        border: format!("1px solid {}", var!(border-color));
        max_width: "800px";
        margin: "0 auto";
    }
}

// 切换主题：将 c_theme_light() 替换为 c_theme_dark() 即可
html! {
    div {
        class: c_theme_light()
        class: c_container()
        "Themed content"
    }
}
```

> [!tip]
>
> `var!` 宏在 `class!`、内联样式和 `format!` 宏中都可以使用。它仅生成 CSS `var(--variable-name)` 字符串，实际变量值由 `vars!` 生成的 `Css` 在注入 DOM 时定义。以数字开头的变量名必须使用字符串字面量形式（如 `var!("font-2xl")`）。更多 `vars!` 用法参见 [vars! 和 var! 宏](../macros/css-vars.md)。

<Bottom />
