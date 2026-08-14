---
synced_from: docs-pages/src/hyperlane-macros/version-filter.md@f972247
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
> `hyperlane-macros` 提供了 HTTP 版本过滤属性宏，用于限制路由处理函数仅匹配特定 HTTP 协议版本。

## 版本过滤宏

```rust
use hyperlane::*;
use hyperlane_macros::*;

#[route("/http11-only")]
struct Http11Only;

impl ServerHook for Http11Only {
    async fn new(_: &mut Stream, _: &mut Context) -> Self {
        Self
    }

    #[is_http1_1_version]
    async fn handle(self, stream: &mut Stream, ctx: &mut Context) -> Status {
        Status::Continue
    }
}
```

### 可用宏列表

| 宏名称                            | 匹配的 HTTP 版本     |
| --------------------------------- | -------------------- |
| `#[is_http0_9_version]`           | HTTP/0.9             |
| `#[is_http1_0_version]`           | HTTP/1.0             |
| `#[is_http1_1_version]`           | HTTP/1.1             |
| `#[is_http2_version]`             | HTTP/2               |
| `#[is_http3_version]`             | HTTP/3               |
| `#[is_http1_1_or_higher_version]` | HTTP/1.1 及以上版本  |
| `#[is_unknown_version]`           | 无法识别的 HTTP 版本 |

## 标准 HTTP 请求过滤

`#[is_http_version]` 用于限制仅处理**标准 HTTP 请求**（排除 WebSocket、h2c、TLS 等协议升级请求）：

```rust
use hyperlane::*;
use hyperlane_macros::*;

#[route("/http-only")]
struct HttpOnly;

impl ServerHook for HttpOnly {
    async fn new(_: &mut Stream, _: &mut Context) -> Self {
        Self
    }

    #[is_http_version]
    async fn handle(self, stream: &mut Stream, ctx: &mut Context) -> Status {
        Status::Continue
    }
}
```

> [!tip]
>
> `#[is_http_version]` **不接收参数**。它的作用是排除协议升级请求（WebSocket、h2c、TLS 升级），只有标准 HTTP 请求才会通过过滤。

<Bottom />
