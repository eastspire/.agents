---
synced_from: docs-pages/src/hyperlane/usage-introduction/run.md@0c74235
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
> `hyperlane` 框架运行后需要显示调用 `run` 来完成服务启动。此过程只会启动服务，监听端口，不会等待和处理请求。

```rust
let _: ServerControlHook = server.run().await.unwrap_or_default();
```

<Bottom />
