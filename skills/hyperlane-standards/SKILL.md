---
name: hyperlane-standards
description: '**hyperlane 框架完整 API + 坑表 — 与 hyperlane 打交道时必加载**。Monorepo 架构(根 `hyperlane` re-export + 5 子包: `hyperlane-core` / `hyperlane-macros` / `hyperlane-type` / `hyperlane-cli`),版本 21.3.6,edition 2024,Tokio 异步 HTTP server。覆盖:Server::default() + route/task_panic/request_error/request_middleware/response_middleware 5 个注册方法(async,不能链式) + ServerHook::new/handle -> Status 钩子 trait + Context::get_request/get_mut_response 读写 + ServerConfig/RequestConfig 配置(setter 是 sync)+ RoutePattern/RouteSegment/RouteParams 路由(static / dynamic {name} / regex {name:pattern})+ HttpVersion / Status / RequestError / ServerError 错误体系 + hyperlane-macros 过程宏(#[route] #[hyperlane] #[task_panic] #[request_error] #[request_middleware] #[response_middleware] #[prologue_macros] #[epilogue_macros] context!)+ 22 个常见坑(async setter 不能链式、response setter 是 sync、ServerControlHook::Default 用 unwrap_or_default、Stream 不需要 import、inventory::collect! 由框架在 route/impl.rs 调用)+ monorepo 内部依赖图 + cargo publish 路径 + `readme = ../../README.md` 拒绝陷阱 + 5 个子包之间 `path = ...` path-dep 模式。触发关键词:hyperlane, Server::default, ServerHook, ServerControlHook, HookType, RoutePattern, RouteSegment, RouteParams, Context, ServerConfig, RequestConfig, Status, RequestError, ServerError, HttpVersion, Stream, hyperlane-macros, hyperlane-core, hyperlane-type, hyperlane-cli, #[route], #[hyperlane], #[prologue_macros], #[epilogue_macros], context!, inventory, TaskPanicHook, RequestErrorHook, RequestMiddleware, ResponseMiddleware, RequestHook, ResponseHook, WebSocketHook, SseHook, broadcast::Bus, http-type, http-constant, http-parse, plugin-websocket, plugin-server-monitor。**当且仅当任务完全不使用 hyperlane**才不需要加载。'
license: MIT
---
# hyperlane-standards — 框架完整 API + 坑表

> **本 skill 是 hyperlane 框架的 source of truth**。hyperlane 入口 skill 只是个跳转 + 5 行示例,所有 API/坑细节都在这里。

---

## Index

