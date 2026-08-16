---
synced_from: docs-pages/src/euv/usage-introduction/mount.md@0c74235
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

## mount

将虚拟 DOM 树挂载到指定选择器匹配的元素：

```rust
use euv::{web_sys::*, *};

fn app() -> VirtualNode {
    html! {
        div {
            h1 { "Hello, euv!" }
        }
    }
}

// 挂载到 #app 元素
App::mount("#app", app);

// 挂载到 body 元素
App::mount("body", app);
```

支持的选择器：

| 选择器     | 说明                       |
| ---------- | -------------------------- |
| `"body"`   | 挂载到 body 元素           |
| `"#id"`    | 通过元素 ID 选择           |
| `".class"` | 通过类名选择（首个匹配）   |
| `"tag"`    | 通过标签名选择（首个匹配） |

> [!tip]
>
> 选择器未匹配到任何元素时，`App::mount` 会静默返回，不会 panic。

## mount 函数签名

`App::mount` 接受一个 CSS 选择器字符串和一个渲染函数：

```rust
App::mount::<S, F>(selector: S, render_fn: F)
where
    S: AsRef<str>,
    F: FnOnce() -> VirtualNode,
```

`render_fn` 可以是函数名（如 `app`），也可以是闭包：

```rust
// 传入函数名
App::mount("#app", app);

// 传入闭包
App::mount("#app", || {
    html! { div { "Hello" } }
});
```

> [!tip]
>
> `mount` 会接管渲染函数的所有权并立即调用一次以获取初始虚拟 DOM 树，之后由框架负责响应式更新。如果选择器未匹配到任何元素，`App::mount` 会静默返回。

<Bottom />
