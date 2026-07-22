---
name: hyperlane
description: 'A lightweight, high-performance, cross-platform Rust HTTP server library built on Tokio. Use when building Rust web services with HTTP + WebSocket + SSE + raw TCP, defining route handlers via trait `ServerHook` with `new` + `async fn handle -> Status` + registered through `Server::default().route::<MyHandler>(path)` (turbofish type marker) or `task_panic::<T>()`, wiring request/response middleware via `request_middleware::<T>`/`response_middleware::<T>`, registering panic/error hooks via `task_panic::<T>`/`request_error::<T>`, using `Context` for per-request request/response/attributes/route_params/panic+error data, and exposing lifecycle via `ServerControlHook { wait, shutdown }` returned from `Server::run().await`. Triggers: hyperlane, Server::new, Server::default, ServerHook, ServerControlHook, HookType, RoutePattern, Context, ServerConfig, RequestConfig, Status, RequestError, ServerError, web framework, Tokio HTTP server.'
license: MIT
---

# hyperlane

- GitHub: <https://github.com/hyperlane-dev/hyperlane.git>
- crates.io: <https://crates.io/crates/hyperlane>
- docs.rs: <https://docs.rs/hyperlane>

## Overview

Hyperlane is a Tokio-based HTTP server library (v21.x, edition 2024, `panic = "unwind"`) that exposes a fluent builder for assembling:

- routes (static, dynamic `{name}`, regex `{name:pattern}`)
- request middleware (chain executed before route handler)
- response middleware (chain executed after route handler)
- task-panic hooks (recovery / logging)
- request-error hooks (404 / 405 / panics with response shaping)

It re-exports `http_type::*` (request/response types) and the `inventory` plugin-registration crate. WebSocket and SSE are supported via the standalone companion crates `hyperlane-plugin-websocket` and `hyperlane-broadcast` (registered as separate plugins at server boot via `inventory::collect!(HookType)` — see Related Skills below).

Top-level module graph (`src/lib.rs`):

```rust
mod config;     // ServerConfig, RequestConfig
mod context;    // Context (request/response + attributes + panic/error data)
mod error;      // ServerError, RouteError
mod hook;       // HookType, DefaultServerHook, ServerControlHook, Hook, traits + types
mod route;      // RoutePattern, RouteMatcher, RouteSegment
mod server;     // Server (the builder + run loop)

pub use {config::*, context::*, error::*, hook::*, route::*, server::*};
pub use {http_type::*, inventory};
```

Plugin self-registration: `collect!(HookType);` is invoked in `src/route/impl.rs` — every `#[proc_macro_attribute]` handler registered through `hyperlane-macros` (`#[route]`, `#[request_middleware]`, etc.) is collected by `inventory` and the framework can find them statically without explicit registration calls.

## 项目元信息

- crate 名: `hyperlane`
- Rust edition: `2024`
- License: `MIT`
- 类型: 单 crate 库（非 workspace），暴露 `Server` builder + `Context` + `Hook`/`Route`/`Config` 类型
- 关键字: `http`, `request`, `response`, `tcp`, `cross-platform`
- 顶层重导出: `config::*`, `context::*`, `error::*`, `hook::*`, `route::*`, `server::*`, `http_type::*`, `inventory`
- 关键宏支持: 派生自 `lombok-macros` (`Data`, `New`, `Getter`, `GetterMut`, `Setter`, `CustomDebug`, `DisplayDebug`, `Eq`, `PartialEq`, `Hash`, `Clone`, `Default`)
- profile: `[profile.dev]` + `[profile.release]` both use `opt-level = 3`, `lto = true`, `incremental = false`, `panic = "unwind"`, `debug = false`, `codegen-units = 1`, `strip = "debuginfo"` (per `Cargo.toml`)

## Installation

```shell
cargo add hyperlane
```

`Cargo.toml` 关键依赖（from `hyperlane/Cargo.toml`）:

```toml
[dependencies]
regex = "1.13.1"
http-type = "20.1.7"
inventory = "0.3.24"
lombok-macros = "2.0.33"
serde = { version = "1.0.229", features = ["derive"] }

# proc-macro sugar for declaring route handlers / middleware:
hyperlane-macros = "23"
```

## Quick start (HTTP-only, function-style)

Minimal `main.rs` pattern (matches `hyperlane-quick-start` style). Hyperlane offers two registration styles: (1) **function-style** — register any `async fn(&mut Context)`-shaped closure via `ServerHookHandlerFactory`; (2) **trait-style** — implement the `ServerHook` trait (recommended, used by `hyperlane-macros`). This example uses the trait-style form to be macro-friendly:

