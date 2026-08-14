---
synced_from: docs-pages/src/euv/usage-introduction/event.md@f972247
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

## 内联闭包事件

在 `html!` 宏中直接使用闭包处理事件，闭包签名为 `FnMut(Event)`，其中 `Event` 是 `web_sys::Event`：

```rust
html! {
    button {
        onclick: move |event: Event| {
            // 处理点击
        }
        "Click me"
    }
}
```

## NativeEventHandler 事件

通过 `NativeEventHandler::create` 创建事件处理器，适合在组件间传递或复用：

```rust
pub fn counter_on_increment(counter: Signal<i32>) -> NativeEventHandler {
    NativeEventHandler::create("click", move |_event: Event| {
        let current: i32 = counter.get();
        counter.set(current + 1);
    })
}

html! {
    button {
        onclick: counter_on_increment(count)
        "Increment"
    }
}
```

> [!tip]
>
> `NativeEventHandler::create` 接受两个参数：事件名称（`&'static str`）和事件处理闭包。闭包签名为 `FnMut(Event)`。对于自定义事件，直接传入事件名字符串即可（如 `"custom-event"`）。

### NativeEventHandler 结构

`NativeEventHandler` 内部包含以下字段：

|              | 字段           | 类型                                                                                                      | 说明 |
| ------------ | -------------- | --------------------------------------------------------------------------------------------------------- | ---- |
| `event_name` | `&'static str` | 事件名称（如 `"click"`、`"input"`），必须是静态生命周期的字符串                                           |
| `callback`   | 内部共享闭包   | `Rc<UnsafeCell<Box<dyn FnMut(Event)>>>`（实现细节，`pub(crate)` 字段；通过 `create` 构造、`handle` 调用） |

> [!tip]
>
> `NativeEventHandler` 实现了 `Clone`，克隆时共享同一个回调闭包。使用 `Rc<UnsafeCell<>>` 而非 `Rc<RefCell<>>` 是因为在单线程 WASM 环境中无需运行时借用检查，可以减少开销。

### NativeEventHandler 方法

| 方法                                               | 说明                                                             |
| -------------------------------------------------- | ---------------------------------------------------------------- |
| `NativeEventHandler::create(event_name, callback)` | 创建事件处理器，接受 `&'static str` 事件名和 `FnMut(Event)` 闭包 |
| `handler.handle(event)`                            | 手动调用事件处理器，传入 `Event` 参数                            |

## 输入事件

通过 `event.dyn_ref::<HtmlInputElement>()` 获取具体的 DOM 元素，再读取其值：

```rust
html! {
    input {
        r#type: "text"
        placeholder: "Enter text"
        oninput: move |event: Event| {
            if let Some(target) = event.target()
                && let Ok(input) = target.clone().dyn_into::<HtmlInputElement>() {
                    name_signal.set(input.value());
                }
        }
    }
}
```

## 表单变更事件

```rust
html! {
    input {
        r#type: "checkbox"
        checked: agree_signal
        onchange: move |event: Event| {
            if let Some(target) = event.target()
                && let Ok(input) = target.clone().dyn_into::<HtmlInputElement>() {
                    agree_signal.set(input.checked());
                }
        }
    }
}
```

## 支持的事件名称

在 `html!` 宏中使用 `on` 前缀小写形式（如 `onclick`、`oninput`），框架自动映射到对应的事件类型。使用 `NativeEventHandler::create` 时，传入不含 `on` 前缀的事件名字符串（如 `"click"`、`"input"`）。

| 类别   | 事件名称                                                                                                                                         |
| ------ | ------------------------------------------------------------------------------------------------------------------------------------------------ |
| 鼠标   | `onclick`, `ondblclick`, `onmousedown`, `onmouseup`, `onmousemove`, `onmouseenter`, `onmouseleave`, `onmouseover`, `onmouseout`, `oncontextmenu` |
| 输入   | `oninput`                                                                                                                                        |
| 键盘   | `onkeydown`, `onkeyup`, `onkeypress`                                                                                                             |
| 焦点   | `onfocus`, `onblur`, `onfocusin`, `onfocusout`                                                                                                   |
| 表单   | `onsubmit`, `onchange`                                                                                                                           |
| 拖拽   | `ondrag`, `ondragstart`, `ondragend`, `ondragover`, `ondragenter`, `ondragleave`, `ondrop`                                                       |
| 触摸   | `ontouchstart`, `ontouchend`, `ontouchmove`, `ontouchcancel`                                                                                     |
| 滚轮   | `onwheel`                                                                                                                                        |
| 剪贴板 | `oncopy`, `oncut`, `onpaste`                                                                                                                     |
| 媒体   | `onplay`, `onpause`, `onended`, `onloadeddata`, `oncanplay`, `onvolumechange`, `ontimeupdate`                                                    |
| 路由   | `onhashchange`, `onpopstate`                                                                                                                     |
| 窗口   | `onresize`, `onscroll`, `onload`, `onunload`, `onbeforeunload`, `onerror`, `ononline`, `onoffline`, `onvisibilitychange`                         |
| 动画   | `onanimationstart`, `onanimationend`, `onanimationiteration`                                                                                     |
| 过渡   | `ontransitionstart`, `ontransitionend`, `ontransitionrun`                                                                                        |
| 自定义 | 任意 `on` 前缀 + 事件名，如 `onmy-event`                                                                                                         |

