---
name: hyperlane-quick-start
description: "Full-stack reference web app built on the hyperlane HTTP framework. Workspace of 5 crates (application + bootstrap + config + plugin + resources) at v23.0.28, layered as application/{controller (32) / service (26) / model (3) / view (30)} + plugin/ (11 plugins: database / docker / env / logger / message_queue / mysql / postgresql / process / redis / shutdown / common) + config/ + resources/. Bundles authentication, JWT, database (sea-orm), WebSocket (via hyperlane-plugin-websocket), SSE (via hyperlane-broadcast), AI workflow, online judge, GitHub Pages proxy, Redis, RSS, and 30+ HTTP endpoints. Use when building a complete production hyperlane server, when copying the layered architecture, or when investigating the bootstrap→config→plugin→application lifecycle. Triggers: hyperlane-quick-start, hyperlane_application, hyperlane_bootstrap, hyperlane_config, hyperlane_plugin, hyperlane_resources, hyperlane-quick-start workspace, controller service view model."
license: MIT
---

# hyperlane-quick-start

- GitHub: <https://github.com/hyperlane-dev/hyperlane-quick-start.git>
- crates.io: <https://crates.io/crates/hyperlane-quick-start>
- docs.rs: <https://docs.rs/hyperlane-quick-start>

> A lightweight rust http server with middleware, websocket, sse, and tcp support, built on tokio for cross-platform async networking, hyperlane simplifies modern web service development.

## Overview

`D:\code\hyperlane-quick-start` is a **workspace of 5 crates** that compose a production-ready full-stack hyperlane server. Members (from `Cargo.toml` `[workspace]`):

| Member crate | Path | Purpose |
|---|---|---|
| `hyperlane_application` | `application/` | Core: 32 controllers + 26 services + 3 models + 30 views. Depends on `hyperlane_config` / `hyperlane_plugin` / `hyperlane_resources`. |
| `hyperlane_bootstrap` | `bootstrap/` | Framework lifecycle / entrypoint. Wires config → plugins → application run. |
| `hyperlane_config` | `config/` | Configuration loading (file, env, runtime). |
| `hyperlane_plugin` | `plugin/` | 11 plugins: `common` / `database` / `docker` / `env` / `logger` / `message_queue` / `mysql` / `postgresql` / `process` / `redis` / `shutdown`. |
| `hyperlane_resources` | `resources/` | Static-resource serving + per-page frontend bundles. |

Workspace-level dependencies (from `Cargo.toml`):

```toml
tracing = "0.1.44"
hyperlane = "21.3.3"
hyperlane-utils = "33.1.9"
serde = { version = "1.0.229", features = ["derive"] }
```

## 项目元信息

- crate 名: `hyperlane-quick-start` (workspace root)
- 版本: `23.0.28`
- Rust edition: `2024`
- License: `MIT`
- 类型: `[workspace]` with 5 members: `application`, `bootstrap`, `config`, `plugin`, `resources`
- 关键字: `http`, `request`, `response`, `tcp`, `cross-platform`
- 依赖生态: `hyperlane 21.3.3`, `hyperlane-utils 33.1.9`, `serde 1`, `tracing 0.1.44`
- 控制器数量: **32** (ai_workflow, auth, blog, chat, chat_v2, cicd, conversation, euv_playground, github_pages, gomoku, group, health, index, judge_server, log, monitor, network_capture, notification, online, openapi, order, quantitative, redis, rss, shortlink, sse, templates, trace, tracking, upload, user, websocket)
- 服务数量: **26**
- 模型数量: **3** (`application`, `request`, `response`)
- 视图数量: **30**
- 插件数量: **11**

## Application layer (32 controllers)

```rust
// application/controller/<name>/{fn,impl,struct,mod}.rs — same Rust-keyword file convention as hyperlane
// application/service/<name>/{fn,impl,struct,mod}.rs    — pure data + sanitize + persist, no HTTP I/O
// application/model/<name>/{fn,impl,struct,enum,mod}.rs — shared across controllers and services
// application/view/<name>/{fn,impl,struct,mod}.rs        — HTTP-handler shell, glues controller to hyperlane's Context
```

