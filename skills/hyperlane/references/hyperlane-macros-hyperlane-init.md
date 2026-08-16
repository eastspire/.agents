---
synced_from: docs-pages/src/hyperlane-macros/hyperlane-init.md@0c74235
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
> `hyperlane-macros` 提供了 `#[hyperlane]` 属性宏用于简化 Server 初始化，以及 `context!` 函数宏用于在 unsafe 上下文中转换 Context 指针引用。

## #[hyperlane] 属性宏

`#[hyperlane]` 属性宏用于自动创建指定类型的实例，支持一个或多个变量类型对。当类型为 `Server` 时，自动从 inventory 注册表收集并注册所有钩子（路由、中间件等）。

### 基本用法

```rust
use hyperlane::*;
use hyperlane_macros::*;

#[hyperlane(server: Server)]
#[hyperlane(server_config: ServerConfig)]
#[tokio::main]
async fn main() {
    server_config.set_nodelay(Some(false));
    server.server_config(server_config);
    let server_control_hook: ServerControlHook = server.run().await.unwrap_or_default();
    server_control_hook.wait().await;
}
```

### 单次调用多变量

```rust
#[hyperlane(server: Server, server_config: ServerConfig)]
#[tokio::main]
async fn main() {
    server_config.set_nodelay(Some(false));
    server.server_config(server_config);
    let server_control_hook: ServerControlHook = server.run().await.unwrap_or_default();
    server_control_hook.wait().await;
}
```

### 在 impl 块中使用

```rust
struct ServerInitializer;

impl ServerInitializer {
    #[hyperlane(server: Server)]
    #[hyperlane(server_config: ServerConfig)]
    async fn initialize() -> Server {
        server
    }

    #[hyperlane(server: Server)]
    async fn initialize_default() -> Server {
        server
    }
}
```

> [!tip]
>
> 当类型为 `Server` 时，`#[hyperlane]` 会自动调用 `HookType::assert_unique_order` 检查钩子顺序唯一性，然后按顺序将所有已注册的钩子（`#[route]`、`#[request_middleware]` 等）注入到 server 实例中。

## context! 函数宏

`context!` 是一个函数式宏，用于将 Context 指针转换为 Rust 引用，主要用于在 unsafe 上下文中重新获得对 `Box` 分配的 `Context` 或 `Stream` 的控制权。

### 基本用法

```rust
use hyperlane::*;
use hyperlane_macros::*;

async fn handle(ctx: &mut Context) {
    // 转换为可变引用
    let ctx_ref: &mut Context = unsafe { context!(ctx: &mut Context) };
    let _ = ctx_ref.get_mut_response();
}
```

### 不可变引用

```rust
async fn read_only(ctx: &mut Context) {
    let ctx_ref: &Context = unsafe { context!(ctx: &Context) };
    let _ = ctx_ref.get_request();
}
```

### 省略类型标注（默认不可变）

```rust
async fn default_ref(ctx: &mut Context) {
    let ctx_ref = unsafe { context!(ctx) };
    let _ = ctx_ref.get_request();
}
```

### 实际应用场景

```rust
#[route("/context-demo")]
struct ContextDemo;

impl ServerHook for ContextDemo {
    async fn new(_: &mut Stream, _: &mut Context) -> Self {
        Self
    }

    async fn handle(self, _: &mut Stream, ctx: &mut Context) -> Status {
        let new_ctx: &mut Context = unsafe { context!(ctx: &mut Context) };
        let _ = new_ctx.get_mut_response();
        Status::Continue
    }
}
```

> [!warning]
>
> `context!` 宏生成 unsafe 代码，调用者必须确保指针在转换时是有效的。通常在框架内部的异步回调中使用，普通路由处理中无需使用。

<Bottom />
