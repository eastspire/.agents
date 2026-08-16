---
synced_from: docs-pages/src/hyperlane/usage-introduction/response.md@0c74235
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
> `hyperlane` 框架默认的 `Response` 会自动设置版本为 `Http1_1`、状态码为 `200`，发送响应前通过 `ctx` 中 `get_response` 获取的只是响应的初始化实例，里面其实没有数据，
> 只有当用户发送响应时才会构建出完整 `http` 响应，此后再次 `get_response` 才能获取到响应内容。

> [!tip]
>
> `hyperlane` 框架对 `ctx` 额外封装了子字段的方法，可以直接调用大部分子字段的 `get` 和 `set` 方法名称，
> 例如：调用 `response` 上的 `get_status_code` 方法。
>
> **调用规律**
>
> - 原 `response` 的 `get` 方法的 `get` 名称后加 `response` 名称，中间使用\_拼接。
> - 原 `response` 的 `set` 方法的 `set` 名称后加 `response` 名称，中间使用\_拼接。

### 获取响应

#### 获取 `response`

```rust
let response: &Response = ctx.get_response();
```

#### 获取响应版本

```rust
let version: &ResponseVersion = ctx.get_response().get_version();
```

#### 获取响应状态码

```rust
let status_code: ResponseStatusCode = ctx.get_response().get_status_code();
```

#### 获取响应原因短语

```rust
let reason_phrase: &ResponseReasonPhrase = ctx.get_response().get_reason_phrase();
```

#### 获取完整响应头

```rust
let headers: &ResponseHeaders = ctx.get_response().get_headers();
```

#### 获取某个响应头

```rust
// 尝试获取响应头
let value: Option<ResponseHeadersValue> = ctx.get_response().try_get_header(CONTENT_TYPE);
// 获取响应头（获取不到则panic）
let value: ResponseHeadersValue = ctx.get_response().get_header(CONTENT_TYPE);
```

#### 获取响应头的第一个值

```rust
// 尝试获取响应头的第一个值
let header_value: Option<ResponseHeadersValueItem> = ctx.get_response().try_get_header_front(CONTENT_TYPE);
// 获取响应头的第一个值（获取不到则panic）
let header_value: ResponseHeadersValueItem = ctx.get_response().get_header_front(CONTENT_TYPE);
```

#### 获取响应头的最后一个值

```rust
// 尝试获取响应头的最后一个值
let header_value: Option<ResponseHeadersValueItem> = ctx.get_response().try_get_header_back(CONTENT_TYPE);
// 获取响应头的最后一个值（获取不到则panic）
let header_value: ResponseHeadersValueItem = ctx.get_response().get_header_back(CONTENT_TYPE);
```

#### 检查是否存在特定响应头

```rust
let has_header: bool = ctx.get_response().has_header(CONTENT_TYPE);
```

#### 检查响应头是否包含特定值

```rust
let has_value: bool = ctx.get_response().has_header_value(CONTENT_TYPE, APPLICATION_JSON);
```

#### 获取响应头数量

```rust
let headers_count: usize = ctx.get_response().get_headers_size();
```

#### 获取响应头值的数量

```rust
// 尝试获取响应头值的数量
let header_count: Option<usize> = ctx.get_response().try_get_header_size(CONTENT_TYPE);
// 获取响应头值的数量（获取不到则panic）
let header_count: usize = ctx.get_response().get_header_size(CONTENT_TYPE);
```

#### 获取所有响应头值的总数量

```rust
let total_values: usize = ctx.get_response().get_headers_values_size();
```

#### 获取响应体

```rust
let body: &ResponseBody = ctx.get_response().get_body();
```

#### 获取 `string` 格式的响应体

```rust
let body: String = ctx.get_response().get_body_string();
```

#### 获取 `json` 格式的响应体

```rust
// 反序列化响应体
let body: Result<T, serde_json::Error> = ctx.get_response().try_get_body_json::<T>();
// 反序列化响应体（反序列化失败则panic）
let body: T = ctx.get_response().get_body_json::<T>();
```

### 设置响应

#### 设置 `response`

```rust
ctx.get_mut_response().set_response(Response::default());
```

#### 设置响应版本

```rust
ctx.get_mut_response().set_version(HttpVersion::Http1_1);
```

#### 设置响应状态码

```rust
ctx.get_mut_response().set_status_code(200);
```

#### 设置响应原因短语

```rust
ctx.get_mut_response().set_reason_phrase("OK");
```

#### 设置响应体

```rust
ctx.get_mut_response().set_body("Hello World");
```

#### 设置（添加）响应头

> [!tip]
>
> `hyperlane` 框架对响应头的 `key` 是不做大小写处理的，建议使用框架定义的常量。

```rust
ctx.get_mut_response().add_header(SERVER, "hyperlane");
```

#### 设置（替换）响应头

```rust
ctx.get_mut_response().set_header(CONTENT_TYPE, APPLICATION_JSON);
```

#### 移除响应头

```rust
ctx.get_mut_response().remove_header(CONTENT_TYPE);
```

#### 移除响应头的特定值

```rust
ctx.get_mut_response().remove_header_value(CONTENT_TYPE, APPLICATION_JSON);
```

#### 清空所有响应头

```rust
ctx.get_mut_response().clear_headers();
```

## 属性宏写法

> [!tip]
>
> `hyperlane` 框架提供了属性宏来简化响应信息的设置，可以在 `handle` 方法上使用属性宏自动设置响应信息。

### 设置响应状态码

```rust
use hyperlane::*;
use hyperlane_macros::*;

#[route("/response_status_code")]
struct ResponseStatusCodeRoute;

impl ServerHook for ResponseStatusCodeRoute {
    async fn new(_: &mut Stream, _: &mut Context) -> Self {
        Self
    }

    #[response_status_code(200)]
    async fn handle(self, stream: &mut Stream, ctx: &mut Context) -> Status {
        Status::Continue
    }
}
```

### 设置响应版本

```rust
#[response_version(HttpVersion::Http1_1)]
async fn handle(self, stream: &mut Stream, ctx: &mut Context) -> Status {
    Status::Continue
}
```

### 设置响应原因短语

```rust
#[response_reason_phrase("OK")]
async fn handle(self, stream: &mut Stream, ctx: &mut Context) -> Status {
    Status::Continue
}
```

### 设置响应头

> [!tip]
>
> `#[response_header]` 属性宏支持两种语法：
>
> - `KEY => VALUE`：替换（set）操作，替换同名响应头的值。
> - `KEY, VALUE`：添加（add）操作，保留同名响应头的现有值。

#### 替换响应头（set 操作）

```rust
#[response_header(SERVER => HYPERLANE)]
async fn handle(self, stream: &mut Stream, ctx: &mut Context) -> Status {
    Status::Continue
}
```

#### 添加响应头（add 操作）

```rust
#[response_header(SET_COOKIE, "session_id=abc123")]
async fn handle(self, stream: &mut Stream, ctx: &mut Context) -> Status {
    Status::Continue
}
```

### 设置响应体

```rust
#[response_body("Hello World")]
async fn handle(self, stream: &mut Stream, ctx: &mut Context) -> Status {
    Status::Continue
}
```

### 清空所有响应头

```rust
#[clear_response_headers]
async fn handle(self, stream: &mut Stream, ctx: &mut Context) -> Status {
    Status::Continue
}
```

### 转字符串

#### 通过 `to_string`

> [!tip]
>
> 将获得完整的原始结构体字符串结构。

```rust
ctx.get_response().to_string();
```

<Bottom />