| Domain | Controllers |
|---|---|
| Identity | `auth`, `user`, `group` |
| Content | `blog`, `order`, `rss`, `shortlink`, `templates` |
| Real-time | `chat`, `chat_v2`, `conversation`, `notification`, `online`, `websocket`, `sse` |
| DevOps | `cicd`, `docker`, `judge_server`, `monitor`, `trace`, `log`, `process` |
| AI / Quant | `ai_workflow`, `quantitative`, `gomoku` |
| Data | `redis`, `upload`, `tracking`, `network_capture` |
| Utility | `health`, `index`, `openapi`, `github_pages`, `euv_playground`, `database` (in plugin/) |

Each controller typically pairs with a same-named service under `application/service/<name>/`. The HTTP-handler glue lives in `application/view/<name>/` and follows the keyword-per-file convention: `fn.rs` (free fns), `impl.rs` (impl blocks), `struct.rs` (struct decls), `enum.rs`, `mod.rs` (re-exports).

## Plugin layer (11 plugins)

`plugin/` is a tree of reusable, optional subsystems registered at boot. Each plugin ships its own `Cargo.toml` and is wired into `Server::default()` via `handle_hook(HookType::*)` or `route` calls:

| Plugin | Path | Role |
|---|---|---|
| `common` | `plugin/common/` | Shared utilities (cross-plugin glue) |
| `database` | `plugin/database/` | Sea-ORM entity layer (used by auth, blog, order, etc.) |
| `mysql` / `postgresql` | `plugin/mysql/` / `plugin/postgresql/` | DB driver backends |
| `redis` | `plugin/redis/` | Redis connection pool + broadcast bridge |
| `message_queue` | `plugin/message_queue/` | Pub/sub bridge over `hyperlane-broadcast` |
| `logger` | `plugin/logger/` | `tracing` integration, request logging, panic recovery |
| `env` | `plugin/env/` | Environment-variable loader |
| `docker` | `plugin/docker/` | Optional docker daemon proxy |
| `process` | `plugin/process/` | Process supervisor (subprocess spawn / reap) |
| `shutdown` | `plugin/shutdown/` | Graceful shutdown coordination |

## Bootstrap (entrypoint)

`bootstrap/` wires config + plugins + application into a single `Server`. Typical lifecycle:

```text
bootstrap::run()
  ├── config::load()              ← hyperlane_config
  ├── plugin::init_all()          ← 11 plugins from plugin/
  ├── application::register_routes()  ← 32 controllers via Server::default().route::<H>(path)
  └── Server::new().await.run().await
       ↓
       ServerControlHook { wait_hook, shutdown_hook }
```

## Quick start

```sh
git clone https://github.com/hyperlane-dev/hyperlane-quick-start.git
cd hyperlane-quick-start

cargo build --release
cargo run --release -p hyperlane_bootstrap
```

The server listens on the address configured in `config/`. Default endpoints:

- `GET /` — `index` controller
- `GET /health` — `health` controller
- `GET /openapi` — `openapi` controller (OpenAPI 3 JSON)
- `GET /docs` — `docs` view (Swagger UI)
- `GET /euv` — `euv` view (euv framework demo page, served from `resources/static/euv/`)
- `GET /euv-playground` — `euv_playground` controller + view (online IDE)
- `GET /sse` — `sse` controller (Server-Sent Events)
- `GET /ws` — `websocket` controller (WebSocket upgrade)
- `/api/auth/*`, `/api/blog/*`, `/api/order/*`, etc.

## Layered architecture

```text
HTTP request
  ↓
application/view/<x>/fn.rs          ← hyperlane Context handler (parse path / query / body)
  ↓
application/controller/<x>/fn.rs   ← route → use-case dispatch
  ↓
application/service/<x>/fn.rs      ← business logic (pure, no HTTP)
  ↓
plugin/database/, plugin/redis/     ← persistence + cache
  ↓
application/model/<x>/struct.rs     ← DTO + DB entity
  ↓
JSON response
```

