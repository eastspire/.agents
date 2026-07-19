---
name: hyperlane
description: "A lightweight, high-performance, cross-platform Rust HTTP server library built on Tokio. Use when building Rust web services with HTTP + WebSocket + SSE + raw TCP, defining route handlers with `Server::default().route::<T>(path)`, wiring request/response middleware via `request_middleware` / `response_middleware`, or registering panic/error hooks via `task_panic` / `request_error`. Triggers: hyperlane, Server::new, Server::default, request_middleware, response_middleware, ServerHook, ServerControlHook, HookType, RoutePattern, Context, ServerConfig, RequestConfig, web framework."
license: MIT
---

# hyperlane

- GitHub: <https://github.com/hyperlane-dev/hyperlane.git>
- crates.io: <https://crates.io/crates/hyperlane>
- docs.rs: <https://docs.rs/hyperlane>

## Overview

Hyperlane is a Tokio-based HTTP server library that exposes a fluent builder for assembling:

- routes (static, dynamic `{name}`, regex `{name:pattern}`)
- request middleware (chain executed before route handler)
- response middleware (chain executed after route handler)
- task-panic hooks (recovery / logging)
- request-error hooks (404 / 405 / panics with response shaping)

It re-exports `http_type::*` (request/response types) and the `inventory` plugin-registration crate. WebSocket and SSE are supported via the standalone companion crates `hyperlane-plugin-websocket` and `hyperlane-broadcast` (registered as separate plugins at server boot — see Related Skills below).

Top-level module graph (`src/lib.rs`):

```rust
mod config;     // ServerConfig, RequestConfig
mod context;    // Context (request/response + attributes + panic/error data)
mod error;      // ServerError, RouteError
mod hook;       // HookType, DefaultServerHook, ServerControlHook, traits + types
mod route;      // RoutePattern, RouteMatcher, RouteSegment
mod server;     // Server (the builder + run loop)

pub use {config::*, context::*, error::*, hook::*, route::*, server::*};
pub use {http_type::*, inventory};
```

## 项目元信息

- crate 名: `hyperlane`
- Rust edition: `2024`
- License: `MIT`
- 类型: 单 crate 库（非 workspace），暴露 `Server` 链式 builder + `Context` + `Hook`/`Route`/`Config` 类型
- 关键字: `http`, `request`, `response`, `tcp`, `cross-platform`
- 顶层重导出: `config`, `context`, `error`, `hook`, `route`, `server`, `http_type::*`, `inventory`
- 关键宏支持: 派生自 `lombok-macros` (`Data`, `New`, `Getter`, `Setter`, `CustomDebug`, `DisplayDebug`, `Eq`, `PartialEq`)

## Installation

```shell
cargo add hyperlane
```

`Cargo.toml` 关键依赖（from `hyperlane/Cargo.toml`）:

```toml
[dependencies]
regex = "1"
http-type = "20"
inventory = "0.3"
lombok-macros = "2"
serde = { version = "1", features = ["derive"] }
```

Both `[profile.dev]` and `[profile.release]` use `opt-level = 3`, `lto = true`, `codegen-units = 1`, `strip = "debuginfo"` (per `Cargo.toml`).

## Quick start (HTTP-only)

Minimal `main.rs` pattern (matches `hyperlane-quick-start` style):

```rust
use hyperlane::*;
use serde::{Deserialize, Serialize};

#[derive(Serialize, Deserialize, Debug)]
struct HelloData {
    name: String,
}

async fn front_html(ctx: &mut Context) {
    ctx.set_response_body("hello world")
        .await
        .set_response_status_code(200)
        .await
        .set_response_header("Content-Type", "text/html; charset=utf-8")
        .await;
}

async fn api_post(ctx: &mut Context) {
    let body: String = ctx.get_request_body().await;
    let data: HelloData = serde_json::from_str(&body).unwrap();
    let json: String = serde_json::to_string(&data).unwrap();
    ctx.set_response_body(json)
        .await
        .set_response_status_code(200)
        .await
        .set_response_header("Content-Type", "application/json")
        .await;
}

async fn not_found(ctx: &mut Context) {
    ctx.set_response_status_code(404)
        .await
        .set_response_body("404 not found")
        .await;
}

async fn panic_handler(_ctx: &mut Context) {}

#[tokio::main]
async fn main() {
    let config: ServerConfig = ServerConfig::default().set_address("0.0.0.0:80");
    let server: Server = Server::new()
        .await
        .server_config(config)
        .route::<front_html>("/")
        .route::<api_post>("/api/hello")
        .route::<not_found>("/*")
        .task_panic::<panic_handler>()
        .request_middleware::<front_html>()
        .response_middleware::<front_html>()
        .run().await.unwrap();
    server.wait().await;   // blocks until shutdown_hook fires
}
```

