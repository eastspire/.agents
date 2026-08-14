---
synced_from: docs-pages/src/hyperlane/usage-introduction/async.md@f972247
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
> 由于 `hyperlane` 框架使用 `tokio` 作为异步运行时

#### 原生写法

```rust
#[tokio::main]
async fn main() {
    let mut server: Server = Server::default();
    let server_control_hook: ServerControlHook = server.run().await.unwrap_or_default();
    server_control_hook.wait().await;
}
```

#### 属性宏写法

```rust
use hyperlane::*;
use hyperlane_macros::*;

#[hyperlane(server: Server)]
#[hyperlane(server_config: ServerConfig)]
#[tokio::main]
async fn main() {
    server.server_config(server_config);
    let server_control_hook: ServerControlHook = server.run().await.unwrap_or_default();
    server_control_hook.wait().await;
}
```

> [!tip]
>
> 如果需要在异步中使用 `Context` 请使用 `Context` 中的 `clone` 方法，原因是框架内 `Context` 分配在堆上，请求完成后会回收堆上内存，不保证线程安全（例如并发更新 `Context` 上的数据），如果需要安全操作请使用上述方法。

<Bottom />
