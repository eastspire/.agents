---
name: hyperlane
description: '**入口 skill — 使用 hyperlane 框架必须加载**。hyperlane 是 Tokio 异步 HTTP server,edition 2024,workspace monorepo(根 `hyperlane` re-export + `hyperlane-core` + `hyperlane-macros` + `http-type` + `http-compress` + `http-constant` + `http-request` + `hyperlane-cli`)。关键 API:Server::default() + server.route::<T>(path).await + server.task_panic::<T>().await + server.request_error::<T>().await + server.request_middleware::<T>().await + server.response_middleware::<T>().await,handler 实现 ServerHook::new/handle -> Status,用 Context::get_request/get_mut_response 读写。**Progressive loading 模式**:本 skill 是入口 + 5 行最小调用 + 跳转表;具体 API 在 references/api-*.md 子文档按需加载。**任何涉及 hyperlane 框架的任务先 load 本 skill,然后根据要写的代码类型加载对应的 api-*.md**。**当且仅当任务完全不使用 hyperlane**(纯 CLI、纯 std、不 import hyperlane crate)才不需要加载。'
license: MIT
---
# hyperlane 入口 skill — Progressive Loading Index

> **本 skill 只做跳转 + 5-行最小调用**。hyperlane 框架的完整 API / 坑表按需求分到 references/api-*.md 子文档中,需要哪个加载哪个,不要一次读全。

## 0. 必须先了解

- **Monorepo 布局**(2026-09 起):7 个 crate,见 `hyperlane-standards/SKILL.md` §1
- **Workspace 成员**:根 `hyperlane`(re-export shim) + `hyperlane-core` + `hyperlane-macros` + `http-type` + `http-compress` + `http-constant` + `http-request` + `hyperlane-cli`
- **crate 名 ≠ 目录名**:`type/` → `http-type`;`request/` → `http-request`;`compress/` → `http-compress`;`constant/` → `http-constant`(路径仍叫原名,crates.io publish 时是 `http-*`)
- **Tokio 异步 HTTP server**,`panic = "unwind"`
- **skill 不维护版本号**:查根 `Cargo.toml` `[workspace.package] version`
- **工具分工**:`hyperlane-cli` 只提供 `watch / new / template / help / version`;`fmt / bump / publish / sync` 全部在外部 `crate-cli`(`~/.cargo/bin/crate`)

## 1. 按需加载 — references/api-*.md

### `references/api-core.md`(hyperlane-core 完整 pub API,~83 项,~8.5 KB)

**何时加载**:写 `Server` builder / `Context` / `Hook` trait / `Route` / `Config` 时。

| 你要写... | 看哪一段 |
|---|---|
| `Server::default()` + `route / task_panic / request_error / request_middleware / response_middleware` 注册 | `server::impl`(18 个 fn) |
| `ServerConfig` / `RequestConfig` setter | `config::impl` + `config::struct` |
| `Context::get_request / get_mut_response` + body / header 操作 | `context::impl`(12 个 fn)+ `context::struct` |
| `ServerHook` trait + `HookType` enum + `Status::Continue / Next / ...` | `hook::trait`(7 个 trait)+ `hook::enum` + `hook::type`(9 个 type alias) |
| `RoutePattern` + `RouteSegment` + `RouteParams` + `RouteMatcher` | `route::enum` + `route::struct` + `route::type` + `route::impl` |
| `ServerError` / `RouteError` 错误体系 | `error::enum`(2 个 enum) |
| `DefaultServerHook` / `ServerControlHook` 实例化 | `hook::struct`(3 个 struct)+ `server::struct` |

### `references/api-macros.md`(hyperlane-macros,77 个 proc_macro,~9 KB)

**何时加载**:写 `#[route]` / `#[hyperlane]` / `#[task_panic]` / `#[request_error]` / `#[request_middleware]` / `#[response_middleware]` / `#[prologue_macros]` / `#[epilogue_macros]` / `context!{}` / `#[is_*_method]` / `#[response_*]` / `#[request_*]` 时。

