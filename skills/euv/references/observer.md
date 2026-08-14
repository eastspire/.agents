---
synced_from: docs-pages/src/euv/usage-introduction/observer.md@f972247
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

## 概述

在 euv 中可以通过 `web_sys::IntersectionObserver` 监听元素是否进入或离开视口，适用于懒加载、无限滚动、曝光统计等场景。

## 基本用法

创建 `IntersectionObserver`，观察指定元素，在回调中处理交叉事件：

```rust
use euv::{web_sys::*, *};
use wasm_bindgen::prelude::*;
use js_sys::*;

fn use_intersection_observer(selector: &str) {
    let selector_owned: String = selector.to_string();
    // IntersectionObserver::new 接收 &::js_sys::Function，所以需要
    // 先 Closure::wrap 包闭包，再 as_ref().unchecked_ref::<Function>()
    let callback: Closure<dyn FnMut(Array)> = Closure::new(move |entries: Array| {
        for i in 0..entries.length() {
            // js_sys::Array::get 返回 JsValue，直接 unchecked_into 下转
            let entry: IntersectionObserverEntry = entries.get(i).unchecked_into();
            let ratio = entry.intersection_ratio();
            let target = entry.target();
            let id = target.id();
            web_sys::console::log_5(
                &"Element".into(),
                &JsValue::from(id),
                &"intersection ratio:".into(),
                &JsValue::from(ratio),
                &JsValue::from(if ratio > 0.0 { "visible" } else { "hidden" }),
            );
        }
    });
    let observer = IntersectionObserver::new(callback.as_ref().unchecked_ref())
        .expect("should create observer");
    // 闭包交给 observer 后需要 forget 防止被释放
    callback.forget();

    let document = window().expect("should have a window").document().expect("should have a document");
    if let Some(container) = document.query_selector(&selector_owned).ok().flatten() {
        observer.observe(&container);
    }
}
```

## 在组件中使用

```rust
#[component]
fn observer_demo(_node: VirtualNode<()>) -> VirtualNode {
    // 组件挂载时注册观察器
    let _: Signal<bool> = App::use_signal(|| {
        use_intersection_observer("[data-observe]");
        true
    });

    html! {
        div {
            ul {
                for index in 0..100 {
                    li {
                        key: index.to_string()
                        data-observe: "true"
                        format!("Item {}", index + 1)
                    }
                }
            }
        }
    }
}
```

## 带阈值的观察器

```rust
let options = IntersectionObserverInit::new();
options.set_threshold_f64(0.5); // 50% 可见时触发（更简洁的 f64 setter）

let callback: Closure<dyn FnMut(Array)> = Closure::new(move |entries: Array| {
    // 处理交叉事件
});
let observer = IntersectionObserver::new_with_options(
    callback.as_ref().unchecked_ref(),
    &options,
)
.expect("should create observer");
callback.forget();
```

> [!tip]
>
> `IntersectionObserver` 适用于懒加载图片（元素进入视口时加载）和无限滚动（元素接近底部时加载更多）。观察器应在组件挂载时创建一次，避免在渲染函数中重复创建。

<Bottom />
