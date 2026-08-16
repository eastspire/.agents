---
synced_from: docs-pages/src/hyperlane/usage-introduction/send.md@0c74235
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

> [!tip]
>
> `hyperlane` 框架提供了多种响应发送方法，支持完整 HTTP 响应发送、仅响应体发送，以及连接管理。
>
> - `stream.try_send` 和 `stream.send`: 发送完整 HTTP 响应并保留连接。
> - `stream.try_send_list` 和 `stream.send_list`: 批量发送响应体。
> - `stream.try_flush` 和 `stream.flush`: 刷新网络缓冲区。

## 发送完整 HTTP 响应

### try_send 方法

> [!tip]
>
> 发送完整的 HTTP 响应，发送后 TCP 连接保留。返回 Result 类型，可以进行错误处理。

```rust
let data: Vec<u8> = ctx
    .get_mut_response()
    .set_version(HttpVersion::Http1_1)
    .set_status_code(200)
    .set_header(SERVER, HYPERLANE)
    .set_header(CONTENT_TYPE, TEXT_PLAIN)
    .set_body("Hello World")
    .build();
if stream.try_send(data).await.is_err() {
    stream.set_closed(true);
}
```

### send 方法

> [!tip]
>
> 发送完整的 HTTP 响应，发送后 TCP 连接保留。失败时会 panic。

```rust
let data: Vec<u8> = ctx
    .get_mut_response()
    .set_version(HttpVersion::Http1_1)
    .set_status_code(200)
    .set_body("Hello World")
    .build();
stream.send(data).await;
```

## 批量发送响应

### try_send_list 方法

> [!tip]
>
> 批量发送多个响应体数据，适用于 WebSocket 帧列表等场景，发送后 TCP 连接保留。返回 Result 类型，可以进行错误处理。

```rust
let body: &ResponseBody = ctx.get_response().get_body();
let frame_list: Vec<ResponseBody> = WebSocketFrame::create_frame_list(body);
if stream.try_send_list(&frame_list).await.is_err() {
    stream.set_closed(true);
}
```

### send_list 方法

> [!tip]
>
> 批量发送多个响应体数据，适用于 WebSocket 帧列表等场景，发送后 TCP 连接保留。失败时会 panic。

```rust
let body: &ResponseBody = ctx.get_response().get_body();
let frame_list: Vec<ResponseBody> = WebSocketFrame::create_frame_list(body);
stream.send_list(&frame_list).await;
```

## 刷新缓冲区

### try_flush 方法

> [!tip]
>
> 强制刷新网络缓冲区，确保数据立即发送。返回 Result 类型，可以进行错误处理。

```rust
let flush_result: Result<(), ResponseError> = stream.try_flush().await;
```

### flush 方法

> [!tip]
>
> 强制刷新网络缓冲区，确保数据立即发送。失败时会 panic。

```rust
stream.flush().await;
```

## 属性宏写法

> [!tip]
>
> `hyperlane` 框架提供了属性宏来简化响应发送操作，通过 `#[try_send]` 和 `#[send]` 属性宏可以自动在函数执行后发送响应。

### try_send 属性宏

> [!tip]
>
> 自动在函数执行后发送响应。如果不传参数，默认从 `ctx` 构建响应并发送。

```rust
use hyperlane::*;
use hyperlane_macros::*;

#[route("/try_send")]
struct TrySendRoute;

impl ServerHook for TrySendRoute {
    async fn new(_: &mut Stream, _: &mut Context) -> Self {
        Self
    }

    #[response_body("Hello World")]
    #[try_send]
    async fn handle(self, stream: &mut Stream, ctx: &mut Context) -> Status {
        Status::Continue
    }
}
```

#### try_send 属性宏（带数据表达式）

> [!tip]
>
> 可以传入数据表达式作为参数，发送指定的数据。

```rust
#[try_send(ctx.get_mut_response().build())]
async fn handle(self, stream: &mut Stream, ctx: &mut Context) -> Status {
    Status::Continue
}
```

### send 属性宏

> [!tip]
>
> 自动在函数执行后发送响应，发送失败会 panic。如果不传参数，默认从 `ctx` 构建响应并发送。

```rust
use hyperlane::*;
use hyperlane_macros::*;

#[route("/send")]
struct SendRoute;

impl ServerHook for SendRoute {
    async fn new(_: &mut Stream, _: &mut Context) -> Self {
        Self
    }

    #[response_body("Hello World")]
    #[send]
    async fn handle(self, stream: &mut Stream, ctx: &mut Context) -> Status {
        Status::Continue
    }
}
```

#### send 属性宏（带数据表达式）

> [!tip]
>
> 可以传入数据表达式作为参数，发送指定的数据。

```rust
#[send(ctx.get_mut_response().build())]
async fn handle(self, stream: &mut Stream, ctx: &mut Context) -> Status {
    Status::Continue
}
```

### 使用 prologue_macros 和 epilogue_macros 组合

> [!tip]
>
> `prologue_macros` 在函数体之前注入代码，`epilogue_macros` 在函数体之后注入代码。
> 宏列表中的顺序：`prologue_macros` 为头部插入顺序（第一个宏是最外层），`epilogue_macros` 为尾部插入顺序（最后一个宏是最外层）。

```rust
use hyperlane::*;
use hyperlane_macros::*;

#[route("/combined")]
struct CombinedRoute;

impl ServerHook for CombinedRoute {
    async fn new(_: &mut Stream, _: &mut Context) -> Self {
        Self
    }

    #[prologue_macros(is_post_method, response_body("combined"), send)]
    async fn handle(self, stream: &mut Stream, ctx: &mut Context) -> Status {
        Status::Continue
    }
}
```

### try_flush 属性宏

> [!tip]
>
> 尝试刷新网络缓冲区，确保数据立即发送。返回 Result 类型，可以进行错误处理。

```rust
use hyperlane::*;
use hyperlane_macros::*;

#[route("/try_flush")]
struct TryFlushRoute;

impl ServerHook for TryFlushRoute {
    async fn new(_: &mut Stream, _: &mut Context) -> Self {
        Self
    }

    #[response_body("try_flush")]
    #[try_send]
    #[try_flush]
    async fn handle(self, stream: &mut Stream, ctx: &mut Context) -> Status {
        Status::Continue
    }
}
```

### flush 属性宏

> [!tip]
>
> 刷新网络缓冲区，确保数据立即发送。失败时会 panic。

```rust
use hyperlane::*;
use hyperlane_macros::*;

#[route("/flush")]
struct FlushRoute;

impl ServerHook for FlushRoute {
    async fn new(_: &mut Stream, _: &mut Context) -> Self {
        Self
    }

    #[response_body("flush")]
    #[send]
    #[flush]
    async fn handle(self, stream: &mut Stream, ctx: &mut Context) -> Status {
        Status::Continue
    }
}
```

<Bottom />
