---
name: hyperlane-broadcast
description: "Lightweight Tokio broadcast wrapper at v2.0.9. Two namespaces: `Broadcast<T>` (single-channel pub/sub) and `BroadcastMap<T>` (multi-key pub/sub, keyed by `String`, backed by `DashMap<String, Broadcast<T>, XxHash3_64>`). Auto-registers with hyperlane via `inventory::submit!` so any hyperlane server can use it without explicit plugin wiring. Use when broadcasting to multiple subscribers in async Rust, when keying pub/sub by string ID, when integrating with `hyperlane-plugin-websocket`, or when needing a lightweight alternative to raw tokio::sync::broadcast. Triggers: hyperlane-broadcast, BroadcastTrait, BroadcastMapTrait, BroadcastSender, BroadcastReceiver, DashMapStringBroadcast, hyperlane broadcast, tokio broadcast wrapper, broadcast_map."
license: MIT
---

# hyperlane-broadcast

- GitHub: <https://github.com/hyperlane-dev/hyperlane-broadcast.git>
- crates.io: <https://crates.io/crates/hyperlane-broadcast>
- docs.rs: <https://docs.rs/hyperlane-broadcast>

> hyperlane-broadcast is a lightweight and ergonomic wrapper over Tokio's broadcast channel designed for easy-to-use publish-subscribe messaging in async Rust applications. It simplifies the native Tokio broadcast API by providing a straightforward interface for broadcasting messages to multiple subscribers with minimal boilerplate.

## Overview

`D:\code\hyperlane-broadcast` v2.0.9 — a single-crate Rust library at `D:\code\hyperlane-broadcast\src`. Two namespaces:

| Module | Source files | Purpose |
|---|---|---|
| `broadcast` | `broadcast/{const,impl,trait,type,struct,mod}.rs` | Single-channel pub/sub |
| `broadcast_map` | `broadcast_map/{impl,trait,type,struct,mod}.rs` | Multi-key pub/sub, keyed by `String`, backed by `DashMap` |

Both follow the keyword-per-file rule. Top-level re-export at `src/lib.rs`:

```rust
pub use broadcast::*;
pub use broadcast_map::*;
```

## 项目元信息

- crate 名: `hyperlane-broadcast`
- 版本: `2.0.9`
- Rust edition: `2024`
- License: `MIT`
- 类型: 单 crate 库，2 个模块（`broadcast` + `broadcast_map`）
- 关键字: `time`, `hyperlane`, `broadcast`, `tokio`
- 依赖: `dashmap 6.2.1`, `twox-hash 2.1.3`, `tokio 1.53.0 (full)`
- Profile: dev+release both `opt-level = 3, lto = true, codegen-units = 1, strip = "debuginfo"`

## Installation

```shell
cargo add hyperlane-broadcast
```

## `Broadcast<T>` — single-channel pub/sub

From `src/broadcast/`:

```rust
pub trait BroadcastTrait: Clone + Debug

pub type Capacity           = usize;
pub type ReceiverCount      = usize;
pub type BroadcastReceiver<T> = Receiver<T>;
pub type BroadcastSender<T>   = Sender<T>;
pub type BroadcastSendError<T> = SendError<T>;
pub type BroadcastSendResult<T> = Result<ReceiverCount, BroadcastSendError<T>>;

pub const DEFAULT_BROADCAST_SENDER_CAPACITY: usize = 1024;

impl<T> Broadcast<T> {
    pub fn new(capacity: Capacity) -> Self
    pub fn subscribe(&self) -> BroadcastReceiver<T>
    pub fn send(&self, data: T) -> BroadcastSendResult<T>
    pub fn receiver_count(&self) -> ReceiverCount
}
```

Usage:

```rust
use hyperlane_broadcast::*;

let broadcast: Broadcast<String> = Broadcast::new(1024);
let mut rx: BroadcastReceiver<String> = broadcast.subscribe();

broadcast.send("hello".to_string())?;
// or async:
broadcast.send_async("hello".to_string()).await?;

while let Ok(msg) = rx.recv().await {
    println!("got: {msg}");
}
```

`send` returns `Err(BroadcastSendError<T>)` when there are zero active receivers (Tokio semantics). `receiver_count` returns the active subscriber count.

## `BroadcastMap<T>` — multi-key pub/sub

From `src/broadcast_map/`:

