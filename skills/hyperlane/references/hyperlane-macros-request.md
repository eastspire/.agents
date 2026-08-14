---
synced_from: docs-pages/src/hyperlane-macros/request.md@f972247
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
> `hyperlane-macros` 提供了多种请求数据提取属性宏，用于在路由处理函数中便捷地获取请求的各个部分，无需手动调用 `ctx.get_request()`。

## 请求体提取

### 原始请求体

```rust
use hyperlane::*;
use hyperlane_macros::*;

#[route("/body")]
struct BodyRoute;

impl ServerHook for BodyRoute {
    async fn new(_: &mut Stream, _: &mut Context) -> Self {
        Self
    }

    #[request_body(body)]
    async fn handle(self, stream: &mut Stream, ctx: &mut Context) -> Status {
        // body 可用作 RequestBody (Vec<u8>)
        Status::Continue
    }
}
```

支持多参数提取：

```rust
#[request_body(body1, body2)]
async fn handle(self, stream: &mut Stream, ctx: &mut Context) -> Status {
    Status::Continue
}
```

### JSON 请求体（解析失败 panic）

```rust
use serde::{Deserialize, Serialize};

#[derive(Clone, Debug, Deserialize, Serialize)]
struct User {
    name: String,
    age: u32,
}

#[route("/json")]
struct JsonRoute;

impl ServerHook for JsonRoute {
    async fn new(_: &mut Stream, _: &mut Context) -> Self {
        Self
    }

    #[request_body_json(user: User)]
    async fn handle(self, stream: &mut Stream, ctx: &mut Context) -> Status {
        // user 可直接使用，类型为 User
        Status::Continue
    }
}
```

支持多参数：

```rust
#[request_body_json(user: User, config: Config)]
async fn handle(self, stream: &mut Stream, ctx: &mut Context) -> Status {
    Status::Continue
}
```

### JSON 请求体（安全方式，返回 Result）

```rust
#[request_body_json_result(user: User)]
async fn handle(self, stream: &mut Stream, ctx: &mut Context) -> Status {
    // user 类型为 Result<User, serde_json::Error>
    if let Ok(user_data) = user {
        // 使用 user_data
    }
    Status::Continue
}
```

> [!warning]
>
> `#[request_body_json]` 解析失败会 panic；`#[request_body_json_result]` 返回 `Result` 类型，可由开发者自行处理错误。

## 请求头提取

### 不安全获取（获取不到 panic）

```rust
#[route("/header")]
struct HeaderRoute;

impl ServerHook for HeaderRoute {
    async fn new(_: &mut Stream, _: &mut Context) -> Self {
        Self
    }

    #[request_header(HOST => host_value)]
    async fn handle(self, stream: &mut Stream, ctx: &mut Context) -> Status {
        // host_value 类型为 RequestHeadersValueItem
        Status::Continue
    }
}
```

### 安全获取（返回 Option）

```rust
#[try_get_request_header(HOST => host_value)]
async fn handle(self, stream: &mut Stream, ctx: &mut Context) -> Status {
    // host_value 类型为 Option<RequestHeadersValueItem>
    if let Some(host) = host_value {
        // 使用 host
    }
    Status::Continue
}
```

> [!tip]
>
> 请求头 key 使用框架常量（如 `HOST`、`CONTENT_TYPE`）或字符串字面量（如 `"X-Custom-Header"`）。

### 获取所有请求头

```rust
#[request_headers(headers)]
async fn handle(self, stream: &mut Stream, ctx: &mut Context) -> Status {
    // headers 类型为 RequestHeaders
    Status::Continue
}
```

支持多参数：

```rust
#[request_headers(h1, h2)]
async fn handle(self, stream: &mut Stream, ctx: &mut Context) -> Status {
    Status::Continue
}
```

## 查询参数提取

### 不安全获取（获取不到 panic）

```rust
#[request_query("key" => query_value)]
async fn handle(self, stream: &mut Stream, ctx: &mut Context) -> Status {
    // query_value 类型为 RequestQuerysValue
    Status::Continue
}
```

### 安全获取（返回 Option）

```rust
#[try_get_request_query("key" => query_value)]
async fn handle(self, stream: &mut Stream, ctx: &mut Context) -> Status {
    // query_value 类型为 Option<RequestQuerysValue>
    Status::Continue
}
```

### 获取所有查询参数

```rust
#[request_querys(querys)]
async fn handle(self, stream: &mut Stream, ctx: &mut Context) -> Status {
    // querys 类型为 RequestQuerys
    Status::Continue
}
```

支持多参数：

```rust
#[request_querys(q1, q2)]
async fn handle(self, stream: &mut Stream, ctx: &mut Context) -> Status {
    Status::Continue
}
```

## 请求路径提取

```rust
#[request_path(path)]
async fn handle(self, stream: &mut Stream, ctx: &mut Context) -> Status {
    // path 类型为 RequestPath
    Status::Continue
}
```

## 请求版本提取

```rust
#[request_version(version)]
async fn handle(self, stream: &mut Stream, ctx: &mut Context) -> Status {
    // version 类型为 RequestVersion
    Status::Continue
}
```

## Cookie 提取

### 不安全获取（获取不到 panic）

```rust
#[request_cookie("session_id" => session)]
async fn handle(self, stream: &mut Stream, ctx: &mut Context) -> Status {
    // session 类型为 String
    Status::Continue
}
```

### 安全获取（返回 Option）

```rust
#[try_get_request_cookie("session_id" => session)]
async fn handle(self, stream: &mut Stream, ctx: &mut Context) -> Status {
    // session 类型为 Option<String>
    Status::Continue
}
```

### 获取所有 Cookie 字符串

```rust
#[request_cookies(cookie_value)]
async fn handle(self, stream: &mut Stream, ctx: &mut Context) -> Status {
    // cookie_value 类型为 String（原始 Cookie 头字符串）
    Status::Continue
}
```

支持多参数：

```rust
#[request_cookies(c1, c2)]
async fn handle(self, stream: &mut Stream, ctx: &mut Context) -> Status {
    Status::Continue
}
```

<Bottom />
