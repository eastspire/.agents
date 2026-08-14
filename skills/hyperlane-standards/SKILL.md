---
name: hyperlane-standards
description: '**hyperlane 框架完整 API + 坑表 — 与 hyperlane 打交道时必加载**。版本 21.3.6,edition 2024,Tokio 异步 HTTP server。覆盖:Server::default() + route/task_panic/request_error/request_middleware/response_middleware 5 个注册方法(async,不能链式) + ServerHook::new/handle -> Status 钩子 trait + Context::get_request/get_mut_response 读写 + ServerConfig/RequestConfig 配置(setter 是 sync)+ RoutePattern/RouteSegment/RouteParams 路由(static / dynamic {name} / regex {name:pattern})+ HttpVersion / Status / RequestError / ServerError 错误体系 + hyperlane-macros 过程宏(#[route] #[hyperlane] #[task_panic] #[request_error] #[request_middleware] #[response_middleware] #[prologue_macros] #[epilogue_macros] context!)+ 22 个常见坑(async setter 不能链式、response setter 是 sync、ServerControlHook::Default 用 unwrap_or_default、Stream 不需要 import、inventory::collect! 由框架在 route/impl.rs 调用)+ 7 个互锁生态 crate(http-type 20.1.9 / http-constant / http-parse / hyperlane-macros / hyperlane-plugin-websocket / hyperlane-broadcast / hyperlane-plugin-server-monitor)。触发关键词:hyperlane, Server::default, ServerHook, ServerControlHook, HookType, RoutePattern, RouteSegment, RouteParams, Context, ServerConfig, RequestConfig, Status, RequestError, ServerError, HttpVersion, Stream, hyperlane-macros, #[route], #[hyperlane], #[prologue_macros], #[epilogue_macros], context!, inventory, TaskPanicHook, RequestErrorHook, RequestMiddleware, ResponseMiddleware, RequestHook, ResponseHook, WebSocketHook, SseHook, broadcast::Bus, http-type, http-constant, http-parse, plugin-websocket, plugin-server-monitor。**当且仅当任务完全不使用 hyperlane**才不需要加载。'
license: MIT
---
# hyperlane-standards — 框架完整 API + 坑表

> **本 skill 是 hyperlane 框架的 source of truth**。hyperlane 入口 skill 只是个跳转 + 5 行示例,所有 API/坑细节都在这里。

## 0. 互锁 skill(本 skill 加载时必同时加载)

- **`hyperlane`**(入口) — 互锁指针,任何 hyperlane 任务先命中入口再跳到这里
- **`rust-standards`** — Rust 通用规范,对 hyperlane 同样适用,优先级最高
- 生态 crate 各有独立 skill(http-type / http-constant / lombo-macros 暂无独立 skill,内容内联在本文件)

## 1. 项目元信息

- crate 名: `hyperlane`
- 当前版本: `21.3.6`
- Rust edition: `2024`
- License: `MIT`
- 类型: 单 crate 库(非 workspace),`Server` builder + `Context` + `Hook`/`Route`/`Config` 类型
- 关键字: `http`, `request`, `response`, `tcp`, `cross-platform`
- 顶层重导出: `config::*`, `context::*`, `error::*`, `hook::*`, `route::*`, `server::*`, `http_type::*`, `inventory`
- 关键宏支持: 派生自 `lombok-macros` (`Data`, `New`, `Getter`, `GetterMut`, `Setter`, `CustomDebug`, `DisplayDebug`, `Eq`, `PartialEq`, `Hash`, `Clone`, `Default`)
- profile: `[profile.dev]` + `[profile.release]` 都用 `opt-level = 3`, `lto = true`, `incremental = false`, `panic = "unwind"`, `debug = false`, `codegen-units = 1`, `strip = "debuginfo"`

## 2. 安装

```shell
cargo add hyperlane
```

`Cargo.toml` 关键依赖:

