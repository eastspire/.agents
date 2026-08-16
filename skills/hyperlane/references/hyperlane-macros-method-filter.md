---
synced_from: docs-pages/src/hyperlane-macros/method-filter.md@0c74235
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
> `hyperlane-macros` 提供了多种 HTTP 方法过滤属性宏，用于限制路由处理函数仅匹配特定 HTTP 方法。不匹配时直接返回 `Status::Continue`，跳过当前处理逻辑。

## 单方法过滤

使用 `is_${method}_method` 命名格式的属性宏，限制函数仅响应特定的 HTTP 方法：

```rust
use hyperlane::*;
use hyperlane_macros::*;

#[route("/get-only")]
struct GetOnly;

impl ServerHook for GetOnly {
    async fn new(_: &mut Stream, _: &mut Context) -> Self {
        Self
    }

    #[is_get_method]
    async fn handle(self, stream: &mut Stream, ctx: &mut Context) -> Status {
        Status::Continue
    }
}
```

### 可用宏列表

| 宏名称                 | 匹配的 HTTP 方法 |
| ---------------------- | ---------------- |
| `#[is_get_method]`     | GET              |
| `#[is_post_method]`    | POST             |
| `#[is_put_method]`     | PUT              |
| `#[is_delete_method]`  | DELETE           |
| `#[is_patch_method]`   | PATCH            |
| `#[is_head_method]`    | HEAD             |
| `#[is_options_method]` | OPTIONS          |
| `#[is_connect_method]` | CONNECT          |
| `#[is_trace_method]`   | TRACE            |
| `#[is_unknown_method]` | 非标准的未知方法 |

## 多方法过滤

使用 `#[methods(method1, method2, ...)]` 同时匹配多个 HTTP 方法，方法名使用小写标识符：

```rust
use hyperlane::*;
use hyperlane_macros::*;

#[route("/get-or-post")]
struct GetOrPost;

impl ServerHook for GetOrPost {
    async fn new(_: &mut Stream, _: &mut Context) -> Self {
        Self
    }

    #[methods(get, post)]
    async fn handle(self, stream: &mut Stream, ctx: &mut Context) -> Status {
        Status::Continue
    }
}
```

> [!tip]
>
> `#[methods]` 的参数是 Rust 标识符，**不是字符串**。正确写法：`#[methods(get, post)]`，而非 `#[methods("GET", "POST")]`。

## 在 impl 块中使用

这些宏也可以用于 `impl` 块中的方法：

```rust
impl GetOrPost {
    #[is_get_method]
    async fn handle_get(&self, stream: &mut Stream, ctx: &mut Context) -> Status {
        Status::Continue
    }

    #[methods(post, put)]
    async fn handle_post_or_put(&self, stream: &mut Stream, ctx: &mut Context) -> Status {
        Status::Continue
    }
}
```

## 独立函数中使用

方法过滤宏可以用于独立函数（非 `ServerHook` 实现）：

```rust
#[is_get_method]
async fn standalone_handler(stream: &mut Stream, ctx: &mut Context) -> Status {
    Status::Continue
}
```

## 与 prologue_macros 组合

```rust
#[prologue_macros(is_post_method, response_body("created"), send)]
async fn handle(self, stream: &mut Stream, ctx: &mut Context) -> Status {
    Status::Continue
}
```

<Bottom />
