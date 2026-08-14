---
synced_from: docs-pages/src/hyperlane/usage-introduction/attribute.md@f972247
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
> `hyperlane` 框架支持临时上下文属性以 `key-value` 形式存储，生命周期贯穿一个完整的请求和响应。
> 存储的 `value` 支持实现了`Any + Send + Sync + Clone` 的 `trait` 的类型。

### 设置某个临时上下文属性

```rust
ctx.set_attribute("key", "value");
```

### 获取某个临时上下文属性

```rust
let value: Option<String> = ctx.try_get_attribute("key");
```

### 移除某个临时上下文属性

```rust
ctx.remove_attribute("key");
```

### 清空临时上下文属性

```rust
ctx.clear_attribute();
```

### 属性宏写法

> [!tip]
>
> 可以使用 `#[attribute]`、`#[try_get_attribute]` 或 `#[attributes]` 属性宏提取上下文属性。

#### 安全获取属性（返回 Option）

```rust
use hyperlane::*;
use hyperlane_macros::*;

#[route("/attribute")]
struct AttributeRoute;

impl ServerHook for AttributeRoute {
    async fn new(_: &mut Stream, _: &mut Context) -> Self {
        Self
    }

    #[try_get_attribute("key" => value: String)]
    async fn handle(self, stream: &mut Stream, ctx: &mut Context) -> Status {
        if let Some(v) = value {
            // use v
        }
        Status::Continue
    }
}
```

#### 不安全获取属性（获取属性失败会 Panic）

```rust
use hyperlane::*;
use hyperlane_macros::*;

#[route("/attribute")]
struct AttributeRoute;

impl ServerHook for AttributeRoute {
    async fn new(_: &mut Stream, _: &mut Context) -> Self {
        Self
    }

    #[attribute("key" => value: String)]
    async fn handle(self, stream: &mut Stream, ctx: &mut Context) -> Status {
        // value is available directly
        Status::Continue
    }
}
```

### 额外示例

#### 设置闭包

> [!tip]
>
> 闭包需要实现 `Send + Sync` 的 `trait`，否则无法跨线程调用。
> 不推荐 `value` 存储函数，这里只是提供一个示例

> [!warning]
>
> 存储的 `value` 必须实现 `AnySendSyncClone` trait（即 `Any + Send + Sync + Clone`）。
> 基本类型如 `String`、`i32`、`Vec<u8>` 等已自动实现此 trait。
> 闭包类型需要手动实现 `Clone`，不推荐存储函数。

**此示例为安全获取属性**

```rust
ctx.set_attribute("key", "value");
if let Some(value) = ctx.try_get_attribute::<String>("key") {
    println!("value: {value}");
}
```

**此示例为不安全获取属性（获取属性失败会Panic）**

```rust
ctx.set_attribute("key", "value");
let value: String = ctx.get_attribute("key");
```

<Bottom />