Every layer follows the keyword-per-file rule (`fn.rs` / `impl.rs` / `struct.rs` / `enum.rs` / `mod.rs`). External API symbols (the ones hyperlane reaches via `route::<T>(path)`) are always the `view` layer's handler fn — never controller or service fns.

## API surface (root crate)

```rust
// In hyperlane-quick-start's own lib.rs (workspace root)
pub use hyperlane_application::*;
pub use hyperlane_bootstrap::*;
pub use hyperlane_config::*;
pub use hyperlane_plugin::*;
pub use hyperlane_resources::*;
```

The 5 member crates are independently versioned at `23.0.28` and re-exported at the root for convenience. In a real deployment, the binary crate is `hyperlane_bootstrap` (which depends on `hyperlane_application`).

## Common pitfalls

1. **Don't add `controller` logic that does I/O** — controllers dispatch to services. Direct `Context::set_response_body` in controllers is a layering violation; route through `view` + `service`.
2. **`route::<T>(path)` in application must point at view-layer fn** — `route::<controller_fn>` will compile but bypasses the view glue that adapts Context to controller args.
3. **Plugin order matters** — `plugin/database` must be initialized before any controller that touches a Sea-ORM entity. `bootstrap/` encodes the init order.
4. **`plugin/redis` ≠ `plugin/message_queue`** — redis is the storage backend; message_queue is the pub/sub bridge built on top of `hyperlane-broadcast`. Use message_queue for WebSocket fanout, redis for KV.
5. **Don't skip the keyword-per-file rule** — `application/controller/auth/{fn.rs,impl.rs,struct.rs,mod.rs}` is the established layout. Mixing handlers into `mod.rs` breaks audit tooling.
6. **`Server::new().await` is async** — `bootstrap::run` must be `async fn`. Forgetting `await` on `Server::new()` silently picks up zero plugins.
7. **`inventory` collection** — every plugin that registers a hook MUST compile in the final binary; if you feature-gate a plugin, gate the hook registration too, or boot will hang at `inventory::collect`.

## Verification checklist

- [ ] `cargo check --workspace` exits 0
- [ ] `cargo clippy --workspace --all-targets` 0 warnings
- [ ] `cargo test -p hyperlane_application` passes
- [ ] `GET /health` returns 200
- [ ] `GET /openapi` returns 200 with OpenAPI 3 JSON
- [ ] WebSocket: `wscat -c ws://127.0.0.1/ws` upgrades and echoes
- [ ] SSE: `curl -N http://127.0.0.1/sse` streams events
- [ ] `plugin::database` migrations apply on cold start

## Source-of-truth files

- `Cargo.toml` — workspace + member declarations + version pinning (`hyperlane = "21.3.3"`, `hyperlane-utils = "33.1.9"`)
- `bootstrap/src/lib.rs` — entrypoint + lifecycle order
- `application/controller/<x>/{fn,impl}.rs` — 32 domain controllers
- `application/service/<x>/{fn,impl}.rs` — 26 services (pure logic)
- `application/model/{application,request,response}/` — 3 model namespaces
- `application/view/<x>/{fn,impl}.rs` — 30 hyperlane Context handlers
- `plugin/<x>/src/lib.rs` — 11 plugins
- `config/src/lib.rs` — config loader
- `resources/static/<x>/` — frontend bundles served by `application/view/static_resource`

## Related skills

- `hyperlane` — core HTTP framework (Server builder / Context / HookType)
- `hyperlane-broadcast` — Tokio broadcast wrapper used by plugin/message_queue
- `hyperlane-plugin-websocket` — WebSocket plugin used by `controller/websocket`
- `hyperlane-macros` — `lombok-macros`-derived types used throughout
- `hyperlane-log` — async logging helpers used by plugin/logger
- `euv` — frontend framework rendered by `view/euv` and `view/euv_playground`
- `rust-standards` — keyword-per-file layout enforced across all 5 crates