**77 个 proc_macro 按用途分组**:
- **路由**: `route` / `hyperlane`
- **hook 注册**: `task_panic` / `request_error` / `request_middleware` / `response_middleware` / `prologue_macros` / `epilogue_macros`
- **method filter**: `is_get_method / is_post_method / is_put_method / is_delete_method / is_patch_method / is_head_method / is_options_method / is_connect_method / is_trace_method / is_unknown_method` + `methods`
- **version filter**: `is_http0_9_version / is_http1_0_version / is_http1_1_version / is_http2_version / is_http3_version / is_http1_1_or_higher_version / is_http_version / is_unknown_version`
- **upgrade filter**: `is_ws_upgrade_type / is_h2c_upgrade_type / is_tls_upgrade_type / is_unknown_upgrade_type`
- **request extract**: `try_get_*` + `request_body / request_body_json / request_body_json_result / attribute(s) / route_param(s) / request_query(s) / request_header(s) / request_cookie(s) / request_version / request_path`
- **response build**: `response_status_code / response_reason_phrase / response_header(s) / response_body / response_version / clear_response_headers`
- **filter**: `filter / reject / host / reject_host / referer / reject_referer / closed`
- **send/flush**: `try_send / send / try_flush / flush`
- **类型探测**: `try_get_websocket_request / try_get_http_request / try_get_task_panic_data / try_get_request_error_data / try_get_attribute`
- **数据构造**: `task_panic_data / request_error_data`
- **context macro**: `context!`(macro `pub fn context(input: TokenStream)` — declarative-style macro)

### `references/api-type.md`(http-type 完整 pub API,~252 项,~24 KB)

**何时加载**:写 `Request` / `Response` / `Method` / `Status` / `Stream` / `WebSocketFrame` / `Cookie` / `ArcMutex` / `BoxRwLock` / `HashMapXxHash3_64` / `ContentType` / `HttpVersion` / `HttpStatus` 等基础类型时。

**模块**: `any / arc_mutex / arc_rwlock / attribute / box_leak / box_rwlock / content_type / cookie / file_extension / hash_map_xx_hash3_64 / hash_set_xx_hash3_64 / http_status / http_url / http_version / lifetime / methods / panic / protocol / rc_rwlock / request / response / status / stream / task / upgrade_type / websocket_frame`

### `references/api-request.md`(http-request 客户端,~128 项,~12 KB)

**何时加载**:写客户端代码 — HTTP/HTTPS 请求 / `RequestBuilder` / `Proxy` / 自动 redirect / 响应解码。

**模块**: `common / request/{config, http_request, proxy, request_builder, tmp} / response / utils`

**注意**:`Request` 模块已拆为 `parser/{mod, fn}.rs` 子模块;**用绝对路径** `crate::request::parser::wire::split_*`,不要 `use super::parser::*`(跨 crate 模块)。

### `references/api-compress.md`(http-compress,~11 项)

**何时加载**:用 Brotli / Deflate / Gzip 压缩 / 解压时。

**模块**: `brotli / deflate / gzip + compress` enum

### `references/api-constant.md`(http-constant,14 模块,~1 KB)

**何时加载**:用 HTTP 常量 — header 名 / version / MIME / protocol / method / status / path / query / session 时。

**用法**:`use hyperlane::http_constant::{HEADER_CONTENT_TYPE, METHOD_GET, STATUS_200, VERSION_HTTP_1_1};`

### `references/api-cli.md`(hyperlane-cli,~19 项)

**何时加载**:用 `hyperlane-cli` 的 `watch / new / template / help / version` 子命令。**注意**:bump/sync/fmt/publish 在外部 `crate-cli`。

### `references/pitfalls.md`(consolidated index,链接到详细 reference)

**何时加载**:写完代码准备提交 / debug 一个奇怪行为时。包含 **22 个核心坑**(hyperlane-standards §10 原版)+ 8 个 monorepo/工具链坑。