```rust
use hyperlane::*;

struct FrontHtml;

impl ServerHook for FrontHtml {
    async fn new(_: &mut Stream, _: &mut Context) -> Self { Self }
    async fn handle(self, _: &mut Stream, ctx: &mut Context) -> Status {
        ctx.set_response_body("hello world").await
            .set_response_status_code(200).await
            .set_response_header("Content-Type", "text/html; charset=utf-8").await;
        Status::Continue
    }
}

struct NotFound;

impl ServerHook for NotFound {
    async fn new(_: &mut Stream, _: &mut Context) -> Self { Self }
    async fn handle(self, _: &mut Stream, ctx: &mut Context) -> Status {
        ctx.set_response_status_code(404).await
            .set_response_body("404 not found").await;
        Status::Continue
    }
}

struct PanicHandler;

impl ServerHook for PanicHandler {
    async fn new(_: &mut Stream, _: &mut Context) -> Self { Self }
    async fn handle(self, _: &mut Stream, _: &mut Context) -> Status { Status::default() }
}

#[tokio::main]
async fn main() {
    let config: ServerConfig = ServerConfig::default().set_address("0.0.0.0:80".to_owned());
    let server: Server = Server::default()
        .server_config(config)
        .route::<FrontHtml>("/")
        .route::<NotFound>("/*")
        .task_panic::<PanicHandler>()
        .request_middleware::<FrontHtml>()
        .response_middleware::<FrontHtml>();
    let control: ServerControlHook = server.run().await.unwrap();
    control.wait().await;
}
```

With `hyperlane-macros`, the trait boilerplate collapses to a single attribute on an async fn:

```rust
use hyperlane::*;
use hyperlane_macros::*;

#[route]
async fn root(_: &mut Stream, ctx: &mut Context) {
    ctx.set_response_body("hello").await
        .set_response_status_code(200).await;
}

#[request_middleware]
async fn log_req(_: &mut Stream, ctx: &mut Context) {
    eprintln!("{} {}", ctx.get_request_method().await, ctx.get_request_path().await);
}
```

## `Server` builder API

From `src/server/{struct,impl}.rs`. All `route::<T>`, `task_panic::<T>`, `request_error::<T>`, `request_middleware::<T>`, `response_middleware::<T>` methods take a **type marker** `S` (only used at compile time to monomorphize the `ServerHookHandlerFactory`) — they are turbofish-only, no runtime value comes from `S`. Chainable methods return `&mut Self`.

```rust
impl Server {
    // Hook dispatcher (rarely called directly):
    pub fn handle_hook(&mut self, hook: HookType)            // dispatches by HookType variant

    // Configuration:
    pub fn config_from_json<C: AsRef<str>>(&mut self, json: C) -> &mut Self
    pub fn server_config(&mut self, config: ServerConfig) -> &mut Self
    pub fn request_config(&mut self, config: RequestConfig) -> &mut Self

    // Registration (turbofish type marker only — no value):
    pub fn route<S>(&mut self, path: impl AsRef<str>) -> &mut Self where S: ServerHook
    pub fn task_panic<S>(&mut self) -> &mut Self             where S: ServerHook
    pub fn request_error<S>(&mut self) -> &mut Self          where S: ServerHook
    pub fn request_middleware<S>(&mut self) -> &mut Self     where S: ServerHook
    pub fn response_middleware<S>(&mut self) -> &mut Self    where S: ServerHook

    // Lifecycle:
    pub async fn run(&self) -> Result<ServerControlHook, ServerError>

    // Bound-address builder (associated fn, no &self):
    pub fn format_bind_address<H: AsRef<str>>(host: H, port: u16) -> String

    // Stdout / stderr flush helpers (associated fns):
    pub fn try_flush_stdout() -> io::Result<()>
    pub fn flush_stdout()
    pub fn try_flush_stderr() -> io::Result<()>
    pub fn flush_stderr()
    pub fn try_flush_stdout_and_stderr() -> io::Result<()>
    pub fn flush_stdout_and_stderr()
}

// Conversions:
impl Default for Server { /* empty Vec hooks + default RouteMatcher */ }
impl Eq / PartialEq for Server       // pointer-equality on hook arcs
impl From<usize> for Server            // Arc::from raw address
impl From<&Server> / From<&mut Server> for usize
impl AsRef<Server> / AsMut<Server>
impl From<ServerConfig> for Server      // uses config, default the rest
impl From<RequestConfig> for Server     // uses request config, default the rest
```

Implementation notes:

