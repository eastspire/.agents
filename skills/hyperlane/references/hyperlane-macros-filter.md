---
synced_from: docs-pages/src/hyperlane-macros/filter.md@f972247
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
> `hyperlane-macros` 提供了请求过滤和拒绝的属性宏，可根据条件控制请求是否继续处理。

## filter（条件过滤）

当条件为 `true` 时继续执行，条件不满足时返回 `Status::Continue` 跳过当前处理：

```rust
use hyperlane::*;
use hyperlane_macros::*;

#[route("/filter")]
struct FilterRoute;

impl ServerHook for FilterRoute {
    async fn new(_: &mut Stream, _: &mut Context) -> Self {
        Self
    }

    #[filter(ctx.get_request().get_method().is_get())]
    async fn handle(self, stream: &mut Stream, ctx: &mut Context) -> Status {
        // 只有 GET 请求到达这里
        Status::Continue
    }
}
```

## reject（条件拒绝）

当条件为 `true` 时拒绝请求（返回 `Status::Reject`）：

```rust
#[reject(ctx.get_request().get_method().is_post())]
async fn handle(self, stream: &mut Stream, ctx: &mut Context) -> Status {
    // POST 请求会被拒绝，不会到达这里
    Status::Continue
}
```

## Host 过滤

### host — 仅匹配指定 Host

只有请求的 Host 头匹配指定值时才会执行：

```rust
#[route("/host-filter")]
struct HostFilterRoute;

impl ServerHook for HostFilterRoute {
    async fn new(_: &mut Stream, _: &mut Context) -> Self {
        Self
    }

    #[host("example.com")]
    async fn handle(self, stream: &mut Stream, ctx: &mut Context) -> Status {
        // 只有 Host: example.com 的请求到达这里
        Status::Continue
    }
}
```

### reject_host — 拒绝匹配指定 Host

当请求的 Host 头匹配指定值时拒绝请求：

```rust
#[reject_host("blocked.com")]
async fn handle(self, stream: &mut Stream, ctx: &mut Context) -> Status {
    // Host: blocked.com 的请求被拒绝
    Status::Continue
}
```

## Referer 过滤

### referer — 仅匹配指定 Referer

只有请求的 Referer 头匹配指定值时才会执行：

```rust
#[route("/referer-filter")]
struct RefererFilterRoute;

impl ServerHook for RefererFilterRoute {
    async fn new(_: &mut Stream, _: &mut Context) -> Self {
        Self
    }

    #[referer("https://trusted-site.com")]
    async fn handle(self, stream: &mut Stream, ctx: &mut Context) -> Status {
        // 只有从 trusted-site.com 来的请求到达这里
        Status::Continue
    }
}
```

### reject_referer — 拒绝匹配指定 Referer

当请求的 Referer 头匹配指定值时拒绝请求：

```rust
#[reject_referer("https://malicious.com")]
async fn handle(self, stream: &mut Stream, ctx: &mut Context) -> Status {
    // 从 malicious.com 来的请求被拒绝
    Status::Continue
}
```

## 与 prologue_macros 组合

```rust
#[prologue_macros(
    reject_host("spam.example.com"),
    filter(ctx.get_request().get_method().is_get()),
    response_body("filtered response"),
    send
)]
async fn handle(self, stream: &mut Stream, ctx: &mut Context) -> Status {
    Status::Continue
}
```

<Bottom />
