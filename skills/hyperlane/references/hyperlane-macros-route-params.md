---
synced_from: docs-pages/src/hyperlane-macros/route-params.md@0c74235
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
> `hyperlane-macros` 提供了路由参数提取属性宏，用于从动态路由 URL 中提取参数值。

## 不安全获取（获取不到 panic）

```rust
use hyperlane::*;
use hyperlane_macros::*;

#[route("/user/{id}")]
struct UserRoute;

impl ServerHook for UserRoute {
    async fn new(_: &mut Stream, _: &mut Context) -> Self {
        Self
    }

    #[route_param("id" => id)]
    async fn handle(self, stream: &mut Stream, ctx: &mut Context) -> Status {
        // id 类型为 String（获取不到则 panic）
        Status::Continue
    }
}
```

支持多参数：

```rust
#[route("/user/{id}/post/{post_id}")]
struct UserPostRoute;

impl ServerHook for UserPostRoute {
    async fn new(_: &mut Stream, _: &mut Context) -> Self {
        Self
    }

    #[route_param("id" => id, "post_id" => post_id)]
    async fn handle(self, stream: &mut Stream, ctx: &mut Context) -> Status {
        Status::Continue
    }
}
```

## 安全获取（返回 Option）

```rust
#[try_get_route_param("id" => id)]
async fn handle(self, stream: &mut Stream, ctx: &mut Context) -> Status {
    // id 类型为 Option<String>
    if let Some(user_id) = id {
        // 使用 user_id
    }
    Status::Continue
}
```

## 获取所有路由参数

```rust
#[route_params(params)]
async fn handle(self, stream: &mut Stream, ctx: &mut Context) -> Status {
    // params 类型为 RouteParams (HashMap<String, String>)
    Status::Continue
}
```

支持多参数：

```rust
#[route_params(p1, p2)]
async fn handle(self, stream: &mut Stream, ctx: &mut Context) -> Status {
    Status::Continue
}
```

## 动态路由注册

路由参数在路径中使用 `{param_name}` 语法：

```rust
#[route("/user/{id}")]
struct UserRoute;

#[route("/post/{post_id}")]
struct PostRoute;

// 正则表达式动态路由：/user/{id:\d+}
#[route("/user/{id:\d+}")]
struct UserWithIdRoute;

// 尾部正则匹配：/files/{path:^.*$}
#[route("/files/{path:^.*$}")]
struct FileRoute;
```

> [!tip]
>
> - `{key}` — 朴素动态路由，匹配一个路径段
> - `{key:regex}` — 正则动态路由，在路径末尾时匹配后续所有路径段

<Bottom />
