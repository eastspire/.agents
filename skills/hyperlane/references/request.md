---
synced_from: docs-pages/src/hyperlane/usage-introduction/request.md@f972247
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

> [!tip]
>
> `hyperlane` 框架对 `ctx` 额外封装了子字段的方法，可以直接调用大部分子字段的 `get` 和 `set` 方法名称。
> 例如：调用 `request` 上的 `get_method` 方法，
> 一般需要从 `ctx` 解出 `request`，再调用`request.get_method()`，
> 可以简化成直接调用 `ctx.get_request().get_method()`。
>
> **调用规律**
>
> - `request` 仅支持`get`，不支持`set`，框架保证请求信息不会被意外修改。
> - 原 `request` 的 `get` 方法的 `get` 名称后加 `request` 名称，中间使用\_拼接。

## 获取请求信息

#### 获取 `request`

```rust
let request: &Request = ctx.get_request();
```

#### 获取 `method`

```rust
let method: &RequestMethod = ctx.get_request().get_method();
```

#### 获取 `host`

```rust
let host: &RequestHost = ctx.get_request().get_host();
```

#### 获取 `path`

```rust
let path: &RequestPath = ctx.get_request().get_path();
```

#### 获取 `version`

```rust
let version: &RequestVersion = ctx.get_request().get_version();
```

#### 获取 `querys`

```rust
let querys: &RequestQuerys = ctx.get_request().get_querys();
```

#### 获取特定查询参数

```rust
// 尝试获取查询参数
let query_value: Option<RequestQuerysValue> = ctx.get_request().try_get_query("key");
// 获取查询参数（获取不到则panic）
let query_value: RequestQuerysValue = ctx.get_request().get_query("key");
```

#### 获取 `header`

> [!tip]
>
> `hyperlane` 框架请求头的 `key` 是经过全小写处理，建议使用框架定义的常量。

```rust
// 尝试获取请求头
let header: Option<RequestHeadersValue> = ctx.get_request().try_get_header(CONTENT_TYPE);
// 获取请求头（获取不到则panic）
let header: RequestHeadersValue = ctx.get_request().get_header(CONTENT_TYPE);
```

#### 获取 `headers`

```rust
let headers: &RequestHeaders = ctx.get_request().get_headers();
```

#### 获取请求头的第一个值

```rust
// 尝试获取请求头的第一个值
let header_value: Option<RequestHeadersValueItem> = ctx.get_request().try_get_header_front(CONTENT_TYPE);
// 获取请求头的第一个值（获取不到则panic）
let header_value: RequestHeadersValueItem = ctx.get_request().get_header_front(CONTENT_TYPE);
```

#### 获取请求头的最后一个值

```rust
// 尝试获取请求头的最后一个值
let header_value: Option<RequestHeadersValueItem> = ctx.get_request().try_get_header_back(ACCEPT);
// 获取请求头的最后一个值（获取不到则panic）
let header_value: RequestHeadersValueItem = ctx.get_request().get_header_back(ACCEPT);
```

#### 获取请求头值的数量

```rust
// 尝试获取请求头值的数量
let header_count: Option<usize> = ctx.get_request().try_get_header_size(ACCEPT_ENCODING);
// 获取请求头值的数量（获取不到则panic）
let header_count: usize = ctx.get_request().get_header_size(ACCEPT_ENCODING);
```

#### 获取所有请求头值的总数量

```rust
let total_values: usize = ctx.get_request().get_headers_values_size();
```

#### 获取请求头的数量

```rust
let headers_count: usize = ctx.get_request().get_headers_size();
```

#### 检查是否存在特定请求头

```rust
let has_header: bool = ctx.get_request().has_header(CONTENT_TYPE);
```

#### 检查请求头是否包含特定值

```rust
let has_value: bool = ctx.get_request().has_header_value(CONTENT_TYPE, APPLICATION_JSON);
```

#### 获取请求体

```rust
let body: &RequestBody = ctx.get_request().get_body();
```

#### 获取 `string` 格式的请求体

```rust
let body: String = ctx.get_request().get_body_string();
```

#### 获取 `json` 格式的请求体

```rust
// 反序列化请求体
let body: Result<T, serde_json::Error> = ctx.get_request().try_get_body_json::<T>();
// 反序列化请求体（反序列化失败则panic）
let body: T = ctx.get_request().get_body_json::<T>();
```

#### 获取请求升级类型

```rust
let upgrade_type: UpgradeType = ctx.get_request().get_upgrade_type();
```

#### 检查是否为 WebSocket 升级

```rust
let is_ws: bool = ctx.get_request().is_ws_upgrade_type();
```

## 属性宏写法

> [!tip]
>
> `hyperlane` 框架提供了属性宏来简化请求信息的获取，可以在 `handle` 方法上使用属性宏自动提取请求信息。

### 获取请求体

```rust
use hyperlane::*;
use hyperlane_macros::*;

#[route("/request_body")]
struct RequestBodyRoute;

impl ServerHook for RequestBodyRoute {
    async fn new(_: &mut Stream, _: &mut Context) -> Self {
        Self
    }

    #[request_body(body)]
    async fn handle(self, stream: &mut Stream, ctx: &mut Context) -> Status {
        // body is available as Vec<u8>
        Status::Continue
    }
}
```

### 获取请求体 JSON

```rust
#[request_body_json(body: TestData)]
async fn handle(self, stream: &mut Stream, ctx: &mut Context) -> Status {
    // body is available as the deserialized type
    Status::Continue
}
```

### 安全获取请求体 JSON（返回 Result）