```toml
[dependencies]
regex = "1.13.1"
http-type = "20.1.9"
inventory = "0.3.24"
lombok-macros = "2.0.36"
serde = { version = "1.0.229", features = ["derive"] }
```

## 3. 5 行最小完整调用模式

```rust
use hyperlane::*;
use hyperlane_macros::*;

#[tokio::main]
async fn main() {
    let mut server: Server = Server::default();
    server.route::<Index>("/").await;       // 路由注册是 async,不能链式
    let control: ServerControlHook = server.run().await.unwrap_or_default();
    control.wait().await;
}
```

## 4. 完整 `Server` builder API

所有 `route::<T>`, `task_panic::<T>`, `request_error::<T>`, `request_middleware::<T>`, `response_middleware::<T>` 方法拿 **type marker** `S`(仅编译期用于 monomorphize `ServerHookHandlerFactory`)— 它们只接受 turbofish,不接受运行时值。每个注册方法都是 `async` 必须独立 `.await`,**不能链式**。`Server` 必须 `let mut server: Server = Server::default();`,方法作为独立语句调用。`server_config` / `request_config` / `config_from_json` 是 **sync** setter(不 `.await`)。

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
```

## 5. `ServerHook` trait + `HookType` 枚举

`ServerHook` 是所有路由/middleware/panic/error handler 实现的统一 trait。它有 **2 个 async fn**:

```rust
#[async_trait]   // 实际是 lombok-macros 提供的 #[async_trait] 替代品
pub trait ServerHook: Sized + Send + Sync + 'static {
    async fn new(stream: &mut Stream, ctx: &mut Context) -> Self;
    async fn handle(self, stream: &mut Stream, ctx: &mut Context) -> Status;
}
```

`Status` 是 5 态 enum: `Continue` / `Next` / `Break` / `Exit` / ...(细节见 `error` 模块)。

`HookType` 决定 handler 在请求生命周期哪个阶段被调用:

| variant | 触发时机 | handler type marker | 典型用途 |
|---|---|---|---|
| `Route(RouteMatcher)` | 路由匹配后 | `S: ServerHook` | 业务 handler |
| `RequestMiddleware` | 在 Route 之前 | `S: ServerHook` | auth / 限流 / 日志 |
| `ResponseMiddleware` | 在 Route 之后 | `S: ServerHook` | 响应包装 / 缓存 |
| `TaskPanic` | 任务 panic 时 | `S: ServerHook` | panic 日志 / 上报 |
| `RequestError` | 404 / 405 / 内错 | `S: ServerHook` | 错误页 JSON |

`inventory::collect!(HookType);` 在 `src/route/impl.rs` 调用,框架自动注册 hook 类型。

## 6. `Context` 详解

`Context` 是请求-响应绑定的可变状态容器。**重点:response setter 是 sync**(直接 `.set_xxx().build()`),**不需要 `.await`**。

```rust
impl Context {
    // Request 读:
    pub fn get_request(&self) -> &Request
    pub fn get_request_mut(&mut self) -> &mut Request

    // Response 写(setter 是 SYNC,直接链式):
    pub fn get_mut_response(&mut self) -> &mut Response

    // Route 参数:
    pub fn get_route_params(&self) -> &RouteParams

    // 通用 attribute (type-erased):
    pub fn set_attribute<T: 'static + Send + Sync>(&mut self, key: &str, value: T)
    pub fn get_attribute<T: 'static + Send + Sync>(&self, key: &str) -> Option<&T>

    // Panic / error 数据:
    pub fn set_panic_data<T: 'static + Send + Sync>(&mut self, data: T)
    pub fn get_panic_data<T: 'static + Send + Sync>(&self) -> Option<&T>
    pub fn set_error_data<T: 'static + Send + Sync>(&mut self, data: T)
    pub fn get_error_data<T: 'static + Send + Sync>(&self) -> Option<&T>
}
```

`Response` 的 fluent API(都是 sync):

```rust
ctx.get_mut_response()
    .set_version(HttpVersion::Http1_1)
    .set_status_code(200)
    .set_header("Content-Type", "text/html; charset=utf-8")
    .set_body("hello world")
    .build();   // 返回 Vec<u8>
