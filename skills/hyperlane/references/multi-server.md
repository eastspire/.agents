---
synced_from: docs-pages/src/hyperlane/usage-introduction/multi-server.md@f972247
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
> `hyperlane` 框架支持多服务模式，仅需创建多个 `server` 实例并进行监听即可

### 多服务

> [!tip]
>
> 启动多个服务，监听多个端口

```rust
let app1: tokio::task::JoinHandle<()> = tokio::spawn(async move {
    let mut server_config: ServerConfig = ServerConfig::default();
    server_config.set_address(Server::format_bind_address(DEFAULT_HOST, 80));
    let mut server: Server = Server::default();
    server.server_config(server_config);
    let server_control_hook: ServerControlHook = server.run().await.unwrap_or_default();
    server_control_hook.wait().await;
});
let app2: tokio::task::JoinHandle<()> = tokio::spawn(async move {
    let mut server_config: ServerConfig = ServerConfig::default();
    server_config.set_address(Server::format_bind_address(DEFAULT_HOST, 81));
    let mut server: Server = Server::default();
    server.server_config(server_config);
    let server_control_hook: ServerControlHook = server.run().await.unwrap_or_default();
    server_control_hook.wait().await;
});
let _ = tokio::join!(app1, app2);
```

<Bottom />
