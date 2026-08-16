---
synced_from: docs-pages/src/euv/usage-introduction/file.md@0c74235
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

在 euv 中通过原生 `<input type="file">` 元素实现文件选择，配合信号管理文件状态。

## 隐藏文件输入 + 按钮触发

典型的文件上传模式：隐藏真实 input，通过按钮触发选择对话框：

```rust
use euv::{web_sys::*, *};

const FILE_UPLOAD_ID: &str = "file-upload";

let file_names: Signal<Vec<String>> = App::use_signal(|| Vec::new());

let on_select = move |_: Event| {
    let document = web_sys::document().expect("should have a document");
    if let Some(input) = document.get_element_by_id(FILE_UPLOAD_ID) {
        let input: web_sys::HtmlInputElement = input.dyn_into().unwrap();
        input.click();
    }
};

let on_change = move |event: Event| {
    let target: web_sys::HtmlInputElement = event
        .target()
        .expect("should have target")
        .dyn_into()
        .expect("should be input");
    let files = target.files();
    let names: Vec<String> = files
        .map(|file_list| {
            (0..file_list.length())
                .filter_map(|i| file_list.item(i))
                .map(|f| f.name())
                .collect()
        })
        .unwrap_or_default();
    file_names.set(names);
};

html! {
    div {
        input {
            id: FILE_UPLOAD_ID
            r#type: "file"
            style: {display: "none";}
            onchange: on_change
        }
        euv_button {
            variant: EuvButtonVariant::Primary
            label: "Browse"
            onclick: on_select
            "Browse"
        }
        if { !file_names.get().is_empty() } {
            ul {
                for name in { file_names.get() } {
                    li { name }
                }
            }
        }
    }
}
```

## 多文件上传

添加 `multiple: true` 属性允许选择多个文件：

```rust
input {
    id: "file-input-multi"
    r#type: "file"
    multiple: true
    onchange: on_change
}
```

## Accept 过滤

通过 `accept` 属性限制可选文件类型：

```rust
input {
    id: "file-input-filtered"
    r#type: "file"
    accept: ".pdf,.doc,.docx"
    // 或 MIME 类型: "image/png,image/jpeg"
    // 或类别: "image/*"
    onchange: on_change
}
```

## 读取文件内容

选择文件后可以通过 `FileReader` 读取文件内容：

```rust
use wasm_bindgen::prelude::*;
use wasm_bindgen_futures::spawn_local;

let on_change = move |event: Event| {
    let target: web_sys::HtmlInputElement = event
        .target().unwrap().dyn_into().unwrap();
    let files = target.files().unwrap();
    if let Some(file) = files.item(0) {
        let reader = web_sys::FileReader::new().unwrap();
        let reader_ref = reader.clone();
        let on_load = Closure::<dyn FnMut(_)>::new(move |_: Event| {
            let result = reader_ref.result().unwrap();
            // result 为 JsValue，可转换为 String 或 ArrayBuffer
            let text = result.as_string().unwrap_or_default();
            web_sys::console::log_1(&format!("File content: {}", text).into());
        });
        reader.set_onload(Some(on_load.as_ref().unchecked_ref()));
        on_load.forget();
        reader.read_as_text(&file).unwrap();
    }
};
```

> [!tip]
>
> 文件输入使用原生 `<input type="file">`，推荐将其隐藏（`display: none`）并通过按钮触发 `click()`。文件选择由浏览器安全机制控制，只能由用户手势触发。

<Bottom />