- `Server::run` is `&self`, **not** `&mut self` — clones the relevant state internally so the same `Server` value can be inspected after launch. Internally it `unsafe { self.leak() }` the `&self` to obtain a `&'static Server` (used by the spawned accept loop), so each `run` call effectively consumes the `Server` for background tasks.
- `route::<T>(path)` calls `RouteMatcher::add(...)` which `unwrap()`s — empty pattern panics with `RouteError::EmptyPattern`, duplicate pattern panics with `RouteError::DuplicatePattern(String)`, invalid regex pattern returns `RouteError::InvalidRegexPattern(String)` (also unwrapped → panic).
- `task_panic::<T>` / `request_middleware::<T>` / `response_middleware::<T>` push into `Vec<ServerHookHandler>` which grows monotonically; `assert_unique_order` is **not** called by the fluent helpers — only when using `handle_hook(HookType::...)` with an explicit `order: Some(isize)` does priority-uniqueness get checked.
- Memory ownership: each accepted connection boxes a `Stream` and a `Context`, `Box::leak`s them to obtain `&'static mut`, then converts to a `usize` address that is passed through a spawn boundary; on completion the inner closures reclaim them with `Box::from_raw`. This is why `Stream` + `Context` implement `From<usize>`/`From<&mut Self> for usize` and the unsafe `Lifetime::leak/leak_mut`. **Do not allocate `Stream` / `Context` yourself and submit them via `From<usize>` from outside the accept loop** — the framework expects exclusive ownership per request.

## `ServerConfig` and `RequestConfig`

Both come from `src/config/struct.rs` + `src/config/impl.rs` and are `#[derive(Data, New, Deserialize, ...)]` — so they expose lombok-style `Default::set_*(&mut self) -> &mut Self` builders, JSON `from_json` constructors, and `Getter` methods.

### `ServerConfig`

```rust
#[derive(Clone, CustomDebug, Data, Deserialize, DisplayDebug, Eq, New, PartialEq, Serialize)]
pub struct ServerConfig {
    #[set(type(AsRef<str>))]
    pub(super) address: String,   // bind address, e.g. "0.0.0.0:80"
    pub(super) nodelay: Option<bool>,                       // TCP_NODELAY applied per accepted socket
    pub(super) ttl: Option<u32>,                            // IP_TTL applied per accepted socket
}

let cfg: ServerConfig = ServerConfig::default()
    .set_address("0.0.0.0:80".to_owned())
    .set_nodelay(Some(true))
    .set_ttl(Some(64));
let cfg: ServerConfig = ServerConfig::from_json(r#"{"address":"0.0.0.0:80","nodelay":true,"ttl":64}"#).unwrap();
```

In the server's accept loop, `configure_stream(&TcpStream)` (from `src/server/impl.rs`) reads `nodelay` and `ttl` and applies them after `TcpListener::accept` — `None` means "leave default".

### `RequestConfig`

```rust
#[derive(Clone, Copy, Data, Debug, Deserialize, DisplayDebug, Eq, New, PartialEq, Serialize)]
pub struct RequestConfig {
    #[get(type(copy))] #[set] pub buffer_size: usize,            // per-read chunk size for header parsing
    #[get(type(copy))] #[set] pub max_path_size: usize,
    #[get(type(copy))] #[set] pub max_header_count: usize,
    #[get(type(copy))] #[set] pub max_header_key_size: usize,
    #[get(type(copy))] #[set] pub max_header_value_size: usize,
    #[get(type(copy))] #[set] pub max_body_size: usize,
    #[get(type(copy))] #[set] pub read_timeout_ms: u64,
}
```

This struct is `Copy` (everything is `usize` / `u64`), and lives inside each `Stream` so every connection enforces the same limits. Tune via `.request_config(cfg)` on `Server`.

## `Context`

From `src/context/{struct,impl}.rs`. Every route/middleware/hook handler receives `&mut Context` after the framework boxed+leaked+address-roundtripped it. Conceptually:

```rust
#[derive(Clone, CustomDebug, Data, DisplayDebug)]
pub struct Context {
    pub(super) request: Request,
    pub(super) response: Response,
    #[get_mut(skip)] pub(super) route_params: RouteParams,
    pub(super) attributes: ThreadSafeAttributeStore,
}
```

The `attributes` store is `HashMap<String, ArcAnySendSync>` keyed by stringified `Attribute` (internal vs external); the keys for externally-set attributes are `Attribute::External("your-key").to_string()` and internally reserved ones are `Attribute::Internal(key)` (`InternalAttribute` is `enum { TaskPanicData, RequestErrorData }`).

