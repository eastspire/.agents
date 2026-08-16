---
synced_from: docs-pages/src/hyperlane/usage-introduction/cookie.md@0c74235
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
> `hyperlane` 框架提供了完整的 `Cookie` 处理功能，支持请求和响应中的 `Cookie` 操作。

## 请求 Cookie 操作

### 获取请求所有 Cookie

```rust
// 尝试获取请求所有 Cookie
let cookies: Option<Cookies> = ctx.get_request().try_get_cookies();
// 获取请求所有 Cookie（获取不到则panic）
let cookies: Cookies = ctx.get_request().get_cookies();
```

### 获取请求特定 Cookie

```rust
// 尝试获取请求特定 Cookie
let cookie_value: Option<CookieValue> = ctx.get_request().try_get_cookie("session_id");
// 获取请求特定 Cookie（获取不到则panic）
let cookie_value: CookieValue = ctx.get_request().get_cookie("session_id");
```

> [!tip]
>
> `Cookie` 名称通常是自定义的，所以使用字符串字面量。但对于标准的请求头操作，建议使用框架常量。

## 响应 Cookie 操作

### 设置响应 Cookie

#### 使用字符串直接设置

```rust
ctx.get_mut_response().set_header(SET_COOKIE, "session_id=abc123; Path=/; HttpOnly");
```

#### 使用 CookieBuilder 构建

```rust
let cookie_value: String = CookieBuilder::new("session_id", "abc123")
    .set_path("/")
    .http_only()
    .build();
ctx.get_mut_response().set_header(SET_COOKIE, &cookie_value);
```

### 设置多个 Cookie

```rust
let session_cookie: String = CookieBuilder::new("session_id", "abc123")
    .set_max_age(3600)
    .set_path("/")
    .http_only()
    .secure()
    .build();

let pref_cookie: String = CookieBuilder::new("user_pref", "dark_mode")
    .set_max_age(86400)
    .set_path("/")
    .build();

ctx.get_mut_response()
    .add_header(SET_COOKIE, &session_cookie)
    .add_header(SET_COOKIE, &pref_cookie);
```

## 属性宏写法

> [!tip]
>
> 可以使用 `#[request_cookie]` 或 `#[try_get_request_cookie]` 属性宏提取请求 Cookie。

### 获取特定 Cookie（安全方式）

```rust
use hyperlane::*;
use hyperlane_macros::*;

#[route("/cookie")]
struct CookieRoute;

impl ServerHook for CookieRoute {
    async fn new(_: &mut Stream, _: &mut Context) -> Self {
        Self
    }

    #[response_body(&format!("Session cookie: {session_cookie1_option:?}, {session_cookie2_option:?}"))]
    #[try_get_request_cookie("test1" => session_cookie1_option, "test2" => session_cookie2_option)]
    async fn handle(self, stream: &mut Stream, ctx: &mut Context) -> Status {
        Status::Continue
    }
}
```

### 获取特定 Cookie（不安全方式，获取失败会 Panic）

```rust
use hyperlane::*;
use hyperlane_macros::*;

#[route("/cookie")]
struct CookieRoute;

impl ServerHook for CookieRoute {
    async fn new(_: &mut Stream, _: &mut Context) -> Self {
        Self
    }

    #[response_body(&format!("Session cookie: {session_cookie1}, {session_cookie2}"))]
    #[request_cookie("test1" => session_cookie1, "test2" => session_cookie2)]
    async fn handle(self, stream: &mut Stream, ctx: &mut Context) -> Status {
        Status::Continue
    }
}
```

### 获取所有 Cookie 字符串

> [!tip]
>
> 可以使用 `#[request_cookies]` 属性宏获取所有 Cookie 作为原始字符串。

```rust
use hyperlane::*;
use hyperlane_macros::*;

#[route("/cookies")]
struct CookiesRoute;

impl ServerHook for CookiesRoute {
    async fn new(_: &mut Stream, _: &mut Context) -> Self {
        Self
    }

    #[request_cookies(cookie_value)]
    async fn handle(self, stream: &mut Stream, ctx: &mut Context) -> Status {
        // cookie_value is available as String
        Status::Continue
    }
}
```

## CookieBuilder 方法

### 基本构建

```rust
let cookie: String = CookieBuilder::new("name", "value").build();
```

### 设置属性

```rust
let cookie: String = CookieBuilder::new("session", "token123")
    .set_expires("Wed, 21 Oct 2025 07:28:00 GMT")
    .set_domain("example.com")
    .set_same_site("Strict")
    .set_max_age(3600)
    .set_path("/")
    .secure()
    .http_only()
    .build();
```

### 解析现有 Cookie

```rust
let cookie_builder: CookieBuilder = CookieBuilder::parse("name=value; Path=/; HttpOnly");
let rebuilt_cookie: String = cookie_builder.build();
```

## 基本使用示例

### 会话管理

```rust
// 响应设置Cookie
let session_cookie: String = CookieBuilder::new("session", "token123")
    .set_max_age(3600)
    .http_only()
    .secure()
    .build();
ctx.get_mut_response().set_header(SET_COOKIE, &session_cookie);
// 请求读取Cookie
if let Some(session) = ctx.get_request().try_get_cookie("session") {}
```

### 清除 Cookie

```rust
let clear_cookie: String = CookieBuilder::new("session", "")
    .set_max_age(0)
    .build();
ctx.get_mut_response().set_header(SET_COOKIE, &clear_cookie);
```

<Bottom />
