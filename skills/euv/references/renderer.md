---
synced_from: docs-pages/src/euv/usage-introduction/renderer.md@0c74235
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

## 渲染虚拟 DOM

`Renderer` 是框架内部的渲染器类型，负责将虚拟 DOM 渲染到真实 DOM。通常不需要手动创建，使用 `mount` 即可自动管理渲染器：

```rust
use euv::{web_sys::*, *};

// App::mount 内部自动创建 Renderer 并渲染
App::mount("#app", app);
```

> [!tip]
>
> `Renderer` 是框架内部类型，无法在 euv crate 外部直接使用。使用 `App::mount` 函数即可自动管理渲染器的创建和渲染。

## 渲染模式

框架根据场景自动选择两种渲染模式：

- **增量渲染** — 对比新旧虚拟 DOM 树并仅更新变化的部分。标签相同则仅修补属性和子节点，标签不同则替换整个 DOM 节点，文本内容相同则跳过更新。增量渲染采用精确脏标记，只有依赖变化信号的动态节点才会重新渲染
- **完全替换渲染** — 跳过 Diff，直接替换所有子节点。`match` 分支切换（如路由变化）时自动使用此模式

> [!tip]
>
> 这两种渲染模式由框架内部自动选择，用户无需手动调用。

## Keyed Diffing

渲染器支持基于 `key` 的列表 Diff 算法，当所有子节点都带有 `key` 属性时自动启用：

```rust
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

Keyed Diffing 的优势：

- 列表重排序时，通过 `key` 映射复用已有 DOM 节点，避免不必要的删除和重建
- 插入/删除元素时，仅操作受影响的节点

> [!tip]
>
> 当所有子节点都带有 `key` 属性时，框架自动使用 Keyed Diffing。如果部分或全部子节点没有 `key`，则回退到位置 Diffing（按索引逐一比较）。

## 布尔属性

对于 `checked`、`disabled`、`selected`、`readonly` 等布尔属性，框架使用 DOM 属性（property）而非 HTML 属性（attribute）：

```rust
html! {
    input {
        r#type: "checkbox"
        checked: agree_signal
    }
    input {
        r#type: "text"
        disabled: disabled_signal
    }
}
```

> [!warning]
>
> 布尔属性必须通过 `Signal<bool>` 传入，不能直接传字符串 `"true"` / `"false"`。

## 渲染优化

框架在动态节点 重新渲染时会比较新旧虚拟 DOM 树，如果渲染结果完全相同，则跳过 DOM 修补操作，避免不必要的 DOM 操作。`match` 分支切换时始终执行完全替换，不受此优化影响。

> [!tip]
>
> 这一优化对频繁信号更新但 UI 实际未变的场景（如定时器信号更新但渲染结果不变）特别有效。

## 事件委托

渲染器对冒泡事件使用全局事件委托：同一事件名只会在 `window` 上注册一次 `addEventListener`，各元素的事件处理器通过全局注册表（`HandlerRegistry`）按 `(euv_id, event_name)` 键查找和调用。对于非冒泡事件（如 `load`、`error`、`loadstart`），则在对应 DOM 元素上直接绑定监听器。

> [!tip]
>
> 事件委托由框架自动管理，无需手动干预。全局委托减少了 DOM 事件监听器数量，提升性能。

## DOM 清理

框架在移除 DOM 节点时会自动递归清理关联的框架资源（事件处理器、动态节点监听器、信号监听器等），无需手动干预。

> [!tip]
>
> DOM 清理由框架自动管理，无需手动干预。

<Bottom />
