---
name: hyperlane-plugin-websocket
description: "WebSocket plugin for the hyperlane framework at v14.0.15. Self-registers via `inventory::submit!` so `Server::new().await` picks it up automatically. Pairs a `WebSocket` handler (per-connection lifecycle: connected / request / sended / closed hooks) with `hyperlane-broadcast`'s `Broadcast<T>` / `BroadcastMap<T>` for fanout across multiple WebSocket subscribers grouped by `BroadcastType<T>`. Use when adding WebSocket to a hyperlane server, when fanning out events to multiple connected clients, or when wiring `set_connected_hook` / `set_request_hook` / `set_sended_hook` / `set_closed_hook` callbacks. Triggers: hyperlane-plugin-websocket, WebSocket, BroadcastType, BroadcastTypeTrait, WebSocketConfig, websocket plugin, inventory self-register, hyperlane websocket."
license: MIT
---

# hyperlane-plugin-websocket

- GitHub: <https://github.com/hyperlane-dev/hyperlane-plugin-websocket.git>
- crates.io: <https://crates.io/crates/hyperlane-plugin-websocket>
- docs.rs: <https://docs.rs/hyperlane-plugin-websocket>

> A WebSocket plugin for the Hyperlane framework, providing robust WebSocket communication capabilities and integrating with hyperlane-broadcast for efficient message dissemination.

## Overview

`D:\code\hyperlane-plugin-websocket` v14.0.15 — single-crate library at `D:\code\hyperlane-plugin-websocket\src`. Two key types:

- `WebSocket<'a, B>` — per-connection handler bound to a hyperlane `Context`. Configures capacity, context, broadcast type, and 4 lifecycle hooks (`connected` / `request` / `sended` / `closed`).
- `WebSocketConfig<'a, B: BroadcastTypeTrait>` — built via the `WebSocket::new(stream, context).set_*` chain; passed to `WebSocketServer::run`.

Plus `WebSocketServer` (registered as a global singleton via `inventory::submit!`) holding the broadcast fanout state, with `send` / `try_send` / `receiver_count` methods.

Top-level module files (keyword-per-file):

```text
src/lib.rs            ← re-export facade + inventory submit
src/const.rs          ← constants
src/enum.rs           ← BroadcastType<T>
src/struct.rs         ← WebSocket, WebSocketConfig
src/trait.rs          ← BroadcastTypeTrait
src/impl.rs           ← all impl blocks
```

## 项目元信息

- crate 名: `hyperlane-plugin-websocket`
- 版本: `14.0.15`
- Rust edition: `2024`
- License: `MIT`
- 类型: 单 crate 库（含 proc-style inventory 自动注册）
- 关键字: `http`, `request`, `response`, `tcp`, `redirect`
- 依赖: `hyperlane 21.3.3`, `hyperlane-broadcast 2.0.9`
- Profile dev: `incremental = true, opt-level = 3, lto = true`
- Profile release: `incremental = false, opt-level = 3, lto = true, codegen-units = 1, strip = "debuginfo"`

## Installation

```shell
cargo add hyperlane-plugin-websocket
```

`hyperlane-plugin-websocket 14.x` requires `hyperlane-broadcast 2.x` — pin both together. The plugin self-registers via `inventory::submit!` so `Server::new().await` picks it up automatically; no explicit `plugin.register()` call is needed.

## `BroadcastType<T>` and `BroadcastTypeTrait`

From `src/enum.rs` and `src/trait.rs`:

```rust
pub trait BroadcastTypeTrait: ToString + PartialOrd + Clone
pub enum BroadcastType<T: BroadcastTypeTrait> { /* concrete variants */ }
```

`BroadcastType<T>` is the key hyperlane-plugin-websocket uses to multiplex connections across logical channels. Common impls in the codebase:

- `BroadcastType::Group(String)` — fanout to all sockets in a named group
- `BroadcastType::User(String)` — fanout to all sockets owned by a user ID
- `BroadcastType::All` — fanout to every connected socket

