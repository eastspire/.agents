---
synced_from: docs-pages/src/euv/usage-introduction/platform.md@f972247
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

euv 框架基于 `web-sys` 和 `wasm-bindgen` 提供浏览器 API 访问能力。浏览器 API 类型需通过 `use euv::*` 使用，无需单独引入 `web-sys`、`js-sys`、`wasm-bindgen`、`wasm-bindgen-futures` 或 `console_error_panic_hook`。

## euv 重新导出的依赖

`euv` crate 重新导出了 WASM 生态常用的所有 crate，所有内容可通过 `use euv::*` 直接访问：

| 路径                            | 来源 crate                                    | 说明                                                                                                    |
| ------------------------------- | --------------------------------------------- | ------------------------------------------------------------------------------------------------------- |
| `euv::*`                        | 框架核心（`App`、`Signal`、`VirtualNode` 等） | 框架核心类型和宏                                                                                        |
| `euv::wasm_bindgen::prelude::*` | `wasm-bindgen`                                | `#[wasm_bindgen]` 宏、`JsCast` 等                                                                       |
| `euv::wasm_bindgen_futures::*`  | `wasm-bindgen-futures`                        | `spawn_local`、`JsFuture`、`future_to_promise` 等                                                       |
| `euv::js_sys::*`                | `js-sys`                                      | `Promise`、`Function`、`Array`、`JSON`、`Date`、`Math`、`Object` 等 JS 绑定类型                         |
| `euv::web_sys::*`               | `web-sys`                                     | `Window`、`Document`、`HtmlElement`、`Event`、`Storage`、`Location`、`Navigator` 等 DOM/浏览器 API 类型 |
| `euv::console_error_panic_hook` | `console_error_panic_hook`                    | `set_once()` 在浏览器控制台显示 panic 信息，开发时必须调用                                              |

```rust
use euv::*;

// 框架核心
let signal: Signal<i32> = App::use_signal(|| 0);

// wasm-bindgen
use euv::wasm_bindgen::prelude::*;

// wasm-bindgen-futures
spawn_local(async move { /* ... */ });

// js-sys
let promise: Promise = window.fetch_with_str("...");

// web-sys
let document: Document = window().unwrap().document().unwrap();

// console_error_panic_hook
console_error_panic_hook::set_once();
```

## Window 和 Document

```rust
use euv::{web_sys::*, *};

let win: Window = window().expect("no global window exists");
let doc: Document = win.document().expect("should have a document");
```

## 导航与路由

```rust
let win: Window = window().expect("no global window exists");
let location: Location = win.location();

// 获取当前 hash 路由
let hash: String = location.hash().unwrap_or_default();

// 设置 hash 路由（页面导航）
let _ = location.set_hash("#/about");
```

## 本地存储

```rust
let win: Window = window().expect("no global window exists");
let storage: Option<Storage> = win.local_storage().unwrap_or_default();

if let Some(storage) = storage {
    // 写入
    let _ = storage.set_item("key", "value");
    // 读取
    let value: Option<String> = storage.get_item("key").unwrap_or_default();
    // 删除
    let _ = storage.remove_item("key");
}
```

## 异步操作

使用 `spawn_local`（`euv` 重新导出的 `wasm_bindgen_futures::spawn_local`）在 WASM 中执行异步任务：

```rust
spawn_local(async move {
    // 异步操作，如 fetch 请求
    // 完成后通过信号更新 UI
});
```

> [!tip]
>
> 所有浏览器 API 通过 `web-sys` crate 访问，`euv` 在 `Cargo.toml` 中已预启用 60+ 个 `web-sys` 特性（包括 `Window`、`Document`、`Storage`、`Clipboard`、`Navigator`、`FileReader`、`FileList`、`IntersectionObserver`、`console` 等），并通过 `use euv::{web_sys::*, *}` 统一导出。

<Bottom />
