---
synced_from: docs-pages/src/hyperlane/usage-introduction/shutdown.md@0c74235
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
> `hyperlane` 框架支持优雅的停机方式，可以通过 `server.shutdown()` 方法实现停机。

```rust
let server_control_hook: ServerControlHook = server.run().await.unwrap_or_default();
server_control_hook.shutdown().await;
```

<Bottom />