| I want to... | Jump to |
| --- | --- |
| See which other skills must load with this one | [Mutual-Lock Skills](#0-mutual-lock-skills) |
| Check crate name / version / edition / license | [Project Metadata](#1-project-metadata) |
| Add `hyperlane` to `Cargo.toml` | [Installation](#2-installation) |
| See the 5-line minimum call to start a server | [5-Line Minimum Call](#3-5-line-minimum-call) |
| Browse the full `Server` builder API (route, middleware, hook) | [Full `Server` Builder API](#4-full-server-builder-api) |
| Implement a `ServerHook` / pick a `HookType` | [`ServerHook` trait + `HookType` enum](#5-serverhook-trait--hooktype-enum) |
| Read/write the per-request `Context` | [`Context` Reference](#6-context-reference) |
| Define a route (static / dynamic / regex) | [`RoutePattern` / `RouteSegment` / `RouteParams`](#7-routepattern--routesegment--routeparams) |
| Configure server-level or request-level behavior | [`ServerConfig` / `RequestConfig`](#8-serverconfig--requestconfig) |
| Use `#[route]`, `#[hyperlane]`, `context!`, etc. | [`hyperlane-macros` Procedural Macros](#9-hyperlane-macros-procedural-macros) |
| Avoid the 22 most common gotchas | [22 Common Pitfalls](#10-22-common-pitfalls) |
| Pick an ecosystem crate to extend hyperlane | [7 Interlocking Ecosystem Crates](#11-7-interlocking-ecosystem-crates) |
| Find docs-pages source for tutorials | [Documentation sources (docs-pages)](#12-documentation-sources-docs-pages) |
| Work with the monorepo / path-deps / publish order | [Monorepo Layout & Internal Deps](#13-monorepo-layout--internal-deps) |
| Bump the version of all crates at once | [Version Bump Rule](#14-version-bump-rule) |

---

## 0. Mutual-Lock Skills

- **`hyperlane`**(入口) — 互锁指针,任何 hyperlane 任务先命中入口再跳到这里
- **`rust-standards`** — Rust 通用规范,对 hyperlane 同样适用,优先级最高
- 生态 crate 各有独立 skill(http-type / http-constant / lombo-macros 暂无独立 skill,内容内联在本文件)

## 1. Project Metadata

- 仓库: `hyperlane-dev/hyperlane` (single repo, monorepo)
- **Monorepo**(2026-09 起) — 5 个 crate:
  - `hyperlane` (根) — 纯 re-export shim,`use hyperlane::*` 暴露 core + macros + type(通过 core 间接)
  - `hyperlane-core` — 框架本体: `Server` builder + `Context` + `Hook`/`Route`/`Config` + `http_type::*` 重导出
  - `hyperlane-macros` — proc-macro 集合(`#[route]` 等),独立 proc-macro crate
  - `hyperlane-type` — HTTP 类型库: Request/Response/Method/Status/Stream/Context/RouteParams/HttpStatus + concurrent 包装(ArcMutex/BoxRwLock/xxhash 等)
  - `hyperlane-cli` — 命令行工具(fmt/bump/publish/watch/new/template)
- 当前版本: 全部 crate 同步发布,单 version 号(`21.3.6`)
- Rust edition: `2024`
- License: `MIT`
- workspace 布局:
  ```
  hyperlane/
  ├── Cargo.toml          # [workspace] + 根 hyperlane re-export 包
  ├── core/               # hyperlane-core
  ├── macros/             # hyperlane-macros (proc-macro)
  ├── type/               # hyperlane-type
  └── cli/                # hyperlane-cli (bin target)
  ```
- 顶层重导出(根 `hyperlane`): `hyperlane_core::*`(涵盖原 `config/context/error/hook/route/server/http_type/inventory`)
- 关键宏支持: 派生自 `lombok-macros` (`Data`, `New`, `Getter`, `GetterMut`, `Setter`, `CustomDebug`, `DisplayDebug`, `Eq`, `PartialEq`, `Hash`, `Clone`, `Default`)
- profile: `[profile.dev]` + `[profile.release]` 都用 `opt-level = 3`, `lto = true`, `incremental = false`, `panic = "unwind"`, `debug = false`, `codegen-units = 1`, `strip = "debuginfo"`(workspace 根定义一次,子包若重复定义会被 cargo 警告忽略,这是预期行为 — 跟 euv 一致)

### 1.1 版本升级规则(用户说「升级版本」时,hyperlane 全家桶通用)

Monorepo 5 个 crate 共享一个 version 号(`21.3.6`)。bump 时 **只改根 `Cargo.toml` 第 3 行 `[package] version`**,子 crate 的 `[package] version` + `[workspace.dependencies]` path-dep 内的 `version` 一律不动 — 由 CI `.github/workflows/rust.yml` 的 `sync_workspace_version` job 在 master push 上自动 propagate。

**禁止全仓 sed `version = "X.Y.Z"`**(会误伤第三方依赖如 `http-compress = "3.0.28"`)。**禁止**手改 4 个子 crate 的 `Cargo.toml` 中的 `version` 字段。

**PR 前 diff stat 自检**:`git diff --stat` 期望只有 1 file + 1 line(根 `Cargo.toml`)。多于 1 file = 停下来,先 `git checkout HEAD -- <额外文件>`。

CI sync 行为: master merge → `sync_workspace_version` job 跑 → 在 master 上追加 `chore: sync all package versions to X.Y.Z` commit → 5 个 `Cargo.toml` + 根 `[workspace.dependencies]` 内 path-dep `version` 全部同步。等这个自动 commit 出现后再认为 release 完成。

(详细跨多 PR 的 release bump 实战见 `references/release-bump-flow.md` — 含 PR #171 + #220 + minor/major patch 的踩坑史)

## 2. Installation

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

## 3. 5-Line Minimum Call

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

## 4. Full `Server` Builder API

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

## 5. `ServerHook` trait + `HookType` enum

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

## 6. `Context` Reference

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

## 9. `hyperlane-macros` Procedural Macros

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

## 10. 22 Common Pitfalls

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

## 11. 7 Interlocking Ecosystem Crates

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

## 13. Monorepo Layout & Internal Deps

### 13.1 内部依赖图(path-dep,workspace 模式)

```
hyperlane-type        (叶子, 无内部依赖)
   ↑ path-dep
hyperlane-core ───────┐
   ↑ path-dep        │
hyperlane-macros ─────┤
   ↑ path-dep        │
hyperlane-cli ────────┤
   ↑ path-dep        │
hyperlane (根) ───────┘
```

**验证命令**:`cargo metadata --format-version=1 --no-deps` 看每个 `package.dependencies[]`,内部依赖的 `source` 字段必须是 `null`(path-dep,不打 crates.io)。任何 `source` 不为 null = 循环依赖 / 错配。

**与 euv 的差异**: euv 子包间内部依赖为 0(core/macros/ui/engine/cli 完全平行)。hyperlane 的 `core` 仓**实际使用** `hyperlane-type` 的 `Request/Response/Status/Stream/Context/RouteParams` 类型,所以 core→type 是代码约束(非设计选择)。若要 euv-style 0 内部依赖,需要把 core 内部使用的 type 拆碎重定义,会破坏现有 API。

### 13.2 Cargo.toml 依赖写法

子包内部依赖用 `path = "..."` + 显式 `version`:
```toml
# core/Cargo.toml
hyperlane-type = { path = "../type", version = "21.3.6" }

# macros/Cargo.toml
hyperlane-core = { path = "../core", version = "21.3.6" }

# 根 Cargo.toml 引用子包用 workspace = true:
hyperlane-core = { workspace = true }
```

根 `Cargo.toml` 的 `[workspace.dependencies]` 必须包含**全部** path-dep(sync_workspace_version job 依赖它来 sed):
```toml
[workspace.dependencies]
hyperlane-core = { path = "core", version = "21.3.6" }
hyperlane-macros = { path = "macros", version = "21.3.6" }
hyperlane-type = { path = "type", version = "21.3.6" }
hyperlane-cli = { path = "cli", version = "21.3.6" }
```

### 13.3 根 hyperlane 包(纯 re-export shim)

```rust
// src/lib.rs(无 //! 头注释,无 fn)
pub use hyperlane_core::*;
pub use hyperlane_macros::*;
```

`hyperlane_type::*` 由 `hyperlane_core` 内部 `pub use {hyperlane_type::*, inventory};` 间接暴露给用户,**根 lib.rs 不需要单独 re-export**(否则触发 unused_imports warning + 不必要)。

根 `[dependencies]`:
```toml
[dependencies]
hyperlane-core = { workspace = true }
hyperlane-macros = { workspace = true }
# 不要加 hyperlane-type — root 不直接用,加了就 dead dep
```

### 13.4 `cargo publish` 顺序(拓扑序,与 euv 一致)

CI `.github/workflows/rust.yml` 的 `publish` job 按**拓扑序**发布(被依赖的先发):

```
hyperlane-type → hyperlane-core → hyperlane-macros → hyperlane-cli → hyperlane
```

每个 `cargo publish -p X --allow-dirty --no-verify` 是纯本地 package 操作,workspace 模式下 path-dep 自动解析为本地路径。**不需要**先把 path-dep 改成 crates.io 版本。

**顺序由依赖图决定**(2026-09-14 PR #34 验证):`hyperlane-macros` 在 `Cargo.toml` 里 `dev-dependencies` 引 `hyperlane-core` + 生成代码引用 `::hyperlane_core::*`,所以 **`core` 必须先于 `macros` 发布**。如果 publish job 写成 `type → macros → core → cli → hyperlane`,macros 发布时 core 还没上 crates.io,resolver 失败。CI 静默吞错误(retry+continue),最终 `max_stable_version` 不匹配 tag。

**检测 publish 顺序是否对**:`cargo metadata --format-version=1 --no-deps | jq -r '.packages[].dependencies[] | select(.source == null) | .name'` 看 internal dep 关系,反推拓扑序。或者直接看 `Cargo.toml` 的 `[dev-dependencies]` 里 `path = "..."` 引的目标。

### 13.4.1 PR #34 实际 publish 顺序 pitfall(2026-09-14 verified)

`hyperlane-macros/Cargo.toml` 写了:
```toml
[dev-dependencies]
serde = { ... }
```

但宏生成代码里 `quote!` 出来的 token 含 `::hyperlane_core::Status /::RouteParams`,doctest 100 处有 `use hyperlane_core::*;`。**编译期宏展开需要 core crate 存在**。所以核心仓 `hyperlane-core` 必须先 publish,macros 才能 publish。

不强制 `path-only dev-dep`(Rust macros 子 crate 通常不反向 dev-dep 根 crate,因为根是 re-export shim);只要 publish 顺序对,`hyperlane-core` 上 crates.io 后,`hyperlane-macros` 的 resolver 找到 `hyperlane-core = "21.3.6"` 即可。

### 13.5 README 陷阱(cargo publish 拒绝跨仓 README)

每个子包 `Cargo.toml` 的 `readme` **必须指向子包目录内的相对路径**。**禁止** `readme = "../../README.md"`(指向 monorepo 根 README) — `cargo publish` 会拒绝:
```
error: readme `../../README.md` does not appear to exist
       (relative to `/path/to/monorepo/<subcrate>`).
```

**修复**:每个子包目录各放一份 `README.md`(从仓根 `cp` 一份即可),`readme = "README.md"`。这跟 euv monorepo 同模式(每个 euv-* 子仓都有独立 README.md)。

### 13.6 顶层 `use` 命名坑(proc-macro crate)

`hyperlane-macros` 是 proc-macro crate,其源码生成的 TokenStream 用 `::hyperlane::Status/HookType/inventory` 等路径。如果保留单仓时代的 `::hyperlane::*` 路径,展开到用户代码时会找不到 crate。

**monorepo 改法**:把所有 `macros/src/**/*.rs` 内的 `::hyperlane::` 替换为 `::hyperlane_core::`(`sed -i 's|::hyperlane::|::hyperlane_core::|g'`)。同时 `macros/src/lib.rs` 的 100 个 doctest 里 `use hyperlane::*;` → `use hyperlane_core::*;`。

**为什么不反过来**让根 `hyperlane` 反向依赖 macros?会成环(`hyperlane-macros` 不能依赖 `hyperlane`)。正确方向: macros 用 `::hyperlane_core::*` 直接引用,不绕根包。

### 13.7 monorepo 引入后从单仓迁移的 checklist

(从单仓 hyperlane → monorepo 的实战顺序,见 `references/monorepo-migration-checklist.md`)

- [ ] `git mv src core/src && git mv tests core/tests`
- [ ] `cp -r upstream-cli/* cli/` + 同理 macros/type
- [ ] 删除每个子仓的 `.git` 子目录(避免嵌套 repo)
- [ ] 每个子仓的 `lib.rs` 顶部 `//! <name>` 头注释必须删除(rust-standards §2.5)
- [ ] 每个子仓的 `Cargo.toml` 改:
  - `name` → 改前缀 (`hyperlane-type` / `hyperlane-macros` / `hyperlane-cli`)
  - `readme = "../../README.md"` → `readme = "README.md"`(并 `cp README.md` 到子包目录)
  - `repository` → 统一指向 `https://github.com/hyperlane-dev/hyperlane.git`
  - 内部依赖用 `path = "..."` + `version`
- [ ] 根 `Cargo.toml` 写 `[workspace]` + 根 hyperlane 包(纯 re-export)
- [ ] `macros/src/**` 内所有 `::hyperlane::` 替换为 `::hyperlane_core::`
- [ ] `macros/src/lib.rs` 内 100 个 doctest 的 `use hyperlane::*` 替换为 `use hyperlane_core::*`
- [ ] `tests/mod.rs` 内 `use hyperlane::*` 替换为 `use hyperlane_core::*`(在子包内)
- [ ] 跑 `cargo check --workspace` + `cargo test --workspace` + `audit_rust_standards.py`
- [ ] 跑 `cargo metadata` 验证无循环

## 14. Version Bump Rule

跟 `euv-standards §17` 同模式。简版:

```bash
cd /root/github/hyperlane-dev/hyperlane
NEW_VER="21.3.7"
OLD_VER="21.3.6"
# 只改根 Cargo.toml
sed -i "s/^version = \"$OLD_VER\"$/version = \"$NEW_VER\"/" Cargo.toml
git diff --stat   # 期望只有 Cargo.toml +1/-1
git add Cargo.toml
git commit -m "chore: bump version to $NEW_VER"
```

**不**做:
- ❌ `sed -i 's/version = "21.3.6"/version = "21.3.7"/' */Cargo.toml`
- ❌ 编辑 `core/Cargo.toml` / `macros/Cargo.toml` / `type/Cargo.toml` / `cli/Cargo.toml`
- ❌ 编辑 `[workspace.dependencies]` 内 path-dep 的 `version`

CI sync 在 master push 上自动补齐上述字段。