## 2. 互锁 skill(必须同时加载)

| 你要做... | 加载 |
|---|---|
| 写任何 Rust 代码 | `rust-standards` |
| 用 `bump / sync / fmt / publish` | `crates-cli-usage`(外部 `crate-cli` 工具)|
| monorepo 内部依赖 / publish 顺序 | `crates-cli-usage` + `references/release-bump-flow.md` |
| 写 WebSocket 服务 | `references/hyperlane-plugin-websocket.md` |
| 写 SSE | `references/sse.md` + `references/hyperlane-broadcast.md` |
| 写客户端(HTTP request) | `references/http-request.md` + `references/proxy.md` |

## 3. 5-行最小调用

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

struct Index;
#[hyperlane]                                       // 必填 attribute
impl ServerHook for Index {
    async fn new(_stream: &mut Stream, _ctx: &mut Context) -> Self { Self }
    async fn handle(self, _stream: &mut Stream, _ctx: &mut Context) -> Status { Status::Next }
}
```

**重要约束**(必须知道):
- 路由注册是 **async**(`server.route().await`),**不能链式**
- response setter 是 **sync**(不需要 `.await`)
- `ServerControlHook` 有 `Default`,用 `.unwrap_or_default()`
- `#[route]` / `#[hyperlane]` 来自 `hyperlane-macros`,需要 `use hyperlane_macros::*;`

完整约束清单见 `references/pitfalls.md` §22 核心坑。

## 4. docs-pages 文档站(教程 / 完整示例)

`docs-pages` 仓库(docs-pages/docs)提供完整中文教程 — 全 30+ 个 page 同步到本 skill 的 `references/` 下(按 topic 切分):
- **基础**: `references/run.md`, `shutdown.md`, `wait.md`, `timeout.md`, `process.md`
- **路由**: `references/route.md`, `references/hyperlane-macros-route-params.md`
- **请求**: `references/request.md`, `references/cookie.md`, `references/attribute.md`, `references/cross.md`, `references/auth.md`
- **响应**: `references/response.md`, `references/send.md`, `references/flush.md`, `references/static-file.md`
- **hook**: `references/hyperlane-macros-method-filter.md`, `references/hyperlane-macros-version-filter.md`, `references/hyperlane-macros-upgrade-filter.md`, `references/hyperlane-macros-attributes.md`, `references/hyperlane-macros-composition.md`, `references/hyperlane-macros-filter.md`, `references/hyperlane-macros-hyperlane-init.md`, `references/hyperlane-macros-request.md`, `references/hyperlane-macros-response.md`, `references/hyperlane-macros-send-flush.md`
- **plugin**: `references/hyperlane-plugin-websocket.md`, `references/hyperlane-broadcast.md`, `references/websocket.md`, `references/sse.md`, `references/async.md`, `references/stream.md`, `references/hook-composition.md`, `references/multi-server.md`, `references/connection.md`

这些是**教程**(有完整示例代码),与 `references/api-*.md` 的**API 速查**互补。

## 5. 何时不加载本 skill

- 任务只涉及 euv / rust-standards / cargo / git — 与 hyperlane 完全无关
- 任务只读 hyperlane 源码做静态分析 / extract API

## 6. 相关 skill

- **`hyperlane-standards`**:workspace 布局 + crate 关系 + 跨 crate 规则(`[workspace.package]` / sync_workspace_version / 7 个 crate 互依赖 / version bump 铁律)
- **`crates-cli-usage`**:跨 monorepo 通用 `crate-cli` 工具使用(替代废弃的 `hyperlane fmt`)
- **`hyperlane-standards/references/release-bump-flow.md`**:bump 流程
- **`hyperlane-standards/references/monorepo-migration-checklist.md`**:从旧版单仓迁移到 monorepo 的检查清单
- **`rust-standards`**:Rust 通用规范