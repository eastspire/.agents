---
synced_from: docs-pages/src/hyperlane/usage-introduction/connection.md@f972247
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
> `hyperlane` 框架提供了完整的连接状态管理功能，通过 `Stream` 对象管理连接的关闭状态，以及 `Keep-Alive` 连接支持。

## 连接状态管理

### 设置连接关闭

```rust
stream.set_closed(true);
```

## 读取请求

### try_get_http_request

> [!tip]
>
> 从 TCP 流中读取并解析下一个 HTTP 请求。如果连接已关闭，返回 `RequestError::ServerClosedConnection` 错误。支持超时配置。

```rust
let request_result: Result<Request, RequestError> = stream.try_get_http_request().await;
```

## Keep-Alive 连接

### 检查是否启用 Keep-Alive

```rust
let keep_alive: bool = ctx.get_request().is_enable_keep_alive();
```

### is_keep_alive

> [!tip]
>
> 判断连接是否应该保持活跃，需要结合 `keep_alive` 参数和连接关闭状态综合判断。

```rust
let keep_alive: bool = stream.is_keep_alive(ctx.get_request().is_enable_keep_alive());
```

## 基本使用示例

#### 原生写法

##### 手动管理长连接

> 框架默认会处理长连接，对开发者也提供了手动管理长连接的方式。

```rust
while stream.try_get_http_request().await.is_ok() {
    if !ctx.get_request().is_enable_keep_alive() {
        stream.set_closed(true);
        break;
    }
}
```

##### 关闭连接

> [!tip]
>
> 此方法会关闭 `TCP` 连接，不会终止当前的生命周期（当前生命周期结束不会进入下一次生命周期循环，需要重新建立 `TCP` 连接），当前生命周期内的代码正常执行，但是不会再发送响应。

```rust
stream.set_closed(true);
```

#### 属性宏写法

##### 使用 closed 属性宏

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

<Bottom />