## `Server` builder API

From `src/server/impl.rs`. All methods are `&mut self -> &mut Self` (chainable) except `run` (consumes self, returns `Result<ServerControlHook, ServerError>`):

```rust
impl Server {
    pub fn handle_hook(&mut self, hook: HookType) -> &mut Self
    pub fn config_from_json<C: AsRef<str>>(&mut self, json: C) -> &mut Self
    pub fn server_config(&mut self, config: ServerConfig) -> &mut Self
    pub fn request_config(&mut self, config: RequestConfig) -> &mut Self
    pub fn route<S: AsRef<str>>(&mut self, path: S) -> &mut Self     // registers <T> as the route handler
    pub fn task_panic<S>(&mut self) -> &mut Self                     // registers <T> as task-panic hook
    pub fn request_error<S>(&mut self) -> &mut Self                  // registers <T> as request-error hook
    pub fn request_middleware<S>(&mut self) -> &mut Self
    pub fn response_middleware<S>(&mut self) -> &mut Self
    pub async fn run(&self) -> Result<ServerControlHook, ServerError>
}
impl Default for Server { /* empty Vec hooks + default RouteMatcher */ }
impl From<usize> for Server { /* Arc::from raw address */ }
```

`Server::default()` is also usable; some examples (see `tests/route/fn.rs`) use it directly:

```rust
let mut server: Server = Server::default();
server
    .route::<TestRoute>("/")
    .route::<TestRoute>("/dynamic/{routing}")
    .route::<TestRoute>("/regex/{file:^.*$}");
```

`Default` is the most common path; `Server::new()` is `async` because of internal `inventory` collection.

## `ServerConfig` and `RequestConfig`

From `src/config/struct.rs`:

```rust
#[derive(Clone, CustomDebug, Data, Deserialize, DisplayDebug, Eq, New, PartialEq, Serialize)]
pub struct ServerConfig {
    pub(super) address: String,                // bind address, e.g. "0.0.0.0:80"
    pub(super) nodelay: Option<bool>,          // TCP_NODELAY
    pub(super) ttl: Option<u32>,               // IP_TTL
}
```

Config can be loaded from JSON (test `tests/config/fn.rs::server_config_from_json`):

```json
{
    "address": "0.0.0.0:80",
    "nodelay": true,
    "ttl": 64
}
```

```rust
let cfg: ServerConfig = ServerConfig::from_json(json).unwrap();
// or build via setter chain from `New` macro
let cfg: ServerConfig = ServerConfig::default()
    .set_address("0.0.0.0:80")
    .set_nodelay(Some(true))
    .set_ttl(Some(64));
```

`RequestConfig` (separate struct in same module) holds per-request HTTP settings (buffer sizes, timeouts, etc. — see `http-type` crate for the underlying fields).

## `Context`

From `src/context/{struct,impl}.rs`. Every route/middleware/hook handler receives `&mut Context`. Key methods:

