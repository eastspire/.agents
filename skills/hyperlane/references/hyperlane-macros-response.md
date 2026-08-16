---
synced_from: docs-pages/src/hyperlane-macros/response.md@0c74235
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

> [!tip]
>
> `hyperlane-macros` 提供了多种响应设置属性宏，用于在路由处理函数中便捷地设置 HTTP 响应的各个部分，无需手动操作 `ctx.get_mut_response()`。

## 设置响应状态码

```rust
use hyperlane::*;
use hyperlane_macros::*;

#[route("/ok")]
struct OkRoute;

impl ServerHook for OkRoute {
    async fn new(_: &mut Stream, _: &mut Context) -> Self {
        Self
    }

    #[response_status_code(200)]
    async fn handle(self, stream: &mut Stream, ctx: &mut Context) -> Status {
        Status::Continue
    }
}
```

也支持使用全局常量：

```rust
const CUSTOM_STATUS: i32 = 201;

#[response_status_code(CUSTOM_STATUS)]
async fn handle(self, stream: &mut Stream, ctx: &mut Context) -> Status {
    Status::Continue
}
```

## 设置响应原因短语

```rust
#[response_reason_phrase("OK")]
async fn handle(self, stream: &mut Stream, ctx: &mut Context) -> Status {
    Status::Continue
}
```

支持使用全局常量：

```rust
const CUSTOM_REASON: &str = "Accepted";

#[response_reason_phrase(CUSTOM_REASON)]
async fn handle(self, stream: &mut Stream, ctx: &mut Context) -> Status {
    Status::Continue
}
```

## 设置响应头

`#[response_header]` 支持两种语法：

### 替换响应头（set 操作）

使用 `=>` 语法，替换同名响应头的现有值：

```rust
#[response_header(SERVER => HYPERLANE)]
async fn handle(self, stream: &mut Stream, ctx: &mut Context) -> Status {
    Status::Continue
}
```

### 添加响应头（add 操作）

使用逗号分隔的语法，保留同名响应头的现有值：

```rust
#[response_header(SET_COOKIE, "session_id=abc123")]
async fn handle(self, stream: &mut Stream, ctx: &mut Context) -> Status {
    Status::Continue
}
```

> [!tip]
>
> 参数可以是字符串字面量或全局常量：`#[response_header(CONTENT_TYPE => APPLICATION_JSON)]`

## 设置响应体

```rust
#[response_body("Hello World")]
async fn handle(self, stream: &mut Stream, ctx: &mut Context) -> Status {
    Status::Continue
}
```

支持使用全局常量：

```rust
const RESPONSE_DATA: &str = "{\"status\": \"success\"}";

#[response_body(&RESPONSE_DATA)]
async fn handle(self, stream: &mut Stream, ctx: &mut Context) -> Status {
    Status::Continue
}
```

## 设置响应版本

```rust
#[response_version(HttpVersion::Http1_1)]
async fn handle(self, stream: &mut Stream, ctx: &mut Context) -> Status {
    Status::Continue
}
```

## 清空所有响应头

```rust
#[clear_response_headers]
async fn handle(self, stream: &mut Stream, ctx: &mut Context) -> Status {
    Status::Continue
}
```

## 组合使用

```rust
#[prologue_macros(
    response_status_code(200),
    response_version(HttpVersion::Http1_1),
    response_header(CONTENT_TYPE => APPLICATION_JSON),
    response_body("{\"status\":\"ok\"}"),
    send
)]
async fn handle(self, stream: &mut Stream, ctx: &mut Context) -> Status {
    Status::Continue
}
```

<Bottom />