```

## 7. `RoutePattern` / `RouteSegment` / `RouteParams`

`RoutePattern` 接受 3 种语法:

- 静态: `"/"`, `"/api/health"`
- 动态: `"/users/{id}"` — `{id}` 会被 capture 为 `RouteParams["id"]`
- regex: `"/users/{id:\\d+}"` — `{id:\d+}` 用 regex 约束 + capture

`RouteSegment` 是 enum: `Static(&'static str)` / `Dynamic { name: &'static str, pattern: Option<&'static str> }`。`RouteParams` 实际是 `HashMap<String, String>`。

在 handler 里:

```rust
let id: String = ctx.get_route_params().get("id").cloned().unwrap_or_default();
```

## 8. `ServerConfig` / `RequestConfig`

```rust
pub struct ServerConfig {
    pub address: String,             // default "0.0.0.0:80"
    pub max_connections: usize,      // default 10000
    // ... (其他字段略)
}

pub struct RequestConfig {
    pub timeout: Duration,           // default 30s
    pub max_body_size: usize,        // default 4MB
    // ... (其他字段略)
}
```

**注意**:`set_address` 等 setter 是 **sync**(返回 `&mut Self`),必须单独写一行,不能 `.await` 链式。

```rust
let mut config: ServerConfig = ServerConfig::default();
config.set_address("0.0.0.0:8080".to_owned());    // sync
let mut server: Server = Server::default();
server.server_config(config);                      // sync
server.route::<Index>("/").await;                 // async
```

## 9. `hyperlane-macros` 过程宏

`hyperlane-macros` 是**独立的 companion crate**,**不在** `hyperlane` 的 `Cargo.toml` 依赖中。需要单独 `cargo add hyperlane-macros` 后 `use hyperlane_macros::*;`。

提供:

| 宏 | 用途 | 作用对象 |
|---|---|---|
| `#[route("/path")]` | 把 struct 标记为路由 handler | `struct` impl `ServerHook` |
| `#[hyperlane]` | alias,同上 | 同上 |
| `#[task_panic]` | 标记 panic handler struct | struct impl `ServerHook` |
| `#[request_error]` | 标记 error handler struct | struct impl `ServerHook` |
| `#[request_middleware]` | 标记 request middleware struct | struct impl `ServerHook` |
| `#[response_middleware]` | 标记 response middleware struct | struct impl `ServerHook` |
| `#[prologue_macros]` | 标记结构体级别的"前置宏" | struct |
| `#[epilogue_macros]` | 标记结构体级别的"后置宏" | struct |
| `context!` | DSL 宏(类似 yew,但内部用不同语法) | - |

宏版本: `hyperlane-macros` 当前 `0.x` 系列(查 `Cargo.toml` 实时确认)。

## 10. 22 个常见坑(必读)

1. **路由注册是 async**:`server.route::<T>(path).await` — 不能 `.route().route()` 链式。
2. **response setter 是 sync**:`ctx.get_mut_response().set_xxx()` — 不需要 `.await`。
3. **`ServerControlHook` 有 `Default`**:`server.run().await.unwrap_or_default()` — 不要 `expect`。
4. **不要自己 import `Stream`**:框架的 `Stream` 类型通过 `use hyperlane::*;` 进来,不要跟 `tokio::net::TcpStream` 混。
5. **`inventory::collect!` 框架调用**:**不要**在自己代码里再 `collect!` 一遍,会重复注册。
6. **`#[route]` 来自 `hyperlane-macros`,不是 `hyperlane`**:需要 `use hyperlane_macros::*;`。
7. **`Server` 必须是 `let mut`**:所有注册方法都改 `&mut self`。
8. **`Status::Continue` vs `Status::Next`**:继续走下一个 hook vs 跳到下一阶段(细节查 enum 定义)。
9. **`hook` 函数签名是 `async fn handle(self, ...)`**:它拿 `self` 而非 `&self` — 因为 handler 是一次性的(per-request instance)。
10. **`new` 钩子也拿 `&mut Stream, &mut Context`**:可以在 `new` 里做请求级初始化。
11. **`RouteParams` 是 `HashMap<String, String>`**:注意字符串拥有权。
12. **dynamic segment 必须用 `{name}` 包裹**:写 `/users/:id` 是错的,要 `/users/{id}`。
13. **regex segment 语法是 `{name:pattern}`**:`/users/{id:\\d+}` — **注意双反斜杠**(Rust string literal 转义)。
14. **response body 用 `set_body` 接收 `Into<Vec<u8>>`**:传 `&str` 也行,内部 `.into()`。
15. **`build()` 返回 `Vec<u8>`**:这个返回值通常 `let _ = ...;` 丢掉,因为 setter 已经把 body 写到 `Response` 里。
16. **`server_config()` / `request_config()` 是 sync**:不要加 `.await`。
17. **`config_from_json` 是 sync**:接收 `impl AsRef<str>`,传 `&str` 或 `String` 都行。
18. **Tokio runtime 必须自己起**:`#[tokio::main] async fn main() { ... }` — 框架不自动起。
19. **每个 hook 的 `new()` 每次请求都执行**:**不要**在 `new` 里放 expensive IO,放 `handle` 里。
20. **panics 在 `handle` 里会被 `TaskPanic` hook 捕获**:不要在 `handle` 里 `std::panic::catch_unwind` — 让框架做。
21. **404 / 405 默认走 `RequestError` hook**:如果你没注册 `RequestError` hook,框架会用内置 default(返回空 404 body)。
22. **profile `panic = "unwind"`**:`TaskPanic` hook 才能拿到 panic;`panic = "abort"` 直接 abort 不触发。

## 11. 7 个互锁生态 crate

| crate | 用途 | 关系 |
|---|---|---|
| `http-type` `20.1.9` | Request/Response/HttpVersion 类型 | `hyperlane::http_type::*` 重导出 |
| `http-constant` | HTTP 常量(headers、status code、methods) | 通过 `http-type` 间接 |
| `http-parse` | HTTP 解析器 | 通过 `http-type` 间接 |
| `lombok-macros` `2.0.36` | 派生宏源(`Data/New/Getter/Setter/...`)| `hyperlane` 依赖,derive 在 hyperlane 结构上 |
| `hyperlane-macros` | 过程宏(`#[route]` 等) | **独立 crate**,需单独 `cargo add` |
| `hyperlane-plugin-websocket` | WebSocket 支持 | 独立 plugin crate,`inventory::submit!` |
| `hyperlane-plugin-server-monitor` | 服务监控(指标/健康检查) | 独立 plugin crate |
| `hyperlane-broadcast` | 进程内 broadcast bus | 独立 plugin crate,`broadcast::Bus<T>` |

## 12. Documentation sources (docs-pages)

完整中文参考在 [docs-pages](https://github.com/docs-pages/docs) 仓库(私有)。本地镜像在 `references/`:

- `read_file('hyperlane-standards/references/websocket.md')` — WebSocket setup
- `read_file('hyperlane-standards/references/auth.md')` — auth middleware
- `read_file('hyperlane-standards/references/hyperlane-macros-request.md')` — request-extraction 宏
- `read_file('hyperlane-standards/references/route.md')` — 路由模式 + 例子
- `read_file('hyperlane-standards/references/server-config.md')` — ServerConfig / RequestConfig
- ...任何 `references/<topic>.md` 都在

同步脚本:

```shell
bash scripts/sync-references.sh                       # 全量(clones docs-pages)
bash scripts/sync-references.sh --source-dir <path>   # 复用本地 clone
bash scripts/verify-references.sh                     # 看 vs HEAD 的 diff
```

mapping 文件: `scripts/sync-references.mapping`(references/<file>.md → docs-pages/src/...)。要 pin 某个文件加 `# manual override:`,脚本不动它。
