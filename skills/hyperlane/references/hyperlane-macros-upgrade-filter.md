---
synced_from: docs-pages/src/hyperlane-macros/upgrade-filter.md@0c74235
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
> `hyperlane-macros` 提供了协议升级类型过滤属性宏，用于限制路由处理函数仅匹配特定类型的协议升级请求（如 WebSocket、h2c、TLS 等）。

## 可用宏列表

| 宏名称                       | 匹配的升级类型                  |
| ---------------------------- | ------------------------------- |
| `#[is_ws_upgrade_type]`      | WebSocket 升级请求              |
| `#[is_h2c_upgrade_type]`     | HTTP/2 Cleartext (h2c) 升级请求 |
| `#[is_tls_upgrade_type]`     | TLS/SSL 加密连接                |
| `#[is_unknown_upgrade_type]` | 无法识别的非标准升级类型        |

## 示例：WebSocket 升级

```rust
use hyperlane::*;
use hyperlane_macros::*;

#[route("/ws")]
struct WsHandler;

impl ServerHook for WsHandler {
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

## 示例：h2c 升级过滤

```rust
use hyperlane::*;
use hyperlane_macros::*;

#[route("/h2c")]
struct H2cHandler;

impl ServerHook for H2cHandler {
    async fn new(_: &mut Stream, _: &mut Context) -> Self {
        Self
    }

    #[is_h2c_upgrade_type]
    async fn handle(self, stream: &mut Stream, ctx: &mut Context) -> Status {
        Status::Continue
    }
}
```

## 示例：TLS 连接过滤

```rust
#[is_tls_upgrade_type]
async fn handle(self, stream: &mut Stream, ctx: &mut Context) -> Status {
    // 只有 TLS 加密的请求会到达这里
    Status::Continue
}
```

<Bottom />
