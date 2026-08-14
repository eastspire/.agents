---
name: hyperlane
description: 'A lightweight, high-performance, cross-platform Rust HTTP server library built on Tokio. Use when building Rust HTTP services with static/dynamic/regex routes, request/response middleware, task-panic and request-error hooks, raw TCP streams, and lifecycle control. Define `ServerHook::new` + `handle` handlers returning `Status`, register them with `Server::default().route::<T>(path)`, `task_panic::<T>()`, `request_error::<T>()`, `request_middleware::<T>()`, or `response_middleware::<T>()`, and use `Context` for request/response/route params/attributes/error data. Triggers: hyperlane, Server::default, ServerHook, ServerControlHook, HookType, RoutePattern, RouteSegment, RouteParams, Context, ServerConfig, RequestConfig, Status, RequestError, ServerError, Tokio HTTP server, middleware, HTTP routing.'
license: MIT
---
# hyperlane

- GitHub: <https://github.com/hyperlane-dev/hyperlane.git>
- crates.io: <https://crates.io/crates/hyperlane>
- docs.rs: <https://docs.rs/hyperlane>

## Documentation sources (docs-pages)

The full Chinese reference for hyperlane + its companion crates lives in the [docs-pages](https://github.com/docs-pages/docs) repo (private). **This skill is the API/pitfall cheatsheet; docs-pages is the source of truth for tutorials, examples, and macro deep-dives.**

To read a topic, use the local mirror — no network or PAT needed. Pages are vendored flat (one file per topic) under `references/`:

- `read_file('references/websocket.md')` — WebSocket setup
- `read_file('references/auth.md')` — auth middleware
- `read_file('references/hyperlane-macros-request.md')` — request-extraction macros
- `read_file('references/hyperlane-plugin-websocket.md')` — plugin-websocket overview
- `read_file('references/hyperlane-broadcast.md')` — broadcast bus overview
- `read_file('references/route.md')` — routing patterns + examples (manual override — has an extra dynamic-routing section on top of upstream)
- …and any other `references/<topic>.md` in this skill

To refresh `references/` after docs-pages updates, run the sync script from the repo root:

```shell
bash scripts/sync-references.sh                       # full sync (clones docs-pages)
bash scripts/sync-references.sh --source-dir <path>   # reuse an existing clone
bash scripts/verify-references.sh                     # show what changed vs HEAD
```

The mapping of `references/<file>.md` → `docs-pages/src/...` lives in `scripts/sync-references.mapping`. To add a new file, append a line; to pin a customized version, add `# manual override:` to its line and the script will leave that dest alone. See `scripts/README.md` for the full workflow.


## Overview

Hyperlane is a Tokio-based HTTP server library at version `21.3.6` (edition 2024, `panic = "unwind"`) that exposes a fluent builder for assembling:

- routes (static, dynamic `{name}`, regex `{name:pattern}`)
- request middleware (chain executed before route handler)
- response middleware (chain executed after route handler)
- task-panic hooks (recovery / logging)
- request-error hooks (404 / 405 / panics with response shaping)

It re-exports `http_type::*` (request/response types) and the `inventory` plugin-registration crate. The published crate itself depends on `http-type = "20.1.9"`, `inventory = "0.3.24"`, `lombok-macros = "2.0.36"`, and `serde = "1.0.229"`. WebSocket and SSE support is provided by separate companion crates, not by dependencies declared in this `Cargo.toml`.

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

Plugin self-registration: `inventory::collect!(HookType);` is invoked in `src/route/impl.rs`. This crate exposes the registry type, while any external macro/plugin crate must arrange its own `inventory::submit!` entries; `hyperlane` itself has no `hyperlane-macros` dependency.

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
http-type = "20.1.9"
inventory = "0.3.24"
lombok-macros = "2.0.36"
serde = { version = "1.0.229", features = ["derive"] }
```

## Quick start (HTTP-only, trait-style)

Minimal `main.rs` pattern. The official companion crate `hyperlane-macros` provides process/attribute macros (`#[route]`, `#[hyperlane]`, `#[task_panic]`, `#[request_error]`, `#[request_middleware]`, `#[response_middleware]`, `#[prologue_macros]`, `#[epilogue_macros]`, `context!`, etc.) and is the recommended way to write routes/hooks. Examples below import both `use hyperlane::*;` and `use hyperlane_macros::*;`. The fluent `Server::route::<T>()` etc. registration methods are now `async` and each call must be `.await`ed individually (no chaining). Response setters are **sync** and live on `ctx.get_mut_response()`.

```rust
use hyperlane::*;
use hyperlane_macros::*;

struct FrontHtml;

impl ServerHook for FrontHtml {
    async fn new(_: &mut Stream, _: &mut Context) -> Self { Self }
    async fn handle(self, _: &mut Stream, ctx: &mut Context) -> Status {
        let data: Vec<u8> = ctx
            .get_mut_response()
            .set_version(HttpVersion::Http1_1)
            .set_status_code(200)
            .set_header("Content-Type", "text/html; charset=utf-8")
            .set_body("hello world")
            .build();
        Status::Continue
    }
}

struct NotFound;

impl ServerHook for NotFound {
    async fn new(_: &mut Stream, _: &mut Context) -> Self { Self }
    async fn handle(self, _: &mut Stream, ctx: &mut Context) -> Status {
        let _: Vec<u8> = ctx
            .get_mut_response()
            .set_status_code(404)
            .set_body("404 not found")
            .build();
        Status::Continue
    }
}

struct PanicHandler;

impl ServerHook for PanicHandler {
    async fn new(_: &mut Stream, _: &mut Context) -> Self { Self }
    async fn handle(self, _: &mut Stream, _: &mut Context) -> Status { Status::Continue }
}

#[tokio::main]
async fn main() {
    // ServerConfig setter is sync; assign separately (no chaining).
    let mut config: ServerConfig = ServerConfig::default();
    config.set_address("0.0.0.0:80".to_owned());

    // Server builder registration: each method is async, no chaining.
    let mut server: Server = Server::default();
    server.server_config(config);            // sync config setter
    server.route::<FrontHtml>("/").await;
    server.route::<NotFound>("/*").await;
    server.task_panic::<PanicHandler>().await;
    server.request_middleware::<FrontHtml>().await;
    server.response_middleware::<FrontHtml>().await;

    // run() returns Result; ServerControlHook has Default, so unwrap_or_default is the recommended fallback.
    let control: ServerControlHook = server.run().await.unwrap_or_default();
    control.wait().await;
}
```

## `Server` builder API

From `src/server/{struct,impl}.rs`. All `route::<T>`, `task_panic::<T>`, `request_error::<T>`, `request_middleware::<T>`, `response_middleware::<T>` methods take a **type marker** `S` (only used at compile time to monomorphize the `ServerHookHandlerFactory`) — they are turbofish-only, no runtime value comes from `S`. Each registration method is `async` and must be `.await`ed individually; `Server` must be declared `let mut server: Server = Server::default();` and methods are called as separate statements (no fluent chaining). `server_config` / `request_config` / `config_from_json` are **sync** setters (no `.await`).

```rust
impl Server {
    // Hook dispatcher (rarely called directly):
    pub fn handle_hook(&mut self, hook: HookType)            // dispatches by HookType variant

    // Configuration (all SYNC — no .await):
    pub fn config_from_json<C: AsRef<str>>(&mut self, json: C) -> &mut Self
    pub fn server_config(&mut self, config: ServerConfig) -> &mut Self
    pub fn request_config(&mut self, config: RequestConfig) -> &mut Self

    // Registration (all ASYNC, no chaining — call as separate statements on a `let mut server`):
    pub async fn route<S>(&mut self, path: impl AsRef<str>) -> &mut Self where S: ServerHook
    pub async fn task_panic<S>(&mut self) -> &mut Self             where S: ServerHook
    pub async fn request_error<S>(&mut self) -> &mut Self          where S: ServerHook
    pub async fn request_middleware<S>(&mut self) -> &mut Self     where S: ServerHook
    pub async fn response_middleware<S>(&mut self) -> &mut Self    where S: ServerHook

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

- `Server::run` requires `let mut server` because registration methods above take `&mut self`. `run` itself returns `Result<ServerControlHook, ServerError>` — the recommended idiom is `server.run().await.unwrap_or_default()` (not `.unwrap()`) since `ServerControlHook: Default`. The `Server` instance is effectively consumed by the accept loop after `run` returns; use `server_control_hook.wait().await` to block or `shutdown().await` to abort.
- `route::<T>(path).await` calls `RouteMatcher::add(...)` which `unwrap()`s — empty pattern panics with `RouteError::EmptyPattern`, duplicate pattern panics with `RouteError::DuplicatePattern(String)`, invalid regex pattern returns `RouteError::InvalidRegexPattern(String)` (also unwrapped → panic).
- `task_panic::<T>` / `request_middleware::<T>` / `response_middleware::<T>` push into `Vec<ServerHookHandler>` which grows monotonically. With attribute macros (`#[route(...)]` + `#[hyperlane(server: Server)]`) the `#[hyperlane]` macro calls `HookType::assert_unique_order` automatically; the bare fluent `server.route::<T>(path).await` form does not invoke it. Same applies for `task_panic` / `request_error` / `request_middleware` / `response_middleware`.
- Memory ownership: each accepted connection boxes a `Stream` and a `Context`, `Box::leak`s them to obtain `&'static mut`, then converts to a `usize` address that is passed through a spawn boundary; on completion the inner closures reclaim them with `Box::from_raw`. This is why `Stream` + `Context` implement `From<usize>`/`From<&mut Self> for usize` and the unsafe `Lifetime::leak/leak_mut`. **Do not allocate `Stream` / `Context` yourself and submit them via `From<usize>` from outside the accept loop** — the framework expects exclusive ownership per request.

## `ServerConfig` and `RequestConfig`

- `ServerConfig::from_json` returns `Result<Self, serde_json::Error>`; `Server::config_from_json` parses with `serde_json::from_str(...).unwrap()` and therefore panics on invalid JSON. Both config types derive the lombok-style getters/setters used by the examples.

### `ServerConfig`

```rust
#[derive(Clone, CustomDebug, Data, Deserialize, DisplayDebug, Eq, New, PartialEq, Serialize)]
pub struct ServerConfig {
    #[set(type(AsRef<str>))]
    pub(super) address: String,   // bind address, e.g. "0.0.0.0:80"
    pub(super) nodelay: Option<bool>,                       // TCP_NODELAY applied per accepted socket
    pub(super) ttl: Option<u32>,                            // IP_TTL applied per accepted socket
}

let mut cfg: ServerConfig = ServerConfig::default();
cfg.set_address("0.0.0.0:80".to_owned());
cfg.set_nodelay(Some(true));
cfg.set_ttl(Some(64));
let cfg: ServerConfig = ServerConfig::from_json(r#"{"address":"0.0.0.0:80","nodelay":true,"ttl":64}"#).unwrap();
```

> [!note]
> `ServerConfig` setters are generated by `lombok-macros` and are **sync** — call each as a separate statement on a `let mut cfg`. They return `&mut Self`, but the docs-pages examples all use the standalone-statement form, not fluent chaining.

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

Two factory constructors are exposed:

- `RequestConfig::default()` / `RequestConfig::new()` — balanced defaults.
- `RequestConfig::high_security()` — stricter limits suitable for hostile environments (smaller `buffer_size`, shorter `read_timeout_ms`, lower header / path / body caps; see `config/config.md` for the per-field numbers). Use this for any production deployment that talks to untrusted clients.

## `Context`

From `src/context/{struct,impl}.rs`. Every route/middleware/hook handler receives `&mut Context` after the framework boxed+leaked+address-roundtripped it.

> [!important]
> **All request / response access goes through three entry points on `Context`:** `ctx.get_request() -> &Request`, `ctx.get_response() -> &Response`, `ctx.get_mut_response() -> &mut Response`. There are **no** direct `ctx.get_request_body()` / `ctx.set_response_body(...)` / `ctx.set_response_status_code(...)` / `ctx.set_response_header(...)` methods — those have been moved onto `Request` / `Response` and are reached only via the entry points above.

Conceptually:

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

The `hyperlane-macros` crate provides sugar like `#[request_body]` / `#[request_body_json]` / `#[response_header]` / `#[response_status_code]` / `#[prologue_macros(...)]` / `#[epilogue_macros(...)]` that translates the `set_attribute` / `try_get_attribute` calls into the response / request accessors shown below. The async/sync split after the entry-point migration:

- **Sync** (return `&T` / `&mut T` / `&mut Self` from getters; setters return `&mut Self` for fluent chaining) — all `Request` and `Response` accessors. `ctx.get_request().get_method() / get_path() / get_body() / get_body_string() / get_header(...) / get_querys() / get_version()` all return references and are sync. `ctx.get_mut_response().set_version(...) / set_status_code(...) / set_header(...) / set_body(...)` are sync and return `&mut Response`; call `.build()` on the final reference to materialise the `Vec<u8>` for `stream.try_send(...)`. Also sync: `try_get_route_param` / `get_route_param` / `get_route_params`, all `get/set/remove/clear_attribute`, `try_get_task_panic_data` / `get_task_panic_data`, `try_get_request_error_data` / `get_request_error_data`, `set_task_panic`.
- **Async** — `stream.send / try_send / send_list / try_send_list / flush / try_flush` (network I/O), `Server::run` (consumes the `Server` value to start the accept loop), and the `#[try_get_http_request]` / `#[try_get_websocket_request]` / `#[try_send]` / `#[send]` / `#[try_flush]` / `#[flush]` macros that wrap those stream methods.

```rust
async fn get_user(ctx: &mut Context) -> Status {
    let id: String = ctx.get_route_param("id");
    // Read request via ctx.get_request() (all sync):
    let body: String = ctx.get_request().get_body_string();
    // Write response via ctx.get_mut_response() (all sync, fluent, .build() at the end):
    let data: Vec<u8> = ctx
        .get_mut_response()
        .set_status_code(200)
        .set_header("Content-Type", "text/plain")
        .set_body(format!("user id: {id}: {body}"))
        .build();
    Status::Continue
}

// registered via: server.route::<get_user>("/users/{id}").await;
// or:            #[route("/users/{id}")] struct GetUser;
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

Three route kinds co-exist on the same `Server`. The matcher indexes by segment count (the outer `HashMap` key) for O(1) candidate filtering, then walks matching routes in insertion order. Registration is **async + standalone** (no fluent chaining):

```rust
let mut server: Server = Server::default();
server.route::<Index>("/").await;                        // static
server.route::<About>("/about").await;                  // static
server.route::<UserDetail>("/users/{id}").await;        // dynamic single-param
server.route::<FileDetail>("/files/{path:^.*$}").await; // tail regex matches ≥ N−1 segments
server.route::<Versioned>("/api/{version:\\d+}").await;  // positional regex matches one segment
```

The official attribute-macro form is preferred (auto-collected via `inventory` and injected by `#[hyperlane(server: Server)]`):

```rust
use hyperlane::*;
use hyperlane_macros::*;

#[route("/")]                              struct Index;
#[route("/about")]                         struct About;
#[route("/users/{id}")]                    struct UserDetail;
#[route("/files/{path:^.*$}")]             struct FileDetail;
#[route("/api/{version:\\d+}")]            struct Versioned;

#[hyperlane(server: Server)]
async fn main() {
    let _: ServerControlHook = server.run().await.unwrap_or_default();
}
```

`Server::get_route_matcher()` (accessible after registration) returns `&RouteMatcher`, which exposes the three internal tables for diagnostics: `get_static_route()` (returns the `HashMap<String, ServerHookHandler>` keyed by literal path), `get_dynamic_route()` and `get_regex_route()` (both return the `HashMap<usize, Vec<(RoutePattern, ServerHookHandler)>>` indexed by segment count).

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

`Option<isize>` is the execution priority — but the direction is **counter-intuitive**: hooks with `order = None` (default; no priority specified) run **first**; hooks with `Some(isize)` run after, sorted by their integer. `HookType::assert_unique_order` is called by `#[hyperlane]` (the official init macro) automatically and panics on duplicate `(HookType variant, Some(isize))` pairs; `None` orders are still checked for duplicates when `#[hyperlane]` is the registration entry point. `HookType` has its own `Hash`/`Eq` that compares function pointers via `std::ptr::fn_addr_eq` (important for inventory-keyed hashtables).

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

`ServerHookHandler` is a two-argument `Arc` handler: `Arc<dyn Fn(&mut Stream, &mut Context) -> FutureBox<Status>>` (not just `Context`). `Status` is the `http_type::status::Status` enum (`Continue` / `Reject`).

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

`Handle_router!` sugar is not part of this crate. The recommended way for normal users to register routes/hooks is via the official `hyperlane-macros` attribute macros (`#[route(...)]`, `#[task_panic]`, `#[request_error]`, `#[request_middleware]`, `#[response_middleware]`) combined with `#[hyperlane(server: Server)]` in `main`; the macro then walks the `inventory` registry and injects the handlers into the `Server` instance, automatically calling `HookType::assert_unique_order`. The legacy fluent `Server::route::<T>(path).await` etc. also work but skip the priority-uniqueness check.

`Hook::factory::<T>()` (defined in `src/hook/impl.rs`) builds a `ServerHookHandler` that internally awaits `T::new(stream, ctx)` then `handle(stream, ctx)`. It is a **low-level API** used when writing a custom registration crate (one that submits to `inventory` directly) — ordinary application code should not call it.

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
let control: ServerControlHook = server.run().await.unwrap_or_default();
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

### Reading `RequestError` from a `request_error::<T>` hook

Inside an `impl ServerHook for RequestErrorHook` handler, the error data is read from the `Context` with the **sync** accessor `ctx.try_get_request_error_data() -> Option<RequestError>` (or `ctx.get_request_error_data() -> RequestError`, which panics on absence). `RequestError` exposes `get_http_status_code() -> ResponseStatusCode` and `to_string() -> String` for shaping the response:

```rust
async fn handle(self, _: &mut Stream, ctx: &mut Context) -> Status {
    let error: RequestError = ctx.try_get_request_error_data().unwrap_or_default();
    let _: Vec<u8> = ctx
        .get_mut_response()
        .set_status_code(error.get_http_status_code())
        .set_body(error.to_string())
        .build();
    Status::Continue
}
```

`hyperlane-macros` also exposes `#[try_get_request_error_data(error_data)]` and `#[request_error_data(error_data)]` parameter macros that auto-extract the data into a local binding.

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

`Server::handle_request_error(stream, ctx, error)` is the **internal** entry point invoked by `handle_connection` when the request parse fails — it sets `RequestErrorData` on the context, marks the stream non-closed, and runs the `request_error::<T>` hook chain until one returns `Reject`. **Application code should not call it directly**; register a `request_error` hook with `server.request_error::<MyHook>().await` or the `#[request_error]` attribute macro instead.

### Stream send / flush (the real network I/O surface)

The `Stream` passed alongside `&mut Context` is also the place where bytes are actually written. These are **async** and live on `Stream`, not `Context`:

```rust
stream.try_send(data: impl AsRef<[u8]>) -> Result<(), ResponseError>   // async
stream.send(data: impl AsRef<[u8]>) -> ()                              // async, panics on err
stream.try_send_list(frames: &[impl AsRef<[u8]>]) -> Result<(), ...>  // async
stream.send_list(frames) -> ()                                         // async, panics
stream.try_flush() -> Result<(), ResponseError>                        // async
stream.flush() -> ()                                                   // async, panics
stream.set_closed(closed: bool)                                        // sync — see pitfall
stream.is_keep_alive() -> bool                                         // sync
```

`hyperlane-macros` provides parameter-macro sugar that wraps these: `#[send]`, `#[try_send]`, `#[send_list]`, `#[try_send_list]`, `#[flush]`, `#[try_flush]`, `#[closed]`, `#[try_get_http_request]`, `#[try_get_websocket_request]`. See `references/hyperlane-macros/send-flush.md` for the full macro table.

## Request/Response body and headers

`hyperlane` re-exports `http_type::*`, so `Request`, `Response`, `Method`, `HttpVersion`, `Cookie`, `HttpUrl`, etc. all come via that glob (see `http-type` skill for full listings). All request access is via `ctx.get_request() -> &Request` (read-only); all response mutation is via `ctx.get_mut_response() -> &mut Response` which returns a fluent `&mut Response` for `set_*` chaining and ends with `.build() -> Vec<u8>`. **All of these are sync** — the `.await`/`async` semantics belong to `stream.try_send / try_flush` and `Server::run`, not to the request/response setters.

```rust
async fn json_echo(_: &mut Stream, ctx: &mut Context) -> Status {
    // Read body — three options depending on shape:
    let body_str: String = ctx.get_request().get_body_string();
    // or: let body_bytes: &RequestBody = ctx.get_request().get_body();
    // or: let body_json: T = ctx.get_request().get_body_json::<T>();   // panics on parse err
    //     let body_json: Result<T, _> = ctx.get_request().try_get_body_json::<T>();

    // Write response — all sync, fluent on the &mut Response, .build() materialises Vec<u8>:
    let body_json: &str = r#"{"echo":"ok"}"#;
    let _data: Vec<u8> = ctx
        .get_mut_response()
        .set_status_code(200)
        .set_header("Content-Type", "application/json")
        .set_body(body_json)
        .build();
    Status::Continue
}
```

The `hyperlane-macros` crate offers `#[request_body]`, `#[request_body_json]`, `#[response_header]`, `#[response_status_code]`, `#[response_body]`, `#[response_version]` and the `#[prologue_macros(...)]` / `#[epilogue_macros(...)]` composite macros as sugar over the same accessors — see `references/hyperlane-macros/response.md` and `request.md`.

## Plugin / WebSocket / SSE

WebSocket and SSE are **first-class citizens of the `hyperlane` main crate** — no separate plugin crate is required to host them:

- WebSocket: detect via `ctx.get_request().is_ws_upgrade_type()` (or the `#[is_ws_upgrade_type]` parameter macro), frame and send via `stream.try_send_list(...)` / `stream.send_list(...)` plus `WebSocketFrame::create_frame_list(...)`. `Stream::try_get_websocket_request()` is the async handshake extractor; the `#[try_get_websocket_request(frame_data)]` parameter macro wraps it.
- SSE: just `stream.try_send(&frame)` on a keep-alive stream. No special protocol helper is needed.

The two optional companion crates are **purely additive**:

```toml
# Cargo.toml (all optional — main crate works without them)
hyperlane                 = "..."
hyperlane-broadcast        = "..."   # SSE / event-stream broadcast bus (websocket docs reference it)
hyperlane-plugin-websocket = "..."   # pre-built WebSocket route glue (use only if you want the default frames helper)
hyperlane-utils            = "..."   # frequently-included utilities (cookie, broadcast, etc.)
hyperlane-time             = "..."   # time helpers
hyperlane-log              = "..."   # async logging
```

Anything you can do with the optional crates you can also do directly with `Stream` + `ctx.get_request()` + `WebSocketFrame`. Add them only if their concrete helpers save you real code.

## Async/Sync split quick reference

> **Last verified against docs-pages main branch.** After the `Context` / `Request` / `Response` split, the old `ctx.set_response_*` / `ctx.get_request_*` direct methods are gone — response / request accessors all live on `Request` / `Response` reached via `ctx.get_request() / get_response() / get_mut_response()`. Network I/O on `Stream` is the main async surface.

| Method / family | Sync/Async | Notes |
| --- | --- | --- |
| `ctx.get_request() -> &Request` | sync | the only entry to read-side data |
| `ctx.get_response() -> &Response` | sync | read-only view of the response |
| `ctx.get_mut_response() -> &mut Response` | sync | the only entry to write-side data; ends with `.build() -> Vec<u8>` |
| `Request::get_method / get_path / get_host / get_version / get_querys / get_body / get_body_string / get_body_json / get_header / get_headers / get_query / has_header / is_ws_upgrade_type` | sync | all return references / values, no `.await` |
| `Response::set_version / set_status_code / set_reason_phrase / set_header / add_header / set_body / remove_header / remove_header_value / clear_headers` | sync | fluent on `&mut Response`; `set_response(Response::default())` replaces wholesale |
| `Response::build() -> Vec<u8>` | sync | materialise the wire bytes; pass to `stream.try_send(data).await` |
| `Response::get_body / get_body_string / try_get_body_json / get_body_json` | sync | reading back a response body |
| `ctx.try_get_route_param / get_route_param / get_route_params` | sync | `HashMap` lookup against pattern captures |
| `ctx.{get, set, try_get, remove, clear}_attribute` | sync | generic key/value bag on `Context` |
| `ctx.try_get_task_panic_data / get_task_panic_data` | sync | read by the `task_panic::<T>` hook |
| `ctx.try_get_request_error_data / get_request_error_data` | sync | read by the `request_error::<T>` hook |
| `ctx.set_task_panic` | sync | framework-only; users don't call this |
| `Stream::set_closed / is_keep_alive / try_get_http_request / try_get_websocket_request` (return `Result`) | async (the `try_get_*` pair) / sync (the flag ones) | network I/O on the accept side |
| `Stream::send / try_send / send_list / try_send_list / flush / try_flush` | **async** | main network write surface; `try_*` returns `Result<(), ResponseError>`, plain version panics |
| `Server::route / task_panic / request_error / request_middleware / response_middleware` | **async** | each is a separate `.await`ed statement on `let mut server` |
| `Server::server_config / request_config / config_from_json / format_bind_address` | sync | no `.await` |
| `Server::run` | **async** | returns `Result<ServerControlHook, ServerError>`; use `.unwrap_or_default()` |
| `ServerHook::new / handle` | async | `impl Future + Send` |
| `ServerControlHook::wait / shutdown` | **async** | wait blocks; shutdown triggers a `tokio::sync::watch` abort signal |
| `Server::{try_,}flush_stdout / flush_stderr / flush_stdout_and_stderr` | sync (associated fns) | for the parent process stdout, not the wire stream |
| `#[try_get_*]`, `#[try_send]`, `#[try_flush]`, `#[send]`, `#[flush]`, `#[closed]`, `#[is_get_method]`, `#[methods(get, post)]`, `#[is_http1_1_version]`, `#[is_ws_upgrade_type]` (proc-macro sugar) | async / sync depending on what they wrap | `hyperlane-macros` parameter / attribute macros; see `references/hyperlane-macros/` for the per-macro sync/async classification |

## Common pitfalls

1. **`Server::route<S>` is turbofish-only** — `S` is a type marker for `ServerHook`, not the path. Always write `route::<Index>("/")` for `impl ServerHook for Index`. The `route` method is `async` and must be `.await`ed as a standalone statement on a `let mut server`.
2. **Route pattern `{name}` vs `{name:regex}`** — bare `{name}` matches one segment, `{name:.*}` matches multi-segment tail. The regex must compile; invalid regex yields `InvalidRegexPattern` and a panic.
3. **Duplicate route registration panics** with `DuplicatePattern`; empty pattern panics with `EmptyPattern`; invalid regex panics with `InvalidRegexPattern`. All three are runtime panics — there is no compile-time check.
4. **`get_route_param` panics if absent** — use `try_get_route_param` for optional params.
5. **`Context` has no direct `set_response_*` / `get_request_*` methods** — request access is `ctx.get_request().get_*()` and response mutation is `ctx.get_mut_response().set_*(...).build() -> Vec<u8>`. All of these are **sync**. The genuinely **async** surface is `stream.send / try_send / send_list / try_send_list / flush / try_flush` (network I/O), `Server::run` / `server.route::<T>(path).await` / etc. (registration), `ServerControlHook::wait / shutdown` (control), and the `#[try_send]` / `#[try_flush]` / `#[try_get_*]` proc-macro wrappers.
6. **`Server::run` returns `Result<ServerControlHook, ServerError>`** — use `server.run().await.unwrap_or_default()` (not `.unwrap()`); `ServerControlHook: Default`, so the no-op fallback is well-defined. After `run`, drive the accept loop with `control.wait().await` or terminate it with `control.shutdown().await`.
7. **`HookType` priority order is counter-intuitive** — hooks with `order = None` (no priority specified) run **first**; hooks with `Some(isize)` run after, sorted by their integer. `#[hyperlane(server: Server)]` calls `HookType::assert_unique_order` automatically and panics on duplicate `(HookType variant, Some(isize))` pairs. The bare fluent `server.route::<T>(path).await` form does **not** invoke the uniqueness check.
8. **`inventory` is the registry mechanism for the `#[route]` / `#[task_panic]` / `#[request_error]` / `#[request_middleware]` / `#[response_middleware]` attribute macros** — the `hyperlane` crate declares `inventory::collect!(HookType)`; the `hyperlane-macros` crate emits the `inventory::submit!` payloads that the `#[hyperlane]` macro then walks. You only need to know `inventory` exists if you write a custom registration crate.
9. **`tokio::main` flavor** — hyperlane uses `#[tokio::main]` with default features; multi-threaded runtime is fine. Single-threaded runtime works but spawned `task_handler`s need `Send + 'static` futures which all the framework helpers satisfy.
10. **Body buffering** — large request bodies are streamed via `http_type` buffer config; tune `RequestConfig` (`max_body_size`, `read_timeout_ms`) if you expect multi-MB uploads, or start from `RequestConfig::high_security()` for hostile environments.
11. **`Status::default() == Reject`** — middleware/macros that forget to return `Status::Continue` abort the pipeline silently. Always explicit `Status::Continue` at the end of `handle`.
12. **Don't reuse `Context`/`Stream` across requests** — they're owned per request via the `Box::leak → usize address → Box::from_raw` cycle. `Context: Clone` exists but cloning does not share state across requests. If you must hand a `Context` reference to another task/thread, use `Context::clone` (the explicit `async.md` API) — passing the leaked address across an arbitrary thread boundary is unsafe.
13. **`ServerHookHandler` is two-arg** — `Arc<dyn Fn(&mut Stream, &mut Context) -> FutureBox<Status>>`. If you write your own factory (`Hook::factory::<T>()`), both `&mut Stream` and `&mut Context` matter.
14. **`Server::format_bind_address(host, port)`** returns a `String` suitable for `ServerConfig::set_address(...)`; use it instead of hand-formatting `"{host}:{port}"` so the formatting stays consistent across `multi-server.md` examples.
15. **`request_body` / `request_body_json` / `response_header` macro syntax** has two forms — `KEY => VALUE` and `KEY, VALUE` are both accepted; `response_header` uses `KEY => VALUE` (see `references/hyperlane-macros/response.md`).
16. **`#[methods(get, post)]`** is the correct multi-method filter syntax (a comma-separated list inside the macro, **not** `methods = "get,post"`). Same family: `#[is_get_method]`, `#[is_post_method]`, `#[is_http1_1_version]`, `#[is_ws_upgrade_type]`, `#[host("example.com")]`, `#[referer("...")]`, `#[reject_host(...)]`, `#[reject_referer(...)]`, `#[filter(...)]`, `#[reject(...)]`.
17. **`#[prologue_macros(...)]` and `#[epilogue_macros(...)]` order matters** — the **first** macro inside `prologue_macros` is the **outermost** wrapper; the **last** macro inside `epilogue_macros` is the **outermost** wrapper. Reversing the order changes the order in which the response / request are processed.
18. **`Stream::set_closed(true)` does not terminate the current request lifetime** — it just stops the framework from sending further responses on that stream. Returning `Status::Reject` from your handler is what actually short-circuits the pipeline.
19. **`Server` registration methods are now standalone, not chainable** — every `server.route::<T>(path).await` / `server.task_panic::<T>().await` / `server.request_middleware::<T>().await` / `server.response_middleware::<T>().await` / `server.request_error::<T>().await` is a separate statement; mixing the old `server.route::<A>("/a").route::<B>("/b")` form will not compile. `server_config` / `request_config` / `config_from_json` remain **sync** (no `.await`) and may be called either standalone or chained (they return `&mut Self`).

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

- `hyperlane-macros` — **official companion crate** that ships the process/attribute/composite macros used in modern hyperlane code: `#[route]`, `#[task_panic]`, `#[request_error]`, `#[request_middleware]`, `#[response_middleware]`, `#[hyperlane]`, `#[hyperlane_init]`, `#[methods]`, `#[host]` / `#[referer]` / `#[reject_host]` / `#[reject_referer]`, `#[filter]` / `#[reject]`, `#[is_get_method]` / `#[is_post_method]` / `#[is_http_version]` / `#[is_ws_upgrade_type]`, plus the `prologue_macros` / `epilogue_macros` / `prologue_hooks` / `epilogue_hooks` / `context!` composite / function macros. **Not optional for attribute-macro code**; this is what `use hyperlane_macros::*;` imports.
- `hyperlane-quick-start` — full-stack example app (HTTP + WebSocket + SSE + middleware + DB + JWT)
- `hyperlane-broadcast` — SSE / event-stream broadcast helper (SSE pub/sub bus)
- `hyperlane-plugin-websocket` — pre-built WebSocket route glue (optional convenience wrapper; main crate can host WebSocket directly)
- `hyperlane-log` — async logging helpers
- `hyperlane-cli` — `hyperlane-cli` companion CLI
- `hyperlane-utils` — frequently-included utility crate (cookies, broadcast, etc.) used by `hyperlane-broadcast` and `hyperlane-plugin-websocket`
- `hyperlane-time` — time helpers (used by `hyperlane-plugin-websocket` and several examples)
- `hyperlane-ai` — AI integration helpers (LLM client + streaming adapters)
- `lombok-macros` — `Data`/`New`/`Getter`/`GetterMut`/`Setter`/`CustomDebug`/`DisplayDebug` derives used throughout `hyperlane` + `http_type` structs
- `http-constant` — HTTP method / status / header constants (re-exported by `http_type::*` and thus visible via `hyperlane::*`)
- `http-compress`, `http-request`, `http-type` — sibling crates in the hyperlane ecosystem
- `tcp-request`, `udp-request` — raw TCP / UDP request adapters in the same ecosystem