`BroadcastTypeTrait` requires `ToString + PartialOrd + Clone` — the trait bound lets the plugin hash the key into a `String` for `BroadcastMap<String, …>` lookup while keeping `<` available for sorted iteration.

## `WebSocketConfig<'a, B>` — built via chainable setters

From `src/struct.rs` + `src/impl.rs`:

```rust
pub struct WebSocket<'a, B: BroadcastTypeTrait> { /* … */ }
pub struct WebSocketConfig<'a, B: BroadcastTypeTrait> { /* … */ }

impl<'a, B: BroadcastTypeTrait> WebSocket<'a, B> {
    pub fn new(stream: &'a mut Stream, context: &'a mut Context) -> Self
    pub fn set_capacity(mut self, capacity: Capacity) -> Self
    pub fn set_context(mut self, context: &'a mut Context) -> Self
    pub fn set_broadcast_type(mut self, broadcast_type: BroadcastType<B>) -> Self
    pub fn set_connected_hook<S>(mut self) -> Self
    pub fn set_request_hook<S>(mut self) -> Self
    pub fn set_sended_hook<S>(mut self) -> Self
    pub fn set_closed_hook<S>(mut self) -> Self

    pub fn get_stream(&mut self) -> &mut Stream
    pub fn get_context(&mut self) -> &mut Context
    pub fn get_capacity(&self) -> Capacity
    pub fn get_broadcast_type(&self) -> &BroadcastType<B>
    pub fn get_connected_hook(&self) -> &ServerHookHandler
    pub fn get_request_hook(&self) -> &ServerHookHandler
    pub fn get_sended_hook(&self) -> &ServerHookHandler
    pub fn get_closed_hook(&self) -> &ServerHookHandler
}
```

Each `set_*` consumes and returns `self` (chainable). The 4 hook setters register a `ServerHookHandler` for the corresponding lifecycle stage.

## `WebSocketServer` — broadcast fanout

From `src/impl.rs` (the global singleton registered via `inventory::submit!`):

```rust
impl WebSocketServer {
    pub fn new() -> Self
    pub fn receiver_count<B>(&self, broadcast_type: BroadcastType<B>) -> ReceiverCount
    pub fn receiver_count_before_connected<B>(&self, broadcast_type: BroadcastType<B>) -> ReceiverCount
    pub fn receiver_count_after_closed<B>(&self, broadcast_type: BroadcastType<B>) -> ReceiverCount
    pub fn send<T, B>(&self, broadcast_type: BroadcastType<B>, data: T) -> Option<ReceiverCount>
    pub fn try_send<T, B>(&self, broadcast_type: BroadcastType<B>, data: T) -> Result<Option<ReceiverCount>, SendError<T>>
    pub async fn run<B>(&self, websocket_config: WebSocketConfig<'_, B>)
}
```

`WebSocketServer::run` is the per-connection async loop. Once a connection's lifecycle ends (close / error / panic), it removes the connection from its `BroadcastMap` so future `send` calls don't dead-letter.

## Helper: `get_key`

```rust
pub fn get_key<B: BroadcastTypeTrait>(broadcast_type: BroadcastType<B>) -> String
```

Converts any `BroadcastType<B>` to the `String` key used by the underlying `BroadcastMap<String, Broadcast<T>>`. Most callers won't need this directly.

## Usage

Per-connection handler:

```rust
use hyperlane_plugin_websocket::*;
use hyperlane::*;

async fn ws_handler(stream: &mut Stream, ctx: &mut Context) {
    let ws: WebSocket<BroadcastType<String>> = WebSocket::new(stream, ctx)
        .set_capacity(1024)
        .set_broadcast_type(BroadcastType::Group("chat-room-1".into()))
        .set_connected_hook::<on_connected>()
        .set_request_hook::<on_request>()
        .set_sended_hook::<on_sended>()
        .set_closed_hook::<on_closed>();

    WebSocketServer::new().run(ws.build_config()).await;
}
```

Server-side broadcast:

```rust
let server: WebSocketServer = WebSocketServer::new();
let count: Option<ReceiverCount> = server.send(
    BroadcastType::Group("chat-room-1".into()),
    "hello world".to_string(),
);
```

