---
synced_from: docs-pages/src/hyperlane/middleware/timeout.md@f972247
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

### 超时中间件

#### 原生写法

```rust
use hyperlane::{
    tokio::{
        spawn,
        time::{sleep, timeout},
    },
    *,
};
use std::time::Duration;

struct HttpVersionMiddleware;
struct TimeoutMiddleware;
struct IndexRoute;
struct ResponseMiddleware;

impl ServerHook for HttpVersionMiddleware {
    async fn new(_: &mut Stream, _: &mut Context) -> Self {
        Self
    }

    async fn handle(self, _: &mut Stream, ctx: &mut Context) -> Status {
        ctx.get_mut_response().set_version(HttpVersion::Http1_1);
        Status::Continue
    }
}

impl ServerHook for TimeoutMiddleware {
    async fn new(_: &mut Stream, _: &mut Context) -> Self {
        Self
    }

    async fn handle(self, _: &mut Stream, ctx: &mut Context) -> Status {
        let ctx_addr: usize = ctx.into();
        let new_ctx: &mut Context = ctx_addr.into();
        spawn(async move {
            timeout(Duration::from_millis(100), async move {
                new_ctx
                    .get_mut_response()
                    .set_status_code(504)
                    .set_body("timeout");
                let data: Vec<u8> = new_ctx.get_mut_response().build();
                // Note: stream is not available in spawned task in the new API
            })
            .await
            .unwrap();
        });
        Status::Continue
    }
}

impl ServerHook for IndexRoute {
    async fn new(_: &mut Stream, _: &mut Context) -> Self {
        Self
    }

    async fn handle(self, _: &mut Stream, ctx: &mut Context) -> Status {
        sleep(Duration::from_secs(1)).await;
        ctx.get_mut_response()
            .set_status_code(200)
            .set_body("Hello, world!");
        Status::Continue
    }
}

impl ServerHook for ResponseMiddleware {
    async fn new(_: &mut Stream, _: &mut Context) -> Self {
        Self
    }

    async fn handle(self, stream: &mut Stream, ctx: &mut Context) -> Status {
        if ctx.get_request().is_ws_upgrade_type() {
            return Status::Continue;
        }
        let data: Vec<u8> = ctx.get_mut_response().build();
        if stream.try_send(data).await.is_err() {
            stream.set_closed(true);
            return Status::Reject;
        }
        Status::Continue
    }
}

#[tokio::main]
async fn main() {
    let mut server: Server = Server::default();
    server
        .request_middleware::<HttpVersionMiddleware>()
        .await
        .request_middleware::<TimeoutMiddleware>()
        .await
        .response_middleware::<ResponseMiddleware>()
        .await
        .route::<IndexRoute>("/")
        .await;
    let server_control_hook: ServerControlHook = server.run().await.unwrap_or_default();
    server_control_hook.wait().await;
}
```

#### 属性宏写法

```rust
use hyperlane::{
    tokio::{
        spawn,
        time::{sleep, timeout},
    },
    *,
};
use hyperlane_utils::*;
use std::time::Duration;

#[request_middleware(1)]
struct HttpVersionMiddleware;
#[request_middleware(2)]
struct TimeoutMiddleware;
#[route("/")]
struct IndexRoute;
#[response_middleware(1)]
struct ResponseMiddleware;

impl ServerHook for HttpVersionMiddleware {
    async fn new(_: &mut Stream, _: &mut Context) -> Self {
        Self
    }

    #[response_version(HttpVersion::Http1_1)]
    async fn handle(self, _: &mut Stream, _: &mut Context) -> Status {
        Status::Continue
    }
}

impl ServerHook for TimeoutMiddleware {
    async fn new(_: &mut Stream, _: &mut Context) -> Self {
        Self
    }

    async fn handle(self, _: &mut Stream, ctx: &mut Context) -> Status {
        let ctx_addr: usize = ctx.into();
        let new_ctx: &mut Context = ctx_addr.into();
        spawn(async move {
            timeout(Duration::from_millis(100), async move {
                new_ctx
                    .get_mut_response()
                    .set_status_code(504)
                    .set_body("timeout");
            })
            .await
            .unwrap();
        });
        Status::Continue
    }
}

impl ServerHook for IndexRoute {
    async fn new(_: &mut Stream, _: &mut Context) -> Self {
        Self
    }

    #[response_status_code(200)]
    #[response_body("Hello, world!")]
    async fn handle(self, _: &mut Stream, _: &mut Context) -> Status {
        sleep(Duration::from_secs(1)).await;
        Status::Continue
    }
}

impl ServerHook for ResponseMiddleware {
    async fn new(_: &mut Stream, _: &mut Context) -> Self {
        Self
    }

    #[send]
    async fn handle(self, _: &mut Stream, _: &mut Context) -> Status {
        Status::Continue
    }
}

#[tokio::main]
async fn main() {
    let server_control_hook: ServerControlHook = Server::default().run().await.unwrap_or_default();
    server_control_hook.wait().await;
}
```

<Bottom />