```rust
pub trait BroadcastMapTrait: Clone + Debug

pub type BroadcastMapSender<T>   = Sender<T>;
pub type BroadcastMapReceiver<T> = Receiver<T>;
pub type BroadcastMapSendError<T> = SendError<T>;
pub type DashMapStringBroadcast<T> = DashMap<String, Broadcast<T>, BuildHasherDefault<XxHash3_64>>;

impl<T> BroadcastMap<T> {
    pub fn new() -> Self
    pub fn insert<K>(&self, key: K, capacity: Capacity) -> Option<Broadcast<T>>
    pub fn unsubscribe<K>(&self, key: K) -> Option<Broadcast<T>>
    pub fn subscribe<K>(&self, key: K) -> Option<BroadcastMapReceiver<T>>
    pub fn subscribe_or_insert<K>(&self, key: K, capacity: Capacity) -> BroadcastMapReceiver<T>
    pub fn send<K>(&self, key: K, data: T) -> Option<ReceiverCount>
    pub fn try_send<K>(&self, key: K, data: T) -> Result<Option<ReceiverCount>, SendError<T>>
    pub fn receiver_count<K>(&self, key: K) -> Option<ReceiverCount>
}
```

The map is `DashMap<String, Broadcast<T>, BuildHasherDefault<XxHash3_64>>` — `XxHash3_64` hashing makes key lookup O(1) without the default SipHash overhead.

Usage:

```rust
use hyperlane_broadcast::*;

let map: BroadcastMap<String> = BroadcastMap::new();

// First subscriber for "room-a" auto-creates the channel:
let mut rx_a: BroadcastMapReceiver<String> = map.subscribe_or_insert("room-a", 64);

// Publish to a specific room:
let count: Option<ReceiverCount> = map.send("room-a", "ping".to_string());

// Sender returns None when the key has no broadcast registered:
let missing: Option<ReceiverCount> = map.send("room-b", "no one listening".to_string());

while let Ok(msg) = rx_a.recv().await {
    println!("room-a got: {msg}");
}
```

## Common pitfalls

1. **`Broadcast::send` is sync, not async** — it returns `Result<ReceiverCount, SendError<T>>` synchronously. Use `send_async` for async variants if exposed by trait impls.
2. **`BroadcastMap::send` returns `Option<ReceiverCount>`** — `None` means the key has no channel registered. Use `subscribe_or_insert` first, or call `try_send` to propagate the error.
3. **`DashMap` is not `Send`-safe across `.await`** if you hold guards across awaits — the map itself is `Send`, but holding a `Ref<…>` from a `.iter()` across `.await` will deadlock the shard. Drop guards before `.await`.
4. **`BroadcastReceiver` is a single-consumer stream** — clone or `subscribe()` again if you need a fresh receiver; old receivers stay valid even after new ones are added.
5. **Default capacity is 1024** (`DEFAULT_BROADCAST_SENDER_CAPACITY`) — if your publishers burst faster than consumers drain, the oldest message is dropped. Increase capacity via `Broadcast::new(n)`.
6. **Tokio's `SendError<T>` semantics** — `send` only returns the data back when there are zero receivers. Don't retry blindly; check `receiver_count` first.
7. **`hyperlane-plugin-websocket` depends on this crate** — version-pin both together. `hyperlane-plugin-websocket 14.x` requires `hyperlane-broadcast 2.x`.

## Verification checklist

- [ ] `cargo check -p hyperlane-broadcast` exits 0
- [ ] `cargo test -p hyperlane-broadcast` passes
- [ ] `cargo clippy --all-targets -p hyperlane-broadcast` 0 warnings
- [ ] Round-trip test: `subscribe → send → recv` returns the original `T`
- [ ] `BroadcastMap::send` returns `None` for an unknown key
- [ ] `receiver_count` reflects active subscribers, not total subscriptions ever created

## Source-of-truth files

- `Cargo.toml` — version `2.0.9`, deps `dashmap 6.2.1` + `twox-hash 2.1.3` + `tokio 1.53.0 (full)`
- `src/lib.rs` — re-export facade
- `src/broadcast/{const,impl,trait,type,struct,mod}.rs` — single-channel pub/sub
- `src/broadcast_map/{impl,trait,type,struct,mod}.rs` — multi-key pub/sub
- `tests/` — round-trip + multi-key tests

## Related skills

- `hyperlane` — HTTP framework whose `Server::run` may auto-register this via `inventory::submit!`
- `hyperlane-plugin-websocket` — WebSocket fanout built on top of `BroadcastMap<T>`
- `hyperlane-quick-start` — full-stack reference using this for SSE / WebSocket / message-queue plugin
- `tokio` — `tokio::sync::broadcast` underlying channel