The macro sugar `#[attribute(name = "...")]`, `#[attribute("...")]`, `#[try_get_attribute(name = "...")]` from `hyperlane-macros` translates these `set_attribute` / `try_get_attribute` calls. The async/sync split:

- **Async** — `set_response_body`, `set_response_status_code`, `set_response_header`, `set_response_version`, `get_request_body`, `get_request_header`, `get_request_method`, `get_request_path`, `get_request_query`, `get_request_version` (all delegate to `http_type` buffer completion which may be deferred to the connection phase).
- **Sync** — `try_get_route_param` / `get_route_param`, all `get/set/remove/clear_attribute`, `try_get_task_panic_data` / `get_task_panic_data`, `try_get_request_error_data` / `get_request_error_data`, `set_task_panic`.

```rust
async fn get_user(ctx: &mut Context) {
    let id: String = ctx.get_route_param("id");
    let body: String = ctx.get_request_body().await;
    ctx.set_response_body(format!("user id: {id}: {body}")).await
        .set_response_status_code(200).await
        .set_response_header("Content-Type", "text/plain").await;
}

// registered via: server.route::<get_user>("/users/{id}");
```

`set_task_panic` / `set_request_error_data` are normally only called by the framework; user code reads them with the `try_get_*_data` / `get_*_data` pair inside a panic or error handler.

## Routes (`src/route/`)

From `src/route/{struct,enum,type,impl}.rs`:

```rust
pub struct RoutePattern(/* opaque */);          // wraps a RouteSegmentList (Vec<RouteSegment>)
pub struct RouteMatcher {
    pub(super) static_route:  ServerHookMap,                       // HashMap<String, ServerHookHandler>
    pub(super) dynamic_route: ServerHookPatternRoute,             // HashMap<usize, Vec<(RoutePattern, ServerHookHandler)>>
    pub(super) regex_route:   ServerHookPatternRoute,             // same shape, tail-regex aware
}

#[derive(Clone, CustomDebug, DisplayDebug, Eq, PartialEq, Ord, Hash)]
pub enum RouteSegment {
    Static(String),
    Dynamic(String),                                   // bare {name}
    Regex(String, Regex),                              // {name:regex} — Regex is compiled `regex::Regex`
}

pub type RouteParams = HashMapXxHash3_64<String, String>;          // captured {name} values
pub type RouteSegmentList = Vec<RouteSegment>;
pub(crate) type PathComponentList<'a> = Vec<&'a str>;
```

Three route kinds co-exist on the same `Server`. The matcher indexes by segment count (the outer `HashMap` key) for O(1) candidate filtering, then walks matching routes in insertion order:

```rust
server
    .route::<Index>("/")                                  // static
    .route::<About>("/about")                             // static
    .route::<UserDetail>("/users/{id}")                   // dynamic single-param
    .route::<FileDetail>("/files/{path:^.*$}")            // tail regex matches ≥ N−1 segments
    .route::<Versioned>("/api/{version:\\d+}");           // positional regex matches one segment
```

Pattern parser (`src/route/impl.rs::RoutePattern::parse_route`):

- Empty pattern → `RouteError::EmptyPattern` (panics on `route::<T>("")`).
- Trims a single leading `/` before splitting.
- Splitting on `/`: a segment wrapped in `{}` is `Dynamic(content)`; if `content` contains `:`, the part after `:` is compiled as `Regex::new(...)` and stored as `Regex(name, regex)` (errors propagate as `RouteError::InvalidRegexPattern(String)`).
- Otherwise the segment is `Static(segment.to_owned())`.
- Duplicate registration of the same path → `RouteError::DuplicatePattern(String)`.

Performance notes:

- Purely static routes take a fast path (`is_static() -> try_match_static_path`) that walks bytes without allocating a `PathComponentList`.
- Tail regex (`is_tail_regex` checks the last segment) requires `path_segments_len >= route_segments_len - 1`, capturing the joined remainder into the named param.
- Non-tail regex segments must match the entire one segment (`mat.start() == 0 && mat.end() == segment.len()`), so `/api/{v:\d+}/users` is anchored per-segment.

## Hooks (`src/hook/`)

`HookType` is the unified registration enum from `src/hook/enum.rs`:

```rust
#[derive(Clone, Copy, Debug, DisplayDebug, Eq, PartialEq, Hash)]
pub enum HookType {
    TaskPanic(Option<isize>, ServerHookHandlerFactory),
    RequestError(Option<isize>, ServerHookHandlerFactory),
    RequestMiddleware(Option<isize>, ServerHookHandlerFactory),
    Route(&'static str, ServerHookHandlerFactory),                              // path string must be &'static
    ResponseMiddleware(Option<isize>, ServerHookHandlerFactory),
}

impl HookType {
    pub fn try_get_order(&self) -> Option<isize>           // only meaningful for the 4 non-Route variants
    pub fn try_get_hook(&self) -> Option<ServerHookHandlerFactory>
    pub fn assert_unique_order(list: Vec<HookType>)        // panics on duplicate (HookType, order) pair
}
```

