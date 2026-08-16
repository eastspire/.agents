---
synced_from: docs-pages/src/hyperlane/usage-introduction/websocket.md@0c74235
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
> `hyperlane` 框架支持 `websocket` 协议，服务端自动处理协议升级，支持请求中间件，路由处理，响应中间件。

### 服务端代码

> [!tip]
>
> `hyperlane` 框架发送 `websocket` 响应使用 `stream.try_send_list` 发送帧列表。
> 由于 `websocket` 协议基于 `http`，所以可以像使用 `http` 一样处理请求，
> 但是需要注意响应数据需要通过 `WebSocketFrame::create_frame_list` 进行帧处理。
> 对于 `websocket` 响应，请统一使用 `stream.try_send_list` 或 `stream.try_send` 方法。

#### 单点发送

```rust
struct WebsocketRoute;

impl WebsocketRoute {
    async fn try_send_body_hook(
        &self,
        stream: &mut Stream,
        ctx: &mut Context,
    ) -> Result<(), ResponseError> {
        let send_result: Result<(), ResponseError> = if ctx.get_request().is_ws_upgrade_type() {
            let body: &ResponseBody = ctx.get_response().get_body();
            let frame_list: Vec<ResponseBody> = WebSocketFrame::create_frame_list(body);
            stream.try_send_list(&frame_list).await
        } else {
            let body: &Vec<u8> = ctx.get_response().get_body();
            stream.try_send(body).await
        };
        if send_result.is_err() {
            stream.set_closed(true);
        }
        send_result
    }
}

impl ServerHook for WebsocketRoute {
    async fn new(_: &mut Stream, _: &mut Context) -> Self {
        Self
    }

    async fn handle(self, stream: &mut Stream, ctx: &mut Context) -> Status {
        while let Ok(body) = stream.try_get_websocket_request().await {
            ctx.get_mut_response().set_body(body);
            if self.try_send_body_hook(stream, ctx).await.is_err() {
                return Status::Reject;
            }
        }
        Status::Continue
    }
}
```

#### 属性宏写法

> [!tip]
>
> 可以使用 `#[is_ws_upgrade_type]` 和 `#[try_get_websocket_request]` 属性宏简化 WebSocket 处理。
> `#[try_get_websocket_request]` 支持传入变量名来存储读取的请求数据。

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

> [!tip]
>
> `#[try_get_websocket_request]` 不传变量名时，仅在成功读取数据后执行函数体；传变量名时，将读取的数据存储到指定变量中。

#### 广播发送

> [!tip]
>
> 需要阻塞住当前处理函数，将后续所有请求在处理函数中处理。
> 这里使用 `tokio` 的 `select` 来处理多个请求，使用 [`hyperlane-broadcast`](../../hyperlane-broadcast/README.md) 来实现广播。

### 客户端代码

```js
const ws = new WebSocket('ws://localhost:60000/websocket');

ws.onopen = () => {
  console.log('WebSocket opened');
  setInterval(() => {
    ws.send(`Now time: ${new Date().toISOString()}`);
  }, 1000);
};

ws.onmessage = (event) => {
  console.log('Receive: ', event.data);
};

ws.onerror = (error) => {
  console.error('WebSocket error: ', error);
};

ws.onclose = () => {
  console.log('WebSocket closed');
};
```

<Bottom />