```rust
impl Context {
    // request body / headers / method / version (delegated to http_type)
    pub async fn get_request_body(&self) -> String
    pub async fn get_request_header<K: AsRef<str>>(&self, key: K) -> String
    pub async fn get_request_method(&self) -> Method
    pub async fn get_request_path(&self) -> String
    pub async fn get_request_query<K: AsRef<str>>(&self, key: K) -> String

    // response
    pub async fn set_response_body<B: Into<...>>(&mut self, body: B) -> &mut Self
    pub async fn set_response_status_code(&mut self, code: u16) -> &mut Self
    pub async fn set_response_header<K, V>(&mut self, key: K, value: V) -> &mut Self

    // route params (from /users/{id})
    pub fn try_get_route_param<T: AsRef<str>>(&self, name: T) -> Option<String>
    pub fn get_route_param<T: AsRef<str>>(&self, name: T) -> String  // panics if absent

    // extension attributes (cross-handler scratch space)
    pub fn try_get_attribute<V>(&self, key: impl AsRef<str>) -> Option<V>
    pub fn get_attribute<V>(&self, key: impl AsRef<str>) -> V
    pub fn set_attribute<K, V>(&mut self, key: K, value: V) -> &mut Self
    pub fn remove_attribute<K>(&mut self, key: K) -> &mut Self
    pub fn clear_attribute(&mut self) -> &mut Self

    // panic / error data plumbing
    pub fn set_task_panic(&mut self, panic_data: PanicData) -> &mut Self
    pub fn try_get_task_panic_data(&self) -> Option<PanicData>
    pub fn get_task_panic_data(&self) -> PanicData
    pub fn try_get_request_error_data(&self) -> Option<RequestError>
    pub fn get_request_error_data(&self) -> RequestError
}
```

Route param read example:

```rust
async fn get_user(ctx: &mut Context) {
    let id: String = ctx.get_route_param("id");
    ctx.set_response_body(format!("user id: {id}")).await;
}
// registered via: server.route::<get_user>("/users/{id}");
```

## Routes (`src/route/`)

From `src/route/{struct,enum,type,impl}.rs`:

```rust
pub struct RoutePattern(/* opaque */)
pub struct RouteMatcher {
    /* internally three maps keyed by segment count */
    // static_route:    HashMap<String, RoutePattern>
    // dynamic_route:   HashMap<usize, Vec<(RoutePattern, T)>>     // /users/{id}
    // regex_route:     HashMap<usize, Vec<(RoutePattern, T)>>     // /files/{path:.*}
}

pub enum RouteSegment {
    Static(String),
    Dynamic(String),       // bare {name}
    Regex(String, String), // {name:regex}
}
pub type RouteParams = HashMapXxHash3_64<String, String>;
```

Three route kinds, all co-existing:

```rust
server
    .route::<Index>("/")                         // static
    .route::<About>("/about")                    // static
    .route::<UserDetail>("/users/{id}")          // dynamic single-param
    .route::<FileDetail>("/files/{path:.*}")     // regex
    .route::<Versioned>("/api/{version:\\d+}");  // regex
```

A `ServerHookList` per route slot keeps the handler factory; `RouteMatcher` indexes by segment count for O(1) lookup (test: `tests/route/fn.rs::segment_count_optimization`).

## Hooks (`src/hook/`)

`HookType` (`src/hook/enum.rs`) is the unified registration enum; `Server` exposes the fluent helpers (`route`, `task_panic`, `request_error`, `request_middleware`, `response_middleware`) that internally wrap `handle_hook(HookType::Variant(...))`:

```rust
pub enum HookType {
    TaskPanic(Option<isize>, ServerHookHandlerFactory),
    RequestError(Option<isize>, ServerHookHandlerFactory),
    RequestMiddleware(Option<isize>, ServerHookHandlerFactory),
    Route(&'static str, ServerHookHandlerFactory),
    ResponseMiddleware(Option<isize>, ServerHookHandlerFactory),
}
```

The `Option<isize>` is execution priority — higher runs first. `assert_unique_order` (`src/hook/impl.rs`) panics if two hooks of the same kind share an explicit order.

Trait hierarchy (`src/hook/trait.rs`):

```rust
pub trait FutureSend<T>: Future<Output = T> + Send
pub trait FutureSendStatic<T>: FutureSend<T> + 'static
pub trait FutureBox<T> = Pin<Box<dyn Future<Output = T> + Send>>
pub trait FnContext<R>: Fn(&mut Context) -> R + Send + Sync
pub trait FnContextPinBox<T>: FnContext<FutureBox<T>>
pub trait FnContextStatic<Fut, T>: FnContext<Fut> + 'static
pub trait FutureFn<T>: Fn() -> FutureBox<T> + Send + Sync
pub trait ServerHook: Send + Sync + 'static
```

Type aliases (`src/hook/type.rs`):