`Option<isize>` is the execution priority — higher runs first. `None` means "default order 0" and is **excluded from the uniqueness check**; only hooks with explicit `order = Some(isize)` are deduped. `HookType` has its own `Hash`/`Eq` that compares function pointers via `std::ptr::fn_addr_eq` (important for inventory-keyed hashtables).

### Trait hierarchy (`src/hook/trait.rs`)

```rust
pub trait FutureSend<T>: Future<Output = T> + Send
pub trait FutureSendStatic<T>: FutureSend<T> + 'static
pub trait FnContext<R>:    Fn(&mut Context) -> R + Send + Sync
pub trait FnContextPinBox<T>: FnContext<FutureBox<T>>
pub trait FnContextStatic<Fut, T>: FnContext<Fut> + 'static where Fut: Future<Output = T> + Send
pub trait FutureFn<T>:     Fn() -> FutureBox<T> + Send + Sync

pub trait ServerHook: Send + Sync + 'static {
    fn new(stream: &mut Stream, ctx: &mut Context) -> impl Future<Output = Self> + Send;
    fn handle(self, stream: &mut Stream, ctx: &mut Context) -> impl Future<Output = Status> + Send;
}
```

`ServerHook` is a two-phase trait: `new` initialises from the `Context`/`Stream` pair, then `handle(self, ...)` consumes `self` and runs the request logic returning `Status`. `status::Status::default() == Reject` (continue is `Continue`). To abort the pipeline early (skip the route handler, e.g. for short-circuit middleware), the handler must return `Status::Reject` and write a response before returning.

`Hook::factory::<T>()` (defined in `src/hook/impl.rs`) builds a `ServerHookHandler` that internally awaits `T::new(stream, ctx)` then `handle(stream, ctx)`. The `stream + ctx` round-trip through `usize` address is necessary because the future returned by `handle` is `'static + Send`.

### Type aliases (`src/hook/type.rs`)

```rust
pub type HookHandler<T> = Arc<dyn FnContextPinBox<T>>;
pub type HookHandlerChain<T> = Vec<HookHandler<T>>;
pub type FutureBox<T> = Pin<Box<dyn Future<Output = T> + Send>>;
pub type ServerControlHookHandler<T> = Arc<dyn FutureFn<T>>;
pub type ServerHookHandlerFactory   = fn() -> ServerHookHandler;
pub type ServerHookHandler          =
    Arc<dyn Fn(&mut Stream, &mut Context) -> FutureBox<Status> + Send + Sync>;
pub type ServerHookList             = Vec<ServerHookHandler>;
pub type ServerHookMap              = HashMapXxHash3_64<String, ServerHookHandler>;
pub type ServerHookPatternRoute     = HashMapXxHash3_64<usize, Vec<(RoutePattern, ServerHookHandler)>>;
```

Note that `ServerHookHandler` takes **two arguments**: `&mut Stream` and `&mut Context` (not just `Context`). `Status` is the `http_type::status::Status` enum (`Continue` / `Reject`).

### `DefaultServerHook` and `Hook`

```rust
#[derive(... Default ...)]
pub struct DefaultServerHook;        // zero-size Copy; provides no-op hooks
#[derive(... Default ...)]
pub struct Hook;                     // zero-size Copy namespace of factory utilities

impl ServerHook for DefaultServerHook {
    async fn new(_, _) -> Self { Self }
    async fn handle(self, _, _) -> Status { Status::default() }   // returns Reject (default)
}

impl Hook {
    pub fn default_control_handler() -> ServerControlHookHandler<()>
    pub fn default_handler()         -> ServerHookHandler            // Status::default closure
    pub fn factory<R: ServerHook>()  -> ServerHookHandler
}
```

`Handle_router!` sugar from `hyperlane-macros` (`#[route(...)]`, `#[request_middleware(...)]`, etc.) all internally call `Hook::factory::<MyHandler>()`.

## `ServerControlHook` (`src/hook/struct.rs`)

Returned from `Server::run().await`:

