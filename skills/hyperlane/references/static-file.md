---
synced_from: docs-pages/src/hyperlane/middleware/static-file.md@0c74235
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

### 静态资源中间件

#### 原生写法

```rs
use hyperlane::*;

const STATIC_DIR_PATH_KEY: &str = "static_dir_path";
const STATIC_FILE_DATA_KEY: &str = "static_file_data";

struct HttpVersionMiddleware;
struct StaticMiddleware;
struct ResponseMiddleware;

impl ServerHook for HttpVersionMiddleware {
    async fn new(_: &mut Stream, _: &mut Context) -> Self {
        Self
    }

    async fn handle(self, _: &mut Stream, ctx: &mut Context) -> Status {
        ctx.get_mut_response().set_version(HttpVersion::Http1_1);
        ctx.set_attribute(STATIC_DIR_PATH_KEY, "./");
        Status::Continue
    }
}

impl ServerHook for StaticMiddleware {
    async fn new(_: &mut Stream, _: &mut Context) -> Self {
        Self
    }

    async fn handle(self, _: &mut Stream, ctx: &mut Context) -> Status {
        let static_path_opt: Option<&str> = ctx.try_get_attribute(STATIC_DIR_PATH_KEY);
        let static_path: &str =
            static_path_opt.expect(&format!("attribute {STATIC_DIR_PATH_KEY} not found"));
        let path: &String = ctx.get_request().get_path();
        let file_path: String = format!("{static_path}{path}");
        let file_extension: String = FileExtension::get_extension_name(&file_path);
        let content_type: &'static str = FileExtension::parse(&file_extension).get_content_type();
        let content_type: String =
            ContentType::format_content_type_with_charset(content_type, UTF8);
        ctx.get_mut_response()
            .set_header(CONTENT_TYPE, &content_type);
        let file_data_opt: Option<String> = tokio::fs::read_to_string(&file_path).await.ok();
        ctx.set_attribute(STATIC_FILE_DATA_KEY, file_data_opt);
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
        let static_file_data_opt: Option<String> = ctx
            .try_get_attribute(STATIC_FILE_DATA_KEY)
            .expect("attribute static_file_data not found");
        ctx.get_mut_response()
            .set_body(static_file_data_opt.unwrap_or_default());
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
        .request_middleware::<StaticMiddleware>()
        .await
        .response_middleware::<ResponseMiddleware>()
        .await;
    let server_control_hook: ServerControlHook = server.run().await.unwrap_or_default();
    server_control_hook.wait().await;
}
```

#### 属性宏写法

```rs
use hyperlane::*;
use hyperlane_utils::*;

const STATIC_DIR_PATH_KEY: &str = "static_dir_path";
const STATIC_FILE_DATA_KEY: &str = "static_file_data";

#[request_middleware(1)]
struct HttpVersionMiddleware;
#[request_middleware(2)]
struct StaticMiddleware;
#[response_middleware(1)]
struct ResponseMiddleware;

impl ServerHook for HttpVersionMiddleware {
    async fn new(_: &mut Stream, _: &mut Context) -> Self {
        Self
    }

    #[response_version(HttpVersion::Http1_1)]
    async fn handle(self, _: &mut Stream, ctx: &mut Context) -> Status {
        ctx.set_attribute(STATIC_DIR_PATH_KEY, "./");
        Status::Continue
    }
}

impl ServerHook for StaticMiddleware {
    async fn new(_: &mut Stream, _: &mut Context) -> Self {
        Self
    }

    #[prologue_macros(request_path(path), try_get_attribute(STATIC_DIR_PATH_KEY => static_path_opt: &str))]
    #[epilogue_macros(response_header(CONTENT_TYPE, content_type))]
    async fn handle(self, _: &mut Stream, ctx: &mut Context) -> Status {
        let static_path: &str =
            static_path_opt.expect(&format!("attribute {STATIC_DIR_PATH_KEY} not found"));
        let file_path: String = format!("{static_path}{path}");
        let file_extension: String = FileExtension::get_extension_name(&file_path);
        let content_type: &'static str = FileExtension::parse(&file_extension).get_content_type();
        let content_type: String =
            ContentType::format_content_type_with_charset(content_type, UTF8);
        let file_data_opt: Option<String> = tokio::fs::read_to_string(&file_path).await.ok();
        ctx.set_attribute(STATIC_FILE_DATA_KEY, file_data_opt);
        Status::Continue
    }
}

impl ServerHook for ResponseMiddleware {
    async fn new(_: &mut Stream, _: &mut Context) -> Self {
        Self
    }

    #[try_get_attribute(STATIC_FILE_DATA_KEY => static_file_data_opt: String)]
    async fn handle(self, stream: &mut Stream, ctx: &mut Context) -> Status {
        let static_file_data: String =
            static_file_data_opt.expect("attribute static_file_data not found");
        ctx.get_mut_response().set_body(static_file_data);
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
    let server_control_hook: ServerControlHook = Server::default().run().await.unwrap_or_default();
    server_control_hook.wait().await;
}
```

<Bottom />
