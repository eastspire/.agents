---
synced_from: docs-pages/src/hyperlane-macros/send-flush.md@0c74235
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
> `hyperlane-macros` 提供了发送和刷新网络数据的属性宏，用于在路由处理函数执行完毕后自动发送响应或刷新缓冲区。

## 发送宏

### try_send（安全方式）

自动在函数执行后发送响应，返回 `Result`，可由开发者自行处理错误。不传参数时默认从 `ctx` 构建响应并发送：

```rust
use hyperlane::*;
use hyperlane_macros::*;

#[route("/try-send")]
struct TrySendRoute;

impl ServerHook for TrySendRoute {
    async fn new(_: &mut Stream, _: &mut Context) -> Self {
        Self
    }

    #[response_body("Hello")]
    #[try_send]
    async fn handle(self, stream: &mut Stream, ctx: &mut Context) -> Status {
        Status::Continue
    }
}
```

带数据表达式参数：

```rust
#[try_send(ctx.get_mut_response().build())]
async fn handle(self, stream: &mut Stream, ctx: &mut Context) -> Status {
    Status::Continue
}
```

### send（失败时 panic）

与 `try_send` 功能相同，但发送失败时会 **panic**：

```rust
#[response_body("Hello")]
#[send]
async fn handle(self, stream: &mut Stream, ctx: &mut Context) -> Status {
    Status::Continue
}
```

带数据表达式参数：

```rust
#[send(ctx.get_mut_response().build())]
async fn handle(self, stream: &mut Stream, ctx: &mut Context) -> Status {
    Status::Continue
}
```

## 刷新宏

### try_flush（安全方式）

尝试刷新网络缓冲区，确保数据立即发送，返回 `Result`：

```rust
use hyperlane::*;
use hyperlane_macros::*;

#[route("/try-flush")]
struct TryFlushRoute;

impl ServerHook for TryFlushRoute {
    async fn new(_: &mut Stream, _: &mut Context) -> Self {
        Self
    }

    #[response_body("flush test")]
    #[try_send]
    #[try_flush]
    async fn handle(self, stream: &mut Stream, ctx: &mut Context) -> Status {
        Status::Continue
    }
}
```

### flush（失败时 panic）

强制刷新网络缓冲区，失败时 panic：

```rust
#[response_body("flush")]
#[send]
#[flush]
async fn handle(self, stream: &mut Stream, ctx: &mut Context) -> Status {
    Status::Continue
}
```

## 连接关闭相关宏

### closed

处理已关闭的流，为已完成的连接提供清理逻辑：

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
        // 连接已关闭，执行清理逻辑
        Status::Continue
    }
}
```

### try_get_http_request

从 TCP 流中读取并解析下一个 HTTP 请求。仅在成功读取数据后执行函数体：

```rust
use hyperlane::*;
use hyperlane_macros::*;

#[route("/next-request")]
struct NextRequestRoute;

impl ServerHook for NextRequestRoute {
    async fn new(_: &mut Stream, _: &mut Context) -> Self {
        Self
    }

    #[try_get_http_request]
    async fn handle(self, stream: &mut Stream, ctx: &mut Context) -> Status {
        Status::Continue
    }
}
```

可选地传入变量名存储读取的请求数据：

```rust
#[try_get_http_request(request)]
async fn handle(self, stream: &mut Stream, ctx: &mut Context) -> Status {
    // request 变量包含读取到的 HTTP 请求数据
    Status::Continue
}
```

### try_get_websocket_request

从 TCP 流中读取 WebSocket 请求数据。仅在成功读取数据后执行函数体：

```rust
use hyperlane::*;
use hyperlane_macros::*;

#[route("/ws")]
struct WsRoute;

impl ServerHook for WsRoute {
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

> [!tip]
>
> `#[try_get_websocket_request]` 支持传变量名存储读取的数据；不传变量名时仅在成功读取后执行函数体。

<Bottom />