```rust
#[derive(Clone, CustomDebug, DisplayDebug, Getter, Setter)]
pub struct ServerControlHook {
    #[set(pub(crate))] pub(super) wait_hook:     ServerControlHookHandler<()>,
    #[set(pub(crate))] pub(super) shutdown_hook: ServerControlHookHandler<()>,
}

impl Default for ServerControlHook {
    fn default() -> Self { ... both hooks are no-op `Hook::default_control_handler()` ... }
}

impl ServerControlHook {
    pub async fn wait(&self)               // awaits the wait_hook future
    pub async fn shutdown(&self)           // invokes the shutdown_hook future (sends a `tokio::sync::watch` signal that aborts the accept loop)
}
```

Usage:

```rust
let control: ServerControlHook = server.run().await.unwrap();
tokio::spawn(async move { control.wait().await; /* server is now done */ });
// on Ctrl-C:
control.shutdown().await;     // aborts the spawned accept_connections JoinHandle
```

## `Status`, `Stream`, `RequestError`

These all come from `http_type::*` and are used directly. Hyperlane does NOT re-export them by name separately — they're part of the `http_type::*` glob.

`Status` (in `http_type::status::Status`):

```rust
#[derive(Clone, Copy, Debug, Default, Deserialize, Eq, PartialEq, Serialize)]
pub enum Status {
    Continue,
    #[default]
    Reject,                       // default — short-circuits the pipeline
}
```

`Stream` (in `http_type::stream::Stream`): wraps a `TcpStream`, holds the `RequestConfig`, and is responsible for parsing the next `Request` from the wire (`try_get_http_request()`, `try_get_websocket_request()`), buffering, timeouts, and keep-alive tracking (`is_keep_alive`, `set_closed`). Constructed internally by `handle_connection`; user code normally interacts with it only as the first arg to `ServerHook::new/handle` and via the `Stream` passed alongside `&mut Context`.

`RequestError` (in `http_type::request::RequestError`) has 41 variants, all of shape `VariantName(HttpStatus)` except `Request(String)` for custom messages. Most relevant variants: `HttpRead`, `GetTcpStream`, `ReadConnection`, `RequestAborted`, `MaxRedirectTimes`, `MethodsNotSupport`, `ClientDisconnected`, `IncompleteWebSocketFrame`, `RequestTooLong`, `PathTooLong`, `QueryTooLong`, `HeaderLineTooLong`, `TooManyHeaders`, `HeaderKeyTooLong`, `HeaderValueTooLong`, `ContentLengthTooLarge`, `InvalidContentLength`, `InvalidUrl*`, `ReadTimeout`, `WriteTimeout`, `TcpConnectionFailed`, `TlsHandshakeFailed`, `WebSocketFrameTooLarge`, `WebSocketOpcodeUnsupported`, `WebSocketMaskMissing`, `WebSocketPayloadCorrupted`, `WebSocketInvalidUtf8`, `WebSocketInvalidCloseCode`, `WebSocketInvalidExtension`, `HttpRequestPartsInsufficient`, `ConfigReadError`, `Unknown`. Default is `RequestError::Unknown(HttpStatus::InternalServerError)`. Convertible from `std::io::Error` (mapping `ConnectionReset`/`ConnectionAborted` to `ClientDisconnected(BadRequest)`, rest to `ReadConnection(BadRequest)`) and from `tokio::time::error::Elapsed` (mapping to `ReadTimeout(RequestTimeout)`).

## Errors (`src/error/enum.rs`)

```rust
#[derive(Clone, CustomDebug, Deserialize, DisplayDebug, Eq, PartialEq, Serialize)]
pub enum ServerError {
    TcpBind(String),
    Unknown(String),
    HttpRead(String),
    InvalidHttpRequest(Request),     // carries the malformed Request to be inspected
    Other(String),
}

#[derive(Clone, CustomDebug, Deserialize, DisplayDebug, Eq, PartialEq, Serialize)]
pub enum RouteError {
    EmptyPattern,                                      // route::<T>("") panics
    DuplicatePattern(String),                          // same path registered twice
    InvalidRegexPattern(String),                       // {name:bad-regex}
}
```

`Server::run` returns `Result<ServerControlHook, ServerError>`. `RouteError` is what `RouteMatcher::add(...)` panics with via `.unwrap()`.

## Flush helpers (`src/server/impl.rs`)

`Server` also re-exports these as **associated functions** (no `&self`):

```rust
Server::format_bind_address<H: AsRef<str>>(host: H, port: u16) -> String
Server::try_flush_stdout() -> io::Result<()>
Server::flush_stdout()
Server::try_flush_stderr() -> io::Result<()>
Server::flush_stderr()
Server::try_flush_stdout_and_stderr() -> io::Result<()>
Server::flush_stdout_and_stderr()
```