```rust
#[request_body_json_result(body: TestData)]
async fn handle(self, stream: &mut Stream, ctx: &mut Context) -> Status {
    // body is available as Result<T, serde_json::Error>
    Status::Continue
}
```

### 获取请求头

```rust
#[request_header(HOST => host_value)]
async fn handle(self, stream: &mut Stream, ctx: &mut Context) -> Status {
    // host_value is available
    Status::Continue
}
```

### 安全获取请求头（返回 Option）

```rust
#[try_get_request_header(HOST => host_value)]
async fn handle(self, stream: &mut Stream, ctx: &mut Context) -> Status {
    // host_value is available as Option<RequestHeadersValueItem>
    Status::Continue
}
```

### 获取所有请求头

```rust
#[request_headers(headers)]
async fn handle(self, stream: &mut Stream, ctx: &mut Context) -> Status {
    // headers is available as RequestHeaders
    Status::Continue
}
```

### 获取查询参数

```rust
#[request_query("key" => query_value)]
async fn handle(self, stream: &mut Stream, ctx: &mut Context) -> Status {
    // query_value is available
    Status::Continue
}
```

### 安全获取查询参数（返回 Option）

```rust
#[try_get_request_query("key" => query_value)]
async fn handle(self, stream: &mut Stream, ctx: &mut Context) -> Status {
    // query_value is available as Option<RequestQuerysValue>
    Status::Continue
}
```

### 获取所有查询参数

```rust
#[request_querys(querys)]
async fn handle(self, stream: &mut Stream, ctx: &mut Context) -> Status {
    // querys is available as RequestQuerys
    Status::Continue
}
```

### 获取请求路径

```rust
#[request_path(path)]
async fn handle(self, stream: &mut Stream, ctx: &mut Context) -> Status {
    // path is available as RequestPath
    Status::Continue
}
```

### 获取请求版本

```rust
#[request_version(version)]
async fn handle(self, stream: &mut Stream, ctx: &mut Context) -> Status {
    // version is available as RequestVersion
    Status::Continue
}
```

### 使用 try_get_http_request 属性宏

> [!tip]
>
> 可以使用 `#[try_get_http_request]` 属性宏从 TCP 流中读取并解析下一个 HTTP 请求。

```rust
use hyperlane::*;
use hyperlane_macros::*;

#[route("/try_get_http_request")]
struct TryGetHttpRequestRoute;

impl ServerHook for TryGetHttpRequestRoute {
    async fn new(_: &mut Stream, _: &mut Context) -> Self {
        Self
    }

    #[try_get_http_request]
    async fn handle(self, stream: &mut Stream, ctx: &mut Context) -> Status {
        Status::Continue
    }
}
```

## 请求方法过滤

> [!tip]
>
> `hyperlane` 框架提供了请求方法过滤的属性宏，只有匹配的请求方法才会执行 `handle` 方法。
> 不匹配时直接返回 `Status::Continue`，跳过当前路由。

### 单个方法过滤

```rust
#[is_get_method]
async fn handle(self, stream: &mut Stream, ctx: &mut Context) -> Status {
    // Only GET requests will reach here
    Status::Continue
}
```

支持的方法过滤宏：`#[is_get_method]`、`#[is_post_method]`、`#[is_put_method]`、`#[is_delete_method]`、`#[is_patch_method]`、`#[is_head_method]`、`#[is_options_method]`、`#[is_connect_method]`、`#[is_trace_method]`、`#[is_unknown_method]`

### 多方法过滤

> [!tip]
>
> 可以使用 `#[methods]` 同时匹配多个请求方法，方法名使用小写标识符。

```rust
#[methods(get, post)]
async fn handle(self, stream: &mut Stream, ctx: &mut Context) -> Status {
    // Only GET or POST requests will reach here
    Status::Continue
}
```

## 请求版本过滤

> [!tip]
>
> `hyperlane` 框架提供了 HTTP 版本过滤的属性宏，只有匹配的版本才会执行 `handle` 方法。

```rust
#[is_http1_1_version]
async fn handle(self, stream: &mut Stream, ctx: &mut Context) -> Status {
    // Only HTTP/1.1 requests will reach here
    Status::Continue
}
```

支持的版本过滤宏：`#[is_http0_9_version]`、`#[is_http1_0_version]`、`#[is_http1_1_version]`、`#[is_http2_version]`、`#[is_http3_version]`、`#[is_http1_1_or_higher_version]`、`#[is_unknown_version]`

## 标准 HTTP 过滤

> [!tip]
>
> `#[is_http_version]` 用于过滤**标准 HTTP 请求**（排除 WebSocket、h2c、TLS 等协议升级请求）。只有非升级请求才会执行 `handle` 方法。

```rust
#[is_http_version]
async fn handle(self, stream: &mut Stream, ctx: &mut Context) -> Status {
    // Only standard HTTP requests (non-upgrade) will reach here
    Status::Continue
}
```

## 协议升级类型过滤

> [!tip]
>
> `hyperlane` 框架提供了协议升级类型过滤的属性宏。

```rust
#[is_ws_upgrade_type]
async fn handle(self, stream: &mut Stream, ctx: &mut Context) -> Status {
    // Only WebSocket upgrade requests will reach here
    Status::Continue
}
```

支持的升级类型过滤宏：`#[is_ws_upgrade_type]`、`#[is_h2c_upgrade_type]`、`#[is_tls_upgrade_type]`、`#[is_unknown_upgrade_type]`

## 转字符串

#### 通过 `to_string`

> [!tip]
>
> 将获得完整的原始结构体字符串结构。

```rust
ctx.get_request().to_string();
```

<Bottom />
