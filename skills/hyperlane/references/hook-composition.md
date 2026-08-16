---
synced_from: docs-pages/src/hyperlane/usage-introduction/hook-composition.md@0c74235
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
> `hyperlane` 框架提供了 `prologue_macros` / `epilogue_macros` 和 `prologue_hooks` / `epilogue_hooks` 属性宏，
> 允许将多个属性宏组合在一起，以简化代码编写。

## prologue_macros

> [!tip]
>
> `prologue_macros` 在函数体之前注入代码，宏列表中的顺序为头部插入顺序（第一个宏是最外层）。

```rust
use hyperlane::*;
use hyperlane_macros::*;

#[route("/prologue_macros")]
struct PrologueMacrosRoute;

impl ServerHook for PrologueMacrosRoute {
    async fn new(_: &mut Stream, _: &mut Context) -> Self {
        Self
    }

    #[prologue_macros(is_post_method, response_body("prologue_macros"), send)]
    async fn handle(self, stream: &mut Stream, ctx: &mut Context) -> Status {
        Status::Continue
    }
}
```

## epilogue_macros

> [!tip]
>
> `epilogue_macros` 在函数体之后注入代码，宏列表中的顺序为尾部插入顺序（最后一个宏是最外层）。

```rust
use hyperlane::*;
use hyperlane_macros::*;

#[response_middleware(1)]
struct ResponseMiddleware;

impl ServerHook for ResponseMiddleware {
    async fn new(_: &mut Stream, _: &mut Context) -> Self {
        Self
    }

    #[epilogue_macros(try_send, flush)]
    async fn handle(self, stream: &mut Stream, ctx: &mut Context) -> Status {
        Status::Continue
    }
}
```

## prologue_hooks

> [!tip]
>
> `prologue_hooks` 在函数体之前注入代码，与 `prologue_macros` 不同的是，它接受函数名或方法表达式（而非属性宏名称）作为参数，在函数体前依次调用这些函数。每个钩子函数签名为 `async fn(&mut Stream, &mut Context) -> Status`。

```rust
async fn pre_check_hook(_: &mut Stream, ctx: &mut Context) -> Status {
    if ctx.get_request().get_method().is_get() {
        Status::Continue
    } else {
        Status::Reject
    }
}

#[prologue_hooks(pre_check_hook)]
async fn handle(self, stream: &mut Stream, ctx: &mut Context) -> Status {
    Status::Continue
}
```

## epilogue_hooks

> [!tip]
>
> `epilogue_hooks` 与 `epilogue_macros` 功能类似，区别在于它接受函数名或方法表达式作为参数，在函数体之后依次调用。每个钩子函数签名为 `async fn(&mut Stream, &mut Context) -> Status`。

```rust
async fn post_process_hook(_: &mut Stream, ctx: &mut Context) -> Status {
    Status::Continue
}

#[epilogue_hooks(post_process_hook)]
async fn handle(self, stream: &mut Stream, ctx: &mut Context) -> Status {
    Status::Continue
}
```

## 常用组合示例

### 请求方法过滤 + 响应 + 发送

```rust
use hyperlane::*;
use hyperlane_macros::*;

#[route("/combined")]
struct CombinedRoute;

impl ServerHook for CombinedRoute {
    async fn new(_: &mut Stream, _: &mut Context) -> Self {
        Self
    }

    #[prologue_macros(is_post_method, response_body("combined"), send)]
    async fn handle(self, stream: &mut Stream, ctx: &mut Context) -> Status {
        Status::Continue
    }
}
```

### 请求参数提取 + 响应 + 发送

```rust
use hyperlane::*;
use hyperlane_macros::*;

#[route("/query_combined/{id}")]
struct QueryCombinedRoute;

impl ServerHook for QueryCombinedRoute {
    async fn new(_: &mut Stream, _: &mut Context) -> Self {
        Self
    }

    #[prologue_macros(
        try_get_route_param("id" => id),
        response_body(&format!("id: {id:?}")),
        send
    )]
    async fn handle(self, stream: &mut Stream, ctx: &mut Context) -> Status {
        Status::Continue
    }
}
```

### 请求体提取 + 响应 + 发送

```rust
use hyperlane::*;
use hyperlane_macros::*;

#[route("/body_combined")]
struct BodyCombinedRoute;

impl ServerHook for BodyCombinedRoute {
    async fn new(_: &mut Stream, _: &mut Context) -> Self {
        Self
    }

    #[prologue_macros(
        request_body(body),
        response_body(&format!("body: {body:?}")),
        send
    )]
    async fn handle(self, stream: &mut Stream, ctx: &mut Context) -> Status {
        Status::Continue
    }
}
```

### 中间件中的组合

```rust
use hyperlane::*;
use hyperlane_macros::*;

#[request_middleware(1)]
struct RequestMiddleware;

impl ServerHook for RequestMiddleware {
    async fn new(_: &mut Stream, _: &mut Context) -> Self {
        Self
    }

    #[epilogue_macros(
        response_status_code(200),
        response_version(HttpVersion::Http1_1),
        response_header(SERVER => HYPERLANE)
    )]
    async fn handle(self, stream: &mut Stream, ctx: &mut Context) -> Status {
        Status::Continue
    }
}
```

<Bottom />