`Server::handle_request_error(stream, ctx, error)` is the public method invoked by `handle_connection` when the request parse fails — it sets `RequestErrorData` on the context, marks the stream non-closed, and runs the `request_error::<T>` hook chain until one returns `Reject`.

## Request/Response body and headers

`hyperlane` re-exports `http_type::*`, so `Request`, `Response`, `Method`, `HttpVersion`, `Cookie`, `HttpUrl`, etc. all come via that glob (see `http-type` skill for full listings). The concrete `set_response_body`, `set_response_header`, `get_request_*` calls on `Context` are **async** because the underlying buffers may not be fully read until the connection phase completes — always `.await` them:

```rust
async fn json_echo(_: &mut Stream, ctx: &mut Context) {
    let body: String = ctx.get_request_body().await;
    ctx.set_response_body(body).await;
    ctx.set_response_status_code(200).await;
    ctx.set_response_header("Content-Type", "application/json").await;
    Status::Continue
}
```

## Plugin / WebSocket / SSE

Hyperlane itself is HTTP + middleware + hooks. WebSocket and SSE come from sibling crates registered through `inventory`:

```toml
# Cargo.toml
hyperlane                 = "21"
hyperlane-plugin-websocket = "..."
hyperlane-broadcast        = "..."   # SSE helper
```

The plugins self-register via `inventory::submit!` macros on `static` items (or use `#[plugin_websocket]` style helpers), so once linked into the binary, the framework finds them statically. See `hyperlane-plugin-websocket/SKILL.md` and `hyperlane-broadcast/SKILL.md` for the registration payloads.

## Async/Sync split quick reference

| Method                                                                                                    | Sync/Async                                               | Notes                                   |
| --------------------------------------------------------------------------------------------------------- | -------------------------------------------------------- | --------------------------------------- |
| `Context::set_response_body`                                                                              | **async**                                                | buffer may not be flushed yet           |
| `Context::set_response_status_code`                                                                       | **async**                                                |                                         |
| `Context::set_response_header`                                                                            | **async**                                                |                                         |
| `Context::set_response_version`                                                                           | **async**                                                |                                         |
| `Context::get_request_body`                                                                               | **async**                                                | requires connection buffer completion   |
| `Context::get_request_method/path/version`                                                                | **async**                                                |                                         |
| `Context::get_request_header`                                                                             | **async**                                                |                                         |
| `Context::get_request_query`                                                                              | **async**                                                |                                         |
| `Context::try_get_route_param` / `get_route_param`                                                        | sync                                                     |                                         |
| `Context::set_attribute` / `get_attribute` / `try_get_attribute` / `remove_attribute` / `clear_attribute` | sync                                                     |                                         |
| `Context::try_get_task_panic_data` / `get_task_panic_data`                                                | sync                                                     |                                         |
| `Context::try_get_request_error_data` / `get_request_error_data`                                          | sync                                                     |                                         |
| `Context::set_task_panic`                                                                                 | sync                                                     |                                         |
| `Server::run`                                                                                             | async (consumes internally via `unsafe { self.leak() }`) | spawns a tokio task for the accept loop |
| `ServerHook::new` / `handle`                                                                              | async                                                    | `impl Future + Send`                    |
| `ServerControlHook::wait` / `shutdown`                                                                    | async                                                    |                                         |

## Common pitfalls