> [!tip]
>
> 框架对常用事件使用事件委托，减少 DOM 事件监听器数量。不在委托列表中的事件会自动在对应元素上单独绑定。

## 事件数据

事件回调接收 `web_sys::Event` 类型参数，通过 `dyn_ref::<T>()` 下转型为具体的事件类型来获取数据：

```rust
move |event: Event| {
    if let Some(mouse_event) = event.dyn_ref::<MouseEvent>() {
        let x: i32 = mouse_event.client_x();
        let y: i32 = mouse_event.client_y();
        let button: i16 = mouse_event.button();
        let ctrl_key: bool = mouse_event.ctrl_key();
        let shift_key: bool = mouse_event.shift_key();
        let alt_key: bool = mouse_event.alt_key();
        let meta_key: bool = mouse_event.meta_key();
    }
    if let Some(keyboard_event) = event.dyn_ref::<KeyboardEvent>() {
        let key: String = keyboard_event.key();
        let code: String = keyboard_event.code();
        let repeat: bool = keyboard_event.repeat();
    }
    if let Some(target) = event.target()
        && let Ok(input) = target.clone().dyn_into::<HtmlInputElement>() {
            let value: String = input.value();
            let checked: bool = input.checked();
        }
    if let Some(drag_event) = event.dyn_ref::<DragEvent>() {
        let client_x: i32 = drag_event.client_x();
        let client_y: i32 = drag_event.client_y();
    }
    if let Some(touch_event) = event.dyn_ref::<TouchEvent>() {
        let touches: TouchList = touch_event.touches();
        let count: u32 = touches.length();
    }
    if let Some(wheel_event) = event.dyn_ref::<WheelEvent>() {
        let delta_x: f64 = wheel_event.delta_x();
        let delta_y: f64 = wheel_event.delta_y();
        let delta_mode: u32 = wheel_event.delta_mode();
    }
    if let Some(clipboard_event) = event.dyn_ref::<ClipboardEvent>() {
        let data: Option<String> = clipboard_event
            .clipboard_data()
            .and_then(|cd| cd.get_data("text").ok());
    }
}
```

> [!tip]
>
> 事件名在 HTML 宏中使用 `on` 前缀小写形式，如 `onclick`、`oninput`，框架自动映射到对应的事件类型。事件回调接收的是 `web_sys::Event`，需通过 `event.dyn_ref::<T>()` 下转型为具体事件类型（如 `MouseEvent`、`KeyboardEvent`），或通过 `event.target()` 获取 DOM 元素后 `dyn_into::<HtmlInputElement>()` 等方式读取值。`dyn_ref` 和 `dyn_into` 来自 `wasm_bindgen::JsCast` trait，已在 `euv` 中重新导出。

## 常用事件处理器

`euv-ui` crate 通过 `UseEuvInput` 零尺寸结构体提供常用的事件处理器工厂函数：

```rust
use euv_ui::UseEuvInput;

// 切换布尔信号
pub fn use_toggle(signal: Signal<bool>) -> Option<Rc<dyn Fn(Event)>>;

// 输入值绑定到信号（自动识别 input/textarea/select）
pub fn on_input_value(signal: Signal<String>) -> Option<Rc<dyn Fn(Event)>>;

// 变更值绑定到信号（自动识别 input/select/textarea）
pub fn on_change_value(signal: Signal<String>) -> Option<Rc<dyn Fn(Event)>>;

// Checkbox 变更绑定到 bool 信号
pub fn on_change_checked(signal: Signal<bool>) -> Option<Rc<dyn Fn(Event)>>;

// 移动端聚焦时滚动到可见区域（处理虚拟键盘遮挡）
pub fn on_focus_scroll_into_view() -> Option<Rc<dyn Fn(Event)>>;

// 移动端失焦时恢复页面高度
pub fn on_blur_restore_height() -> Option<Rc<dyn Fn(Event)>>;
```

使用：

```rust
use euv_ui::*;

let is_open: Signal<bool> = App::use_signal(|| false);
let text: Signal<String> = App::use_signal(String::new);

html! {
    euv_button {
        variant: EuvButtonVariant::Primary
        label: "Toggle"
        onclick: UseEuvInput::use_toggle(is_open)
    }
    input {
        r#type: "text"
        value: text
        oninput: UseEuvInput::on_input_value(text)
        onfocus: UseEuvInput::on_focus_scroll_into_view()
        onblur: UseEuvInput::on_blur_restore_height()
    }
}
```

> [!tip]
>
> 上述方法返回 `Option<Rc<dyn Fn(Event)>>`，可直接用于 `html!` 事件属性和组件 Props 的回调字段。`on_input_value` 和 `on_change_value` 自动识别 `HtmlInputElement`、`HtmlTextAreaElement`、`HtmlSelectElement` 三种表单元素，无需为不同元素类型编写不同的处理器。`on_focus_scroll_into_view` / `on_blur_restore_height` 自动处理移动端虚拟键盘遮挡问题。`euv_field` / `euv_input` 组件内部已自动集成这两个聚焦/失焦处理器。完整 API 参见 [输入与布局 Hook](../ui/hooks.md)。

<Bottom />
