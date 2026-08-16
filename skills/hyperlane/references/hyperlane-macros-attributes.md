---
synced_from: docs-pages/src/hyperlane-macros/attributes.md@0c74235
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
> `hyperlane-macros` 提供了属性宏用于提取上下文属性（Attribute）、Panic 数据和请求错误数据。

## 上下文属性提取

### 不安全获取（获取不到 panic）

```rust
use hyperlane::*;
use hyperlane_macros::*;

#[route("/attr")]
struct AttrRoute;

impl ServerHook for AttrRoute {
    async fn new(_: &mut Stream, _: &mut Context) -> Self {
        Self
    }

    #[attribute("key" => value: String)]
    async fn handle(self, stream: &mut Stream, ctx: &mut Context) -> Status {
        // value 类型为 String（获取不到则 panic）
        Status::Continue
    }
}
```

支持使用全局常量作为 key：

```rust
const ATTR_KEY: &str = "user_id";

#[attribute(ATTR_KEY => user_id: String)]
async fn handle(self, stream: &mut Stream, ctx: &mut Context) -> Status {
    Status::Continue
}
```

支持多参数：

```rust
#[attribute("key1" => attr1: String, "key2" => attr2: i32)]
async fn handle(self, stream: &mut Stream, ctx: &mut Context) -> Status {
    Status::Continue
}
```

### 安全获取（返回 Option）

```rust
#[try_get_attribute("key" => value: String)]
async fn handle(self, stream: &mut Stream, ctx: &mut Context) -> Status {
    // value 类型为 Option<String>
    if let Some(v) = value {
        // 使用 v
    }
    Status::Continue
}
```

### 获取所有属性

```rust
#[attributes(all_attrs)]
async fn handle(self, stream: &mut Stream, ctx: &mut Context) -> Status {
    // all_attrs 类型为 ThreadSafeAttributeStore
    Status::Continue
}
```

支持多参数：

```rust
#[attributes(attrs1, attrs2)]
async fn handle(self, stream: &mut Stream, ctx: &mut Context) -> Status {
    Status::Continue
}
```

## Panic 数据提取

### 安全获取（返回 Option）

```rust
#[try_get_task_panic_data(panic_data)]
async fn handle(self, stream: &mut Stream, ctx: &mut Context) -> Status {
    // panic_data 类型为 Option<PanicData>
    if let Some(data) = panic_data {
        // 处理 panic 数据
    }
    Status::Continue
}
```

### 不安全获取（获取不到 panic）

```rust
#[task_panic_data(panic_data)]
async fn handle(self, stream: &mut Stream, ctx: &mut Context) -> Status {
    // panic_data 类型为 PanicData（获取不到则 panic）
    Status::Continue
}
```

## 请求错误数据提取

### 安全获取（返回 Option）

```rust
#[try_get_request_error_data(error_data)]
async fn handle(self, stream: &mut Stream, ctx: &mut Context) -> Status {
    // error_data 类型为 Option<RequestError>
    if let Some(error) = error_data {
        // 处理错误
    }
    Status::Continue
}
```

### 不安全获取（获取不到 panic）

```rust
#[request_error_data(error_data)]
async fn handle(self, stream: &mut Stream, ctx: &mut Context) -> Status {
    // error_data 类型为 RequestError（获取不到则 panic）
    Status::Continue
}
```

> [!tip]
>
> Panic 数据和请求错误数据通常在 `#[task_panic]` 和 `#[request_error]` 钩子中使用，用于获取异常信息。

<Bottom />
