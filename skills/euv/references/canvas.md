---
synced_from: docs-pages/src/euv/usage-introduction/canvas.md@0c74235
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

## 概述

在 euv 中可以直接使用 `<canvas>` 元素，通过 `web_sys::CanvasRenderingContext2d` 进行 2D 绘图。Canvas 的事件处理与普通 HTML 元素一致，支持鼠标和触摸事件。

## 基本 Canvas 元素

```rust
use euv::{web_sys::*, *};

html! {
    canvas {
        id: "my-canvas"
        width: "800"
        height: "600"
        style: {border: "1px solid #ccc";}
        onmousedown: on_canvas_mouse_down
        onmousemove: on_canvas_mouse_move
        onmouseup: on_canvas_mouse_up
    }
}
```

## 获取 Canvas 上下文

Canvas 需要在组件挂载且首次渲染完成后才能获取上下文。通常在事件回调中初始化：

```rust
fn get_canvas_context() -> Option<CanvasRenderingContext2d> {
    let document = web_sys::document()?;
    let canvas = document.get_element_by_id("my-canvas")?;
    canvas.dyn_into::<HtmlCanvasElement>().ok().and_then(|c| {
        c.get_context("2d").ok().flatten().and_then(|ctx| ctx.dyn_into().ok())
    })
}
```

## 鼠标和触摸事件

Canvas 绘制通常需要同时处理鼠标和触摸事件以获得跨设备支持：

```rust
let is_drawing: Signal<bool> = App::use_signal(|| false);

let on_mouse_down = move |event: Event| {
    is_drawing.set(true);
    let offset_x: f64 = event.offset_x() as f64;
    let offset_y: f64 = event.offset_y() as f64;
    if let Some(ctx) = get_canvas_context() {
        ctx.begin_path();
        ctx.move_to(offset_x, offset_y);
    }
};

let on_mouse_move = move |event: Event| {
    if !is_drawing.get() { return; }
    let offset_x: f64 = event.offset_x() as f64;
    let offset_y: f64 = event.offset_y() as f64;
    if let Some(ctx) = get_canvas_context() {
        ctx.line_to(offset_x, offset_y);
        ctx.stroke();
    }
};

let on_mouse_up = move |_: Event| {
    is_drawing.set(false);
};
```

### 触摸事件支持

触摸事件需要阻止默认行为防止滚动，并通过 `changed_touches()` 获取触点位置：

```rust
use wasm_bindgen::JsCast;

let on_touch_start = move |event: Event| {
    event.prevent_default();
    is_drawing.set(true);
    if let Some(touch) = event.changed_touches() {
        let touch = touch.item(0).expect("should have a touch");
        let x = touch.client_x() as f64;
        let y = touch.client_y() as f64;
        // 开始绘制
    }
};
```

## 全屏 Canvas

对于绘图应用，Canvas 通常需要全屏模式以提供充足的绘画空间。使用信号控制全屏容器的显示隐藏：

```rust
let fullscreen: Signal<bool> = App::use_signal(|| false);

html! {
    div {
        euv_button {
            variant: EuvButtonVariant::Primary
            label: if { fullscreen.get() } { "Exit" } else { "Draw" }
            onclick: move |_: Event| { fullscreen.set(!fullscreen.get()); }
        }
        if { fullscreen.get() } {
            div {
                class: c_canvas_container_fullscreen()
                canvas {
                    id: "drawing-canvas"
                }
            }
        }
    }
}
```

> [!tip]
>
> Canvas 上下文仅在 DOM 挂载后有效，不要在组件函数体内直接调用 `getContext`。推荐在事件回调或 `use_interval` 中获取。触摸事件需调用 `event.prevent_default()` 阻止浏览器默认的滚动/缩放行为。

> [!warning]
>
> Canvas 由浏览器直接渲染，不受 euv VDOM diff 管理。Canvas 内容的更新需要通过 Canvas API 手动绘制，而非通过信号绑定自动完成。

<Bottom />
