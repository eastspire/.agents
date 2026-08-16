---
synced_from: docs-pages/src/hyperlane/middleware/auth.md@0c74235
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

### 身份校验中间件

#### 原生写法

```rs
use hyperlane::*;

struct HttpVersionMiddleware;
struct AuthMiddleware;
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

impl ServerHook for AuthMiddleware {
    async fn new(_: &mut Stream, _: &mut Context) -> Self {
        Self
    }

    async fn handle(self, stream: &mut Stream, ctx: &mut Context) -> Status {
        let auth_str: String = ctx
            .get_request()
            .try_get_header_back(AUTHORIZATION)
            .unwrap_or_default();
        if auth_str.is_empty() {
            let data: Vec<u8> = ctx
                .get_mut_response()
                .set_status_code(401)
                .set_body("Unauthorized")
                .build();
            if stream.try_send(data).await.is_err() {
                stream.set_closed(true);
            }
            return Status::Reject;
        }
        Status::Continue
    }
}

impl ServerHook for IndexRoute {
    async fn new(_: &mut Stream, _: &mut Context) -> Self {
        Self
    }

    async fn handle(self, _: &mut Stream, ctx: &mut Context) -> Status {
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
        .request_middleware::<AuthMiddleware>()
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

```rs
use hyperlane::*;
use hyperlane_utils::*;

#[request_middleware(1)]
struct HttpVersionMiddleware;
#[request_middleware(2)]
struct AuthMiddleware;
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

impl ServerHook for AuthMiddleware {
    async fn new(_: &mut Stream, _: &mut Context) -> Self {
        Self
    }

    #[try_get_request_header(AUTHORIZATION => auth_str_opt)]
    async fn handle(self, stream: &mut Stream, ctx: &mut Context) -> Status {
        let auth_str: String = auth_str_opt.unwrap_or_default();
        if auth_str.is_empty() {
            let data: Vec<u8> = ctx
                .get_mut_response()
                .set_status_code(401)
                .set_body("Unauthorized")
                .build();
            if stream.try_send(data).await.is_err() {
                stream.set_closed(true);
            }
            return Status::Reject;
        }
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