1. **`Server::route<S>` is turbofish-only** — `S` is a type marker for `ServerHook`, not the path. `route("/")` is shorthand but reads as `route::<()>(...)` if you don't turbofish. Always write `route::<Index>("/")` for `impl ServerHook for Index`.
2. **Route pattern `{name}` vs `{name:regex}`** — bare `{name}` matches one segment, `{name:.*}` matches multi-segment tail. The regex must compile; invalid regex yields `InvalidRegexPattern` and a panic.
3. **Duplicate route registration panics** with `DuplicatePattern`; empty pattern panics with `EmptyPattern`; invalid regex panics with `InvalidRegexPattern`. All three are runtime panics — there is no compile-time check.
4. **`get_route_param` panics if absent** — use `try_get_route_param` for optional params.
5. **`Context::set/get_request_*` and `set_response_*` are async** — must be `.await`ed. Sync methods are: `get/set/remove/clear_attribute`, `try_get_route_param`, panic/error-data getters/setters.
6. **`Server::run` is `&self`** — clones internally via `unsafe { self.leak() }`. After `run()` returns, the `Server` value can still be inspected for diagnostics.
7. **`HookType` priority uniqueness** — `assert_unique_order` panics only on `(same HookType variant, same Some(isize))`. `None` orders are never checked. Default fluent helpers (`task_panic::<T>` etc.) never call `assert_unique_order` — only explicit `handle_hook(HookType::RequestMiddleware(Some(0), factory))` triggers it.
8. **`inventory` is required for WebSocket / SSE plugins** — they self-register at static-init time. If you see "no websocket plugins found", check that the plugin crate is in `[dependencies]` (not just `dev-dependencies`).
9. **`tokio::main` flavor** — hyperlane uses `#[tokio::main]` with default features; multi-threaded runtime is fine. Single-threaded runtime works but spawned `task_handler`s need `Send + 'static` futures which all the framework helpers satisfy.
10. **Body buffering** — large request bodies are streamed via `http_type` buffer config; tune `RequestConfig` (`max_body_size`, `read_timeout_ms`) if you expect multi-MB uploads.
11. **`Status::default() == Reject`** — middleware/macros that forget to return `Status::Continue` abort the pipeline silently. Always explicit `Status::Continue` at the end of `handle`.
12. **Don't reuse `Context`/`Stream` across requests** — they're owned per request via the `Box::leak → usize address → Box::from_raw` cycle. Cloning a `Context` (`#[derive(Clone)]`) is OK but doesn't share state across requests.
13. **`ServerHookHandler` is two-arg** — `Arc<dyn Fn(&mut Stream, &mut Context) -> FutureBox<Status>>`. If you write your own factory, both `&mut Stream` and `&mut Context` matter.

## Verification checklist

- [ ] `cargo check -p hyperlane` exits 0
- [ ] `cargo test -p hyperlane` passes `route::*` and `config::server_config_from_json`
- [ ] `cargo clippy --all-targets -p hyperlane` 0 warnings
- [ ] Smoke test: `curl http://127.0.0.1:80/` returns 200 with expected body
- [ ] Panic test: register a handler that `panic!()` and verify the `task_panic::<T>` hook fires (no process abort)
- [ ] Request-error test: malformed request → `request_error::<T>` hook fires with `RequestError` data set
- [ ] WebSocket / SSE plugin: if using, verify `inventory` collection picks up plugin at startup (log line or `Server::run` does not hang)
- [ ] `cargo doc -p hyperlane --no-deps` builds without broken-link warnings

## Source-of-truth files

- `src/lib.rs` — top-level module declarations + `pub use`
- `src/server/{struct,impl}.rs` — `Server` builder + `Default`/`PartialEq`/`From<usize>`/`From<ServerConfig>`/`From<RequestConfig>` + `run()` main loop + flush helpers
- `src/config/{struct,impl,mod}.rs` — `ServerConfig` (JSON / setter-based) and `RequestConfig` (parse safety limits)
- `src/context/{struct,impl,mod}.rs` — `Context` request/response + attributes + panic data
- `src/route/{struct,enum,type,impl,mod}.rs` — `RoutePattern`, `RouteMatcher`, `RouteSegment`, `RoutePattern::try_match_path` (regex/dynamic matching)
- `src/hook/{enum,struct,trait,type,impl,mod}.rs` — `HookType`, `ServerControlHook`, `Hook`, `DefaultServerHook`, all traits + aliases, `Hook::factory`
- `src/error/{enum,impl,mod}.rs` — `ServerError`, `RouteError`
- `tests/{route,config,context,error,server,cli}/fn.rs` — routing behavior (`empty_route`, `duplicate_route`, `get_route`, `segment_count_optimization`, `regex_route_segment_count`, `mixed_route_types`) and JSON round-trip

## Related skills

- `hyperlane-macros` — `#[route]`, `#[request_middleware]`, `#[response_middleware]`, `#[task_panic]`, `#[request_error]`, plus 73 other attribute macros that wrap `Hook::factory::<T>()` invocations
- `hyperlane-quick-start` — full-stack example app (HTTP + WebSocket + SSE + middleware + DB + JWT)
- `hyperlane-broadcast` — SSE / event-stream broadcast helper
- `hyperlane-plugin-websocket` — WebSocket plugin registration
- `hyperlane-log` — async logging helpers
- `hyperlane-cli` — `hyperlane-cli` companion CLI
- `lombok-macros` — `Data`/`New`/`Getter`/`GetterMut`/`Setter`/`CustomDebug`/`DisplayDebug` derives used throughout `hyperlane` + `http_type` structs
- `http-constant` — HTTP method / status / header constants (re-exported by `http_type::*` and thus visible via `hyperlane::*`)
- `http-compress`, `http-request`, `http-type` — sibling crates in the hyperlane ecosystem