```rust
pub type HookHandler<T> = Arc<dyn FnContextPinBox<T>>;
pub type HookHandlerChain<T> = Vec<HookHandler<T>>;
pub type FutureBox<T> = Pin<Box<dyn Future<Output = T> + Send>>;
pub type ServerControlHookHandler<T> = Arc<dyn FutureFn<T>>;
pub type ServerHookHandlerFactory = fn() -> ServerHookHandler;
pub type ServerHookHandler = Arc<dyn FnContextPinBox<()>>;
pub type ServerHookList = Vec<ServerHookHandler>;
pub type ServerHookMap = HashMapXxHash3_64<String, ServerHookHandler>;
pub type ServerHookPatternRoute = HashMapXxHash3_64<usize, Vec<(RoutePattern, ServerHookHandler)>>;
```

`DefaultServerHook` is a `Copy` zero-size struct that gives you pre-wired handlers:

```rust
let server: Server = Server::default().handle_hook(HookType::RequestMiddleware(
    Some(0),
    DefaultServerHook::default_request_middleware,   // factory fn
));
```

`Hook::factory::<T>()` returns a `ServerHookHandler` for any type `T: ServerHook`.

## `ServerControlHook` (`src/hook/struct.rs`)

Returned from `Server::run().await`:

```rust
#[derive(Clone, CustomDebug, DisplayDebug, Getter, Setter)]
pub struct ServerControlHook {
    #[set(pub(crate))] pub(super) wait_hook:     ServerControlHookHandler<()>,
    #[set(pub(crate))] pub(super) shutdown_hook: ServerControlHookHandler<()>,
}

impl ServerControlHook {
    pub async fn wait(&self)               // resolves when server stops
    pub async fn shutdown(&self)           // triggers graceful shutdown
}
```

Usage:

```rust
let control: ServerControlHook = server.run().await.unwrap();
// in main: tokio::spawn(async move { control.wait().await; });
// on Ctrl-C: control.shutdown().await;
```

`format_bind_address(host, port) -> String` (`src/server/impl.rs`) is a free helper that builds the bind string from parts.

## Errors (`src/error/enum.rs`)

```rust
pub enum ServerError { /* bind / accept / IO variants */ }
pub enum RouteError  { /* pattern parse / duplicate / empty */ }
```

`Server::run` returns `Result<ServerControlHook, ServerError>`. `RouteError` is what `route::<T>("")` / duplicate `route::<T>("/x")` calls panic with (see `tests/route/fn.rs::empty_route`/`duplicate_route` using `#[should_panic(expected = "EmptyPattern")]`/`"DuplicatePattern"`).

## Flush helpers (`src/server/impl.rs`)

```rust
pub fn format_bind_address<H: AsRef<str>>(host: H, port: u16) -> String
pub fn try_flush_stdout() -> io::Result<()>
pub fn flush_stdout()
pub fn try_flush_stderr() -> io::Result<()>
pub fn flush_stderr()
pub fn try_flush_stdout_and_stderr() -> io::Result<()>
pub fn flush_stdout_and_stderr()
pub async fn handle_request_error(ctx: &mut Context)  // default 500 body
```

These are the panic-safe wrappers around std I/O — use them in middleware when you `eprintln!` and need to ensure the line is visible before a process exit.

## Request/Response body and headers

`hyperlane` re-exports `http_type::*`. The concrete `set_response_body`, `set_response_header`, `get_request_*` calls on `Context` are async because the underlying buffers may not be fully read until the connection phase completes — always `.await` them.

```rust
async fn json_echo(ctx: &mut Context) {
    let body: String = ctx.get_request_body().await;
    ctx.set_response_body(body).await;
    ctx.set_response_status_code(200).await;
    ctx.set_response_header("Content-Type", "application/json").await;
}
```

## Plugin / WebSocket / SSE

Hyperlane itself is HTTP + middleware + hooks. WebSocket and SSE come from sibling crates registered through the `inventory` plugin registry:

```rust
// Cargo.toml
hyperlane = "21"
hyperlane-plugin-websocket = "..."
hyperlane-broadcast = "..."   // SSE helper
```

