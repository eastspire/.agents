---
synced_from: docs-pages/src/hyperlane/usage-introduction/stream.md@f972247
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

> [!tip]
>
> `hyperlane` 框架中 `Stream` 是对底层 `TCP` 连接的封装，提供了请求数据读取、响应数据发送、连接状态管理等功能。
> `Stream` 作为 `ServerHook` 的 `handle` 方法的参数传入，可在路由和中间件中使用。

## 读取请求数据

### try_get_http_request

> [!tip]
>
> 从 `TCP` 流中读取并解析下一个 `HTTP` 请求。如果连接已关闭，返回 `RequestError::ServerClosedConnection` 错误。支持超时配置。

```rust
let request_result: Result<Request, RequestError> = stream.try_get_http_request().await;
```

### try_get_websocket_request

> [!tip]
>
> 从 `TCP` 流中读取并解析下一个 `WebSocket` 请求。

```rust
let body_result: Result<ResponseBody, RequestError> = stream.try_get_websocket_request().await;
```

## 发送响应数据

### try_send

> [!tip]
>
> 发送数据到客户端，保留 `TCP` 连接。返回 `Result` 类型，可进行错误处理。

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

### send

> [!tip]
>
> 发送数据到客户端，保留 `TCP` 连接。失败时会 panic。

```rust
let data: Vec<u8> = ctx
    .get_mut_response()
    .set_version(HttpVersion::Http1_1)
    .set_status_code(200)
    .set_body("Hello World")
    .build();
stream.send(data).await;
```

### try_send_list

> [!tip]
>
> 批量发送多个响应体数据，适用于 `WebSocket` 帧列表等场景，保留 `TCP` 连接。返回 `Result` 类型。

```rust
let body: &ResponseBody = ctx.get_response().get_body();
let frame_list: Vec<ResponseBody> = WebSocketFrame::create_frame_list(body);
if stream.try_send_list(&frame_list).await.is_err() {
    stream.set_closed(true);
}
```

### send_list

> [!tip]
>
> 批量发送多个响应体数据，适用于 `WebSocket` 帧列表等场景，保留 `TCP` 连接。失败时会 panic。

```rust
let body: &ResponseBody = ctx.get_response().get_body();
let frame_list: Vec<ResponseBody> = WebSocketFrame::create_frame_list(body);
stream.send_list(&frame_list).await;
```

## 刷新缓冲区

### try_flush

> [!tip]
>
> 强制刷新网络缓冲区，确保数据立即发送。返回 `Result` 类型。

```rust
let flush_result: Result<(), ResponseError> = stream.try_flush().await;
```

### flush

> [!tip]
>
> 强制刷新网络缓冲区，确保数据立即发送。失败时会 panic。

```rust
stream.flush().await;
```

## 连接状态管理

### 设置连接关闭

> [!tip]
>
> 此方法会关闭 `TCP` 连接，不会终止当前的生命周期（当前生命周期结束不会进入下一次生命周期循环，需要重新建立 `TCP` 连接），当前生命周期内的代码正常执行，但是不会再发送响应。

```rust
stream.set_closed(true);
```

### is_keep_alive

> [!tip]
>
> 判断连接是否应该保持活跃，需要结合 `keep_alive` 参数和连接关闭状态综合判断。

```rust
let keep_alive: bool = stream.is_keep_alive(ctx.get_request().is_enable_keep_alive());
```

## 属性宏写法

> [!tip]
>
> `hyperlane` 框架提供了属性宏来简化 `Stream` 操作。

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

### send 属性宏

> [!tip]
>
> 自动在函数执行后发送响应，发送失败会 panic。

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

### try_flush 属性宏

```rust
#[response_body("try_flush")]
#[try_send]
#[try_flush]
async fn handle(self, stream: &mut Stream, ctx: &mut Context) -> Status {
    Status::Continue
}
```

### flush 属性宏

> [!warning]
>
> 刷新失败会 panic。

```rust
#[response_body("flush")]
#[send]
#[flush]
async fn handle(self, stream: &mut Stream, ctx: &mut Context) -> Status {
    Status::Continue
}
```

### closed 属性宏

> [!tip]
>
> 可以使用 `#[closed]` 属性宏处理已关闭的流，为已完成的连接提供清理逻辑。

```rust
use hyperlane::*;
use hyperlane_macros::*;

#[route("/closed")]
struct ClosedRoute;

impl ServerHook for ClosedRoute {
    async fn new(_: &mut Stream, _: &mut Context) -> Self {
        Self
    }

    #[closed]
    async fn handle(self, stream: &mut Stream, ctx: &mut Context) -> Status {
        Status::Continue
    }
}
```

### try_get_http_request 属性宏

> [!tip]
>
> 可以使用 `#[try_get_http_request]` 属性宏从 `TCP` 流中读取并解析下一个 `HTTP` 请求。

```rust
use hyperlane::*;
use hyperlane_macros::*;

#[route("/try_get_http_request")]
struct TryGetHttpRequestRoute;

impl ServerHook for TryGetHttpRequestRoute {
    async fn new(_: &mut Stream, _: &mut Context) -> Self {
        Self
    }

    #[try_get_http_request]
    async fn handle(self, stream: &mut Stream, ctx: &mut Context) -> Status {
        Status::Continue
    }
}
```

### try_get_websocket_request 属性宏

> [!tip]
>
> 可以使用 `#[try_get_websocket_request]` 属性宏从 `TCP` 流中读取 `WebSocket` 请求数据，支持传入变量名存储读取结果。

```rust
use hyperlane::*;
use hyperlane_macros::*;

#[route("/ws_upgrade_type")]
struct Websocket;

impl ServerHook for Websocket {
    async fn new(_: &mut Stream, _: &mut Context) -> Self {
        Self
    }

    #[is_ws_upgrade_type]
    #[try_get_websocket_request(body)]
    async fn handle(self, stream: &mut Stream, ctx: &mut Context) -> Status {
        let body_list: Vec<ResponseBody> = WebSocketFrame::create_frame_list(&body);
        stream.send_list(body_list).await;
        Status::Continue
    }
}
```

<Bottom />