## Lifecycle hooks (4 stages)

| Hook | Fires when | Typical use |
|---|---|---|
| `set_connected_hook` | After WebSocket upgrade succeeds, before first message | Auth check, register connection in `BroadcastMap`, send welcome |
| `set_request_hook`   | On every inbound frame from client | Parse + dispatch to a service fn |
| `set_sended_hook`    | After a frame is written to the socket | Log + update metrics |
| `set_closed_hook`    | On connection close (any reason) | Unregister from `BroadcastMap`, free resources |

Hooks are typed `ServerHookHandler = Arc<dyn FnContextPinBox<()>>`, so they share the same `&mut Context` semantics as hyperlane routes/middleware.

## Common pitfalls

1. **Hook order in `set_*_hook::<T>()`** — turbofish syntax: `set_connected_hook::<MyHook>()`, NOT `set_connected_hook(MyHook::new())`. The `S` generic resolves to the hook type via inventory, not via direct call.
2. **`WebSocketConfig<'a, B>` borrows `Context`** — the `'a` lifetime ties the config to the original `Context`. Don't move the `Context` out before `run` finishes.
3. **`BroadcastMap` cardinality** — `set_capacity` sets the **per-channel** buffer size, not the global one. If you have 1000 groups with capacity 64, total buffered messages can reach 64 000.
4. **Connection is auto-removed on close** — `WebSocketServer::run` cleans up the `BroadcastMap` entry. Don't double-remove from a `set_closed_hook`; you'll get `None` from `unsubscribe`.
5. **`receiver_count_before_connected` ≠ `receiver_count`** — first is the count seen by THIS connection when it joined; second is the live count including this connection. Use `before` for "you're the Nth to join" messages.
6. **Inventory compilation** — if you feature-gate this crate behind a flag, gate the call site too. `Server::new().await` will hang at `inventory::collect` if the plugin crate is in dev-dependencies only.
7. **`hyperlane-broadcast` version pinning** — `hyperlane-plugin-websocket 14.x` ↔ `hyperlane-broadcast 2.x`. Mismatched majors break the `BroadcastSendError<T>` type alias.
8. **`set_capacity(0)` is undefined** — Tokio's broadcast channel requires capacity ≥ 1. Pass at least 1 or use the default 1024.

## Verification checklist

- [ ] `cargo check -p hyperlane-plugin-websocket` exits 0
- [ ] `cargo clippy --all-targets -p hyperlane-plugin-websocket` 0 warnings
- [ ] WebSocket upgrade: `wscat -c ws://127.0.0.1/ws` connects
- [ ] Broadcast: opening 2 sockets in the same group + `server.send` delivers to both
- [ ] Cleanup: closing one socket removes it from `receiver_count`
- [ ] `inventory` cold-start: `Server::new().await` completes within ~1s (long hang = missing plugin in deps)

## Source-of-truth files

- `Cargo.toml` — version `14.0.15`, deps `hyperlane 21.3.3` + `hyperlane-broadcast 2.0.9`
- `src/lib.rs` — re-export facade + `inventory::submit!` for `WebSocketServer`
- `src/enum.rs` — `BroadcastType<T>`
- `src/trait.rs` — `BroadcastTypeTrait`
- `src/struct.rs` — `WebSocket`, `WebSocketConfig`
- `src/impl.rs` — all method impls (`new`, `set_*`, `get_*`, `send`, `try_send`, `run`)
- `src/const.rs` — defaults
- `tests/` — upgrade + broadcast + cleanup round-trips

## Related skills

- `hyperlane` — HTTP framework this plugin hooks into
- `hyperlane-broadcast` — `Broadcast<T>` + `BroadcastMap<T>` backing store
- `hyperlane-quick-start` — reference app using this in `controller/websocket` + `application/view/websocket`
- `tokio` — `tokio::sync::broadcast` underlying channel
- `inventory` — static-init plugin collection mechanism (`Server::new().await` picks plugins up automatically)