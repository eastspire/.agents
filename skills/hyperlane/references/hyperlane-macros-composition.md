---
synced_from: docs-pages/src/hyperlane-macros/composition.md@f972247
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
> `hyperlane-macros` 提供了四种宏组合方式：`prologue_macros` / `epilogue_macros` 用于组合属性宏，`prologue_hooks` / `epilogue_hooks` 用于组合函数调用。

## prologue_macros

在函数体之前注入代码，宏列表按头部插入顺序应用（第一个宏是最外层）。适用于组合多个属性宏：

```rust
use hyperlane::*;
use hyperlane_macros::*;

#[route("/prologue")]
struct PrologueRoute;

impl ServerHook for PrologueRoute {
    async fn new(_: &mut Stream, _: &mut Context) -> Self {
        Self
    }

    #[prologue_macros(is_post_method, response_body("prologue"), send)]
    async fn handle(self, stream: &mut Stream, ctx: &mut Context) -> Status {
        Status::Continue
    }
}
```

## epilogue_macros

在函数体之后注入代码，宏列表按尾部插入顺序应用（最后一个宏是最外层）：

```rust
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

在函数体之前注入代码，但接受的是**函数名或方法表达式**（而非属性宏）。每个钩子函数签名为 `async fn(&mut Stream, &mut Context) -> Status`：

```rust
async fn check_auth(stream: &mut Stream, ctx: &mut Context) -> Status {
    if ctx.get_request().has_header(AUTHORIZATION) {
        Status::Continue
    } else {
        Status::Reject
    }
}

#[route("/auth")]
struct AuthRoute;

impl ServerHook for AuthRoute {
    async fn new(_: &mut Stream, _: &mut Context) -> Self {
        Self
    }

    #[prologue_hooks(check_auth)]
    #[response_body("authenticated")]
    async fn handle(self, stream: &mut Stream, ctx: &mut Context) -> Status {
        Status::Continue
    }
}
```

支持方法表达式：

```rust
impl AuthRoute {
    async fn log_request(_: &mut Stream, ctx: &mut Context) -> Status {
        println!("Request: {}", ctx.get_request().get_path());
        Status::Continue
    }
}

#[prologue_hooks(AuthRoute::log_request, check_auth)]
async fn handle(self, stream: &mut Stream, ctx: &mut Context) -> Status {
    Status::Continue
}
```

## epilogue_hooks

在函数体之后注入代码，接受函数名或方法表达式：

```rust
async fn cleanup(stream: &mut Stream, ctx: &mut Context) -> Status {
    // 清理资源
    Status::Continue
}

#[epilogue_hooks(cleanup)]
async fn handle(self, stream: &mut Stream, ctx: &mut Context) -> Status {
    Status::Continue
}
```

## 组合使用

```rust
#[prologue_macros(
    try_get_route_param("id" => id),
    response_body(&format!("id: {id:?}")),
    send
)]
async fn handle(self, stream: &mut Stream, ctx: &mut Context) -> Status {
    Status::Continue
}
```

<Bottom />