The plugins self-register via `inventory::submit!` macros on `static` items, so once they are linked into the binary, `Server::run` picks them up automatically. See `hyperlane-plugin-websocket/SKILL.md` and `hyperlane-broadcast/SKILL.md` for the registration payloads.

## Common pitfalls

1. **`Server::default()` vs `Server::new().await`** — `new()` is async because of `inventory` collection. Use `default()` when you don't need plugin inventory; use `new()` when you do (WebSocket / SSE plugins).
2. **Route pattern `{name}` vs `{name:regex}`** — bare `{name}` matches one segment, `{name:.*}` matches multi-segment. The parser is strict: regex must compile.
3. **Duplicate route registration panics** with `DuplicatePattern`; empty pattern panics with `EmptyPattern`. Both are runtime panics, not compile errors. The duplicate-check is in `src/route/impl.rs`.
4. **`get_route_param` panics if absent** — use `try_get_route_param` for optional params.
5. **`Context` methods are mostly async** — `set_response_body`, `set_response_header`, `set_response_status_code`, all `get_request_*` must be `.await`ed. The sync methods are: `get/set_attribute`, `try_get_route_param`, panic/error-data getters.
6. **Hook priority must be unique per kind** — `assert_unique_order` panics on collision. `None` priority means "default order (0)" and is shared.
7. **`Server::run()` is `&self`, not `&mut self`** — clones internally so the same `Server` value can be inspected after launch.
8. **`inventory` is required for WebSocket / SSE plugins** — they self-register at static-init time. If you see "no websocket plugins found", check that the plugin crate is in `[dependencies]` (not just dev).
9. **`tokio::main` flavor** — hyperlane uses `#[tokio::main]` with default features; multi-threaded runtime is fine.
10. **Body buffering** — large request bodies are streamed via `http_type` buffer config; tune `RequestConfig` buffer size if you expect multi-MB uploads.

## Verification checklist

- [ ] `cargo check -p hyperlane` exits 0
- [ ] `cargo test -p hyperlane` passes `route::*` and `config::server_config_from_json`
- [ ] `cargo clippy --all-targets -p hyperlane` 0 warnings
- [ ] Smoke test: `curl http://127.0.0.1:80/` returns 200 with expected body
- [ ] Panic test: register a handler that `panic!()` and verify `task_panic` hook fires (no process abort)
- [ ] WebSocket / SSE plugin: if using, verify `inventory` collection picks up plugin at startup (log line or `Server::new().await` does not hang)

## Source-of-truth files

- `src/lib.rs` — top-level module declarations + `pub use`
- `src/server/{struct,impl}.rs` — `Server` builder + `Default`/`PartialEq`/`From<usize>`
- `src/server/impl.rs::run` — main loop entry
- `src/config/struct.rs` — `ServerConfig` (JSON / setter-based)
- `src/context/{struct,impl}.rs` — `Context` request/response + attributes + panic data
- `src/route/{struct,enum,type,impl}.rs` — `RoutePattern`, `RouteMatcher`, `RouteSegment`
- `src/hook/{enum,struct,trait,type,impl}.rs` — `HookType`, `ServerControlHook`, all traits + aliases
- `src/error/enum.rs` — `ServerError`, `RouteError`
- `tests/route/fn.rs` — routing behavior (`empty_route`, `duplicate_route`, `get_route`, `segment_count_optimization`, `regex_route_segment_count`, `mixed_route_types`)
- `tests/config/fn.rs` — JSON round-trip

## Related skills

- `hyperlane-quick-start` — full-stack example app (HTTP + WebSocket + SSE + middleware + DB + JWT)
- `hyperlane-broadcast` — SSE / event-stream broadcast helper
- `hyperlane-plugin-websocket` — WebSocket plugin registration
- `hyperlane-macros` — `lombok-macros`-derived `Data`/`New`/`Getter`/`Setter`/`CustomDebug`/`DisplayDebug` patterns used throughout hyperlane
- `hyperlane-log` — async logging helpers
- `hyperlane-cli` — `hyperlane-cli` companion CLI
- `http-constant` — HTTP method / status / header constants (referenced by `http_type`)
- `http-compress`, `http-request`, `http-type` — sibling crates in the hyperlane ecosystem